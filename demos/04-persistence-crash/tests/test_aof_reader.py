"""Test local AOF parsing without redis-py or a Redis server."""

import sys
import unittest
from io import BytesIO
from pathlib import Path

# Tests need sibling scripts on sys.path before the local imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import aof_reader


class TestAofReader(unittest.TestCase):
    def test_read_consecutive_commands(self):
        stream = BytesIO(
            b"*2\r\n$6\r\nSELECT\r\n$1\r\n0\r\n"
            b"*3\r\n$3\r\nSET\r\n$1\r\nk\r\n$1\r\nv\r\n"
        )
        self.assertEqual(aof_reader.read_command(stream), [b"SELECT", b"0"])
        self.assertEqual(aof_reader.read_command(stream), [b"SET", b"k", b"v"])
        self.assertEqual(stream.read(), b"")

    def test_empty_and_binary_bulk_strings(self):
        stream = BytesIO(b"*3\r\n$3\r\nSET\r\n$0\r\n\r\n$3\r\n\x00\xffx\r\n")
        self.assertEqual(
            aof_reader.read_command(stream), [b"SET", b"", b"\x00\xffx"]
        )

    def test_reject_malformed_or_unsupported_commands(self):
        for payload in (
            b"", b"+OK\r\n", b"*0\r\n", b"*-1\r\n", b"*x\r\n",
            b"*1\n$1\r\nx\r\n", b"*1\r\n$-1\r\n", b"*1\r\n:2\r\n",
            b"*1\r\n$2\r\nx", b"*1\r\n$1\r\nxZZ",
        ):
            with self.subTest(payload=payload), self.assertRaises(ValueError):
                aof_reader.read_command(BytesIO(payload))


if __name__ == "__main__":
    unittest.main()
