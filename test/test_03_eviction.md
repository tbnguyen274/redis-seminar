# Kiểm thử Demo 03: Eviction (allkeys-lru)

Tài liệu quy trình kiểm thử tự động và kiểm thử thủ công cho Demo 03 trên Redis instance port `6382`.

---

## 1. Kiểm thử tự động (Automated Testing)

Chạy bộ kiểm thử tự động gồm 9 assertions:

```bash
bash test/test_demo_03.sh
```

### Các tiêu chí kiểm tra:
1. `Test 1`: Kết nối tới port 6382 (`PING -> PONG`).
2. `Test 2`: Xác thực `maxmemory` bằng `10485760` bytes (10MB).
3. `Test 3`: Xác thực `maxmemory-policy` bằng `allkeys-lru`.
4. `Test 4`: Xác thực lệnh dọn dẹp `FLUSHALL`.
5. `Test 5`: Tạo 10 Cold Keys và 5 Hot Keys đối chứng.
6. `Test 6`: Kích hoạt cơ chế Eviction (`evicted_keys >= 15`).
7. `Test 7`: Khẳng định Cold Keys bị trục xuất (`EXISTS = 0`).
8. `Test 8`: Khẳng định Hot Keys được giữ lại (`EXISTS = 1`).
9. `Test 9`: Khẳng định RAM được kiểm soát quanh mức 10MB.

---

## 2. Kiểm thử thủ công qua CLI (Manual Testing)

### Bước 1: Khởi động và kiểm tra cấu hình
```bash
redis-server redis/redis-eviction.conf &
redis-cli -p 6382 ping
redis-cli -p 6382 config get maxmemory
redis-cli -p 6382 config get maxmemory-policy
redis-cli -p 6382 flushall
```

### Bước 2: Tạo dữ liệu đối chứng
```bash
# Cold keys (chỉ ghi 1 lần)
redis-cli -p 6382 set cold_k1 "val1"
redis-cli -p 6382 set cold_k2 "val2"
redis-cli -p 6382 set cold_k3 "val3"

# Hot keys (ghi và đọc liên tục)
redis-cli -p 6382 set hot_k1 "val1"
redis-cli -p 6382 set hot_k2 "val2"
```

### Bước 3: Bơm dữ liệu làm tràn RAM
```bash
# Bơm 120 key, mỗi key 100KB
redis-benchmark -p 6382 -t set -n 120 -d 100000 -r 100000 -q

# Đọc hot keys để cập nhật LRU
redis-cli -p 6382 get hot_k1
redis-cli -p 6382 get hot_k2
```

### Bước 4: Kiểm tra kết quả
```bash
# Kiểm tra RAM và evicted keys
redis-cli -p 6382 info memory | grep used_memory_human
redis-cli -p 6382 info stats | grep evicted_keys

# Kiểm tra tồn tại
redis-cli -p 6382 exists cold_k1 cold_k2 cold_k3   # Mong đợi: 0 (bị xóa)
redis-cli -p 6382 exists hot_k1 hot_k2             # Mong đợi: 2 (còn tồn tại)
```

---

## 3. Khôi phục trạng thái (Reset)

```bash
bash demos/03-eviction/reset.sh
```
