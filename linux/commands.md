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
  /tmp/redis-seminar/eviction \
  /tmp/redis-seminar/data-structures \
  /tmp/redis-seminar/cache-aside
sudo chown -R "$USER":"$USER" /tmp/redis-seminar
```

Khởi động từng instance trong một terminal riêng:

```bash
redis-server redis/redis-eviction.conf
redis-server redis/redis-data-structures.conf
redis-server redis/redis-cache-aside.conf
```

Các file mẫu dùng port và thư mục dữ liệu khác nhau để tránh trộn dữ liệu giữa các demo.

| Demo | Port | Thư mục dữ liệu |
|---|---:|---|
| Persistence RDB | `6380` | `demos/04-persistence-crash/results/run-.../trial-.../rdb/data` |
| Persistence AOF | `6381` | `demos/04-persistence-crash/results/run-.../trial-.../aof/data` |
| Eviction | `6382` | `/tmp/redis-seminar/eviction` |
| Data Structures và TTL | `6383` | `/tmp/redis-seminar/data-structures` |
| Cache-Aside | `6384` | `/tmp/redis-seminar/cache-aside` |

Kiểm tra kết nối đúng port:

```bash
redis-cli -p 6383 PING
redis-cli -p 6384 PING
```

Khi viết script Cache-Aside, cấu hình client kết nối tới `127.0.0.1:6384` thay vì port mặc định `6379`.

## Chạy persistence crash test trên Bash/Linux

Hai file `redis/redis-rdb.conf` và `redis/redis-aof.conf` là template có placeholder. Không truyền trực tiếp chúng cho `redis-server`. Script tự tạo config thực với đường dẫn tuyệt đối, khởi động, gây crash và restart các instance riêng.

Cần Redis 7+, Python 3.9+ và hai port 6380/6381 còn trống. Các lệnh bên dưới dùng Bash trên Ubuntu/Debian hoặc trong WSL, chạy từ thư mục gốc repository.

### 1. Cài công cụ hệ thống bằng apt

`requirements.txt` chỉ chứa package Python. Các chương trình Redis và công cụ Linux phải cài riêng:

| Gói | Cung cấp | Khi nào cần |
|---|---|---|
| `redis-server` | Tiến trình Redis | Mọi crash trial |
| `redis-tools` | `redis-cli` | Kiểm tra thủ công và bài Bash |
| `python3` | Trình chạy Python | Bản Python |
| `python3-venv` | Tạo virtualenv | Cài dependency Python trong môi trường riêng |
| `strace` | Theo dõi syscall | Chỉ khi dùng `--trace-fsync` |
| `iproute2` | `ss` kiểm tra port | Bài `persistence_crash.sh` |

```bash
sudo apt update
sudo apt install -y redis-server redis-tools python3 python3-venv
redis-server --version
redis-cli --version
python3 --version
```

Cài thêm theo chế độ sẽ chạy, không bắt buộc cho bản Python thông thường:

```bash
# Chỉ cần khi bật --trace-fsync
sudo apt install -y strace

# Chỉ cần khi chạy bài Bash persistence_crash.sh
sudo apt install -y iproute2
```

`linux/setup.sh` hiện chỉ cài `redis-server`/`redis-tools` và quản lý dịch vụ Redis mặc định. Nó chưa cài Python/venv, strace, iproute2 hoặc dependency Python cho demo 04.

### 2. Cài dependency Python bằng pip trong virtualenv

Thực hiện một lần khi chuẩn bị repo; không dùng `sudo pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demos/04-persistence-crash/requirements.txt
```

[requirements.txt](../demos/04-persistence-crash/requirements.txt) hiện ghim `redis==5.3.1` (redis-py, client Python), không cài Redis server. Các dependency Python gián tiếp được pip cài theo thư viện; không đưa `redis-server` hoặc `strace` vào file này.

Mỗi lần mở terminal mới, chỉ cần kích hoạt lại virtualenv đã có. Với WSL, tạo và dùng virtualenv bên Linux, không dùng lại virtualenv tạo bằng Python Windows.

### 3. Chạy bản Python

```bash
source .venv/bin/activate
python demos/04-persistence-crash/scripts/run_trials.py \
  --trials 3 --baseline 2000 --delta 1000 --delays 0,0.2,1.5
```

Mỗi lần chạy tạo `results/run-<UTC>-<id>/summary.csv` riêng trong thư mục demo. Xem [hướng dẫn demo 04](../demos/04-persistence-crash/README.md) để biết cấu trúc trial và cách đọc kết quả.

### 4. Chạy tùy chọn quan sát fsync

Sau khi đã cài `strace` và kích hoạt virtualenv:

```bash
python demos/04-persistence-crash/scripts/run_trials.py \
  --trials 3 --baseline 100 --delta 30 --delays 0,0.5,1.5 \
  --trace-fsync
```

Chế độ này chỉ quan sát fsync của incremental AOF, có overhead và không phải thử nghiệm cắt nguồn máy. Không chạy Python bằng sudo để xử lý lỗi ptrace; xem thông báo lỗi và chính sách của máy lab trước.

### 5. Chạy bài Bash theo từng bước

Cần `redis-server`, `redis-tools`, `iproute2`, Bash 4+ và các công cụ Linux thông dụng có sẵn trên Ubuntu. Không cần Python hoặc redis-py:

```bash
bash demos/04-persistence-crash/scripts/persistence_crash.sh
```

Không chạy đồng thời bài Bash và bản Python vì cùng dùng port 6380/6381. Hai bản tự khởi động Redis riêng; không cần bật thủ công các instance ở hai port này trước khi chạy.

### 6. Kiểm tra offline

Sau khi cài requirements, trong virtualenv; không cần Redis server đang chạy:

```bash
python -m unittest discover -s demos/04-persistence-crash/tests -v
```
