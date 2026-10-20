# Kịch bản phần Memory và Eviction (Demo 03)

Phạm vi: phần trình bày về Quản lý bộ nhớ và Cơ chế Eviction trong Redis, dự kiến khoảng **5–6 phút** trong seminar 30–45 phút của nhóm. Nguồn lý thuyết: [`docs/theory/03-eviction.md`](../theory/03-eviction.md).

## Lời dẫn theo slides

| Mốc thời gian | Nội dung trên slide | Lời giải thích gợi ý |
|---|---|---|
| 0:00–0:45 | Giới hạn bộ nhớ (`maxmemory`) | “Redis lưu trữ toàn bộ dữ liệu trên RAM. Khi bộ nhớ vật lý cạn kiệt, hệ điều hành Linux sẽ kích hoạt OOM Killer để tắt tiến trình. Tham số `maxmemory` giúp khống chế trần tài nguyên; trước mỗi lệnh ghi, Redis kiểm tra `used_memory > maxmemory` để quyết định thu hồi bộ nhớ hoặc từ chối ghi.” |
| 0:45–1:30 | Phân biệt Expiration vs Eviction | “Expiration xảy ra khi key hết thời gian sống (TTL), áp dụng cho key có cài đặt thời hạn. Eviction xảy ra khi RAM chạm ngưỡng `maxmemory`, buộc Redis phải trục xuất dữ liệu để nhường chỗ cho dữ liệu mới, ngay cả khi key đó chưa hết hạn hoặc không cài TTL.” |
| 1:30–2:15 | Các chính sách `maxmemory-policy` | “Có ba nhóm chính: `noeviction` giữ nguyên vẹn dữ liệu và từ chối lệnh ghi mới; `allkeys-lru` quét toàn bộ cơ sở dữ liệu để loại bỏ key ít dùng nhất, đây là lựa chọn chuẩn mực cho hệ thống Cache; `volatile-ttl` chỉ thu hồi trong tập key có TTL sắp hết hạn để bảo vệ dữ liệu tĩnh.” |
| 2:15–3:00 | Thuật toán Approximate LRU | “Redis không dùng True LRU (danh sách liên kết đôi) vì tốn thêm 16–24 bytes con trỏ cho mỗi key và gây tranh chấp bộ nhớ ở mỗi lệnh đọc `GET`. Thay vào đó, Redis dùng Approximate LRU: lưu timestamp 24-bit trong header object, lấy mẫu ngẫu nhiên 5 keys và đưa vào Eviction Pool để chọn key cũ nhất để xóa.” |
| 3:00–4:30 | Demo 03: Eviction thực tế | “Phần demo kiểm chứng instance port 6382 giới hạn 10MB. Khi nạp dữ liệu lớn vượt ngưỡng, các key nguội ít dùng bị loại bỏ (`EXISTS = 0`), trong khi các key nóng được truy cập liên tục vẫn được bảo toàn nguyên vẹn trong bộ nhớ (`EXISTS = 1`).” |
| 4:30–5:00 | Kết luận & Khuyến nghị production | “Khi triển khai thực tế, khuyến nghị đặt `maxmemory` ở mức 70–80% RAM vật lý (hoặc 50–60% nếu có bật RDB/AOF) để chừa tài nguyên cho bộ đệm mạng và cơ chế Copy-on-Write khi fork tiến trình con.” |

## Chuẩn bị trước khi record

- [ ] Instance port 6382 chạy độc lập với cấu hình `redis/redis-eviction.conf`.
- [ ] Chạy `bash test/test_demo_03.sh` đạt 9/9 PASS trước khi ghi hình.
- [ ] Terminal đặt giao diện nền sáng (Light mode), cỡ chữ lớn (20–24 pt) để dễ nhìn khi trình chiếu.
- [ ] Mở sẵn hai cửa sổ: một bên theo dõi `watch -n 1 info memory/stats`, một bên chạy kịch bản.

## Shot list video demo, khoảng 90 giây

| Thời lượng | Thao tác / Lệnh thực hiện | Mục tiêu quan sát |
|---|---|---|
| 0–15 giây | `redis-cli -p 6382 config get maxmemory`, `config get maxmemory-policy` | Chứng minh cấu hình `10485760` (10MB) và chính sách `allkeys-lru`. |
| 15–30 giây | `bash demos/03-eviction/reset.sh` | Đưa database về trạng thái sạch (`dbsize = 0`, `evicted_keys = 0`). |
| 30–60 giây | `python3 demos/03-eviction/fill_memory.py` | Tạo cold/hot keys, bơm dữ liệu lớn, quan sát RAM chạm ngưỡng ~9.8M và `evicted_keys` bắt đầu tăng dần. |
| 60–90 giây | Bảng tổng kết đối chứng | Chứng minh toàn bộ Cold Keys bị evict và toàn bộ Hot Keys vẫn còn tồn tại trong cache. |

## Sau record

- [ ] Xem lại video ở độ phân giải trình chiếu; đọc được lệnh và kết quả.
- [ ] Thời lượng video trong khoảng 1.5 – 2 phút, không để thời gian chết.
- [ ] Đặt tên video rõ ràng theo quy ước của nhóm (`demo-03-eviction.mp4`).

## Câu hỏi tập trả lời

1. Vì sao Redis dùng Approximate LRU thay vì True LRU? Đánh đổi khi tăng `maxmemory-samples` từ 5 lên 10?
2. Nếu dùng policy `volatile-*` nhưng database không có key nào có TTL thì Redis xử lý thế nào?
3. Quá trình eviction có làm block tiến trình đơn luồng của Redis không? Giải pháp `lazyfree-lazy-eviction` là gì?
4. Phân biệt LRU và LFU? Trường hợp nào LRU bị thất bại (Cache Pollution)?
5. Tại sao `top` trên Linux hiển thị dung lượng RAM cao hơn chỉ số `maxmemory` của Redis?

Chi tiết đáp án chuyên sâu được lưu tại [`docs/theory/03-eviction-qa.md`](../theory/03-eviction-qa.md).
