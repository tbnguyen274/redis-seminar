"""Check native replies, retries, batching and final ACK timing."""

import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, call, patch

# Tests need sibling scripts on sys.path before the local imports.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import redis_client as client


class TestRedisPyClient(unittest.TestCase):
    def setUp(self):
        self.connection = MagicMock()
        self.connection.__enter__.return_value = self.connection
        self.pipe = (
            self.connection.pipeline.return_value.__enter__.return_value
        )

    def test_explicit_connection_and_retry_settings(self):
        with client.create_client(6380, timeout=30) as connection:
            options = connection.connection_pool.connection_kwargs
            self.assertEqual(options["host"], "127.0.0.1")
            self.assertEqual(options["port"], 6380)
            self.assertEqual(options["protocol"], 2)
            self.assertFalse(options["decode_responses"])
            self.assertEqual(options["socket_timeout"], 30)
            self.assertEqual(options["socket_connect_timeout"], 4)
            self.assertEqual(options["health_check_interval"], 0)
            self.assertIsNone(options["lib_name"])
            attempt = MagicMock(
                side_effect=client.redis_py.exceptions.ConnectionError
            )
            with self.assertRaises(client.RedisError):
                options["retry"].call_with_retry(attempt, lambda error: None)
            attempt.assert_called_once()

    def test_real_library_callbacks_return_native_types(self):
        with client.create_client(6380) as connection:
            callbacks = connection.response_callbacks
            self.assertIs(callbacks["PING"](b"PONG"), True)
            self.assertIs(
                callbacks["BGSAVE"](b"Background saving started"), True
            )
            self.assertEqual(
                callbacks["INFO"](
                    b"rdb_bgsave_in_progress:0\r\nrdb_saves:1\r\n"
                ),
                {"rdb_bgsave_in_progress": 0, "rdb_saves": 1},
            )
            self.assertEqual(
                callbacks["CONFIG GET"]([b"save", b""]), {"save": ""}
            )

    def test_command_info_and_config_adapters(self):
        self.connection.execute_command.return_value = True
        self.connection.info.return_value = {"rdb_saves": 1}
        self.connection.config_get.return_value = {"save": ""}
        with patch.object(
            client, "create_client", return_value=self.connection
        ):
            self.assertTrue(client.redis_ping(6380))
            self.assertEqual(
                client.get_info(6380, "persistence"), {"rdb_saves": 1}
            )
            self.assertEqual(client.get_config(6380, "save"), "")
        self.connection.execute_command.assert_called_once_with("PING")
        self.connection.info.assert_called_once_with("persistence")
        self.connection.config_get.assert_called_once_with("save")

    def test_ping_handles_redis_connection_error(self):
        self.connection.execute_command.side_effect = (
            client.redis_py.exceptions.ConnectionError
        )
        with patch.object(
            client, "create_client", return_value=self.connection
        ):
            self.assertFalse(client.redis_ping(6380))

    def test_pipeline_batches_and_timestamps_after_last_ack(self):
        events = []
        replies = iter(([True] * 250, [True] * 250, [True]))

        def execute():
            events.append("ACK")
            return next(replies)

        def timestamp():
            events.append("TIME")
            return 123

        self.pipe.execute.side_effect = execute
        with (
            patch.object(
                client, "create_client", return_value=self.connection
            ),
            patch.object(client.time, "monotonic_ns", side_effect=timestamp),
            patch.object(client.time, "time", return_value=4.5),
        ):
            self.assertEqual(
                client.write_range(6380, 0, 501),
                {"mono_ns": 123, "epoch": 4.5},
            )
        self.assertEqual(events, ["ACK", "ACK", "ACK", "TIME"])
        self.assertEqual(
            self.connection.pipeline.call_args_list,
            [call(transaction=False)] * 3,
        )
        self.assertEqual(self.pipe.set.call_count, 501)
        self.assertEqual(
            self.pipe.set.call_args_list[0],
            call("demo:00000000", "value:00000000"),
        )
        self.assertEqual(
            self.pipe.set.call_args_list[-1],
            call("demo:00000500", "value:00000500"),
        )

    def test_failed_or_incomplete_batch_has_no_ack_timestamp(self):
        for replies in ([True, False], [True], [], [True, 1]):
            with self.subTest(replies=replies):
                self.pipe.execute.side_effect = None
                self.pipe.execute.return_value = replies
                with (
                    patch.object(
                        client, "create_client", return_value=self.connection
                    ),
                    patch.object(client.time, "monotonic_ns") as timestamp,
                ):
                    with self.assertRaises(client.RedisError):
                        client.write_range(6380, 0, 2)
                    timestamp.assert_not_called()

    def test_pipeline_batch_size_uses_constant(self):
        self.pipe.execute.side_effect = [[True, True], [True, True], [True]]
        with (
            patch.object(client.settings, "PIPELINE_BATCH_SIZE", 2),
            patch.object(
                client, "create_client", return_value=self.connection
            ),
        ):
            client.write_range(6380, 0, 5)
        self.assertEqual(self.pipe.execute.call_count, 3)
        self.assertEqual(self.pipe.set.call_count, 5)

    def test_key_width_uses_shared_constant(self):
        self.pipe.execute.return_value = [True]
        self.connection.mget.return_value = [b"value:000"]
        self.connection.dbsize.return_value = 1
        with (
            patch.object(client.settings, "KEY_INDEX_WIDTH", 3),
            patch.object(
                client, "create_client", return_value=self.connection
            ),
        ):
            client.write_range(6380, 0, 1)
            outcome = client.verify_range(6380, 1, baseline=1)
        self.pipe.set.assert_called_once_with("demo:000", "value:000")
        self.connection.mget.assert_called_once_with(["demo:000"])
        self.assertEqual(outcome["verified_correct"], 1)

    def test_mget_batch_and_sample_limit_use_constants(self):
        self.connection.mget.side_effect = [
            [None, None], [None, None], [b"wrong"]
        ]
        self.connection.dbsize.return_value = 1
        with (
            patch.object(client.settings, "MGET_BATCH_SIZE", 2),
            patch.object(client.settings, "KEY_SAMPLE_LIMIT", 2),
            patch.object(
                client, "create_client", return_value=self.connection
            ),
        ):
            outcome = client.verify_range(6380, 5, baseline=2)
        self.assertEqual(self.connection.mget.call_count, 3)
        self.assertEqual(outcome["missing_keys"], 4)
        self.assertEqual(outcome["sample_missing_ids"], [0, 1])
        self.assertEqual(outcome["sample_corrupt_ids"], [4])

    def test_writer_count_is_derived_from_modes(self):
        with patch.object(
            client.concurrent.futures, "ThreadPoolExecutor"
        ) as factory:
            pool = factory.return_value.__enter__.return_value
            pool.submit.return_value.result.return_value = {
                "mono_ns": 1, "epoch": 2
            }
            outcome = client.write_both(0, 1, {"rdb": 6380})
        factory.assert_called_once_with(max_workers=1)
        self.assertEqual(outcome, {"rdb": {"mono_ns": 1, "epoch": 2}})

    def test_pipeline_exception_is_not_converted_to_success(self):
        self.pipe.execute.side_effect = (
            client.redis_py.exceptions.ResponseError("write failed")
        )
        with (
            patch.object(
                client, "create_client", return_value=self.connection
            ),
            patch.object(client.time, "monotonic_ns") as timestamp,
        ):
            with self.assertRaises(client.RedisError):
                client.write_range(6380, 0, 2)
            timestamp.assert_not_called()

    def test_mget_batches_use_bytes_and_native_dbsize(self):
        self.connection.mget.side_effect = [
            [f"value:{i:08d}".encode() for i in range(200)], [None]]
        self.connection.dbsize.return_value = 200
        with patch.object(
            client, "create_client", return_value=self.connection
        ):
            result = client.verify_range(6380, 201, baseline=200)
        self.assertEqual(result["verified_correct"], 200)
        self.assertEqual(result["missing_baseline"], 0)
        self.assertEqual(result["missing_delta"], 1)
        self.assertEqual(result["dbsize"], 200)
        self.assertEqual(
            self.connection.mget.call_args_list[-1], call(["demo:00000200"])
        )

    def test_mget_invalid_reply_is_rejected(self):
        for reply in (None, [None], b"unexpected"):
            with self.subTest(reply=reply):
                self.connection.mget.side_effect = None
                self.connection.mget.return_value = reply
                with patch.object(
                    client, "create_client", return_value=self.connection
                ):
                    with self.assertRaises(client.RedisError):
                        client.verify_range(6380, 2, baseline=1)


if __name__ == "__main__":
    unittest.main()
