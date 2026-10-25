# Nội dung và thiết kế slide: Cache-Aside (Lazy Loading)

**Người trình bày:** Nguyễn Quốc Thắng (theo phân công trong bản Data Structures và TTL).  
**Ngôn ngữ:** tiếng Việt, giữ thuật ngữ Cache Hit, Cache Miss, Cache-Aside, TTL và tên các chiến lược.  
**Vị trí:** mục 03 của seminar, sau Data Structures and TTL và trước Memory and Eviction.  
**Số lượng:** 8 slide nội dung, gồm 6 slide lý thuyết và 2 slide demo. Trang tiêu đề mục `#cache` đã có và không tính vào 8 slide này.

Nguồn chính là [docs/theory/03-cache-aside.md](docs/theory/03-cache-aside.md). Bản thiết kế giữ toàn bộ các nhóm kiến thức trong tài liệu đó. Phần demo bám vào [README](demos/02-cache-aside/README.md), [app.py](demos/02-cache-aside/app.py), [giao diện](demos/02-cache-aside/index.html) và [Redis config](redis/redis-cache-aside.conf). Những mục TODO trong tài liệu lý thuyết là ghi chú cũ, không phải yêu cầu sửa ứng dụng demo.

---

## A. Quy ước thiết kế

- Giữ canvas 1280 × 720, nền trắng ngà `#fffefa`, chữ chính `#20242b`, chữ phụ `#414b5a`. Không dùng chữ xám nhạt trên nền trắng.
- Tiêu đề khoảng 40 px, phụ đề 19 px, nội dung chính 20–23 px. Các giải thích dài đặt trong speaker notes, mở bằng phím **N**.
- Dùng sơ đồ HTML/SVG có thể sửa, bảng và các hàng so sánh đơn giản. Không cần ảnh trang trí hoặc ảnh terminal.
- Xanh ngọc thể hiện HIT và dữ liệu cache còn dùng được. Đỏ thể hiện MISS, stale hoặc nhiều truy vấn dồn xuống database. Luôn có nhãn chữ đi kèm màu.
- Các nút chỉ chuyển trạng thái của sơ đồ hoặc chọn video. Bấm nút không chuyển trang. Những kiến thức bắt buộc đều có trên mặt slide, không giấu trong thẻ mở rộng.
- Sáu slide đầu chỉ trình bày kiến thức chung. Port, key, tham số ứng dụng và cách đọc số đo chỉ xuất hiện ở phần demo hoặc notes.
- Sơ đồ cơ chế không mang số đo hiệu năng. Biểu diễn TTL chỉ mô tả thứ tự hết hạn, không phải kết quả benchmark.
- Không diễn giải TTL hoặc invalidation thành bảo đảm dữ liệu luôn mới tức thì. Các thao tác database và Redis không tự trở thành một transaction chung.

### Cấu trúc và thời lượng

| Slide | Tiêu đề | Thời gian nói gợi ý |
|---|---|---:|
| 1 | Cache Hit và Cache Miss | 0:40 |
| 2 | Cache-Aside: ứng dụng điều phối việc đọc | 0:55 |
| 3 | Cache-Aside và các chiến lược khác | 0:50 |
| 4 | Dữ liệu cũ, invalidation và TTL | 0:55 |
| 5 | Penetration và Stampede | 1:00 |
| 6 | Avalanche và TTL Jitter | 0:50 |
| 7 | Demo: bốn tình huống Cache-Aside | 0:20 giới thiệu + video |
| 8 | Đọc kết quả demo | 0:55 |

Khoảng 6 phút 25 giây lời nói, cộng thời lượng video được chọn. Không ấn định độ dài hoặc kết quả đo của video khi chưa đối chiếu bản ghi. Thời lượng không xuất hiện trên nút **Video**.

---

## Slide 1: Cache Hit và Cache Miss

**Phụ đề:** Cache giúp giảm truy vấn database khi dữ liệu cần đọc đã có sẵn.

**Bố cục:** hai hàng ngang, cùng bắt đầu ở Application và kiểm tra Redis. Hàng HIT dừng ở dữ liệu cache. Hàng MISS có thêm bước ứng dụng đọc database rồi điền cache.

**Nội dung hiển thị:**

- **HIT:** cache có dữ liệu hợp lệ, ứng dụng trả kết quả trực tiếp.
- **MISS:** cache thiếu dữ liệu, đã hết hạn hoặc ứng dụng xác định không còn hợp lệ. Ứng dụng cần đọc nguồn dữ liệu chính.
- HIT thường giảm độ trễ và tải database. MISS còn tốn bước đọc database và điền cache.

**Trực quan:** các ô thể hiện nơi xử lý, đường nối thể hiện thứ tự công việc. Database chỉ xuất hiện trong nhánh MISS. Nhãn “Application đọc DB” tránh hiểu lầm Redis tự truy vấn database.

**Lời nói:**

> Cache là bản sao phục vụ truy cập nhanh. Nếu có giá trị dùng được, ứng dụng trả ngay. Khi thiếu giá trị, ứng dụng phải lấy ở database rồi mới có dữ liệu để trả và cache cho lần sau. Vì vậy hiệu quả phụ thuộc nhiều vào tần suất truy cập lại. Redis không tự biết dữ liệu trong database đã đổi chỉ vì key vẫn còn TTL.

**Chuyển ý:** Ai thực hiện các bước kiểm tra, đọc database và lưu cache?

## Slide 2: Cache-Aside: ứng dụng điều phối việc đọc

**Phụ đề:** Lazy Loading: dữ liệu được nạp vào cache khi có request cần đến.

**Bố cục:** sequence diagram bốn cột **User / Application / Redis / Database**. Hai nút **Cache Hit** và **Cache Miss** đổi nhánh, giữ nguyên vị trí các thành phần.

**Nhánh HIT:**

1. User gửi request tới Application.
2. Application đọc Redis bằng GET.
3. Redis trả giá trị cache.
4. Application trả giá trị cho User, không đọc database.

**Nhánh MISS:**

1. User gửi request, Application GET Redis.
2. Redis trả MISS.
3. Application query Database và nhận dữ liệu.
4. Application lưu dữ liệu vào Redis kèm TTL.
5. Application trả kết quả cho User.

**Câu chốt hiển thị:** Application chịu trách nhiệm đọc DB và điền cache khi MISS.

**Thẻ mở rộng:** Vì sao gọi là “lazy”? Chỉ những dữ liệu được yêu cầu mới cần đi vào cache, thay vì nạp toàn bộ database từ đầu.

**Lời nói:**

> Đây là trách nhiệm của mã ứng dụng. Redis cung cấp GET, SET và expiration. Chính ứng dụng quyết định khi nào query database, cache key nào và đặt TTL bao lâu. Database là nguồn dữ liệu chính trong mô hình này. Nhánh HIT bỏ qua database, còn nhánh MISS đi qua cả hai hệ thống. Các mũi tên biểu diễn thứ tự thao tác, không biểu diễn thời gian chờ.

## Slide 3: Cache-Aside và các chiến lược khác

**Phụ đề:** Phân biệt nơi xử lý cache miss và thời điểm ghi database.

**Bố cục:** bảng năm hàng, chia hai nhóm bằng nhãn **Đọc** và **Ghi** ở cột đầu. Không dùng năm thẻ riêng biệt.

| Nhóm | Chiến lược | Cơ chế chính |
|---|---|---|
| Đọc | Cache-Aside | Application đọc DB và điền cache khi MISS. |
| Đọc | Read-Through | Cache layer đọc DB và điền cache khi MISS. |
| Ghi | Write-Through | Ghi qua cache layer, cập nhật DB đồng bộ trước khi hoàn tất. |
| Ghi | Write-Behind / Write-Back | Ghi cache trước, cập nhật DB bất đồng bộ sau. |
| Ghi | Write-Around | Ghi thẳng DB, bỏ qua bước điền cache khi ghi. |

**Câu chốt:** Chính sách đọc và chính sách ghi có thể kết hợp trong cùng hệ thống.

**Lời nói:**

> Cache-Aside khác Read-Through ở bên nào chịu trách nhiệm nạp dữ liệu khi miss. Các dòng phía dưới mô tả đường ghi. Write-Through chờ cập nhật database, trong khi Write-Behind cho phép cache và database lệch nhau trong thời gian chờ ghi. Write-Around ghi database trực tiếp. Nếu đã có bản sao trong cache thì vẫn cần chính sách xóa hoặc làm mới bản sao đó.

**Thẻ mở rộng:** Write-Behind cần xử lý hàng đợi ghi, retry và nguy cơ mất các bản ghi chưa đẩy xuống DB. Bảng này mô tả mô hình chung, không khẳng định Redis tự cung cấp tất cả các chính sách.

## Slide 4: Dữ liệu cũ, invalidation và TTL

**Phụ đề:** Database thay đổi trong khi bản sao ở cache có thể vẫn còn TTL.

**Bố cục:** ví dụ bảng ba trạng thái với các cột **Sự kiện / Database / Redis / Lần đọc tiếp theo**. Các nhãn v1 và v2 chỉ là phiên bản minh họa, không phải output demo.

| Sự kiện | Database | Redis | Lần đọc tiếp theo |
|---|---|---|---|
| DB cập nhật | v2 | v1 còn TTL | Có thể trả v1: stale data. |
| App xóa cache sau khi cập nhật DB | v2 | Không có key | MISS, ứng dụng đọc DB. |
| App nạp lại sau MISS | v2 | v2 + TTL mới | HIT trả v2. |

**Hai hàng giải thích bên dưới:**

- **Invalidation:** ứng dụng xóa hoặc làm mới bản sao cache khi dữ liệu thay đổi.
- **TTL:** đặt hạn dùng. Khi hết hạn, lần đọc sau cần nạp lại dữ liệu.

**Câu nhấn:** TTL giới hạn thời gian dùng bản sao cũ, không bảo đảm dữ liệu mới tức thì.

**Thẻ mở rộng:** Vì sao cập nhật DB rồi mới xóa cache? Nếu xóa trước, một reader có thể nạp lại dữ liệu DB cũ trong lúc writer chưa commit. Cập nhật DB rồi xóa cache vẫn có race giữa các reader/writer và cần xử lý lỗi invalidation.

**Lời nói:**

> TTL trả lời “bản sao được dùng bao lâu”, còn invalidation trả lời “khi dữ liệu đổi thì xử lý bản sao thế nào”. Nếu database vừa đổi, key còn TTL vẫn có thể chứa dữ liệu cũ. Một cách thường dùng là commit DB, xóa key tương ứng, để lần đọc sau tự nạp lại. Hệ thống có nhiều truy cập đồng thời vẫn cần thiết kế consistency và xử lý trường hợp DEL thất bại.

## Slide 5: Penetration và Stampede

**Phụ đề:** Cùng gây nhiều MISS, nhưng nguyên nhân và cách xử lý khác nhau.

**Bố cục:** hai nửa phẳng, ngăn bằng một đường dọc. Mỗi nửa có sơ đồ request dồn xuống DB, nguyên nhân và biện pháp tương ứng.

**Bên trái: Cache Penetration**

- Request lặp lại cho dữ liệu không tồn tại trong cache lẫn DB.
- Nếu không cache kết quả “không tồn tại”, request sau lại xuống DB.
- **Negative caching:** lưu dấu “không tồn tại” với TTL ngắn.
- **Rate limiter / Bloom filter:** hạn chế request hoặc lọc key chắc chắn không tồn tại.

**Bên phải: Cache Stampede**

- Một key phổ biến hết hạn, nhiều request đồng thời cùng MISS.
- Nhiều request thực hiện cùng một truy vấn DB để nạp lại key.
- **Lock / single-flight:** một request nạp, các request khác chờ hoặc dùng phương án phù hợp.
- **Background refresh:** chủ động làm mới dữ liệu phổ biến.

**Thẻ mở rộng:** Negative cache cần sentinel phân biệt với cache miss. Bloom filter có thể báo dương tính giả. Lock cần thời hạn, cơ chế giải phóng đúng chủ sở hữu và xử lý loader thất bại.

**Lời nói:**

> Penetration là hỏi thứ không có, nên miss lặp đi lặp lại. Stampede là thứ có thật và được đọc nhiều, nhưng key vừa hết hạn nên mọi người cùng đi lấy lại. Negative caching xử lý tình huống đầu. Phối hợp chỉ một loader hoặc refresh trước khi hết hạn giúp tình huống thứ hai. Không coi việc thêm một lock là giải pháp hoàn chỉnh nếu chưa xử lý timeout và lỗi.

## Slide 6: Avalanche và TTL Jitter

**Phụ đề:** Nhiều key hết hạn cùng lúc có thể dồn tải xuống database.

**Bố cục:** hai dải gồm bốn key. Ở dải trái các điểm hết hạn thẳng hàng. Ở dải phải các điểm hết hạn giãn ra. Không đặt số giây hoặc thang đo benchmark lên sơ đồ.

**Nội dung:**

- **Cache Avalanche:** nhiều key cùng hết hạn, hoặc cache gặp sự cố khiến nhiều request chuyển xuống DB.
- **TTL Jitter:** thêm thành phần ngẫu nhiên vào TTL để giảm việc nhiều key hết hạn cùng lúc.
- Công thức minh họa: `TTL = base TTL + random jitter`.
- Khi Redis không khả dụng, cần giới hạn tải xuống DB và chính sách fallback. Jitter chỉ xử lý việc hết hạn đồng loạt.

**Chú thích sơ đồ:** Thời điểm hết hạn minh họa, không phải dữ liệu đo.

**Lời nói:**

> Nếu ứng dụng nạp nhiều key cùng lúc và đặt cùng TTL, chúng có thể đồng loạt hết hạn. Thêm một khoảng ngẫu nhiên giúp tách các thời điểm này. Tuy nhiên avalanche còn có thể đến từ Redis ngừng hoạt động. Trong trường hợp đó, thay đổi TTL không làm cache hoạt động lại. Ứng dụng cần bảo vệ database bằng giới hạn concurrency, rate limit hoặc circuit breaker và phương án trả kết quả phù hợp.

## Slide 7: Demo: bốn tình huống Cache-Aside

**Phụ đề:** Cùng một key, so sánh đường đọc và quan sát thời gian từng request.

**Tài nguyên:** video sẽ được chia sẻ qua link Drive. Slide chỉ chứa placeholder, không nhúng MP4 hoặc dữ liệu Base64 để giữ HTML nhẹ. Để trống `driveUrl` trong `demo02-config` cho đến khi có URL thật. File `docs/screenshots/02-cache-aside/cache-aside-demo.mp4` vẫn là tài nguyên riêng trong repository, không tải từ slide.

**Bố cục:** hai nút **Quy trình** và **Video**. Mặc định hiện quy trình. Khi chọn Video, hiện placeholder **Demo 02 · Cache-Aside** và dòng **Link Drive sẽ được cập nhật sau**. Khi đã có URL thật, hiện liên kết **Mở video trên Drive** để mở ở tab mới. Không có player nhúng hoặc autoplay trong HTML.

**Quy trình hiển thị:**

| Case | Chuẩn bị | Request được đo |
|---|---|---|
| Without Cache | Bỏ qua Redis | Mọi request đọc DB giả lập. |
| With Cache | Xóa key trước | MISS đầu tiên, sau đó HIT khi key còn TTL. |
| After TTL Expiration | Seed key và chờ hết hạn | Request tiếp theo MISS rồi điền cache. |
| After Cache Invalidation | Seed key rồi DEL | Request tiếp theo MISS rồi điền cache. |

**Thông tin nhỏ cạnh sơ đồ:** key `demo:user:1`, Redis `6384`, web app `127.0.0.1:8000`. Cấu hình trong ảnh chạy thực: **TTL 10 s, DB delay 500 ms, 5 request ở cả bốn case**. Đây là tham số hiển thị trong ảnh do người trình bày cung cấp, thay cho mặc định trong mã ứng dụng.

**Lời nói:**

> Database trong demo được giả lập bằng một hàm sleep rồi trả dữ liệu. Lần chạy trong ảnh đặt TTL 10 giây và delay DB 500 ms. Mỗi case có 5 request. Bốn case tách riêng việc bỏ cache, cache rỗng, hết TTL và xóa chủ động. Nhìn trạng thái từng request, thời gian và event log. Các bước seed, xóa hoặc chờ hết TTL là chuẩn bị, không tính vào thời gian request trung bình.

**Nguồn xác nhận:** ba ảnh giao diện và kết quả chạy do người trình bày gửi. Chưa đối chiếu toàn bộ video Drive sẽ gửi sau. Không mô tả việc đọc ảnh thành một lần tự chạy lại demo.

**Giới hạn:** demo chạy request tuần tự trong từng case. Không dùng clip này để kết luận đã tái hiện stampede, penetration hoặc avalanche. DB giả lập trả cùng chuỗi, nên case invalidation minh họa key bị xóa và nạp lại, không kiểm chứng một bản ghi DB thay đổi từ v1 sang v2.

## Slide 8: Đọc kết quả demo

**Phụ đề:** TTL 10 s, DB delay 500 ms. Mỗi tình huống gồm 5 request.

**Bố cục:** bảng số liệu bốn case và dải **5 request thực tế của With Cache**. MISS và HIT có màu lẫn chữ. Nhãn nguồn trên slide ghi **Kết quả từ ảnh chạy thực**.

**Bảng kết quả đọc trực tiếp từ ảnh cung cấp:**

| Case | Request | Trạng thái ghi nhận | Hit rate | Trung bình hiển thị |
|---|---:|---|---|---:|
| Without Cache | 5 | NO CACHE × 5 | Bỏ qua cache | 500.24 ms |
| With Cache | 5 | 1 MISS, rồi 4 HIT | 80% | 100.38 ms |
| After TTL Expiration | 5 | 1 MISS, rồi 4 HIT | 80% | 100.64 ms |
| After Cache Invalidation | 5 | 1 MISS, rồi 4 HIT | 80% | 100.39 ms |

**Dải request With Cache:** MISS **501.18 ms**, sau đó HIT **0.33 / 0.20 / 0.10 / 0.10 ms**. Chiều rộng bằng nhau chỉ biểu diễn thứ tự request, không biểu diễn độ trễ.

**Số liệu chi tiết dành cho notes:**

| Case | Request 1 | Request 2 | Request 3 | Request 4 | Request 5 |
|---|---:|---:|---:|---:|---:|
| Without Cache, tất cả NO CACHE | 500.20 ms | 500.23 ms | 500.33 ms | 500.23 ms | 500.21 ms |
| With Cache, MISS rồi 4 HIT | 501.18 ms | 0.33 ms | 0.20 ms | 0.10 ms | 0.10 ms |
| After TTL Expiration, MISS rồi 4 HIT | 501.18 ms | 0.53 ms | 0.52 ms | 0.49 ms | 0.49 ms |
| After Cache Invalidation, MISS rồi 4 HIT | 500.82 ms | 0.26 ms | 0.34 ms | 0.29 ms | 0.25 ms |

Giữ các số trung bình giao diện hiển thị. Không thay chúng bằng kết quả tính lại từ các giá trị request đã làm tròn. Số lần gọi DB suy ra từ trạng thái và hàm `get_data` là 5 ở Without Cache và 1 ở mỗi case dùng cache. Ảnh không có bộ đếm DB độc lập để đo trực tiếp con số này.

**Cách đọc thời gian:**

- `delay_ms = 500` là thời gian sleep mô phỏng DB trong lần chạy được chụp. Thời gian request còn có overhead, nên MISS khoảng 501 ms và HIT vẫn lớn hơn 0 ms.
- Trung bình từng case chỉ bao gồm request được đo, không gồm thời gian seed key hoặc chờ TTL.
- Mỗi lần chạy thay kết quả cũ, không tự gộp nhiều lần thành benchmark.
- Cả ba case dùng cache trong ảnh đều ghi nhận 1 MISS và 4 HIT, tương ứng 80% hit rate. Đây là số liệu của lần chạy này, không phải lời hứa mọi workload đều có hit rate đó.

**Thẻ mở rộng:** Vì sao trung bình vẫn khoảng 100 ms dù HIT dưới 1 ms? Một MISS 501.18 ms chiếm phần lớn tổng thời gian của 5 request. Với With Cache: `(501.18 + 0.33 + 0.20 + 0.10 + 0.10) / 5 ≈ 100.38 ms`. Không khái quát thành hệ số tăng tốc cố định cho mọi workload.

**Lời nói:**

> Không cache thì mỗi request đều chờ DB giả lập, trung bình 500.24 ms. Với cache, lần đầu MISS mất 501.18 ms, rồi bốn HIT đều dưới 1 ms. Trung bình cả nhóm là 100.38 ms vì vẫn tính lần MISS đầu tiên. Sau hết TTL và sau DEL cũng ghi nhận một MISS rồi bốn HIT, nhưng nguyên nhân key vắng mặt khác nhau. Đây là kết quả thực trong ảnh, với DB giả lập và request tuần tự. Sau phần này, câu hỏi tiếp theo là cache dùng bao nhiêu RAM và khi đầy thì Redis giữ hay loại bỏ key nào.

---

## B. Tài nguyên và thao tác cập nhật

| File | Vai trò |
|---|---|
| `docs/theory/03-cache-aside.md` | Nội dung lý thuyết chính. |
| `demos/02-cache-aside/app.py` | Luồng GET, DB giả lập, SETEX, DEL, TTL và tính thời gian. |
| `demos/02-cache-aside/README.md` | Cách chạy và bốn tình huống. |
| `redis/redis-cache-aside.conf` | Instance Redis riêng ở port 6384. |
| `docs/screenshots/02-cache-aside/cache-aside-demo.mp4` | Video riêng trong repository, không nhúng vào HTML. |
| `slides_redis.html` | Bản triển khai, anchor `#cache-1` đến `#cache-8`. |

Link Drive sẽ được người trình bày gửi sau. Để thêm, sửa `{"driveUrl":""}` trong thẻ JSON `demo02-config`. URL thật sẽ làm hiện liên kết mở Drive và cập nhật thông báo trong placeholder. Video mở ở tab mới khi người trình bày bấm liên kết.

**Cách phân phối hiện tại:** HTML chứa sơ đồ, nội dung và placeholder. Video được cung cấp qua Drive, cần mạng và quyền xem phù hợp để mở liên kết. Dữ liệu MP4/Base64 đã được gỡ khỏi HTML. Các slide và sơ đồ vẫn xem được khi gửi riêng HTML, còn video được xem qua liên kết khi có.

Nội dung đầy đủ dùng speaker notes. Các tương tác chỉ hỗ trợ giải thích, không tự chạy hiệu ứng hoặc request Redis trong lúc trình chiếu. Bản này không yêu cầu thay đổi ứng dụng demo và không yêu cầu chạy thử.

## C. Ghi chú về độ chính xác

- Giữ đầy đủ các chiến lược và ba vấn đề cache từ tài liệu nguồn.
- Điều chỉnh phát biểu “luôn cập nhật” thành giới hạn thời gian stale và trách nhiệm invalidation. [Microsoft Learn: Cache-Aside](https://learn.microsoft.com/en-us/azure/architecture/patterns/cache-aside) xác nhận mô hình này không tự bảo đảm consistency giữa cache và data store.
- TTL là expiration của key, không phải kiểm tra phiên bản trong database. Xem [Redis EXPIRE](https://redis.io/docs/latest/commands/expire/).
- TTL jitter giảm việc hết hạn cùng lúc. Cần xử lý riêng trường hợp cache không khả dụng.
- Slide 7–8 đã thay cấu hình dự kiến từ mã mặc định bằng cấu hình và số liệu thực trong ba ảnh người trình bày cung cấp: TTL 10 s, DB delay 500 ms, 5 request mỗi case. Các số trung bình, HIT/MISS và hit rate được đọc trực tiếp từ ảnh.
- Số lần gọi DB là suy ra từ trạng thái và luồng mã, không phải số đo của một bộ đếm DB trong ảnh. Không khẳng định đã chạy lại hoặc kiểm tra toàn bộ video.
