# Kịch bản phần tổng quan và môi trường

Phạm vi: phần người phụ trách môi trường, dự kiến khoảng **5 phút** trong seminar 30–45 phút. Đây là nội dung dùng để tập nói và quay, không phải báo cáo nộp. Nguồn lý thuyết: [01-redis-overview.md](../../theory/01-redis-overview.md).

Slides sẽ được chuẩn bị ở giai đoạn sau; hiện chưa đưa file slides lên repo. Kịch bản dưới đây dùng để chuẩn bị phần trình bày và quay demo.

Đã có [minh chứng VMware ngày 20/10/2026](../screenshots/00-environment/vmware-2026-10-20/README.md): Workstation Pro 26H1u1 (người dùng xác nhận), 512 MB/2 CPUs, Ubuntu 26.04.1, Redis 8.0.5 và Python 3.14.4. Recording gốc dài **8 phút 26.8 giây**, nền sáng, không có lời dẫn nghe được; chưa biên tập về khoảng 90 giây. Chưa làm hoặc cập nhật slides trong lần đối chiếu này.

## Lời dẫn theo slides

| Mốc thời gian | Nội dung trên slide | Lời giải thích gợi ý |
|---|---|---|
| 0:00–0:35 | Redis và dữ liệu trong RAM | “Redis là kho dữ liệu có cấu trúc. Ngoài đọc/ghi value, ta còn thao tác List, Hash hay bảng điểm trực tiếp. Trong seminar, nhóm dùng Redis để khảo sát cache, bộ nhớ và phục hồi.” |
| 0:35–1:20 | Cache hit/miss | “Khi nhiều request hỏi cùng dữ liệu, cache giúp dùng lại kết quả. Hit trả từ cache; miss thì ứng dụng lấy nguồn rồi ghi cache. TTL giới hạn thời gian giữ key, còn update dữ liệu cần chính sách invalidation.” |
| 1:20–2:00 | Use case và giới hạn | “Redis thường dùng cho cache, session, quota, bảng xếp hạng và queue. Mức ảnh hưởng khi mất dữ liệu khác nhau: cache có thể dựng lại, nhưng session/job có thể ảnh hưởng người dùng. Cần chọn persistence phù hợp.” |
| 2:00–2:35 | Bốn demo | “Bốn phần tiếp theo kiểm tra cấu trúc dữ liệu và TTL, thời gian hit/miss, eviction khi chạm bộ nhớ, rồi dữ liệu phục hồi từ RDB và AOF.” |
| 2:35–3:05 | Môi trường cách ly | “Service mặc định ở 6379. Mỗi bài có process, port và thư mục riêng. Crash hoặc reset một bài không làm dừng server của bài khác.” |
| 3:05–4:35 | Video môi trường | Dành khoảng 90 giây cho bản biên tập về sau; không phát nguyên recording 8 phút 26.8 giây trong slot này. Nêu phiên bản VMware/guest thực tế và swap bật. |
| 4:35–5:00 | Chuyển phần | “Môi trường đã kiểm tra kết nối và cách ly. Phần đầu tiên sẽ cho thấy Redis lưu và thao tác các cấu trúc dữ liệu như thế nào.” |

Tập nói bằng ý chính, không đọc nguyên văn. Khi làm slides sau này, dùng kết quả VMware cho môi trường cuối; chỉ dùng số WSL nếu ghi rõ là rehearsal riêng. Hai checker PASS và normal restart không chứng minh workload cuối hoặc crash-loss đã hoàn thành. Log vẫn có overcommit/PID-file warning cần kiểm tra lại.

## Nguồn recording đã có và việc biên tập sau

File gốc: `F:\Git\Uni\Linux\Seminar evidence\2026-10-20 14-56-09.mp4`, 1080p/60 fps. [Chỉ mục minh chứng](../screenshots/00-environment/vmware-2026-10-20/README.md) có mốc thời gian gần đúng cho OS/service, checker, isolation/TTL và normal restart. Giữ bản gốc; chưa cắt video trong lần chỉnh tài liệu này. Ảnh settings CPU/RAM được cung cấp riêng, không giả định nằm trong recording.

Khi nhóm làm phần trình chiếu, chọn đoạn thật có command và output, bỏ thời gian chờ cài package, giữ đủ thời gian đọc kết quả. Nếu thuyết minh trực tiếp thì video không cần voiceover; thử đồng bộ lời nói và playback trước buổi trình bày. Nếu dùng ảnh settings trong bản biên tập, ghi rõ đó là ảnh cấu hình VM.

## Chuẩn bị trước khi record

- [ ] VM cuối có đúng RAM/CPU dự định và chạy ổn; chụp settings khi thích hợp.
- [ ] Setup và tải dependency xong trước khi quay, không dành video chính để chờ apt.
- [ ] Snapshot môi trường sẵn sàng; nhớ `/tmp` có thể cần tạo lại sau reboot.
- [ ] Cả năm instance hoạt động, `bash linux/check.sh` trả PASS.
- [ ] Key `env:probe` chưa được bài khác dùng; chưa bắt đầu đo cache/eviction.
- [ ] Terminal nền sáng, chữ tối, cỡ khoảng 24–28 pt hoặc đủ lớn khi thử trên màn hình trình chiếu.
- [ ] Khung hình 16:9; tắt thông báo, che thông tin riêng; giữ lệnh trên từng dòng.
- [ ] Dùng giọng nói hoặc caption ngắn; giữ output đủ lâu để đọc.

## Shot list video môi trường, khoảng 90 giây

| Thời lượng | Hình/lệnh cần quay | Ý cần nói và kỳ vọng |
|---|---|---|
| 0–10 giây | VMware settings CPU/RAM | Nêu cấu hình thực, không dùng ảnh WSL thay ảnh VM |
| 10–25 giây | `cat /etc/os-release`, `redis-server --version` | Chọn phần output cần thiết, đọc tên distro và Redis version |
| 25–40 giây | `systemctl is-active redis-server`, `redis-cli -p 6379 PING` | `active`, `PONG` chứng minh service và lệnh hoạt động |
| 40–55 giây | Vòng lặp PING các port hoặc phần port trong `linux/check.sh` | Sáu port trả PONG; không cuộn hết log cấu hình dài |
| 55–75 giây | Block cách ly `env:probe` trong commands.md | 6383 đọc được, 6384 không có, xóa probe sau khi quay |
| 75–90 giây | `redis-cli -p 6383 SHUTDOWN`, start lại bằng config, PING | Dừng bình thường và khôi phục đúng instance; server chạy foreground cần terminal thứ hai để PING |

Không quay cảnh gõ mật khẩu. Nếu cần `sudo`, xác thực trước đoạn quay. Hãy chạy thử toàn bộ shot list một lượt trước khi record thật. Nếu lỗi, dừng record, đọc log/reset đúng bài, rồi quay lại từ trạng thái sạch.

## Sau record

- [ ] Xem video ở độ phân giải/cỡ hiển thị giống lúc trình chiếu; đọc được cả command và output.
- [ ] Không cắt bỏ lỗi khiến kết luận khác với kết quả thực tế.
- [ ] Kiểm tra âm lượng/caption và giữ phiên bản video có tên rõ ràng.
- [ ] Thử phát video bằng slide deck trên máy dự định trình bày.
- [ ] Giữ file video rời ngoài deck và bản dự phòng offline.
- [ ] Ghi đường dẫn video dùng chung vào PR hoặc checklist nhóm; tránh commit video lớn vào Git khi nhóm chưa thống nhất.

## Câu hỏi tập trả lời

1. Vì sao cần cache nếu database cũng có cache nội bộ?
2. Khi Redis lỗi thì app làm gì, database nguồn có chịu được fallback không?
3. Vì sao nhiều logical database chưa đủ để cách ly crash và memory limit?
4. Restart có luôn xóa dữ liệu không? Khác nhau giữa normal shutdown và kill -9?
5. Minh chứng nào chứng minh VM 512 MB, minh chứng nào chỉ chứng minh Redis hoạt động?

Đáp án nền nằm trong theory/01-redis-overview.md. Người phụ trách từng demo trả lời cơ chế sâu và số liệu của phần mình.
