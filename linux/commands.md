# Lệnh chuẩn bị và chạy demo

Chạy lệnh trong **guest Ubuntu Server**, từ thư mục gốc repo. Dùng cùng commit, cấu hình `redis/*.conf` để đồng nhất môi trường.
VM trình diễn theo đề bài có **512 MB RAM**.

Lần đầu: mục 1 → 2. Mỗi buổi làm việc: mục 2; sau reboot thêm mục 6. Sửa cấu hình: mục 4. Kiểm tra cả nhóm: mục 7.

Demo setup theo recording, gồm giải thích từng bước và output kỳ vọng: [environment-demo.md](environment-demo.md).

## Cài đặt lần đầu

```bash
sudo apt-get update
sudo apt-get upgrade
sudo apt-get install -y git ca-certificates
git clone --branch feat/environment-prep https://github.com/tbnguyen274/redis-seminar.git
cd redis-seminar
sudo bash linux/setup.sh
```

Setup cài Redis, Python/venv và công cụ kiểm tra, tạo năm thư mục dữ liệu dưới `/tmp/redis-seminar/`, bật service mặc định **6379**. Setup **không** start năm instance demo. Chạy lại setup sẽ restart 6379; không chạy giữa lúc đang đo.

```bash
redis-cli -p 6379 PING
git rev-parse HEAD
redis-server --version
python3 --version
```

Kết nối thành công trả `PONG`. Gói apt không được khóa phiên bản; dùng cùng image/snapshot nếu cần cùng phiên bản Redis/Python.

## Khởi động demo

| Demo | File trong `redis/` | Port | Thư mục dữ liệu |
|---|---|---:|---|
| Cấu trúc dữ liệu/TTL | `redis-data-structures.conf` | 6383 | `/tmp/redis-seminar/data-structures` |
| Cache-Aside | `redis-cache-aside.conf` | 6384 | `/tmp/redis-seminar/cache-aside` |
| Eviction | `redis-eviction.conf` | 6382 | `/tmp/redis-seminar/eviction` |
| RDB | `redis-rdb.conf` | 6380 | `/tmp/redis-seminar/rdb` |
| AOF | `redis-aof.conf` | 6381 | `/tmp/redis-seminar/aof` |

**Chọn lệnh tương ứng với demo**. Mỗi lệnh giữ terminal để hiện log; mở terminal khác để chạy ứng dụng/Redis CLI. Nếu chạy nhiều instance, mỗi instance dùng một terminal riêng.

```bash
# Demo 01
redis-server redis/redis-data-structures.conf
```

```bash
# Demo 02
redis-server redis/redis-cache-aside.conf
```

```bash
# Demo 03
redis-server redis/redis-eviction.conf
```

Trong terminal thứ hai:

```bash
redis-cli -p 6382 CONFIG GET maxmemory
redis-cli -p 6382 CONFIG GET maxmemory-policy
```

Mặc định: `10485760` bytes (10 MiB), `allkeys-lru`. `CONFIG SET` chỉ đổi cấu hình đang chạy, không tự cập nhật file trong repo. Thay đổi dùng chung cần PR và thống nhất với nhóm; nếu đổi giá trị mà `linux/check.sh` kiểm tra thì cập nhật kỳ vọng tương ứng trong script.

## Dừng, chạy lại và reset

| Demo | Port | Thư mục dữ liệu |
|---|---:|---|
| Persistence RDB | `6380` | `demos/04-persistence-crash/results/run-.../trial-.../rdb/data` |
| Persistence AOF | `6381` | `demos/04-persistence-crash/results/run-.../trial-.../aof/data` |
| Eviction | `6382` | `/tmp/redis-seminar/eviction` |
| Data Structures và TTL | `6383` | `/tmp/redis-seminar/data-structures` |
| Cache-Aside | `6384` | `/tmp/redis-seminar/cache-aside` |

RDB: xóa key và lưu snapshot rỗng để dữ liệu cũ không quay lại:

```bash
redis-cli -p 6380 FLUSHALL SYNC
redis-cli -p 6380 SAVE
redis-cli -p 6380 DBSIZE
```

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
