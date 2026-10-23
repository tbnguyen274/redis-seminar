# Demo 01 - Cấu trúc dữ liệu và TTL

Người phụ trách: **Viết Toàn**. Thời lượng trình bày dự kiến: 5–6 phút.

Demo dùng một instance Redis riêng ở **port 6383** để thao tác bốn kiểu dữ liệu, mỗi kiểu gắn với một use case thật:

| Kiểu dữ liệu | Use case | Key trong demo |
|---|---|---|
| String | Cache sản phẩm (JSON) và bộ đếm lượt xem | `cache:product:1001`, `stats:page:home:views` |
| List | Hàng đợi gửi email (FIFO) | `queue:emails` |
| Hash | Thông tin user | `user:1001` |
| Sorted Set | Bảng xếp hạng game | `leaderboard:game` |
| TTL | Session tự hết hạn sau 5 giây | `session:abc123` |

Lý thuyết chi tiết nằm ở [`docs/theory/02-data-structures.md`](../../docs/theory/02-data-structures.md). Kịch bản nói nằm ở [`docs/presentation-notes/02-data-structures.md`](../../docs/presentation-notes/02-data-structures.md).

## File trong thư mục

| File | Dùng khi nào |
|---|---|
| `run.sh` | Chạy toàn bộ demo tự động: in lệnh kèm kết quả, đếm ngược TTL, tổng kết. **Dùng file này khi quay video.** |
| `demo.redis` | Danh sách lệnh để gõ tay hoặc copy từng dòng vào `redis-cli` khi live demo hay trả lời câu hỏi |
| `expected-output.txt` | Kết quả mẫu của `run.sh --no-pause` (Redis 7.0.15) để đối chiếu |

## Chuẩn bị (chỉ làm 1 lần)

Chạy từ **thư mục gốc repo**:

```bash
sudo bash linux/setup.sh                                   # cài redis-server, redis-cli
sudo mkdir -p /tmp/redis-seminar/data-structures
sudo chown -R "$USER":"$USER" /tmp/redis-seminar
```

## Chạy demo

Terminal 1: khởi động instance riêng (chạy foreground, `Ctrl+C` để dừng):

```bash
redis-server redis/redis-data-structures.conf
```

Terminal 2: chạy demo:

```bash
bash demos/01-data-structures/run.sh             # dừng chờ Enter sau mỗi phần (khi thuyết trình)
bash demos/01-data-structures/run.sh --no-pause  # chạy liền mạch (khi quay video), khoảng 6 giây
```

Tùy chọn qua biến môi trường: `REDIS_PORT` (mặc định `6383`), `REDIS_HOST` (mặc định `127.0.0.1`), `TTL_SECONDS` (mặc định `5`). Ví dụ muốn đếm ngược lâu hơn cho khán giả kịp nhìn: `TTL_SECONDS=10 bash demos/01-data-structures/run.sh`.

Kiểm tra nhanh instance đang chạy đúng port: `redis-cli -p 6383 PING` phải trả về `PONG`.

## Reset để chạy lại

`run.sh` tự `FLUSHDB` ở đầu mỗi lần chạy, nên chạy lại bao nhiêu lần cũng cho cùng kết quả. Chỉ muốn dọn dữ liệu thì dùng:

```bash
bash demos/01-data-structures/run.sh --reset
```

Script **từ chối chạy trên port 6379** (instance mặc định của hệ thống) để không xóa nhầm dữ liệu. Instance 6383 tắt `save` và `appendonly`, nên dừng `redis-server` cũng xóa sạch dữ liệu.

## Kết quả mong đợi

| Phần | Lệnh kiểm chứng | Kết quả đúng |
|---|---|---|
| String | `GET cache:product:1001`, `TTL cache:product:1001` | Trả JSON sản phẩm; TTL khoảng `60` |
| Counter | `INCR` 2 lần rồi `INCRBY 10` | `1`, `2`, `12` |
| List | `LRANGE queue:emails 0 -1` sau `LPOP` | Còn `job:2`, `job:3` (job:1 đã được lấy ra trước, đúng FIFO) |
| Hash | `HGETALL user:1001` | `role` = `admin`, `login_count` = `1` |
| Sorted Set | `ZREVRANGE leaderboard:game 0 2 WITHSCORES` | Trước: bob 2300, eve 2100, carol 1800. Sau `ZINCRBY 600 carol`: **carol 2400**, bob 2300, eve 2100 |
| TTL còn hạn | `TTL session:abc123` | `5`, đếm ngược về `1` |
| Key không có TTL | `TTL user:1001` | `-1` |
| Bẫy SET | `SET` lại không có `KEEPTTL` | TTL từ ~60 về `-1`; có `KEEPTTL` thì giữ nguyên |
| Hết hạn | `GET` / `TTL` / `EXISTS session:abc123` | `(nil)` / `-2` / `0` |

## Minh chứng cần chụp (lưu vào `docs/screenshots/01-data-structures/`)

Khi chạy trên VM, chụp các màn hình sau (để terminal **light mode, cỡ chữ lớn**):

1. `01-string.png`: GET và TTL của cache sản phẩm, kết quả INCR.
2. `02-list.png`: LRANGE trước và sau LPOP.
3. `03-hash.png`: HGETALL user:1001.
4. `04-sorted-set.png`: ZREVRANGE trước và sau ZINCRBY.
5. `05-ttl-countdown.png`: đếm ngược TTL, rồi GET trả `(nil)` và TTL trả `-2`.
6. `06-summary.png`: bảng tổng kết key, kiểu dữ liệu, TTL và thời gian chạy.

Ghi lại thời gian toàn demo, là dòng cuối "Hoàn thành demo trong N giây".

## Tương thích

Chỉ dùng lệnh có từ Redis **6.0** trở xuống (`KEEPTTL` cần 6.0). Ubuntu 22.04 (Redis 6.0.16) và Debian 12 / Ubuntu 24.04 (Redis 7.0.x) đều chạy được. Không dùng `GETEX`, `ZRANGE ... REV`, `LPOP key count` vì các lệnh này cần Redis 6.2 trở lên.
