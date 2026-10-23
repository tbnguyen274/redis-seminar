# Bộ 10 Câu hỏi Mở & Câu trả lời Chuyên sâu: Redis Memory & Eviction

Tài liệu này được biên soạn phục vụ buổi vấn đáp seminar và phản biện với Giảng viên / Sinh viên về chủ đề **Quản lý Bộ nhớ và Thuật toán Eviction trong Redis**.

---

### Câu 1: Tại sao Redis không dùng "True LRU" (danh sách liên kết đôi) mà lại dùng "Approximate LRU"? Nếu tăng tham số `maxmemory-samples` từ 5 lên 10 thì được gì và mất gì?
* **Bản chất vấn đề:** Đánh đổi (Trade-off) giữa độ chính xác thuật toán, mức tiêu thụ RAM và chi phí chu kỳ CPU trong kiến trúc đơn luồng.
* **Câu trả lời chuẩn:**
  - True LRU đòi hỏi mỗi phần tử phải được nối vào một Doubly Linked List. Trên hệ điều hành 64-bit, 2 con trỏ `prev` và `next` tốn ít nhất $16$ bytes (hoặc $24$ bytes nếu kèm padding). Với 10 triệu keys, hệ thống tốn thêm ~160MB – 240MB chỉ để lưu con trỏ. Hơn nữa, mỗi lệnh đọc `GET` lại biến thành thao tác ghi trên RAM để nhấc node lên đầu danh sách, gây nghẽn CPU cache và giảm throughput.
  - Approximate LRU giải quyết bằng cách lưu trường `unsigned lru:24` (chỉ tốn 24-bit trong header `robj`). Khi cần xóa, Redis lấy mẫu ngẫu nhiên $N$ key (`maxmemory-samples`, mặc định là 5) và đẩy vào một Eviction Pool (16 phần tử sắp xếp theo idle time) để chọn key cũ nhất.
  - **Khi tăng `maxmemory-samples` từ 5 lên 10:**
    - *Được:* Tăng độ chính xác xấp xỉ lên gần 99% so với True LRU, hạn chế tối đa việc xóa nhầm key vừa được truy cập.
    - *Mất:* Redis phải đọc thêm 5 key ngẫu nhiên từ bảng băm ở mỗi chu kỳ dọn dẹp, tiêu tốn thêm khoảng 2%–3% CPU. Vì Redis xử lý lệnh đơn luồng, điều này có thể làm tăng nhẹ độ trễ (latency spikes) của các lệnh ghi đang chờ.

---

### Câu 2: Giả sử hệ thống cấu hình `maxmemory-policy volatile-lru` hoặc `volatile-ttl`, nhưng người dùng hoàn toàn KHÔNG đặt TTL cho bất kỳ key nào. Chuyện gì sẽ xảy ra khi RAM chạm ngưỡng `maxmemory`?
* **Bản chất vấn đề:** Khả năng xử lý trường hợp ngoại lệ (Edge Case) của các chính sách nhóm `volatile-*`.
* **Câu trả lời chuẩn:**
  - Chính sách nhóm `volatile-*` chỉ tìm kiếm các ứng viên bị trục xuất nằm trong từ điển các key có TTL (`db->expires`).
  - Khi `db->expires` trống rỗng (không có key nào có TTL), Redis không thể tìm thấy bất kỳ key nào thỏa mãn điều kiện để xóa.
  - Lúc này, Redis sẽ **tự động fallback về hành vi của `noeviction`**: Từ chối mọi lệnh ghi mới làm tăng dung lượng bộ nhớ và trả về lỗi:
    `(error) OOM command not allowed when used memory > 'maxmemory'`.
  - Các lệnh đọc (`GET`) hoặc lệnh xóa (`DEL`) vẫn hoạt động bình thường.

---

### Câu 3: Quá trình Eviction diễn ra đồng bộ hay bất đồng bộ? Khi phải xóa hàng loạt key dung lượng lớn (Big Keys), nó có làm "đơ" (block) tiến trình chính của Redis không?
* **Bản chất vấn đề:** Ảnh hưởng của Eviction đến độ trễ hệ thống (Latency & Single-threaded event loop) và cơ chế Lazy Freeing.
* **Câu trả lời chuẩn:**
  - **Mặc định (Synchronous):** Quá trình kiểm tra và giải phóng bộ nhớ diễn ra **đồng bộ** ngay trong luồng chính (Main Thread) tại thời điểm nhận lệnh ghi mới trước khi lệnh đó được thực thi (trong hàm `performEvictions()` của `src/evict.c`).
  - Nếu key được chọn để xóa là một **Big Key** (ví dụ: Hash hoặc List chứa 1 triệu phần tử), việc giải phóng hàng triệu con trỏ bộ nhớ (hàm `free()` của C) có thể tốn từ hàng chục đến hàng trăm mili-giây, làm block toàn bộ tiến trình Redis, khiến các client khác bị timeout.
  - **Giải pháp:** Từ Redis 4.0 trở đi, Redis bổ sung cơ chế **Lazy Freeing**. Bằng cách bật cấu hình:
    ```text
    lazyfree-lazy-eviction yes
    ```
    Khi eviction xảy ra, Redis chỉ unlink key ra khỏi từ điển (thao tác $O(1)$) và đẩy việc giải phóng vùng nhớ thực tế cho một luồng nền (Background I/O Thread) xử lý dạng `bioCreateLazyFreeJob()`, loại bỏ hoàn toàn hiện tượng block server.

---

### Câu 4: Phân biệt sự khác nhau giữa LRU (Least Recently Used) và LFU (Least Frequently Used)? Khi nào nên chuyển từ LRU sang LFU?
* **Bản chất vấn đề:** Hiểu sâu về ngữ cảnh sử dụng (Use Cases) của các thuật toán Cache Replacement.
* **Câu trả lời chuẩn:**
  - **LRU (Dựa trên thời gian):** Quan tâm đến **lần cuối cùng** key được truy cập cách đây bao lâu.
  - **LFU (Dựa trên tần suất):** Quan tâm đến **số lần** key được truy cập trong một khoảng thời gian. Redis hiện thực LFU bằng thuật toán Morris Counter (8-bit) kết hợp với cơ chế suy giảm tần suất theo thời gian (decay interval).
  - **Trường hợp LRU thất bại và nên chuyển sang LFU:**
    - *Vấn đề quét hàng loạt (Cache Pollution / Batch Scanning):* Giả sử có một tiến trình batch job chạy lúc 2h sáng đọc qua toàn bộ 1 triệu bản ghi cũ (mỗi bản ghi chỉ đọc đúng 1 lần). Với LRU, toàn bộ dữ liệu "nóng" thực sự của người dùng ban ngày sẽ bị coi là cũ hơn và bị xóa sạch để nhường chỗ cho dữ liệu rác vừa quét.
    - Với LFU, do dữ liệu quét chỉ có tần suất truy cập là 1, chúng sẽ bị trục xuất ngay lập tức, trong khi các Hot Keys có tần suất truy cập hàng nghìn lần vẫn được bảo vệ nguyên vẹn.

---

### Câu 5: Tại sao khi cấu hình `maxmemory 10mb`, nhưng kiểm tra lệnh `top` hoặc `htop` trên Linux lại thấy tiến trình Redis chiếm 14MB – 16MB RAM?
* **Bản chất vấn đề:** Phân biệt giữa `used_memory` (Redis tính) và `RSS (Resident Set Size)` (Hệ điều hành cấp).
* **Câu trả lời chuẩn:**
  - Tham số `maxmemory` của Redis chỉ kiểm soát chỉ số **`used_memory`**, tức là lượng RAM thuần mà Redis dùng để lưu trữ dữ liệu (tính qua hàm `zmalloc_used_memory()`).
  - Lệnh `top`/`htop` hiển thị chỉ số **`RSS (Resident Set Size)`** – tổng lượng RAM vật lý mà Linux đã cấp phát cho tiến trình. RSS luôn lớn hơn `used_memory` do 3 thành phần:
    1. **Memory Fragmentation (Phân mảnh bộ nhớ):** Trình cấp phát jemalloc giữ lại các trang nhớ (pages) đã giải phóng để tái sử dụng mà không trả ngay cho OS.
    2. **Bộ nhớ dùng chung và buffers:** Bộ đệm kết nối client (`client output buffers`), bộ đệm nhân rộng replication backlog, mã nhị phân của tiến trình redis-server.
    3. **Metadata của allocator:** Các bảng quản lý bộ nhớ nội bộ của jemalloc.
  - Do đó, cần dựa vào `INFO memory` để xem cả hai chỉ số `used_memory` và `used_memory_rss`.

---

### Câu 6: Hệ số `mem_fragmentation_ratio` nhỏ hơn 1.0 có ý nghĩa gì? Tác hại và cách xử lý?
* **Bản chất vấn đề:** Hiện tượng bộ nhớ ảo (Swap Space) và suy giảm hiệu năng IO.
* **Câu trả lời chuẩn:**
  - Công thức: $\text{mem\_fragmentation\_ratio} = \frac{\text{used\_memory\_rss}}{\text{used\_memory}}$.
  - Khi tỉ số này $< 1.0$, điều đó có nghĩa là lượng RAM vật lý thực tế được cấp (`RSS`) nhỏ hơn lượng RAM mà Redis nghĩ nó đang sử dụng (`used_memory`).
  - **Nguyên nhân:** Máy chủ Linux đã bị cạn kiệt RAM vật lý, buộc hệ điều hành phải chuyển một phần bộ nhớ của Redis ra ổ cứng thông qua cơ chế **Swap (Virtual Memory)**.
  - **Tác hại:** Redis là In-Memory Store với thời gian truy cập RAM ~100 nano-giây. Khi bị swap ra đĩa cứng (ngay cả SSD NVMe), độ trễ sẽ tăng lên từ vài mili-giây đến hàng chục mili-giây (chậm hơn từ 10.000 đến 100.000 lần), gây nghẽn toàn bộ hệ thống.
  - **Cách xử lý:** Ngay lập tức tắt Swap cho tiến trình Redis, hạ thấp `maxmemory` hoặc nâng cấp thêm RAM cho máy chủ.

---

### Câu 7: Trong mô hình nhân rộng Master - Replica, node Replica có tự động chạy thuật toán Eviction khi RAM đầy không?
* **Bản chất vấn đề:** Tính nhất quán dữ liệu (Data Consistency) giữa Master và Replica.
* **Câu trả lời chuẩn:**
  - **Không.** Node Replica **hoàn toàn KHÔNG tự ý thực hiện Eviction**.
  - **Lý do:** Để đảm bảo tính nhất quán dữ liệu tuyệt đối giữa Master và Replica (bản sao phải giống hệt bản chính).
  - **Cơ chế hoạt động:**
    - Khi Master đạt ngưỡng `maxmemory` và thực hiện evict một key (ví dụ `key_A`), Master sẽ tổng hợp một lệnh `DEL key_A` vào luồng nhân rộng (Replication Stream) và gửi tới tất cả các Replica.
    - Các Replica chỉ đơn thuần nhận lệnh `DEL` đó từ Master và thực thi xóa.
    - *Lưu ý quan trọng:* Nếu cấu hình `maxmemory` trên Replica nhỏ hơn trên Master, Replica có thể bị cạn RAM mà không thể tự evict, dẫn đến nguy cơ Replica bị treo hoặc crash. Vì vậy, `maxmemory` trên Replica luôn phải bằng hoặc lớn hơn Master.

---

### Câu 8: Nếu trong hệ thống có một lệnh ghi key dung lượng 20MB vào Redis đang có `maxmemory 10mb`, Redis sẽ xử lý như thế nào?
* **Bản chất vấn đề:** Cơ chế dọn dẹp theo vòng lặp và điều kiện dừng của hàm `performEvictions()`.
* **Câu trả lời chuẩn:**
  - Khi nhận lệnh ghi (ví dụ `SET big_key <payload 20MB>`), Redis kiểm tra thấy cần thêm 20MB RAM để chứa key này.
  - Redis bước vào vòng lặp Eviction: Liên tục tìm và xóa các key cũ theo chính sách `maxmemory-policy`.
  - Kể cả khi Redis đã xóa **toàn bộ 100% key hiện có** trong database (bộ nhớ về mức 0MB), dung lượng RAM trống tối đa cũng chỉ là 10MB, vẫn không đủ để chứa key 20MB mới.
  - Khi nhận thấy không còn key nào để xóa mà bộ nhớ vẫn vượt quá `maxmemory`, Redis lập tức dừng vòng lặp và trả về lỗi:
    `(error) OOM command not allowed when used memory > 'maxmemory'`.
  - Database lúc này bị rơi vào tình trạng trống rỗng (các key cũ đã bị xóa sạch trong vô vọng) mà key mới vẫn không ghi được. Đây là bài học lớn: **Tuyệt đối không lưu trữ Big Keys vượt quá `maxmemory` trong Redis**.

---

### Câu 9: Khi hệ thống đang chạy lệnh lưu dữ liệu nền RDB (`bgsave`) hoặc ghi lại AOF (`bgrewriteaof`), cơ chế Copy-on-Write (CoW) của Linux tương tác thế nào với `maxmemory`?
* **Bản chất vấn đề:** Tương tác giữa cơ chế cấp phát bộ nhớ của OS Linux (`fork()`, Copy-on-Write) và giới hạn ứng dụng.
* **Câu trả lời chuẩn:**
  - Khi Redis thực hiện `bgsave`, tiến trình chính sẽ gọi hàm hệ thống `fork()` để tạo ra một tiến trình con (Child Process). Nhờ cơ chế **Copy-on-Write (CoW)** của Linux kernel, ban đầu tiến trình cha và con chia sẻ chung các trang RAM vật lý.
  - Tuy nhiên, nếu trong lúc tiến trình con đang ghi đĩa, hệ thống có nhiều lệnh ghi mới vào tiến trình cha, Linux buộc phải nhân bản (copy) các trang RAM bị sửa đổi sang vùng nhớ mới.
  - Lúc này, tổng lượng RAM tiêu thụ trên máy chủ có thể tăng lên gấp đôi trong trường hợp xấu nhất (Worst-case).
  - Mặc dù `maxmemory` chỉ tính trên tiến trình cha, nhưng **tổng RAM của máy chủ** có thể bị cạn kiệt, dẫn đến việc OS kích hoạt OOM Killer để tiêu diệt tiến trình cha hoặc con. Vì vậy, khuyến nghị thực tế là chỉ đặt `maxmemory` ở mức **50% – 70% RAM máy chủ** nếu có bật Persistence RDB/AOF.

---

### Câu 10: Quy tắc thực tế khi cấu hình `maxmemory` cho một hệ thống Production là gì?
* **Bản chất vấn đề:** Kiến thức vận hành hệ thống thực tế (DevOps / System Administration).
* **Câu trả lời chuẩn:**
  - **Không bao giờ đặt `maxmemory` bằng 100% RAM vật lý:**
    - Cần dành **20% - 30% RAM** cho hệ điều hành, các tiến trình nền và hiện tượng phân mảnh bộ nhớ jemalloc.
    - Cần dành RAM đệm cho quá trình Copy-On-Write khi chạy RDB snapshot hoặc AOF rewrite.
  - **Quy tắc vàng phân bổ RAM:**
    - *Nếu Redis KHÔNG bật persistence (chỉ thuần làm Cache):* Đặt `maxmemory` bằng **75% – 80% RAM vật lý**.
    - *Nếu Redis CÓ bật RDB/AOF:* Đặt `maxmemory` bằng **50% – 60% RAM vật lý** để đảm bảo quá trình `fork()` chạy an toàn tuyệt đối ngay cả khi traffic ghi tăng đột biến.
  - **Luôn kích hoạt giám sát (Monitoring & Alerts):** Cài đặt cảnh báo khi chỉ số `used_memory / maxmemory > 85%` và khi chỉ số `evicted_keys` tăng bất thường theo thời gian (dấu hiệu cho thấy kích thước cache đang bị thiếu hụt so với nhu cầu thực tế).
