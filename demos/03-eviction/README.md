# Demo 03: Eviction (allkeys-lru)

Thực nghiệm cơ chế giới hạn bộ nhớ (`maxmemory`) và chính sách trục xuất (`allkeys-lru`) trong Redis.

## Cấu hình

- **Port:** `6382`
- **Config:** `redis/redis-eviction.conf`
- **Data dir:** `/tmp/redis-seminar/eviction`
- **Maxmemory:** `10mb`
- **Policy:** `allkeys-lru`

## Cấu trúc thư mục

```text
demos/03-eviction/
├── requirements.txt   # Thư viện Python (redis)
├── reset.sh           # Reset dữ liệu port 6382
├── fill_memory.py     # Script chính: tạo cold/hot keys, bơm data và đối chứng
├── run.sh             # Script chạy tự động toàn bộ demo
├── test_eviction.py   # Script kiểm thử tự động
└── README.md
```

## Cách chạy

```bash
# 1. Khởi động instance
mkdir -p /tmp/redis-seminar/eviction
redis-server redis/redis-eviction.conf &

# 2. Cài đặt thư viện
pip install -r demos/03-eviction/requirements.txt

# 3. Chạy demo
python3 demos/03-eviction/fill_memory.py
# hoặc chạy trọn gói:
bash demos/03-eviction/run.sh

# 4. Reset sau khi chạy
bash demos/03-eviction/reset.sh
```

## Kết quả mong đợi

- `used_memory_human`: dừng ở mức ~9.8MB - 10MB (không vượt 10MB).
- `evicted_keys`: tăng dần (> 0).
- Cold keys (`cold_user_*`): bị trục xuất (`EXISTS = 0`).
- Hot keys (`hot_user_*`): được giữ lại (`EXISTS = 1`).
