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
mkdir -p /tmp/redis-seminar/eviction
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

### Bước 3: Khởi tạo các Cold Keys (ít dùng, tạo trước tiên)
```bash
redis-cli -p 6382 set cold_k1 "ColdData_1"

redis-cli -p 6382 set cold_k2 "ColdData_2"

redis-cli -p 6382 set cold_k3 "ColdData_3"

```
- Kỳ vọng: `OK` (các key này nằm lại từ đầu, sẽ là đối tượng cũ nhất trong LRU).

### Bước 4: Nạp dữ liệu nền gần đầy RAM (~8.5MB)
```bash
redis-benchmark -p 6382 -c 1 -t set -n 85 -d 100000 -r 10000 -q
```
- Kỳ vọng: Nạp 85 keys x 100KB, RAM tăng lên ~9.4MB, chưa kích hoạt eviction.

### Bước 5: Khởi tạo và truy cập Hot Keys (dữ liệu nóng mới nhất)
```bash
redis-cli -p 6382 set hot_k1 "HotData_1"
redis-cli -p 6382 set hot_k2 "HotData_2"
redis-cli -p 6382 get hot_k1
redis-cli -p 6382 get hot_k2
```
- Kỳ vọng: `"HotData_1"`, `"HotData_2"` (Hot Keys được làm mới, có độ ưu tiên cao nhất).

### Bước 6: Bơm thêm dữ liệu kích hoạt tràn 10MB RAM
```bash
redis-benchmark -p 6382 -c 1 -t set -n 20 -d 100000 -r 10000 -q
```
- Kỳ vọng: Nạp thêm 20 keys x 100KB, RAM vượt 10MB, kích hoạt trục xuất ~8-12 keys cũ nhất.

### Bước 7: Kiểm tra RAM và đối chứng kết quả LRU
```bash
redis-cli -p 6382 info memory | grep used_memory_human
redis-cli -p 6382 info stats | grep evicted_keys
redis-cli -p 6382 exists cold_k1 cold_k2 cold_k3
redis-cli -p 6382 exists hot_k1 hot_k2
```
- Kỳ vọng:
  - `used_memory_human`: `~9.8M - 9.9M` (chạm trần an toàn).
  - `evicted_keys`: `> 0` (khoảng 5 - 10 keys).
  - `cold_k1 cold_k2 cold_k3`: `(integer) 0` (đã bị loại bỏ vì cũ nhất).
  - `hot_k1 hot_k2`: `(integer) 2` (được bảo toàn 100%).

---

## 3. Khôi phục Trạng thái (Reset) & Xử lý Sự cố

### Dọn sạch dữ liệu đưa về 0 để chạy lại:
```bash
redis-cli -p 6382 flushall
redis-cli -p 6382 config resetstat
```
Hoặc dùng script reset trọn gói:
```bash
bash demos/03-eviction/reset.sh
```

### Khởi động lại instance (khi đã tắt hoặc bị kill):
```bash
mkdir -p /tmp/redis-seminar/eviction
redis-server redis/redis-eviction.conf &
redis-cli -p 6382 ping
```

### Giải phóng port và tắt instance:
```bash
sudo fuser -k 6382/tcp
redis-cli -p 6382 shutdown
```
