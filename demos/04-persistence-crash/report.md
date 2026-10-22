# Báo cáo thực nghiệm Redis: RDB và AOF khi tiến trình crash

## 1. Mục tiêu và phạm vi

Thực nghiệm so sánh dữ liệu khôi phục của RDB-only và AOF-only `everysec` sau khi tiến trình Redis bị kết thúc bằng `SIGKILL`. Báo cáo trình bày kết quả đã thu được, cách thực hiện và giới hạn diễn giải; phần lý thuyết chi tiết nằm trong [Redis architecture và persistence](../../docs/theory/04-redis_architecture_persistence.md).

Có hai phép quan sát riêng: bộ thử nghiệm chính không tracing và bộ bổ sung theo dõi syscall để xác nhận fsync trước crash. Không gộp số đo timing của hai bộ này.

## 2. Thiết kế và quy trình

### 2.1. Các biến được kiểm soát

| Thành phần | RDB | AOF |
|---|---|---|
| Instance độc lập | Port 6380 | Port 6381 |
| Persistence | `save ""`, `appendonly no` | `save ""`, `appendonly yes`, `appendfsync everysec` |
| Checkpoint/rewrite | Một `BGSAVE` sau baseline | Tắt rewrite tự động |
| Dữ liệu ban đầu | 2.000 key baseline | Cùng 2.000 key baseline |
| Dữ liệu ghi thêm | 1.000 key delta | Cùng 1.000 key delta |
| Khôi phục | Chính config và thư mục dữ liệu của trial | Chính config và thư mục dữ liệu của trial |

Không dùng TTL, eviction hoặc client ghi ngoài kịch bản. Key có dạng `demo:00000000`, value tương ứng `value:00000000`. Mỗi `SET` phải trả ACK thành công; tổng kỳ vọng trước crash là 3.000 key.

Hai instance bind loopback và có thư mục dữ liệu riêng. Cấu hình RDB cố định một checkpoint giúp xác định rõ phần dữ liệu nằm ngoài snapshot; tỷ lệ thiếu key của phép thử không đại diện cho tỷ lệ mất dữ liệu của RDB nói chung.

### 2.2. Lệnh chạy

Chạy các lệnh Bash sau từ thư mục gốc repository, sau khi cài requirements và kích hoạt virtualenv theo [README demo 04](README.md).

Lệnh hiện tại dùng redis-py; các bảng số liệu dưới đây được giữ nguyên từ phép đo trước migration, không được sửa hoặc coi như đã đo bằng client mới. Trial mới ghi phiên bản redis-py trong JSON; cần giữ riêng số đo timing khi so sánh các phiên bản client.

```bash
python3 demos/04-persistence-crash/scripts/run_trials.py \
  --trials 3 --baseline 2000 --delta 1000 --delays 0,0.2,1.5
```

Script dùng hai template [redis-rdb.conf](../../redis/redis-rdb.conf) và [redis-aof.conf](../../redis/redis-aof.conf), thay placeholder bằng đường dẫn riêng của từng trial. Không khởi động trực tiếp template chưa thay placeholder.

### 2.3. Trình tự đo

1. Kiểm tra hai port còn trống, tạo dữ liệu sạch và config riêng, khởi động hai instance.
2. Ghi baseline vào cả hai instance và nhận đủ ACK.
3. Gọi `BGSAVE` trên RDB. Đợi kết thúc, xác nhận trạng thái thành công, bộ đếm save tăng và snapshot tồn tại.
4. Thu thập thông tin trước delta, xác minh danh tính tiến trình và chuẩn bị gửi tín hiệu.
5. Ghi delta vào cả hai instance. Sau khi cả hai nhận đủ ACK, chờ delay yêu cầu rồi gửi `SIGKILL` cho AOF trước, RDB ngay sau.
6. Sau khi tiến trình chết và trước restart, đo kích thước file persistence. Nếu bật tracing, phân tích trace tại bước này.
7. Restart với đúng dữ liệu của trial, kiểm tra từng key/value bằng `MGET`, ghi kết quả và chỉ sau đó mới cleanup instance đã phục hồi.

Mặc định không truy vấn `INFO`, `DBSIZE` hoặc ghi JSON giữa ACK cuối và kill. Cờ `--measure-prekill-dbsize` cho phép đo thêm nhưng làm tăng khoảng thời gian trước crash; bộ kết quả chính không bật cờ này.

### 2.4. Cách đọc chỉ số

- `Expected`: số key suy ra từ các `SET` đã ACK, không phải `DBSIZE` đo tại thời điểm crash.
- `Correct`: key tồn tại và có đúng value mong đợi sau restart.
- `Missing`: key mong đợi không tồn tại sau restart.
- `Corrupt`: key tồn tại nhưng value sai. Nhãn này không tự động có nghĩa file persistence bị hỏng vật lý.
- `Delay(s)`: khoảng chờ yêu cầu sau khi cả hai nhóm ghi delta hoàn tất.
- `ACK(ms)`: khoảng đo thực tế từ ACK cuối của từng instance tới sau khi gửi tín hiệu kill, dùng đồng hồ monotonic.

Với tập key được kiểm tra: `Correct + Missing + Corrupt = Expected`. `DBSIZE` kiểm tra tổng số key, nhưng không thay thế được kiểm tra từng value.

## 3. Kết quả thực nghiệm chính

### 3.1. Khôi phục dữ liệu

| Trial | Delay (s) | Mode | Expected | Correct | Missing | Corrupt | ACK->kill (ms) |
|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 0 | RDB | 3000 | 2000 | 1000 | 0 | 14.618 |
| 1 | 0 | AOF | 3000 | 3000 | 0 | 0 | 0.686 |
| 2 | 0.2 | RDB | 3000 | 2000 | 1000 | 0 | 205.249 |
| 2 | 0.2 | AOF | 3000 | 3000 | 0 | 0 | 202.070 |
| 3 | 1.5 | RDB | 3000 | 2000 | 1000 | 0 | 1507.091 |
| 3 | 1.5 | AOF | 3000 | 3000 | 0 | 0 | 1501.548 |

Trong cả ba trial, `DBSIZE` sau restart bằng số key đúng. RDB không thiếu key baseline và thiếu đúng 1.000 key delta; AOF không thiếu baseline hoặc delta.

Một phép chạy nhanh riêng với baseline 100, delta 30, delay 0 cũng cho RDB đúng 100/130 key và AOF đúng 130/130 key, không có value sai. Phép chạy nhanh chỉ kiểm tra luồng, không gộp với ba trial chính.

### 3.2. Dung lượng và thời gian khởi động lại

| Trial | Mode | Bytes tại crash | Bytes sau restart | Startup (ms) |
|---|---|---:|---:|---:|
| 1 | RDB | 60095 | 60095 | 67.840 |
| 1 | AOF | 162200 | 162200 | 173.762 |
| 2 | RDB | 60095 | 60095 | 65.611 |
| 2 | AOF | 162200 | 162200 | 129.826 |
| 3 | RDB | 60095 | 60095 | 91.470 |
| 3 | AOF | 162200 | 162200 | 146.350 |

Startup trung bình là 74,974 ms với RDB và 149,979 ms với AOF. Đây là thời gian script quan sát từ lúc khởi động đến khi instance sẵn sàng, gồm chi phí tạo tiến trình và polling; không phải thời gian thuần đọc/parsing persistence.

RDB khôi phục 2.000 key, còn AOF khôi phục 3.000 key. Vì lượng dữ liệu khôi phục khác nhau, không dùng bảng này để kết luận so sánh hiệu năng hoặc dung lượng công bằng cho cùng dataset.

## 4. Phân tích và lý giải

### 4.1. Vì sao RDB thiếu đúng 1.000 key?

Snapshot đã hoàn tất sau baseline 2.000 key. Sau đó không có snapshot mới nên 1.000 key delta chỉ nằm trong trạng thái đang chạy của instance RDB. Khi tiến trình bị kill và restart, Redis nạp lại checkpoint 2.000 key.

Tỷ lệ thiếu 1.000/3.000 = 33,33% phản ánh cách chọn baseline và delta trong kịch bản này, không phải xác suất hoặc tỷ lệ mất dữ liệu cố hữu của RDB.

### 4.2. Vì sao AOF vẫn đủ key khi delay bằng 0?

`appendfsync everysec` điều khiển nhịp đồng bộ file, không có nghĩa Redis chỉ ghi AOF mỗi giây. Redis có thể đã dùng `write()` chuyển dữ liệu sang page cache của hệ điều hành trước khi đến lần fsync tiếp theo.

`SIGKILL` kết thúc tiến trình Redis, nhưng hệ điều hành và page cache vẫn tồn tại. Instance mới có thể đọc lại dữ liệu đó. Vì vậy, `Missing = 0` chưa chứng minh toàn bộ delta đã fsync trước crash hoặc sẽ sống sót khi mất nguồn thật.

Delay bằng 0 cũng không có nghĩa kill xảy ra tức thời: trial 1 đo được 0,686 ms với AOF và 14,618 ms với RDB. Hai instance hoàn tất ACK ở các thời điểm khác nhau, còn tín hiệu kill được gửi lần lượt.

### 4.3. Vì sao AOF base có 0 key nhưng incremental chứa 3.000 key?

Instance AOF tạo base khi dataset còn rỗng. Sau đó cả 2.000 key baseline và 1.000 key delta đều đi vào incremental AOF. Rewrite tự động bị tắt nên không có lần tạo base mới chứa baseline.

`BGSAVE` chỉ chạy trên instance RDB port 6380, không tác động đến base của instance AOF port 6381. File `.base.rdb` thuộc bộ AOF là một file khác với `dump.rdb` của instance RDB.

Tổng AOF 162.200 byte gồm base 89 byte, incremental 162.023 byte và manifest 88 byte. Redis dùng manifest để xác định bộ file, nạp base rồi replay incremental theo thứ tự để dựng lại dữ liệu trong RAM. Sự hiện diện của đầy đủ lệnh trong incremental tự nó chỉ xác nhận nội dung có thể đọc, chưa xác nhận thời điểm fsync.

## 5. Quan sát bổ sung: xác nhận fsync trước crash

### 5.1. Phương pháp và lệnh chạy

Theo dõi riêng instance AOF ban đầu bằng `strace`, gồm các thread nền và các syscall `write`, `writev`, `fsync`, `fdatasync`. Phần restart/cleanup không thuộc trace.

```bash
python3 demos/04-persistence-crash/scripts/run_trials.py \
  --trials 3 --baseline 100 --delta 30 --delays 0,0.2,1.5 \
  --trace-fsync
```

Bộ phân tích đối chiếu đúng incremental AOF và workload mong đợi. Trạng thái `Confirmed` đòi hỏi một syscall đồng bộ thành công trên đúng file, bắt đầu sau khi mọi ghi được đối chiếu đã hoàn tất và kết thúc trước mốc chuẩn bị gửi kill. Điều kiện này có chủ ý thận trọng.

### 5.2. Kết quả bộ nhỏ

| Trial | Delay (s) | AOF ACK->kill (ms) | Correct | Missing | Delta fsync |
|---|---:|---:|---:|---:|---|
| 1 | 0 | 0.400 | 130 | 0 | Not confirmed |
| 2 | 0.2 | 200.641 | 130 | 0 | Not confirmed |
| 3 | 1.5 | 1500.591 | 130 | 0 | Confirmed |

Ở trial 3, các ghi vào incremental gồm 5.423 byte baseline và 1.620 byte delta, tổng 7.043 byte. Bộ quan sát xác nhận `fdatasync` thành công sau khi các ghi này hoàn tất và trước kill.

Một phép chạy bổ sung với 2.000 baseline + 1.000 delta, delay 1,5 giây cũng cho AOF đúng 3.000 key, thiếu 0 key và trạng thái `Confirmed`; ACK->kill là 1.500,909 ms. Đây vẫn là số đo có tracing, tách khỏi bộ chính.

### 5.3. Diễn giải trạng thái

| Trạng thái | Ý nghĩa |
|---|---|
| Confirmed | Quan sát được đồng bộ file bao phủ delta, hệ điều hành xác nhận thành công trước crash |
| Not confirmed | Trace hợp lệ nhưng không có syscall đáp ứng đầy đủ điều kiện xác nhận |
| Unknown | Trace, thời gian hoặc nội dung không đủ rõ để kết luận |
| N/A | Hàng RDB không thuộc phép quan sát fsync AOF |

`Not confirmed` không đồng nghĩa chắc chắn chưa xuống thiết bị. Ví dụ, fsync chồng lấn với ghi có thể không đạt điều kiện thận trọng của bộ phân tích. Ngược lại, khôi phục đủ key không tự nâng trạng thái thành `Confirmed`.

Cùng `Missing = 0` có thể đi kèm các trạng thái fsync khác nhau. Đây là kết quả quan trọng của phép quan sát bổ sung. Tracing làm thay đổi timing, nên không cam kết mọi lần chạy delay 1,5 giây đều có cùng trạng thái.

## 6. Giới hạn và xử lý khi kết quả khác

Thử nghiệm kiểm tra process crash, không làm mất page cache và không cắt nguồn thiết bị. Xác nhận fsync là xác nhận ở giao diện hệ điều hành, chưa phải kiểm chứng toàn bộ chuỗi lưu trữ trước mất nguồn.

Ba trial chính, mỗi mức delay một trial, chưa đủ để ước lượng xác suất mất dữ liệu. Dataset nhỏ, RDB một checkpoint cố định và AOF không rewrite cũng không đại diện đầy đủ cho workload vận hành thực tế.

Khi chạy lại:

- RDB thiếu baseline hoặc có value sai: kiểm tra checkpoint đã hoàn tất và đường dẫn restart có đúng trial.
- AOF thiếu delta: kiểm tra trạng thái ghi, bộ manifest/base/incremental, thông báo nạp và timing thực tế. Không chỉnh số liệu để khớp kết quả trước.
- AOF đủ key nhưng fsync chưa xác nhận: trình bày hai quan sát riêng, không coi là mâu thuẫn.
- Trace trả `Unknown`: kiểm tra lý do do bộ phân tích trả về; không chuyển thành `Not confirmed` hoặc `Confirmed` theo suy đoán.
- Port đang dùng: dừng phép thử và xác định tiến trình sở hữu port, không kill dịch vụ không thuộc demo.

## 7. Kết luận

Với checkpoint kiểm soát, RDB phục hồi đủ 2.000 key baseline và thiếu 1.000 key delta. AOF `everysec` phục hồi đủ 3.000 key trong cả ba trial process crash. Phép theo dõi syscall bổ sung phân biệt được phục hồi đủ dữ liệu với xác nhận fsync trước crash.

Kết quả minh họa khác biệt giữa khôi phục theo snapshot và replay nhật ký. Chưa có cơ sở từ thử nghiệm này để cam kết không mất dữ liệu khi máy mất nguồn.
