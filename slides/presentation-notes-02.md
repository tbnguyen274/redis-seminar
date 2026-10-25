# **Hướng dẫn tạo slide Quản lý Bộ nhớ và Cơ chế Eviction**

Phần 3 của seminar Redis  \|  Tiếng Việt  \|  5–6 phút gồm 90 giây video demo

Tạo 7 slide trình bày cơ chế quản lý bộ nhớ Redis: từ giới hạn maxmemory, phân biệt expiration và eviction, các chính sách loại bỏ dữ liệu, đến thuật toán Approximate LRU. Kết thúc bằng demo thực nghiệm allkeys-lru trên instance 10 MB và khuyến nghị production. Nội dung tiếp nối từ phần Cache-Aside; ví dụ xuyên suốt dùng tình huống cache sản phẩm đã giới thiệu ở phần mở đầu.

## **A  Hướng dẫn chung**

Mỗi slide có một tiêu đề lớn, một phụ đề ngắn và một thông điệp chính. Nội dung hiển thị khoảng 20–40 từ, ưu tiên sơ đồ và bảng so sánh ngắn; phần "Lời nói" dùng làm speaker notes, không chép lên slide.

Dùng tiếng Việt tự nhiên, trung tính. Giải thích thuật ngữ ngay lần đầu: eviction là loại dữ liệu khi chạm giới hạn bộ nhớ; maxmemory là trần RAM cho phép; LRU là Least Recently Used — ưu tiên loại key ít được truy cập gần đây nhất; idle time là khoảng thời gian key không được đọc/ghi. Kể tiếp tình huống cache sản phẩm từ phần overview thay vì đọc danh sách định nghĩa.

Khung hình 16:9, nền sáng, chữ tương phản cao. Tiêu đề khoảng 32–40 pt, nội dung 24–28 pt. Màu nhấn đỏ cho Redis, xanh cho dữ liệu tìm thấy, vàng/cam cho cảnh báo giới hạn; không dùng màu làm dấu hiệu duy nhất.

Nếu có base HTML của nhóm, giữ font, màu và điều hướng của base. Không bắt buộc tương tác trên mọi slide; slide demo có thể dùng bấm để hiện từng bước kết quả. Bản tĩnh phải thể hiện đủ nội dung.

Không giảng chi tiết mã nguồn C của Redis, không đi sâu LFU (chỉ nhắc ngắn để so sánh), không trình bày RDB/AOF hoặc Replication trong phần eviction. Không thêm công thức toán phức tạp lên slide; để trong speaker notes nếu cần.

## **Phân bổ thời gian**

| Slide | Nội dung | Thời lượng |
| :---- | :---- | :---- |
| 1 | Vì sao cần giới hạn bộ nhớ (maxmemory) | 45 giây |
| 2 | Phân biệt Expiration và Eviction | 45 giây |
| 3 | Các chính sách maxmemory-policy | 45 giây |
| 4 | Thuật toán Approximate LRU | 45 giây |
| 5 | Demo thực nghiệm: chuẩn bị và cấu hình | 30 giây |
| 6 | Video demo eviction thực tế | 90 giây |
| 7 | Kết luận và khuyến nghị production | 30 giây |

 

 

## **Tài nguyên để tạo slide**

### **Ảnh minh chứng**

Ảnh thuộc giai đoạn chạy demo eviction trên port 6382, được lưu tại: docs/screenshots/03-eviction/

| File | Nội dung cần lấy | Slide |
| :---- | :---- | :---- |
| 01-config.png | PONG, maxmemory 10485760, allkeys-lru, flushall, dbsize 0 | 5 hoặc 6 |
| 02-eviction-trigger.png | Cold keys, benchmark bơm dữ liệu, Hot keys và benchmark tràn RAM | 6 |
| 03-lru-result.png | used\_memory\_human: 9.86M, evicted\_keys: 27, cold keys EXISTS \= 0, hot keys EXISTS \= 2 | 6 |

 

Không cần chèn tất cả ảnh cùng lúc. Slide 5 ưu tiên sơ đồ cấu hình; slide 6 dùng video và ảnh kết quả dự phòng. Crop phần terminal cần đọc nhưng giữ lệnh, output và port liên quan; không sửa nội dung output.

### **Video demo**

Bản gốc: demo-03-eviction.mp4, được lưu tại demos/03-eviction/. Dùng đoạn chọn tổng khoảng 90 giây; bản cắt và đường dẫn chia sẻ cần được bổ sung khi dựng deck. Không gán tên clip mới như thể đã có file.

Video có terminal nền sáng và không có lời dẫn nghe được. Thuyết minh trực tiếp theo slide 6\. Không phát toàn bộ thời gian chờ benchmark; chuẩn bị bản offline để phát trên máy trình chiếu.

### **Thông tin đúng cho minh chứng demo**

| Thành phần | Giá trị dùng trong phần eviction |
| :---- | :---- |
| Instance | Port 6382, config redis/redis-eviction.conf |
| Giới hạn bộ nhớ | maxmemory 10mb (10485760 bytes) |
| Chính sách | maxmemory-policy allkeys-lru |
| Data directory | /tmp/redis-seminar/eviction |
| Persistence | save "", appendonly no (tắt hoàn toàn để cách ly demo) |
| Cold Keys | 3 keys (cold\_k1, cold\_k2, cold\_k3) — ghi 1 lần, không đọc lại |
| Hot Keys | 2 keys (hot\_k1, hot\_k2) — ghi và đọc lại trước khi tràn |
| Kết quả thực nghiệm | RAM \~9.86 MB, 27 keys bị trục xuất, cold EXISTS \= 0, hot EXISTS \= 2 |
| Phạm vi đã kiểm tra | Cấu hình, bơm dữ liệu, kích hoạt eviction, đối chứng LRU |

 

Các số này mô tả lượt chạy demo đã ghi hình. Script tự động (fill\_memory.py) dùng 10 cold keys và 5 hot keys với payload lớn hơn; kết quả CLI thủ công dùng 3 cold keys và 2 hot keys theo shot list. Không chép phiên bản hoặc kết quả từ demo khác sang phần eviction.

 

## **Slide 1  Vì sao cần giới hạn bộ nhớ cho Redis**

**Phụ đề:** maxmemory đặt trần RAM mà Redis được phép sử dụng

**Thời gian:** 0:00–0:45

**Nội dung hiển thị:** Redis lưu toàn bộ dữ liệu trên RAM. Nếu không giới hạn, RAM cạn kiệt → hệ điều hành tắt tiến trình (OOM Killer). maxmemory đặt trần dung lượng để Redis tự quản lý trước khi điều đó xảy ra.

**Định nghĩa trên slide:** maxmemory là tham số cấu hình quy định dung lượng RAM tối đa mà một tiến trình Redis được phép sử dụng.

**Bố cục:** Bên trái vẽ thanh RAM với hai trạng thái: không có maxmemory (thanh đầy đỏ, nhãn "OOM Killer") và có maxmemory (thanh có mốc giới hạn xanh). Bên phải đặt một dòng cấu hình mẫu: maxmemory 10mb. Đây là sơ đồ khái niệm, không phải số đo thực nghiệm.

**Lời nói:** "Ở phần Cache-Aside, chúng ta đã thấy Redis giữ bản cache sản phẩm trong RAM. Nhưng RAM có giới hạn. Nếu ứng dụng liên tục ghi thêm dữ liệu mà không kiểm soát, Redis sẽ chiếm hết bộ nhớ và hệ điều hành Linux sẽ kích hoạt OOM Killer để tắt tiến trình đó một cách đột ngột. Tham số maxmemory cho phép đặt trần dung lượng RAM. Trước mỗi lệnh ghi, Redis kiểm tra xem bộ nhớ đang dùng có vượt trần chưa. Nếu vượt, Redis sẽ quyết định xử lý theo chính sách đã cấu hình thay vì để hệ điều hành can thiệp."

**Ghi chú cho notes:** Khi maxmemory 0 trên 64-bit, Redis không giới hạn — đây là giá trị mặc định. Các lệnh đọc (GET, HGET) vẫn được phục vụ ngay cả khi bộ nhớ vượt trần; chỉ lệnh ghi mới bị từ chối.

**Chuyển slide:** "Vậy khi chạm trần, key biến mất vì lý do gì? Có hai cơ chế khác nhau."

 

## **Slide 2  Phân biệt Expiration và Eviction**

**Phụ đề:** Key biến mất vì hết hạn hay vì bộ nhớ đầy?

**Thời gian:** 0:45–1:30

**Nội dung hiển thị:**

|   | Expiration (Hết hạn) | Eviction (Trục xuất) |
| :---- | :---- | :---- |
| Nguyên nhân | TTL hết → key tự hết hạn | RAM chạm maxmemory → buộc xóa |
| Phạm vi | Chỉ key có đặt TTL | Tùy chính sách: toàn bộ hoặc chỉ key có TTL |
| Trạng thái key | Đã quá hạn sử dụng | Vẫn còn hạn nhưng bị hy sinh |
| Chỉ số giám sát | expired\_keys | evicted\_keys |

 

**Bố cục:** Bảng so sánh hai cột rõ ràng ở giữa slide. Cột trái nhãn "Expiration" với biểu tượng đồng hồ; cột phải nhãn "Eviction" với biểu tượng thanh RAM đầy. Dùng màu khác nhau cho hai cột để phân biệt.

**Lời nói:** "Ở phần trước, chúng ta đã biết TTL giúp key tự hết hạn — đó là Expiration. Nhưng Eviction khác hẳn: key bị Redis chủ động xóa vì RAM đã chạm trần maxmemory, dù key đó có thể chưa hết hạn hoặc thậm chí không có TTL. Nói cách khác, Expiration xảy ra vì thời gian, còn Eviction xảy ra vì dung lượng. Hai chỉ số giám sát cũng khác nhau: expired\_keys đếm key hết hạn, evicted\_keys đếm key bị trục xuất do bộ nhớ đầy. Phân biệt đúng hai cơ chế này rất quan trọng khi vận hành."

**Lưu ý cho người gen:** Không thêm chi tiết về cơ chế lazy expiration hoặc active expiration cycle; giữ bảng so sánh đơn giản. Expiration đã được giới thiệu ở phần TTL trước đó.

**Chuyển slide:** "Khi eviction xảy ra, Redis chọn key nào để xóa? Điều đó phụ thuộc vào chính sách cấu hình."

 

## **Slide 3  Các chính sách loại bỏ dữ liệu**

**Phụ đề:** maxmemory-policy quyết định Redis xóa key nào khi đầy bộ nhớ

**Thời gian:** 1:30–2:15

**Nội dung hiển thị:** Sơ đồ ba nhánh:

·     **noeviction** → Không xóa, từ chối lệnh ghi (lỗi OOM)

·     **allkeys-\*** → Tìm và xóa trên toàn bộ database

·     **volatile-\*** → Chỉ tìm và xóa trong tập key có TTL

Nhấn mạnh: allkeys-lru — lựa chọn chuẩn cho hệ thống cache.

**Bố cục:** Vẽ sơ đồ cây đơn giản. Gốc là "RAM chạm maxmemory", phân thành 3 nhánh. Nhánh allkeys-lru được đánh dấu đặc biệt (viền đỏ Redis hoặc ngôi sao). Mỗi nhánh ghi tóm tắt một dòng. Không liệt kê đầy đủ 8 chính sách trên slide; để trong speaker notes.

**Lời nói:** "Redis có 8 chính sách loại bỏ dữ liệu, chia làm 3 nhóm. noeviction là mặc định: không xóa gì cả, từ chối mọi lệnh ghi mới — phù hợp khi Redis lưu dữ liệu không được phép mất. Nhóm allkeys quét trên toàn bộ key; allkeys-lru chọn key ít được truy cập gần đây nhất để xóa — đây là lựa chọn phổ biến nhất cho hệ thống cache. Nhóm volatile chỉ quét trong tập key có TTL, bảo vệ dữ liệu không có thời hạn. Ví dụ volatile-ttl ưu tiên xóa key sắp hết hạn trước. Lưu ý: nếu dùng volatile-\* mà không có key nào có TTL, Redis sẽ trả lỗi OOM giống noeviction."

**Ghi chú bổ sung cho notes:** Đưa bảng đầy đủ 8 chính sách vào notes:

| Chính sách | Không gian quét | Tiêu chí chọn |
| :---- | :---- | :---- |
| noeviction | Không xóa | Trả lỗi OOM |
| allkeys-lru | Toàn bộ keys | Ít truy cập gần đây nhất |
| allkeys-lfu | Toàn bộ keys | Tần suất truy cập thấp nhất |
| allkeys-random | Toàn bộ keys | Ngẫu nhiên |
| volatile-lru | Keys có TTL | Ít truy cập gần đây nhất |
| volatile-lfu | Keys có TTL | Tần suất thấp nhất |
| volatile-ttl | Keys có TTL | TTL còn lại ngắn nhất |
| volatile-random | Keys có TTL | Ngẫu nhiên |

 

**Chuyển slide:** "Với allkeys-lru, làm sao Redis biết key nào ít được dùng gần đây nhất mà không tốn quá nhiều bộ nhớ?"

 

## **Slide 4  Thuật toán Approximate LRU**

**Phụ đề:** Lấy mẫu ngẫu nhiên thay vì theo dõi chính xác từng key

**Thời gian:** 2:15–3:00

**Nội dung hiển thị:**

·     True LRU: cần danh sách liên kết đôi → tốn 16 bytes/key cho con trỏ, mỗi lệnh GET phải cập nhật vị trí.

·     Approximate LRU của Redis: lưu timestamp 24-bit trong header mỗi key. Khi cần xóa → lấy mẫu 5 key ngẫu nhiên → chọn key có idle time lớn nhất.

**Bố cục:** Chia đôi slide. Bên trái: "True LRU" với hình danh sách liên kết đôi bị gạch chéo (✕) và nhãn "tốn RAM \+ CPU". Bên phải: "Approximate LRU" với hình lấy 5 key mẫu từ bảng băm, mũi tên chỉ vào key có idle time cao nhất, nhãn "tiết kiệm \+ đủ chính xác" (✓). Không chèn mã nguồn C lên slide.

**Lời nói:** "Cách đơn giản nhất để tìm key ít dùng là duy trì một danh sách liên kết đôi: mỗi lần đọc key, nhấc nó lên đầu danh sách. Key ở cuối là cũ nhất. Nhưng cách này tốn thêm ít nhất 16 bytes con trỏ cho mỗi key, và mỗi lệnh GET vốn chỉ đọc lại biến thành thao tác ghi trên bộ nhớ. Redis chọn cách khác gọi là Approximate LRU: mỗi key chỉ lưu một timestamp 24-bit ghi lần truy cập cuối. Khi cần giải phóng bộ nhớ, Redis lấy ngẫu nhiên 5 key — số này cấu hình qua maxmemory-samples — tính khoảng thời gian mỗi key không được dùng, rồi xóa key có thời gian nhàn rỗi lớn nhất. Với 5 mẫu đã gần đúng so với True LRU; tăng lên 10 thì chính xác hơn nhưng tốn thêm khoảng 2–3% CPU."

**Ghi chú cho notes:** Công thức idle time: idle\_time \= server.lruclock \- robj.lru. Eviction Pool chứa tối đa 16 ứng viên, sắp xếp theo idle time giảm dần. Tham chiếu: src/evict.c hàm performEvictions() và evictionPoolPopulate().

**Chuyển slide:** "Lý thuyết đã đủ. Bây giờ kiểm chứng bằng demo trên một instance giới hạn 10 MB."

 

## **Slide 5  Chuẩn bị demo: instance 10 MB với allkeys-lru**

**Phụ đề:** Cấu hình, dữ liệu đối chứng và kịch bản bơm tràn

**Thời gian:** 3:00–3:30

**Thông tin trên slide:**

| Thành phần | Giá trị |
| :---- | :---- |
| Port | 6382 |
| maxmemory | 10mb (10485760 bytes) |
| maxmemory-policy | allkeys-lru |
| Persistence | Tắt (save "", appendonly no) |

 

**Thông điệp:** Tạo Cold Keys (ghi 1 lần, không đọc lại) và Hot Keys (đọc liên tục). Bơm dữ liệu tràn 10 MB → quan sát key nào bị loại.

**Bố cục:** Bên trái đặt bảng thông số cấu hình nhỏ. Bên phải vẽ sơ đồ 3 bước:

1\.   Tạo Cold Keys (cold\_k1, cold\_k2, cold\_k3) — biểu tượng tuyết ❄

2\.   Bơm dữ liệu nền \~8.5 MB rồi tạo Hot Keys (hot\_k1, hot\_k2) và đọc lại — biểu tượng lửa 🔥

3\.   Bơm thêm → tràn 10 MB → Eviction xảy ra — biểu tượng cảnh báo ⚠

Không hiển thị lệnh dài trên slide; giữ sơ đồ trực quan.

**Lời nói:** "Demo dùng một instance Redis riêng ở port 6382, giới hạn 10 MB RAM và chính sách allkeys-lru. Persistence bị tắt hoàn toàn để cách ly khỏi các demo khác. Trước tiên tạo 3 Cold Keys — ghi một lần rồi không truy cập lại, mô phỏng dữ liệu nguội. Sau đó bơm dữ liệu nền cho gần đầy RAM, rồi tạo và đọc lại 2 Hot Keys — mô phỏng dữ liệu nóng đang được dùng. Cuối cùng bơm thêm cho tràn 10 MB. Theo lý thuyết allkeys-lru, Redis sẽ ưu tiên loại Cold Keys vì chúng có idle time lớn nhất, còn Hot Keys vừa được đọc sẽ được giữ lại."

**Tài nguyên:** Ảnh 01-config.png là minh chứng PONG, maxmemory, allkeys-lru và trạng thái sạch. Sơ đồ bước chỉ cần ý tưởng; lệnh cụ thể để trong hướng dẫn vận hành test/test\_03\_eviction.md.

**Chuyển slide:** "Sau đây là quá trình chạy thực tế đã ghi hình."

 

## **Slide 6  Demo: Eviction thực tế trên terminal**

**Phụ đề:** Cold Keys bị loại, Hot Keys được giữ lại

**Thời gian:** 3:30–5:00

**Bố cục:** Đặt video ở giữa với nút phát. Một dòng chú thích: "Minh chứng demo eviction — instance port 6382, maxmemory 10mb, allkeys-lru". Có ảnh 03-lru-result.png làm phương án thay thế khi không phát được video.

### **Dựng đoạn video**

Bảng dưới là kế hoạch chọn footage; các khoảng ghi là thời gian trong clip đích 90 giây. Chọn từ recording gốc, giữ output đủ lâu để đọc và giữ đúng thứ tự lệnh với kết quả.

| Thời gian | Hình cần thấy | Lời nói khi phát |
| :---- | :---- | :---- |
| 0–15 giây | PONG, config get maxmemory → 10485760, config get maxmemory-policy → allkeys-lru, flushall OK, dbsize → 0 | "Instance port 6382 trả lời PONG. Cấu hình giới hạn 10 MB với chính sách allkeys-lru. Database đã được dọn sạch." |
| 15–30 giây | set cold\_k1, set cold\_k2, set cold\_k3 → OK | "Tạo 3 Cold Keys, ghi một lần rồi không đọc lại. Đây là đối tượng cũ nhất theo LRU." |
| 30–45 giây | redis-benchmark \-n 85 \-d 100000 → SET requests/sec | "Bơm 85 key lớn (\~100 KB mỗi key) cho gần đầy 10 MB RAM." |
| 45–55 giây | set hot\_k1, set hot\_k2, get hot\_k1, get hot\_k2 → giá trị trả về | "Tạo và đọc lại 2 Hot Keys. LRU timestamp của chúng vừa được cập nhật." |
| 55–65 giây | redis-benchmark \-n 20 \-d 100000 → SET requests/sec | "Bơm thêm 20 key nữa. Lúc này RAM vượt 10 MB, eviction được kích hoạt." |
| 65–80 giây | info memory → used\_memory\_human: 9.86M, info stats → evicted\_keys: 27 | "RAM giữ ở mức 9.86 MB, không vượt trần. Redis đã trục xuất 27 key." |
| 80–90 giây | exists cold\_k1 cold\_k2 cold\_k3 → (integer) 0, exists hot\_k1 hot\_k2 → (integer) 2 | "Toàn bộ Cold Keys đã bị loại vì ít dùng nhất. Cả 2 Hot Keys đều sống sót vì được đọc liên tục. Đúng với lý thuyết allkeys-lru." |

 

### **Mốc tham khảo trong video gốc**

Tham khảo shot list tại docs/presentation-notes/03-eviction-script.md và kịch bản từng lệnh tại test/test\_03\_eviction.md. Đây là mốc gần đúng để chọn đoạn, không phải clip đã được dựng.

### **Nội dung terminal**

Nếu dựng lại một khung terminal thay ảnh, chỉ chép lệnh và output từ minh chứng. Ví dụ đã có minh chứng:

redis-cli \-p 6382 ping      	→ PONG  
 config get maxmemory         	→ "10485760"  
 config get maxmemory-policy  	→ "allkeys-lru"  
 info memory \| grep used\_memory\_human → used\_memory\_human:9.86M  
 info stats \| grep evicted\_keys   	→ evicted\_keys:27  
 exists cold\_k1 cold\_k2 cold\_k3  	→ (integer) 0  
 exists hot\_k1 hot\_k2             	→ (integer) 2

Không tạo log hoặc sửa kết quả để minh họa.

### **Giữ đúng phạm vi**

Video eviction không cần phần setup môi trường chung hay kiểm tra các port khác. Không đưa kết luận "đã chạy đủ bốn workload" hoặc kết quả crash/persistence từ demo khác.

### **Phương án dự phòng**

Nếu không phát video được, trình bày 3 ảnh minh chứng theo đúng thứ tự:

1\.   01-config.png — cấu hình và trạng thái sạch

2\.   02-eviction-trigger.png — quá trình tạo key và bơm dữ liệu

3\.   03-lru-result.png — kết quả RAM, evicted\_keys và đối chứng cold/hot

Không tăng thời lượng phần này quá 90 giây.

 

## **Slide 7  Kết luận và khuyến nghị production**

**Phụ đề:** Đặt maxmemory đúng mức và chọn policy phù hợp mục đích

**Thời gian:** 5:00–5:30

**Bố cục:** Đặt 3 khuyến nghị ngắn, mỗi khuyến nghị một dòng có biểu tượng:

| \# | Khuyến nghị |
| :---- | :---- |
| 1 | Luôn đặt maxmemory — không để Redis dùng hết RAM máy chủ |
| 2 | Cache → allkeys-lru; dữ liệu quan trọng → noeviction có giám sát |
| 3 | Đặt trần ở 70–80% RAM vật lý (50–60% nếu bật RDB/AOF) |

 

**Lời nói:** "Khi triển khai Redis thực tế, ba điều cần nhớ. Thứ nhất, luôn cấu hình maxmemory — đừng để mặc định không giới hạn vì hệ điều hành sẽ tắt tiến trình khi RAM cạn. Thứ hai, chọn chính sách phù hợp: allkeys-lru cho hệ thống cache là lựa chọn phổ biến nhất, còn noeviction phù hợp khi Redis lưu dữ liệu không được phép mất — nhưng cần có giám sát cảnh báo trước khi bộ nhớ đầy. Thứ ba, không đặt maxmemory bằng 100% RAM vật lý. Cần chừa khoảng 20–30% cho bộ đệm mạng, phân mảnh bộ nhớ và quá trình fork khi lưu đĩa. Khuyến nghị là 70–80% RAM, hoặc 50–60% nếu bật RDB hay AOF. Demo vừa rồi đã cho thấy cơ chế này hoạt động đúng lý thuyết: dữ liệu nguội bị loại, dữ liệu nóng được bảo vệ."

**Ghi chú cho notes:** Nếu traffic có tính lặp lại theo chu kỳ dài (ví dụ batch job đọc quét hàng loạt), cân nhắc allkeys-lfu thay vì allkeys-lru để tránh Cache Pollution. Khi maxmemory-samples tăng từ 5 lên 10, độ chính xác tăng \~99% so với True LRU nhưng CPU tốn thêm 2–3%.

**Chuyển phần:** "Eviction giúp Redis quản lý khi bộ nhớ đầy, nhưng dữ liệu bị loại sẽ mất. Phần tiếp theo — Persistence — sẽ trả lời câu hỏi: làm sao phục hồi dữ liệu sau sự cố."

 

## **B  Câu hỏi dự phòng**

Dùng khi được hỏi, không tạo thêm slide trong thời lượng 5–6 phút.

| Câu hỏi | Trả lời ngắn |
| :---- | :---- |
| Vì sao Redis dùng Approximate LRU thay vì True LRU? | True LRU tốn thêm 16 bytes con trỏ mỗi key và biến mỗi lệnh đọc thành thao tác ghi. Approximate LRU chỉ lưu timestamp 24-bit, lấy mẫu 5 key là đủ gần chính xác. |
| Nếu dùng volatile-\* mà không có key nào có TTL? | Redis không tìm được key nào để xóa, tự động rơi về hành vi noeviction — từ chối lệnh ghi mới, trả lỗi OOM. |
| Eviction có làm block Redis không? | Mặc định có (synchronous). Với Big Key chứa hàng triệu phần tử, việc giải phóng bộ nhớ có thể tốn hàng trăm ms. Bật lazyfree-lazy-eviction yes để Redis chỉ unlink key rồi giao việc giải phóng cho luồng nền. |
| Phân biệt LRU và LFU? | LRU quan tâm lần cuối truy cập (thời gian), LFU quan tâm số lần truy cập (tần suất). LFU chống được Cache Pollution khi batch job quét hàng loạt key chỉ một lần. |
| Tại sao top hiển thị RAM cao hơn maxmemory? | maxmemory chỉ kiểm soát used\_memory. top hiển thị RSS bao gồm cả phân mảnh bộ nhớ, bộ đệm mạng và metadata của jemalloc — luôn lớn hơn used\_memory. |
| Key 20 MB ghi vào Redis maxmemory 10mb thì sao? | Redis sẽ xóa hết key hiện có nhưng vẫn không đủ chỗ (tối đa 10 MB), trả lỗi OOM. Database lúc này trống rỗng mà key mới vẫn không ghi được — đây là bài học không lưu Big Key vượt maxmemory. |
| Replica có tự chạy eviction không? | Không. Replica chỉ nhận lệnh DEL từ Master qua Replication Stream để đảm bảo nhất quán. maxmemory trên Replica phải bằng hoặc lớn hơn Master. |

 

 

## **C  Prompt để tạo slide**

Đưa tài liệu này cùng base slide của nhóm và các ảnh/video đã chọn cho công cụ tạo slide. Có thể dùng nguyên prompt sau:

Tạo phần Eviction của seminar Redis bằng tiếng Việt theo tài liệu đính kèm, gồm đúng 7 slide. Tổng thời lượng 5–6 phút, trong đó slide 6 dành 90 giây cho video demo. Giữ nguyên thứ tự và thông điệp từng mục Slide 1 đến Slide 7\. Dùng mục "Nội dung hiển thị" để viết ngắn trên slide; mục "Bố cục" để dựng sơ đồ; mục "Lời nói" chỉ đưa vào speaker notes. Không đưa câu hỏi dự phòng, prompt hoặc checklist thành slide.

Giữ phong cách của base slide đính kèm. Nếu không có base, dùng 16:9, nền sáng, chữ lớn và màu nhấn đỏ Redis. Mỗi slide một ý chính; giải thích thuật ngữ khi xuất hiện. Sơ đồ chính sách phải phân biệt rõ 3 nhóm (noeviction, allkeys, volatile). Slide Approximate LRU cần đối lập rõ True LRU và Approximate LRU. Không thêm mã nguồn C, công thức phức tạp hoặc giải thích sâu RDB/AOF vào phần eviction.

Chỉ dùng ảnh/log/video thật được cung cấp. Minh chứng demo dùng instance port 6382, maxmemory 10mb, allkeys-lru. Kết quả thực nghiệm: RAM \~9.86 MB, 27 keys bị trục xuất, cold keys EXISTS \= 0, hot keys EXISTS \= 2\. Không lấy kết quả từ demo khác. Nếu thiếu video đã cắt hoặc link phát, đặt placeholder ghi rõ tài nguyên cần chèn; không tạo URL hoặc file như thể đã tồn tại. Nếu xuất HTML, nút bấm phải có cách xem đầy đủ ở bản tĩnh; không tự phát video. Nếu xuất PPTX, giữ chữ và sơ đồ chỉnh sửa được.

 

## **D  Checklist trước khi dùng**

·     ☐ Đủ 7 slide; thời lượng 45 \+ 45 \+ 45 \+ 45 \+ 30 \+ 90 \+ 30 \= 330 giây (\~5.5 phút).

·     ☐ Các thuật ngữ mới (eviction, maxmemory, LRU, idle time, Eviction Pool) có giải thích ngắn ngay lần đầu xuất hiện.

·     ☐ Lời nói đi theo ví dụ cache sản phẩm và tình huống cold/hot key; không đọc bảng thuật ngữ.

·     ☐ Nội dung trên slide ngắn (20–40 từ); speaker notes và phần hỏi đáp không tràn vào nội dung trình chiếu.

·     ☐ Bảng so sánh Expiration vs Eviction rõ ràng, không nhầm lẫn hai cơ chế.

·     ☐ Sơ đồ 3 nhóm chính sách phân biệt được noeviction, allkeys-\*, volatile-\*.

·     ☐ Slide Approximate LRU đối lập rõ ưu/nhược với True LRU; không chèn mã nguồn C.

·     ☐ Ảnh/lệnh/output đúng minh chứng port 6382: PONG, 10485760, allkeys-lru, 9.86M, evicted 27, cold 0, hot 2\.

·     ☐ Bản video hoặc placeholder được ghi rõ trạng thái; ảnh dự phòng đủ 3 ảnh đúng thứ tự.

·     ☐ Video phát được trên máy trình chiếu, chữ đọc được; có bản offline và ảnh dự phòng.

·     ☐ Không thêm đoạn RDB/AOF, Replication hoặc mã nguồn C vào phần eviction.

·     ☐ Không suy diễn kết quả eviction thành kết quả demo khác hoặc kết luận toàn bộ seminar.

 

## **E  Tài liệu đối chiếu**

| Tài liệu | Đường dẫn |
| :---- | :---- |
| Lý thuyết Eviction đầy đủ | docs/theory/03-eviction.md |
| Bộ câu hỏi đáp chuyên sâu | docs/theory/03-eviction-qa.md |
| Kịch bản slide và shot list | docs/presentation-notes/03-eviction-script.md |
| README demo | demos/03-eviction/README.md |
| Script chính (Python) | demos/03-eviction/fill\_memory.py |
| Script kiểm thử tự động | demos/03-eviction/test\_eviction.py |
| Kịch bản gõ từng lệnh CLI | test/test\_03\_eviction.md |
| Runbook vận hành | test/03\_eviction.md |
| Cấu hình Redis | redis/redis-eviction.conf |
| Ảnh minh chứng | docs/screenshots/03-eviction/ |
| Video demo | demos/03-eviction/demo-03-eviction.mp4 |
| Đề tài seminar (yêu cầu gốc) | de\_tai\_seminar.md — Mục 7B, demo 3 |

 

Nguồn khái niệm: [Redis Key eviction](https://redis.io/docs/latest/develop/reference/eviction/); [Memory optimization](https://redis.io/docs/latest/develop/optimization/memory-optimization/); [antirez blog — Redis as LRU cache](http://antirez.com/news/109). Dùng các liên kết nguồn trong tài liệu lý thuyết, đặt nguồn ở notes hoặc tài liệu tham khảo chung của deck.

 

