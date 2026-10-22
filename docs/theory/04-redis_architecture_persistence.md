# Kiến trúc Redis và Persistence

**Phạm vi:** Redis Open Source; kiến trúc cơ bản áp dụng cho Redis hiện đại, các chi tiết multi-part AOF áp dụng từ Redis 7; phần I/O threading nêu rõ sự khác biệt giữa các phiên bản.  
**Mục tiêu:** Hiểu cách Redis xử lý nhiều kết nối, vì sao có độ trễ thấp, đâu là tác vụ gây blocking, và đánh đổi giữa RDB với AOF về hiệu năng, dung lượng, thời gian khôi phục và nguy cơ mất dữ liệu.

> **Ý chính:** Redis phục vụ nhiều kết nối nhờ event loop và I/O multiplexing, trong khi phần lớn logic thực thi lệnh truy cập dữ liệu vẫn được tuần tự hóa trên main thread. RDB lưu các ảnh chụp trạng thái (snapshot); AOF ghi các thay đổi để phục hồi gần thời điểm sự cố hơn. Không cơ chế nào tự động đảm bảo mất dữ liệu bằng 0 trong mọi tình huống.

---

## 1. Tổng quan kiến trúc Redis

Redis là **in-memory data store**, thường được sử dụng để làm cache, lưu session, bộ đếm, leaderboard, hàng đợi và dữ liệu cần truy cập với độ trễ thấp. Dataset đang được phục vụ chủ yếu nằm trong **RAM**; tùy cấu hình, Redis có thể lưu dữ liệu bền vững hơn trên thiết bị lưu trữ bằng RDB (Redis Database) hoặc AOF (Append Only File).

Ba đặc trưng cần phân biệt:

1. **In-memory:** phần lớn thao tác thông thường truy cập dữ liệu trong RAM, thay vì đọc ngẫu nhiên từ đĩa cho từng yêu cầu.
2. **Event-driven networking:** event loop nhận và điều phối các sự kiện kết nối, đọc/ghi socket, timer và một số công việc nội bộ.
3. **Mostly single-threaded command execution:** phần lớn lệnh thao tác cấu trúc dữ liệu của Redis được thực thi tuần tự, chủ yếu trên main thread. Điều này **không có nghĩa** Redis chỉ có một thread hoặc một process cho mọi tác vụ.

Sơ đồ khái quát (lược bỏ các nhánh tối ưu và tác vụ nội bộ):

```text
Client A --\
Client B ----> TCP sockets --> I/O multiplexing --> Event loop
Client C --/                                      |
                                                  v
                              Read/parse request -> Execute command
                                                        |
                                                        v
                                             In-memory dataset (RAM)
                                                        |
                                                  Build/send reply

           Persistence (nếu bật):
           - RDB: fork child -> tạo snapshot -> lưu storage
           - AOF: ghi bản ghi thay đổi -> fsync theo chính sách
           - AOF rewrite: background child + quản lý AOF mới
```

**Phạm vi phiên bản:** Từ Redis 6, có thể bật I/O threads cho một phần xử lý mạng; Redis 8 tiếp tục cải thiện cơ chế I/O threading. Điều này không đồng nghĩa toàn bộ lệnh dữ liệu chạy song song trên nhiều worker thread. Cần xem phiên bản và cấu hình thực tế (`io-threads`).

## 2. Single-threaded command execution

### 2.1. `single-threaded` nghĩa là gì?

Trong mô hình Redis cơ bản, **lệnh thông thường trên dữ liệu được xử lý lần lượt trong quá trình thực thi**. Ví dụ, nếu nhiều client cùng gửi `GET`, `SET`, `INCR`, Redis có thể nhận yêu cầu từ nhiều socket, nhưng phần lớn logic lệnh trên dữ liệu vẫn không được chạy CPU song song trong cùng một instance theo kiểu một worker cho mỗi client.

```redis
SET user:1 "Alice"
INCR page_views
GET user:1
```

**Hệ quả quan trọng:** Một lệnh dữ liệu đơn lẻ thông thường có tính *atomic* đối với các lệnh Redis khác trên cùng instance, tức là một lệnh khác không chen vào giữa quá trình thực thi lệnh đó. Tuy nhiên, **nhiều lệnh liên tiếp của ứng dụng không tự động là một giao dịch nguyên tử (atomic transaction)**. Khi cần gộp các thao tác, ta nên tìm hiểu `MULTI`/`EXEC` hoặc Lua script và cân nhắc tính phù hợp.

### 2.2. Vì sao kiến trúc này có thể nhanh?

- Giảm chi phí khóa (lock) và đồng bộ đối với dữ liệu dùng chung trong luồng thực thi lệnh chủ đạo.
- Tránh overhead của cách tiếp cận tạo một thread riêng cho mỗi kết nối/lệnh.
- Kết hợp với phần lớn lệnh có độ phức tạp nhỏ và dữ liệu trong RAM để xử lý nhanh.

### 2.3. Giới hạn

- Lệnh hoặc Lua script xử lý quá lâu sẽ khiến các yêu cầu khác trên cùng main execution path phải chờ.
- Tăng số lượng CPU core **không tự động** làm một lệnh CPU-heavy chạy nhanh tương ứng.
- Các thread/process nền có thể xử lý I/O, lưu snapshot, AOF rewrite hoặc giải phóng bộ nhớ; chúng không loại bỏ hoàn toàn các nguồn latency như `fork()`, contention CPU/đĩa và Copy-on-Write.

> **Chú ý:** "Redis single-threaded nên mỗi lần chỉ có một client được kết nối" là **sai**. Redis có thể quản lý rất nhiều kết nối; ý chính là **mô hình thực thi lệnh** - mỗi lệnh được xử lý tuần tự, không phải giới hạn số client.

## 3. Event loop và I/O multiplexing

### 3.1. Event loop là gì?

Event loop là vòng lặp điều phối công việc dựa trên sự kiện thay vì chặn một thread để đợi riêng từng client. Dưới đây là **mô hình đơn giản hóa**, không phải thứ tự nội bộ cố định trong mọi phiên bản:

1. Yêu cầu hệ điều hành thông báo các socket đang sẵn sàng đọc/ghi.
2. Tiếp nhận các sự kiện và đọc dữ liệu từ những socket có thể đọc.
3. Parse request và chuyển tới logic thực thi lệnh.
4. Cập nhật/tra cứu dữ liệu trong RAM, tạo phản hồi.
5. Gửi phản hồi ngay khi socket cho phép hoặc chờ sự kiện có thể ghi.
6. Xử lý các công việc nội bộ rồi lặp lại.

Nếu client A chưa gửi thêm byte nào, Redis không phải đứng chờ A; Redis có thể phục vụ các kết nối khác đã có dữ liệu sẵn sàng.

### 3.2. I/O multiplexing là gì?

I/O multiplexing là cơ chế cho phép **theo dõi nhiều file descriptor/socket thông qua một cơ chế chờ sự kiện**, thay vì sử dụng một thread blocking trên mỗi kết nối. Trên Linux thường là `epoll`; hệ điều hành khác có thể dùng `kqueue` (MacOS) hoặc `select`/cơ chế tương ứng.

| Thành phần | Vai trò | Không phải |
|---|---|---|
| **I/O multiplexing** | Cho biết socket nào sẵn sàng I/O | Chạy nhiều phép tính CPU-heavy song song |
| **Event loop** | Điều phối khi nào đọc/ghi, parse, thực thi và xử lý sự kiện | Một thuật toán xử lý dữ liệu riêng biệt |
| **Main execution thread** | Xử lý phần lớn logic lệnh truy cập dataset | Toàn bộ các tác vụ của Redis |
| **Background threads/processes** | Hỗ trợ I/O, fsync, RDB, AOF rewrite và công việc phụ trợ | Bảo đảm main thread không bị gián đoạn bao giờ |

**Điểm mấu chốt:** I/O multiplexing giúp **xử lý nhiều kết nối hiệu quả**; nó không biến một lệnh `KEYS *` hay Lua script kéo dài thành tác vụ tự động chạy song song.

## 4. Vì sao Redis có độ trễ thấp?

Redis nhanh nhờ **nhiều yếu tố kết hợp**, không phải chỉ nhờ RAM:

1. **RAM:** tránh độ trễ đọc ngẫu nhiên từ storage cho phần lớn thao tác thông thường. Truy cập RAM cũng không phải miễn phí: vẫn có chi phí CPU, cache miss, cấp phát và sao chép dữ liệu, nhưng thường thấp hơn nhiều so với Disk I/O.
2. **Cấu trúc dữ liệu tối ưu:** hash table, list, sorted set và các cấu trúc/encoding phù hợp cho nhiều loại thao tác.
3. **Command nhỏ:** nhiều lệnh có độ phức tạp trung bình `O(1)` hoặc `O(log N)`.
4. **Event loop và I/O multiplexing:** không cần chờ riêng từng client khi socket chưa sẵn sàng.
5. **Giảm tranh chấp lock trong thực thi lệnh chủ đạo:** ít overhead đồng bộ hơn ở nhiều trường hợp.

Một số lệnh và độ phức tạp điển hình:

| Lệnh | Độ phức tạp | Lưu ý |
|---|---|---|
| `GET key` | `O(1)` | Value rất lớn vẫn tốn sao chép và truyền qua mạng |
| `SET key value` | `O(1)` theo số key | Giá trị lớn có chi phí xử lý/cấp phát thực tế |
| `INCR key` | `O(1)` | Chỉ dùng với giá trị số phù hợp |
| `HGET key field` | `O(1)` trung bình | Phụ thuộc cấu trúc/encoding và kích thước dữ liệu |
| `ZADD key score member` | `O(log N)` cho một member | `N` là số member trong sorted set |
| `KEYS pattern` | `O(N)` | Duyệt keyspace; rất dễ gây chặn khi database lớn |

**Phân biệt:** *Command time complexity* khác *end-to-end latency*. Thời gian quan sát từ client còn gồm network RTT, độ lớn response, queueing, persistence, CPU scheduling và các yếu tố khác. Bật persistence cũng có thể tạo thêm I/O và latency dù dữ liệu chủ yếu phục vụ từ RAM.

## 5. Những lệnh/tác vụ nặng có thể chặn Redis

Vì phần lớn command logic được xử lý tuần tự, lệnh tốn nhiều CPU (CPU-bound) hoặc thao tác đồng bộ tốn kém làm tăng thời gian chờ của client khác.

| Lệnh/tác vụ | Rủi ro | Cách thay thế/giảm thiểu |
|---|---|---|
| `KEYS *` | Duyệt toàn bộ keyspace, `O(N)` | `SCAN` theo nhiều lần gọi; tránh truy vấn toàn bộ thường xuyên |
| `HGETALL big_hash` | Trả về toàn bộ field/value của hash lớn | `HSCAN` hoặc giới hạn dữ liệu cần lấy |
| `SMEMBERS big_set` | Đọc toàn bộ tập member | `SSCAN` hoặc tổ chức dữ liệu khác |
| `LRANGE list 0 -1` | Trả về cả list nếu list lớn | Chỉ đọc một khoảng cần thiết |
| `SORT` trên tập lớn | Tốn CPU, bộ nhớ, có thể sắp xếp khối lượng lớn | Giới hạn dữ liệu hoặc xử lý ở nơi phù hợp |
| `EVAL`/Lua chạy lâu | Script thường giữ đường xử lý lệnh cho đến khi hoàn tất | Viết script ngắn, tránh vòng lặp lớn |
| `DEL` với đối tượng lớn | Thu hồi nhiều phần tử có thể chiếm thời gian trên main thread | `UNLINK` khi phù hợp để giải phóng bộ nhớ bất đồng bộ |
| `FLUSHALL SYNC` hoặc `FLUSHDB SYNC` | Xóa dữ liệu đồng bộ, tác động lớn | Không chạy trên production tùy tiện; xem `ASYNC` nếu thực sự cần |
| `SAVE` | Lưu RDB **đồng bộ**, chặn server khi đang tạo snapshot | Thông thường dùng `BGSAVE` thay cho `SAVE` |
| `fork()` khi `BGSAVE`/AOF rewrite | Có thể tạo khoảng dừng ngắn, tiêu tốn RAM/CPU | Theo dõi latency, RAM và điều kiện workload |

**Lưu ý về `SCAN`:** `SCAN` làm nhỏ công việc mỗi lần gọi, **không phải** transactional snapshot nhất quán. Khi keyspace thay đổi trong quá trình duyệt, kết quả có thể trùng hoặc không thấy một số phần tử thay đổi; `COUNT` chỉ là *hint*, không bảo đảm đúng số phần tử mỗi lần trả về. Ứng dụng phải xử lý được trùng lặp nếu cần.

Một số công cụ kiểm tra:

```bash
redis-cli SLOWLOG GET 10
redis-cli INFO commandstats
redis-cli LATENCY DOCTOR
redis-cli --latency
```

`SLOWLOG` chủ yếu đo **thời gian thực thi lệnh tại server**, không bao gồm thời gian truyền request/response qua mạng. `LATENCY DOCTOR` phụ thuộc cơ chế theo dõi latency và cấu hình của instance; nếu không có dữ liệu, chưa chắc hệ thống không có vấn đề.

## 6. Persistence: khái niệm và mô hình lỗi

Persistence lưu một biểu diễn của dữ liệu Redis xuống storage để khôi phục sau khi process dừng. Các chế độ:

- **RDB:** snapshot tại thời điểm xác định (point-in-time).
- **AOF:** ghi nhận các thay đổi để tái tạo (replay) dataset (trong Redis 7+, bộ AOF có thể gồm cả file base định dạng RDB).
- **RDB + AOF:** cùng bật hai cơ chế.
- **No persistence:** chấp nhận không có dữ liệu bền vững trên instance đó sau khi restart (phù hợp một số cache có thể tái tạo).

Cần phân biệt 4 mốc trong hành trình một lệnh ghi:

```text
Client gửi SET
    |
    v
Redis cập nhật dataset trong RAM
    |
    +--> Redis tạo AOF record / ghi vào buffer
                |
                v
        write() -> OS page cache
                |
                v
        fsync() / đồng bộ xuống storage theo chính sách
```

Sơ đồ này mô tả các **giai đoạn logic**, không khẳng định thứ tự gửi phản hồi giống nhau cho mọi `appendfsync` policy. Đặc biệt, với `always`, Redis yêu cầu đồng bộ AOF trước khi gửi phản hồi cho nhóm write tương ứng trong cơ chế thông thường.

- **`write()` thành công:** dữ liệu đã được hệ điều hành chấp nhận, nhưng có thể mới nằm trong page cache.
- **`fsync()`:** yêu cầu hệ điều hành đồng bộ dữ liệu file xuống storage; không phải bảo đảm tuyệt đối trước mọi lỗi thiết bị/hạ tầng.
- **Process crash (`kill -9`):** Redis bị kết thúc, **OS và page cache vẫn tồn tại**.
- **Kernel crash/power loss:** có thể làm mất dữ liệu chưa bền vững trong page cache.

Vì thế, kết quả sau `kill -9` **không thể** suy ra giống kết quả khi mất điện.

## 7. RDB - snapshot persistence

### 7.1. Nguyên lý

RDB lưu dataset dưới dạng ảnh chụp tại **một mốc thời gian** vào file nhị phân (thường là `dump.rdb`). RDB không cần ghi từng command như nhật ký AOF.

```text
T0  Dataset có 2.000 key
T1  BGSAVE bắt đầu: child được fork để tạo snapshot
T2  Parent tiếp tục nhận 1.000 key mới
T3  BGSAVE hoàn tất thành công với snapshot của mốc T1
T4  Redis process crash
T5  Restart chỉ bằng RDB -> có dataset tại T1, thiếu 1.000 key mới
```

Tình huống trên giả định **không có snapshot mới hơn, không có AOF**, không có thao tác ghi/xóa/expire khác và khôi phục đúng file snapshot đó.

### 7.2. `BGSAVE`, `fork()` và Copy-on-Write

1. Redis xử lý yêu cầu `BGSAVE`.
2. Parent dùng `fork()` tạo child process (trên cơ chế Unix-like truyền thống). Mốc dataset của child được xác lập tại thời điểm fork.
3. Child ghi snapshot vào file tạm, rồi thay thế snapshot cũ khi hoàn tất thành công.
4. Parent tiếp tục xử lý request. Nếu parent sửa vùng nhớ đang được chia sẻ, cơ chế **Copy-on-Write (CoW)** tạo bản sao các trang bộ nhớ liên quan.

```text
Trước khi parent cập nhật:
  Parent ----> page A (chia sẻ) <---- Child

Khi parent cập nhật page A:
  Parent ----> page A' (bản copy mới)
  Child  ----> page A  (bản dùng để ghi snapshot)
```

**Ưu điểm:** snapshot gọn, thuận tiện backup, không phải dừng xử lý lệnh trong suốt thời gian child ghi dữ liệu.  
**Hạn chế:** `fork()` có thể tạm dừng main thread; CoW tăng mức dùng RAM khi có nhiều thay đổi; CPU/disk I/O của child vẫn có thể gây cạnh tranh tài nguyên. RDB có nguy cơ mất dữ liệu từ snapshot gần nhất đến lúc crash.

### 7.3. Cấu hình và kiểm tra

Ví dụ snapshot theo điều kiện:

```conf
save 60 1000
dbfilename dump.rdb
```

`save 60 1000` nghĩa là điều kiện tạo snapshot liên quan đến **ít nhất 1.000 thay đổi trong khoảng 60 giây** theo chính sách `save`, không phải tạo snapshot đúng mỗi 60 giây vô điều kiện.

```bash
redis-cli BGSAVE
redis-cli LASTSAVE
redis-cli INFO persistence
```

`BGSAVE` trả về việc **bắt đầu/lên lịch**, không có nghĩa file đã ghi xong. Cần kiểm tra `rdb_bgsave_in_progress:0`, `rdb_last_bgsave_status:ok`, và đối chiếu thời gian lưu/file thực tế. `LASTSAVE` trả Unix timestamp của lần lưu thành công gần nhất.

### 7.4. Ưu và nhược điểm RDB

- **Ưu:** file snapshot thường nhỏ gọn; dễ chép, lưu trữ và phục hồi theo mốc; thường có lợi thế thời gian nạp so với log AOF dài.
- **Nhược:** các thay đổi kể từ snapshot gần nhất có thể mất; snapshot/fork/CoW gây tải CPU, RAM và storage; không thích hợp một mình nếu yêu cầu giảm tối đa lượng write có thể mất.

## 8. AOF - Append Only File

### 8.1. Nguyên lý

AOF ghi lại các lệnh/biểu diễn ghi cần thiết để tái tạo trạng thái. Khi restart, Redis nạp dữ liệu từ bộ AOF, thường bằng **nạp base file trước rồi áp dụng các incremental record** tương ứng trong Redis 7+.

```redis
SET counter 10
INCR counter
SET user:1 "Alice"
```

Các bản ghi lệnh gia tăng sử dụng định dạng Redis protocol (RESP). **Không phải mọi byte trong một bộ AOF của Redis 7+ đều là command RESP:** base AOF có thể có định dạng RDB.

### 8.2. `appendfsync`: điểm trọng tâm

`appendfsync` quyết định chính sách Redis yêu cầu hệ điều hành đồng bộ AOF xuống storage. Cần phân biệt **append vào file/page cache** và **fsync xuống thiết bị lưu trữ**.

| `appendfsync` | Cách hoạt động | Hiệu năng | Rủi ro khi OS/power crash |
|---|---|---|---|
| `always` | Fsync cho các write AOF trước khi xác nhận phản hồi; có thể gộp nhóm lệnh | Thường tốn chi phí ghi/độ trễ nhất | Thấp nhất trong ba lựa chọn khi storage hoạt động đúng, **không phải bảo đảm tuyệt đối** |
| `everysec` | Yêu cầu fsync nền khoảng mỗi giây (mặc định thường dùng) | Cân bằng throughput và durability | Thường được mô tả nguy cơ mất khoảng **1 giây** write gần nhất, không phải giới hạn cứng trong mọi sự cố |
| `no` | Redis không chủ động fsync theo chu kỳ này; để OS quyết định khi flush | Có thể giảm overhead | Khó dự đoán hơn, phụ thuộc kernel/storage |

```conf
appendonly yes
appendfsync everysec
```

`always` không đồng nghĩa "mỗi `SET` luôn tạo đúng một lần fsync riêng": Redis có thể gộp các lệnh đã xử lý thành một nhóm AOF append + fsync. `everysec` không có nghĩa "chắc chắn mất đúng một giây khi crash". Trong tình trạng I/O nghẽn hoặc thiết bị lỗi, các bảo đảm thực tế cần được xem cùng log và đặc tính storage.

### 8.3. Vì sao `kill -9` đôi khi vẫn khôi phục đủ với `everysec`?

Khi Redis đã chuyển byte vào **OS page cache**, `kill -9` chỉ giết process Redis; byte đó không tự nhiên biến mất khỏi bộ nhớ của kernel. Sau restart, hệ điều hành vẫn có thể cung cấp dữ liệu này. Vì thế AOF có thể khôi phục toàn bộ các cập nhật dù lệnh `fsync` gần nhất chưa diễn ra trước lúc process bị giết.

**Kết luận đúng:** "Trong trial process crash này, AOF đã khôi phục X/Y key."  
**Kết luận sai:** "AOF `everysec` bảo đảm không mất dữ liệu khi máy mất điện."

### 8.4. Rewrite và multi-part AOF (Redis 7+)

Một chuỗi:

```redis
SET score 10
SET score 20
SET score 30
SET score 40
```

không cần lưu lại nguyên vẹn tất cả các bước trung gian để dựng lại trạng thái cuối. **AOF rewrite** tạo dạng biểu diễn gọn hơn, tương đương về trạng thái, mà không phải xóa/sửa tùy tiện trực tiếp log đang được ghi.

Từ Redis 7, multi-part AOF gồm:

- **Base AOF:** trạng thái nền sau rewrite, có thể là định dạng RDB hoặc AOF.
- **Incremental AOF:** các thay đổi phát sinh sau mốc nền (có thể có nhiều file).
- **Manifest:** xác định các thành phần hợp lệ của bộ AOF cần nạp.

Khi rewrite, parent tiếp tục phục vụ write và ghi vào incremental AOF mới; child xây dựng base mới; Redis cập nhật manifest một cách nhất quán khi chuyển bộ file hiện hành. `BGREWRITEAOF` là lệnh rewrite thủ công; Redis cũng có thể rewrite tự động theo cấu hình. Rewrite tiêu tốn tài nguyên, không loại bỏ mọi chi phí I/O.

**Lưu ý backup:** Với multi-part AOF, **không sao chép tùy tiện một file lẻ**. Phải sao lưu bộ file và manifest nhất quán, đặc biệt khi đang diễn ra rewrite.

### 8.5. Ưu và nhược điểm AOF

- **Ưu:** ghi nhận cập nhật thường xuyên hơn RDB định kỳ; có thể điều chỉnh trade-off qua `appendfsync`; rewrite giúp tránh log tăng mãi theo số lần cập nhật.
- **Nhược:** phát sinh write/fsync I/O khi hoạt động; thường chiếm nhiều dung lượng hơn RDB tương đương; rewrite làm tăng chi phí tài nguyên; thời gian nạp có thể dài nếu nhiều log phải replay, **nhưng base RDB của AOF hiện đại có thể giảm chi phí này**.

## 9. So sánh RDB và AOF

| Tiêu chí | RDB | AOF |
|---|---|---|
| **Bản chất** | Snapshot trạng thái tại một thời điểm | Base state + ghi nhận thay đổi để khôi phục |
| **Tần suất ghi** | Theo điều kiện `save` hoặc chủ động `BGSAVE` | Khi có write; đồng bộ bền vững theo `appendfsync` |
| **Hiệu năng khi chạy** | Thường ít I/O liên tục hơn; nhưng snapshot có fork/CoW/đĩa | I/O cho log và fsync; mức overhead tùy chính sách |
| **Dung lượng** | Snapshot thường gọn | Thường lớn hơn; giảm sau rewrite; base có thể nén/định dạng RDB |
| **Thời gian khởi động** | Thường nhanh khi chỉ cần nạp snapshot | Có thể chậm hơn do replay incremental records; phụ thuộc base/rewrite/workload |
| **Mất dữ liệu** | Có thể mất mọi thay đổi kể từ snapshot gần nhất | `always` thấp hơn, `everysec` thường cỡ 1 giây, `no` tùy OS; không có cam kết tuyệt đối |
| **Backup/restore** | Một file snapshot tương đối dễ sao lưu theo mốc | Cần quản lý nhất quán base, incremental và manifest (Redis 7+) |
| **Chi phí tài nguyên nổi bật** | `fork`, CoW, I/O snapshot | AOF writes, fsync, I/O và fork/CoW khi rewrite |
| **Phù hợp** | Cache có thể tái tạo, backup định kỳ, chấp nhận mất write gần nhất | Muốn giảm mất cập nhật và điều chỉnh durability |
| **Use case** | Periodic backup, point-in-time recovery, fast restart, disaster recovery (khi lưu snapshot ngoài máy), workload chấp nhận mất dữ liệu giữa các snapshot | Frequent writes requiring higher durability, crash recovery with minimal data loss, applications prioritizing data safety; có thể kết hợp với RDB |

### 9.1. Có thể dùng cả hai không?

**Có.** Khi bật RDB và AOF đồng thời, Redis thường **nạp AOF khi khởi động** nếu AOF hiện hữu và được bật, vì nó có thông tin cập nhật đầy đủ hơn. RDB vẫn hữu ích để backup hoặc khôi phục theo mốc. **Không nên suy luận** rằng bật hai chế độ thì Redis sẽ mặc nhiên khởi động bằng RDB nhanh hơn: đường nạp chính của cấu hình hỗn hợp là AOF. Ngoài ra, một base file của multi-part AOF có định dạng RDB **không đồng nghĩa** đang bật snapshot RDB độc lập.

### 9.2. Nên chọn phương án nào?

- **RDB-only:** ưu tiên snapshot nhỏ gọn, backup và chịu được khoảng mất cập nhật kể từ snapshot cuối.
- **AOF `everysec`:** lựa chọn cân bằng phổ biến nếu muốn dữ liệu bền hơn mà không chịu chi phí của `always`.
- **AOF `always`:** khi đặc biệt nhạy cảm với mất write và chấp nhận overhead; vẫn cần backup và thiết kế khôi phục thảm họa.
- **RDB + AOF:** cần kết hợp khả năng backup snapshot với cơ chế AOF; phải cân nhắc I/O, RAM và thời gian nạp khi restart.
- **Không persistence:** chỉ khi dữ liệu là cache/tạm thời và có thể mất/tái tạo.

**Quan trọng:** Persistence không thay thế cho backup độc lập, replication, giám sát trạng thái persistence hay thử nghiệm disaster recovery.

## 10. Tổng kết kiến thức cần nhớ

1. **Redis có thể phục vụ nhiều client vì event loop và I/O multiplexing**, không phải vì mỗi client nhất thiết có một thread.
2. **Mostly single-threaded** nói về phần lớn *command execution*; I/O threads và background child không mâu thuẫn với khái niệm này.
3. **Dữ liệu trong RAM + thao tác nhỏ** giúp giảm latency; lệnh `O(N)`/script nặng, response rất lớn và persistence vẫn có thể gây chặn hoặc làm tăng latency.
4. **RDB = snapshot:** gọn và thuận tiện backup nhưng mất các thay đổi sau snapshot gần nhất nếu không có cơ chế khác.
5. **AOF = lưu thay đổi và phục hồi:** `appendfsync always/everysec/no` đánh đổi durability lấy hiệu năng; Redis 7+ có multi-part AOF, base có thể ở định dạng RDB.
6. **`write()` khác `fsync()`; process crash khác power failure.** Đây là chìa khóa để đọc đúng kết quả crash test.
7. **Nếu bật cả RDB và AOF, Redis ưu tiên nạp AOF khi startup.** Đừng coi RDB snapshot và AOF base định dạng RDB là một.

## Tài liệu tham khảo chính thức

1. [Redis Documentation - Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/): RDB, AOF, fsync, rewrite, multi-part AOF, khi bật cả hai.
2. [Redis Documentation - Diagnosing latency issues](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/): single-threaded, blocking commands, fork latency.
3. [Redis Documentation - SCAN](https://redis.io/docs/latest/commands/scan/): incremental scan, các giới hạn khi dataset thay đổi.
4. [Redis Documentation - BGSAVE](https://redis.io/docs/latest/commands/bgsave/): snapshot background và trạng thái lệnh.
5. [Redis Documentation - SLOWLOG](https://redis.io/docs/latest/commands/slowlog/): đo command execution, không tính I/O tới client.
6. [Redis Documentation - FLUSHALL](https://redis.io/docs/latest/commands/flushall/): `SYNC`/`ASYNC`.
7. [Redis Open Source 8.0 release notes](https://redis.io/docs/latest/operate/oss_and_stack/stack-with-enterprise/release-notes/redisce/redisos-8.0-release-notes/): thay đổi kiến trúc I/O threading.
8. [Redis Documentation - INFO](https://redis.io/docs/latest/commands/info/): các trường trạng thái và thống kê.
