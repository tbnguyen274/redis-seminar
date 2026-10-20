# Quy Trình Kiểm Thử & Quay Demo Từng Lệnh (Port 6382)

Tài liệu hướng dẫn thực thi tuần tự từng lệnh qua `redis-cli` phục vụ kiểm thử và quay video demo cho cơ chế Eviction (`allkeys-lru`).

> **Lưu ý:** Thực thi các lệnh dưới đây từ thư mục gốc của repository (`redis-seminar/`).

---

## 1. Kiểm thử Tự động Nhanh

```bash
bash test/test_demo_03.sh
bash demos/03-eviction/run.sh
```

---

## 2. Kịch Bản Gõ Từng Lệnh Khi Quay Video Demo (90 - 120 giây)

### Bước 1: Khởi động instance và kiểm tra cấu hình ban đầu
```bash
redis-server redis/redis-eviction.conf &
redis-cli -p 6382 ping
redis-cli -p 6382 config get maxmemory
redis-cli -p 6382 config get maxmemory-policy
```
- Kỳ vọng: `PONG`, `10485760` (~10MB), `allkeys-lru`.

### Bước 2: Dọn sạch database và ghi nhận trạng thái rỗng
```bash
redis-cli -p 6382 flushall
redis-cli -p 6382 config resetstat
redis-cli -p 6382 info memory | grep used_memory_human
redis-cli -p 6382 dbsize
```
- Kỳ vọng: `OK`, RAM rỗng `~850K - 1M`, `(integer) 0`.

### Bước 3: Khởi tạo tập key đối chứng
```bash
redis-cli -p 6382 set cold_k1 "ColdData_1"
redis-cli -p 6382 set cold_k2 "ColdData_2"
redis-cli -p 6382 set cold_k3 "ColdData_3"
redis-cli -p 6382 set hot_k1 "HotData_1"
redis-cli -p 6382 set hot_k2 "HotData_2"
redis-cli -p 6382 dbsize
```
- Kỳ vọng: `(integer) 5`.

### Bước 4: Bơm dữ liệu lớn làm tràn 10MB RAM
```bash
redis-benchmark -p 6382 -t set -n 120 -d 100000 -r 100000 -q
```

### Bước 5: Truy cập Hot Keys để cập nhật LRU clock
```bash
redis-cli -p 6382 get hot_k1
redis-cli -p 6382 get hot_k2
```
- Kỳ vọng: `"HotData_1"`, `"HotData_2"`.

### Bước 6: Kiểm tra biến thiên RAM và cơ chế Eviction
```bash
redis-cli -p 6382 info memory | grep used_memory_human
redis-cli -p 6382 info stats | grep evicted_keys
```
- Kỳ vọng: `used_memory_human: ~9.8M - 10M`, `evicted_keys > 0`.

### Bước 7: Đối chứng kết quả xóa key theo LRU
```bash
redis-cli -p 6382 exists cold_k1 cold_k2 cold_k3
redis-cli -p 6382 exists hot_k1 hot_k2
```
- Kỳ vọng:
  - `cold_k1 cold_k2 cold_k3`: `(integer) 0` (đã bị loại bỏ).
  - `hot_k1 hot_k2`: `(integer) 2` (được bảo toàn).

---

## 3. Khôi phục Trạng thái (Reset) & Xử lý Sự cố

```bash
bash demos/03-eviction/reset.sh
sudo fuser -k 6382/tcp
redis-cli -p 6382 shutdown
```
