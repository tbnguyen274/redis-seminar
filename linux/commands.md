# Redis commands

## Kiểm tra dịch vụ

```bash
sudo systemctl status redis-server
redis-server --version
redis-cli ping
redis-cli INFO server
redis-cli INFO memory
redis-cli INFO persistence
redis-cli INFO stats
```

## Quản lý dịch vụ và log

```bash
sudo systemctl restart redis-server
sudo journalctl -u redis-server --since "10 minutes ago"
sudo ss -lntp | grep 6379
```

## Chạy với file cấu hình riêng

Tạo các thư mục dữ liệu và cấp quyền cho người dùng hiện tại:

```bash
sudo mkdir -p \
  /tmp/redis-seminar/rdb \
  /tmp/redis-seminar/aof \
  /tmp/redis-seminar/eviction \
  /tmp/redis-seminar/data-structures \
  /tmp/redis-seminar/cache-aside
sudo chown -R "$USER":"$USER" /tmp/redis-seminar
```

Khởi động từng instance trong một terminal riêng:

```bash
redis-server redis/redis-rdb.conf
redis-server redis/redis-aof.conf
redis-server redis/redis-eviction.conf
redis-server redis/redis-data-structures.conf
redis-server redis/redis-cache-aside.conf
```

Các file mẫu dùng port và thư mục dữ liệu khác nhau để tránh trộn dữ liệu giữa các demo.

| Demo | Port | Thư mục dữ liệu |
|---|---:|---|
| Persistence RDB | `6380` | `/tmp/redis-seminar/rdb` |
| Persistence AOF | `6381` | `/tmp/redis-seminar/aof` |
| Eviction | `6382` | `/tmp/redis-seminar/eviction` |
| Data Structures và TTL | `6383` | `/tmp/redis-seminar/data-structures` |
| Cache-Aside | `6384` | `/tmp/redis-seminar/cache-aside` |

Kiểm tra kết nối đúng port:

```bash
redis-cli -p 6383 PING
redis-cli -p 6384 PING
```

Khi viết script Cache-Aside, cấu hình client kết nối tới `127.0.0.1:6384` thay vì port mặc định `6379`.
