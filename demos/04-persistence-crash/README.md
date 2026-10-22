# Demo 04 — Redis persistence crash test: RDB-only vs AOF `everysec`

> **Mục tiêu gốc:** Giả lập sự cố bằng `kill -9` ngay sau khi ghi dữ liệu, rồi so sánh lượng dữ liệu phục hồi giữa RDB-only và AOF `appendfsync everysec`.
>
> **Chính xác về failure model:** `kill -9` tương đương `SIGKILL` làm chết **tiến trình Redis**, **không** làm máy mất điện. OS page cache vẫn còn. Kết quả demo **không** thể dùng để khẳng định lượng dữ liệu mất khi cắt nguồn thật.

## 1. Thiết kế và giả thuyết

| | RDB-only | AOF-only |
|---|---|---|
| Địa chỉ | `127.0.0.1:6380` | `127.0.0.1:6381` |
| `appendonly` | `no` | `yes` |
| `save` | `""` (tắt snapshot tự động) | `""` |
| Điều kiện lưu | `BGSAVE` **một lần sau baseline** | Ghi AOF, `appendfsync everysec` |
| Rewrite AOF | Không áp dụng | Tắt tự động trong demo |
| Dataset đầu vào | `baseline` + `delta` | Cùng key/value như RDB |

Với `baseline=2000`, `delta=1000`:

1. Ghi `demo:00000000` đến `demo:00001999` vào **cả hai Redis**; chờ `SET` ACK.
2. Gọi `BGSAVE` trên **RDB** và kiểm tra snapshot hoàn thành. Đây là checkpoint cố định chứa 2.000 key.
3. Thu thập thông tin Redis, xác thực PID và chuẩn bị cho crash **trước khi** gửi nhóm ghi cuối.
4. Ghi tiếp `demo:00002000` đến `demo:00002999` vào hai instance, **đọc đủ ACK**.
5. Chờ delay nếu có; gửi `SIGKILL` cho **AOF trước, RDB ngay sau**. Không chạy `INFO`, `DBSIZE`, không ghi JSON vào khoảng ACK->SIGKILL ở chế độ mặc định.
6. Khi hai tiến trình đã chết, ghi kích thước file persistence; restart **bằng đúng file cấu hình và data directory ban đầu**; kiểm tra từng key/value và tạo báo cáo.

**Kỳ vọng có điều kiện:** Nếu RDB checkpoint thành công và không có checkpoint thứ hai, RDB khôi phục 2.000 key và mất 1.000 key delta. AOF **có thể** phục hồi đủ 3.000 key sau `SIGKILL`, kể cả khi chưa kịp `fsync` theo chu kỳ, bởi dữ liệu vẫn có thể tồn tại trong page cache. AOF không được bảo đảm mất chính xác 0 hoặc 1 giây dữ liệu. Đây là dự đoán, **không phải kết quả đo**.

Cấu hình `save ""` cùng một `BGSAVE` thủ công được dùng để **kiểm soát checkpoint** trong phép so sánh, không đại diện cho cấu hình RDB production chạy snapshot định kỳ.

## 2. Điều kiện chạy

- Ubuntu/Linux với `/proc` được mount; **máy lab**, không chạy trên Redis production.
- Redis Open Source **7.0 trở lên**, Python **3.9 trở lên**.
- Hai port `6380`, `6381` còn trống; quyền tạo tiến trình và gửi tín hiệu cho chính tiến trình mình tạo.
- Đủ RAM, dung lượng trống; tránh chạy hai bản script đồng thời. Mỗi trial có thư mục dữ liệu riêng.
- Bản Python dùng **redis-py**, cài theo [requirements.txt](requirements.txt) trong virtualenv; bản Bash không cần dependency Python.

Có hai nhóm dependency: công cụ hệ thống cài bằng `apt`, thư viện Python cài bằng `pip` trong virtualenv. Không thêm `redis-server`, `redis-tools`, `strace` hoặc `iproute2` vào requirements Python.

| Thành phần | Cách cài | Khi nào cần |
|---|---|---|
| `redis-server` | `apt` | Mọi crash trial |
| `redis-tools` (`redis-cli`) | `apt` | Kiểm tra thủ công, bài Bash |
| `python3`, `python3-venv` | `apt` | Bản Python và virtualenv |
| `redis` (redis-py) | `pip install -r requirements.txt` | Bản Python |
| `strace` | `apt` | Chỉ khi dùng `--trace-fsync` |
| `iproute2` (`ss`) | `apt` | Bài Bash |

Quy trình đầy đủ theo từng bước nằm tại [linux/commands.md](../../linux/commands.md). `linux/setup.sh` chỉ cài Redis/server tools, chưa cài đủ dependency của demo 04.

Trên Ubuntu, chạy từ thư mục gốc repo:

```bash
sudo apt update
sudo apt install -y redis-server redis-tools python3 python3-venv
redis-server --version
python3 --version
# Chạy từ thư mục gốc repository, không dùng sudo pip.
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r demos/04-persistence-crash/requirements.txt
```

Cài thêm nếu dùng các chế độ tùy chọn:

```bash
# Quan sát fsync bằng --trace-fsync
sudo apt install -y strace
# Bài Bash persistence_crash.sh
sudo apt install -y iproute2
```

Mỗi terminal mới cần `source .venv/bin/activate` trước khi chạy bản Python hoặc unit tests. Không dùng lại virtualenv được tạo bằng Python Windows trong WSL. File requirements ghim `redis==5.3.1` để giữ khả năng chạy với Redis 7.0 và Python 3.9+; đây là lựa chọn tương thích cho lab, không phải tuyên bố là phiên bản mới nhất. Tham khảo [metadata và compatibility của bản client này](https://pypi.org/project/redis/5.3.1/).

Client được đặt rõ RESP2, không tự retry, không health-check định kỳ; pipeline dùng `transaction=False`. Nếu đổi phiên bản client, cần kiểm thử lại, không gộp timing mới với các phép đo cũ như cùng một điều kiện.

Chương trình không chạm tới Redis mặc định ở `:6379`. Tuy nhiên, nó **cố ý `SIGKILL` các Redis riêng của demo**. Script xác minh PID bằng Redis `INFO`, pidfile, `/proc` và ưu tiên Linux `pidfd` để tránh PID reuse. Không chạy với quyền root nếu không cần.

## 3. Cấu trúc

Cấu hình và tài liệu dùng chung:

- [redis/redis-rdb.conf](../../redis/redis-rdb.conf), [redis/redis-aof.conf](../../redis/redis-aof.conf): template, KHÔNG chạy trực tiếp.
- [report.md](report.md): kết quả thực nghiệm, quy trình và phân tích; không phụ thuộc bằng chứng local.
- [scripts.md](scripts.md): giải thích từng script/module, timing, fsync và câu hỏi bảo vệ.
- [Kịch bản thuyết trình](../../docs/presentation-notes/redis-architecture-persistence-talk.md) và [đề cương slide](../../docs/presentation-notes/redis-architecture-persistence-slides.md): trọng tâm lý thuyết, tổng 7:40 đã gồm video demo 60 giây và phân tích kết quả.
- [Persistence crash review](../../docs/presentation-notes/persistence-crash-review.md): ghi chú phương pháp.
- [Ảnh minh chứng](../../docs/screenshots/04-persistence-crash/).

```text
demos/04-persistence-crash/
├── README.md
├── scripts.md                       # Giải thích mã và chuẩn bị bảo vệ
├── requirements.txt                # Dependency redis-py được ghim phiên bản
├── scripts/
│   ├── run_trials.py                 # CLI và điều phối trial
│   ├── constants.py                 # Mặc định, giới hạn, timeout và ngưỡng đo
│   ├── redis_client.py               # Adapter redis-py, workload, kiểm chứng
│   ├── redis_instance.py             # Config, checkpoint, PID, start/stop/SIGKILL
│   ├── results.py                    # Thư mục run, JSON, CSV và in kết quả
│   ├── fsync_trace.py                # Quan sát write/fsync trước crash (tùy chọn)
│   ├── aof_reader.py                 # Đọc RESP từ file AOF local, không mở socket
│   └── persistence_crash.sh          # Bài thực hành Bash theo từng bước
├── tests/
│   ├── test_run_trials.py
│   ├── test_redis_client.py
│   ├── test_aof_reader.py
│   └── test_fsync_trace.py
└── results/
    ├── .gitkeep
    └── run-<UTC>-<id>/                  # một lần gọi script
        ├── summary.csv                 # chỉ tổng hợp trial của run này
        ├── trial-01-.../
        │   ├── trial-results.json
        │   ├── rdb/
        │   │   ├── rdb.conf             # config thực, dùng lại khi restart
        │   │   ├── redis.pid            # có thể bị xóa khi shutdown
        │   │   ├── redis.log
        │   │   ├── before-delta-info.json
        │   │   ├── after-restart-info.json
        │   │   └── data/dump.rdb
        │   └── aof/
        │       ├── aof.conf
        │       ├── redis.pid
        │       ├── redis.log
        │       ├── before-delta-info.json
        │       ├── after-restart-info.json
        │       └── data/appendonlydir/   # Redis 7+: base/incremental/manifest
        └── trial-02-.../
```

Mỗi lần gọi script tạo một thư mục run riêng bằng timestamp UTC và hậu tố ngẫu nhiên, kể cả khi chạy nhiều lần trong cùng một giây. Mỗi trial có config và data directory riêng; restart dùng lại đúng các đường dẫn đó. Dữ liệu crash test giữ trong demo, không ghi vào `/tmp`.

`summary.csv` được cập nhật sau mỗi trial trong run hiện tại; run mới không ghi đè CSV hoặc trial của run cũ. Nếu một trial lỗi, CSV vẫn chứa các trial đã hoàn tất trước đó. Kết quả runtime được Git bỏ qua và giữ local. Báo cáo chung chứa số liệu, quy trình và phân tích, không đính kèm bằng chứng hoặc liên kết tới file run local.

`run_trials.py` là entry point của bản đo tự động. `redis_client.py` dùng redis-py để giao tiếp Redis, không ghi file; `redis_instance.py` quản lý tiến trình và checkpoint; `results.py` chỉ xử lý artifacts. `fsync_trace.py` dùng bộ đọc file riêng `aof_reader.py`, không dùng parser nội bộ của redis-py. Các module phụ không import ngược file điều phối. Bản dạy lệnh Linux/Redis nằm riêng trong `persistence_crash.sh`.

Các số cấu hình của bản Python nằm trong [scripts/constants.py](scripts/constants.py): mặc định CLI, port, kích thước lô, timeout, giới hạn key mẫu, ngưỡng thời gian của trace và hệ số đổi đơn vị. Giá trị mặc định không đổi. Tham số CLI vẫn ghi đè mặc định như trước; nếu sửa port/host phải đồng bộ template trong `redis/`. Thay đổi batch/timeout/ngưỡng trace làm thay đổi điều kiện đo, không chỉ hình thức mã nguồn. Bản Bash có thiết lập riêng, không tự đọc file Python này.

## 4. Chạy demo

Chạy từ thư mục gốc repository trong Bash/Linux, sau khi kích hoạt virtualenv và cài requirements ở mục 2:

```bash
# Test chuẩn, 3 lần thử với các delay khác nhau
python3 demos/04-persistence-crash/scripts/run_trials.py --trials 3 --baseline 2000 --delta 1000 --delays 0,0.2,1.5

# Kiểm thử nhanh 1 trial
python3 demos/04-persistence-crash/scripts/run_trials.py --trials 1 --baseline 100 --delta 30 --delays 0

# Quay video hoặc kiểm tra từng bước: dừng tại checkpoint TRƯỚC ghi delta
python3 demos/04-persistence-crash/scripts/run_trials.py --trials 1 --pause-after-checkpoint --delays 0

# Nếu rất cần số DBSIZE được đo đúng sau delta: tùy chọn này làm TĂNG ACK->kill
python3 demos/04-persistence-crash/scripts/run_trials.py --trials 1 --measure-prekill-dbsize --delays 0
```

Đường dẫn template và kết quả được tính từ vị trí script, không phụ thuộc thư mục terminal hiện tại. Nếu đang ở thư mục demo, dùng `python3 scripts/run_trials.py` với các tham số tương tự. Hai port `6380`/`6381` phải trống; không khởi động Redis thủ công trước script.

Trong chế độ `--pause-after-checkpoint`, khi script in thông báo đợi Enter, có thể mở terminal khác để xem hai cấu hình và trạng thái baseline. Sau đó nhấn Enter để script thực hiện ghi delta và `SIGKILL` liền mạch. **Không** mở terminal để quan sát giữa ACK delta và thời điểm kill vì sẽ làm chậm phép thử.

### Quan sát fsync trước crash trên Redis 7.0+

Cài `strace` rồi bật chế độ quan sát riêng (không cần nâng Redis lên 7.2):

```bash
sudo apt install -y strace
python3 demos/04-persistence-crash/scripts/run_trials.py \
  --trace-fsync --trials 3 --baseline 2000 --delta 1000 --delays 0,0.2,1.5
```

Script chạy instance AOF ban đầu dưới `strace`, theo dõi cả các thread từ lúc khởi động. Không cần chạy Python bằng `sudo` hoặc tự attach tracer. Nếu môi trường chặn ptrace, script báo lỗi; không tự đổi chính sách bảo mật của máy. Redis phục hồi và bước cleanup không nằm trong trace ban đầu.

Sau SIGKILL và **trước restart**, script đối chiếu:

1. Incremental AOF chứa đủ key/value đã được ACK của workload.
2. Các syscall write/writev thành công trong trace bao phủ đủ số byte của file này.
3. Có fsync/fdatasync **trên đúng file incremental**, bắt đầu sau khi lần ghi delta cuối đã hoàn tất, trả về thành công trước thời điểm script chuẩn bị gửi SIGKILL.

Trace dùng timestamp microsecond, có biên phân tách nhỏ để tránh kết luận từ sự kiện quá sát nhau. Nếu đồng hồ wall-clock thay đổi đáng kể so với monotonic hoặc trace không đủ rõ, kết quả là Unknown.

| `Fsync` trên terminal / `delta_fsync_status` trong CSV | Cách hiểu |
|---|---|
| `Confirmed` | Có syscall đồng bộ thành công chứng minh bao phủ toàn bộ delta trước crash |
| `Not confirmed` | Trace đủ để kiểm tra các lần ghi nhưng không có đồng bộ đáp ứng điều kiện; không suy ra chắc chắn dữ liệu chưa xuống thiết bị (Có thể dữ liệu chưa được ghi xuống thiết bị, hoặc hệ điều hành đã tự ghi xuống thiết bị trong nền, nhưng script không có sự kiện fsync phù hợp để xác nhận) |
| `Unknown` | Thiếu bằng chứng, cú pháp trace chưa hỗ trợ, syscall chưa hoàn tất, thiếu delta hoặc timing không rõ |
| `N/A` | Dòng RDB; chế độ này chỉ quan sát fsync AOF |

Chỉ khi bật `--trace-fsync`, CSV thêm cột thứ 9 `delta_fsync_status` và terminal thêm nhãn `Fsync`. Không bật thì CSV vẫn có 8 cột như trước. Các file bổ sung trong mỗi trial:

```text
trial-.../
├── aof-trace/
│   ├── aof.<pid-or-thread-id>   # syscall gốc
│   └── strace.stderr           # lỗi của tracer nếu có
└── aof/
    └── fsync-evidence.json     # trạng thái, lý do, byte count và timeline
```

`trial-results.json` giữ thêm `fsync_tracing`, `delta_fsync_status` và bằng chứng chi tiết cho AOF. Đây là xác nhận đồng bộ file ở mức hệ điều hành, không phải thử nghiệm mất nguồn của SSD, máy Windows hoặc WSL. Tracing làm thay đổi timing; không gộp timing của run có tracing với các run không tracing.

Bộ quan sát bổ sung dùng baseline 100, delta 30: AOF phục hồi đủ 130 key ở cả ba trial; delay 0 và 0,2 giây là `Not confirmed`, delay 1,5 giây là `Confirmed`. Xem bảng số liệu trong [báo cáo demo](report.md). Đây là quan sát đã thu được, không phải cam kết trạng thái cho mọi lần chạy.

### Bản Bash để dạy từng lệnh

Chạy trong terminal Ubuntu/WSL, từ thư mục gốc repo:

```bash
bash demos/04-persistence-crash/scripts/persistence_crash.sh
```

Bản này không cần Python. Cần Bash 4+, Redis 7+ (`redis-server`, `redis-cli`), `ss` (gói `iproute2`) và các công cụ Linux thông dụng. Nếu chưa có:

```bash
sudo apt update
sudo apt install -y redis-server redis-tools iproute2
```

Script hiện lệnh trước khi chạy, giải thích ngắn và đợi Enter ở mỗi bước:

1. Xem môi trường bằng `uname`, `redis-server --version`, `ss`.
2. Tạo config thực từ hai template trong `redis/`, đọc lại bằng `cat`.
3. Khởi động hai instance port 6380/6381, kiểm tra `PING`, `ps`, `CONFIG GET`.
4. Ghi 3 key baseline bằng `SET`, đếm bằng `DBSIZE`.
5. Gọi `BGSAVE`, đợi snapshot hoàn thành, xem `INFO persistence` và `dump.rdb`.
6. Ghi thêm 2 key delta, quan sát cả hai instance đang có 5 key.
7. Xác minh PID/config, dùng `kill -9` với AOF trước rồi RDB; quan sát file persistence.
8. Restart bằng đúng config/data cũ, xem PID mới.
9. Kiểm tra từng key/value và in bảng phục hồi.
10. Đọc log bằng `tail`, giải thích kết quả; sau đó script dừng các instance đã phục hồi bằng `SHUTDOWN NOSAVE`.

Mỗi lần chạy tạo `results/lesson-<UTC>-<id>/` riêng, chứa `lesson.log` (lệnh và kết quả), `summary.csv`, config/log/data của `rdb/` và `aof/`. CSV bài học dùng các cột đơn giản `mode`, `expected_before`, `dbsize_after`, `verified_correct`, `missing_baseline`, `missing_delta`, `wrong_values`; không phải schema CSV của Python. Script giữ lại toàn bộ artifacts sau khi cleanup tiến trình.

Không chạy đồng thời bản Bash và Python vì cùng dùng port 6380/6381. Script từ chối port đang bận, chỉ gửi tín hiệu tới instance có config/PID phù hợp với thư mục bài học. Có thể dùng Ctrl+C để kết thúc bài học và cleanup các instance đã được xác minh.

Để chạy kiểm tra không cần nhấn Enter:

```bash
bash demos/04-persistence-crash/scripts/persistence_crash.sh --auto
```

Các lần gọi `redis-cli`, hiển thị kết quả và điểm dừng trước SIGKILL cho AOF thêm thời gian ghi/fsync. Vì vậy bản này phục vụ giảng dạy; không đo ACK->kill, không dùng thời gian của nó thay cho số liệu Python trong báo cáo. AOF giữ đủ 5 key sau SIGKILL vẫn là kết quả hợp lệ, không chứng minh độ bền khi mất điện.

## 5. Hiểu chính xác các trường kết quả

CSV Python mới có 8 cột theo thứ tự dưới đây. Tên field giữ nguyên để đọc bằng script; terminal dùng nhãn ngắn tiếng Anh.

| Field CSV | Nhãn terminal | Ý nghĩa |
|---|---|---|
| `trial` | `Trial` | Số thứ tự trial, in một lần phía trên bảng |
| `mode` | `Mode` | RDB hoặc AOF |
| `delay_seconds` | `Delay(s)` | Khoảng chờ yêu cầu sau khi cả hai nhóm ghi đã ACK |
| `expected_dbsize_before` | `Expected` | Số key suy ra từ SET đã ACK, không phải DBSIZE đo ngay trước crash |
| `verified_correct_after` | `Correct` | Số key có value đúng sau restart |
| `missing_keys` | `Missing` | Số key kỳ vọng nhưng MGET trả nil |
| `corrupt_keys` | `Corrupt` | Số key tồn tại nhưng sai value |
| `ack_to_kill_seconds` | `ACK(ms)` | CSV lưu giây; terminal đổi sang mili giây, làm tròn 3 chữ số thập phân |

Ví dụ hiển thị (số liệu từ trial 1 của run chính đã ghi trong báo cáo):

```text
Trial 1:
Mode Delay(s) Expected  Correct  Missing  Corrupt    ACK(ms)
RDB         0     3000     2000     1000        0     14.618
AOF         0     3000     3000        0        0      0.686
Expected = ACKed SETs; ACK(ms) = final ACK -> SIGKILL.
```

`trial-results.json` vẫn lưu đầy đủ dữ liệu, gồm PID, port, baseline/delta, timing gốc, kích thước file, trạng thái persistence và ID key mẫu. Thay đổi này chỉ áp dụng output của các lần chạy mới; CSV cũ và số liệu nguồn của báo cáo không bị sửa. CSV bài học Bash giữ nguyên schema riêng.

Sau migration, JSON của trial mới có thêm `redis_py_version`. Các file INFO mới dùng kiểu dữ liệu do redis-py phân tích: bộ đếm là số nguyên, keyspace có thể là dict lồng nhau, thay vì mọi value đều là chuỗi.

Các trường chi tiết sau chỉ nằm trong JSON của run mới (hoặc CSV cũ):

| Trường | Ý nghĩa |
|---|---|
| `port`, `pid_before`, `pid_after` | Port và PID để đối chiếu tiến trình trước/sau crash |
| `redis_py_version` | Phiên bản client của trial mới; chỉ nằm trong JSON, không làm dài CSV |
| `baseline_keys`, `delta_keys` | Số key theo hai nhóm ghi |
| `dbsize_before_measured` | Chỉ có khi bật `--measure-prekill-dbsize`; thêm overhead |
| `dbsize_after` | `DBSIZE` đo sau restart |
| `not_recovered_keys` | `missing_keys + corrupt_keys`; không đánh đồng với số key mất |
| `missing_baseline`, `missing_delta` | Phân loại key mất theo checkpoint và dữ liệu mới |
| `persistence_bytes_at_crash` | Kích thước các file data **sau khi process chết, trước restart** |
| `persistence_bytes_after_restart` | Kích thước file ngay sau restart/verification |
| `startup_ms` | Thời gian từ gọi start Redis tới `PING` trả lời, bao gồm subprocess/OS/polling; **không phải chỉ thời gian parse RDB/AOF** |
| `initial_startup_ms` | Thời gian khởi động lần đầu trước khi ghi baseline |
| `last_write_ack_epoch`, `kill_epoch` | Timestamp gốc để đối chiếu sự kiện |
| `rdb_last_bgsave_status`, `aof_last_write_status` | Trạng thái đọc từ INFO sau restart; đối chiếu checkpoint trước crash bằng INFO trước delta và log |
| `sample_missing_ids`, `sample_corrupt_ids` | Mẫu ID key bị thiếu hoặc sai value |

`--delays` là thời gian chờ sau khi **cả hai instance** nhận đủ ACK, không phải cam kết thời gian chính xác ACK->kill của mỗi Redis. So sánh bằng cột đo thực tế `ack_to_kill_seconds`.

Dòng lệnh:

```bash
# Script in đường dẫn "Run files"; điền tên run đã chạy vào đây.
run_dir='demos/04-persistence-crash/results/run-<UTC>-<id>'
cat "$run_dir/summary.csv"
find "$run_dir" -type f \( -name 'dump.rdb' -o -name '*.aof*' -o -name '*.manifest' \)
find "$run_dir" -type f \( -name 'before-delta-info.json' -o -name 'after-restart-info.json' \)
```

Các JSON `before-delta-info.json` được lấy **trước nhóm ghi cuối** để không kéo dài cửa sổ ACK->kill; tuyệt đối không chú thích chúng là ảnh chụp `INFO` *ngay trước crash*. File `trial-results.json` có mẫu ID key bị mất/sai để minh họa. Sau khi đo xong, chương trình sẽ `SHUTDOWN NOSAVE` các Redis **đã phục hồi**, không làm sạch Redis trước crash.

## 6. Gợi ý trình bày riêng demo (3–5 phút)

Phần dưới dành cho demo độc lập hoặc tham khảo khi quay. Bài thuyết trình kiến trúc và persistence dùng [kịch bản 7:40](../../docs/presentation-notes/redis-architecture-persistence-talk.md), đã gồm video dựng riêng 60 giây; không chạy demo trực tiếp và không cộng thêm 3–5 phút vào bài chính.

1. Cho xem `redis/redis-rdb.conf` (`appendonly no`, `save ""`) và `redis/redis-aof.conf` (`appendonly yes`, `appendfsync everysec`).
2. Giải thích timeline: baseline -> `BGSAVE` checkpoint -> delta/ACK -> `SIGKILL` -> restart/verify.
3. Chạy với `--pause-after-checkpoint`. Tại lúc pause mở một terminal khác để xem `redis-cli -p 6380 INFO persistence`, sau đó Enter.
4. Hiển thị bảng `results/run-<UTC>-<id>/summary.csv`, minh họa RDB mất bao nhiêu key delta, AOF phục hồi bao nhiêu key, với ACK->kill thực tế.
5. Giải thích **vì sao AOF có thể không mất key sau kill -9**, và vì sao điều này không chứng minh độ bền khi mất điện thật.

Lệnh kiểm tra tại thời điểm pause:

```bash
redis-cli -p 6380 DBSIZE
redis-cli -p 6380 INFO persistence
redis-cli -p 6381 DBSIZE
redis-cli -p 6381 CONFIG GET appendfsync
```

## 7. Những giới hạn bắt buộc phải công bố

- `kill -9` **không** cắt nguồn máy, **không** xoá OS page cache; kết quả không chứng minh power-loss durability.
- `save ""` + 1 `BGSAVE` thủ công nhằm tạo độ lệch checkpoint xác định; RDB snapshot định kỳ ngoài thực tế có thể khác.
- Ghi theo lô/pipeline, kiểm tra từng value, chạy 3 trial và đo chính xác delay cải thiện tái lập nhưng **không loại bỏ** scheduler, I/O, page cache, thiết bị lưu trữ, Redis version.
- Dữ liệu 3.000 key quá nhỏ để kết luận về độ nhanh/chậm của restart hoặc mức sử dụng storage trong production.
- Nếu AOF phục hồi đủ key ở mọi trial, **đó vẫn là kết quả hợp lệ**; không cố ép kịch bản cho AOF mất key bằng cách sửa số liệu.
- Không dùng `killall redis-server`, `pkill redis-server` hoặc `redis-cli SHUTDOWN` thay SIGKILL trong giai đoạn sự cố.

## 8. Kiểm tra script không cần Redis

Cần cài requirements và kích hoạt virtualenv trước; tests không cần Redis server đang chạy.

```bash
python3 -m unittest discover -s demos/04-persistence-crash/tests -v
python3 -m py_compile demos/04-persistence-crash/scripts/run_trials.py
```

Unit tests không thay thế được việc chạy demo end-to-end trên máy có `redis-server`.

## 9. Nguồn chính thức

- [Redis persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [BGSAVE](https://redis.io/docs/latest/commands/bgsave/)
- [INFO](https://redis.io/docs/latest/commands/info/)
- [Redis latency diagnosis](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/)
