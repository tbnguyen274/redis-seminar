# Giải thích và bảo vệ mã nguồn demo persistence crash

Tài liệu này giải thích mã **hiện tại**, không phải đề xuất viết lại. Đọc [README](README.md) để cài/chạy, [báo cáo](report.md) để xem số liệu, và [kịch bản thuyết trình](../../docs/presentation-notes/redis-architecture-persistence-talk.md) để chọn nội dung trong 7–8 phút.

## 1. Có hai chương trình với hai mục tiêu khác nhau

| Chương trình | Mục tiêu | Cách thực hiện |
|---|---|---|
| `run_trials.py` cùng các module Python | Thí nghiệm tự động, kiểm soát checkpoint và đo ACK->kill | Pipeline, hai nhóm ghi đồng thời, restart và kiểm tra từng value |
| `persistence_crash.sh` | Dạy lệnh Linux/Redis từng bước | In lệnh, chạy `redis-cli`, đợi Enter, dataset nhỏ |

Bản Bash độc lập, không gọi bản Python. Hai bản dùng cùng template và port, nên **không chạy đồng thời**. Không lấy timing của bài học Bash thay cho số đo của Python.

## 2. Bản đồ trách nhiệm và phụ thuộc

Hiện có **7 file Python**, gồm sáu module chức năng và một file hằng số. Thư viện redis-py đảm nhiệm giao tiếp mạng; `aof_reader.py` giữ riêng phần đọc file AOF local phục vụ phân tích fsync. Chỉ file điều phối là entry point của bản Python.

| File | Trách nhiệm | Không chịu trách nhiệm |
|---|---|---|
| [run_trials.py](scripts/run_trials.py) | CLI, thứ tự các giai đoạn, ghép kết quả, cleanup | Không tự cài lại RESP hoặc phân tích syscall |
| [constants.py](scripts/constants.py) | Mặc định/giới hạn CLI, kết nối, batch, timeout, ngưỡng trace và đơn vị | Không chạy lệnh, không tự cập nhật config Redis hoặc bài Bash |
| [redis_client.py](scripts/redis_client.py) | Adapter redis-py, ghi workload, đọc INFO/config, kiểm tra key/value | Không quản lý PID hoặc đọc file AOF |
| [redis_instance.py](scripts/redis_instance.py) | Sinh config, start/stop, checkpoint, xác minh PID, gửi tín hiệu | Không xuất CSV hoặc quyết định workload |
| [results.py](scripts/results.py) | Thư mục run, JSON, CSV, dung lượng file, bảng terminal | Không kết nối Redis hoặc gửi kill |
| [fsync_trace.py](scripts/fsync_trace.py) | Khởi động tracer và phân tích write/fsync trên AOF | Không đo thời gian recovery hoặc chứng minh mất nguồn |
| [aof_reader.py](scripts/aof_reader.py) | Đọc command RESP array/bulk strings từ incremental AOF local | Không kết nối Redis hoặc phụ thuộc parser nội bộ redis-py |
| [persistence_crash.sh](scripts/persistence_crash.sh) | Một bài thực hành Bash hoàn chỉnh | Không tái tạo phép đo timing chính xác của Python |

`run_trials` gọi `redis_client`, `redis_instance`, `results`, `fsync_trace`; `redis_instance` dùng `redis_client`, còn `fsync_trace` dùng `aof_reader`. Hai module phân tích file không cần client mạng; `results` chỉ dùng thư viện chuẩn. Các module phụ không import ngược `run_trials`.

### Hằng số và các số vẫn giữ tại chỗ

`constants.py` tập trung các giá trị có ý nghĩa cấu hình/đo lường. Ví dụ: `PIPELINE_BATCH_SIZE=250`, `MGET_BATCH_SIZE=200`, `KEY_SAMPLE_LIMIT=20`, `POLL_INTERVAL_SECONDS=0.05`, `SYNC_TIMESTAMP_MARGIN_SECONDS=0.000002`. Các ngưỡng thời gian có hậu tố `_SECONDS` để tránh nhầm giây với mili giây; các module dùng chung hệ số đổi đơn vị và độ rộng chỉ số key.

Các số 0/1 để khởi tạo bộ đếm, chỉ số/cấu trúc RESP, độ dài CRLF, độ rộng cột terminal và dữ liệu mẫu trong tests vẫn giữ tại nơi sử dụng. Đây không phải tham số điều chỉnh thí nghiệm; tests giữ giá trị kỳ vọng độc lập để phát hiện thay đổi hành vi ngoài ý muốn. Số worker được suy ra từ số instance thay vì cố định 2.

Nếu đổi port/host trong hằng số, phải sửa cả template ở `redis/`; test render config kiểm tra hai phía khớp nhau. Đổi batch, timeout hoặc ngưỡng xác nhận có thể ảnh hưởng timing/kết luận, cần kiểm thử lại. File hằng số không phải cơ chế tự tạo mọi cấu hình hay mở rộng parser sang workload tùy ý; bản Bash vẫn có thiết lập riêng.

## 3. `run_trials.py`: điều phối một lần chạy

### 3.1. `main()` và tham số CLI

| Tham số | Mặc định | Ý nghĩa |
|---|---|---|
| `--trials` | `3` | Số trial độc lập, cho phép 1–100 |
| `--baseline` | `2000` | Số key trước checkpoint, phải dương |
| `--delta` | `1000` | Số key ghi sau checkpoint, phải dương |
| `--delays` | `0,0.2,1.5` | Delay giây từ 0–60, hữu hạn; chọn luân phiên theo trial |
| `--pause-after-checkpoint` | Tắt | Đợi Enter trước delta, thích hợp trình bày live |
| `--measure-prekill-dbsize` | Tắt | Đo DBSIZE sau delta, thêm overhead trước kill |
| `--trace-fsync` | Tắt | Theo dõi syscall của AOF ban đầu; cần `strace`, làm thay đổi timing |

Ví dụ `--trials 5 --delays 0,1.5` chọn lần lượt 0; 1,5; 0; 1,5; 0 giây. Ba trial mặc định không phải ba lần lặp của từng mức delay.

`main()` kiểm tra Linux với `/proc`, Redis 7+, công cụ cần thiết và hai port trống. Đường dẫn repo/config/results tính từ `__file__`, không phụ thuộc vị trí terminal. Không tự cài package, không quản lý Redis mặc định port 6379.

### 3.2. `run_trial()` theo trình tự thực thi

1. Tạo thư mục trial mới bên trong run; render config/data riêng cho RDB và AOF.
2. Khởi động hai instance và kiểm tra cấu hình persistence thực tế, tránh chỉ tin nội dung template.
3. Ghi baseline; cả hai DBSIZE phải đúng baseline.
4. Tạo và xác nhận checkpoint RDB bằng `checkpoint_rdb()`.
5. Ghi thông tin **trước delta**, tùy chọn pause, rồi xác minh/pin tiến trình.
6. Ghi delta, nhận toàn bộ ACK, tùy chọn DBSIZE, chờ delay, kill AOF trước rồi RDB.
7. Đợi port đóng, đóng pidfd, đo dung lượng trước restart. Nếu tracing thì kết thúc/đọc trace ngay ở đây.
8. Restart từng instance bằng chính config cũ, kiểm tra từng key/value, thu thập kết quả.
9. Ghi JSON và in bảng; trả các hàng cho `main()` cập nhật summary của run.
10. Trong `finally`, đóng tài nguyên và chỉ cleanup các instance xác minh được quyền sở hữu.

### 3.3. Vì sao đoạn sau ACK phải ngắn?

Cửa sổ mặc định là: delta hoàn tất ACK của hai bên, delay yêu cầu, gửi tín hiệu AOF rồi RDB. Không chèn `INFO`, ghi JSON hoặc kiểm tra qua mạng vào đoạn này. Nếu chèn, AOF có thêm cơ hội fsync và phép đo "delay 0" dễ bị hiểu sai.

`write_both()` hoàn tất khi hai worker đều trả kết quả; mỗi bên có timestamp ACK riêng. Vì vậy `ack_to_kill_seconds` tính riêng cho từng instance, không lấy delay nhập vào làm số đo. Timestamp được lấy sau khi `write_range()` đã đọc đủ ACK và đóng kết nối ghi, nên đây là mốc quan sát phía client, không phải thời điểm nội bộ Redis thực thi `SET` cuối.

AOF bị kill trước để không được cộng thêm thời gian kill RDB. Hai tín hiệu vẫn không đồng thời. Tracing thêm mốc wall-clock ngay trước tín hiệu AOF, nên bản tracing có overhead khác bản mặc định.

### 3.4. Xử lý lỗi và cleanup

Mode được thêm vào danh sách `attempts` **trước** lúc start, để startup lỗi giữa chừng vẫn có cơ hội cleanup. Cleanup từ chối instance không xác minh được; có thể in cảnh báo và cần người chạy kiểm tra, không dùng kill diện rộng.

`main()` cập nhật CSV trong `finally` của mỗi trial từ danh sách các trial đã hoàn tất. Trial lỗi giữa chừng không được ghi thành kết quả thành công; các trial trước vẫn còn. Trong cùng run, summary được cập nhật; lần gọi script mới tạo run khác nên không ghi đè kết quả cũ.

`SHUTDOWN NOSAVE` chỉ dùng khi cleanup sau đo hoặc khi thoát lỗi, không phải cơ chế tạo crash của phép thử thành công. Với AOF, shutdown vẫn có thể đồng bộ file; vì vậy trace ban đầu được đóng và phân tích **trước restart**, không lấy fsync của cleanup để xác nhận trước crash.

## 4. `redis_client.py`: gửi lệnh và kiểm chứng dữ liệu

### 4.1. Adapter redis-py và kiểu dữ liệu trả về

`create_client()` tạo client loopback với RESP2, DB 0, `decode_responses=False`, timeout kết nối 4 giây và timeout lệnh 15 giây (ghi/kiểm chứng dùng 30 giây). `Retry(NoBackoff(), 0)` tắt gửi lại tự động; không bật health-check định kỳ và không gửi metadata tên thư viện qua CLIENT SETINFO. Mỗi thao tác hoặc nhóm ghi/kiểm tra dùng context manager để đóng client/pool do nó sở hữu.

| Lệnh/API | Giá trị Python | Ý nghĩa với script |
|---|---|---|
| PING, BGSAVE, SET | `bool` khi thành công | Kiểm tra `is True`, không so `PONG`/`OK`/thông báo BGSAVE |
| DBSIZE | `int` | Đếm số key |
| INFO | `dict`, bộ đếm thường là `int` | `rdb_bgsave_in_progress == 0`, không so chuỗi `"0"` |
| CONFIG GET | `dict` với key/value chuỗi | Lấy trực tiếp theo tên cấu hình |
| MGET | `list[bytes hoặc None]` | Giữ so sánh value dạng bytes, phân biệt key thiếu |
| Lệnh/kết nối lỗi | Exception của redis-py | `RedisError` trong adapter là alias của exception gốc |

`redis()` dùng `execute_command()` cho các lệnh điều phối; `get_info()` gọi `info()`, `get_config()` gọi `config_get()`. Không tự pack/unpack giao thức trên socket nữa. `redis_ping()` bắt lỗi kết nối/Redis để phục vụ polling readiness.

Dependency ghim trong [requirements.txt](requirements.txt), cài qua virtualenv theo README. Phiên bản 5.3.1 giữ tương thích với Redis 7.0 và Python 3.9+ của bài lab; không tự nâng phiên bản hoặc cài thêm parser tăng tốc khi muốn so timing dưới cùng điều kiện. Bộ đọc AOF riêng không dùng API nội bộ của thư viện.

### 4.2. Ghi workload

`write_range(port, begin, end)` tạo key `demo:{i:08d}` và value `value:{i:08d}`. Baseline dùng chỉ số `[0, baseline)`, delta dùng `[baseline, baseline + delta)`, nên không ghi đè nhau.

Mỗi kết nối gửi pipeline tối đa 250 SET/lô bằng `pipeline(transaction=False)`. `execute()` nhận đầy đủ phản hồi; script kiểm tra số phản hồi đúng và từng kết quả `is True` rồi mới ghi mốc ACK sau lô cuối. Phản hồi thiếu, False hoặc exception làm trial lỗi, không báo hoàn tất. Đặt `transaction=False` là có chủ ý: pipeline mặc định của redis-py dùng MULTI/EXEC, sẽ đổi workload cũ.

`write_both()` dùng hai worker gửi cùng workload tới hai instance độc lập. Điều này giảm độ lệch do ghi hết bên này mới ghi bên kia, không có nghĩa hai bên hoàn tất cùng lúc hoặc Redis xử lý lệnh dữ liệu song song trong một instance.

### 4.3. Kiểm tra sau restart

`verify_range()` dùng MGET tối đa 200 key/lô, so sánh value với giá trị đã biết. Phân loại đúng, thiếu (`None`), sai value; chia key thiếu thành baseline/delta; giữ tối đa 20 ID mẫu cho mỗi nhóm thiếu/sai. Cuối cùng đo thêm DBSIZE.

Quan hệ cần giải thích:

- `verified_correct + missing_keys + corrupt_keys = baseline + delta`.
- `not_recovered_keys = missing_keys + corrupt_keys`.
- `missing_baseline + missing_delta = missing_keys`.
- DBSIZE không phát hiện value sai và có thể bao gồm key ngoài tập mong đợi nếu có client khác ghi vào. Vì vậy cần dataset cô lập và kiểm tra value, không chỉ đếm.

`collect_info()` chỉ lấy dữ liệu vào dict; thao tác ghi JSON thuộc `results.py`. INFO trong JSON mới giữ kiểu native redis-py: số nguyên và dict lồng nhau thay vì mọi value là chuỗi. Các trạng thái INFO sau restart phản ánh instance đã phục hồi; không dùng chúng thay cho trạng thái trước crash.

## 5. `redis_instance.py`: config, checkpoint và tín hiệu an toàn

### 5.1. Config và start

`MODES` cố định RDB 6380 và AOF 6381. `render_config()` đọc template ở `redis/`, thay `@PID_FILE@`, `@LOG_FILE@`, `@DATA_DIR@` bằng đường dẫn trial đã quote, rồi tạo config thực và thư mục data. Restart dùng lại chính config này.

`start_instance()` từ chối port đang mở, gọi `redis-server` với config, chờ PING và xác minh PID. Khi có tracer, dùng `trace.launch()` thay cho gọi Redis trực tiếp. `startup_ms` bao gồm tạo tiến trình, kiểm tra và polling tới 50 ms/lượt; đây không phải phép đo riêng bộ nạp RDB/AOF.

`verify_persistence_config()` kiểm tra qua CONFIG GET: cả hai tắt auto-save; RDB không AOF; AOF bật appendonly, everysec, auto rewrite bằng 0. `save ""` không cấm gọi BGSAVE thủ công.

### 5.2. Vì sao checkpoint phải kiểm tra nhiều điều kiện?

`checkpoint_rdb()` ghi nhận bộ đếm save trước, gọi BGSAVE, polling tối đa 60 giây, kiểm tra không còn save đang chạy, trạng thái `ok`, bộ đếm tăng nếu có trường đó, và `dump.rdb` tồn tại.

Phản hồi "Background saving started" được redis-py chuyển thành `True`, chỉ xác nhận đã nhận yêu cầu. Trạng thái `ok` đơn lẻ có thể thuộc lần save trước. Các kiểm tra kết hợp với bộ đếm và cờ tiến độ dạng số tránh cho delta bắt đầu khi snapshot chưa hoàn tất hoặc không tạo được snapshot mới.

### 5.3. Danh tính tiến trình và kill

`check_pid()` đối chiếu port/PID trong INFO, pidfile và tên process `/proc/<pid>/comm`. `process_start_ticks()` đọc trường 22 của `/proc/<pid>/stat`, đại diện thời điểm process được tạo, giúp phát hiện PID bị tái sử dụng.

`open_verified_pidfds()` thực hiện việc xác minh trước delta. Nếu có `os.pidfd_open` và `signal.pidfd_send_signal`, script pin process bằng pidfd; nếu không thì giữ PID/start ticks để kiểm tra lại trước kill. `kill_verified_process()` gửi SIGKILL và ghi mốc monotonic ngay sau lời gọi gửi tín hiệu. `wait_dead()` kiểm tra port đã đóng trước khi restart.

Pidfd tốt hơn giữ một số PID đơn thuần vì PID có thể được tái cấp phát. Fallback start-time check giảm rủi ro nhưng vẫn có khe thời gian giữa kiểm tra và gửi tín hiệu. Kiểm tra port cũng không phải khóa độc quyền chống chương trình khác tranh port. Đây là lab cô lập, không phải bộ quản lý process an toàn trước tác nhân cạnh tranh tùy ý.

### 5.4. Dừng instance sau đo

`stop_owned_instance()` chỉ shutdown nếu PING được và kiểm tra danh tính khớp. Không dùng killall/pkill, không tự đụng Redis ở port khác. Cleanup có thể bỏ qua khi danh tính không rõ; người chạy cần đọc cảnh báo, không coi việc bỏ qua là đã dừng chắc chắn mọi process.

## 6. `results.py`: lưu và trình bày kết quả

`create_run_dir()` tạo `results/run-<UTC>-<id>/`. UTC giúp ghi thời điểm độc lập múi giờ, hậu tố do `mkdtemp()` tạo giúp không trùng khi gọi trong cùng giây. Bên trong có các trial riêng; phần timestamp của trial hiện dùng giờ local. Tên thư mục chỉ để tổ chức, không dùng tính ACK->kill.

`write_json()` giữ kết quả chi tiết. `folder_bytes()` cộng kích thước logic các file trong data directory, không đo dung lượng block vật lý, RAM hay số byte đã fsync. Tổng AOF bao gồm base, incremental và manifest.

`write_summary()` giữ 8 cột mặc định:

| CSV | Nhãn terminal | Cách đọc |
|---|---|---|
| `trial` | Trial ở đầu bảng | Thứ tự trial trong run |
| `mode` | Mode | RDB/AOF |
| `delay_seconds` | Delay(s) | Khoảng chờ yêu cầu |
| `expected_dbsize_before` | Expected | Số SET đã ACK, không phải đo DBSIZE trước kill |
| `verified_correct_after` | Correct | Key tồn tại, đúng value |
| `missing_keys` | Missing | Key không tồn tại |
| `corrupt_keys` | Corrupt | Key tồn tại, sai value |
| `ack_to_kill_seconds` | ACK(ms) | CSV lưu giây; terminal nhân 1.000 và làm tròn 3 số lẻ |

Khi bật tracing, thêm cột thứ 9 `delta_fsync_status` và nhãn terminal `Fsync`. `save_trial_results()` ghi JSON đầy đủ trước rồi in bảng ngắn; bỏ cột khỏi CSV không có nghĩa bỏ thông tin khỏi JSON. CSV dùng UTF-8 và newline LF.

JSON của trial mới thêm `redis_py_version` để phân biệt phiên bản client. CSV vẫn 8/9 cột, không thay đổi tên/đơn vị hoặc sửa file kết quả cũ. Đổi client có thể đổi timing; kết quả trước migration không được diễn giải như đã đo bằng client mới.

## 7. `fsync_trace.py`: xác nhận điều gì và bằng cách nào?

### 7.1. Vai trò của `AofTrace`

`launch()` chạy Redis dưới strace từ lúc khởi động, thay vì attach vào process đang chạy. Cách này theo dõi cả daemon và thread nền, không cần tự gọi sudo; chính sách ptrace của máy vẫn có thể chặn.

Các flag chính:

| Flag | Mục đích |
|---|---|
| `-ff` | Theo fork/thread, mỗi PID/TID một file trace |
| `-ttt` | Timestamp epoch để so với mốc trước kill |
| `-T` | Thời lượng syscall, suy ra thời điểm hoàn tất |
| `-yy` | Hiện đường dẫn gắn với file descriptor |
| `-s 0` | Giảm nội dung chuỗi được dump, tránh ghi toàn payload vào trace |
| `-e trace=write,writev,fsync,fdatasync` | Chỉ theo các syscall cần đối chiếu |

`mark_before_kill()` chụp mốc **trước** gửi tín hiệu, nghiêm ngặt hơn lấy mốc sau kill. Nó so thời gian wall-clock đã trôi với monotonic; sai lệch từ 10 ms trở lên làm mất điều kiện xác nhận. `finish()` đợi tracer kết thúc/drain file sau crash, trước restart. `close()` thu hồi tracer khi kết thúc/lỗi.

### 7.2. Các lớp kiểm tra trong `analyze()`

1. Kiểm tra mốc kill và tính nhất quán đồng hồ. Không đủ thì `Unknown`.
2. Yêu cầu đúng một incremental AOF trong `appendonlydir`, phù hợp cấu hình không rewrite.
3. Dùng `aof_reader.read_command()` đọc RESP từ incremental, chỉ chấp nhận SELECT DB 0 và SET theo workload; đối chiếu đủ key/value mong đợi.
4. Tìm syscall trong các file trace liên quan **đúng đường dẫn incremental**. Ghi socket, log hoặc fsync file khác không được tính.
5. Đối chiếu các write/writev thành công; tổng byte trả về phải bằng độ dài incremental. Dòng chưa hoàn tất/không parse được, ghi lỗi hoặc timing mơ hồ làm kết quả `Unknown`.
6. Tìm fsync/fdatasync trả về 0, bắt đầu sau lần ghi cuối đã đối chiếu và kết thúc trước mốc trước kill. Có khoảng cách an toàn 2 microsecond ở hai biên vì timestamp làm tròn.

Đọc được toàn bộ incremental mới là một lớp kiểm tra nội dung. Bằng chứng xác nhận fsync đến từ syscall đồng bộ tương ứng, không đến từ việc file đọc được hoặc có đủ 3.000 key.

### 7.3. Điều kiện xác nhận, viết dưới dạng thời gian

Gọi `W` là thời điểm hoàn tất muộn nhất của các ghi incremental đã đối chiếu, `S` là lúc bắt đầu sync, `E` là lúc sync hoàn tất, `K` là mốc trước gửi kill. Bộ phân tích đòi hỏi:

```text
sync trả về 0
S > W + 2 microsecond
E < K - 2 microsecond
```

Điều kiện `S > W` cố ý thận trọng: không suy luận độ bao phủ từ một fsync bắt đầu trước/chồng lấn với ghi cuối. Điều này có thể bỏ lỡ một lần sync thực tế đã bao phủ dữ liệu; đổi lại tránh xác nhận quá mức từ trace chưa rõ.

### 7.4. Trạng thái và giới hạn

| Trạng thái | Tình huống điển hình | Không được suy ra |
|---|---|---|
| Confirmed | Đủ nội dung/byte và có sync thành công đúng khoảng thời gian | Mọi thiết bị chắc chắn sống sót trước mất nguồn |
| Not confirmed | Trace và ghi đối chiếu được nhưng không có sync đáp ứng điều kiện | Dữ liệu chắc chắn chưa bền hoặc chắc chắn sẽ mất |
| Unknown | Trace thiếu, syscall chưa xong, thiếu delta, clock lệch hoặc định dạng chưa hỗ trợ | Có hay không fsync thành công |
| N/A | Hàng RDB | Kết luận về fsync của snapshot RDB |

`fdatasync` đồng bộ dữ liệu file và metadata cần để đọc dữ liệu, không nhất thiết mọi metadata như fsync; cả hai đều phù hợp mục tiêu quan sát đồng bộ nội dung AOF ở đây.

Bộ phân tích được thiết kế cho workload SET/SELECT kiểm soát với một incremental, không phải công cụ giám định mọi AOF. Workload có DEL, transaction, TTL hoặc rewrite cần thiết kế phân tích khác. Chương trình không chứng minh riêng độ bền của manifest/thay đổi tên file, cache thiết bị hoặc toàn bộ chuỗi lưu trữ trước mất nguồn.

Output chi tiết `aof/fsync-evidence.json` và trace gốc vẫn được giữ **local** trong results. Báo cáo chung chỉ trình bày phương pháp, trạng thái và kết quả, không cần đính kèm chúng. Không bỏ code ghi các file local vì chúng hữu ích khi tự kiểm tra.

### 7.5. Vì sao vẫn có `aof_reader.py` sau khi dùng redis-py?

redis-py đọc phản hồi qua mạng, còn phép xác nhận fsync cần kiểm tra byte trong **file incremental** sau crash/trước restart. `read_command()` chỉ đọc array các bulk string, kiểm tra độ dài và CRLF, trả `list[bytes]`. Nó từ chối dữ liệu thiếu, độ dài âm, array rỗng hoặc dạng RESP ngoài phạm vi này bằng `ValueError`; bộ phân tích chuyển thành `Unknown` thay vì suy đoán.

Bộ đọc không tạo kết nối và không phụ thuộc thư viện redis-py; không còn `resp_request()` hoặc parser phản hồi mạng tự viết. Tính hợp lệ nghiệp vụ SELECT/SET và các giá trị mong đợi vẫn do `fsync_trace.analyze()` kiểm tra.

## 8. `persistence_crash.sh`: dạy Linux/Redis theo 10 bước

### 8.1. Các phần nền tảng của Bash

- `set -euo pipefail`: hỗ trợ phát hiện lỗi lệnh, biến chưa gán và pipeline; không thay thế kiểm tra nghiệp vụ ở từng bước.
- Associative arrays lưu port, PID, start ticks và mode đã thử khởi động.
- `show()` in lệnh được quote trước khi chạy; `step()` giải thích rồi chờ Enter, trừ khi có `--auto`.
- `rcli()` dùng redis-cli raw, báo lỗi Redis và timeout 5 giây; `field()` trích trường INFO bằng awk.
- `owned_pid()` đối chiếu INFO, runtime config, pidfile, tên process và start ticks trước tín hiệu/cleanup.
- Trap EXIT/INT/TERM cố cleanup instance đã xác minh. Không thể bảo đảm cleanup nếu chính shell bị SIGKILL.
- `mktemp -d` tạo thư mục lesson riêng; `tee` giữ transcript lệnh/kết quả trong `lesson.log`.

### 8.2. Mười bước và điều cần giải thích

| Bước | Lệnh/công việc | Ý nghĩa khi trình bày |
|---|---|---|
| 1 | uname, version, ss | Biết đang thao tác ở đâu, port nào dùng |
| 2 | Render config, cat | Config thực trỏ đúng data directory riêng |
| 3 | redis-server, PING, ps, CONFIG GET | Phân biệt file config và process đang chạy |
| 4 | SET 3 key baseline, DBSIZE | Cùng dữ liệu, mỗi SET phải OK |
| 5 | BGSAVE, INFO, ls | Chờ checkpoint thành công, không chỉ chờ chấp nhận lệnh |
| 6 | SET 2 delta, GET/DBSIZE | Cả hai đang có 5 key trong RAM |
| 7 | Xác minh PID, kill -9, đợi port đóng | Tạo crash process, không phải shutdown bình thường |
| 8 | Start đúng config cũ, quan sát PID mới | Khôi phục phải dùng lại dữ liệu đã ghi |
| 9 | EXISTS, GET từng key, summary | Tách key thiếu baseline/delta và value sai |
| 10 | tail log, kết luận | Nối kết quả với cơ chế nạp lại, sau đó cleanup |

Key của bài Bash là `lesson:baseline:1..3`, `lesson:delta:1..2`; khác tên key của Python. Kỳ vọng RDB giữ 3 key baseline, không có snapshot cho 2 delta; AOF có thể giữ đủ 5 key sau process crash.

Bash ghi SET tuần tự qua từng lần gọi redis-cli, hiện kết quả và có pause trước kill. Mỗi thao tác cho AOF thêm thời gian ghi/fsync. Ngay cả `--auto` cũng chỉ bỏ Enter, không biến bài học thành benchmark.

CSV riêng gồm 7 cột `mode, expected_before, dbsize_after, verified_correct, missing_baseline, missing_delta, wrong_values`. Bài này không đo ACK->kill hoặc fsync; không có cột Fsync. File config/log/data và transcript nằm trong `results/lesson-<UTC>-<id>/`, không ghi đè run Python.

## 9. Tests kiểm tra được gì?

Bốn file test kiểm tra các trách nhiệm riêng. Đây là unit tests có mock/trace mẫu, **không phải các lần crash Redis thật**. Cần cài requirements trước, nhưng không cần Redis server đang chạy:

- [test_run_trials.py](tests/test_run_trials.py): config, lưu kết quả, cộng dung lượng file, phân loại missing/value sai, thứ tự ACK–kill, không thêm probe ở cửa sổ mặc định và tính riêng biệt của run.
- [test_redis_client.py](tests/test_redis_client.py): callback kiểu native của thư viện thật, cấu hình không retry, pipeline không transaction, chia lô, chỉ timestamp sau ACK cuối và xử lý phản hồi/lỗi.
- [test_aof_reader.py](tests/test_aof_reader.py): command RESP liên tiếp, bulk string rỗng/binary, dữ liệu sai/truncated; không phụ thuộc client mạng.
- [test_fsync_trace.py](tests/test_fsync_trace.py): xác nhận sync đúng điều kiện; từ chối sync file khác, sync quá sớm/quá muộn hoặc chồng lấn, lỗi sync, syscall chưa hoàn tất, thiếu delta/byte và clock không nhất quán.

Chạy từ gốc repo sau khi kích hoạt virtualenv:

```bash
python3 -m unittest discover -s demos/04-persistence-crash/tests -v
python3 demos/04-persistence-crash/scripts/run_trials.py --help
bash -n demos/04-persistence-crash/scripts/persistence_crash.sh
```

Test phụ thuộc `/proc` sẽ skip ngoài Linux. `bash -n` chỉ kiểm tra cú pháp, không chứng minh Redis được khởi động hoặc cleanup đúng trong mọi tình huống. Vẫn cần trial thật trên máy lab để có số liệu.

## 10. Các câu hỏi cần trả lời được khi bảo vệ

**Vì sao dùng redis-py?** Để bỏ phần giao thức socket tự viết và tập trung vào persistence. Vẫn giữ kiểm tra từng kết quả SET, mốc ACK, xác minh PID và bộ đọc file AOF riêng. Thư viện không tự chứng minh độ bền dữ liệu.

**Vì sao không để pipeline/retry mặc định?** Pipeline mặc định dùng transaction; retry có thể gửi lại lệnh sau lỗi, làm thay đổi workload và timing. Demo chọn rõ `transaction=False`, RESP2 và không retry để giữ phép đo dễ diễn giải.

**Vì sao không chỉ dùng DBSIZE?** Cùng số key vẫn có thể sai value hoặc sai tập key. MGET đối chiếu từng cặp với workload biết trước.

**ACK có nghĩa dữ liệu đã bền không?** ACK xác nhận lệnh thành công theo chính sách hiện tại. Với everysec, ACK không phải xác nhận fsync từng SET.

**Corrupt có nghĩa AOF hỏng không?** Ở bảng output, chỉ có nghĩa key tồn tại nhưng value khác mong đợi. Cần kiểm tra khác để kết luận file hỏng.

**Vì sao BGSAVE chỉ tạo baseline, còn AOF chứa cả baseline/delta?** Hai instance độc lập; chỉ RDB checkpoint sau baseline. AOF base tạo lúc rỗng, không rewrite nên incremental nhận toàn bộ ghi tiếp theo.

**Vì sao Delay(s) và ACK(ms) khác nhau?** Delay bắt đầu sau khi hai worker xong; ACK timestamp riêng từng bên, còn có scheduler và chi phí gửi tín hiệu.

**Vì sao AOF đủ key ở delay 0 vẫn hợp lý?** write có thể đã đưa byte vào page cache. Kill Redis không xóa cache của hệ điều hành.

**Làm sao tránh lấy fsync lúc restart làm bằng chứng trước crash?** Chỉ trace instance ban đầu; đợi trace kết thúc và phân tích sau kill, trước restart.

**Confirmed có chứng minh dữ liệu đã xuống SSD vật lý không?** Nó chứng minh syscall đồng bộ trả thành công theo giao diện hệ điều hành. Để kết luận trước mất nguồn cần đánh giá cả filesystem, tầng lưu trữ, thiết bị và phép thử phù hợp.

**Tại sao giữ JSON/trace local dù bỏ bằng chứng khỏi report?** Chúng phục vụ tự kiểm tra và chẩn đoán. Báo cáo chung đọc độc lập bằng kết quả/phương pháp đã trình bày, không phụ thuộc đường dẫn local.

**Nếu muốn chứng minh AOF mất một giây dữ liệu?** Demo này không bảo đảm có mất dữ liệu. Everysec không phải cam kết lần nào cũng mất một giây; không sửa timing hoặc số liệu để ép kết quả mong muốn.
