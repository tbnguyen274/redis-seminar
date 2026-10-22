"""Manage Redis config, processes, checkpoints and verified signals."""

import json
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path

import constants as settings
import redis_client as client

MODES = settings.REDIS_PORTS


def port_available(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((settings.REDIS_HOST, port)) != 0


def check_pid(port, config_pidfile):
    """Require agreement between Redis INFO, pidfile and /proc."""

    server = client.get_info(port, "server")
    pid = int(server["process_id"])

    actual_port = int(server["tcp_port"])
    if actual_port != port:
        raise RuntimeError(
            f"Redis INFO port mismatch: {actual_port} != {port}"
        )

    disk_pid = int(config_pidfile.read_text().strip())
    if disk_pid != pid:
        raise RuntimeError(
            f"PID mismatch, Redis INFO={pid}, pidfile={disk_pid}"
        )

    proc_comm = Path(f"/proc/{pid}/comm")
    if not proc_comm.exists() or not proc_comm.read_text().startswith(
        "redis-server"
    ):
        raise RuntimeError(
            f"Refusing to target PID {pid}: not a verified redis-server"
        )

    return pid


def process_start_ticks(pid):
    """Read /proc/<pid>/stat field 22 to check for PID reuse."""
    raw = Path(f"/proc/{pid}/stat").read_text()
    return raw.rsplit(") ", 1)[1].split()[
        settings.PROC_STARTTIME_INDEX_AFTER_COMM
    ]


def render_config(mode, run_dir, config_dir):
    template = (config_dir / f"redis-{mode}.conf").read_text(encoding="utf-8")
    home = run_dir / mode
    data = home / "data"
    data.mkdir(parents=True, exist_ok=True)

    mapping = {
        "@PID_FILE@": home / "redis.pid",
        "@LOG_FILE@": home / "redis.log",
        "@DATA_DIR@": data,
    }

    for marker, path in mapping.items():
        template = template.replace(marker, json.dumps(str(path)))

    target = home / f"{mode}.conf"
    target.write_text(template, encoding="utf-8")

    return target, mapping["@PID_FILE@"]


def start_instance(mode, conf, pidfile, trace=None):
    port = MODES[mode]
    if not port_available(port):
        raise RuntimeError(
            f"Port {port} is occupied; refusing to touch another Redis"
        )

    started = time.perf_counter()
    if trace is not None:
        trace.launch(conf)
    else:
        completed = subprocess.run(
            ["redis-server", str(conf)], text=True, capture_output=True,
            timeout=settings.REDIS_START_COMMAND_TIMEOUT_SECONDS,
        )
        if completed.returncode:
            raise RuntimeError(
                f"Failed to start Redis {mode}: "
                f"{completed.stderr} {completed.stdout}"
            )

    deadline = time.monotonic() + settings.REDIS_READY_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        if trace is not None:
            trace.check_running()
        if client.redis_ping(port):
            check_pid(port, pidfile)
            return round(
                (time.perf_counter() - started)
                * settings.MILLISECONDS_PER_SECOND,
                settings.MILLISECONDS_DECIMAL_PLACES,
            )
        time.sleep(settings.POLL_INTERVAL_SECONDS)

    raise RuntimeError(
        f"Redis on port {port} did not become ready; inspect redis.log"
    )


def wait_dead(port, timeout=settings.REDIS_STOP_TIMEOUT_SECONDS):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if port_available(port):
            return
        time.sleep(settings.POLL_INTERVAL_SECONDS)
    raise RuntimeError(f"Port {port} remained open after process termination")


def stop_owned_instance(mode, pidfile):
    port = MODES[mode]
    if not client.redis_ping(port):
        return
    try:
        check_pid(port, pidfile)
    except Exception as exc:
        print(
            f"WARNING: refusing cleanup on port {port}: {exc}",
            file=sys.stderr,
        )
        return
    try:
        # Only AFTER measurement; not part of the simulated failure.
        client.redis(port, "SHUTDOWN", "NOSAVE")
    except (OSError, client.RedisError, TimeoutError):
        # SHUTDOWN usually closes the connection without a response.
        pass
    wait_dead(port)


def verify_persistence_config():
    expected = {"rdb": ("no", ""), "aof": ("yes", "")}
    for mode, port in MODES.items():
        appendonly, save = expected[mode]
        if client.get_config(port, "appendonly") != appendonly:
            raise RuntimeError(f"{mode}: unexpected appendonly setting")
        if client.get_config(port, "save") != save:
            raise RuntimeError(
                f"{mode}: automatic RDB save should be disabled"
            )
    aof_port = MODES["aof"]
    if client.get_config(aof_port, "appendfsync") != "everysec":
        raise RuntimeError("AOF must use appendfsync everysec")
    if client.get_config(aof_port, "auto-aof-rewrite-percentage") != "0":
        raise RuntimeError("AOF auto rewrite must be disabled in this test")


def open_verified_pidfds(configs):
    """Pin processes before writes to avoid late INFO requests."""
    processes = {}
    try:
        for mode, (_conf, pidfile) in configs.items():
            pid = check_pid(MODES[mode], pidfile)
            birth = process_start_ticks(pid)
            fd = None
            if hasattr(os, "pidfd_open") and hasattr(
                signal, "pidfd_send_signal"
            ):
                try:
                    fd = os.pidfd_open(pid)
                except OSError as exc:
                    print(
                        f"WARNING: pidfd unavailable ({exc}); "
                        "using start-time verification",
                        file=sys.stderr,
                    )
            processes[mode] = {"pid": pid, "start_ticks": birth, "pidfd": fd}
        return processes
    except Exception:
        close_pidfds(processes)
        raise


def close_pidfds(processes):
    for process in processes.values():
        if process["pidfd"] is not None:
            os.close(process["pidfd"])
            process["pidfd"] = None


def kill_verified_process(mode, process):
    # pidfd avoids PID reuse and needs no network round trip.
    if process["pidfd"] is not None:
        signal.pidfd_send_signal(process["pidfd"], signal.SIGKILL)
    else:
        # On older Linux, check that the PID has not been reused.
        if process_start_ticks(process["pid"]) != process["start_ticks"]:
            raise RuntimeError(f"Refusing kill: {mode} PID was reused")
        os.kill(process["pid"], signal.SIGKILL)
    mono_ns = time.monotonic_ns()
    return {"mono_ns": mono_ns, "epoch": time.time()}


def checkpoint_rdb(run_dir):
    """Verify the baseline checkpoint before writing the delta."""
    rdb_port = MODES["rdb"]
    saves_before = int(
        client.get_info(rdb_port, "persistence").get("rdb_saves", "0")
    )
    if client.redis(rdb_port, "BGSAVE") is not True:
        raise RuntimeError("BGSAVE did not start")
    deadline = time.monotonic() + settings.RDB_CHECKPOINT_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        info = client.get_info(rdb_port, "persistence")
        if info.get("rdb_bgsave_in_progress") == 0:
            if info.get("rdb_last_bgsave_status") != "ok":
                raise RuntimeError("BGSAVE failed; check RDB log")
            if "rdb_saves" in info and int(info["rdb_saves"]) <= saves_before:
                raise RuntimeError(
                    "BGSAVE has not produced a new successful snapshot"
                )
            break
        time.sleep(settings.POLL_INTERVAL_SECONDS)
    else:
        raise RuntimeError(
            "BGSAVE did not complete in "
            f"{settings.RDB_CHECKPOINT_TIMEOUT_SECONDS} seconds"
        )
    if not (run_dir / "rdb" / "data" / "dump.rdb").is_file():
        raise RuntimeError("No dump.rdb was created")
