"""Run offline checks, not substitutes for Redis integration tests."""

import csv
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

SCRIPT = Path(__file__).resolve().parent.parent / "scripts" / "run_trials.py"
# Tests need sibling scripts on sys.path before the local imports.
sys.path.insert(0, str(SCRIPT.parent))
import run_trials as rt

client = rt.client
instance = rt.instance
artifacts = rt.artifacts


class TestConfig(unittest.TestCase):
    def test_config_rendering(self):
        with tempfile.TemporaryDirectory() as td:
            for mode in instance.MODES:
                conf, pidfile = instance.render_config(
                    mode, Path(td), rt.CONFIG_DIR
                )
                self.assertTrue(conf.is_file())
                self.assertIn(json.dumps(str(pidfile)), conf.read_text())
                for marker in ("@PID_FILE@", "@LOG_FILE@", "@DATA_DIR@"):
                    self.assertNotIn(marker, conf.read_text())
                self.assertIn('save ""', conf.read_text())
                self.assertIn(
                    f"port {instance.MODES[mode]}\n", conf.read_text()
                )
                self.assertIn(
                    f"bind {rt.settings.REDIS_HOST}\n", conf.read_text()
                )
            self.assertIn(
                "appendfsync everysec",
                (Path(td) / "aof" / "aof.conf").read_text(),
            )
            self.assertIn(
                "appendonly no", (Path(td) / "rdb" / "rdb.conf").read_text()
            )

    def test_summary_fields(self):
        self.assertEqual(
            len(artifacts.SUMMARY_FIELDS), len(set(artifacts.SUMMARY_FIELDS))
        )
        self.assertIn("expected_dbsize_before", artifacts.SUMMARY_FIELDS)
        self.assertIn("ack_to_kill_seconds", artifacts.SUMMARY_FIELDS)

    def test_folder_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "a").write_bytes(b"1234")
            (root / "nested").mkdir()
            (root / "nested" / "b").write_bytes(b"12")
            self.assertEqual(artifacts.folder_bytes(root), 6)

    @unittest.skipUnless(
        Path("/proc/self/stat").exists(), "Requires Linux procfs"
    )
    def test_starttime(self):
        self.assertTrue(instance.process_start_ticks(os.getpid()).isdigit())


class TestVerification(unittest.TestCase):
    def test_missing_vs_corrupt(self):
        # Four keys, baseline two; one nil and one wrong value.
        connection = MagicMock()
        connection.__enter__.return_value = connection
        connection.mget.return_value = [
            b"value:00000000", None, b"WRONG", b"value:00000003"
        ]
        connection.dbsize.return_value = 3
        with patch.object(client, "create_client", return_value=connection):
            outcome = client.verify_range(6380, 4, baseline=2)
        self.assertEqual(outcome["verified_correct"], 2)
        self.assertEqual(outcome["missing_keys"], 1)
        self.assertEqual(outcome["corrupt_keys"], 1)
        self.assertEqual(outcome["not_recovered_keys"], 2)
        self.assertEqual(outcome["missing_baseline"], 1)
        self.assertEqual(outcome["missing_delta"], 0)
        self.assertEqual(outcome["sample_missing_ids"], [1])
        self.assertEqual(outcome["sample_corrupt_ids"], [2])


class TestCrashOrder(unittest.TestCase):
    def test_default_has_no_probes_between_delta_ack_and_kill(self):
        events = []
        state = {"saved": False}
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)

            def cfg(mode, run_dir, config_dir):
                home = run_dir / mode
                (home / "data").mkdir(parents=True)
                return home / "fake.conf", home / "fake.pid"

            def fake_redis(port, command, *args):
                events.append(f"REDIS_{command}")
                if command == "DBSIZE":
                    return 10  # baseline
                if command == "BGSAVE":
                    (
                        next(root.iterdir()) / "rdb" / "data" / "dump.rdb"
                    ).write_bytes(b"snapshot")
                    state["saved"] = True
                    return True
                raise AssertionError(f"unexpected {command}")

            def fake_info(port, section):
                events.append("INFO")
                return {
                    "rdb_saves": 1 if state["saved"] else 0,
                    "rdb_bgsave_in_progress": 0,
                    "rdb_last_bgsave_status": "ok",
                }

            def fake_collect_info(port):
                events.append("SAVE_INFO")
                return {
                    "persistence": {
                        "rdb_last_bgsave_status": "ok",
                        "aof_last_write_status": "ok",
                    }
                }

            def fake_write_both(start, end, modes):
                if start == 10:
                    events.append("ACK_DELTA")
                else:
                    events.append("ACK_BASELINE")
                now = rt.time.monotonic_ns()
                return {
                    m: {"epoch": 1.0, "mono_ns": now} for m in instance.MODES
                }

            def fake_kill(mode, process):
                events.append("KILL_" + mode.upper())
                return {"epoch": 2.0, "mono_ns": rt.time.monotonic_ns()}

            processes = {
                mode: {"pid": 123 + n, "start_ticks": "0", "pidfd": None}
                for n, mode in enumerate(instance.MODES)
            }
            with (
                patch.object(rt, "BASE", root),
                patch.object(instance, "render_config", side_effect=cfg),
                patch.object(instance, "start_instance", return_value=5.0),
                patch.object(instance, "verify_persistence_config"),
                patch.object(
                    client, "write_both", side_effect=fake_write_both
                ),
                patch.object(client, "redis", side_effect=fake_redis),
                patch.object(client, "get_info", side_effect=fake_info),
                patch.object(
                    client, "collect_info", side_effect=fake_collect_info
                ),
                patch.object(
                    instance, "open_verified_pidfds", return_value=processes
                ),
                patch.object(
                    instance, "kill_verified_process", side_effect=fake_kill
                ),
                patch.object(instance, "wait_dead"),
                patch.object(artifacts, "folder_bytes", return_value=1),
                patch.object(instance, "check_pid", return_value=900),
                patch.object(instance, "stop_owned_instance"),
                patch.object(client, "verify_range", return_value={
                    "dbsize": 20, "verified_correct": 20, "missing_keys": 0,
                    "corrupt_keys": 0, "not_recovered_keys": 0,
                    "missing_baseline": 0, "missing_delta": 0,
                    "sample_missing_ids": [], "sample_corrupt_ids": [],
                }),
            ):
                with redirect_stdout(StringIO()):
                    rt.run_trial(
                        1, baseline=10, delta=10, delay=0, run_root=root
                    )
            index = events.index("ACK_DELTA")
            self.assertEqual(
                events[index:index + 3], ["ACK_DELTA", "KILL_AOF", "KILL_RDB"]
            )
            # Baseline only; no DBSIZE probe after delta.
            self.assertEqual(events.count("REDIS_DBSIZE"), 2)


class TestRunStorage(unittest.TestCase):
    def test_compact_csv_keeps_values_in_seconds(self):
        row = {
            "trial": 1, "mode": "rdb", "delay_seconds": 0,
            "expected_dbsize_before": 3000, "verified_correct_after": 2000,
            "missing_keys": 1000, "corrupt_keys": 0,
            "ack_to_kill_seconds": 0.014618,
            "pid_before": 100, "startup_ms": 67.84,
        }
        with tempfile.TemporaryDirectory() as td:
            output = artifacts.write_summary([row], Path(td))
            with output.open(encoding="utf-8", newline="") as stream:
                reader = csv.DictReader(stream)
                self.assertEqual(reader.fieldnames, [
                    "trial", "mode", "delay_seconds", "expected_dbsize_before",
                    "verified_correct_after", "missing_keys", "corrupt_keys",
                    "ack_to_kill_seconds",
                ])
                saved = next(reader)
            self.assertEqual(float(saved["ack_to_kill_seconds"]), 0.014618)
            self.assertEqual(saved["verified_correct_after"], "2000")
            self.assertNotIn("pid_before", saved)

    def test_short_terminal_labels_preserve_full_json(self):
        row = {
            "trial": 1, "mode": "rdb", "delay_seconds": 0,
            "expected_dbsize_before": 3000, "verified_correct_after": 2000,
            "missing_keys": 1000, "corrupt_keys": 0,
            "ack_to_kill_seconds": 0.014618,
            "pid_before": 100, "pid_after": 200, "startup_ms": 67.84,
            "missing_baseline": 0, "missing_delta": 1000,
            "sample_missing_ids": [2000, 2001],
        }
        console = StringIO()
        with tempfile.TemporaryDirectory() as td, redirect_stdout(console):
            artifacts.save_trial_results(Path(td), 1, [row])
            saved = json.loads(
                (Path(td) / "trial-results.json").read_text(encoding="utf-8")
            )
        self.assertEqual(saved, [row])
        lines = console.getvalue().splitlines()
        self.assertIn("Trial 1: recovery results", lines)
        table_lines = [line for line in lines if " | " in line]
        self.assertEqual(
            [cell.strip() for cell in table_lines[0].split("|")],
            [
                "Mode", "Delay(s)", "Expected", "Correct", "Missing",
                "Corrupt", "ACK(ms)",
            ],
        )
        self.assertEqual(
            [cell.strip() for cell in table_lines[1].split("|")],
            ["RDB", "0", "3000", "2000", "1000", "0", "14.618"],
        )
        self.assertNotIn("PID=", console.getvalue())
        self.assertNotIn("restart=", console.getvalue())

    def test_each_invocation_has_its_own_summary_even_in_same_second(self):
        with (
            tempfile.TemporaryDirectory() as td,
            patch.object(
                artifacts.time, "strftime", return_value="20261021-000000Z"
            ),
        ):
            first = artifacts.create_run_dir(Path(td))
            first_csv = artifacts.write_summary(
                [{"trial": 1, "mode": "rdb"}], first
            )
            original = first_csv.read_bytes()
            second = artifacts.create_run_dir(Path(td))
            second_csv = artifacts.write_summary(
                [{"trial": 1, "mode": "aof"}], second
            )
            self.assertNotEqual(first, second)
            self.assertEqual(first_csv.read_bytes(), original)
            self.assertNotEqual(first_csv, second_csv)
            self.assertEqual(first.parent, Path(td) / "results")
            self.assertFalse((Path(td) / "results" / "summary.csv").exists())
            with second_csv.open(encoding="utf-8", newline="") as stream:
                self.assertEqual(
                    list(csv.DictReader(stream))[0]["mode"], "aof"
                )
            artifacts.write_summary([], second)
            self.assertEqual(first_csv.read_bytes(), original)

    def test_failed_later_trial_preserves_completed_summary(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            with (
                patch.object(
                    rt.sys, "argv", ["run_trials.py", "--trials", "2"]
                ),
                patch.object(rt.sys, "platform", "linux"),
                patch.object(rt.Path, "exists", return_value=True),
                patch.object(
                    rt.shutil, "which", return_value="/usr/bin/redis-server"
                ),
                patch.object(
                    rt.subprocess, "run", return_value=type(
                        "Version", (), {"stdout": "Redis server v=7.0.0"}
                    )()
                ),
                patch.object(instance, "port_available", return_value=True),
                patch.object(artifacts, "create_run_dir", return_value=root),
                patch.object(rt, "run_trial", side_effect=[
                    [{"trial": 1, "mode": "rdb"}, {"trial": 1, "mode": "aof"}],
                    RuntimeError("second trial failed"),
                ]),
                redirect_stdout(StringIO()),
            ):
                with self.assertRaisesRegex(
                    RuntimeError, "second trial failed"
                ):
                    rt.main()
            with (root / "summary.csv").open(
                encoding="utf-8", newline=""
            ) as stream:
                rows = list(csv.DictReader(stream))
            self.assertEqual([row["mode"] for row in rows], ["rdb", "aof"])


if __name__ == "__main__":
    unittest.main()
