"""Use redis-py for concurrent writes and key/value checks."""

import concurrent.futures
import time

import redis as redis_py
from redis.backoff import NoBackoff
from redis.retry import Retry

import constants as settings

RedisError = redis_py.exceptions.RedisError
REDIS_PY_VERSION = redis_py.__version__


def create_client(port, timeout=settings.COMMAND_TIMEOUT_SECONDS):
    # Keep protocol/retry behavior stable for the experiment.
    return redis_py.Redis(
        host=settings.REDIS_HOST, port=port, db=settings.REDIS_DATABASE,
        protocol=settings.RESP_VERSION, decode_responses=False,
        socket_connect_timeout=settings.CONNECT_TIMEOUT_SECONDS,
        socket_timeout=timeout,
        retry=Retry(NoBackoff(), settings.AUTOMATIC_RETRIES),
        retry_on_timeout=False, retry_on_error=[],
        health_check_interval=settings.HEALTH_CHECK_INTERVAL_SECONDS,
        lib_name=None, lib_version=None,
    )


def redis(port, *args):
    with create_client(port) as connection:
        return connection.execute_command(*args)


def redis_ping(port):
    try:
        return redis(port, "PING") is True
    except (OSError, RedisError, TimeoutError):
        return False


def get_info(port, section):
    with create_client(port) as connection:
        return connection.info(section)


def collect_info(port):
    """Collect native redis-py types without file I/O."""
    return {
        section: get_info(port, section)
        for section in ("server", "persistence", "keyspace")
    }


def get_config(port, key):
    with create_client(port) as connection:
        return connection.config_get(key)[key]


def write_range(port, begin, end):
    """Timestamp bounded batches only after EVERY SET succeeds."""
    with create_client(
        port, timeout=settings.WORKLOAD_TIMEOUT_SECONDS
    ) as connection:
        for base in range(begin, end, settings.PIPELINE_BATCH_SIZE):
            upper = min(base + settings.PIPELINE_BATCH_SIZE, end)
            with connection.pipeline(transaction=False) as pipe:
                for i in range(base, upper):
                    pipe.set(
                        f"demo:{i:0{settings.KEY_INDEX_WIDTH}d}",
                        f"value:{i:0{settings.KEY_INDEX_WIDTH}d}",
                    )
                replies = pipe.execute()
            if len(replies) != upper - base or any(
                reply is not True for reply in replies
            ):
                raise RedisError(f"Not all SETs succeeded on port {port}")
    mono_ns = time.monotonic_ns()
    return {"epoch": time.time(), "mono_ns": mono_ns}


def write_both(start, end, modes):
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(modes)) as pool:
        futures = {
            name: pool.submit(write_range, port, start, end)
            for name, port in modes.items()
        }
        return {name: f.result() for name, f in futures.items()}


def verify_range(port, count, baseline):
    good = missing = corrupt = 0
    missing_baseline = missing_delta = 0
    sample_missing = []
    sample_corrupt = []

    with create_client(
        port, timeout=settings.WORKLOAD_TIMEOUT_SECONDS
    ) as connection:
        for start in range(0, count, settings.MGET_BATCH_SIZE):
            indices = range(
                start, min(start + settings.MGET_BATCH_SIZE, count)
            )
            values = connection.mget(
                [f"demo:{i:0{settings.KEY_INDEX_WIDTH}d}" for i in indices]
            )
            if not isinstance(values, list) or len(values) != len(indices):
                raise RedisError("MGET verification failed")
            for i, value in zip(indices, values):
                expected = f"value:{i:0{settings.KEY_INDEX_WIDTH}d}".encode()
                if value == expected:
                    good += 1
                elif value is None:
                    missing += 1
                    missing_baseline += int(i < baseline)
                    missing_delta += int(i >= baseline)
                    if len(sample_missing) < settings.KEY_SAMPLE_LIMIT:
                        sample_missing.append(i)
                else:
                    corrupt += 1
                    if len(sample_corrupt) < settings.KEY_SAMPLE_LIMIT:
                        sample_corrupt.append(i)
        dbsize = connection.dbsize()

    return {
        "dbsize": dbsize,
        "verified_correct": good,
        "missing_keys": missing,
        "corrupt_keys": corrupt,
        "not_recovered_keys": missing + corrupt,
        "missing_baseline": missing_baseline,
        "missing_delta": missing_delta,
        "sample_missing_ids": sample_missing,
        "sample_corrupt_ids": sample_corrupt,
    }
