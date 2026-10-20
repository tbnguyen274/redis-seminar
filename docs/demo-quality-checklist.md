# Checklist phần môi trường và chất lượng demo

Theo cập nhật nhóm: nộp slides qua Moodle, seminar 30–45 phút, nên quay trước các demo với light mode và chữ lớn. Theory là tài liệu học/đối chiếu trong `theory/`; `report/seminar.md` là khung cũ. Checklist này ghi việc còn phải làm, không tự đánh dấu đạt chỉ vì có hướng dẫn.

## Trạng thái công việc

### Người phụ trách môi trường

- [x] Soạn nghiên cứu overview, use case, FAQ và nguồn chính thức trong `theory/01-redis-overview.md`.
- [x] Chuẩn bị setup có Redis, Python/venv và năm thư mục dữ liệu.
- [x] Chuẩn bị lệnh start/stop/reset/restart, script kiểm tra chỉ đọc và hướng dẫn phục hồi.
- [x] Soạn lời nói, shot list quay môi trường và tiêu chí xem lại video.
- [x] Chuẩn bị sáu slides chỉnh sửa được, nguồn trong speaker notes; đánh dấu đúng kết quả rehearsal WSL.
- [ ] Chạy lại trên VMware cấu hình cuối 512 MB; ghi OS/Redis/CPU/RAM thực tế.
- [ ] Chụp settings VMware và bằng chứng màn hình của lần chạy cuối.
- [ ] Quay video môi trường nền sáng, chữ lớn; xem lại ở kích thước trình chiếu.
- [ ] Chốt slide section với nhóm, ghép video và tập nói khoảng 5 phút.
- [ ] Chạy demo của từng thành viên từ README của họ, không cần hướng dẫn miệng.
- [ ] Nhờ thành viên review PR và thống nhất merge.

Kết quả kiểm tra tự động/thực nghiệm được ghi riêng trong [environment-verification.md](environment-verification.md). WSL rehearsal không thay thế mục VMware 512 MB phía trên.

## Bàn giao tối thiểu từ mỗi chủ demo

- [ ] Theory của phần mình có nguồn và liên hệ tới experiment.
- [ ] Script/chuỗi lệnh chạy từ repo root, ghi đúng port.
- [ ] Requirements và phiên bản dependency; không phụ thuộc file bí mật hoặc đường dẫn riêng.
- [ ] README có điều kiện đầu vào, lệnh chạy, output kỳ vọng và reset.
- [ ] Dữ liệu đo/log thật, có đơn vị, môi trường và số lượt chạy.
- [ ] Reset và rerun ít nhất hai lượt không trộn kết quả cũ.
- [ ] Video đã quay, dễ đọc; slide giải thích được kết quả.
- [ ] PR riêng để review, không sửa đè phần người khác.

## Demo 01: cấu trúc dữ liệu và TTL

- [ ] Port 6383, đúng config và dataset riêng.
- [ ] String, List, Hash, Sorted Set đều có thao tác ghi và đọc minh họa.
- [ ] Leaderboard đúng thứ tự score; List và Sorted Set được phân biệt rõ.
- [ ] TTL giảm, key hết hạn, giải thích được -1 và -2.
- [ ] Reset không ảnh hưởng port khác; ảnh/video có cả command và output.

## Demo 02: Cache-Aside

- [ ] Port 6384, app tìm cache trước và fallback nguồn khi miss.
- [ ] Nguồn chậm được ghi rõ là mô phỏng khoảng 300 ms, không phải benchmark database thật.
- [ ] Dữ liệu trả đúng và giống nhau ở nhánh hit/miss.
- [ ] Có TTL, invalidation/reset; xóa cache tạo được miss lại.
- [ ] Đo nhiều lần với đồng hồ monotonic như `time.perf_counter`; cùng phạm vi đo cho các nhánh.
- [ ] Báo cáo số liệu thật; phân biệt hệ số nhanh hơn với phần trăm giảm thời gian.
- [ ] Không trộn thời gian cài package/khởi động app vào một nhánh duy nhất.

## Demo 03: eviction

- [ ] Port 6382, `maxmemory=10485760`, policy `allkeys-lru` được kiểm tra bằng CONFIG GET.
- [ ] Ghi `INFO memory`, `INFO stats` trước/sau, `evicted_keys` tăng.
- [ ] Phân biệt `expired_keys` và `evicted_keys`; không dùng key hết TTL làm bằng chứng eviction.
- [ ] Kiểm tra key mất/còn; hot key có xác suất giữ cao hơn, không hứa luôn tồn tại.
- [ ] Reset thống kê hoặc dùng chênh lệch trước/sau, nêu rõ cách tính.
- [ ] Payload có giới hạn và không ép hết RAM toàn VM để thay cho cơ chế maxmemory.

## Demo 04: persistence/crash

- [ ] RDB 6380 và AOF 6381 dùng config và directory riêng.
- [ ] Xác nhận RDB đã có snapshot baseline cần thiết, AOF bật everysec; ghi INFO persistence.
- [ ] Cùng workload, có số thứ tự key hoặc kiểm tra nội dung, không chỉ đếm key nếu nội dung có thể sai.
- [ ] Ghi PID/port hiện tại, số key và thời điểm trước crash; chỉ kill đúng demo process.
- [ ] Restart cùng config/dir, ghi key phục hồi và mất; lặp lại nhiều lần.
- [ ] Ghi rõ normal shutdown khác crash; kill -9 không mô phỏng mất page cache kernel.
- [ ] AOF không mất key vẫn là kết quả hợp lệ; không tuyên bố luôn mất đúng một giây.
- [ ] Redis 7+ có thể có multi-part AOF, kiểm tra đúng appendonlydir/manifest.

## Duyệt chung trước nộp

- [ ] Bốn demo có người sở hữu và kết quả review rõ ràng.
- [ ] Cùng thuật ngữ, port và phiên bản trên code, slides, video.
- [ ] Chạy thử cả nhóm trong 30–45 phút, thống nhất thời gian Q&A với giảng viên/nhóm.
- [ ] Slide không chứa số liệu dự đoán được trình bày như kết quả đo.
- [ ] Video playback hoạt động trên máy trình chiếu, có bản offline dự phòng.
- [ ] Chốt ai nộp slides và định dạng Moodle chấp nhận; kiểm tra upload cuối.

## Nội dung PR của phần môi trường

Nêu vấn đề, file thay đổi, môi trường thật và các lệnh đã kiểm tra. Link minh chứng; liệt kê mục chưa làm (VMware cuối, record, script của thành viên). Không ghi “mọi demo đã hoàn thành” khi chỉ mới verify server/config. Không cần commit/push/merge để hoàn thành bước chuẩn bị local.
