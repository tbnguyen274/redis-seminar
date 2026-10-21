# Redis Seminar

Repository phục vụ seminar **Redis In-Memory Data Store** trên một máy ảo Linux tối thiểu **512 MB RAM**. Nội dung tập trung vào vai trò của cache, mô hình Cache-Aside, kiến trúc xử lý lệnh của Redis, cơ chế persistence RDB/AOF và các chính sách eviction khi bộ nhớ đầy.

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
├── docs/
│   ├── theory/                 # Tài liệu lý thuyết
│   ├── screenshots/            # Ảnh minh chứng cài đặt và demo
│   └── presentation-notes/     # Kịch bản và ghi chú thuyết trình
├── linux/
│   ├── setup.sh                # Cài đặt Redis trên Ubuntu/Debian
│   ├── commands.md             # Lệnh kiểm tra và vận hành cơ bản
│   └── troubleshooting.md      # Checklist xử lý sự cố
├── redis/
│   ├── redis-rdb.conf          # Template RDB cho script demo 04
│   ├── redis-aof.conf          # Template AOF cho script demo 04
│   ├── redis-eviction.conf     # Cấu hình maxmemory và allkeys-lru
│   ├── redis-data-structures.conf # Instance riêng cho demo 01
│   └── redis-cache-aside.conf  # Instance riêng cho demo 02
├── demos/
│   ├── 01-data-structures/     # String, List, Hash, Sorted Set, TTL
│   ├── 02-cache-aside/         # Mô phỏng DB chậm và đo miss/hit
│   ├── 03-eviction/            # Ghi dữ liệu vượt maxmemory
│   └── 04-persistence-crash/   # kill -9 và kiểm tra dữ liệu phục hồi
└── report/
    └── seminar.md              # Khung báo cáo seminar
```

File [`de_tai_seminar.md`](de_tai_seminar.md) là đề bài gốc dùng để đối chiếu phạm vi và tiêu chí demo.

## Luồng hoạt động và demo

1. **Chuẩn bị môi trường**
   - Tạo VM Linux 512 MB RAM.
   - Chạy `sudo bash linux/setup.sh` để cài Redis và công cụ dòng lệnh.
   - Xác nhận dịch vụ bằng `redis-cli ping` (kết quả mong đợi: `PONG`).
   - Tạo các thư mục dữ liệu bằng lệnh trong `linux/commands.md` trước khi chạy các instance riêng.

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
   - Bản Python cần virtualenv và dependency `redis-py` theo `demos/04-persistence-crash/requirements.txt`; cài theo README của demo, không dùng `sudo pip`.
   - Chạy script theo [hướng dẫn demo 04](demos/04-persistence-crash/README.md). Script tự khởi động hai instance từ template `redis/redis-rdb.conf` và `redis/redis-aof.conf`; không chạy trực tiếp hai template.
   - Ghi baseline, tạo checkpoint RDB bằng `BGSAVE`, rồi ghi delta cho cả RDB và AOF.
   - Dùng `SIGKILL` để mô phỏng Redis process crash, sau đó restart và kiểm chứng từng key/value. Đây không phải thử nghiệm cắt nguồn máy.
   - Mỗi lần chạy lưu CSV riêng và dữ liệu trial tại `demos/04-persistence-crash/results/run-<UTC>-<id>/`.
   - Tổng hợp số liệu thực tế vào [báo cáo](demos/04-persistence-crash/report.md); không suy ra AOF luôn mất chính xác một giây dữ liệu.

## Nguyên tắc chạy demo

- Dùng instance/port và thư mục dữ liệu riêng cho từng thử nghiệm để tránh trộn dữ liệu.
- Phân bổ port: RDB `6380`, AOF `6381`, Eviction `6382`, Data Structures `6383`, Cache-Aside `6384`.
- Không chạy `kill -9` trên Redis đang chứa dữ liệu quan trọng.
- Chụp màn hình lệnh, cấu hình, số liệu thời gian, `INFO stats` và kết quả sau restart vào `docs/screenshots/`.
- Ghi rõ phiên bản hệ điều hành, Redis và cấu hình thực tế trong báo cáo để kết quả có thể tái lập.

## Trạng thái

Repository đã có cấu trúc, tài liệu và demo persistence crash kèm unit tests. Các demo còn lại tiếp tục được bổ sung trong thư mục tương ứng.
