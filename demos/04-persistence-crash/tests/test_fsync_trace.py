"""Test fsync evidence independently of successful recovery."""

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

# Tests need sibling scripts on sys.path before the local imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import fsync_trace as ft
import results as artifacts


class TestFsyncEvidence(unittest.TestCase):
    def analyze(
        self, sync_line, *, write_time="10.100000", byte_adjust=0,
        expected_keys=2, clock_consistent=True,
    ):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            data = root / "data" / "appendonlydir"
            data.mkdir(parents=True)
            aof = data / "appendonly.aof.1.incr.aof"
            payload = b"".join(
                (f"*3\r\n$3\r\nSET\r\n$13\r\ndemo:{i:08d}\r\n"
                 f"$14\r\nvalue:{i:08d}\r\n").encode()
                for i in range(2))
            aof.write_bytes(payload)
            trace = root / "trace"
            trace.mkdir()
            write = (f'{write_time} write(8<{aof}>, ""..., {len(payload)}) = '
                     f'{len(payload)+byte_adjust} <0.001000>\n')
            # Another thread syncs; both descriptor and path matter.
            (trace / "aof.1").write_text(write, encoding="utf-8")
            (trace / "aof.2").write_text(
                sync_line.format(file=aof), encoding="utf-8"
            )
            return ft.analyze(
                trace, root / "data", expected_keys, 10.5, clock_consistent
            )

    def test_sync_after_complete_delta_before_kill(self):
        result = self.analyze(
            '10.200000 fdatasync(8<{file}>) = 0 <0.002000>\n'
        )
        self.assertEqual(result["status"], "Confirmed")
        self.assertAlmostEqual(result["confirmed_sync"]["end"], 10.202)

    def test_sync_before_delta_does_not_confirm(self):
        result = self.analyze('10.000000 fsync(8<{file}>) = 0 <0.002000>\n')
        self.assertEqual(result["status"], "Not confirmed")

    def test_no_sync_does_not_confirm_even_when_file_is_complete(self):
        self.assertEqual(self.analyze("")["status"], "Not confirmed")

    def test_sync_finishes_after_kill(self):
        result = self.analyze('10.400000 fsync(8<{file}>) = 0 <0.200000>\n')
        self.assertEqual(result["status"], "Not confirmed")

    def test_overlapping_sync_does_not_confirm(self):
        result = self.analyze('10.050000 fsync(8<{file}>) = 0 <0.200000>\n')
        self.assertEqual(result["status"], "Not confirmed")

    def test_wrong_file_does_not_confirm(self):
        result = self.analyze(
            '10.200000 fsync(9</elsewhere/redis.log>) = 0 <0.002000>\n'
        )
        self.assertEqual(result["status"], "Not confirmed")

    def test_missing_write_evidence_is_unknown(self):
        result = self.analyze(
            '10.200000 fsync(8<{file}>) = 0 <0.002000>\n', byte_adjust=-1
        )
        self.assertEqual(result["status"], "Unknown")

    def test_incomplete_delta_is_unknown(self):
        result = self.analyze(
            '10.200000 fsync(8<{file}>) = 0 <0.002000>\n', expected_keys=3
        )
        self.assertEqual(result["status"], "Unknown")

    def test_unfinished_sync_is_unknown(self):
        result = self.analyze('10.200000 fsync(8<{file}> <unfinished ...>\n')
        self.assertEqual(result["status"], "Unknown")

    def test_failed_sync_is_not_a_confirmation(self):
        result = self.analyze(
            '10.200000 fsync(8<{file}>) = -1 '
            'EIO (Input/output error) <0.002000>\n'
        )
        self.assertNotEqual(result["status"], "Confirmed")

    def test_clock_jump_is_unknown(self):
        result = self.analyze(
            '10.200000 fsync(8<{file}>) = 0 <0.002000>\n',
            clock_consistent=False,
        )
        self.assertEqual(result["status"], "Unknown")

    def test_sync_margin_uses_constant(self):
        with patch.object(ft.settings, "SYNC_TIMESTAMP_MARGIN_SECONDS", 0.15):
            result = self.analyze(
                '10.200000 fsync(8<{file}>) = 0 <0.002000>\n'
            )
        self.assertEqual(result["status"], "Not confirmed")

    def test_clock_tolerance_uses_constant(self):
        for tolerance, expected in ((0.01, False), (0.05, True)):
            with (
                self.subTest(tolerance=tolerance),
                tempfile.TemporaryDirectory() as td,
            ):
                with (
                    patch.object(ft.time, "time", return_value=100),
                    patch.object(ft.time, "monotonic", return_value=200),
                ):
                    tracer = ft.AofTrace(Path(td) / "trace")
                with (
                    patch.object(
                        ft.settings, "CLOCK_DRIFT_TOLERANCE_SECONDS", tolerance
                    ),
                    patch.object(ft.time, "time", return_value=101.02),
                    patch.object(ft.time, "monotonic", return_value=201),
                ):
                    tracer.mark_before_kill()
                self.assertIs(tracer.clock_consistent, expected)

    def test_csv_adds_status_only_for_traced_runs(self):
        with tempfile.TemporaryDirectory() as td:
            output = artifacts.write_summary([
                {
                    "mode": "rdb", "fsync_tracing": True,
                    "delta_fsync_status": "N/A",
                },
                {
                    "mode": "aof", "fsync_tracing": True,
                    "delta_fsync_status": "Confirmed",
                },
            ], Path(td))
            text = output.read_text(encoding="utf-8")
            self.assertEqual(len(text.splitlines()[0].split(",")), 9)
            self.assertTrue(
                text.splitlines()[0].endswith("delta_fsync_status")
            )
            self.assertTrue(text.splitlines()[2].endswith("Confirmed"))


if __name__ == "__main__":
    unittest.main()
