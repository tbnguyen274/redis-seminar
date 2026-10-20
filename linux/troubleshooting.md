# Troubleshooting checklist

## Cài apt dừng ở “Processing triggers”, process có trạng thái `T`

`T` trong `ps` là process bị stop/suspend, thường do Ctrl+Z hoặc một stop signal; chỉ output này không xác định được ai gửi signal. Swap có thể làm cài đặt chậm nhưng không tự giải thích trạng thái `T`.

Trong terminal gốc, dùng `jobs -l`; nếu job setup đang Stopped, dùng `fg` để tiếp tục. Nếu terminal gốc còn bị giữ, ở phiên SSH thứ hai kiểm tra PID hiện tại bằng `ps -p <PID> -o pid,ppid,stat,comm`; chỉ khi đúng process apt đang stop mới gửi `sudo kill -CONT <PID>`. Không dùng lại PID cũ mà chưa đối chiếu. Không xóa lock apt/dpkg hoặc chạy setup chồng lên tiến trình còn tồn tại.

## Script lỗi `pipefail`, `$'\r'` hoặc `bad interpreter`

Đây thường là line ending CRLF do checkout trên Windows. Repo quy định LF cho `*.sh` và `*.conf` trong `.gitattributes`. Với clone cũ, kiểm tra `file linux/setup.sh`; đổi shell script về LF trước khi chạy. Không dùng `sudo sh linux/setup.sh`: script yêu cầu Bash, dùng `sudo bash linux/setup.sh`.

## WSL báo không có systemd

Trong Linux kiểm tra `ps -p 1 -o comm=`. Nếu không phải `systemd`, mở `/etc/wsl.conf` bằng `sudoedit /etc/wsl.conf`, giữ các mục hiện có và thêm/cập nhật:

```ini
[boot]
systemd=true
```

Thoát shell. Trong PowerShell chạy `wsl --terminate <tên-distro>` rồi mở lại distro và kiểm tra PID 1. Lệnh terminate dừng mọi process trong distro đó; lưu công việc trước. Cần WSL hỗ trợ systemd (0.67.6 trở lên), cập nhật WSL nếu phiên bản quá cũ. Không sửa `.wslconfig` toàn máy chỉ để chạy các demo.

`sudo` có thể hỏi mật khẩu Linux user. Đây là mật khẩu của tài khoản trong distro, không nhất thiết là mật khẩu Windows. Không ghi mật khẩu vào repo hoặc video.

Nguồn: [Microsoft: systemd trong WSL](https://learn.microsoft.com/en-us/windows/wsl/systemd).

## Dịch vụ không khởi động

1. Kiểm tra trạng thái: `sudo systemctl status redis-server`.
2. Đọc log: `sudo journalctl -u redis-server -n 100 --no-pager`.
3. Kiểm tra cú pháp/cấu hình bằng cách chạy `redis-server <config-file>` ở foreground.
4. Kiểm tra port đang được dùng: `sudo ss -lntp | grep 6379`.
5. Kiểm tra quyền ghi của `dir`, file RDB và thư mục AOF.

Port 6380–6384 là instance start tay: `systemctl status redis-server` chỉ phản ánh service mặc định. Đọc log ngay trong terminal chạy `redis-server` của demo.

Nếu báo address already in use, chạy `sudo ss -lntp 'sport = :6383'` với đúng port. Đối chiếu process trước khi stop; không kill tất cả Redis. Nếu thiếu `dir` sau reboot, tạo lại đúng thư mục và owner như [commands.md](commands.md).

## Không kết nối được

- Xác nhận đúng host/port và tiến trình đang lắng nghe.
- Kiểm tra `bind`, `protected-mode`, firewall và thông tin xác thực.
- Không public Redis trực tiếp ra Internet. Chỉ mở mạng khi demo yêu cầu và phải giới hạn nguồn truy cập.

## Lỗi ghi dữ liệu

- Đọc `INFO memory` để kiểm tra `used_memory`, `maxmemory` và policy.
- Với `noeviction`, Redis trả lỗi ghi khi hết bộ nhớ; với `allkeys-lru`, theo dõi `evicted_keys` trong `INFO stats`.
- Đọc `INFO persistence` để phát hiện lỗi RDB/AOF và kiểm tra dung lượng đĩa.

Nếu background save/fork lỗi trên VM ít RAM, kiểm tra `free -h`, log, `sysctl vm.overcommit_memory` và dung lượng dataset. Thu nhỏ dataset, giảm process không cần thiết, kiểm tra trạng thái snapshot/rewrite. Bất kỳ điều chỉnh kernel hoặc RAM nào cũng cần ghi vào môi trường thực đo; không đổi cấu hình toàn máy WSL để che lỗi. Xem [Redis FAQ](https://redis.io/docs/latest/develop/get-started/faq/) về fork và copy-on-write.

## Sau crash test

- Chỉ dùng `kill -9` với instance demo độc lập.
- Khởi động lại bằng đúng config, port và `dir` đã dùng trước sự cố.
- Đếm key, kiểm tra `rdb_last_bgsave_status`, `aof_last_write_status` và lưu kết quả thực đo.

- Ghi kết quả vào tài liệu demo và slides; báo cáo riêng không còn là sản phẩm nộp theo cập nhật nhóm.
- `kill -9` process Redis không làm mất page cache kernel. AOF phục hồi đủ key là kết quả hợp lệ, không phải bằng chứng fsync everysec bảo đảm không mất dữ liệu khi mất điện.
- Lưu PID bằng `redis-cli -p <port> INFO server`, đối chiếu port/process ngay trước crash. Không dùng PID đã lưu từ lần start trước.
- Khi test lại từ đầu, reset cả dữ liệu RAM và trạng thái persistence theo [commands.md](commands.md). Không xóa AOF/snapshot trong lúc server vẫn ghi.
