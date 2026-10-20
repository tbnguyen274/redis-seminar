# Demo 03: Giới hạn Bộ nhớ (maxmemory) và Chính sách Trục xuất allkeys-lru

- **Người thực hiện:** Mạnh Tường (Thành viên STT 4)
- **Cổng dịch vụ:** `6382`
- **File cấu hình:** [`redis/redis-eviction.conf`](../../redis/redis-eviction.conf)
- **Thư mục dữ liệu:** `/tmp/redis-seminar/eviction`

---

## 1. Mục tiêu Thực nghiệm

1. Chứng minh Redis tuân thủ tuyệt đối giới hạn bộ nhớ được cấu hình (`maxmemory 10mb`).
2. Quan sát trực quan cơ chế thu hồi bộ nhớ tự động: chỉ số `used_memory_human` dừng ở mức ~10MB và chỉ số `evicted_keys` tăng dần.
3. Kiểm chứng thuật toán **Approximate LRU (`allkeys-lru`)** hoạt động đúng thực tế:
   - **Cold Keys (Key nguội):** Ghi lúc đầu, không được đọc lại $\rightarrow$ Bị Redis tự động trục xuất (Evicted).
   - **Hot Keys (Key nóng):** Ghi lúc đầu, được đọc lặp lại liên tục $\rightarrow$ Được cập nhật `lru clock` và được giữ lại trong bộ nhớ.

---

## 2. Cấu trúc Thư mục

```text
demos/03-eviction/
├── requirements.txt   # Khai báo dependency (redis-py)
├── reset.sh           # Script dọn dẹp sạch dữ liệu port 6382
├── fill_memory.py     # Script chính tạo key, bơm tràn RAM và kiểm chứng LRU
├── run.sh             # Script chạy trọn gói một chạm
└── README.md          # Tài liệu hướng dẫn kỹ thuật này
```

---

## 3. Hướng dẫn Chạy Thực nghiệm

### Bước 1: Khởi động Redis Instance (Port 6382)
Mở terminal và chạy lệnh khởi động Redis ở chế độ nền:
```bash
# Tạo thư mục dữ liệu nếu chưa có
mkdir -p /tmp/redis-seminar/eviction

# Khởi động instance riêng biệt trên port 6382
redis-server redis/redis-eviction.conf &

# Kiểm tra kết nối
redis-cli -p 6382 ping
# Kết quả mong đợi: PONG
```

### Bước 2: Kiểm tra Cấu hình Ban đầu
```bash
redis-cli -p 6382 config get maxmemory
# Kết quả: 10485760 (10MB)

redis-cli -p 6382 config get maxmemory-policy
# Kết quả: allkeys-lru
```

### Bước 3: Cài đặt Thư viện Python
```bash
pip install -r demos/03-eviction/requirements.txt
```

### Bước 4: Chạy Demo
Bạn có thể chạy bằng một trong hai cách:

**Cách 1 (Khuyên dùng khi quay video demo):**
Chia 2 cửa sổ terminal:
- **Cửa sổ 1 (Giám sát real-time):**
  ```bash
  watch -n 1 "redis-cli -p 6382 info memory | grep used_memory_human; redis-cli -p 6382 info stats | grep evicted_keys"
  ```
- **Cửa sổ 2 (Chạy demo):**
  ```bash
  python3 demos/03-eviction/fill_memory.py
  ```

**Cách 2 (Chạy tự động toàn bộ):**
```bash
bash demos/03-eviction/run.sh
```

---

## 4. Kết quả Thực nghiệm Mong đợi

Khi script chạy xong, bạn sẽ thấy kết quả bảng đối chứng:

1. **Bộ nhớ RAM (`used_memory`):** Chạm trần ở mức **9.8MB - 10MB** và không bao giờ vượt qua 10MB.
2. **Chỉ số `evicted_keys`:** Tăng từ `0` lên `30+` keys.
3. **Bảng đối chiếu Key sống/chết:**
   - 10 Cold Keys (`cold_user_1` .. `cold_user_10`): **ĐÃ BỊ EVICT [✓]**
   - 5 Hot Keys (`hot_user_1` .. `hot_user_5`): **VẪN CÒN SỐNG [✓]**

---

## 5. Script Dọn dẹp (Reset)

Sau khi demo xong hoặc trước mỗi lần quay video mới, chạy lệnh sau để đưa instance về trạng thái trống:
```bash
bash demos/03-eviction/reset.sh
```
Lệnh này sẽ thực thi `FLUSHALL` và `CONFIG RESETSTAT` an toàn riêng trên port `6382`.
