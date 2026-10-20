# Kết quả kiểm tra môi trường

## Kết luận hiện tại: VMware 512 MB

Đã đối chiếu ảnh, recording và log người dùng chạy ngày **20/10/2026**, phiên **07:55:53–08:04:24 UTC** (14:55:53–15:04:24 Việt Nam). Ảnh settings xác nhận VM **512 MB RAM, 2 processors**. Setup, checker, cách ly, TTL và normal restart đạt trong phạm vi dưới đây. Đây là kiểm tra hạ tầng với probe nhỏ; chưa chứng minh bốn workload cuối của seminar chạy ổn định ở mức RAM này.

Minh chứng và nguồn: [VMware 2026-10-20](screenshots/00-environment/vmware-2026-10-20/README.md). Kết quả WSL trước đó được giữ ở phần lịch sử cuối trang; không dùng phiên bản WSL thay cho VM cuối.

## Môi trường VMware thực đo

| Thành phần | Giá trị và nguồn |
|---|---|
| Hypervisor | VMware Workstation Pro **26H1u1**, người dùng xác nhận; guest/kernel nhận diện VMware |
| Phân bổ VM | **512 MB RAM, 2 processors**, virtual disk 20 GB, NAT; ảnh settings |
| Guest OS | Ubuntu **26.04.1 LTS** (Resolute Raccoon), x86_64 |
| Kernel | `7.0.0-38-generic` |
| Service manager | systemd; service Redis enabled và active |
| Redis runtime | **8.0.5**, 64-bit, jemalloc 5.3.0 |
| Gói Redis apt | redis-server/redis-tools `5:8.0.5-1ubuntu0.1` |
| Python runtime / pip | **3.14.4** / **25.1.1** trong venv |
| Gói `python3` meta-package | `3.14.3-0ubuntu2`; khác số phiên bản interpreter, không phải lỗi |
| CPU guest thấy | **2 logical CPUs**, Intel Core i5-12500H được guest báo cáo |
| RAM guest thấy | `free -h`: **404 MiB**; fastfetch: khoảng 404.61 MiB, không thay thế ảnh allocation 512 MB |
| Swap | Khoảng **1.6 GiB**, dùng **98 MiB** tại initial check và **107 MiB** tại final check |
| Available memory | **143 MiB** initial, **157 MiB** final; đây là available, không phải cột free |
| Commit / branch | `2cd27a98b251231f1bc5e524451ce3ead546fcb4` / `feat/environment-prep` |

Kết quả được đo với **swap bật**; không mô tả là thử nghiệm không swap. VM disk 20 GB là dung lượng thiết bị ảo; root filesystem guest báo khoảng 9.75 GiB. Không suy ra hai số phải bằng nhau.

## Các kiểm tra VMware có minh chứng

| Kiểm tra | Kết quả quan sát |
|---|---|
| Setup | `SETUP_EXIT=0`, PONG và phiên bản ở cuối setup.txt |
| Shell syntax | Session ghi `SHELL_SYNTAX_EXIT=0` sau lệnh `bash -n linux/setup.sh linux/check.sh`; lệnh này không chứng minh Bash đã parse cả hai file, xem lưu ý dưới bảng |
| Service mặc định | enabled, active, port 6379 PONG |
| Initial checker | **PASS**, `CHECK_EXIT=0`, 07:59:44 UTC |
| Sáu instance | 6379–6384 PONG, PID khác nhau, bind loopback; directory và các setting được checker kiểm tra khớp |
| Cách ly | SET/GET ở 6383 trả `vm-test`; EXISTS cùng key ở 6384 trả 0 |
| TTL | Sau SET EX 5, TTL=5; sau chờ 6 giây, EXISTS=0 và TTL=-2 |
| RDB normal restart | SAVE thành công, SHUTDOWN/start lại 6380, GET trả `rdb-ok`; log nạp snapshot có 1 key |
| AOF normal restart | SHUTDOWN/start lại 6381, GET trả `aof-ok`; log nạp multi-part AOF |
| Ephemeral restart | 6383 được ghi `temporary`, SHUTDOWN/start lại, EXISTS=0 |
| Cleanup probe | DEL ở 6380/6381 trả 1; RDB SAVE sau DEL trả OK |
| Python venv | `VENV_EXIT=0`, Python 3.14.4 và pip 25.1.1 |
| Final checker | **PASS**, `FINAL_CHECK_EXIT=0`, 08:03:30 UTC |
| Kết thúc phiên | Session ghi SHUTDOWN 6380–6384, sau đó COMMAND_EXIT_CODE=0; không có PING đối chứng sau cleanup |

`bash -n script1 script2` chỉ parse script đầu; script sau là argument. Hướng dẫn đã được sửa thành hai lệnh riêng. Việc `linux/check.sh` thực sự chạy và trả PASS chứng minh script đó thực thi được trong phiên này, nhưng không gọi output trên là hai lượt syntax check độc lập.

Setup chỉ có **một lượt đầy đủ được lưu**; service journal có thêm restart không đủ chứng minh repeat setup. VMware chưa có negative test sai policy/thiếu instance, chưa có kiểm tra non-root rejection hoặc restart/reset riêng cho 6382/6384. Các bài đó từng đạt trên WSL, không tự chuyển thành kết quả VMware.

## Giới hạn kiểm tra

1. **Memory và swap:** initial/final check có swap sử dụng; chưa có resource profile của workload cuối. Không tìm thấy `oom-kill`, `Out of memory` hoặc `Killed process` trong kernel log được cung cấp; điều này chỉ áp dụng phạm vi log đó.
2. **Phạm vi persistence:** normal shutdown flush/save dữ liệu; chưa có `kill -9`, VM power-off hoặc đo mất dữ liệu. `rdb-ok` và `aof-ok` không phải bảng crash-loss.

## Recording và trạng thái tài liệu

Đã có tám ảnh, archive log và video **8 phút 26.8 giây**, H.264 1920×1080/60 fps. Đã xem các frame mẫu trên toàn timeline: terminal nền sáng, chữ đọc được ở kích thước gốc. AAC có trong file nhưng đo mean/max -91 dB, thực tế không có lời dẫn nghe được; có thể thuyết minh trực tiếp. Video vẫn là bản ghi đầy đủ có đoạn cài package/chờ, chưa cắt thành đoạn khoảng 90 giây. Xem [chỉ mục video và ảnh](screenshots/00-environment/vmware-2026-10-20/README.md).

Theo yêu cầu mới nhất, **chưa làm/cập nhật/nộp slides**. File slides đã được gỡ khỏi branch remote; bản local giữ riêng cho giai đoạn sau. Video gốc giữ ngoài Git; chưa ghép hoặc kiểm tra playback trong deck/máy chiếu.

## Việc còn cần để hoàn tất

- [ ] Nếu muốn khẳng định tái lập sau reboot/repeat setup: cung cấp log đúng các lượt đó; hiện chưa có.
- [ ] Chủ từng demo cung cấp script/requirements và log workload cuối trên VM 512 MB; đo Cache-Aside, eviction và controlled crash-loss riêng.
- [ ] Biên tập đoạn môi trường theo thời lượng nhóm; chuẩn bị slides và playback ở giai đoạn sau.

Không cần chụp lại settings, versions, PONG, cách ly, TTL hoặc normal restart chỉ để thay thế minh chứng đã đủ ở trên.

## Lịch sử rehearsal WSL2

Phần sau ghi phạm vi của lần rehearsal trước VMware, giữ để đối chiếu; các câu “chưa kiểm tra VM” bên dưới chỉ nói về lần WSL đó.

### Phạm vi WSL

Đã kiểm tra môi trường bằng lệnh thực tế ngày **20/10/2026**, khoảng **09:47 giờ Việt Nam**. Log dùng UTC (02:47). Đây là **WSL2 rehearsal**, không phải bằng chứng VM VMware 512 MB. Không chạy VMware, đổi RAM toàn máy hoặc đo mất dữ liệu bằng crash test trong lần chuẩn bị này.

Log thô: [wsl-rehearsal.txt](screenshots/00-environment/wsl-rehearsal.txt).

### Môi trường WSL thực đo

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

### Kiểm tra WSL đã đạt

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

### Vấn đề WSL tìm thấy và xử lý

1. Checkout Windows có CRLF khiến Bash báo `pipefail\r`. Đã đổi shell scripts về LF và thêm `.gitattributes` cho shell/config.
2. WSL dừng/khởi động lại có thể dọn `/tmp`. Có lượt start thất bại vì thiếu data dir; tạo lại directory bằng setup rồi kiểm tra trong cùng lượt chạy đã thành công. Hướng dẫn có bước phục hồi directory sau reboot.

### Chạy lại kiểm tra

Theo [commands.md](../linux/commands.md): chạy setup; start cả năm instance; chạy `set -o pipefail` và `bash linux/check.sh | tee <file-log>`; kiểm tra cách ly; kiểm tra stop/reset/restart trên dữ liệu bỏ được. Script check là chỉ đọc; phần reset là thao tác riêng, cần đúng port.
