# Hướng Dẫn Vận Hành & Kiểm Thử Demo 03: Eviction (allkeys-lru)

Tài liệu tra cứu nhanh toàn bộ quy trình cấu hình, kiểm thử tự động, kiểm thử thủ công và xử lý sự cố cho Demo 03 trên Redis instance port `6382`.

> **Lưu ý:** Mặc định thực hiện các lệnh từ thư mục gốc của repository (`redis-seminar/`).

---

## 1. Thông tin Cấu hình Instance

- **Cổng dịch vụ (Port):** `6382`
- **File cấu hình:** `redis/redis-eviction.conf`
- **Thư mục dữ liệu:** `/tmp/redis-seminar/eviction`
- **Giới hạn bộ nhớ:** `maxmemory 10mb` (10485760 bytes)
- **Chính sách trục xuất:** `maxmemory-policy allkeys-lru`

---

## 2. Khởi động & Kiểm tra Ban đầu

```bash
# 1. Tạo thư mục dữ liệu
mkdir -p /tmp/redis-seminar/eviction

# 2. Khởi động instance nền
redis-server redis/redis-eviction.conf &

# 3. Kiểm tra kết nối (Mong đợi: PONG)
redis-cli -p 6382 ping

# 4. Kiểm tra cấu hình đã nạp đúng chưa
redis-cli -p 6382 config get maxmemory        # Mong đợi: 10485760
redis-cli -p 6382 config get maxmemory-policy # Mong đợi: allkeys-lru
```

---

## 3. Kiểm thử Tự động (Automated Testing)

Chạy bộ kiểm thử tự động 9 assertions để xác thực toàn bộ hệ thống hoạt động chính xác:

```bash
# Chạy từ thư mục gốc:
bash test/test_demo_03.sh

# Hoặc nếu đang đứng trong thư mục test/:
cd test && bash test_demo_03.sh
```

### 9 tiêu chí được kiểm thử tự động:
1. `Test 1`: Kết nối Redis port 6382 (`PING -> PONG`).
2. `Test 2`: Xác thực `maxmemory` đúng bằng `10485760` bytes (10MB).
3. `Test 3`: Xác thực `maxmemory-policy` đúng là `allkeys-lru`.
4. `Test 4`: Xác thực lệnh dọn dẹp `FLUSHALL`.
5. `Test 5`: Tạo 10 Cold Keys và 5 Hot Keys đối chứng.
6. `Test 6`: Bơm dữ liệu lớn để kích hoạt `evicted_keys >= 15`.
7. `Test 7`: Khẳng định Cold Keys ít dùng đã bị xóa (`EXISTS = 0`).
8. `Test 8`: Khẳng định Hot Keys đọc liên tục được giữ lại (`EXISTS = 1`).
9. `Test 9`: Khẳng định RAM được kiểm soát quanh mức 10MB, không tràn.

---

## 4. Chạy Kịch bản Demo Chính (Phục vụ Quay Video)

```bash
# Chạy script demo có hiển thị tiến trình và bảng đối chứng màu sắc
bash demos/03-eviction/run.sh
```

---

## 5. Kiểm thử Thủ công Trực tiếp qua CLI (Khi Thuyết trình/Phản biện)

```bash
# Bước 1: Dọn sạch dữ liệu cũ
redis-cli -p 6382 flushall && redis-cli -p 6382 config resetstat

# Bước 2: Tạo dữ liệu đối chứng
# - 3 Cold keys (chỉ ghi 1 lần rồi bỏ mặc):
redis-cli -p 6382 set cold_k1 "ColdData_1"
redis-cli -p 6382 set cold_k2 "ColdData_2"
redis-cli -p 6382 set cold_k3 "ColdData_3"

# - 2 Hot keys (sẽ được đọc liên tục):
redis-cli -p 6382 set hot_k1 "HotData_1"
redis-cli -p 6382 set hot_k2 "HotData_2"

# Bước 3: Bơm 120 key lớn (~100KB/key) để làm tràn 10MB RAM
redis-benchmark -p 6382 -t set -n 120 -d 100000 -r 100000 -q

# Bước 4: Đọc Hot Keys để cập nhật LRU clock
redis-cli -p 6382 get hot_k1
redis-cli -p 6382 get hot_k2

# Bước 5: Kiểm tra kết quả đối chứng
redis-cli -p 6382 exists cold_k1 cold_k2 cold_k3   # Kết quả: 0 (Đã bị evict)
redis-cli -p 6382 exists hot_k1 hot_k2             # Kết quả: 2 (Còn tồn tại)
```

---

## 6. Giám sát Số liệu Thời gian Thực

Mở một cửa sổ terminal riêng để theo dõi dung lượng RAM và số lượng key bị trục xuất mỗi giây:

```bash
watch -n 1 "redis-cli -p 6382 info memory | grep used_memory_human; redis-cli -p 6382 info stats | grep evicted_keys"
```

---

## 7. Khôi phục Trạng thái (Reset) & Xử lý Sự cố

```bash
# Dọn dẹp sạch dữ liệu port 6382 về trạng thái 0
bash demos/03-eviction/reset.sh

# Giải phóng cổng 6382 nếu bị chiếm dụng (Address already in use)
sudo fuser -k 6382/tcp

# Tắt instance port 6382 an toàn
redis-cli -p 6382 shutdown
```
