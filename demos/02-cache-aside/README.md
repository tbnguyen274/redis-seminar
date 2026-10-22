# Cache-aside demo

Start the isolated Redis instance from the repository root:

Khởi chạy redis server với cấu hình dùng cho cache-aside demo:

```bash
mkdir -p /tmp/redis-seminar/cache-aside
redis-server redis/redis-cache-aside.conf
```

Mở một terminal mới, cài đặt môi trường ảo và chạy demo:

```bash
cd demos/02-cache-aside
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 app.py
```

Open **http://127.0.0.1:8000**. Every experiment runs all four cases using the fixed Redis key `demo:user:1`. Configure the TTL (1–60 seconds), simulated database delay (0–2000 ms), and request counts (1–100 per case). Each run replaces the displayed results; request timings stream live. The event log explains cache preparation and the TTL countdown.

Mở **http://127.0.0.1:8000**. Mỗi lần chạy thử nghiệm sẽ thực hiện tất cả bốn trường hợp: không có cache, có cache, sau khi TTL hết hạn và sau khi xóa cache.

Có thể cấu hình TTL (1–60 giây), độ trễ của cơ sở dữ liệu mô phỏng (0–2000 ms) và số lượng yêu cầu (1–100 cho mỗi trường hợp).

| Case                     | Behavior                                                                           |
| ------------------------ | ---------------------------------------------------------------------------------- |
| Without cache            | Every request queries the simulated database; Redis is bypassed.                   |
| With cache               | Deletes the demo key first, then shows a MISS followed by HITs.                    |
| After TTL expiration     | Seeds the key, waits for its TTL to expire, then measures a MISS followed by HITs. |
| After cache invalidation | Seeds and explicitly deletes the key, then measures a MISS followed by HITs.       |
