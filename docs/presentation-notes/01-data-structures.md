# Kịch bản thuyết trình - Phần 2: Cấu trúc dữ liệu và TTL

Người trình bày: **Viết Toàn**. Thời lượng: **5–6 phút** (khoảng 3 phút lý thuyết, 2–2,5 phút video demo, 30 giây chốt).
Đứng sau phần tổng quan (Nam Anh), đứng trước phần Cache-Aside (Quốc Thắng).

## Dàn ý slide (6 slide)

| # | Tiêu đề slide | Nội dung trên slide | Thời gian |
|---|---|---|---|
| 1 | Redis không chỉ là key → string | Sơ đồ 1 key trỏ tới 4 kiểu value: String, List, Hash, Sorted Set. Một dòng: "Value có kiểu, lệnh chạy ngay trên server, nguyên tử" | 30s |
| 2 | String và Hash | 2 cột. String: cache JSON, `INCR` counter, tối đa 512 MB. Hash: object nhiều field, sửa từng field. Bảng nhỏ "JSON trong String hay Hash?" | 45s |
| 3 | List và Sorted Set | 2 cột. List: queue FIFO (`RPUSH` → `LPOP`). Sorted Set: leaderboard (`ZADD`, `ZINCRBY`, `ZREVRANGE`). Bảng so sánh: thứ tự chèn vs theo score, trùng vs duy nhất | 60s |
| 4 | TTL: key tự hết hạn | Timeline `SET ... EX 5` → TTL 5…1 → `GET` = nil. Bảng `n` / `-1` / `-2`. Bẫy: `SET` lại làm mất TTL → `KEEPTTL` | 45s |
| 5 | Demo | Video quay `run.sh --no-pause` (light mode, chữ to) | 2–2,5 phút |
| 6 | Chọn cấu trúc nào? | Cây quyết định ngắn + 1 câu nối sang Cache-Aside | 30s |

## Lời nói gợi ý

**Slide 1.** "Phần trước Nam Anh nói Redis lưu dữ liệu trong RAM. Điểm khác biệt lớn thứ hai là value trong Redis *có kiểu*. Nhờ vậy, muốn cộng điểm cho người chơi, ta không cần kéo cả object về ứng dụng, sửa rồi ghi lại. Chỉ cần một lệnh chạy ngay trên server, và lệnh đó là nguyên tử. Phần này mình giới thiệu 4 kiểu hay dùng nhất, cùng cơ chế TTL."

**Slide 2.** "String là kiểu đơn giản nhất: một key, một giá trị, tối đa 512 MB. Hai cách dùng phổ biến là cache một chuỗi JSON và làm bộ đếm bằng `INCR`. `INCR` là nguyên tử, nên nghìn người cùng bấm like cũng không mất lượt nào. Hash giống một object: một key, nhiều field. Ưu điểm là sửa đúng một field, ví dụ đổi role của user, mà không phải ghi lại cả object."

**Slide 3.** "List giữ đúng thứ tự chèn. Đẩy vào cuối bằng `RPUSH`, lấy ra ở đầu bằng `LPOP` là có ngay một hàng đợi FIFO. Sorted Set thì mỗi phần tử có một điểm số, và Redis *luôn tự sắp xếp* theo điểm. Lấy top 10 hay hỏi 'tôi hạng mấy' chỉ mất O(log N). Khác biệt cốt lõi: List trả lời 'ai đến trước', Sorted Set trả lời 'ai đứng thứ mấy'. List cho phép trùng, Sorted Set thì mỗi member là duy nhất."

**Slide 4.** "TTL là thời gian sống của key. Ta gán ngay khi ghi bằng `SET ... EX`, hoặc gán sau bằng `EXPIRE`. Lệnh `TTL` trả về số giây còn lại. Có hai giá trị đặc biệt cần nhớ: `-1` là key còn đó nhưng không bao giờ hết hạn, `-2` là key không tồn tại nữa. Và một cái bẫy: `SET` lại một key sẽ xóa TTL cũ, cache bỗng thành vĩnh viễn. Muốn giữ TTL thì thêm `KEEPTTL`."

**Slide 5 (vừa chạy video vừa nói).**
- Phần String: "Ghi cache sản phẩm kèm TTL 60 giây trong một lệnh. `INCR` ba lần cho ra 1, 2, rồi 12."
- Phần List: "Ba job được đẩy vào. `LPOP` lấy job 1 ra trước, đúng thứ tự FIFO."
- Phần Hash: "`HINCRBY` tăng số lần đăng nhập, `HSET` đổi role thành admin. Các field còn lại giữ nguyên."
- Phần Sorted Set: "Ban đầu bob dẫn đầu. carol được cộng 600 điểm và vượt lên hạng 1. Ta không phải sắp xếp gì cả."
- Phần TTL: "Session có TTL 5 giây, các bạn thấy nó đếm ngược 5, 4, 3, 2, 1. Sau đó `GET` trả về nil, `TTL` trả `-2`. Redis đã tự xóa key."
- Cuối video: "`expired_keys` tăng 1 vì key hết hạn, còn `evicted_keys` bằng 0 vì RAM vẫn dư. Phân biệt hai chỉ số này, Tường sẽ nói kỹ ở phần Eviction."

**Slide 6 (nối sang người tiếp theo).** "Tóm lại: giá trị đơn hoặc JSON dùng String, object hay sửa từng phần dùng Hash, hàng đợi dùng List, xếp hạng dùng Sorted Set. Thứ gì là cache thì luôn gắn TTL. Chính String kết hợp TTL là nền móng của mô hình Cache-Aside mà Thắng sẽ trình bày ngay sau đây."

## Quay video demo

1. Terminal **light mode** (nền trắng, chữ đen), cỡ chữ 18–22 pt, cửa sổ khoảng 100 cột × 30 dòng.
2. Khởi động instance: `redis-server redis/redis-data-structures.conf` (ở terminal khác, không cần quay).
3. Quay bằng chế độ có dừng: `bash demos/01-data-structures/run.sh`. Bấm Enter sau mỗi phần để người xem kịp đọc. Nếu muốn đếm ngược lâu hơn: `TTL_SECONDS=8 bash demos/01-data-structures/run.sh`.
4. Gợi ý công cụ: OBS Studio, hoặc `asciinema rec demo01.cast` (nhẹ, chữ nét, có thể xuất GIF bằng `agg`).
5. Cắt video còn khoảng 2–2,5 phút. Chụp 6 ảnh minh chứng theo danh sách trong `demos/01-data-structures/README.md`.

## Phối hợp với phần Cache-Aside (Demo 02)

Cần thống nhất trước khi viết `demos/02-cache-aside/app.py`:

- Key cache: `cache:product:<id>`, kiểu String chứa JSON.
- Ghi cache **bằng một lệnh** `SET key value EX <ttl>` (trong redis-py: `r.set(key, value, ex=ttl)`), không tách `SET` rồi `EXPIRE`.
- TTL đề xuất: 60 giây, để khớp số liệu với Demo 01.
- Demo 01 nhắc "SET lại làm mất TTL", nên khi Demo 02 cập nhật cache cũng phải luôn truyền `ex=`.
- Instance riêng: Demo 01 dùng `6383`, Demo 02 dùng `6384`. Không dùng chung port.

## Câu hỏi dự phòng

Xem mục 9 trong `docs/theory/02-data-structures.md`. Nếu bị hỏi bất ngờ, mở `redis-cli -p 6383` và gõ lệnh trong `demos/01-data-structures/demo.redis` để minh họa trực tiếp.
