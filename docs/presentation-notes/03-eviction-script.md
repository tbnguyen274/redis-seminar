# Kịch bản Thuyết trình & Dàn bài Slide: Memory & Eviction (Demo 03)

- **Người trình bày:** Mạnh Tường
- **Chủ đề:** Giới hạn bộ nhớ và Thuật toán Eviction trong Redis
- **Thời lượng:** ~5 phút 30 giây

---

## Phần 1: Dàn bài Slide (Nội dung từng Slide)

### Slide 1: Đặt vấn đề & Giới hạn Bộ nhớ (`maxmemory`)
* **Tiêu đề:** Quản lý Bộ nhớ trong Redis: Chuyện gì xảy ra khi cạn RAM?
* **Nội dung chính:**
  - Redis lưu trữ 100% dữ liệu trên RAM để đạt tốc độ microsecond.
  - RAM là tài nguyên hữu hạn. Nếu không đặt giới hạn, OS OOM Killer sẽ `kill -9` tiến trình Redis khi đầy RAM.
  - Cấu hình: `maxmemory <bytes>` (ví dụ: `10mb`).
  - Kiểm tra trước mỗi lệnh ghi: Nếu `used_memory > maxmemory` $\rightarrow$ Kích hoạt dọn dẹp hoặc từ chối ghi (`OOM command not allowed`).
* **Hình minh họa:** Sơ đồ luồng kiểm tra `used_memory` trước khi thực thi lệnh ghi.

---

### Slide 2: Phân biệt Expiration (TTL) vs Eviction (Trục xuất)
* **Tiêu đề:** Expiration vs Eviction: Đừng nhầm lẫn!
* **Bảng so sánh trực quan:**
  - **Expiration (Hết hạn):** Do thời gian sống của key kết thúc. Key không còn giá trị. Xóa theo cơ chế chủ động/thụ động. Theo dõi qua `expired_keys`.
  - **Eviction (Trục xuất):** Do RAM chạm ngưỡng `maxmemory`. Key **vẫn còn hạn sử dụng** nhưng bị hy sinh để nhường chỗ cho dữ liệu mới. Theo dõi qua `evicted_keys`.
* **Thông điệp:** *"Key bị expire là do key hết thời gian; key bị evict là do máy chủ hết bộ nhớ."*

---

### Slide 3: Các Chính sách Eviction (`maxmemory-policy`)
* **Tiêu đề:** Lựa chọn Chiến lược: 8 Chính sách Eviction
* **Nội dung chính:**
  - **`noeviction` (Mặc định):** Giữ nguyên vẹn dữ liệu, từ chối lệnh ghi mới $\rightarrow$ Dùng cho Database chính, session quan trọng.
  - **`allkeys-lru`:** Trục xuất key ít được truy cập gần đây nhất trên toàn database $\rightarrow$ Chuẩn mực cho hệ thống Caching.
  - **`volatile-ttl`:** Chỉ xóa trong tập key có cài TTL, ưu tiên key sắp hết hạn $\rightarrow$ Bảo vệ dữ liệu tĩnh vĩnh viễn.
  - *Mở rộng:* `allkeys-lfu` (tần suất), `random` (ngẫu nhiên).

---

### Slide 4: Điểm nhấn Kiến trúc: Approximate LRU vs True LRU
* **Tiêu đề:** Bí mật Hiệu năng: Thuật toán Approximate LRU của Redis
* **Nội dung so sánh:**
  - **Vì sao không dùng True LRU?** Danh sách liên kết đôi tốn thêm 16–24 bytes con trỏ/key và gây nghẽn lock trên memory khi chạy lệnh đọc `GET`.
  - **Giải pháp của Redis (Approximate LRU):**
    - Lưu trường `lru` 24-bit trong header mỗi object `robj`.
    - Lấy mẫu ngẫu nhiên $N$ keys (`maxmemory-samples`, mặc định 5).
    - Đưa vào bể ứng viên (Eviction Pool) và xóa key có thời gian nhàn rỗi (idle time) lớn nhất.
  - **Kết luận:** Tiết kiệm RAM vượt trội, độ chính xác xấp xỉ 99% so với True LRU.

---

### Slide 5: Thiết kế Thực nghiệm (Demo 03)
* **Tiêu đề:** Demo 03: Kiểm chứng Giới hạn 10MB và Chính sách `allkeys-lru`
* **Nội dung:**
  - Cổng chạy: `6382`, cấu hình `maxmemory 10mb`, `maxmemory-policy allkeys-lru`.
  - Thiết kế 2 nhóm dữ liệu:
    - **Cold keys:** Ghi lúc đầu, không đọc lại.
    - **Hot keys:** Ghi lúc đầu, đọc liên tục (`GET`).
  - Bơm dữ liệu lớn vượt 10MB để quan sát eviction.

---

### Slide 6: Kết quả Demo & Video Minh họa
* **Tiêu đề:** Kết quả Thực nghiệm & Video Demo
* **Nội dung:**
  - Bộ nhớ giữ vững ở mức 10MB, `evicted_keys` tăng đều đặn.
  - Cold keys bị xóa sạch; Hot keys được giữ lại 100%.
  - Video demo quay sẵn (Light mode, phóng to terminal).

---

## Phần 2: Kịch bản Nói Chi tiết (Speaking Script)

*(Thời gian dự kiến cho phần Lý thuyết: ~2 phút 30 giây)*

> **[Bắt đầu Slide 1]**  
> *"Kính thưa thầy và các bạn, tiếp nối phần Cache-Aside của bạn Thắng, câu hỏi đặt ra là: Nếu lượng truy cập tăng vọt, dữ liệu cache liên tục được ghi vào mà RAM máy chủ có hạn, chuyện gì sẽ xảy ra?  
> Redis là hệ thống hoàn toàn lưu trữ trên RAM. Nếu không giới hạn dung lượng, khi cạn kiệt RAM, tiến trình OOM Killer của hệ điều hành Linux sẽ lập tức kill tiến trình Redis, gây sập dịch vụ.  
> Để ngăn chặn điều này, Redis cung cấp chỉ thị `maxmemory`. Trước mỗi lệnh ghi, Redis sẽ kiểm tra nếu dung lượng vượt ngưỡng, nó sẽ kích hoạt cơ chế dọn dẹp hoặc từ chối ghi."*

> **[Chuyển sang Slide 2]**  
> *"Ở đây, chúng ta cần phân biệt rất rõ ràng hai khái niệm thường bị nhầm lẫn: **Expiration** và **Eviction**.  
> Expiration xảy ra khi một key kết thúc thời gian sống TTL của nó. Dữ liệu này đã lỗi thời và bị xóa để dọn rác.  
> Ngược lại, Eviction xảy ra khi RAM chạm ngưỡng `maxmemory`. Lúc này, ngay cả khi dữ liệu vẫn còn hạn dùng hoặc là dữ liệu vĩnh viễn, Redis vẫn bắt buộc phải 'hy sinh' nó để nhường chỗ cho dữ liệu mới ghi vào."*

> **[Chuyển sang Slide 3]**  
> *"Vậy Redis quyết định hy sinh key nào? Điều đó phụ thuộc vào tham số `maxmemory-policy`.  
> Mặc định, Redis dùng `noeviction` – tức là thà từ chối lệnh ghi và báo lỗi OOM chứ tuyệt đối không tự ý xóa dữ liệu của người dùng, phù hợp khi dùng Redis làm database.  
> Nhưng khi dùng Redis làm Cache, chính sách chuẩn mực nhất là `allkeys-lru` – tự động tìm và xóa các key ít được sử dụng nhất trong thời gian qua. Ngoài ra, nếu hệ thống có cả dữ liệu tĩnh và dữ liệu cache, ta có thể dùng `volatile-ttl` để chỉ xóa các key có TTL sắp hết hạn."*

> **[Chuyển sang Slide 4]**  
> *"Một điểm rất đặc biệt trong kiến trúc của Redis: Redis không dùng thuật toán LRU chính xác (True LRU) bằng danh sách liên kết đôi như trong sách giáo khoa.  
> Lý do là vì linked-list sẽ tốn thêm 16 đến 24 byte con trỏ cho mỗi key, đồng thời mỗi thao tác đọc `GET` lại phải sửa đổi con trỏ bộ nhớ, làm giảm hiệu năng.  
> Thay vào đó, Redis dùng thuật toán **Approximate LRU**. Mỗi object chỉ gắn thêm 24-bit timestamp. Khi cần xóa, Redis lấy mẫu ngẫu nhiên 5 key, đưa vào một Eviction Pool và trục xuất key có thời gian nhàn rỗi lâu nhất. Thực nghiệm cho thấy với 5 mẫu ngẫu nhiên, kết quả đạt độ chính xác gần như tương đương True LRU nhưng tiết kiệm bộ nhớ đáng kể."*

> **[Chuyển sang Slide 5 & 6 - Demo]**  
> *"Để chứng minh cơ chế này trên thực tế, sau đây em xin trình bày Demo 03..."*
