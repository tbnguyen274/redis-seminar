# Kết quả kiểm tra môi trường

## Phạm vi

Đã kiểm tra môi trường bằng lệnh thực tế ngày **20/10/2026**, khoảng **09:47 giờ Việt Nam**. Log dùng UTC (02:47). Đây là **WSL2 rehearsal**, không phải bằng chứng VM VMware 512 MB. Không chạy VMware, đổi RAM toàn máy hoặc đo mất dữ liệu bằng crash test trong lần chuẩn bị này.

Log thô: [wsl-rehearsal.txt](screenshots/00-environment/wsl-rehearsal.txt).

## Môi trường thực đo

| Thành phần | Giá trị |
|---|---|
| Distro | Ubuntu 24.04.5 LTS, WSL2, distro `RedisSeminar` |
| Kernel | `6.18.33.2-microsoft-standard-WSL2` |
| PID 1 | systemd |
| Redis | 7.0.15, 64-bit, jemalloc |
| Gói redis-server/redis-tools | `5:7.0.15-1ubuntu0.24.04.5` |
| Python | 3.12.3 |
| CPU guest thấy | 16 logical CPUs |
| RAM/swap guest thấy | Khoảng 7.6 GiB RAM, 2.0 GiB swap |
| Bộ nhớ yêu cầu cuối | VM 512 MB, **chưa kiểm tra** |

RAM/CPU WSL phản ánh cấu hình rehearsal, không phải cấu hình đề bài. Gói apt có thể đổi theo thời điểm; ghi version hoặc giữ snapshot để so sánh giữa thành viên.

## Kiểm tra đã đạt

- Setup chạy hoàn tất bằng quyền root với `SUDO_USER=kyrie`, rồi chạy lại thành công. Đây là cách gọi không tương tác trong môi trường kiểm tra; người dùng Linux bình thường dùng `sudo bash linux/setup.sh`.
- Shell scripts qua `bash -n`; gọi setup không có quyền root bị từ chối trước khi cài đặt.
- Service mặc định active, enabled, port 6379 trả PONG.
- Năm config gốc start được dưới user thường, có override `--daemonize yes` và logfile riêng cho rehearsal.
- Port 6380–6384 đều trả PONG, process ID khác nhau, bind loopback.
- `dir` đúng từng bài; RDB tắt AOF; AOF bật everysec và tắt snapshot; eviction có maxmemory 10485760/allkeys-lru; các instance ephemeral tắt persistence.
- Key ghi ở 6383 không xuất hiện ở 6384; key kiểm tra TTL hết hạn.
- RDB normal restart nạp lại key đã SAVE; FLUSHALL + SAVE rồi restart giữ dataset rỗng.
- AOF normal restart nạp lại key; FLUSHALL rồi normal shutdown/restart giữ dataset rỗng. Xác nhận multi-part AOF trong `appendonlydir`.
- Stop/start 6382–6384 xóa dữ liệu ephemeral.
- Checker trả lỗi khi policy eviction bị đổi sai; trả lỗi khi thiếu instance; sau phục hồi chạy lại PASS.
- `python3 -m venv` thành công, pip 24.0 có sẵn trong venv.
- Năm test instance đã shutdown sau khi kiểm tra; service mặc định được giữ enabled. Khi mở lại WSL, systemd có thể start lại service, còn instance demo cần start tay.

## Vấn đề tìm thấy và xử lý

1. Checkout Windows có CRLF khiến Bash báo `pipefail\r`. Đã đổi shell scripts về LF và thêm `.gitattributes` cho shell/config.
2. WSL dừng/khởi động lại có thể dọn `/tmp`. Có lượt start thất bại vì thiếu data dir; tạo lại directory bằng setup rồi kiểm tra trong cùng lượt chạy đã thành công. Hướng dẫn có bước phục hồi directory sau reboot.

## Chưa thể đánh dấu hoàn thành

- [ ] Chạy lại trên VMware/VM 512 MB thực tế, kiểm tra ổn định với dataset cuối của nhóm.
- [ ] Ảnh settings VMware, screenshot terminal và video light mode của môi trường cuối.
- [ ] Cài/chạy requirements ứng dụng của các thành viên khi có script hoàn chỉnh.
- [ ] Đo latency Cache-Aside, memory eviction và bảng mất dữ liệu RDB/AOF của demo thật.
- [ ] Ghép và thử playback video trong deck toàn nhóm.

Chỉ số key/latency/memory-loss của bốn demo chưa được điền. Kiểm tra hạ tầng và normal restart không thay thế experiment của từng chủ demo.

## Chạy lại kiểm tra

Theo [commands.md](../linux/commands.md): chạy setup; start cả năm instance; chạy `set -o pipefail` và `bash linux/check.sh | tee <file-log>`; kiểm tra cách ly; kiểm tra stop/reset/restart trên dữ liệu bỏ được. Script check là chỉ đọc; phần reset là thao tác riêng, cần đúng port.
