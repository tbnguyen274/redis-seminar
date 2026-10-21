# Checklist phần môi trường và chất lượng demo

Checklist dùng khi bàn giao từng demo và chạy tích hợp cả nhóm. Kết quả từng lần kiểm tra nằm trong [environment-verification.md](environment-verification.md); lệnh vận hành nằm trong [linux/commands.md](../linux/commands.md).

## Môi trường dùng chung

- [ ] Thành viên dùng cùng commit và cấu hình `redis/*.conf`; ghi phiên bản OS/Redis/Python khi bàn giao.
- [ ] Setup đã hoàn tất trên VM; instance tương ứng với demo khởi động được và trả `PONG` đúng port.
- [ ] Client dùng đúng host/port, không sửa hoặc reset instance của phần khác.
- [ ] Thay đổi cấu hình có trong PR, hướng dẫn chạy và kỳ vọng checker được cập nhật nếu cần.
- [ ] Khi tích hợp, service 6379 và đủ năm instance 6380–6384 hoạt động; `bash linux/check.sh` trả `PASS`.
- [ ] Bốn workload cuối chạy được trên VM 512 MB; ghi rõ swap và điều kiện đo.
- [ ] Có hướng dẫn stop/start/reset và khôi phục thư mục sau reboot.

Đây là checklist dùng lại cho mỗi lần review, không phải nhật ký hoàn thành. Minh chứng hạ tầng đã có trong [lần chạy VMware](screenshots/00-environment-setup/vmware-2026-10-20/README.md); các workload được kiểm tra riêng khi chủ phần bàn giao.

## Bàn giao tối thiểu từ mỗi chủ demo

- [ ] Lý thuyết của demo có nguồn và liên hệ tới experiment.
- [ ] Script/chuỗi lệnh chạy từ repo root, ghi đúng port.
- [ ] Requirements và phiên bản dependency; không phụ thuộc file bí mật hoặc đường dẫn riêng.
- [ ] README có điều kiện đầu vào, lệnh chạy, output kỳ vọng và reset.
- [ ] Dữ liệu đo/log thật, có đơn vị, môi trường và số lượt chạy.
- [ ] Reset và rerun ít nhất hai lượt không trộn kết quả cũ.
- [ ] Video đã quay, dễ đọc; slide giải thích được kết quả.
- [ ] PR riêng để review, không sửa đè phần người khác.

## Demo 01: cấu trúc dữ liệu và TTL

- [ ] Port 6383, đúng config và directory riêng.
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

- [ ] Port 6382, `maxmemory=10485760`, policy `allkeys-lru` đúng cấu hình chung.
- [ ] Ghi `INFO memory`, `INFO stats` trước/sau, `evicted_keys` tăng.
- [ ] Phân biệt `expired_keys` và `evicted_keys`; không dùng key hết TTL làm bằng chứng eviction.
- [ ] Kiểm tra key mất/còn; hot key có xác suất giữ cao hơn, không hứa luôn tồn tại.
- [ ] Reset thống kê hoặc dùng chênh lệch trước/sau, nêu rõ cách tính.
- [ ] Payload có giới hạn và không ép hết RAM toàn VM để thay cho cơ chế maxmemory.

## Demo 04: persistence/crash

- [ ] RDB 6380 và AOF 6381 dùng config/directory riêng.
- [ ] Xác nhận RDB đã có snapshot baseline cần thiết, AOF bật everysec; ghi INFO persistence.
- [ ] Cùng workload, có số thứ tự key hoặc kiểm tra nội dung, không chỉ đếm key nếu nội dung có thể sai.
- [ ] Ghi PID/port hiện tại, số key và thời điểm trước crash; chỉ kill đúng demo process.
- [ ] Restart cùng config/dir, ghi key phục hồi và mất; lặp lại nhiều lần.
- [ ] Ghi rõ normal shutdown khác crash; kill -9 không mô phỏng mất page cache kernel.
- [ ] AOF không mất key vẫn là kết quả hợp lệ; không tuyên bố luôn mất đúng một giây.
- [ ] Redis 7+ có thể có multi-part AOF, kiểm tra đúng appendonlydir/manifest.

## Duyệt chung trước nộp

- [ ] Bốn demo có người sở hữu và kết quả review rõ ràng.
- [ ] Phần tổng quan và môi trường gói trong khoảng 5 phút, gồm video khoảng 90 giây; chỉ giới thiệu các nội dung sẽ được đào sâu ở từng demo.
- [ ] Cùng thuật ngữ, port và phiên bản trên code, slides, video.
- [ ] Chạy thử cả nhóm trong 30–45 phút, thống nhất thời gian Q&A với giảng viên/nhóm.
- [ ] Slide không chứa số liệu dự đoán được trình bày như kết quả đo.
- [ ] Video playback hoạt động trên máy trình chiếu, có bản offline dự phòng.
- [ ] Chốt ai nộp slides và định dạng Moodle chấp nhận; kiểm tra upload cuối.

## Nội dung PR của phần môi trường

Nêu thay đổi, cách chạy, kết quả kiểm tra và mục còn lại. Link minh chứng cần thiết; không đưa nhật ký thao tác hoặc đường dẫn máy cá nhân vào hướng dẫn dùng chung. Người review phải chạy lại được từ repo.
