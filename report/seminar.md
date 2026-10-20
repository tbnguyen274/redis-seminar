# Báo cáo Seminar: Redis In-Memory Data Store

## 1. Thông tin môi trường

- Hệ điều hành:
- CPU/RAM: 1 VM, 512 MB RAM
- Phiên bản Redis:
- Ngày thực hiện:

## 2. Nội dung lý thuyết

### 2.1. Vai trò của caching và mô hình Cache-Aside

### 2.2. Redis single-threaded và hiệu năng

### 2.3. Persistence: RDB và AOF

### 2.4. Eviction: noeviction, allkeys-lru và volatile-ttl

#### a. Cơ chế giới hạn bộ nhớ (`maxmemory`)
Redis lưu trữ dữ liệu hoàn toàn trên RAM. Để kiểm soát tài nguyên trên máy chủ và tránh bị tiến trình OOM Killer của hệ điều hành tắt đột ngột, Redis cung cấp tham số cấu hình `maxmemory`. Trước mỗi lệnh ghi dữ liệu mới, Redis kiểm tra nếu `used_memory > maxmemory`, hệ thống sẽ kích hoạt thuật toán thu hồi bộ nhớ theo chính sách `maxmemory-policy`. Nếu không thể thu hồi thêm bộ nhớ, Redis từ chối lệnh ghi và trả lỗi `OOM command not allowed`.

#### b. Phân biệt Expiration (Hết hạn TTL) và Eviction (Trục xuất khi đầy RAM)
- **Expiration (Hết hạn):** Xóa các key khi thời gian sống (TTL) định sẵn đã trôi qua hết. Cơ chế này áp dụng cho các key có cài đặt `EXPIRE` và diễn ra theo hai phương thức: thụ động (khi có truy cập) hoặc chủ động (quét ngẫu nhiên định kỳ 100ms).
- **Eviction (Trục xuất):** Buộc phải xóa key khi bộ nhớ RAM chạm ngưỡng `maxmemory` để lấy chỗ cho dữ liệu mới, ngay cả khi key đó còn hạn sử dụng hoặc không bao giờ hết hạn.

#### c. Các chính sách Eviction chính
1. **`noeviction` (Mặc định):** Không xóa bất kỳ dữ liệu nào. Khi RAM đầy, từ chối mọi lệnh ghi mới và trả lỗi OOM. Thích hợp khi Redis đóng vai trò cơ sở dữ liệu chính xác thực, không được phép mất mát dữ liệu.
2. **`allkeys-lru`:** Quét trên toàn bộ database và loại bỏ các key có thời gian không được truy cập lâu nhất (Least Recently Used). Đây là cấu hình tối ưu nhất cho bài toán Caching, đảm bảo dữ liệu "nóng" luôn được giữ lại.
3. **`volatile-ttl`:** Chỉ áp dụng đối với tập hợp các key có cài đặt TTL, ưu tiên xóa các key có thời gian sống còn lại ngắn nhất. Các key tĩnh hoặc không có TTL sẽ được bảo toàn an toàn.

#### d. Thuật toán Approximate LRU trong Redis
Redis không sử dụng thuật toán True LRU (danh sách liên kết đôi kết hợp bảng băm) vì mô hình này tiêu tốn thêm 16–24 bytes con trỏ cho mỗi key và gây tranh chấp ghi trên bộ nhớ ở mỗi lệnh đọc `GET`. Thay vào đó, Redis sử dụng **Approximate LRU**:
- Mỗi đối tượng dữ liệu (`robj`) lưu trữ một trường thời gian 24-bit (`lru clock`).
- Khi bộ nhớ đầy, Redis lấy ngẫu nhiên $N$ key (`maxmemory-samples`, mặc định là 5) và đưa vào bể ứng viên (Eviction Pool) có kích thước 16 phần tử, sắp xếp theo thời gian nhàn rỗi (idle time) giảm dần.
- Key có thời gian nhàn rỗi lớn nhất trong pool sẽ bị tiêu hủy. Cách tiếp cận này tiết kiệm RAM đáng kể và đạt độ chính xác xấp xỉ True LRU.

#### e. Memory Overhead và Phân mảnh bộ nhớ (`mem_fragmentation_ratio`)
Mỗi key-value trong Redis ngoài dung lượng dữ liệu thô còn chịu chi phí metadata từ `dictEntry` (24B) và `robj` (16B). Trình cấp phát bộ nhớ jemalloc phân bổ RAM theo trang cố định, dẫn đến hiện tượng phân mảnh bộ nhớ khi dữ liệu bị xóa hoặc cập nhật liên tục. Hệ số `mem_fragmentation_ratio = used_memory_rss / used_memory` phản ánh mức độ phân mảnh; nếu chỉ số này lớn hơn 1.5, cần kích hoạt `activedefrag yes` để tối ưu lại RAM.

## 3. Kết quả demo

### 3.1. Cấu trúc dữ liệu và TTL

### 3.2. Cache-Aside: Cache Miss và Cache Hit

| Lần chạy | Trạng thái cache | Thời gian phản hồi |
|---|---|---:|
| 1 | Miss | |
| 2 | Hit | |
| 3 | Hit | |

### 3.3. Eviction với allkeys-lru

### 3.4. Crash test: RDB so với AOF

| Cấu hình | Số key trước crash | Số key sau restart | Số key mất |
|---|---:|---:|---:|
| RDB | | | |
| AOF everysec | | | |

## 4. Troubleshooting và bài học

## 5. Kết luận

## 6. Tài liệu tham khảo

1. Redis Documentation - Key Eviction: https://redis.io/docs/latest/develop/reference/eviction/
2. Redis Documentation - Memory Optimization: https://redis.io/docs/latest/develop/optimization/memory-optimization/
3. Salvatore Sanfilippo (antirez) - "Redis as an LRU cache": http://antirez.com/news/109
4. Redis Source Code Repository - `src/evict.c` and `src/server.h`: https://github.com/redis/redis
