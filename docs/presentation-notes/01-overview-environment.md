# Trình bày tổng quan và môi trường

Thời lượng đề xuất: **5 phút, gồm video môi trường khoảng 90 giây**, trong seminar 30–45 phút của nhóm. Tài liệu này dùng để tập nói và chuẩn bị recording; slides được làm sau.

Nghiên cứu đầy đủ nằm trong [theory/01-redis-overview.md](../../theory/01-redis-overview.md). Phần mở đầu chỉ cần giải thích Redis dùng để làm gì và nhóm sẽ minh họa bằng những demo nào. Thuật toán, lệnh chi tiết và số liệu dành cho chủ từng demo.

## Nội dung nói

| Thời gian | Ý chính |
|---|---|
| 0:00–0:45 | Redis là kho dữ liệu có cấu trúc, phục vụ dữ liệu chủ yếu từ RAM. Giới thiệu một ví dụ cache kết quả đọc lặp lại. |
| 0:45–1:30 | Hit là có dữ liệu trong cache; miss cần lấy từ nguồn. Cache giảm công việc lặp nhưng cần xử lý dữ liệu cũ. Chưa đi sâu luồng Cache-Aside hoặc cách đo. |
| 1:30–2:00 | Nêu ngắn gọn cache, session, leaderboard; RAM có giới hạn và cần chọn cách phục hồi phù hợp. |
| 2:00–2:30 | Giới thiệu bốn demo: cấu trúc dữ liệu/TTL, Cache-Aside, eviction, persistence. Mỗi demo sẽ giải thích cơ chế và kết quả riêng. |
| 2:30–3:00 | Môi trường chung: mỗi demo có process, port, thư mục và file config riêng; các thành viên dùng cùng cấu hình để tái lập. |
| 3:00–4:30 | Video môi trường: cấu hình VM, phiên bản, PONG, cách ly giữa hai instance. Chỉ phát đoạn đã chọn trong khung 90 giây. |
| 4:30–5:00 | Chốt môi trường đã sẵn sàng cho các demo; chuyển sang phần cấu trúc dữ liệu. |

Không đọc hết tài liệu nghiên cứu. Phần này không cần trình bày thao tác từng kiểu dữ liệu, công thức latency, thuật toán eviction hoặc cơ chế RDB/AOF. Kết quả kiểm tra hạ tầng không thay thế kết quả workload của từng demo.

## Chuẩn bị recording

- Hoàn tất cài đặt, tải dependency và chạy thử trước khi quay.
- Start đủ năm instance; `bash linux/check.sh` trả `PASS`.
- Terminal nền sáng, chữ lớn, khung hình 16:9; thử đọc ở kích thước trình chiếu.
- Chuẩn bị ảnh settings RAM/CPU và output phiên bản của VM dùng trình diễn.
- Không dành video chính cho thời gian chờ apt hoặc nhập mật khẩu.

## Shot list môi trường, khoảng 90 giây

| Thời gian | Hình/lệnh | Kết quả cần thấy |
|---|---|---|
| 0–15 giây | Settings VM và `cat /etc/os-release` | Allocation RAM/CPU và OS thực tế |
| 15–30 giây | `redis-server --version`, `redis-cli -p 6379 PING` | Phiên bản và `PONG` |
| 30–50 giây | Phần port và kết luận của `bash linux/check.sh` | Các port hoạt động, `PASS` |
| 50–80 giây | Probe cách ly dưới đây | 6383 có key, 6384 không có |
| 80–90 giây | Bảng port/config trong hướng dẫn | Mỗi demo dùng instance riêng |

Chạy probe trước khi lấy số liệu demo, khi hai instance chưa có key `env:probe`:

```bash
redis-cli -p 6383 SET env:probe instance-6383 EX 60
redis-cli -p 6383 GET env:probe
redis-cli -p 6384 GET env:probe
redis-cli -p 6383 DEL env:probe
```

Kỳ vọng: `OK`, `instance-6383`, `(nil)`, `1`. Với output không tương tác, nil có thể là dòng trống. Probe chỉ minh họa cách ly, không phải bài đo hiệu năng.

## Chọn footage và kiểm tra trước trình bày

Recording và ảnh đã có được mô tả trong [chỉ mục minh chứng](../screenshots/00-environment/vmware-2026-10-20/README.md). Bản gốc dài 8:26.8; chọn đoạn phù hợp thay vì phát toàn bộ. Có thể thuyết minh trực tiếp hoặc thêm caption; giữ output đủ lâu để đọc và không cắt làm sai ý kết quả.

Trước buổi seminar: thử playback trên máy trình chiếu, kiểm tra chữ/âm thanh, giữ bản video offline và tập toàn bộ phần nói cùng video trong 5 phút.
