# 02 - Cấu trúc dữ liệu và TTL trong Redis

Demo đi kèm: [`demos/01-data-structures/`](../../demos/01-data-structures/README.md).

## 1. Ý tưởng chung: Redis là "từ điển khổng lồ trong RAM"

Mọi dữ liệu trong Redis có dạng **key → value**. Khác với cache đơn giản như Memcached (value chỉ là chuỗi), **value trong Redis có kiểu**: String, List, Hash, Set, Sorted Set... Mỗi kiểu có bộ lệnh riêng chạy ngay trên server.

Vì sao điều này quan trọng? Muốn cộng 1 điểm cho người chơi, với cache kiểu chuỗi ta phải đọc cả object về, sửa, rồi ghi lại (3 bước, dễ bị ghi đè khi nhiều client cùng sửa). Với Redis chỉ cần `ZINCRBY leaderboard 1 alice`: một lệnh, nguyên tử, không cần kéo dữ liệu về ứng dụng.

```bash
TYPE user:1001        # hỏi kiểu của value: string | list | hash | set | zset
```

### Quy ước đặt tên key (nhóm dùng chung)

Dùng dấu `:` phân cấp theo dạng `<loại>:<đối tượng>:<id>`. Dễ đọc, dễ tìm bằng `SCAN MATCH`, và tránh trùng giữa các tính năng.

| Mục đích | Mẫu key | Kiểu | TTL |
|---|---|---|---|
| Cache dữ liệu từ DB (dùng chung với Demo 02) | `cache:product:<id>` | String (JSON) | Có, gán bằng `SET ... EX` |
| Bộ đếm | `stats:page:<tên>:views` | String (số) | Không |
| Hàng đợi | `queue:<tên>` | List | Không |
| Thông tin đối tượng | `user:<id>` | Hash | Không |
| Bảng xếp hạng | `leaderboard:<tên>` | Sorted Set | Không |
| Session | `session:<token>` | String | Có |

Trên production **không dùng `KEYS *`**, vì lệnh này duyệt toàn bộ key, chặn server đơn luồng. Hãy dùng `SCAN` (chi tiết ở `05-persistence.md`, phần kiến trúc single-threaded).

## 2. String

**Đặc điểm.** Kiểu cơ bản nhất: một key ứng với một chuỗi byte. Chuỗi này *binary-safe*, chứa được text, số, JSON, cả ảnh nhỏ, tối đa **512 MB**. Nếu giá trị là số nguyên, Redis cho phép tăng/giảm trực tiếp.

| Lệnh | Ý nghĩa | Độ phức tạp |
|---|---|---|
| `SET key value [EX s \| PX ms] [NX \| XX] [KEEPTTL]` | Ghi giá trị, có thể kèm TTL / điều kiện | O(1) |
| `GET key` | Đọc giá trị | O(1) |
| `INCR` / `INCRBY` / `DECR` | Tăng/giảm số nguyên, **nguyên tử** | O(1) |
| `MSET` / `MGET` | Ghi/đọc nhiều key một lần (giảm round-trip) | O(N) |
| `SETNX` hoặc `SET ... NX` | Chỉ ghi nếu key chưa có (nền tảng của distributed lock) | O(1) |

**Use case:** cache kết quả truy vấn/API (JSON), bộ đếm lượt xem, lượt like, rate limiting (`INCR` + `EXPIRE` theo cửa sổ thời gian), session token, khóa phân tán.

**Ví dụ:**
```bash
SET cache:product:1001 '{"id":1001,"name":"Ban phim co","price":890000}' EX 60
GET cache:product:1001
INCR stats:page:home:views          # (integer) 1, 2, 3...
```

**Bên trong:** số nguyên nhỏ được lưu dạng `int`, chuỗi ngắn (≤ 44 byte) dạng `embstr`, còn lại dạng `raw`. Xem bằng `OBJECT ENCODING key`.

## 3. List

**Đặc điểm.** Danh sách chuỗi **giữ đúng thứ tự chèn, cho phép trùng**. Thêm/lấy ở **hai đầu** rất nhanh (O(1)). Truy cập phần tử ở giữa thì chậm (O(N)). Bên trong là *quicklist*: danh sách liên kết của các khối nén *listpack* (Redis 7; bản 6.x dùng *ziplist*).

| Lệnh | Ý nghĩa | Độ phức tạp |
|---|---|---|
| `LPUSH` / `RPUSH key v1 v2...` | Thêm vào đầu / cuối | O(1) mỗi phần tử |
| `LPOP` / `RPOP key` | Lấy ra từ đầu / cuối | O(1) |
| `BLPOP` / `BRPOP key timeout` | Như POP nhưng **chờ (block)** đến khi có phần tử | O(1) |
| `LRANGE key start stop` | Xem một đoạn (`0 -1` là toàn bộ) | O(S+N) |
| `LLEN key` | Độ dài | O(1) |
| `LTRIM key start stop` | Cắt giữ một đoạn, ví dụ chỉ giữ 100 phần tử mới nhất | O(N) |

**Use case:**
- **Queue (FIFO):** producer `RPUSH`, worker `LPOP`/`BLPOP`. Ví dụ hàng đợi gửi email, xử lý ảnh.
- **Stack (LIFO):** `LPUSH` + `LPOP`.
- **Timeline / "10 hoạt động gần nhất":** `LPUSH` + `LTRIM 0 9`.

**Ví dụ:**
```bash
RPUSH queue:emails "job:1" "job:2" "job:3"
LPOP  queue:emails      # "job:1" (vào trước, ra trước)
LRANGE queue:emails 0 -1
```

Giới hạn khi dùng làm queue: phần tử đã `POP` là mất khỏi Redis. Nếu worker chết giữa chừng thì job mất theo. Hệ thống cần đảm bảo hơn nên dùng `LMOVE` (chuyển sang list "đang xử lý") hoặc **Redis Streams**.

## 4. Hash

**Đặc điểm.** Một key chứa **nhiều cặp field → value**, giống một object hay một dòng trong bảng. Có thể đọc/sửa **từng field riêng** mà không cần đụng phần còn lại. Hash nhỏ (mặc định ≤ 512 field và mỗi value ≤ 64 byte, cấu hình `hash-max-listpack-entries` / `hash-max-listpack-value`) được nén dạng *listpack* nên rất tiết kiệm RAM. Lớn hơn thì chuyển sang *hashtable*.

| Lệnh | Ý nghĩa | Độ phức tạp |
|---|---|---|
| `HSET key f1 v1 f2 v2...` | Ghi một hoặc nhiều field (trả về số field **mới** được tạo) | O(1) mỗi field |
| `HGET key field` | Đọc 1 field | O(1) |
| `HMGET key f1 f2` | Đọc nhiều field | O(N) |
| `HGETALL key` | Đọc toàn bộ field + value | O(N) |
| `HINCRBY key field n` | Tăng số trong 1 field | O(1) |
| `HDEL` / `HEXISTS` / `HLEN` | Xóa / kiểm tra / đếm field | O(1) |

**Use case:** hồ sơ user, giỏ hàng (`cart:<user>`, field = mã sản phẩm, value = số lượng), cấu hình, thông tin sản phẩm.

**String (JSON) hay Hash để lưu một object?**

| | String chứa JSON | Hash |
|---|---|---|
| Đọc cả object | 1 lệnh `GET`, rất gọn | `HGETALL` |
| Sửa 1 thuộc tính | Phải đọc → parse → sửa → ghi lại cả chuỗi | `HSET user:1001 role admin`, chỉ đụng 1 field |
| Tăng số đếm | Không làm trực tiếp được | `HINCRBY`, nguyên tử |
| Dữ liệu lồng nhiều tầng | Lưu được | Không (Hash chỉ phẳng 1 tầng) |
| TTL | Cho cả key | Cho cả key (TTL từng field chỉ có từ Redis 7.4) |

Kết luận: object cache nguyên khối, ít sửa thì dùng String JSON (Demo 02). Object hay sửa từng phần thì dùng Hash.

## 5. Sorted Set (ZSET)

**Đặc điểm.** Tập hợp các **member không trùng**, mỗi member có một **score** (số thực). Redis **luôn giữ chúng được sắp xếp theo score**, nên lấy top-N hay xem hạng của một người rất nhanh. Bên trong là **skip list** (để duyệt theo thứ tự, O(log N)) kết hợp **hash table** (để tra score theo member, O(1)). Hai member cùng score được sắp theo thứ tự từ điển của tên member.

| Lệnh | Ý nghĩa | Độ phức tạp |
|---|---|---|
| `ZADD key score member...` | Thêm member, hoặc **cập nhật score** nếu đã có | O(log N) |
| `ZINCRBY key n member` | Cộng điểm | O(log N) |
| `ZREVRANGE key 0 9 WITHSCORES` | Top 10 điểm cao nhất | O(log N + M) |
| `ZRANGE key 0 -1 WITHSCORES` | Toàn bộ, điểm thấp → cao | O(log N + M) |
| `ZREVRANK key member` | Hạng (tính từ 0) khi xếp điểm cao → thấp | O(log N) |
| `ZSCORE key member` | Điểm của member | O(1) |
| `ZRANGEBYSCORE key min max` | Lọc theo khoảng điểm | O(log N + M) |
| `ZCARD` / `ZREM` | Đếm / xóa member | O(1) / O(log N) |

**Use case:** leaderboard game, bảng xếp hạng bài viết, hàng đợi có độ ưu tiên (score = priority), **lịch hẹn giờ** (score = unix timestamp, worker lấy các job có `score ≤ now`), sliding-window rate limiting.

**Ví dụ:**
```bash
ZADD leaderboard:game 1500 alice 2300 bob 1800 carol
ZINCRBY leaderboard:game 600 carol       # carol: 2400
ZREVRANGE leaderboard:game 0 2 WITHSCORES # carol 2400, bob 2300, alice 1500
ZREVRANK leaderboard:game carol           # 0  -> hạng 1
```

Nếu làm bảng xếp hạng bằng SQL, mỗi lần xem top phải `ORDER BY score DESC LIMIT 10`, và tính hạng của một người bằng `COUNT(*) WHERE score > x`. Với hàng triệu người chơi, việc này tốn kém. Sorted Set giữ sẵn thứ tự nên đọc top/hạng chỉ mất O(log N).

## 6. Phân biệt List và Sorted Set

| Tiêu chí | List | Sorted Set |
|---|---|---|
| Thứ tự | Theo **thứ tự chèn** | Theo **score**, tự sắp xếp |
| Trùng lặp | Cho phép | Member là **duy nhất** (thêm lại chỉ cập nhật score) |
| Thao tác nhanh | Thêm/lấy ở 2 đầu, O(1) | Thêm/sửa/tìm hạng, O(log N) |
| Truy cập giữa | Chậm, O(N) | Nhanh theo rank hoặc khoảng score |
| Hợp với | Queue, stack, timeline, log gần nhất | Xếp hạng, ưu tiên, hẹn giờ, top-N |
| Câu hỏi trả lời được | "Việc nào đến trước?" | "Ai đứng thứ mấy?", "Ai có điểm 1000–2000?" |

Ví dụ trong demo: `RPUSH compare:list 1500 2300 1800 2300` trả về đúng thứ tự chèn, và `2300` xuất hiện 2 lần. Còn `ZADD compare:zset ... 2300 bob ... 2300 bob` chỉ giữ một `bob` và tự sắp theo điểm.

## 7. TTL và key expiration

### 7.1. Gán TTL

| Cách | Ví dụ | Ghi chú |
|---|---|---|
| Ghi kèm TTL (khuyên dùng) | `SET session:abc "u1" EX 5` (giây) hoặc `PX 5000` (ms) | Ghi và gán hạn trong **1 lệnh nguyên tử**. Nếu tách 2 lệnh, có thể bị crash ở giữa, để lại key vĩnh viễn |
| Gán cho key đã có | `EXPIRE key 300` / `PEXPIRE key 300000` | Áp dụng cho **mọi kiểu** (List, Hash, ZSET...) |
| Hết hạn tại thời điểm | `EXPIREAT key 1798736400` | Unix timestamp |
| Lệnh cũ | `SETEX key 60 value` | Tương đương `SET key value EX 60` |

TTL gắn với **cả key**, không gắn với từng phần tử bên trong List/Hash/ZSET.

### 7.2. Kiểm tra TTL và ý nghĩa -1, -2

```bash
TTL key     # số giây còn lại (PTTL: mili giây)
```

| Kết quả | Ý nghĩa | Ví dụ trong demo |
|---|---|---|
| Số dương `n` | Key còn sống n giây | `TTL session:abc123` → `5` |
| **`-1`** | Key **tồn tại nhưng không có hạn**, sống vĩnh viễn | `TTL user:1001` → `-1` |
| **`-2`** | Key **không tồn tại** (đã hết hạn, đã bị xóa, hoặc chưa từng có) | Sau 5 giây: `TTL session:abc123` → `-2`, `GET` → `(nil)` |

Cách nhớ: **-1 là "còn đó, không hết hạn"**, **-2 là "không còn gì để hỏi"**.

### 7.3. Xóa / thay đổi TTL

| Thao tác | Kết quả với TTL |
|---|---|
| `PERSIST key` | **Bỏ TTL**, key thành vĩnh viễn (TTL → -1) |
| `SET key value` (không kèm tùy chọn) | **Xóa TTL cũ**. Bẫy hay gặp, cache bỗng thành vĩnh viễn |
| `SET key value KEEPTTL` (Redis ≥ 6.0) | Ghi giá trị mới, **giữ** TTL cũ |
| `EXPIRE key` lại | Ghi đè TTL bằng giá trị mới |
| `EXPIRE key 0` hoặc số âm | Xóa key ngay |
| `INCR`, `LPUSH`, `HSET`, `ZADD`... | Sửa nội dung, **không** đụng tới TTL |
| `DEL key` | Xóa key, mất luôn TTL |
| `RENAME a b` | TTL đi theo key sang tên mới |

### 7.4. Redis xóa key hết hạn như thế nào?

Redis lưu thời điểm hết hạn dưới dạng *unix timestamp (ms)*. Việc xóa kết hợp 2 cơ chế:

1. **Passive (lười):** khi client truy cập một key, Redis kiểm tra nếu key đã quá hạn thì xóa ngay và trả về như không tồn tại. Client **không bao giờ đọc được** key đã hết hạn.
2. **Active (định kỳ):** khoảng 10 lần mỗi giây, Redis lấy ngẫu nhiên 20 key có TTL và xóa các key đã hết hạn. Nếu hơn 25% số key trong mẫu đã hết hạn thì lặp lại ngay. Cơ chế này dọn dần các key hết hạn mà không ai truy cập nữa, nhưng không quét hết một lượt để tránh chặn server.

Hệ quả: một key hết hạn có thể còn chiếm RAM thêm một chút, nhưng không bao giờ được trả cho client. Số key đã bị xóa do hết hạn xem bằng `INFO stats` → `expired_keys`.

**Expiration khác eviction** (chi tiết ở `04-eviction.md`):

| | Expiration (hết hạn) | Eviction (loại bỏ) |
|---|---|---|
| Nguyên nhân | Key **đến hạn TTL** | Redis **chạm `maxmemory`** |
| Ai quyết định | Lập trình viên đặt TTL | Chính sách `maxmemory-policy` |
| Có xảy ra khi RAM còn dư? | Có | Không |
| Chỉ số | `expired_keys` | `evicted_keys` |

### 7.5. Khi nào nên gán TTL?

- **Luôn gán** cho cache (để dữ liệu cũ tự làm mới, tránh stale data, xem Demo 02), session, OTP, mã xác thực, bộ đếm rate-limit theo cửa sổ.
- **Không gán** cho dữ liệu cần giữ lâu như leaderboard mùa giải, queue, cấu hình (hoặc gán TTL dài theo mùa).
- Nhiều key cache cùng TTL hết hạn cùng lúc có thể gây **cache stampede**. Thêm một ít ngẫu nhiên (jitter), ví dụ `EX 60 + random(0..10)` (chi tiết ở `03-cache-aside.md`).

## 8. Chọn cấu trúc dữ liệu phù hợp

```
Cần lưu gì?
├─ Một giá trị đơn / JSON nguyên khối / bộ đếm ............ String
├─ Một object, hay sửa từng thuộc tính ...................... Hash
├─ Danh sách theo thứ tự đến, lấy ở hai đầu (queue/stack) ... List
├─ Tập không trùng, cần sắp theo điểm/thời gian ............. Sorted Set
└─ Tập không trùng, không cần thứ tự (tag, đã-xem) .......... Set (ngoài phạm vi demo)
```

| Bài toán | Chọn | Lệnh chính |
|---|---|---|
| Cache kết quả API | String + TTL | `SET ... EX`, `GET` |
| Đếm lượt xem | String | `INCR` |
| Session đăng nhập | String (hoặc Hash) + TTL | `SET ... EX`, `EXPIRE` |
| Hồ sơ user, giỏ hàng | Hash | `HSET`, `HGET`, `HINCRBY` |
| Hàng đợi gửi email | List | `RPUSH`, `BLPOP` |
| 10 hoạt động gần nhất | List | `LPUSH`, `LTRIM` |
| Bảng xếp hạng | Sorted Set | `ZADD`, `ZINCRBY`, `ZREVRANGE` |
| Job hẹn giờ | Sorted Set (score = timestamp) | `ZADD`, `ZRANGEBYSCORE` |

## 9. Câu hỏi có thể bị hỏi

1. **TTL trả -1 và -2 khác nhau thế nào?** -1: key có nhưng không hạn. -2: key không tồn tại.
2. **Vì sao dùng `SET key v EX 60` thay vì `SET` rồi `EXPIRE`?** Một lệnh là nguyên tử. Hai lệnh có thể bị gián đoạn ở giữa, để lại key không bao giờ hết hạn.
3. **Tôi `SET` lại một key cache thì TTL còn không?** Không, TTL bị xóa. Phải gán lại `EX` hoặc dùng `KEEPTTL`.
4. **Key hết hạn có bị xóa khỏi RAM ngay đúng giây đó không?** Không nhất thiết. Redis xóa khi có truy cập (passive) hoặc khi lấy mẫu định kỳ (active). Nhưng client không bao giờ đọc được key đã hết hạn.
5. **Vì sao leaderboard dùng Sorted Set mà không dùng List?** List không tự sắp xếp và cho phép trùng. Sorted Set giữ thứ tự theo điểm, cập nhật điểm O(log N), lấy top và hạng rất nhanh.
6. **Có đặt TTL cho một field trong Hash được không?** Từ Redis 7.4 có `HEXPIRE`. Các bản trước chỉ đặt TTL cho cả key.
7. **List làm queue có an toàn không?** Đủ cho tác vụ đơn giản. Nếu worker chết sau `LPOP` thì job mất. Cần độ tin cậy cao thì dùng `LMOVE` hoặc Redis Streams.

## 10. Tài liệu tham khảo

- Redis data types: https://redis.io/docs/latest/develop/data-types/
- Lệnh `EXPIRE` và cơ chế hết hạn: https://redis.io/docs/latest/commands/expire/
- Lệnh `TTL`: https://redis.io/docs/latest/commands/ttl/
- Lệnh `SET` (EX, PX, NX, XX, KEEPTTL): https://redis.io/docs/latest/commands/set/
- Sorted sets: https://redis.io/docs/latest/develop/data-types/sorted-sets/
