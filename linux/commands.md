# Redis commands

## 1. Chuẩn bị Ubuntu/Debian

Chạy các lệnh Linux từ thư mục gốc repo. Môi trường cuối theo đề: VM Linux **512 MB RAM**. Ưu tiên bản server tối giản nếu desktop không chạy ổn ở mức RAM này. Chụp cấu hình CPU/RAM trong VMware; `free -h` chỉ là thông tin bổ sung từ guest.

Lần chạy VMware đã đối chiếu dùng Ubuntu 26.04.1 LTS, Redis 8.0.5, Python 3.14.4, 512 MB/2 CPUs và khoảng 1.6 GiB swap. WSL trước đó dùng phiên bản khác. Xem [kết quả và cảnh báo thực tế](../docs/environment-verification.md); lệnh start nền dưới đây bổ sung PID file riêng từ phát hiện trong log, chưa được chạy lại trên VM sau thay đổi này.

```bash
sudo apt-get update
sudo apt-get install -y git ca-certificates
git clone --branch feat/environment-prep https://github.com/tbnguyen274/redis-seminar.git
cd redis-seminar
sudo bash linux/setup.sh
```

Nếu đã clone thì dùng thư mục hiện có. Repo có thể yêu cầu tài khoản GitHub được cấp quyền. `setup.sh` cần systemd, cài Redis, Python/venv và công cụ kiểm tra process/port, tạo năm thư mục dữ liệu cho user gọi sudo, rồi khởi động dịch vụ mặc định. Chạy lại setup sẽ restart port 6379; thực hiện trước khi lấy số liệu, không chạy giữa một experiment.

```bash
cat /etc/os-release
uname -r
free -h
df -h /
redis-server --version
python3 --version
```

Giữ phiên bản gói thực tế trong log. Script dùng gói apt của distro, không khóa phiên bản tuyệt đối; tái lập cùng phiên bản cần dùng cùng image/snapshot và ghi lại `dpkg-query -W redis-server redis-tools python3`.

Branch trên là branch chuẩn bị đang có draft PR; sau khi nhóm merge, dùng branch đã thống nhất. Lưu `git rev-parse HEAD` trước lần đo. Kiểm tra syntax từng script bằng lệnh riêng:

```bash
bash -n linux/setup.sh
bash -n linux/check.sh
```

`bash -n file1 file2` chỉ parse file1; file2 là argument, không phải lượt kiểm tra thứ hai.

## 2. Rehearsal bằng WSL2

WSL2 có systemd có thể chạy cùng config/lệnh Redis. Đây là môi trường rehearsal; một lần chạy WSL với RAM mặc định không xác minh yêu cầu VM 512 MB.

Trong PowerShell, nếu chưa có distro phù hợp:

```powershell
wsl --install Ubuntu-24.04 --name RedisSeminar --no-launch --web-download
wsl -d RedisSeminar
```

Hoàn thành tạo Linux user nếu được hỏi. Sau đó làm bước 1 trong Linux. Nên clone trong home Linux để tránh khác biệt filesystem với `/mnt/c` hoặc `/mnt/f`; có thể mở thư mục Linux từ Windows khi cần. Kiểm tra `ps -p 1 -o comm=` phải trả `systemd`; xem troubleshooting nếu khác.

Python demo nên dùng virtual environment, không cài library bằng `sudo pip`:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip --version
```

Sau khi chủ demo cung cấp `requirements.txt`, cài đúng file của demo đó và ghi phiên bản dependency. Script Cache-Aside chưa có trong starter repo, nên chưa có dependency ứng dụng để xác nhận.

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

Các config dùng `daemonize no`: mỗi dòng start ở trên chạy trong **một terminal riêng** và giữ terminal để hiện log. Khi rehearsal tự động, có thể chạy nền bằng tùy chọn dòng lệnh, không cần sửa config:

```bash
redis-server redis/redis-rdb.conf --daemonize yes --pidfile /tmp/redis-seminar/rdb/server.pid --logfile /tmp/redis-seminar/rdb/server.log
redis-server redis/redis-aof.conf --daemonize yes --pidfile /tmp/redis-seminar/aof/server.pid --logfile /tmp/redis-seminar/aof/server.log
redis-server redis/redis-eviction.conf --daemonize yes --pidfile /tmp/redis-seminar/eviction/server.pid --logfile /tmp/redis-seminar/eviction/server.log
redis-server redis/redis-data-structures.conf --daemonize yes --pidfile /tmp/redis-seminar/data-structures/server.pid --logfile /tmp/redis-seminar/data-structures/server.log
redis-server redis/redis-cache-aside.conf --daemonize yes --pidfile /tmp/redis-seminar/cache-aside/server.pid --logfile /tmp/redis-seminar/cache-aside/server.log
```

Chọn một cách start. Nếu port đã có process thì kiểm tra process/config trước, không start chồng. Log trên dùng thư mục riêng; foreground log nằm ngay terminal. Vì `daemonize yes` trả terminal trước khi server sẵn sàng, xác nhận `PING` sau mỗi lần start.

PID file riêng tránh đường dẫn mặc định mà user thường không ghi được. Không dùng PID file cũ để kill process; đối chiếu `INFO server` và port hiện tại. Nếu log cảnh báo overcommit, đọc mục tương ứng trong [troubleshooting.md](troubleshooting.md) trước thử nghiệm BGSAVE/rewrite.

## Kiểm tra tổng hợp và lưu minh chứng

Khi dịch vụ mặc định và cả năm instance đã chạy:

```bash
set -o pipefail
bash linux/check.sh | tee docs/screenshots/00-environment/environment-check.txt
```

Script chỉ đọc trạng thái, không tạo/xóa key và không start/stop process. Nó phải kết thúc bằng `PASS`; sai port/config hoặc thiếu instance sẽ trả exit code khác 0. File log ghi môi trường thật của lần chạy, không thay cho ảnh cấu hình VMware. Dùng tên file khác cho các lần chạy cần giữ lại.

Chứng minh cách ly bằng key tạm, chạy khi chưa thu số liệu demo:

```bash
redis-cli -p 6383 SET env:probe instance-6383 EX 60
redis-cli -p 6383 GET env:probe
redis-cli -p 6384 GET env:probe
redis-cli -p 6383 DEL env:probe
```

Kỳ vọng: `OK`, `instance-6383`, `(nil)`, rồi số key xóa. Kiểm tra trước rằng `env:probe` không phải key của bài khác. Khi output không tương tác, nil có thể hiện thành dòng trống.

## Stop, restart và reset

**Stop bình thường** dùng đúng port, ví dụ:

```bash
redis-cli -p 6383 SHUTDOWN
ss -lnt 'sport = :6383'
```

Start lại bằng đúng config đã dùng. Dịch vụ mặc định port 6379 quản lý riêng bằng `sudo systemctl restart redis-server`. Các instance demo start tay không được quản lý bởi service này.

**Reset dữ liệu** chỉ áp dụng instance chứa dữ liệu demo bỏ được. `FLUSHALL` xóa toàn bộ logical database của port chỉ định. Lưu kết quả experiment trước khi reset. Với RDB, thay snapshot cũ bằng dataset rỗng:

```bash
redis-cli -p 6380 FLUSHALL SYNC
redis-cli -p 6380 SAVE
redis-cli -p 6380 DBSIZE
```

Với AOF, lệnh xóa được ghi vào log, rồi shutdown bình thường:

```bash
redis-cli -p 6381 FLUSHALL SYNC
redis-cli -p 6381 DBSIZE
redis-cli -p 6381 SHUTDOWN
```

Start lại AOF bằng `redis/redis-aof.conf`, `DBSIZE` phải là 0. Redis 7+ có thể dùng nhiều file trong `appendonlydir`; không chỉ xóa một file `appendonly.aof` rồi cho rằng đã reset.

Các port 6382–6384 tắt persistence. Stop/start bằng đúng config sẽ tạo dataset và bộ đếm mới. Nếu chỉ muốn xóa key mà giữ process:

```bash
redis-cli -p 6383 FLUSHALL SYNC
redis-cli -p 6383 DBSIZE
```

`FLUSHALL` không đặt lại toàn bộ thống kê và không hoàn tác `CONFIG SET`. Với eviction, nên restart từ config trước mỗi lượt để số `evicted_keys` bắt đầu lại; hoặc đo chênh lệch trước/sau cùng một lượt, ghi rõ cách làm. Chưa có bằng chứng reset chỉ vì đã nhận `OK`: luôn đối chiếu `DBSIZE` sau restart.

## Sau reboot và trước khi quay

- `/tmp/redis-seminar/` có thể bị dọn. Tạo lại năm thư mục bằng block phía trên, rồi start các demo. Không cần chạy lại apt chỉ để tạo thư mục.
- Dịch vụ 6379 đã enable sẽ tự start khi systemd khởi động. Năm instance demo phải start riêng.
- Chạy `bash linux/check.sh`, kiểm tra snapshot/file cũ, rồi reset theo bài trước khi lấy số liệu.
- Giữ bằng chứng trong repo và video ở vị trí chia sẻ của nhóm. Chụp snapshot VMware khi môi trường đã sẵn sàng và ghi chú phiên bản snapshot.
- Khi kết thúc, stop các port demo bằng `redis-cli -p <port> SHUTDOWN`; không dùng `pkill redis-server`.
