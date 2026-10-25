# **Nội dung slide \- Phần 2: Cấu trúc dữ liệu và TTL**

**Người trình bày:** Viết Toàn · **Thời lượng:** 6 phút · **Ngôn ngữ:** tiếng Việt, giữ thuật ngữ tiếng Anh (TTL, Sorted Set, queue...) **Vị trí trong seminar:** sau phần 1 (Tổng quan và môi trường, Nam Anh), trước phần 3 (Cache-Aside, Thắng).

---

## **A. Hướng dẫn chung cho người gen slide**

**Phong cách:** giống slide HTML của thầy.

* Mỗi slide có một **tiêu đề lớn** và một **dòng phụ đề ngắn**.

* Lệnh đặt trong **khung terminal** (có thanh tiêu đề redis-vm — redis-cli), có dấu nhắc 127.0.0.1:6383\> và output thật.

* Các khối chi tiết dùng dạng **thẻ bấm để mở** (click-to-reveal), giống slide "click to explore" của thầy.

* Mỗi kiểu dữ liệu một **màu nhấn** riêng, dùng xuyên suốt:

  * String: cam (amber)

  * Hash: tím

  * List: xanh dương

  * Sorted Set: xanh ngọc (teal)

  * TTL: đỏ

* Chữ trên slide **ít**, chủ yếu là từ khóa, bảng và lệnh. Phần giải thích nằm trong lời nói.

**Bố cục theo yêu cầu của nhóm (lý thuyết rồi demo luôn):** mỗi slide kiểu dữ liệu chia đôi. Bên trái là lý thuyết ngắn. Bên phải là **ảnh chụp chạy thật trên VM**. Video demo đầy đủ đặt ở slide 7\.

**Tài nguyên cần chèn:**

| File | Nằm ở | Dùng ở slide |
| :---- | :---- | :---- |
| 00-environment.png | docs/screenshots/01-data-structures/ | 7 |
| 01-string.png | như trên | 2 |
| 02-list.png | như trên | 4 |
| 03-hash.png | như trên | 3 |
| 04-sorted-set.png | như trên | 5 |
| 05-ttl-countdown.png | như trên | 6 |
| 06-summary.png | như trên | 7 |
| demo01-data-structures.mp4 | Drive nhóm | 7 |

Nếu gen bằng AI, có thể dán nguyên file này kèm câu lệnh:

"Tạo phần slide HTML theo đúng nội dung dưới đây, cùng style với base file đính kèm. Mỗi mục 'Slide N' là một slide. Giữ nguyên lệnh và output trong khung terminal. Phần 'Lời nói' là speaker notes, không hiển thị trên slide."

**Phân bổ thời gian (tổng khoảng 6 phút):**

| Slide | Nội dung | Thời gian |
| :---- | :---- | :---- |
| 1 | Mở đầu: value có kiểu | 0:30 |
| 2 | String | 0:40 |
| 3 | Hash | 0:35 |
| 4 | List | 0:35 |
| 5 | Sorted Set \+ so sánh với List | 0:50 |
| 6 | TTL | 0:50 |
| 7 | Video demo | 1:30 |
| 8 | Chọn cấu trúc nào \+ quiz \+ chuyển phần | 0:30 |

Nếu thiếu giờ: slide 7 chỉ chiếu đoạn TTL đếm ngược (khoảng 30 giây), vì các kiểu khác đã có ảnh ở slide 2–5.

---

## **Slide 1: Redis không chỉ là "key → chuỗi"**

**Phụ đề:** Value trong Redis có kiểu, và mỗi kiểu có bộ lệnh riêng chạy ngay trên server.

**Tình huống mở đầu** (khung nổi bật, giống phần "The challenge" của thầy):

Game có 1 triệu người chơi. Mỗi trận thắng được cộng điểm. Màn hình chính luôn hiện **Top 3** và **hạng của bạn**. Nếu Redis chỉ lưu được chuỗi, mỗi lần cộng điểm ta phải: đọc cả bảng điểm về app → sửa → ghi lại. Chậm, và 2 người cộng cùng lúc thì ghi đè lên nhau. Với Redis: **1 lệnh** ZINCRBY leaderboard 600 carol.

**Sơ đồ** (ở giữa slide): một ô key có 4 mũi tên tỏa ra 4 ô màu:

                ┌─ String      "890000" · JSON · bộ đếm  
   key  ────────┼─ Hash        { name, email, role }  
                ├─ List        \[ job1, job2, job3 \]   (thứ tự chèn)  
                └─ Sorted Set  { carol:2400, bob:2300 } (tự sắp theo điểm)

**3 ý ở chân slide** (3 thẻ nhỏ):

* **Có kiểu:** chọn đúng kiểu thì bài toán thành 1 lệnh.

* **Chạy trên server:** không kéo dữ liệu về ứng dụng.

* **Nguyên tử (atomic):** Redis xử lý lần lượt từng lệnh, nên không bị ghi đè lẫn nhau.

**Lời nói:** "Phần trước Nam Anh đã nói Redis lưu dữ liệu trong RAM nên rất nhanh. Điểm mạnh thứ hai là value trong Redis có kiểu. Lấy ví dụ bảng xếp hạng game: nếu chỉ lưu được chuỗi, mỗi lần cộng điểm ta phải kéo cả bảng về, sửa, rồi ghi lại, vừa chậm vừa dễ ghi đè. Redis làm việc đó bằng một lệnh, chạy ngay trên server, và lệnh đó là nguyên tử. Phần này mình giới thiệu 4 kiểu hay dùng nhất, String, Hash, List, Sorted Set, cùng cơ chế TTL để key tự hết hạn."

---

## **Slide 2: String: cache và bộ đếm (màu cam)**

**Phụ đề:** 1 key → 1 giá trị · tối đa 512 MB · text, số, JSON đều được.

**Cột trái: lý thuyết**

| Lệnh | Ý nghĩa |
| :---- | :---- |
| SET key value EX 60 | Ghi giá trị **và** gán TTL 60 giây trong 1 lệnh |
| GET key | Đọc giá trị |
| INCR / INCRBY key n | Tăng số nguyên, **nguyên tử** |
| SET key value NX | Chỉ ghi nếu key chưa có (dùng làm khóa) |

**Dùng khi:** cache kết quả API/truy vấn, đếm lượt xem/like, session, rate limit.

**Cột phải: chạy thật trên VM** (chèn 01-string.png, hoặc khung terminal):

127.0.0.1:6383\> SET cache:product:1001 '{"id":1001,"name":"Ban phim co","price":890000}' EX 60  
OK  
127.0.0.1:6383\> GET cache:product:1001  
"{\\"id\\":1001,\\"name\\":\\"Ban phim co\\",\\"price\\":890000}"  
127.0.0.1:6383\> TTL cache:product:1001  
(integer) 60  
127.0.0.1:6383\> INCR stats:page:home:views  
(integer) 1  
127.0.0.1:6383\> INCR stats:page:home:views  
(integer) 2  
127.0.0.1:6383\> INCRBY stats:page:home:views 10  
(integer) 12

**Thẻ bấm để mở: "Vì sao INCR quan trọng?"**

2 người cùng bấm like khi lượt like đang là 10\. Nếu app tự đọc 10, cộng 1, rồi ghi 11, thì cả hai cùng ghi 11, mất 1 lượt. INCR làm việc đọc, cộng, ghi bên trong Redis như một bước duy nhất, nên kết quả luôn là 12\.

**Lời nói:** "String là kiểu đơn giản nhất: một key, một giá trị. Hai cách dùng phổ biến nhất. Một là cache: lưu nguyên chuỗi JSON, và SET ... EX 60 vừa ghi vừa gán thời gian sống 60 giây trong một lệnh. Hai là bộ đếm: INCR tăng lên 1, 2, rồi INCRBY 10 thành 12\. Điểm quan trọng là INCR nguyên tử, nên nghìn người cùng bấm like cũng không mất lượt nào."

---

## **Slide 3: Hash: lưu một object (màu tím)**

**Phụ đề:** 1 key chứa nhiều cặp **field → value**, giống một dòng trong bảng.

**Cột trái: lý thuyết**

| Lệnh | Ý nghĩa |
| :---- | :---- |
| HSET key f1 v1 f2 v2 | Ghi một hoặc nhiều field |
| HGET key field | Đọc 1 field |
| HGETALL key | Đọc toàn bộ |
| HINCRBY key field n | Tăng số trong 1 field |

**Dùng khi:** hồ sơ user, giỏ hàng, thông tin sản phẩm, cấu hình.

**Cột phải: chạy thật trên VM** (chèn 03-hash.png):

127.0.0.1:6383\> HSET user:1001 name 'Viet Toan' email toan@example.com role member login\_count 0  
(integer) 4  
127.0.0.1:6383\> HINCRBY user:1001 login\_count 1  
(integer) 1  
127.0.0.1:6383\> HSET user:1001 role admin  
(integer) 0  
127.0.0.1:6383\> HGETALL user:1001  
1\) "name"         2\) "Viet Toan"  
3\) "email"        4\) "toan@example.com"  
5\) "role"         6\) "admin"  
7\) "login\_count"  8\) "1"

**Bảng so sánh nhỏ (chân slide): lưu object bằng String JSON hay Hash?**

|  | String (JSON) | Hash |
| :---- | :---- | :---- |
| Đọc cả object | GET, rất gọn | HGETALL |
| Sửa 1 thuộc tính | Đọc → sửa → ghi lại cả chuỗi | HSET đúng 1 field |
| Tăng số đếm | Không làm trực tiếp được | HINCRBY |
| Hợp với | Cache nguyên khối, ít sửa | Object hay sửa từng phần |

**Lời nói:** "Hash giống một object: một key, nhiều field. Ưu điểm là sửa đúng chỗ cần sửa. Đổi role từ member sang admin chỉ cần HSET một field, tăng số lần đăng nhập thì dùng HINCRBY, các field khác giữ nguyên. Nếu lưu JSON trong String, muốn đổi một thuộc tính ta phải đọc cả chuỗi, sửa rồi ghi lại. Nên: cache nguyên khối thì dùng String, object hay sửa từng phần thì dùng Hash."

---

## **Slide 4: List: hàng đợi công việc (màu xanh dương)**

**Phụ đề:** Danh sách giữ **thứ tự chèn** · cho phép trùng · thêm/lấy ở 2 đầu rất nhanh O(1).

**Hình minh họa** (đầu slide, có hiệu ứng mũi tên):

 LPOP ◀──  \[ job:1 \| job:2 \| job:3 \]  ◀── RPUSH  
 (worker lấy ra ở đầu)          (app đẩy việc vào cuối)  
                 FIFO: vào trước, ra trước

**Cột trái: lý thuyết**

| Lệnh | Ý nghĩa |
| :---- | :---- |
| RPUSH / LPUSH | Thêm vào cuối / đầu |
| LPOP / RPOP | Lấy ra ở đầu / cuối |
| BLPOP key timeout | Chờ (block) đến khi có việc mới |
| LRANGE key 0 \-1 | Xem toàn bộ |

**Dùng khi:** queue gửi email/xử lý ảnh, stack, "10 hoạt động gần nhất" (LPUSH \+ LTRIM).

**Cột phải: chạy thật trên VM** (chèn 02-list.png):

127.0.0.1:6383\> RPUSH queue:emails 'job:1 gui mail chao mung' 'job:2 gui OTP' 'job:3 gui hoa don'  
(integer) 3  
127.0.0.1:6383\> LPOP queue:emails  
"job:1 gui mail chao mung"  
127.0.0.1:6383\> LRANGE queue:emails 0 \-1  
1\) "job:2 gui OTP"  
2\) "job:3 gui hoa don"

**Thẻ bấm để mở: "Giới hạn"**

Đã LPOP là phần tử biến mất khỏi Redis. Nếu worker chết giữa chừng thì job mất theo. Hệ thống cần đảm bảo hơn nên dùng LMOVE hoặc Redis Streams.

**Lời nói:** "List giữ đúng thứ tự chèn. Ứng dụng đẩy việc vào cuối bằng RPUSH, worker lấy ra ở đầu bằng LPOP, thế là có một hàng đợi FIFO. Trên VM, ba job được đẩy vào, LPOP lấy job 1 ra trước, còn lại job 2 và job 3\. Thực tế worker dùng BLPOP để ngồi chờ đến khi có việc, không phải hỏi liên tục."

---

## **Slide 5: Sorted Set: bảng xếp hạng (màu xanh ngọc)**

**Phụ đề:** Mỗi member có 1 **score** · Redis **luôn tự sắp xếp** theo score · member không trùng.

**Cột trái: lý thuyết**

| Lệnh | Ý nghĩa |
| :---- | :---- |
| ZADD key score member | Thêm, hoặc cập nhật điểm nếu đã có |
| ZINCRBY key n member | Cộng điểm |
| ZREVRANGE key 0 2 WITHSCORES | Top 3 điểm cao nhất |
| ZREVRANK key member | Hạng (đếm từ 0\) |
| ZRANGEBYSCORE key min max | Lọc theo khoảng điểm |

**Cột phải: chạy thật trên VM** (chèn 04-sorted-set.png). Nên làm hiệu ứng **trước/sau**:

| Trước | Sau ZINCRBY leaderboard:game 600 carol |
| :---- | :---- |
| 1\. bob, 2300 | 1\. **carol, 2400** (tăng hạng) |
| 2\. eve, 2100 | 2\. bob, 2300 |
| 3\. carol, 1800 | 3\. eve, 2100 |

127.0.0.1:6383\> ZREVRANK leaderboard:game carol  
(integer) 0          ← hạng 1 (đếm từ 0\)

**Bảng so sánh List và Sorted Set (chân slide, nổi bật):**

|  | List | Sorted Set |
| :---- | :---- | :---- |
| Thứ tự | Theo **thứ tự chèn** | Theo **score**, tự sắp |
| Trùng lặp | Cho phép | Member **duy nhất** |
| Trả lời câu hỏi | "Ai đến trước?" | "Ai đứng thứ mấy?" |
| Hợp với | Queue, timeline | Xếp hạng, ưu tiên, hẹn giờ |

**Thẻ bấm để mở: "Bên trong Sorted Set có gì?"**

**Skip list** để duyệt theo thứ tự trong O(log N), cộng **hash table** để tra điểm theo tên trong O(1). Vì vậy lấy top-N hay xem hạng vẫn nhanh dù có hàng triệu người chơi. SQL thì phải ORDER BY mỗi lần xem.

**Lời nói:** "Sorted Set giải đúng bài toán ở slide đầu. Mỗi người chơi là một member có điểm số, và Redis luôn tự giữ thứ tự theo điểm. Ban đầu bob dẫn đầu, carol đứng thứ ba với 1800\. Carol thắng thêm một trận, ZINCRBY cộng 600, và carol vươn lên hạng 1 với 2400\. Ta không phải sắp xếp gì cả. Khác biệt với List rất rõ: List trả lời 'ai đến trước', Sorted Set trả lời 'ai đứng thứ mấy'. List cho phép trùng, Sorted Set thì mỗi member chỉ có một."

---

## **Slide 6: TTL: key tự hết hạn (màu đỏ)**

**Phụ đề:** Gán thời gian sống cho key, hết giờ Redis tự xóa.

**Khối 1: Gán và gỡ TTL**

| Lệnh | Tác dụng |
| :---- | :---- |
| SET key value EX 5 | Ghi **và** gán TTL 5 giây (khuyên dùng, 1 lệnh nguyên tử) |
| EXPIRE key 300 | Gán TTL cho key **đã có** (mọi kiểu dữ liệu) |
| TTL key | Xem số giây còn lại |
| PERSIST key | Gỡ TTL, key thành vĩnh viễn |

**Khối 2: Đọc kết quả TTL** (to, nổi bật nhất slide):

| TTL trả về | Ý nghĩa |
| :---- | :---- |
| **số dương** (5, 4, 3...) | Key còn sống bấy nhiêu giây |
| **\-1** | Key **còn đó**, nhưng **không có hạn** |
| **\-2** | Key **không tồn tại** (đã hết hạn hoặc chưa từng có) |

**Khối 3: Timeline chạy thật trên VM** (chèn 05-ttl-countdown.png, hoặc vẽ dạng dòng thời gian):

SET session:abc123 user:1001 EX 5  
TTL → 5 → 4 → 3 → 2 → 1 → \-2  
GET session:abc123     → (nil)  
EXISTS session:abc123  → 0

**Khối 4 (khung cảnh báo màu đỏ): Cảnh báo: Bẫy hay gặp**

SET cache:product:1001 '{"price":850000}'           → TTL \= \-1   (mất TTL\!)  
SET cache:product:1001 '{"price":800000}' KEEPTTL   → TTL giữ nguyên

SET lại một key sẽ **xóa TTL cũ**, khiến cache bỗng thành vĩnh viễn. Muốn giữ TTL thì thêm KEEPTTL, hoặc gán lại EX.

**Thẻ bấm để mở: "Redis xóa key hết hạn lúc nào?"**

* **Passive:** khi có client truy cập key, Redis thấy quá hạn thì xóa ngay. Client không bao giờ đọc được key đã hết hạn.

* **Active:** khoảng 10 lần mỗi giây, Redis lấy mẫu ngẫu nhiên các key có TTL để dọn dần.

* Hết hạn (**expired**) khác bị loại do đầy RAM (**evicted**). Phần Eviction của Tường sẽ nói rõ.

**Lời nói:** "TTL là thời gian sống của key. Ta gán ngay khi ghi bằng SET ... EX, hoặc gán sau bằng EXPIRE. Lệnh TTL trả về số giây còn lại, và có hai giá trị đặc biệt cần nhớ: \-1 là key còn đó nhưng không bao giờ hết hạn, \-2 là key không tồn tại nữa. Trên VM, session có TTL 5 giây đếm ngược về 1, rồi GET trả nil, TTL trả \-2. Redis đã tự xóa key. Và một cái bẫy rất hay gặp: SET lại một key sẽ làm mất TTL cũ, cache bỗng thành vĩnh viễn. Muốn giữ thì thêm KEEPTTL."

---

## **Slide 7: Demo trên VM**

**Phụ đề:** Ubuntu 24.04.3 LTS · Redis 7.0.15 · VM 512 MB · instance riêng port 6383\.

**Bố cục:**

* **Giữa slide:** video demo01-data-structures.mp4, link Drive, khoảng 1:30 sau khi cắt. Có nút phát. Kèm bản offline dự phòng trên máy trình chiếu.

* **Dưới video, một hàng 3 thẻ nhỏ:**

  * bash demos/01-data-structures/run.sh: 1 script chạy cả 4 kiểu dữ liệu và TTL.

  * Tự xóa dữ liệu cũ mỗi lần chạy, nên chạy lại bao nhiêu lần cũng ra cùng kết quả.

  * Chặn chạy trên port 6379, không đụng Redis của hệ thống.

* **Góc phải:** ảnh nhỏ 06-summary.png (bảng key, kiểu dữ liệu, TTL, và expired\_keys tăng, evicted\_keys \= 0).

**Lời nói** (vừa chiếu vừa nói, ngắn gọn vì lý thuyết đã nói ở slide 2–6):

* Đầu video: "Demo chạy trên VM Ubuntu 24.04 với Redis 7.0.15, dùng instance riêng ở port 6383 để không ảnh hưởng demo khác."

* Phần String và List: "Cache có TTL 60 giây, bộ đếm lên 12\. Job 1 được lấy ra trước, đúng FIFO."

* Phần Sorted Set: "Carol được cộng điểm và vượt lên dẫn đầu."

* Phần TTL: "Các bạn để ý TTL đếm ngược... và GET trả nil."

* Cuối: "expired\_keys tăng vì key hết hạn, còn evicted\_keys bằng 0 vì RAM vẫn dư. Phân biệt hai con số này sẽ quay lại ở phần Eviction."

---

## **Slide 8: Chọn cấu trúc nào?**

**Phụ đề:** Chọn đúng cấu trúc thì bài toán chỉ còn 1–2 lệnh.

**Bảng tra nhanh:**

| Bài toán | Chọn | Lệnh chính |
| :---- | :---- | :---- |
| Cache kết quả API | String \+ TTL | SET ... EX, GET |
| Đếm lượt xem | String | INCR |
| Hồ sơ user, giỏ hàng | Hash | HSET, HINCRBY |
| Hàng đợi gửi email | List | RPUSH, BLPOP |
| Bảng xếp hạng | Sorted Set | ZADD, ZINCRBY, ZREVRANGE |
| Session, OTP | String \+ TTL | SET ... EX |

**Quiz nhanh** (3 câu, dạng bấm chọn đáp án như slide của thầy, có thể dùng để hỏi lớp):

1. TTL key trả về \-1 nghĩa là gì? A. Key đã hết hạn · **B. Key tồn tại nhưng không có hạn** · C. Key không tồn tại

2. Làm bảng xếp hạng top 10 người chơi nên dùng kiểu nào? A. List · B. Hash · **C. Sorted Set**

3. Key cache đang có TTL 60 giây. Chạy SET key "giá trị mới" (không thêm gì) thì TTL thành? A. Vẫn 60 · **B. \-1 (mất TTL)** · C. \-2

**Dòng chuyển phần (chân slide):** "String \+ TTL là nền móng của cache → **Phần 3: Cache-Aside**."

**Lời nói:** "Tóm lại: giá trị đơn hoặc JSON dùng String, object hay sửa từng phần dùng Hash, hàng đợi dùng List, xếp hạng dùng Sorted Set. Thứ gì là cache thì luôn gắn TTL. \[Nếu còn thời gian thì hỏi lớp 1 câu quiz.\] Chính String kết hợp TTL là nền móng của mô hình Cache-Aside. Mời Thắng trình bày cách dùng nó để tăng tốc một truy vấn chậm."

---

## **B. Câu hỏi có thể bị hỏi và cách trả lời ngắn**

| Câu hỏi | Trả lời |
| :---- | :---- |
| Vì sao dùng SET ... EX thay vì SET rồi EXPIRE? | 1 lệnh là nguyên tử. 2 lệnh có thể bị gián đoạn ở giữa, để lại key không bao giờ hết hạn. |
| Key hết hạn có bị xóa khỏi RAM ngay đúng giây đó không? | Không nhất thiết. Redis xóa khi có truy cập hoặc khi lấy mẫu định kỳ, nhưng client không bao giờ đọc được key đã hết hạn. |
| Đặt TTL cho 1 field trong Hash được không? | Từ Redis 7.4 có HEXPIRE. Bản 7.0 trên VM chỉ đặt TTL cho cả key. |
| List làm queue có an toàn không? | Đủ cho việc đơn giản. Worker chết sau LPOP thì mất job. Cần chắc chắn hơn thì dùng LMOVE hoặc Streams. |
| Sao không dùng KEYS \* để liệt kê? | KEYS duyệt toàn bộ key, chặn server đơn luồng. Dùng SCAN, script demo cũng dùng \--scan. |

Nếu bị yêu cầu thử thêm lệnh: mở redis-cli \-p 6383 và gõ theo demos/01-data-structures/demo.redis.

