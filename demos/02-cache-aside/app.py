"""Run the browser demo with `python app.py`, or the original sequence with --cli."""
import argparse
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
import time

import redis

TTL = 5
CASES = {
    "without": "Without Cache",
    "with": "With Cache",
    "expiration": "After TTL Expiration",
    "invalidation": "After Cache Invalidation",
}
DEMO_KEY = "demo:user:1"
DEFAULTS = dict(ttl=TTL, delay_ms=300,
                without_count=5, with_count=10, expiration_count=3,
                invalidation_count=3)


def validate_settings(values):
    if not isinstance(values, dict):
        raise ValueError("Settings must be a JSON object.")
    settings = {name: values.get(name, default) for name, default in DEFAULTS.items()}
    for name, low, high in [("ttl", 1, 60), ("delay_ms", 0, 2000)] + [
        (f"{case}_count", 1, 100) for case in CASES
    ]:
        value = settings[name]
        if type(value) is not int or not low <= value <= high:
            raise ValueError(f"{name} must be an integer from {low} to {high}.")
    return settings


def query_database(key, delay_ms=300):
    time.sleep(delay_ms / 1000)
    return f"Data for {key}"


def get_data(client, key, use_cache=True, ttl=TTL, delay_ms=300):
    start = time.perf_counter()
    if use_cache and client.get(key) is not None:
        return "HIT", (time.perf_counter() - start) * 1000
    data = query_database(key, delay_ms)
    if use_cache:
        client.setex(key, ttl, data)
    return ("MISS" if use_cache else "NO CACHE"), (time.perf_counter() - start) * 1000


def run_demo(client, settings, emit):
    """Emit progress and measurements; preparation is excluded from averages."""
    key, ttl = DEMO_KEY, settings["ttl"]
    for case in CASES:
        emit(dict(type="start", case=case, title=CASES[case]))
        if case == "with":
            client.delete(key)
            emit(dict(type="note", message=f"Deleted {key}; the first request starts cold."))
        elif case in ("expiration", "invalidation"):
            # Seed a fresh value to demonstrate each cache lifecycle event.
            client.setex(key, ttl, f"Data for {key}")
            emit(dict(type="note", message=f"Seeded {key} with a {ttl}s TTL (not measured)."))
            if case == "expiration":
                for remaining in range(ttl, 0, -1):
                    emit(dict(type="note", message=f"Waiting for expiration: {remaining}s remaining…"))
                    time.sleep(1)
                # Account for Redis TTL resolution before sending measured requests.
                while client.exists(key):
                    time.sleep(0.01)
                emit(dict(type="note", message="Key expired; the next request must fetch from the database."))
            else:
                client.delete(key)
                emit(dict(type="note", message="Explicitly deleted the cached key; the next request will miss."))
        elapsed_times, hits = [], 0
        for index in range(settings[f"{case}_count"]):
            status, elapsed = get_data(client, key, case != "without", ttl, settings["delay_ms"])
            elapsed_times.append(elapsed)
            hits += status == "HIT"
            emit(dict(type="request", case=case, number=index + 1, status=status, elapsed_ms=elapsed))
        emit(dict(type="summary", case=case, average_ms=sum(elapsed_times) / len(elapsed_times),
                  hits=hits, count=len(elapsed_times)))
    emit(dict(type="done"))


def make_handler(client):
    run_lock = threading.Lock()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path not in ("/", "/index.html"):
                self.send_error(404)
                return
            content = Path(__file__).with_name("index.html").read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_POST(self):
            if self.path != "/api/run":
                self.send_error(404)
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Invalid request size.")
                settings = validate_settings(json.loads(self.rfile.read(length)))
            except (ValueError, TypeError):
                self.send_error(400, "Invalid settings. Check TTL, delay and request counts.")
                return
            if not run_lock.acquire(blocking=False):
                self.send_error(409, "A demo is already running. Wait for it to finish.")
                return
            try:
                self.send_response(200)
                self.send_header("Content-Type", "application/x-ndjson")
                self.send_header("Cache-Control", "no-store")
                self.end_headers()

                def emit(event):
                    self.wfile.write((json.dumps(event) + "\n").encode())
                    self.wfile.flush()

                try:
                    run_demo(client, settings, emit)
                except redis.RedisError:
                    emit(dict(type="error", message="Redis is unavailable. Check that the demo Redis instance is running and the host/port are correct."))
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                run_lock.release()

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cli", action="store_true", help="Run the four cases in the terminal")
    parser.add_argument("--host", default="127.0.0.1", help="UI bind address")
    parser.add_argument("--port", type=int, default=8000, help="UI port")
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6384)
    args = parser.parse_args()
    client = redis.Redis(host=args.redis_host, port=args.redis_port, decode_responses=True,
                         socket_connect_timeout=3, socket_timeout=3)
    if args.cli:
        def print_event(event):
            if event["type"] == "start":
                print(f'\n=== {event["title"]} ===')
            elif event["type"] == "request":
                print(f'Request {event["number"]:3} | {event["status"]:8} | {event["elapsed_ms"]:8.2f} ms')
            elif event["type"] == "summary":
                print(f'Average response time: {event["average_ms"]:.2f} ms')
            elif event["type"] == "note":
                print(event["message"])
        run_demo(client, DEFAULTS, print_event)
    else:
        server = ThreadingHTTPServer((args.host, args.port), make_handler(client))
        print(f"Cache-aside demo: http://{args.host}:{args.port}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()


if __name__ == "__main__":
    main()
