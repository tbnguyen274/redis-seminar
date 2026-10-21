# Redis Seminar

Môi trường và tài liệu dùng chung cho seminar Redis, gồm bốn demo: cấu trúc dữ liệu/TTL, Cache-Aside, eviction và persistence.

## Bắt đầu từ đâu?

> [!NOTE]
> Lần đầu cài Ubuntu có thể sử dụng RAM cao hơn (VD. 2GB) để tăng tốc quá trình cài, sau đó hạ xuống 512MB

1. Chuẩn bị Ubuntu Server **512 MB RAM**.
2. Clone repo và chạy `sudo bash linux/setup.sh` một lần trên mỗi VM để cài Redis, Python/venv và tạo thư mục dữ liệu.
3. Khởi động Redis bằng file cấu hình tương ứng với demo, rồi kết nối đúng port. Setup không tự khởi động các instance demo.
4. Viết code trong `demos/`, nghiên cứu trong `theory/`, làm trên branch riêng và tạo PR để nhóm review.

Lệnh cụ thể: **[linux/commands.md](linux/commands.md)**. Khi gặp lỗi: [linux/troubleshooting.md](linux/troubleshooting.md).

## Làm độc lập và đồng nhất môi trường

Mỗi thành viên có thể phát triển trên VM riêng, không cần đợi các demo khác. Dùng cùng commit repo và các file `redis/*.conf` để thống nhất cấu hình. Setup dùng gói apt của distro, **không khóa phiên bản**; để đồng nhất cả phiên bản, dùng cùng image/snapshot Ubuntu và ghi lại phiên bản thực tế khi bàn giao.

Nếu dùng chung một VM, thống nhất tài khoản vận hành và người quản lý từng instance. Cùng port là cùng dữ liệu: không start thêm process, reset hoặc đổi cấu hình instance mà người khác đang dùng. Các instance bind `127.0.0.1`; chạy ứng dụng demo trong cùng guest.

| Demo | File cấu hình | Port | Code |
|---|---|---:|---|
| Cấu trúc dữ liệu và TTL | [redis-data-structures.conf](redis/redis-data-structures.conf) | 6383 | `demos/01-data-structures/` |
| Cache-Aside | [redis-cache-aside.conf](redis/redis-cache-aside.conf) | 6384 | `demos/02-cache-aside/` |
| Eviction | [redis-eviction.conf](redis/redis-eviction.conf) | 6382 | `demos/03-eviction/` |
| Persistence — RDB | [redis-rdb.conf](redis/redis-rdb.conf) | 6380 | `demos/04-persistence-crash/` |
| Persistence — AOF | [redis-aof.conf](redis/redis-aof.conf) | 6381 | `demos/04-persistence-crash/` |

Port **6379** là service mặc định do setup bật, quản lý riêng với các instance demo. Muốn đổi cấu hình, sửa file tương ứng trong `redis/`, dừng đúng instance và khởi động lại bằng file đó. Cách kiểm tra cấu hình và phối hợp thay đổi nằm trong [commands.md](linux/commands.md#4-thay-đổi-cấu-hình).

Khi kiểm tra tích hợp, khởi động đủ năm instance rồi chạy `bash linux/check.sh`; script cần cả service 6379 và các port 6380–6384. Khi làm riêng một demo, chỉ cần kiểm tra port của demo đó.

## Tài liệu cần đọc

| Nhu cầu | Tài liệu |
|---|---|
| Cài đặt, start/stop/reset, sửa cấu hình | [linux/commands.md](linux/commands.md) |
| Chạy demo setup theo thứ tự recording, có giải thích và output kỳ vọng | [linux/environment-demo.md](linux/environment-demo.md) |
| Xử lý lỗi | [linux/troubleshooting.md](linux/troubleshooting.md) |
| Nghiên cứu lý thuyết và nguồn tham khảo | [theory/README.md](theory/README.md) |
| Nội dung nói tổng quan và quay môi trường, khoảng 5 phút | [Ghi chú trình bày](docs/presentation-notes/01-overview-environment.md) |
| Review và bàn giao demo | [Checklist chất lượng](docs/demo-quality-checklist.md) |
| Ảnh/log của giai đoạn setup môi trường | [docs/screenshots/00-environment-setup/](docs/screenshots/00-environment-setup/README.md) |
| Kết quả thử nghiệm và phạm vi đã kiểm tra | [Kiểm tra môi trường](docs/environment-verification.md) |
| Đề bài gốc | [de_tai_seminar.md](de_tai_seminar.md) |

## Phạm vi và bàn giao

- Seminar **30–45 phút/nhóm**, nộp **slides** qua Moodle; không cần báo cáo riêng.
- Mỗi chủ demo chuẩn bị code, lý thuyết, kết quả thực đo và video. Theory có thể chi tiết; nội dung nói chọn lọc theo thời lượng. Phần tổng quan chỉ giới thiệu các chủ đề sẽ được đào sâu ở từng demo.
- README từng demo cần có dependency, lệnh chạy, output kỳ vọng và cách reset. Hiện các thư mục demo mới là chỗ để bổ sung code.
- Quay demo trước với terminal nền sáng, chữ lớn và kiểm tra playback trước buổi seminar.
- `report/seminar.md` là khung cũ; nội dung nghiên cứu hiện hành đặt ở `theory/`. Slides được chuẩn bị ở giai đoạn sau.

Hạ tầng đã có [minh chứng VMware 512 MB](docs/screenshots/00-environment-setup/vmware-2026-10-20/README.md). Kiểm tra kết nối/cấu hình và normal restart chưa thay thế việc chạy bốn workload demo cuối.
