# Redis Seminar

Repository phục vụ seminar **Redis In-Memory Data Store** trên một máy ảo Linux tối thiểu **512 MB RAM**. Nội dung tập trung vào vai trò của cache, mô hình Cache-Aside, kiến trúc xử lý lệnh của Redis, cơ chế persistence RDB/AOF và các chính sách eviction khi bộ nhớ đầy.

## Yêu cầu làm việc hiện tại

- Nộp **slides** qua Moodle; không cần nộp báo cáo riêng. Seminar **30–45 phút/nhóm**.
- Nghiên cứu và nguồn đặt ở [`theory/`](theory/README.md), rồi chọn lọc đưa lên slides. `report/seminar.md` là khung cũ, không dùng làm lý thuyết hiện hành.
- Mỗi chủ demo phụ trách cả code, lý thuyết và trình bày phần mình. Người phụ trách môi trường quản lý hạ tầng và kiểm tra khả năng tái lập các demo.
- Quay demo trước, terminal nền sáng và chữ lớn; kiểm tra video ở kích thước trình chiếu.
- Làm trên branch riêng và tạo PR để nhóm review. Các phân công trong sheet là tham khảo, cần thành viên xác nhận.

Bắt đầu với [hướng dẫn môi trường](linux/commands.md), [nghiên cứu overview](theory/01-redis-overview.md), [checklist chất lượng](docs/demo-quality-checklist.md) và [kịch bản nói/quay](docs/presentation-notes/01-overview-environment.md). [Kết quả kiểm tra](docs/environment-verification.md) phân biệt rehearsal WSL và VM cuối.

Đã đối chiếu [minh chứng VMware ngày 20/10/2026](docs/screenshots/00-environment/vmware-2026-10-20/README.md): VM 512 MB/2 CPUs, Ubuntu 26.04.1, Redis 8.0.5, Python 3.14.4; checker, cách ly, TTL và normal restart đạt với swap bật. Log còn cảnh báo overcommit/PID file; workload cuối và crash-loss chưa được xác minh.

Slides phần tổng quan và môi trường sẽ được chuẩn bị ở giai đoạn sau; hiện chưa đưa file slides lên repo.

## Mục tiêu

- Trình bày cách Redis hỗ trợ tăng tốc ứng dụng bằng cache.
- Thực hành String, List, Hash, Sorted Set và TTL.
- Đo sự khác biệt giữa Cache Miss và Cache Hit trong mô hình Cache-Aside.
- Quan sát Redis tự loại bỏ key với `allkeys-lru` khi chạm giới hạn bộ nhớ.
- So sánh mức độ mất dữ liệu sau sự cố giữa RDB và AOF (`appendfsync everysec`).

## Cấu trúc repository

```text
redis-seminar/
├── README.md
├── theory/                      # Nghiên cứu hiện hành và nguồn tham khảo
├── docs/
│   ├── theory/                 # Vị trí cũ, nội dung mới ở theory/
│   ├── demo-quality-checklist.md # Tiêu chí review và việc còn lại
│   ├── environment-verification.md # Kết quả kiểm tra thực tế
│   ├── screenshots/            # Ảnh minh chứng cài đặt và demo
│   └── presentation-notes/     # Kịch bản và ghi chú thuyết trình
├── linux/
│   ├── setup.sh                # Cài đặt Redis trên Ubuntu/Debian
│   ├── check.sh                # Kiểm tra service, port và config, không sửa dữ liệu
│   ├── commands.md             # Lệnh kiểm tra và vận hành cơ bản
│   └── troubleshooting.md      # Checklist xử lý sự cố
├── redis/
│   ├── redis-rdb.conf          # Cấu hình thử nghiệm RDB
│   ├── redis-aof.conf          # Cấu hình thử nghiệm AOF
│   ├── redis-eviction.conf     # Cấu hình maxmemory và allkeys-lru
│   ├── redis-data-structures.conf # Instance riêng cho demo 01
│   └── redis-cache-aside.conf  # Instance riêng cho demo 02
├── demos/
│   ├── 01-data-structures/     # String, List, Hash, Sorted Set, TTL
│   ├── 02-cache-aside/         # Mô phỏng DB chậm và đo miss/hit
│   ├── 03-eviction/            # Ghi dữ liệu vượt maxmemory
│   └── 04-persistence-crash/   # kill -9 và kiểm tra dữ liệu phục hồi
└── report/
    └── seminar.md              # Khung cũ, không phải sản phẩm nộp hiện tại
```

File [`de_tai_seminar.md`](de_tai_seminar.md) là đề bài gốc dùng để đối chiếu phạm vi và tiêu chí demo.

## Luồng hoạt động và demo

1. **Chuẩn bị môi trường**
   - Tạo VM Linux 512 MB RAM.
   - Chạy `sudo bash linux/setup.sh` để cài Redis và công cụ dòng lệnh.
   - Xác nhận dịch vụ bằng `redis-cli ping` (kết quả mong đợi: `PONG`).
   - Setup tạo năm thư mục dữ liệu; sau reboot, tạo lại nếu bị dọn theo `linux/commands.md`.
   - Sau khi start đủ năm instance, chạy `bash linux/check.sh` để kiểm tra cấu hình thực tế.

2. **Demo 01 - Cấu trúc dữ liệu và TTL**
   - Khởi động Redis bằng `redis/redis-data-structures.conf` trên port `6383`.
   - Thực hành String, List, Hash và Sorted Set.
   - Dùng Sorted Set để tạo bảng xếp hạng.
   - Gán TTL, quan sát key tồn tại rồi tự hết hạn.

3. **Demo 02 - Cache-Aside**
   - Khởi động Redis bằng `redis/redis-cache-aside.conf` trên port `6384`.
   - Ứng dụng tìm dữ liệu trong Redis trước.
   - Nếu Cache Miss, ứng dụng mô phỏng truy vấn cơ sở dữ liệu khoảng 300 ms, sau đó ghi kết quả vào Redis.
   - Nếu Cache Hit, ứng dụng trả kết quả trực tiếp từ Redis.
   - Ghi lại thời gian của lần đầu và các lần sau để so sánh.

```text
Client -> Application -> Redis
                         | hit  -> trả dữ liệu
                         | miss
                         v
                    Slow database (~300 ms)
                         |
                         +-> ghi cache có TTL -> trả dữ liệu
```

4. **Demo 03 - Eviction**
   - Khởi động Redis bằng `redis/redis-eviction.conf` với giới hạn nhỏ và `allkeys-lru`.
   - Ghi dữ liệu cho đến khi vượt `maxmemory`.
   - Theo dõi `evicted_keys` và chứng minh các key ít được sử dụng bị loại bỏ.

5. **Demo 04 - Persistence và sự cố**
   - Chạy cùng một kịch bản ghi dữ liệu lần lượt với cấu hình RDB và AOF.
   - Dùng `kill -9` để mô phỏng process Redis bị dừng đột ngột sau khi ghi; đây không phải thử nghiệm mất điện VM/host.
   - Khởi động lại Redis, đếm số key còn lại và so sánh mức mất dữ liệu.
   - Với AOF, sử dụng `appendfsync everysec`; mức mất dữ liệu kỳ vọng thường nhỏ hơn RDB thuần túy.

## Nguyên tắc chạy demo

- Dùng instance/port và thư mục dữ liệu riêng cho từng thử nghiệm để tránh trộn dữ liệu.
- Phân bổ port: RDB `6380`, AOF `6381`, Eviction `6382`, Data Structures `6383`, Cache-Aside `6384`.
- Không chạy `kill -9` trên Redis đang chứa dữ liệu quan trọng.
- Chụp màn hình lệnh, cấu hình, số liệu thời gian, `INFO stats` và kết quả sau restart vào `docs/screenshots/`.
- Ghi rõ phiên bản hệ điều hành, Redis và cấu hình thực tế trong minh chứng/tài liệu demo và slides để kết quả có thể tái lập.

## Trạng thái

Repository có cấu hình mẫu và tài liệu chuẩn bị môi trường. Nghiên cứu overview nằm trong `theory/`; mã nguồn chi tiết và lý thuyết của từng demo do chủ phần bổ sung. Việc server/config chạy được chưa chứng minh bốn demo ứng dụng đã hoàn thành. Xem checklist và verification để biết phần đã kiểm tra và phần còn lại.
