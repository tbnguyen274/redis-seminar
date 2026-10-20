# Runbook: Demo 03 - Redis Eviction (allkeys-lru)

Tài liệu vận hành, kiểm thử và tái lập thực nghiệm cơ chế Eviction trên Redis instance port `6382`.

---

## 1. Thông số Instance

| Tham số | Giá trị |
|---|---|
| Port | `6382` |
| Config file | `redis/redis-eviction.conf` |
| Data directory | `/tmp/redis-seminar/eviction` |
| Memory limit | `maxmemory 10mb` (10485760 bytes) |
| Eviction policy | `maxmemory-policy allkeys-lru` |

> **Lưu ý:** Thực thi các lệnh dưới đây từ thư mục gốc của repository (`redis-seminar/`).

---

## 2. Quickstart

Khởi chạy toàn bộ quy trình demo (tự động bật instance, cài dependency, nạp dữ liệu và xuất kết quả):

```bash
bash demos/03-eviction/run.sh
```

---

## 3. Kiểm thử Tự động (Automated Verification)

Chạy bộ kiểm thử tự động gồm 9 assertions để xác thực cấu hình và hành vi hệ thống:

```bash
bash test/test_demo_03.sh
```

**Các hạng mục kiểm tra:**
- Trạng thái kết nối và phản hồi `PONG` trên port `6382`.
- Cấu hình `maxmemory` đúng 10MB và `maxmemory-policy` đúng `allkeys-lru`.
- Tạo 10 Cold Keys và 5 Hot Keys đối chứng.
- Kích hoạt thành công Eviction khi nạp dữ liệu vượt ngưỡng (`evicted_keys >= 15`).
- Xác nhận Cold Keys bị trục xuất (`EXISTS = 0`) và Hot Keys được bảo toàn (`EXISTS = 1`).
- Kiểm soát dung lượng RAM không vượt quá giới hạn.

---

## 4. Tái lập Thủ công qua CLI (Manual Reproduction)

### 4.1. Khởi động instance và kiểm tra cấu hình
```bash
mkdir -p /tmp/redis-seminar/eviction
redis-server redis/redis-eviction.conf &

redis-cli -p 6382 ping
redis-cli -p 6382 config get maxmemory
redis-cli -p 6382 config get maxmemory-policy
redis-cli -p 6382 flushall
```

### 4.2. Khởi tạo các Cold Keys (ít dùng)
```bash
redis-cli -p 6382 set cold_k1 "val1"
redis-cli -p 6382 set cold_k2 "val2"
redis-cli -p 6382 set cold_k3 "val3"
```

### 4.3. Khởi tạo và đọc làm mới Hot Keys
```bash
redis-cli -p 6382 set hot_k1 "val1"
redis-cli -p 6382 set hot_k2 "val2"
redis-cli -p 6382 get hot_k1
redis-cli -p 6382 get hot_k2
```

### 4.4. Nạp dữ liệu tràn bộ nhớ để kích hoạt Eviction
```bash
redis-benchmark -p 6382 -t set -n 120 -d 100000 -r 100000 -q
```

### 4.5. Kiểm tra kết quả đối chứng
```bash
redis-cli -p 6382 info memory | grep used_memory_human
redis-cli -p 6382 info stats | grep evicted_keys
redis-cli -p 6382 exists cold_k1 cold_k2 cold_k3
redis-cli -p 6382 exists hot_k1 hot_k2
```
- Kỳ vọng: `exists cold_*` trả về `0` (đã bị trục xuất), `exists hot_*` trả về `2` (được giữ lại).

---

## 5. Giám sát Real-time

Theo dõi dung lượng RAM và số lượng key bị trục xuất mỗi giây:

```bash
watch -n 1 "redis-cli -p 6382 info memory | grep used_memory_human; redis-cli -p 6382 info stats | grep evicted_keys"
```

---

## 6. Dọn dẹp & Khắc phục Sự cố

```bash
bash demos/03-eviction/reset.sh
sudo fuser -k 6382/tcp
redis-cli -p 6382 shutdown
```
