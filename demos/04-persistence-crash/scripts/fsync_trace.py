"""Conservatively analyze AOF writes and completed fsync syscalls.

Trace only the initial AOF instance, never its recovery/cleanup.
Confirmation is an OS-level sync acknowledgment, not a physical
power-loss test.
"""

import re
import subprocess
import time
from io import BytesIO

import aof_reader
import constants as settings


class AofTrace:
    def __init__(self, directory):
        self.directory = directory
        directory.mkdir()
        self.process = None
        self.stderr = None
        self.kill_before_epoch = None
        self.started_epoch = time.time()
        self.started_mono = time.monotonic()
        self.clock_consistent = False

    def launch(self, config):
        """Start strace on a Redis server with the given config file."""
        self.stderr = (self.directory / "strace.stderr").open(
            "w", encoding="utf-8"
        )
        # Redis is a child of strace; no sudo/ptrace attach is needed.
        self.process = subprocess.Popen(
            [
                "strace", "-ff", "-ttt", "-T", "-yy",
                "-s", str(settings.TRACE_STRING_LIMIT),
                "-e", "trace=write,writev,fsync,fdatasync",
                "-o", str(self.directory / "aof"), "redis-server", str(config),
            ],
            stdout=subprocess.DEVNULL,
            stderr=self.stderr,
        )

    def check_running(self):
        if self.process is None or self.process.poll() is not None:
            raise RuntimeError(
                f"strace exited during startup; inspect {self.directory}"
            )

    def mark_before_kill(self):
        self.kill_before_epoch = time.time()
        elapsed = time.monotonic() - self.started_mono
        self.clock_consistent = (
            abs(self.kill_before_epoch - self.started_epoch - elapsed)
            < settings.CLOCK_DRIFT_TOLERANCE_SECONDS
        )

    def finish(self):
        """Drain trace files after SIGKILL and before restart."""
        if self.process is None:
            raise RuntimeError("AOF trace was not started")
        self.process.wait(timeout=settings.TRACE_DRAIN_TIMEOUT_SECONDS)
        if self.stderr is not None:
            self.stderr.close()

    def close(self):
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(
                    timeout=settings.TRACE_TERMINATE_TIMEOUT_SECONDS
                )
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()
        if self.stderr is not None:
            self.stderr.close()


def analyze(
    directory, data_dir, expected_keys, kill_before_epoch,
    clock_consistent=True,
):
    evidence = {
        "status": "Unknown", "reason": "Incomplete trace evidence",
        "trace_dir": str(directory), "kill_before_epoch": kill_before_epoch,
        "tracing_overhead": True, "clock_consistent": clock_consistent,
    }
    if not clock_consistent or kill_before_epoch is None:
        evidence["reason"] = (
            "Wall clock discontinuity or no pre-signal timestamp"
        )
        return evidence
    files = list((data_dir / "appendonlydir").glob("*.incr.aof"))
    if len(files) != settings.EXPECTED_INCREMENTAL_AOF_FILES:
        evidence["reason"] = (
            "Expected one incremental AOF with rewrite disabled"
        )
        return evidence
    target = files[0]
    payload = target.read_bytes()
    # Confirm the file at crash contains all acknowledged writes.
    # These bytes alone do NOT prove fsync; check syscalls below.
    values = {}
    stream = BytesIO(payload)
    try:
        while stream.tell() < len(payload):
            command = aof_reader.read_command(stream)
            if command == [b"SELECT", str(settings.REDIS_DATABASE).encode()]:
                continue
            if len(command) != 3 or command[0] != b"SET":
                raise ValueError("Unexpected workload or AOF command")
            values[command[1]] = command[2]
    except (ValueError, IndexError, TypeError):
        evidence["reason"] = "Cannot verify complete delta in incremental AOF"
        return evidence
    complete = len(values) == expected_keys and all(
        values.get(f"demo:{i:0{settings.KEY_INDEX_WIDTH}d}".encode())
        == f"value:{i:0{settings.KEY_INDEX_WIDTH}d}".encode()
        for i in range(expected_keys)
    )
    evidence["verified_values_at_crash"] = len(values)
    if not complete:
        evidence["reason"] = (
            "Not all acknowledged keys are present in the traced AOF"
        )
        return evidence

    # -ff keeps thread files separate. Unsupported/unfinished lines for
    # this AOF are Unknown, not guessed as a confirmation.
    pattern = re.compile(
        r"^(\d+\.\d+)\s+(write|writev|fsync|fdatasync)"
        r"\(\d+<([^>]+)>.*\)\s+=\s+(-?\d+)\s+<(\d+\.\d+)>$"
    )
    writes, syncs = [], []
    target_path = str(target.resolve())
    raw_files = list(directory.glob("aof.*"))
    for path in raw_files:
        for line in path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            if target_path not in line:
                continue
            match = pattern.match(line)
            if not match:
                evidence["reason"] = (
                    "Unparsed or unfinished syscall on incremental AOF"
                )
                return evidence
            start, name, file_path, result, duration = match.groups()
            if file_path != target_path:
                continue
            start, result, duration = (
                float(start), int(result), float(duration)
            )
            end = start + duration
            if name in ("write", "writev"):
                if result <= 0 or end >= kill_before_epoch:
                    evidence["reason"] = (
                        "Failed or ambiguously timed AOF write"
                    )
                    return evidence
                writes.append({"start": start, "end": end, "bytes": result})
            else:
                syncs.append({
                    "start": start, "end": end, "result": result, "call": name
                })
    evidence.update({
        "aof_file": target_path,
        "aof_bytes": len(payload),
        "observed_write_bytes": sum(w["bytes"] for w in writes),
        "writes": writes,
        "syncs": syncs,
    })
    if not writes or evidence["observed_write_bytes"] != len(payload):
        evidence["reason"] = (
            "Trace does not account for every incremental AOF byte"
        )
        return evidence
    last_write_end = max(w["end"] for w in writes)
    evidence["last_write_end_epoch"] = last_write_end
    # Keep a separation margin for rounded microsecond timestamps.
    confirmed = [
        s for s in syncs
        if s["result"] == 0
        and s["start"] > (
            last_write_end + settings.SYNC_TIMESTAMP_MARGIN_SECONDS
        )
        and s["end"] < (
            kill_before_epoch - settings.SYNC_TIMESTAMP_MARGIN_SECONDS
        )
    ]
    if confirmed:
        evidence["status"] = "Confirmed"
        evidence["reason"] = (
            "Successful sync starts after all delta writes "
            "and completes before SIGKILL"
        )
        evidence["confirmed_sync"] = min(confirmed, key=lambda s: s["end"])
    else:
        evidence["status"] = "Not confirmed"
        evidence["reason"] = (
            "No complete successful sync proven to cover all delta "
            "before SIGKILL"
        )
    return evidence
