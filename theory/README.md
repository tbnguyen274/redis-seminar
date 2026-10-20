# Tài liệu nghiên cứu Redis

Nộp **slides** qua Moodle, không yêu cầu báo cáo. Seminar dài **30–45 phút/nhóm**. Thư mục này giữ nghiên cứu, nguồn và giải thích chi tiết để học và chọn lọc đưa lên slides.

| File dự kiến | Phạm vi | Người phụ trách theo bảng tham khảo |
|---|---|---|
| [01-redis-overview.md](01-redis-overview.md) | Redis, caching, use case, giới hạn, tổng quan môi trường | Nam Anh |
| `02-data-structures.md` | String, List, Hash, Sorted Set, TTL | Viết Toàn |
| `03-cache-aside.md` | Hit/miss, invalidation, đo thời gian, rủi ro cache | Quốc Thắng |
| `04-eviction.md` | maxmemory, các policy, approximate LRU | Mạnh Tường |
| `05-persistence.md` | Event loop, xử lý lệnh, RDB/AOF, crash recovery | Thái Bảo |

Phân công cần được các thành viên xác nhận. File của phần khác do chủ phần bổ sung; tên trong bảng là quy ước, không khẳng định các file đã hoàn thành.

Mỗi phần nên có: khái niệm và ví dụ; cơ chế và đánh đổi; liên hệ demo; kết quả thực nghiệm có môi trường đo; câu hỏi thường gặp; nguồn chính thức và ngày tra cứu. Phân biệt số liệu minh họa với số liệu đo thật. Ghi phiên bản khi tính năng phụ thuộc phiên bản Redis.

Tài liệu nghiên cứu có thể dài; khi trình bày, chọn ý chính theo thời lượng từng phần. Tổng quan và môi trường dự kiến khoảng 5 phút gồm video 90 giây; chỉ giới thiệu các chủ đề thuộc demo sau, tránh trình bày lặp. Lý thuyết và demo của cả nhóm nằm trong khung 30–45 phút.

`report/seminar.md` là khung cũ, không dùng làm nguồn lý thuyết hiện hành. `docs/theory/` là vị trí cũ; nội dung mới đặt tại `theory/`.
