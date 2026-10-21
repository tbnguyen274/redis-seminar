# Lệnh chuẩn bị và chạy demo

Chạy lệnh trong **guest Ubuntu Server**, từ thư mục gốc repo. Dùng cùng commit, cấu hình `redis/*.conf` để đồng nhất môi trường.
VM trình diễn theo đề bài có **512 MB RAM**.

Lần đầu: mục 1 → 2. Mỗi buổi làm việc: mục 2; sau reboot thêm mục 6. Sửa cấu hình: mục 4. Kiểm tra cả nhóm: mục 7.

Demo setup theo recording, gồm giải thích từng bước và output kỳ vọng: [environment-demo.md](environment-demo.md).

## 1. Cài đặt lần đầu

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

## 2. Khởi động demo

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

```bash
# Demo 04: chạy trong hai terminal riêng
redis-server redis/redis-rdb.conf
```

```bash
redis-server redis/redis-aof.conf
```

Ví dụ kiểm tra demo 01 từ terminal thứ hai:

```bash
redis-cli -h 127.0.0.1 -p 6383 PING
```

Kỳ vọng `PONG`. Client của từng demo dùng `127.0.0.1` và port trong bảng, không mặc định dùng 6379. Trên VM dùng chung, nếu instance đã chạy thì dùng instance đó, không start chồng.

## 3. Dependency Python (nếu demo cần)

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Tạo venv một lần; kích hoạt lại trong mỗi terminal chạy Python. Cài dependency bằng `python -m pip install -r <đường-dẫn-requirements.txt>` theo README của demo. Chủ demo bổ sung file requirements cùng code.

## 4. Thay đổi cấu hình

| Muốn đổi | Sửa ở đâu |
|---|---|
| Port, bind, thư mục dữ liệu | `port`, `bind`, `dir` trong file `redis/*.conf` của demo |
| Giới hạn RAM và eviction | `maxmemory`, `maxmemory-policy` trong `redis/redis-eviction.conf` |
| Snapshot RDB | `save`, `dbfilename` trong `redis/redis-rdb.conf` |
| AOF | `appendonly`, `appendfsync`, `save` trong `redis/redis-aof.conf` |
| Host/port client, TTL, dữ liệu và tham số đo | Code của demo trong `demos/` |
| Dependency ứng dụng | File requirements của demo |

Sửa file trên branch riêng, dừng đúng instance theo port **đang chạy**, rồi start lại bằng file đã sửa. Nếu đổi `dir`, tạo thư mục mới có quyền ghi trước khi start; nếu đổi port, cập nhật cả client và tài liệu demo. Không sửa `/etc/redis/redis.conf` để cấu hình các demo 6380–6384.

Ví dụ áp dụng và kiểm tra cấu hình eviction, khi vẫn dùng port 6382:

```bash
redis-cli -p 6382 SHUTDOWN
redis-server redis/redis-eviction.conf
```

Trong terminal thứ hai:

```bash
redis-cli -p 6382 CONFIG GET maxmemory
redis-cli -p 6382 CONFIG GET maxmemory-policy
```

Mặc định: `10485760` bytes (10 MiB), `allkeys-lru`. `CONFIG SET` chỉ đổi cấu hình đang chạy, không tự cập nhật file trong repo. Thay đổi dùng chung cần PR và thống nhất với nhóm; nếu đổi giá trị mà `linux/check.sh` kiểm tra thì cập nhật kỳ vọng tương ứng trong script.

## 5. Dừng, chạy lại và reset

Dừng đúng port, ví dụ demo 01:

```bash
redis-cli -p 6383 SHUTDOWN
```

Chạy lại bằng lệnh start ở mục 2. `sudo systemctl restart redis-server` chỉ restart service 6379, không restart các instance demo.

**Reset chỉ trên dữ liệu demo bỏ được; lưu kết quả trước khi xóa.** Các port 6382–6384 tắt persistence: stop/start để xóa dataset và đặt lại bộ đếm. Nếu chỉ xóa key mà giữ process:

```bash
redis-cli -p 6383 FLUSHALL SYNC
redis-cli -p 6383 DBSIZE
```

RDB: xóa key và lưu snapshot rỗng để dữ liệu cũ không quay lại:

```bash
redis-cli -p 6380 FLUSHALL SYNC
redis-cli -p 6380 SAVE
redis-cli -p 6380 DBSIZE
```

AOF: ghi lệnh xóa vào AOF, rồi dừng bình thường:

```bash
redis-cli -p 6381 FLUSHALL SYNC
redis-cli -p 6381 SHUTDOWN
```

Start lại AOF theo mục 2, dùng `redis-cli -p 6381 DBSIZE` kiểm tra kết quả `0`. Không xóa file persistence khi server đang chạy. `FLUSHALL` không đặt lại thống kê hoặc cấu hình tạm; với eviction, restart từ file config trước mỗi lượt đo.

## 6. Sau reboot

Service 6379 tự khởi động. `/tmp` có thể bị dọn; tạo lại thư mục dưới user vận hành rồi start demo cần dùng theo mục 2, không cần chạy lại setup chỉ để tạo thư mục:

```bash
mkdir -p /tmp/redis-seminar/{rdb,aof,eviction,data-structures,cache-aside}
```

## 7. Kiểm tra tích hợp cả nhóm

Chỉ chạy sau khi **service 6379 và đủ năm instance 6380–6384** đã start theo cấu hình chung:

```bash
bash linux/check.sh
```

Kỳ vọng cuối output: `PASS`. Script chỉ đọc trạng thái/cấu hình, không sửa dữ liệu. Thiếu instance hoặc cấu hình khác kỳ vọng sẽ thất bại; khi làm riêng một demo, dùng `PING` và `CONFIG GET` trên port của demo đó.

Xử lý lỗi: [troubleshooting.md](troubleshooting.md). Kết quả các lần thử nghiệm: [environment-verification.md](../docs/environment-verification.md).
