#!/usr/bin/env python3
"""Controlled Redis RDB vs AOF process-crash experiment using redis-py.

Creates two LOCAL, independent Redis processes and checkpoints RDB after
a baseline. Issues a delta, delivers SIGKILL after the final ACKs
and restarts from the SAME directories to verify each key and value.

SIGKILL crashes the Redis PROCESS, not the power or operating system.
Run only in an isolated Linux lab, never on production Redis.
"""

import argparse
import math
import re
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import constants as settings
import fsync_trace
import redis_client as client
import redis_instance as instance
import results as artifacts

BASE = Path(__file__).resolve().parent.parent
REPO_ROOT = BASE.parent.parent
CONFIG_DIR = REPO_ROOT / "redis"
# Kill AOF FIRST so killing RDB does not give it extra time to fsync.
KILL_ORDER = ("aof", "rdb")


def run_trial(
    trial, baseline, delta, delay, run_root, prekill_dbsize=False,
    pause=False, trace_fsync=False,
):
    stamp = time.strftime("%Y%m%d-%H%M%S")
    run_dir = Path(
        tempfile.mkdtemp(prefix=f"trial-{trial:02d}-{stamp}-", dir=run_root)
    )
    configs = {
        mode: instance.render_config(mode, run_dir, CONFIG_DIR)
        for mode in instance.MODES
    }
    attempts = []
    processes = {}
    tracer = (
        fsync_trace.AofTrace(run_dir / "aof-trace") if trace_fsync else None
    )
    total = baseline + delta
    try:
        initial_boot_ms = {}
        for mode, (conf, pidfile) in configs.items():
            # Register for cleanup even if startup fails partway.
            attempts.append(mode)
            if mode == "aof" and tracer is not None:
                initial_boot_ms[mode] = instance.start_instance(
                    mode, conf, pidfile, trace=tracer
                )
            else:
                initial_boot_ms[mode] = instance.start_instance(
                    mode, conf, pidfile
                )
        instance.verify_persistence_config()

        client.write_both(0, baseline, instance.MODES)
        if any(
            client.redis(port, "DBSIZE") != baseline
            for port in instance.MODES.values()
        ):
            raise RuntimeError("Unexpected baseline key count")
        instance.checkpoint_rdb(run_dir)

        # Capture CONFIG, INFO, PID and sizes BEFORE the critical delta.
        # These files are PRE-DELTA, not INFO collected at crash.
        for mode in instance.MODES:
            artifacts.write_json(
                run_dir / mode / "before-delta-info.json",
                client.collect_info(instance.MODES[mode]),
            )
        if pause:
            artifacts.print_path("Checkpoint files", run_dir)
            input("  [Paused] Press Enter to write delta + SIGKILL: ")
        processes = instance.open_verified_pidfds(configs)
        print(
            f"  [Ready] Trial {trial}: checkpoint saved; "
            f"{delta} delta SETs -> wait {delay:g}s -> SIGKILL.",
            flush=True,
        )

        # CRITICAL: no INFO, DBSIZE, JSON or file logging after ACK.
        ack_times = client.write_both(baseline, total, instance.MODES)
        measured_pre = {mode: "" for mode in instance.MODES}
        if prekill_dbsize:
            # OPTIONAL: screenshots at the cost of extra ACK->kill time.
            measured_pre = {
                mode: client.redis(port, "DBSIZE")
                for mode, port in instance.MODES.items()
            }
            if any(count != total for count in measured_pre.values()):
                raise RuntimeError("DBSIZE differs from ACKed SET count")
        if delay:
            time.sleep(delay)
        kill_times = {}
        for mode in KILL_ORDER:
            if mode == "aof" and tracer is not None:
                tracer.mark_before_kill()
            kill_times[mode] = instance.kill_verified_process(
                mode, processes[mode]
            )
        # END TIMING-CRITICAL REGION.

        for port in instance.MODES.values():
            instance.wait_dead(port)
        instance.close_pidfds(processes)
        # Measure file size after crash but BEFORE AOF restart.
        bytes_at_crash = {
            mode: artifacts.folder_bytes(run_dir / mode / "data")
            for mode in instance.MODES
        }
        fsync_evidence = None
        if tracer is not None:
            tracer.finish()
            fsync_evidence = fsync_trace.analyze(
                tracer.directory, run_dir / "aof" / "data", total,
                tracer.kill_before_epoch, tracer.clock_consistent,
            )
            artifacts.write_json(
                run_dir / "aof" / "fsync-evidence.json", fsync_evidence
            )

        result_rows = []
        for mode, (conf, pidfile) in configs.items():
            port = instance.MODES[mode]
            recovered_boot_ms = instance.start_instance(mode, conf, pidfile)
            post = client.verify_range(port, total, baseline)
            after_info = artifacts.write_json(
                run_dir / mode / "after-restart-info.json",
                client.collect_info(port),
            )
            pid_after = instance.check_pid(port, pidfile)
            pers_bytes = artifacts.folder_bytes(run_dir / mode / "data")
            row = {
                "trial": trial,
                "delay_seconds": delay,
                "mode": mode,
                "port": port,
                "redis_py_version": client.REDIS_PY_VERSION,
                "pid_before": processes[mode]["pid"], "pid_after": pid_after,
                "baseline_keys": baseline, "delta_keys": delta,
                # Expected count comes from ALL SET ACKs, not DBSIZE.
                "expected_dbsize_before": total,
                "dbsize_before_measured": measured_pre[mode],
                "dbsize_after": post["dbsize"],
                "verified_correct_after": post["verified_correct"],
                "missing_keys": post["missing_keys"],
                "corrupt_keys": post["corrupt_keys"],
                "not_recovered_keys": post["not_recovered_keys"],
                "missing_baseline": post["missing_baseline"],
                "missing_delta": post["missing_delta"],
                "sample_missing_ids": post["sample_missing_ids"],
                "sample_corrupt_ids": post["sample_corrupt_ids"],
                "persistence_bytes_at_crash": bytes_at_crash[mode],
                "persistence_bytes_after_restart": pers_bytes,
                "startup_ms": recovered_boot_ms,
                "initial_startup_ms": initial_boot_ms[mode],
                "last_write_ack_epoch": ack_times[mode]["epoch"],
                "kill_epoch": kill_times[mode]["epoch"],
                "ack_to_kill_seconds": round(
                    (kill_times[mode]["mono_ns"] - ack_times[mode]["mono_ns"])
                    / settings.NANOSECONDS_PER_SECOND,
                    settings.ACK_SECONDS_DECIMAL_PLACES,
                ),
                "rdb_last_bgsave_status": after_info["persistence"].get(
                    "rdb_last_bgsave_status", ""
                ),
                "aof_last_write_status": after_info["persistence"].get(
                    "aof_last_write_status", ""
                ),
            }
            if fsync_evidence is not None:
                row["fsync_tracing"] = True
                row["delta_fsync_status"] = (
                    fsync_evidence["status"] if mode == "aof" else "N/A"
                )
                if mode == "aof":
                    row["fsync_evidence"] = fsync_evidence
            result_rows.append(row)
        artifacts.save_trial_results(run_dir, trial, result_rows)
        return result_rows
    finally:
        instance.close_pidfds(processes)
        # Stop only matching PID, pidfile and /proc identities.
        for mode in attempts:
            try:
                instance.stop_owned_instance(mode, configs[mode][1])
            except Exception as exc:
                print(
                    f"WARNING: cleanup failed for {mode}: {exc}",
                    file=sys.stderr,
                )
        if tracer is not None:
            tracer.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--trials", type=int, default=settings.DEFAULT_TRIALS)
    parser.add_argument(
        "--baseline", type=int, default=settings.DEFAULT_BASELINE_KEYS
    )
    parser.add_argument(
        "--delta", type=int, default=settings.DEFAULT_DELTA_KEYS
    )
    parser.add_argument(
        "--delays", default=settings.DEFAULT_DELAYS_SECONDS,
        help=(
            "delay after BOTH delta batches ACK (seconds), "
            "cycled across trials"
        ),
    )
    parser.add_argument(
        "--measure-prekill-dbsize", action="store_true",
        help="measure real DBSIZE after delta; adds time before SIGKILL",
    )
    parser.add_argument(
        "--pause-after-checkpoint", action="store_true",
        help=(
            "wait for Enter BEFORE the final writes, "
            "useful in a live presentation"
        ),
    )
    parser.add_argument(
        "--trace-fsync", action="store_true",
        help=(
            "trace initial AOF write/fsync syscalls; "
            "adds overhead, requires strace"
        ),
    )
    args = parser.parse_args()
    if (
        not settings.MIN_TRIALS <= args.trials <= settings.MAX_TRIALS
        or args.baseline < 1 or args.delta < 1
    ):
        parser.error(
            f"trials must be {settings.MIN_TRIALS}..{settings.MAX_TRIALS}; "
            "baseline/delta must be positive"
        )
    try:
        delays = [float(x.strip()) for x in args.delays.split(",")]
        if not delays or any(
            not math.isfinite(x) or x < 0 or x > settings.MAX_DELAY_SECONDS
            for x in delays
        ):
            raise ValueError
    except ValueError:
        parser.error(
            "--delays must be comma-separated finite values "
            f"from 0 to {settings.MAX_DELAY_SECONDS}"
        )
    if not sys.platform.startswith("linux") or not Path(
        "/proc/self/stat"
    ).exists():
        sys.exit(
            "Run this demo on Linux with /proc mounted (or inside WSL Linux)."
        )
    if not shutil.which("redis-server"):
        sys.exit(
            f"Install redis-server >= {settings.MIN_REDIS_MAJOR_VERSION} "
            "first (Ubuntu: sudo apt install redis-server redis-tools)"
        )
    if args.trace_fsync and not shutil.which("strace"):
        sys.exit("Install strace first (Ubuntu: sudo apt install strace)")
    version = subprocess.run(
        ["redis-server", "--version"],
        text=True, capture_output=True, check=True,
    ).stdout.strip()
    match = re.search(r"v=(\d+)\.", version)
    if not match or int(match.group(1)) < settings.MIN_REDIS_MAJOR_VERSION:
        sys.exit(
            f"Redis {settings.MIN_REDIS_MAJOR_VERSION}+ required for "
            f"multi-part AOF demo, found: {version}"
        )
    for port in instance.MODES.values():
        if not instance.port_available(port):
            sys.exit(
                f"Port {port} is already in use: "
                "refusing to touch existing service"
            )
    artifacts.print_section("Redis persistence | RDB vs AOF everysec")
    artifacts.print_field("Server", version)
    artifacts.print_field(
        "Client",
        f"redis-py {client.REDIS_PY_VERSION}; RESP{settings.RESP_VERSION}; "
        "automatic retries disabled",
    )
    artifacts.print_field(
        "Instances",
        f"RDB :{instance.MODES['rdb']} | "
        f"AOF :{instance.MODES['aof']} | bind {settings.REDIS_HOST}",
    )
    artifacts.print_field(
        "Workload", f"{args.baseline} baseline + {args.delta} delta keys"
    )
    artifacts.print_field(
        "Trials", f"{args.trials}; delays (s): {args.delays} (cycled)"
    )
    artifacts.print_field(
        "Fsync trace", "Enabled" if args.trace_fsync else "Disabled"
    )
    print(
        "\n  WARNING: SIGKILL simulates a PROCESS crash, NOT power failure."
    )
    if args.measure_prekill_dbsize:
        print(
            "  NOTE: --measure-prekill-dbsize adds measurable delay "
            "before SIGKILL."
        )
    if args.trace_fsync:
        print(
            "  NOTE: strace changes timing. Fsync confirmation is OS-level,\n"
            "        not a power-loss test."
        )
    run_root = artifacts.create_run_dir(BASE)
    artifacts.print_path("Run files", run_root)
    print(flush=True)
    results = []
    for trial in range(1, args.trials + 1):
        try:
            results.extend(
                run_trial(
                    trial, args.baseline, args.delta,
                    delays[(trial - 1) % len(delays)],
                    run_root=run_root,
                    prekill_dbsize=args.measure_prekill_dbsize,
                    pause=args.pause_after_checkpoint,
                    trace_fsync=args.trace_fsync,
                )
            )
        finally:
            # Preserve completed trials even if a later trial fails.
            path = artifacts.write_summary(results, run_root)
            artifacts.print_path("Summary CSV (completed trials)", path)
            print(flush=True)
    artifacts.print_section("Run complete")
    print(
        "  Demo Redis instances were stopped "
        "after recovery measurements."
    )
    artifacts.print_path("Summary CSV", path)


if __name__ == "__main__":
    main()
