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
