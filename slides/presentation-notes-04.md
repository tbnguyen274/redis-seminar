# Nội dung và thiết kế slide: Kiến trúc Redis và Persistence

**Thời lượng dự kiến:** 9 phút 10 giây, đã gồm video demo khoảng 2 phút 30 giây.  
**Ngôn ngữ:** tiếng Việt, giữ thuật ngữ tiếng Anh khi cần: event loop, I/O multiplexing, snapshot, copy-on-write, page cache, fsync, rewrite.  
**Người trình bày:** điền tên thành viên phụ trách khi chốt phân công.  
**Vị trí:** sau phần Memory and Eviction, trước trang cảm ơn và Q&A.

**Quy ước đánh số:** `04` là mã tài liệu lý thuyết và demo persistence. Trong `slides_redis.html`, Kiến trúc Redis và Persistence là **mục 05**, dùng `data-section="5"` và giữ anchor `#architecture`. Các số Slide 1–8 dưới đây là thứ tự nội bộ của phần này, không phải số trang toàn bộ seminar.

Bản này mô tả cách dựng slide, tương tự [bản Data Structures và TTL](presentation-notes-01.md). Sáu slide lý thuyết giữ nội dung dựa trên [lý thuyết phần 04](docs/theory/04-redis_architecture_persistence.md), [đề cương](docs/presentation-notes/redis-architecture-persistence-slides.md) và [kịch bản nói](docs/presentation-notes/redis-architecture-persistence-talk.md). Hai slide demo dùng **log terminal mới do người trình bày cung cấp**, được trích lại ở phần C của tài liệu này.

**Ưu tiên dữ liệu:** các tài liệu cũ dùng video 60 giây và bộ tracing 130 key. Bản thiết kế này thay bằng video khoảng 2:30 và **hai run riêng, mỗi run đều 2.000 baseline + 1.000 delta**, đúng log mới. Ở run tracing mới, delay 0,2 giây là **Confirmed**, không phải Not confirmed. Không lấy timing hoặc kết quả tracing cũ từ report để điền vào video mới.

---

## A. Hướng dẫn chung cho người dựng slide

### Hình thức

- Khung **16:9**, nền trắng ngà như slide hiện tại. Chữ chính đen than, chữ phụ xanh than đậm (`#414b5a`) để dễ đọc khi chiếu; tránh xám nhạt. Giữ bìa, mục lục và các phần khác của seminar.
- Mỗi slide có **một tiêu đề lớn, một phụ đề ngắn**. Phần giải thích dài đưa vào speaker notes, mở bằng phím **N**.
- Dùng **sơ đồ có nhãn, timeline, biểu đồ và bảng ngắn**. Không cần ảnh chụp terminal hoặc ảnh minh họa database. Biểu diễn trực quan phải dễ chỉ tay và giải thích khi thuyết trình.
- Không dùng nền tối toàn trang, chữ gradient, nhiều badge hoặc thẻ trang trí. Video demo có thể giữ giao diện terminal gốc.
- Thống nhất màu và luôn có nhãn chữ để phân biệt:

| Thành phần | Màu nhấn | Cách dùng |
|---|---|---|
| Main thread, event loop | Xanh dương | Đường thực thi lệnh, hàng chờ |
| Dataset RAM, OS page cache | Amber | Luôn ghi rõ RAM thuộc Redis hay hệ điều hành |
| RDB | Teal | Checkpoint, snapshot và nhánh kết quả RDB |
| AOF | Tím | Base, incremental, manifest và nhánh kết quả AOF |
| Crash, giới hạn kết luận | Đỏ | Đánh dấu đúng phạm vi sự cố, không phủ đỏ cả sơ đồ |

Gợi ý ở canvas 1280 × 720: tiêu đề 38–42 px, phụ đề 19–22 px, nhãn sơ đồ 20–24 px, bảng 18–22 px. Nếu chật, giảm chữ hoặc chuyển chi tiết sang notes trước khi thu nhỏ font.

### Cấu trúc nội dung và tương tác

**8 slide nội dung, không tính trang tiêu đề mục đã có trong baseline.** Sáu slide đầu giải thích lý thuyết, sau đó một slide video và một slide phân tích kết quả. Không chèn một lượt live demo khác.

- Thẻ **click-to-reveal** dùng cho giải thích bổ sung, không giấu các ý bắt buộc phải trình bày.
- Các nút chỉ điều khiển đúng đối tượng: bước sơ đồ, trước/sau, chọn trial hoặc phát video. Bấm nút không được làm chuyển slide.
- Sơ đồ minh họa không được mang hình thức số đo thật. Không thêm thời gian, tốc độ hoặc output chưa được ghi nhận.
- Log được chọn lọc thành nhãn, biểu đồ hoặc bảng có thể sửa. Không chép toàn bộ INFO persistence lên màn hình.
- Các slide 1–6 không cần terminal bên cạnh. Port, baseline/delta và lệnh chạy chỉ xuất hiện khi giới thiệu demo hoặc trong notes.

### Thành phần trực quan cần dựng

| Thành phần | Cách thể hiện | Dùng ở |
|---|---|---|
| Xử lý lệnh và hàng chờ | Sơ đồ request/response và dải công việc | Slide 1–2 |
| Snapshot và CoW | Timeline, hai trạng thái trang RAM | Slide 3 |
| AOF và đường ghi | Sơ đồ manifest/base/incremental; RAM, page cache, storage | Slide 4–5 |
| Lựa chọn persistence | Bảng so sánh ngắn | Slide 6 |
| Quy trình demo | Timeline hai nhánh, bước trước/sau checkpoint | Slide 7 |
| Video khoảng 2:30 | Placeholder, link Drive cập nhật sau | Slide 7 |
| Kết quả phục hồi | Biểu đồ thanh cùng thang đo 0–3.000 key | Slide 8 |
| Fsync quan sát được | Bảng ba trial của run có tracing | Slide 8 |

Các sơ đồ/biểu đồ dựng bằng HTML/SVG có thể chỉnh sửa, không cần chuẩn bị file ảnh. Video để placeholder rõ ràng, không tạo URL Drive giả. Nhãn “Minh họa cơ chế” dùng cho sơ đồ lý thuyết; nhãn “Kết quả từ log demo” dùng cho biểu đồ số liệu. Video local là tài nguyên riêng nếu chưa nhúng vào HTML.

### Phân bổ thời gian

| Slide | Nội dung | Thời lượng | Mốc |
|---|---|---:|---|
| 1 | Kiến trúc xử lý lệnh | 0:55 | 0:00–0:55 |
| 2 | Hiệu năng và giới hạn blocking | 0:40 | 0:55–1:35 |
| 3 | RDB, snapshot và copy-on-write | 0:55 | 1:35–2:30 |
| 4 | AOF, khôi phục và rewrite | 0:50 | 2:30–3:20 |
| 5 | write, fsync và độ bền dữ liệu | 1:00 | 3:20–4:20 |
| 6 | So sánh và lựa chọn persistence | 0:50 | 4:20–5:10 |
| 7 | Giới thiệu 15 giây + video khoảng 2:30 | 2:45 | 5:10–7:55 |
| 8 | Kết quả và lý giải | 1:15 | 7:55–9:10 |

**Tổng dự kiến:** 5:10 lý thuyết + 0:15 giới thiệu + 2:30 video + 1:15 phân tích = **9:10**. Vì video dài khoảng 2:30, thời gian thực tế có thể lệch vài giây. Các thẻ mở rộng và Q&A là nội dung tùy chọn ngoài khung chính.

---

## Slide 1: Redis xử lý nhiều client như thế nào?

**Phụ đề:** Nhiều kết nối cùng tồn tại; phần lớn logic lệnh dữ liệu được xử lý tuần tự.

**Bố cục:** sơ đồ chiếm phần lớn slide. Bên trái là ba client; giữa là đường xử lý request; bên phải là dataset trong RAM. Một nhánh nhỏ phía dưới tách các tác vụ nền khỏi main execution path.

**Sơ đồ chính:**

```text
Client A ─┐
Client B ─┼─ TCP sockets ─ I/O multiplexing ─ Event loop
Client C ─┘                                      │
                                                ▼
                                        Thực thi lệnh
                                                │
                                                ▼
                                          Dataset RAM

Phản hồi: từ đường xử lý Redis trở lại client tương ứng

Tác vụ nền, tách khỏi đường chính:
I/O threads (tùy cấu hình) · RDB child · AOF rewrite child
```

Khi dựng, vẽ rõ chiều request và chiều response; không để sơ đồ kết thúc ở RAM mà thiếu phản hồi cho client. Các khối “Event loop” và “Thực thi lệnh” nằm trong vùng main thread. Thread/process nền là nhánh riêng, không phải worker thực thi mọi lệnh song song.

**Chữ trên slide:**

- Dataset đang hoạt động chủ yếu trong **RAM**.
- **I/O multiplexing** báo socket sẵn sàng.
- **Event loop** điều phối; phần lớn logic lệnh chạy tuần tự.

**Tương tác:** nút “Theo một request” lần lượt nhấn sáng socket sẵn sàng, event loop, thực thi và phản hồi. Không gắn số millisecond vì đây là sơ đồ giải thích.

**Thẻ bấm mở: “Atomic có nghĩa là gì?”**

Một lệnh dữ liệu thông thường không bị lệnh khác chen vào giữa quá trình thực thi. Chuỗi `GET → sửa ở ứng dụng → SET` không tự động nguyên tử; một client khác có thể cập nhật ở giữa.

**Thẻ bấm mở: “Redis có thread/process khác không?”**

Có. I/O threads phụ thuộc phiên bản/cấu hình; snapshot và rewrite có thể dùng background child. “Mostly single-threaded” mô tả đường thực thi lệnh chủ đạo, không khẳng định toàn bộ Redis chỉ có một thread.

**Lời nói — 0:55:**

> Phần này giải thích cách Redis phục vụ nhiều client và cách dữ liệu tồn tại qua một lần khởi động lại. Dataset đang hoạt động chủ yếu nằm trong RAM, nên những lệnh thông thường thao tác trực tiếp trên dữ liệu trong bộ nhớ.
>
> Redis dùng I/O multiplexing để theo dõi nhiều socket. Khi hệ điều hành báo socket sẵn sàng, event loop điều phối việc nhận request, thực thi và gửi phản hồi. Nếu một client chưa gửi dữ liệu, Redis có thể phục vụ client khác thay vì đứng chờ.
>
> Phần lớn logic lệnh dữ liệu chạy tuần tự trên main thread. Redis vẫn có thread hoặc process nền cho một số tác vụ. Một lệnh dữ liệu thông thường có tính atomic đối với lệnh khác; chuỗi GET rồi SET của ứng dụng thì không tự trở thành một giao dịch nguyên tử.

**Nguồn trong notes:** lý thuyết mục 1–3; kịch bản nói slide 1.

---

## Slide 2: Vì sao Redis đơn luồng (Single-threaded) vẫn đạt hiệu năng cao?

**Phụ đề:** RAM, thao tác gọn, I/O multiplexing và ít tranh chấp lock giúp đường thực thi tuần tự hoạt động hiệu quả.

**Bố cục:** hai cột. Trái khoảng 40% cho nguồn hiệu năng; phải khoảng 60% cho hàng chờ lệnh. Không dùng bảng liệt kê quá nhiều command.

**Cột trái: bốn yếu tố phối hợp**

| Yếu tố | Ý nghĩa |
|---|---|
| RAM | Dữ liệu phục vụ chủ yếu nằm trong bộ nhớ |
| Cấu trúc phù hợp | Thao tác đúng ngay trên cấu trúc dữ liệu |
| Lệnh nhỏ | Nhiều thao tác có độ phức tạp thấp |
| Ít tranh chấp lock | Đường thực thi lệnh chủ đạo giảm chi phí đồng bộ dữ liệu dùng chung |

**Cột phải: sơ đồ hàng chờ**

```text
Main execution path:
[ GET ngắn ] [ KEYS trên keyspace lớn ............ ] [ GET ] [ INCR ]
                    đang giữ đường xử lý               phải chờ
```

Chú thích trên slide: **“Lệnh phía sau chỉ được thực thi khi lệnh trước hoàn tất.”** Chiều rộng các khối chỉ minh họa công việc ngắn/nặng, không phải số mili giây đã đo; phần giải thích này để trong speaker notes.

**Hai dòng ở chân slide:**

- `SCAN`: chia công việc duyệt thành nhiều lượt.
- `SLOWLOG`: hỗ trợ tìm lệnh thực thi lâu tại server.

**Tương tác:** bấm khối `KEYS` để làm nổi các lệnh đang xếp sau. Không cần tự chạy hiệu ứng lặp liên tục.

**Thẻ bấm mở: “SCAN có thay thế hoàn toàn KEYS không?”**

`SCAN` chia nhỏ công việc mỗi lần gọi, nhưng không tạo snapshot nhất quán. Có thể gặp phần tử trùng khi duyệt; `COUNT` là hint, không phải số phần tử chắc chắn trả về.

**Thẻ bấm mở: “SLOWLOG có đo cả mạng không?”**

Không. Nó chủ yếu đo thời gian thực thi lệnh tại server. Latency người dùng thấy còn có network RTT, hàng đợi và kích thước phản hồi.

**Lời nói — 0:40:**

> Redis nhanh nhờ kết hợp RAM, cấu trúc dữ liệu phù hợp và nhiều thao tác nhỏ. Đường thực thi tuần tự giảm tranh chấp lock và overhead đồng bộ dữ liệu dùng chung. I/O multiplexing và event loop giúp quản lý nhiều kết nối mà không phải chờ riêng từng socket. Độ trễ client thấy vẫn còn gồm mạng, hàng đợi và lượng dữ liệu trả về.
>
> Vì thực thi lệnh chủ yếu tuần tự, một KEYS quét tập lớn hoặc Lua chạy lâu có thể giữ main thread, khiến client khác phải chờ. Có thể dùng SCAN để chia lượt duyệt và SLOWLOG để tìm lệnh chạy lâu. SCAN không tạo snapshot nhất quán.

**Chuyển ý:** “RAM phục vụ trạng thái đang chạy; persistence quyết định ta dựng lại được trạng thái nào sau sự cố.”

**Nguồn trong notes:** lý thuyết mục 4–5; kịch bản nói slide 2.

---

## Slide 3: RDB: snapshot giữ trạng thái ở mốc nào?

**Phụ đề:** Snapshot phản ánh dataset tại mốc fork, không phải mọi thay đổi đến lúc ghi file xong.

**Bố cục:** nửa trên là timeline; nửa dưới là sơ đồ Copy-on-Write trước/sau. Dùng màu teal cho snapshot, amber cho trang RAM.

**Timeline:**

```text
Mốc fork          Parent tiếp tục ghi       Child ghi xong       Crash
    │                       │                      │                │
    ●───────────────────────┼──────────────────────●────────────────●
    └── Dataset của snapshot ──────────────────────┘

Khôi phục chỉ từ snapshot này: trạng thái tại mốc fork.
```

Không đưa port hoặc bộ 2.000/1.000 key của demo vào slide này. Ghi rõ giả định **“Chưa có snapshot mới hơn; không khôi phục bằng AOF”** dưới timeline.

**Sơ đồ CoW:**

```text
Trước khi sửa:                  Sau khi parent sửa:
Parent ─┐                       Parent ── Page A' (bản mới)
        ├── Page A
Child ──┘                       Child  ── Page A  (góc nhìn cũ)
```

**Ba nhãn chính:**

- `BGSAVE`: child ghi file, parent tiếp tục phục vụ.
- **Copy-on-Write** giữ góc nhìn snapshot, có thể tăng RAM.
- Các thay đổi sau checkpoint có thể mất khi chỉ khôi phục bằng RDB.

**Tương tác:** nút “Parent sửa một trang” chuyển sơ đồ chia sẻ sang hai trang. Không vẽ fork là sao chép ngay toàn bộ dataset, cũng không gắn nhãn “RAM luôn tăng gấp đôi”.

**Thẻ bấm mở: “Ghi nền có hoàn toàn miễn phí không?”**

Không. Fork có thể gây pause ngắn; CoW tăng RAM khi nhiều trang bị sửa; child cạnh tranh CPU và I/O. Parent không phải dừng trong toàn bộ thời gian child ghi snapshot, nhưng latency vẫn có thể chịu ảnh hưởng.

**Thẻ bấm mở: “BGSAVE trả lời là snapshot đã xong?”**

Phản hồi bắt đầu ghi nền chỉ xác nhận đã nhận yêu cầu. Cần chờ kết thúc và kiểm tra trạng thái lưu thành công. Chi tiết lệnh để ở notes, không chép cả `INFO persistence` lên slide.

**Lời nói — 0:55:**

> RDB lưu ảnh chụp dataset tại một mốc thời gian. Khi dùng BGSAVE, Redis fork một process con. Process con ghi snapshot, còn process cha tiếp tục xử lý yêu cầu.
>
> Ban đầu hai process chia sẻ các trang nhớ. Nếu cha sửa một trang đang chia sẻ, copy-on-write tạo bản sao để con vẫn thấy trạng thái cũ. Vì thế snapshot phản ánh mốc fork, không phải mọi thay đổi đến lúc ghi file hoàn tất.
>
> Cách này tạo file thuận tiện cho backup theo mốc, nhưng fork có thể gây pause ngắn, copy-on-write làm tăng RAM và ghi snapshot vẫn tốn I/O. Nếu chỉ khôi phục bằng RDB mà chưa có snapshot mới, các thay đổi sau checkpoint có thể mất.

**Nguồn trong notes:** lý thuyết mục 7; kịch bản nói slide 3.

---

## Slide 4: AOF: dựng lại dữ liệu từ trạng thái nền và thay đổi

**Phụ đề:** Redis 7+ dùng multi-part AOF: base, incremental và manifest.

**Bố cục:** sơ đồ nạp dữ liệu chiếm 2/3 trên; một ví dụ rewrite ngắn ở dưới. Dùng màu tím, phân biệt từng thành phần bằng nhãn thay vì ba sắc độ khó nhận ra.

**Sơ đồ khôi phục:**

```text
                    Manifest
             xác định bộ file/thứ tự nạp
                       │
          ┌────────────┴─────────────┐
          ▼                          ▼
    Base state                 Incremental records
 có thể là RDB                thay đổi sau mốc nền
          └──── nạp base, rồi replay ────┘
                       │
                       ▼
                  Dataset RAM
```

Khi dựng, đánh số **1. Nạp base**, **2. Replay incremental** để tránh hiểu rằng hai nguồn độc lập được nạp theo thứ tự tùy ý.

**Chữ trên slide:**

| Thành phần | Vai trò |
|---|---|
| Base | Trạng thái nền, có thể dùng định dạng RDB |
| Incremental | Những thay đổi tiếp theo |
| Manifest | Bộ file hợp lệ và thứ tự nạp |

**Ví dụ rewrite:**

```text
counter: 10 → 20 → 40
                 │ rewrite
                 ▼
Biểu diễn gọn hơn, tái tạo trạng thái cuối counter = 40
```

Ví dụ chỉ minh họa trạng thái tương đương, không cam kết base mới chứa đúng một dòng `SET counter 40`. Không vẽ rewrite là xóa tùy tiện các dòng trong file incremental đang ghi.

**Tương tác:** nút “Khôi phục” nhấn sáng base, rồi incremental, cuối cùng RAM. Nút “Rewrite” chuyển phần ví dụ sang biểu diễn cuối gọn hơn.

**Thẻ bấm mở: “Base định dạng RDB có phải RDB-only không?”**

Không. File base RDB thuộc bộ AOF; nó khác `dump.rdb` của instance RDB độc lập. Sự có mặt của `.base.rdb` không chứng minh snapshot RDB độc lập đang bật.

**Thẻ bấm mở: “Backup AOF lấy một file là đủ?”**

Cần giữ bộ base, incremental và manifest nhất quán. Parent vẫn có thể nhận write khi rewrite; rewrite vẫn tiêu tốn tài nguyên.

**Lời nói — 0:50:**

> AOF ghi các thay đổi cần thiết để tái tạo trạng thái. Trong multi-part AOF, base chứa trạng thái nền, incremental chứa các thay đổi tiếp theo, còn manifest xác định bộ file cần nạp và thứ tự của chúng.
>
> Khi khởi động, Redis nạp base rồi replay incremental để dựng lại dataset trong RAM. Base có thể dùng định dạng RDB, nhưng file đó thuộc bộ AOF, khác với snapshot RDB độc lập.
>
> Nếu một key được cập nhật nhiều lần, khôi phục trạng thái cuối không nhất thiết cần toàn bộ lịch sử trung gian. AOF rewrite tạo biểu diễn gọn hơn, trong khi Redis tiếp tục nhận ghi vào incremental mới. Rewrite vẫn có chi phí fork và I/O. Khi backup phải giữ bộ file và manifest nhất quán.

**Nguồn trong notes:** lý thuyết mục 8.1, 8.4–8.5; kịch bản nói slide 4.

---

## Slide 5: write khác fsync như thế nào?

**Phụ đề:** Đọc lại được dữ liệu và xác nhận đồng bộ file là hai quan sát khác nhau.

**Bố cục:** nửa trên là sơ đồ các tầng; nửa dưới là bảng ba chính sách. Đây là slide cần rõ nhất, không chèn ảnh terminal hoặc thêm bảng số đo.

**Sơ đồ:**

```text
┌──── Redis process ────┐       ┌──── Hệ điều hành ────┐
│ Dataset / AOF buffer │ write │ OS page cache (RAM)  │
│                      ├──────►│                     │
└──────────────────────┘       └──────────┬──────────┘
                                         │ fsync / fdatasync
                                         ▼
                                Hệ thống lưu trữ
```

- Đặt dấu crash đỏ **chỉ ở Redis process** khi minh họa `SIGKILL`.
- Giữ page cache trong vùng hệ điều hành, không đặt nó trong hộp Redis.
- Nhãn đường ghi: **“write: chuyển byte sang hệ điều hành”**.
- Nhãn đường sync: **“fsync/fdatasync: yêu cầu đồng bộ và đợi xác nhận”**.
- Đây là các giai đoạn logic. Không đặt một mũi tên ACK chung sau RAM hoặc sau storage cho tất cả policy.

**Bảng chính sách:**

| `appendfsync` | Cách đồng bộ | Đánh đổi chính |
|---|---|---|
| `always` | Trước xác nhận nhóm ghi | Chi phí đồng bộ cao hơn |
| `everysec` | Nền, khoảng mỗi giây | Cân bằng hiệu năng và độ bền |
| `no` | Để hệ điều hành quyết định flush | Phụ thuộc nhiều hơn vào OS/storage |

**Dòng nhấn luôn hiển thị:** **“Process crash giữ page cache. Mất nguồn là loại sự cố khác.”**

**Tương tác:** hai nút “Process crash” và “Mất nguồn” đổi phạm vi được đánh dấu trên sơ đồ. Đây là kiến thức chung về mô hình lỗi. Chế độ mất nguồn giải thích rằng dữ liệu chưa đồng bộ trong RAM/page cache có nguy cơ mất và khả năng phục hồi phụ thuộc dữ liệu đã lưu bền vững. Không đề cập demo ở slide lý thuyết này.

**Thẻ bấm mở: “everysec có phải mỗi giây mới ghi AOF?”**

Không. `write()` có thể đã chuyển byte vào page cache trước lần đồng bộ kế tiếp. `everysec` nói về nhịp fsync nền, không phải nhịp ghi AOF và không phải mỗi lần crash luôn mất đúng một giây dữ liệu.

**Thẻ bấm mở: “always có phải mỗi SET một fsync?”**

Redis có thể gộp nhiều lệnh thành một nhóm append/sync. Đồng bộ thành công là xác nhận theo giao diện hệ điều hành; không phải bảo đảm tuyệt đối trước mọi lỗi thiết bị và hạ tầng.

**Lời nói — 1:00:**

> Một lệnh được Redis xử lý thành công chưa tự trả lời dữ liệu đã bền vững đến đâu. Trên đường ghi AOF, write chuyển byte sang hệ điều hành, thường vào page cache trong RAM. fsync hoặc fdatasync yêu cầu đồng bộ file và đợi hệ điều hành xác nhận.
>
> Với always, Redis đồng bộ AOF trước khi xác nhận nhóm ghi; nhiều lệnh có thể dùng chung một lần sync. Everysec thực hiện đồng bộ nền khoảng mỗi giây, còn no để hệ điều hành quyết định việc flush.
>
> Everysec không có nghĩa mỗi giây mới ghi AOF hoặc mỗi lần crash chắc chắn mất một giây dữ liệu. Khi chỉ kill Redis, page cache vẫn còn và instance mới có thể đọc lại byte chưa được xác nhận fsync. Mất nguồn hoặc crash hệ điều hành là loại sự cố khác. Sync thành công cũng chưa thay thế kiểm chứng toàn bộ hệ thống lưu trữ.

**Nguồn trong notes:** lý thuyết mục 6, 8.2–8.3; kịch bản nói slide 5; ghi chú thiết kế phép thử.

---

## Slide 6: Chọn RDB, AOF hay kết hợp?

**Phụ đề:** Chọn theo lượng cập nhật có thể mất, chi phí tài nguyên và cách phục hồi.

**Bố cục:** một bảng so sánh ở giữa. Hai dòng kết luận dưới bảng. Không dùng huy chương, điểm số hoặc màu xanh/đỏ để xếp một cơ chế “thắng” cơ chế kia.

**Bảng hiển thị:**

| Tiêu chí | RDB | AOF |
|---|---|---|
| Bản chất | Trạng thái theo mốc | Trạng thái nền + các thay đổi |
| Dữ liệu gần sự cố | Phụ thuộc snapshot mới nhất | Phụ thuộc ghi và chính sách sync |
| Chi phí nổi bật | Fork, CoW, I/O snapshot | Append, sync, rewrite |
| Tình huống phù hợp | Backup theo mốc, chấp nhận khoảng mất cập nhật | Muốn giảm mất cập nhật và chọn mức đồng bộ |

**Hai dòng bắt buộc:**

- **Bật cả hai:** Redis ưu tiên nạp **AOF** khi khởi động với AOF được bật và có dữ liệu hợp lệ.
- **Persistence cần đi cùng backup độc lập.**

**Thẻ bấm mở: “Cache có thể không bật persistence?”**

Có, nếu dữ liệu có thể tái tạo và chấp nhận mất toàn bộ trạng thái của instance đó sau restart. Khi chọn cần cân nhắc cả tải dồn về nguồn dữ liệu lúc cache được làm nóng lại.

**Thẻ bấm mở: “RDB có luôn nhỏ hơn, nạp nhanh hơn?”**

Không nên dùng từ “luôn”. Kích thước và thời gian nạp phụ thuộc dataset, rewrite, storage và lượng incremental phải replay. So sánh hiệu năng cần cùng dữ liệu và điều kiện đo.

**Lời nói — 0:50:**

> RDB giữ trạng thái theo mốc, phù hợp khi cần snapshot gọn và chấp nhận khoảng thay đổi ngoài checkpoint. AOF ghi nhận cập nhật thường xuyên hơn, nhưng phát sinh chi phí append, đồng bộ và rewrite.
>
> Khi chọn, cần hỏi: có thể mất bao nhiêu cập nhật, chịu được mức I/O và latency nào, và cần phục hồi ra sao. Không có một phương án tốt nhất cho mọi workload. Cache tái tạo được thậm chí có thể không dùng persistence.
>
> Nếu bật cả RDB và AOF, Redis ưu tiên nạp AOF khi khởi động. Snapshot vẫn hữu ích cho backup theo mốc. Dù chọn cách nào, persistence vẫn cần đi cùng backup độc lập.

**Nguồn trong notes:** lý thuyết mục 9; đề cương và kịch bản nói slide 6. Không đưa bảng startup/dung lượng của demo vào slide này.

---

## Slide 7: Demo: từ checkpoint đến process crash

**Phụ đề:** Hai run riêng, cùng 2.000 baseline + 1.000 delta. Một run kiểm tra phục hồi, một run quan sát thêm fsync.

**Thời lượng:** giới thiệu khoảng **15 giây**, phát video khoảng **2 phút 30 giây**. Tổng slide **2:45**. Link Drive cập nhật sau.

### Bố cục và hình ảnh trực quan

Trước khi phát video, dùng **timeline hai nhánh** chiếm giữa slide. Dưới timeline có một hàng thông tin ngắn cho mốc pause; không cần ảnh terminal.

```text
                    Mốc pause: cả hai có 2.000 key
                                  │
RDB / 6380:  baseline 2.000 ─ checkpoint đã xong ─ delta 1.000 ─┐
                                                            │
AOF / 6381:  baseline 2.000 ─ everysec, không rewrite ─ delta 1.000
                                                            │
                          Đủ ACK cho các SET, Expected = 3.000
                                                            │
                                       Chờ delay yêu cầu
                                                            │
                                            SIGKILL Redis
                                                            │
                                      Restart cùng data/config
                                                            │
                                        Kiểm tra từng key/value
```

Khi dựng, thể hiện hai nhánh hội tụ ở bước “Đủ ACK” và đi tiếp theo cùng quy trình; không hiểu đây là kill đồng thời. Script gửi tín hiệu AOF trước, rồi RDB.

**Tương tác:** ba bước “Baseline”, “Delta”, “Khôi phục” nhấn sáng từng giai đoạn. Bước Baseline hiện **DBSIZE = 2.000** từ terminal 2; bước Delta hiện **Expected = 3.000 từ ACK**, không ghi “đã đo DBSIZE 3.000” vì log không có phép đo đó.

**Hàng xác nhận checkpoint, chỉ hiển thị các ý cần thiết:**

| RDB / 6380 | AOF / 6381 |
|---|---|
| 2.000 key | 2.000 key |
| `rdb_saves:1`, save `ok`, đang save `0` | `aof_enabled:1`, `appendfsync:everysec` |
| Một checkpoint sau baseline | `rdb_saves:0`; không có checkpoint RDB độc lập |

Đây là thông tin **trước delta**, được đọc ở mốc pause. Không sử dụng nó như trạng thái tại thời điểm kill hoặc sau restart.

### Vùng video

- Nút chuyển chế độ chỉ ghi **“Video”**. Placeholder: **“Demo 04 · Redis Persistence”**, kèm dòng **“Link Drive sẽ được cập nhật sau”**. Thời lượng 2:30 giữ trong kế hoạch nói/notes, không đưa vào nhãn nút.
- Video chiếm phần lớn màn hình sau khi phát; timeline có thể thu lại hoặc ẩn. Không đặt log đầy đủ cạnh video để người nghe đọc hai nơi.
- Nút mở Drive chỉ hoạt động khi có link hợp lệ. Không tạo link giả hoặc tự yêu cầu tải một video chưa tồn tại.
- Nhãn run rõ ràng: **“Run 1: không tracing”**, sau đó **“Run 2: có tracing”**. Cả hai đều **3.000 expected key**.
- Dòng nhắc: **“SIGKILL là process crash; OS và page cache vẫn tồn tại.”**

### Nội dung cần người xem theo dõi trong clip đã quay

Khi có file/link video, căn lời bình theo các đoạn thực tế. Bảng dưới đây dùng thứ tự nội dung trong log; chưa gán timestamp vì chưa xem được clip.

| Đoạn trong clip | Điểm cần theo dõi | Lời bình gợi ý nếu clip chưa có narration |
|---|---|---|
| Khởi động run 1 | Redis 7.0.15; redis-py 5.3.1; hai port; tracing Disabled | “Hai instance riêng nhận cùng một workload.” |
| Pause sau checkpoint, terminal 2 | Hai DBSIZE đều 2.000; RDB save xong; AOF everysec | “Lúc này mới có baseline. Chỉ nhánh RDB đã tạo checkpoint.” |
| Tiếp tục từng trial của run 1 | Delta, ACK, chờ 0 / 0,2 / 1,5 giây, kill và restart | “Sau khi nhận đủ ACK, script gây process crash rồi kiểm tra key và value.” |
| Bảng phục hồi run 1 | RDB Correct 2.000, Missing 1.000; AOF Correct 3.000 | “RDB trở về checkpoint; AOF phục hồi đủ trong ba trial này.” |
| Chuyển sang run 2 | Tracing Enabled; vẫn 2.000 + 1.000 key | “Run riêng này bổ sung quan sát fsync, không phải lặp lại chính run trước.” |
| Bảng có Fsync | 0: Not confirmed; 0,2 và 1,5: Confirmed | “Cùng phục hồi đủ key nhưng bằng chứng fsync khác nhau.” |
| Kết thúc | Run complete; instance đã dừng sau đo | “Script đã kiểm tra xong và dừng các instance demo.” |

**Lời giới thiệu — khoảng 0:15:**

> Video có hai run cùng 3.000 key: run đầu kiểm tra phục hồi, run sau theo dõi thêm fsync. Hai instance bắt đầu với 2.000 key; chỉ RDB tạo checkpoint. Sau đó script thêm 1.000 key, gây process crash rồi restart và kiểm tra.

**Trong video:** nếu clip đã có narration thì không đọc thêm. Nếu clip chỉ có terminal, dùng lời bình ngắn theo từng đoạn ở bảng trên, không đọc mọi dòng INFO hoặc đường dẫn thư mục.

**Dự phòng:** nếu chưa có link hoặc video không phát, dùng timeline và biểu đồ slide 8 để kể lại quy trình. Không khởi chạy phép thử mới trong lúc trình bày. Thời lượng video vẫn được dự trù khoảng 2:30; bản thay thế có thể ngắn hơn.

**Nguồn trong notes:** log terminal 1 do người trình bày cung cấp, terminal 2 trong tin nhắn; quy trình ở `run_trials.py`. Trích dữ liệu tự chứa nằm ở phần C dưới đây.

---

## Slide 8: Sau restart, dữ liệu nào còn lại?

**Phụ đề:** RDB khôi phục checkpoint; AOF phục hồi đủ key trong demo. Fsync cần bằng chứng riêng.

**Thời lượng:** khoảng **1:15**.

### Bố cục: biểu đồ phục hồi và bảng fsync

**Bên trái khoảng 55%:** biểu đồ thanh ngang cho số key **Correct sau restart**. Dùng cùng thang đo từ 0 đến 3.000, không cắt trục. Một đường/vạch tham chiếu thể hiện Expected = 3.000.

```text
Correct sau restart             0        1.000       2.000       3.000
                                │          │           │           │
RDB / 6380                      ████████████████████████┆···········┆
                                     Correct 2.000       thiếu 1.000

AOF / 6381                      ████████████████████████████████████
                                             Correct 3.000
```

Khối màu đặc là **key đúng đã khôi phục**. Khoảng nét đứt ở RDB là **key thiếu**, không phải key còn sống. Đánh nhãn trực tiếp “2.000 baseline còn” và “1.000 delta thiếu”; không chỉ dựa vào màu. Số liệu giống nhau ở cả ba trial của từng run.

Nhãn dưới biểu đồ: **“Expected 3.000, Corrupt 0 ở cả hai mode; kết quả phục hồi giống nhau trong hai run.”**

**Bên phải khoảng 45%:** bảng ba trial AOF của **run có tracing**, dùng đúng log mới:

| Delay yêu cầu (s) | Correct | Fsync |
|---:|---:|---|
| 0 | 3.000 | Not confirmed |
| 0.2 | 3.000 | Confirmed |
| 1.5 | 3.000 | Confirmed |

Dòng RDB có Fsync `N/A` trong log vì phép quan sát này dành cho AOF; không diễn giải N/A là fsync RDB thành công hay thất bại.

### Ba ý giải thích khi chỉ vào biểu đồ

1. **RDB còn 2.000:** snapshot hoàn tất sau baseline; không có checkpoint mới chứa 1.000 delta.
2. **AOF còn 3.000:** kết quả phù hợp với việc byte AOF có thể được đọc lại từ OS page cache sau process crash.
3. **Fsync khác số key:** ở delay 0, AOF đủ key nhưng chưa được xác nhận sync theo điều kiện của bộ phân tích.

**Dòng kết luận luôn hiển thị:** **“Khôi phục đủ ≠ xác nhận fsync ≠ kiểm chứng chịu mất nguồn.”**

### Tương tác bổ sung, không bắt buộc đọc hết

- Nút **“Trước / Sau crash”**: trước crash ghi “Expected 3.000 từ ACK” cho cả hai; sau restart hiện 2.000 và 3.000 Correct. Không gọi bước trước crash là phép đo DBSIZE trực tiếp.
- Nút **“Vì sao còn đủ key?”** mở sơ đồ nhỏ Redis process bị kill nhưng OS page cache còn, nối lại với slide 5.
- Thẻ **“0,2 giây đã Confirmed có mâu thuẫn everysec?”** mở giải thích bên dưới.
- Timing chi tiết để trong notes/phần C, không thêm bảng ACK(ms) lớn vào slide chính.

**Thẻ bấm mở: “Vì sao 0,2 giây đã Confirmed?”**

`everysec` là lịch đồng bộ nền; chu kỳ không bắt đầu lại từ ACK của từng SET. Một lần sync theo lịch có thể đến trước khi hết khoảng chờ 0,2 giây. Log mới cho thấy bộ quan sát xác nhận đủ điều kiện ở trial này, không có mâu thuẫn với chính sách khoảng mỗi giây. Không suy ra Redis được cấu hình fsync mỗi 0,2 giây, cũng không suy ra mọi trial delay 0,2 đều sẽ Confirmed.

Không có trace thô trong nội dung được cung cấp nên không chỉ định timestamp chính xác của syscall. Giải thích trên là cơ chế có thể xảy ra, còn trạng thái Confirmed là output của bộ quan sát.

**Thẻ bấm mở: “Not confirmed nghĩa là gì?”**

Không có sync đáp ứng đủ điều kiện xác nhận thận trọng của bộ phân tích: đúng file, bao phủ các ghi được đối chiếu, hoàn tất trước mốc kill. Nó không khẳng định chắc chắn dữ liệu chưa bền. `Unknown` là trạng thái thiếu thông tin để kết luận; không xuất hiện trong các hàng log lần này.

**Lời nói — khoảng 1:15:**

> Nhìn vào biểu đồ, RDB phục hồi 2.000 key baseline và thiếu 1.000 key ghi thêm. Snapshot đã xong trước delta, nên khởi động lại chỉ có checkpoint đó. Đây là kết quả của kịch bản, không phải RDB luôn mất một phần ba dữ liệu.
>
> AOF phục hồi đủ 3.000 key ở cả ba delay. Điều này phù hợp với việc kill Redis không làm mất page cache của hệ điều hành. Nhưng phục hồi đủ chưa chứng minh đã fsync: ở run có tracing, delay 0 đủ key mà vẫn Not confirmed.
>
> Delay 0,2 và 1,5 giây trong log mới là Confirmed. Với everysec, lịch sync nền không bắt đầu lại từ từng ACK, nên 0,2 giây có thể đã gặp một lần sync. Confirmed là xác nhận theo điều kiện của bộ quan sát, ở giao diện hệ điều hành; tracing cũng làm thay đổi timing.
>
> Kết luận là RDB phục hồi theo checkpoint, AOF dựng lại từ bộ file. Khôi phục đủ key, xác nhận fsync và khả năng chịu mất nguồn là ba mức kết luận khác nhau. Demo này chưa thử mất nguồn.

**Chuyển phần:** “Nhóm xin kết thúc phần nội dung và mời thầy cùng các bạn đặt câu hỏi.” Chuyển sang trang cảm ơn/Q&A đã có, không thêm slide nội dung thứ 9.

**Nguồn trong notes:** phần C của bản thiết kế này chứa output mới. Hai run cùng Redis 7.0.15, redis-py 5.3.1, nhưng khác chế độ tracing. Mỗi delay chỉ có một trial trong mỗi run, không dùng để ước lượng xác suất mất dữ liệu chung hoặc benchmark overhead của strace.

---

## B. Câu hỏi có thể bị hỏi và cách trả lời ngắn

Phần này là **speaker notes/hỏi đáp ngoài khoảng 9:10**, không phải nội dung cần thêm vào tám slide chính.

| Câu hỏi | Trả lời ngắn |
|---|---|
| Single-threaded có nghĩa chỉ một client kết nối? | Không. Nhiều socket được quản lý qua event loop; phần lớn logic lệnh dữ liệu được xử lý tuần tự. |
| Có nhiều core thì một lệnh nặng tự nhanh lên? | Không tự động. I/O threads và tác vụ nền không biến mọi command thành xử lý song song. |
| Snapshot lấy trạng thái lúc bắt đầu hay lúc ghi xong? | Với cơ chế fork/CoW đang trình bày, tại mốc fork; child hoàn tất ghi file sau đó. |
| Vì sao fork không copy ngay toàn bộ RAM? | Ban đầu parent/child chia sẻ trang; CoW sao chép các trang liên quan khi có thay đổi. |
| Base RDB của AOF có phải dump.rdb của nhánh RDB? | Không. Hai instance và hai bộ file riêng. Base định dạng RDB vẫn có thể thuộc AOF. |
| Rewrite có thay thế fsync? | Không. Rewrite làm gọn biểu diễn phục hồi; fsync liên quan đồng bộ file. |
| Bật cả RDB và AOF thì ưu tiên nạp gì? | AOF khi được bật và có bộ dữ liệu hợp lệ; RDB vẫn dùng cho backup theo mốc. |
| Terminal 2 có phải đã cho thấy 3.000 key? | Không. DBSIZE được đọc ở mốc baseline là 2.000. Expected 3.000 sau delta dựa trên SET đã ACK. |
| INFO AOF cũng có rdb_last_bgsave_status:ok? | Không đọc riêng trường đó để kết luận có snapshot. Nhánh này rdb_saves:0; trạng thái ok đơn lẻ chưa chứng minh một lần BGSAVE đã chạy. |
| Buffer AOF bằng 0 có chứng minh fsync delta? | Không. Đó là trạng thái buffer ở lúc đọc INFO trước delta, không phải bằng chứng syscall trước crash. |
| Vì sao AOF đủ key ở delay 0? | write có thể đã đưa byte vào page cache; kill process không xóa cache của OS. |
| Vì sao everysec mà 0,2 giây đã Confirmed? | Lịch sync nền không bắt đầu lại từ ACK cuối. Run này quan sát được sync đủ điều kiện; không cam kết mọi run giống nhau. |
| Not confirmed có nghĩa chắc chắn chưa bền? | Không. Chưa đủ điều kiện xác nhận; khác Unknown và khác kết luận mất dữ liệu. |
| N/A của RDB có nghĩa không dùng fsync? | Không. Chỉ là không thuộc phép xác nhận fsync AOF của script. |
| Delay 0 có phải kill tức thì? | Không. Ví dụ run không tracing: AOF ACK→kill 1,576 ms, RDB 16,250 ms. |
| Vì sao không chỉ dùng DBSIZE? | Đếm đúng số key chưa chắc đúng tập key/value. Correct dựa trên đối chiếu giá trị mong đợi. |
| Corrupt có nghĩa AOF hỏng vật lý? | Trong output này, đó là key tồn tại nhưng value sai, không tự chứng minh file hỏng. |
| RDB luôn mất 33,33%? | Không. 1.000 delta ngoài checkpoint là lựa chọn của workload này. |
| Có thể nói fsync đã hoàn tất trong 201,590 ms? | Không từ cột ACK(ms). Đây là khoảng ACK→kill, không phải thời lượng syscall fsync. |
| Có chứng minh AOF không mất dữ liệu khi mất điện? | Không. Chỉ gây process crash; xác nhận sync theo OS chưa kiểm chứng toàn bộ storage trước mất nguồn. |

**Nếu muốn hỏi lớp, chọn một câu ngoài khung chính:**

1. AOF đủ 3.000 key ở delay 0 có chứng minh fsync? **Không.**
2. Everysec có bắt đầu lại bộ đếm một giây sau từng SET? **Không.**
3. `aof_buffer_length:0` có đồng nghĩa dữ liệu đã bền vững? **Không.**

---

## C. Dữ liệu và diễn giải output thật trong video

Phần này giúp người dựng điền đúng số liệu và người trình bày trả lời khi cần. Không chép toàn bộ các bảng lên slide 8. Không cần chụp thêm ảnh để minh chứng.

### 1. Terminal 1: run không tracing

**Nguồn:** transcript đính kèm do người trình bày cung cấp. Run ID: `run-20261021-145636Z-7ngih21c`.

Lệnh đã dùng:

```bash
python3 demos/04-persistence-crash/scripts/run_trials.py \
  --trials 3 \
  --baseline 2000 \
  --delta 1000 \
  --delays 0,0.2,1.5 \
  --pause-after-checkpoint
```

Header ghi Redis **7.0.15**, client **redis-py 5.3.1**, RESP2, automatic retries disabled; `Fsync trace: Disabled`.

| Trial | Delay(s) | Mode | Expected | Correct | Missing | Corrupt | ACK(ms) |
|---|---:|---|---:|---:|---:|---:|---:|
| 1 | 0 | RDB | 3000 | 2000 | 1000 | 0 | 16.250 |
| 1 | 0 | AOF | 3000 | 3000 | 0 | 0 | 1.576 |
| 2 | 0.2 | RDB | 3000 | 2000 | 1000 | 0 | 207.419 |
| 2 | 0.2 | AOF | 3000 | 3000 | 0 | 0 | 204.933 |
| 3 | 1.5 | RDB | 3000 | 2000 | 1000 | 0 | 1515.678 |
| 3 | 1.5 | AOF | 3000 | 3000 | 0 | 0 | 1501.109 |

**Cách giải thích:**

- `[Paused]` là dừng **sau checkpoint, trước delta** để kiểm tra baseline. Thời gian chờ Enter không được gọi là ACK→kill của delta.
- `[Ready]` báo script sẽ ghi 1.000 delta, đợi delay rồi SIGKILL. Không phải thông báo snapshot mới chứa delta.
- `Expected` là số SET đã ACK. `Correct` là key có đúng value sau restart. `Missing` là key vắng mặt; `Corrupt` là key có value sai.
- Với mỗi hàng: `Correct + Missing + Corrupt = Expected`.
- `Delay(s)` là khoảng chờ yêu cầu sau khi hai bên xong batch delta. `ACK(ms)` đo từ ACK cuối riêng từng instance đến lúc gửi SIGKILL; hai cột khác đơn vị và khác mốc.
- Không có cột Fsync vì tracing tắt; không gán Confirmed hoặc Not confirmed cho run này.
- `Run complete` nói các instance demo đã được dừng sau khi đo phục hồi, không phải chưa từng restart được.

### 2. Terminal 1: run có tracing

**Nguồn:** cùng transcript người trình bày cung cấp. Run ID: `run-20261021-150053Z-mkfhwdbo`.

```bash
python3 demos/04-persistence-crash/scripts/run_trials.py \
  --trials 3 \
  --baseline 2000 \
  --delta 1000 \
  --delays 0,0.2,1.5 \
  --trace-fsync
```

Run này cũng Redis **7.0.15**, redis-py **5.3.1**, Expected **3.000**. Header ghi `Fsync trace: Enabled` và cảnh báo strace thay đổi timing.

| Trial | Delay(s) | Mode | Expected | Correct | Missing | Corrupt | ACK(ms) | Fsync |
|---|---:|---|---:|---:|---:|---:|---:|---|
| 1 | 0 | RDB | 3000 | 2000 | 1000 | 0 | 11.778 | N/A |
| 1 | 0 | AOF | 3000 | 3000 | 0 | 0 | 0.468 | Not confirmed |
| 2 | 0.2 | RDB | 3000 | 2000 | 1000 | 0 | 229.126 | N/A |
| 2 | 0.2 | AOF | 3000 | 3000 | 0 | 0 | 201.590 | Confirmed |
| 3 | 1.5 | RDB | 3000 | 2000 | 1000 | 0 | 1537.370 | N/A |
| 3 | 1.5 | AOF | 3000 | 3000 | 0 | 0 | 1502.981 | Confirmed |

**Cách giải thích:**

- Kết quả phục hồi giống run không tracing, nhưng timing là số đo của **run riêng**, không lấy hai run ghép thành một trial.
- Trial 1 AOF đủ key nhưng `Not confirmed`: số key phục hồi không tự chứng minh delta đã sync trước kill.
- Trial 2 và 3 là `Confirmed` theo bộ quan sát. Không áp dụng kết quả cũ “0,2 giây Not confirmed” vào run mới.
- `N/A` ở RDB chỉ là không áp dụng phép xác nhận fsync AOF. Không có giá trị `Unknown` trong run này.
- Không suy ra fsync mất 201,590 ms từ trial 2. ACK(ms) không phải thời lượng fsync.
- Không so trực tiếp 0,468 ms có tracing với 1,576 ms không tracing để kết luận tracing làm nhanh hơn: đó là hai run, mỗi delay một trial, có khác biệt scheduling/pha sync.

**Điều kiện Confirmed theo implementation:** bộ phân tích kiểm tra đúng incremental, đúng workload, các write thành công được đối chiếu; thấy fsync/fdatasync thành công trên đúng file, bắt đầu sau các ghi đã đối chiếu và hoàn tất trước mốc trước kill. Output này là kết quả của bộ phân tích, không phải tác giả slide tự thẩm định lại raw trace.

### 3. Terminal 2: đọc đúng mốc baseline/checkpoint

Hai lệnh thực tế đều trả 2.000:

```text
redis-cli -p 6380 DBSIZE
(integer) 2000

redis-cli -p 6381 DBSIZE
(integer) 2000
```

**Cách trình bày dễ hiểu:** tô hai khối RAM cùng nhãn “2.000 baseline”; thêm một checkpoint chỉ ở nhánh RDB. Gọi rõ đây là **trước khi thêm delta**. Không dùng số 2.000 này để nói AOF sau crash chỉ còn 2.000 key.

Trích chọn các trường từ `INFO persistence` được gửi trong tin nhắn:

| Trường | RDB / 6380 | AOF / 6381 |
|---|---|---|
| `loading` | 0 | 0 |
| `rdb_changes_since_last_save` | 0 | 2000 |
| `rdb_bgsave_in_progress` | 0 | 0 |
| `rdb_last_bgsave_status` | ok | ok |
| `rdb_last_bgsave_time_sec` | 0 | -1 |
| `rdb_current_bgsave_time_sec` | -1 | -1 |
| `rdb_saves` | 1 | 0 |
| `rdb_last_cow_size` | 311296 | 0 |
| `aof_enabled` | 0 | 1 |
| `aof_rewrite_in_progress` | 0 | 0 |
| `aof_rewrites` | 0 | 0 |
| `aof_last_write_status` | ok | ok |
| `aof_current_size` | không có trong đoạn INFO gửi | 108023 |
| `aof_base_size` | không có trong đoạn INFO gửi | 0 |
| `aof_buffer_length` | không có trong đoạn INFO gửi | 0 |
| `aof_pending_bio_fsync` | không có trong đoạn INFO gửi | 0 |
| `aof_delayed_fsync` | không có trong đoạn INFO gửi | 0 |

Lệnh cấu hình AOF:

```text
redis-cli -p 6381 CONFIG GET appendfsync
1) "appendfsync"
2) "everysec"
```

**Ý cần giải thích khi nói hoặc hỏi đáp:**

- **Nhánh RDB:** `rdb_saves:1`, trạng thái `ok`, không còn save chạy, và `rdb_changes_since_last_save:0` phù hợp checkpoint baseline đã hoàn tất trong quy trình script.
- **Nhánh AOF:** bật AOF, `rdb_saves:0`; 2.000 thay đổi ở bộ đếm RDB không có nghĩa AOF chưa ghi hoặc mất 2.000 key. Một mình `rdb_last_bgsave_status:ok` không chứng minh đã tạo snapshot.
- **Thời gian `0` và `-1`:** một save ghi nhận thời lượng 0 giây ở độ phân giải giây; `-1` ở thời gian save hiện tại không phải job đang chạy. Không biến 0 giây thành “snapshot hoàn toàn không tốn thời gian”.
- **CoW `311296`:** byte CoW được ghi nhận trong lần lưu RDB trước; không phải số key, kích thước snapshot hay toàn bộ RAM của Redis. `current_cow_*:0` không phủ nhận CoW đã xảy ra.
- **INFO không phải bằng chứng fsync của delta:** các trường đang được đọc trước delta; không thay thế run tracing riêng.

**Các trường AOF dễ đọc nhầm** — đối chiếu định nghĩa trong [Redis INFO](https://redis.io/docs/latest/commands/info/):

| Output AOF | Ý nghĩa khi đọc |
|---|---|
| `aof_current_size:108023` | Kích thước AOF được INFO báo; không phải key hoặc byte đã xác nhận sync. |
| `aof_base_size:0` | Kích thước mốc startup/rewrite; không phải số key trong base. |
| `aof_buffer_length:0` | Buffer rỗng lúc đọc, không chứng minh fsync. |
| `aof_pending_bio_fsync:0` | Không có job fsync đang chờ; không xác nhận delta. |
| `aof_delayed_fsync:0` | Bộ đếm sync trễ bằng 0; không là số lần sync. |
| `aof_last_write_status:ok` | Trạng thái ghi AOF; không là cam kết chịu mất nguồn. |

Không dùng `aof_base_size:0` để kết luận file base không tồn tại hoặc file có đúng 0 byte. Log này không liệt kê file; muốn kết luận thành phần vật lý phải đọc bộ file/manifest. Các trường AOF xuất hiện trong INFO của nhánh RDB dù AOF tắt cũng không phải bằng chứng nhánh đó đang ghi AOF; luôn đọc cùng `aof_enabled`.

### 4. Những việc không đưa vào tám slide

- Không chèn toàn bộ INFO, mọi đường dẫn trial, timestamp epoch hoặc code parser vào phần chính.
- Không yêu cầu thêm ảnh chụp, không tạo terminal giả thay video đã có.
- Lấy timing và trạng thái fsync từ đúng run ở phần C.1/C.2.
- Không thêm INFO/DBSIZE vào cửa sổ sau ACK delta trước kill khi quay lại; ở clip này terminal 2 dùng lúc pause trước delta.
- Khi có link Drive, chỉ cập nhật nguồn video ở slide 7 và căn lời bình theo clip thực tế. Không suy ra timestamp video từ tên thư mục trial hoặc độ dài đoạn chat.

---

## D. Nguồn đối chiếu và quy tắc cập nhật

| Nội dung | Nguồn |
|---|---|
| Mẫu mô tả thiết kế | [presentation-notes-01.md](presentation-notes-01.md) |
| Lý thuyết cho slide 1–6 | [04-redis_architecture_persistence.md](docs/theory/04-redis_architecture_persistence.md) |
| Đề cương và lời nói tham khảo | [Đề cương](docs/presentation-notes/redis-architecture-persistence-slides.md), [kịch bản nói](docs/presentation-notes/redis-architecture-persistence-talk.md) |
| Kết quả cho slide 7–8 | Log terminal 1 và 2 người trình bày cung cấp, trích lại ở phần C |
| Quy trình ACK, checkpoint, kill, restart | [run_trials.py](demos/04-persistence-crash/scripts/run_trials.py), [README](demos/04-persistence-crash/README.md) |
| Định nghĩa Confirmed/Not confirmed | [fsync_trace.py](demos/04-persistence-crash/scripts/fsync_trace.py), [scripts.md](demos/04-persistence-crash/scripts.md) |
| Giới hạn phép thử | [persistence-crash-review.md](docs/presentation-notes/persistence-crash-review.md) |
| Báo cáo các phép đo trước | [report.md](demos/04-persistence-crash/report.md), chỉ dùng để tham khảo phương pháp, không thay log mới |
| Định nghĩa trường INFO | [Redis INFO](https://redis.io/docs/latest/commands/info/) |

Nguồn Redis chính thức để trong speaker notes khi cần: [Persistence](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/), [latency](https://redis.io/docs/latest/operate/oss_and_stack/management/optimization/latency/), [BGSAVE](https://redis.io/docs/latest/commands/bgsave/), [SCAN](https://redis.io/docs/latest/commands/scan/), [SLOWLOG](https://redis.io/docs/latest/commands/slowlog/).

**Quy tắc cập nhật:** dùng phần C làm nguồn số liệu cho slide 7–8. Khi có link Drive, căn lời bình theo video khoảng 2:30 và giữ nhãn hai run rõ ràng. Nguồn tham khảo đặt trong notes để tám slide chính tập trung vào nội dung trình bày.
