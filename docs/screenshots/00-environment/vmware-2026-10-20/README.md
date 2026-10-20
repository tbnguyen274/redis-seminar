# Minh chứng VMware ngày 20/10/2026

Minh chứng gồm recording, tám ảnh và archive log của lần chạy VMware. Commit chạy trong guest: `2cd27a98b251231f1bc5e524451ce3ead546fcb4`, branch `feat/environment-prep`.

## Nguồn và cách lưu

- [original-logs.tar.gz](original-logs.tar.gz) giữ nguyên byte của `redis-vm-evidence.tar.gz`; thư mục bên trong là `vm-20261020-075553/`.
- [source-manifest.json](source-manifest.json) ghi SHA256 của archive, video và từng ảnh, cùng tên file gốc.
- `logs/` là bản dễ đọc: đổi LF, bỏ khoảng trắng cuối dòng; [session-readable.txt](logs/session-readable.txt) bỏ thêm terminal control. Input có thể lặp do echo/redraw; dùng archive gốc khi cần đối chiếu nguyên bản.
- Recording gốc: `2026-10-20 14-56-09.mp4`. Video giữ ngoài Git; khi bàn giao cần chuyển file hoặc bổ sung liên kết lưu trữ chung của nhóm. Metadata nằm ở [video-metadata.json](video-metadata.json).
- Phiên bản **VMware Workstation Pro 26H1u1** theo xác nhận của người thực hiện. Ảnh settings và kernel log xác nhận VMware; chưa có ảnh About để đối chiếu phiên bản ứng dụng host.

## Chỉ mục ảnh

| Ảnh | Minh chứng |
|---|---|
| [01-vm-settings.png](screenshots/01-vm-settings.png) | VM có RAM 512 MB, 2 processors, virtual disk 20 GB, NAT |
| [02-os-and-commit.png](screenshots/02-os-and-commit.png) | Ubuntu 26.04.1 LTS, kernel 7.0.0-38-generic, VMware, commit/branch |
| [03-setup-versions.png](screenshots/03-setup-versions.png) | Setup kết thúc bằng PONG, Redis 8.0.5, Python 3.14.4 |
| [04-service.png](screenshots/04-service.png) | SETUP_EXIT=0, gói apt, service enabled/active và PONG |
| [05-ports.png](screenshots/05-ports.png) | Sáu port trả PONG, PID và RAM/swap thực đo |
| [06-config-pass.png](screenshots/06-config-pass.png) | Directory/persistence/eviction config và checker PASS |
| [07-isolation-ttl.png](screenshots/07-isolation-ttl.png) | 6383 đọc được probe, 6384 không có; TTL 5 rồi -2 |
| [08-normal-restart.png](screenshots/08-normal-restart.png) | SAVE, SHUTDOWN và start lại 6380/6381/6383; kết quả GET sau restart có trong session log |

## Log quan trọng

- [setup.txt](logs/setup.txt): cài đặt và kết thúc bình thường.
- [check.txt](logs/check.txt): PASS lúc **07:59:44 UTC** (14:59:44 Việt Nam).
- [check-final.txt](logs/check-final.txt): PASS lúc **08:03:30 UTC** (15:03:30 Việt Nam).
- [session-readable.txt](logs/session-readable.txt): SETUP_EXIT, SHELL_SYNTAX_EXIT, CHECK_EXIT, VENV_EXIT và FINAL_CHECK_EXIT đều 0; `rdb-ok`, `aof-ok`, ephemeral EXISTS=0; phiên kết thúc 08:04:24 UTC với COMMAND_EXIT_CODE=0.
- [redis-service.txt](logs/redis-service.txt): service mặc định start/restart thành công.
- [kernel.txt](logs/kernel.txt): VMware, swap; không tìm thấy thông báo OOM kill trong phạm vi log được cung cấp.
- [RDB](logs/instance-logs/rdb.log), [AOF](logs/instance-logs/aof.log), [eviction](logs/instance-logs/eviction.log), [data structures](logs/instance-logs/data-structures.log), [Cache-Aside](logs/instance-logs/cache-aside.log): startup và normal restart.

## Recording

MP4 H.264, **1920×1080, 60 fps, 506.833 giây** (8 phút 26.8 giây). Có AAC nhưng mức âm lượng mean/max đo bằng ffmpeg là **-91 dB**, thực tế không có lời dẫn nghe được. Có thể thuyết minh trực tiếp khi trình chiếu. Đã decode video để lấy mẫu toàn timeline và xem các frame đại diện; terminal nền sáng, command/output đọc được ở kích thước gốc. Chưa kiểm tra phát trong deck hoặc trên máy chiếu.

Đây là bản ghi đầy đủ, gồm thời gian cài package/chờ và thao tác thu log, chưa phải đoạn 90 giây dự kiến cho phần môi trường. Các vùng sau là mốc tham khảo gần đúng để biên tập về sau, không phải clip đã cắt:

| Vùng trong video | Nội dung |
|---|---|
| Khoảng 00:00–00:25 | OS, RAM/swap, branch và commit |
| Khoảng 01:45–02:50 | Setup kết thúc, versions, service và PONG |
| Khoảng 03:30–04:10 | Port/config và PASS |
| Khoảng 04:10–05:15 | Cách ly và TTL |
| Khoảng 05:15–06:45 | SAVE, normal shutdown/restart và GET phục hồi |
| Khoảng 06:45–08:27 | Python venv, final checker, log và cleanup |

Ảnh settings VM được cung cấp riêng; không suy ra rằng nó có trong recording. Bản gốc được giữ nguyên; chưa cắt video hoặc làm slides trong lần đối chiếu này.

Kết luận và việc còn lại: [environment-verification.md](../../../environment-verification.md).
