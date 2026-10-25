# **Hướng dẫn tạo slide tổng quan Redis và môi trường**

Phần 1 của seminar Redis  \|  Tiếng Việt  \|  5 phút gồm 90 giây video

Tạo 7 slide mở đầu để người nghe hiểu Redis là gì, vì sao dùng làm cache và các demo sẽ khảo sát điều gì. Nội dung đi theo một ví dụ đọc thông tin sản phẩm; phần môi trường giới thiệu cách tách các demo trước khi chuyển sang cấu trúc dữ liệu và TTL.

# **A  Hướng dẫn chung**

* Mỗi slide có một tiêu đề lớn, một phụ đề ngắn và một thông điệp chính. Nội dung hiển thị khoảng 20–40 từ, ưu tiên sơ đồ; phần “Lời nói” dùng làm speaker notes, không chép lên slide.  
* Dùng tiếng Việt tự nhiên, trung tính. Giải thích thuật ngữ ngay lần đầu: RAM là bộ nhớ làm việc; key là khóa; value là giá trị; cache là bộ nhớ đệm. Kể tiếp tình huống sản phẩm thay vì đọc danh sách định nghĩa.  
* Khung hình 16:9, nền sáng, chữ tương phản cao. Tiêu đề khoảng 32–40 pt, nội dung 24–28 pt. Màu nhấn đỏ cho Redis, xanh cho dữ liệu tìm thấy; không dùng màu làm dấu hiệu duy nhất.  
* Nếu có base HTML của nhóm, giữ font, màu và điều hướng của base. Chỉ dùng bấm để hiện ở nhánh cache hit/miss; bản tĩnh phải thể hiện đủ nội dung. Không bắt buộc tương tác trên mọi slide.  
* Không giảng thuật toán, công thức hiệu năng, lệnh từng kiểu dữ liệu hoặc cơ chế lưu đĩa trong overview. Không thêm phần giải thích RDB/AOF vào lý thuyết mở đầu; để chủ demo trình bày sau.

## **Phân bổ thời gian**

| Slide | Nội dung | Thời lượng |
| :---: | :---- | :---- |
| 1 | Tình huống đọc lặp lại và Redis | 45 giây |
| 2 | Key và value | 30 giây |
| 3 | Cache hit và cache miss | 45 giây |
| 4 | Giới hạn và thêm một ứng dụng | 30 giây |
| 5 | Cách bố trí môi trường demo | 30 giây |
| 6 | Video setup đã chọn đoạn | 90 giây |
| 7 | Chuyển sang các demo | 30 giây |

# **Tài nguyên để tạo slide**

Ảnh dưới đây thuộc giai đoạn setup môi trường chung, được lưu tại:

docs/screenshots/00-environment-setup/vmware-2026-10-20/screenshots/

| File | Nội dung cần lấy | Slide |
| :---: | :---- | :---- |
| 01-vm-settings.png | Allocation 512 MB RAM và 2 processors | 5 hoặc 6 |
| 02-os-and-commit.png | Ubuntu, kernel và commit của lượt chạy | 6 |
| 03-setup-versions.png | Redis/Python và PONG ở cuối setup | 6 |
| 05-ports.png | Các port hoạt động | 6 |
| 06-config-pass.png | Kết luận checker PASS | 6 |
| 07-isolation-ttl.png | Key ở 6383 và cách ly với 6384 | 6 |

Không cần chèn tất cả ảnh cùng lúc. Slide 5 ưu tiên sơ đồ; slide 6 dùng video và một ảnh checker dự phòng. Crop phần terminal cần đọc nhưng giữ lệnh, output và port liên quan; không sửa nội dung output.

## **Video môi trường**

Bản gốc: 2026-10-20 14-56-09.mp4, dài 8 phút 26.8 giây. File được lưu ngoài Git trong thư mục Seminar evidence. Dùng đoạn chọn tổng khoảng 90 giây; bản cắt và đường dẫn chia sẻ cần được bổ sung khi dựng deck. Không gán tên clip mới như thể đã có file.

Video có terminal nền sáng và không có lời dẫn nghe được. Thuyết minh trực tiếp theo slide 6\. Không phát toàn bộ thời gian cài package; chuẩn bị bản offline để phát trên máy trình chiếu.

## **Thông tin đúng cho minh chứng setup**

| Thành phần | Giá trị dùng trong phần overview |
| :---- | :---- |
| Máy ảo | VMware Workstation Pro 26H1u1; allocation 512 MB RAM, 2 processors |
| Phiên bản trong guest | Ubuntu 26.04.1 LTS; Redis 8.0.5; Python 3.14.4 |
| Điều kiện bộ nhớ | Swap bật khoảng 1.6 GiB; ghi trong speaker notes khi nói về giới hạn VM |
| Phạm vi đã kiểm tra | Setup, kết nối, cấu hình, cách ly và probe nhỏ; chưa phải kết quả bốn workload |

Các số này mô tả recording setup ngày 20/10/2026. Mỗi demo chuyên đề dùng đúng phiên bản từ minh chứng của demo đó; không chép phiên bản từ tab tham khảo sang phần setup.

# **Slide 1  Redis hỗ trợ việc đọc dữ liệu lặp lại**

**Phụ đề:** Bắt đầu từ một trang thông tin sản phẩm

**Thời gian:** 0:00–0:45

**Nội dung hiển thị:** Một sản phẩm được xem nhiều lần. Ứng dụng cần đọc lại cùng thông tin tên và giá.

**Định nghĩa trên slide:** Redis lưu dữ liệu đang phục vụ chủ yếu trong RAM, tức bộ nhớ làm việc của máy tính.

**Bố cục:** Bên trái đặt một thẻ sản phẩm minh họa; ở giữa là ứng dụng; bên phải là cơ sở dữ liệu chính. Cho các lượt xem lần lượt đi qua cùng đường đọc. Sau đó hiện ô Redis với nhãn “Dùng lại dữ liệu đã lưu”. Đây là sơ đồ khái niệm, không phải số đo thực nghiệm.

**Lời nói:** “Một trang bán hàng có thể nhận nhiều lượt xem cùng một sản phẩm. Mỗi lượt xem đều cần tên và giá. Nếu ứng dụng phải lặp lại việc lấy và xử lý cùng dữ liệu, nguồn dữ liệu sẽ phải làm thêm việc. Redis là một hệ thống lưu trữ dữ liệu, giữ dữ liệu đang phục vụ chủ yếu trong RAM, tức bộ nhớ làm việc của máy tính. Nó có thể giúp ứng dụng đáp ứng nhanh những yêu cầu đọc và ghi này.”

**Chuyển slide:** “Để lấy dữ liệu từ Redis, ứng dụng cần biết tên dùng để nhận diện dữ liệu đó.”

# **Slide 2  Tìm dữ liệu bằng key**

**Phụ đề:** Key là khóa nhận diện và value là giá trị đi kèm

**Thời gian:** 0:45–1:15

**Nội dung hiển thị:** Key: san-pham:42  →  Value: thông tin sản phẩm số 42

**Bố cục:** Dùng một sơ đồ key → value lớn ở giữa. Trong ô value chỉ có “Tên sản phẩm” và “Giá”. Không hiển thị JSON hoặc danh sách lệnh; không đặt ảnh terminal vào một khái niệm có thể giải thích bằng sơ đồ.

**Lời nói:** “Dữ liệu trong Redis được tìm bằng key, nghĩa là khóa nhận diện. Phần thông tin đi kèm khóa được gọi là value, hay giá trị. Ví dụ, san-pham:42 nhận diện thông tin của sản phẩm số 42\. Khi cần dữ liệu, ứng dụng dùng khóa để lấy giá trị tương ứng. Các kiểu giá trị và cách thao tác sẽ được minh họa ở phần tiếp theo.”

**Chuyển slide:** “Trong ví dụ này, Redis có thể giữ một bản thông tin sản phẩm để dùng lại.”

# **Slide 3  Dùng lại thông tin sản phẩm qua cache**

**Phụ đề:** Cache là bộ nhớ đệm giữ dữ liệu để dùng lại

**Thời gian:** 1:15–2:00

**Nội dung hiển thị:** Cache hit: tìm thấy bản lưu. Cache miss: chưa có, cần lấy từ nguồn.

**Bố cục:** Vẽ 3 ô “Ứng dụng”, “Redis cache”, “Cơ sở dữ liệu chính”. Hiện nhánh hit trước: ứng dụng hỏi Redis và nhận dữ liệu. Hiện nhánh miss sau: ứng dụng hỏi Redis, nhận kết quả chưa có, đọc nguồn rồi có thể lưu lại vào Redis. Gắn nhãn và đánh số mũi tên để hai nhánh không chồng lên nhau.

**Lời nói:** “Cơ sở dữ liệu chính vẫn giữ thông tin sản phẩm. Redis giữ thêm một bản thường được đọc, gọi là cache hay bộ nhớ đệm. Nếu ứng dụng tìm thấy dữ liệu ở Redis thì đó là cache hit và có thể dùng bản lưu. Nếu chưa tìm thấy thì đó là cache miss: ứng dụng phải lấy từ cơ sở dữ liệu chính, rồi có thể lưu lại cho lần sau. Lợi ích ở đây là giảm công việc lặp lại tại nguồn. Phần Cache-Aside sẽ trình bày cách phối hợp các bước cụ thể.”

**Lưu ý cho người gen:** Không thêm con số “nhanh hơn X lần” hoặc đồ thị thời gian giả. Đây là ví dụ cách dùng Redis; không mô tả mọi ứng dụng Redis đều phải đi qua một cache.

# **Slide 4  Chọn dữ liệu phù hợp để giữ trong Redis**

**Phụ đề:** Cần chú ý độ mới của dữ liệu và dung lượng bộ nhớ

**Thời gian:** 2:00–2:30

**Nội dung hiển thị:** Giá đã đổi → bản cache cũng cần được cập nhật hoặc xóa. RAM có giới hạn → cần chọn dữ liệu giữ lại.

**Bố cục:** Hai hình đơn giản: nhãn giá tại nguồn và trong cache đang lệch nhau; thanh dung lượng RAM. Cuối slide đặt một hình bảng xếp hạng nhỏ để giới thiệu thêm ứng dụng, không hiển thị lệnh hay thuật toán.

**Lời nói:** “Cache cũng cần được quản lý. Nếu giá tại nguồn đã thay đổi mà bản lưu chưa đổi, ứng dụng có thể trả giá cũ. RAM có giới hạn nên cũng cần quyết định dữ liệu nào được giữ lại. Ngoài cache, Redis còn hỗ trợ thao tác với dữ liệu có cấu trúc, chẳng hạn cập nhật điểm và lấy danh sách người chơi theo thứ hạng. Những tình huống này sẽ được minh họa trong các demo.”

# **Slide 5  Mỗi demo dùng một tiến trình Redis riêng**

**Phụ đề:** Tách cổng kết nối và thư mục dữ liệu

**Thời gian:** 2:30–3:00

**Thông tin trên slide:** VMware · 512 MB RAM · Ubuntu 26.04.1 · Redis 8.0.5

**Thông điệp:** Một VM chứa 5 tiến trình Redis dành cho 4 demo. Service mặc định ở 6379 được quản lý riêng.

**Bố cục:** Vẽ một khung VM lớn chứa bốn vùng demo. Vùng phục hồi có hai tiến trình; mỗi vùng còn lại có một. “Tiến trình” là một chương trình Redis đang chạy; “cổng” là số giúp ứng dụng chọn đúng nơi kết nối. Đặt nhãn này gần sơ đồ ngay lần đầu xuất hiện.

| Demo | Nhãn cổng trên sơ đồ |
| :---- | :---- |
| Cấu trúc dữ liệu và thời hạn key | 6383 |
| Cache-Aside | 6384 |
| Giới hạn bộ nhớ | 6382 |
| Phục hồi dữ liệu | 6380 và 6381 |

**Lời nói:** “Môi trường setup đã ghi hình là một VM VMware được cấp 512 MB RAM. Để các demo không dùng chung dữ liệu, mỗi thử nghiệm kết nối tới một chương trình Redis đang chạy riêng, gọi là tiến trình. Cổng kết nối giúp ứng dụng chọn đúng tiến trình đó; mỗi tiến trình cũng có thư mục dữ liệu riêng. Riêng phần phục hồi dùng hai tiến trình để đối chiếu. Sau đây là đoạn kiểm tra môi trường trước khi vào các bài demo.”

**Ghi chú bổ sung:** Đưa vào notes: VM có 2 processors; swap bật khoảng 1.6 GiB. Năm tiến trình demo cùng service 6379 tạo thành sáu kết nối được checker kiểm tra. Chỉ bố trí đủ 5 tiến trình khi kiểm tra tích hợp; thành viên có thể phát triển riêng demo của phần được giao.

**Tài nguyên:** Ảnh 01-vm-settings.png là minh chứng allocation, không thay bằng giá trị RAM guest nhìn thấy. Sơ đồ chỉ cần tên demo và port; đường dẫn cấu hình cùng lệnh setup để trong hướng dẫn vận hành.

# **Slide 6  Kiểm tra môi trường trước khi chạy demo**

**Phụ đề:** Kết nối hoạt động và dữ liệu được tách giữa các tiến trình

**Thời gian:** 3:00–4:30

**Bố cục:** Đặt video ở giữa với nút phát. Một dòng chú thích: “Minh chứng setup ngày 20/10/2026”. Có ảnh 06-config-pass.png làm phương án thay thế khi không phát được video.

**Dựng đoạn video:** Bảng dưới là kế hoạch chọn footage; các khoảng ghi là thời gian trong clip đích 90 giây. Chọn từ recording gốc, giữ output đủ lâu để đọc và giữ đúng thứ tự lệnh với kết quả.

| Thời gian | Hình cần thấy | Lời nói khi phát |
| :---: | :---- | :---- |
| 0–15 giây | Ảnh settings VM, OS và phiên bản Redis | “VM được cấp 512 MB RAM. Đây là phiên bản Ubuntu và Redis của lượt setup.” |
| 15–35 giây | PONG và các port | “PONG xác nhận chương trình Redis trả lời được tại cổng đang kiểm tra.” |
| 35–55 giây | Kết luận checker PASS | “Checker kiểm tra các cổng, thư mục và cấu hình theo repo.” |
| 55–80 giây | 6383 đọc được key; 6384 không có cùng key | “Dữ liệu ghi ở tiến trình này không xuất hiện trong tiến trình kia.” |
| 80–90 giây | Giữ sơ đồ port hoặc ảnh PASS | “Các kiểm tra setup đã đạt trong phạm vi này. Mỗi demo sẽ có phép thử riêng.” |

**Mốc video gốc:** Các vùng tham khảo trong video gốc: 00:00–00:25 cho OS/commit; 01:45–02:50 cho phiên bản/service/PONG; 03:30–04:10 cho port/checker; 04:10–05:15 cho cách ly/TTL. Đây là mốc gần đúng để chọn đoạn, không phải clip đã được dựng.

**Nội dung terminal:** Nếu dựng lại một khung terminal thay ảnh, chỉ chép lệnh và output từ log. Ví dụ đã có minh chứng: redis-cli \-p 6379 PING trả PONG. Không tạo log hoặc sửa kết quả để minh họa.

**Giữ đúng phạm vi:** Chỉ chọn phần cách ly trong footage có TTL; việc giải thích TTL dành cho demo kế tiếp. Video overview không cần phần restart. Không đưa kết luận “đã chạy đủ bốn workload” hoặc kết quả crash từ lần kiểm tra setup.

**Phương án dự phòng:** Nếu không phát video được, trình bày ảnh settings, ảnh checker và ảnh cách ly theo đúng thứ tự; không tăng thời lượng phần này quá 90 giây.

# **Slide 7  Các demo sẽ kiểm tra điều gì**

**Phụ đề:** Từ cách tổ chức dữ liệu đến vận hành

**Thời gian:** 4:30–5:00

**Bố cục:** Đặt bốn câu hỏi nối tiếp nhau. Câu đầu được nhấn để chuyển người trình bày; mỗi câu chỉ một dòng.

| Phần | Câu hỏi trên slide |
| :---- | :---- |
| Cấu trúc dữ liệu và TTL | Tổ chức dữ liệu và đặt thời hạn cho key thế nào? |
| Cache-Aside | Dùng cache để giảm thời gian chờ thế nào? |
| Eviction | Redis xử lý ra sao khi chạm giới hạn bộ nhớ? |
| Persistence | Dữ liệu có thể phục hồi ra sao sau sự cố? |

**Thuật ngữ:** Nếu giữ tên tiếng Anh, thêm nghĩa ngay cạnh: TTL là thời gian sống của key; eviction là loại dữ liệu khi chạm giới hạn bộ nhớ; persistence là lưu dữ liệu để có thể phục hồi. Chỉ giới thiệu câu hỏi, không mở thêm slide định nghĩa.

**Lời nói:** “Từ nền tảng này, các demo sẽ lần lượt trả lời bốn câu hỏi: tổ chức dữ liệu và đặt thời hạn ra sao, dùng cache để giảm thời gian chờ thế nào, xử lý khi đầy bộ nhớ thế nào và phục hồi dữ liệu sau sự cố ra sao. Mỗi phần sẽ có cơ chế cùng kết quả riêng. Bắt đầu với cấu trúc dữ liệu và TTL, tức thời gian sống của key.”

## **B  Câu hỏi dự phòng**

Dùng khi được hỏi, không tạo thêm slide trong thời lượng 5 phút.

| Câu hỏi | Trả lời ngắn |
| :---- | :---- |
| Redis có phải chỉ là cache không? | Cache là một cách dùng phổ biến. Redis còn hỗ trợ thao tác trên nhiều cấu trúc dữ liệu; phần kế tiếp sẽ minh họa. |
| Vì sao cache có thể trả giá cũ? | Bản tại nguồn đã đổi nhưng bản cache chưa được cập nhật hoặc xóa. Cách xử lý nằm trong phần Cache-Aside. |
| Vì sao cần nhiều tiến trình? | Mỗi demo có cổng, cấu hình và dữ liệu riêng để giảm ảnh hưởng giữa các thử nghiệm. |
| PASS có nghĩa là mọi demo đều đạt? | PASS ở đây xác nhận các kiểm tra hạ tầng trong checker. Workload và số đo thuộc từng demo. |
| VM có chạy không swap không? | Lượt setup có swap bật khoảng 1.6 GiB. Không mô tả kết quả này là kiểm tra không swap. |

# **C  Prompt để tạo slide**

Đưa tài liệu này cùng base slide của nhóm và các ảnh/video đã chọn cho công cụ tạo slide. Có thể dùng nguyên prompt sau:

Tạo phần mở đầu seminar Redis bằng tiếng Việt theo tài liệu đính kèm, gồm đúng 7 slide. Tổng thời lượng 5 phút, trong đó slide 6 dành 90 giây cho video setup. Giữ nguyên thứ tự và thông điệp từng mục Slide 1 đến Slide 7\. Dùng mục “Nội dung hiển thị” để viết ngắn trên slide; mục “Bố cục” để dựng sơ đồ; mục “Lời nói” chỉ đưa vào speaker notes. Không đưa câu hỏi dự phòng, prompt hoặc checklist thành slide.

Giữ phong cách của base slide đính kèm. Nếu không có base, dùng 16:9, nền sáng, chữ lớn và màu nhấn đỏ Redis. Mỗi slide một ý chính; giải thích thuật ngữ khi xuất hiện. Dùng xuyên suốt ví dụ thông tin sản phẩm. Sơ đồ cache phải phân biệt rõ nhánh hit và miss. Không thêm công thức, tốc độ giả định hoặc giải thích sâu các phần demo.

Chỉ dùng ảnh/log/video thật được cung cấp. Minh chứng setup dùng Ubuntu 26.04.1 LTS, Redis 8.0.5, VM VMware 512 MB RAM và có swap bật. Không lấy phiên bản từ tab mẫu của demo khác. Nếu thiếu video đã cắt hoặc link phát, đặt placeholder ghi rõ tài nguyên cần chèn; không tạo một URL hoặc file như thể đã tồn tại. Nếu xuất HTML, nút bấm phải có cách xem đầy đủ ở bản tĩnh; không tự phát video. Nếu xuất PPTX, giữ chữ và sơ đồ chỉnh sửa được.

## **D  Checklist trước khi dùng**

* Đủ 7 slide; thời lượng 45 \+ 30 \+ 45 \+ 30 \+ 30 \+ 90 \+ 30 \= 300 giây.  
* Các thuật ngữ mới có giải thích ngắn; lời nói đi theo ví dụ, không đọc bảng thuật ngữ.  
* Nội dung trên slide ngắn; speaker notes và phần hỏi đáp không tràn vào nội dung trình chiếu.  
* Ảnh/lệnh/output đúng minh chứng; bản video hoặc placeholder được ghi rõ trạng thái.  
* Video phát được trên máy trình chiếu, chữ đọc được; có bản offline và ảnh dự phòng.  
* Không thêm đoạn RDB/AOF vào overview hoặc suy diễn setup PASS thành kết quả workload.

## **E  Tài liệu đối chiếu**

[Tab mẫu  Phần cấu trúc dữ liệu và TTL](?tab=t.i8o2xb6eg82k#bookmark=id.tfmm0zxh5bin)

[Nội dung overview và nguồn Redis chính thức](https://github.com/tbnguyen274/redis-seminar/blob/938f9d1ad8dd30a1ded0ab6a2eedea16ec40ad20/theory/01-redis-overview.md)

[Ghi chú thời lượng và shot list môi trường](https://github.com/tbnguyen274/redis-seminar/blob/938f9d1ad8dd30a1ded0ab6a2eedea16ec40ad20/docs/presentation-notes/01-overview-environment.md)

[Kết quả kiểm tra môi trường VMware](https://github.com/tbnguyen274/redis-seminar/blob/938f9d1ad8dd30a1ded0ab6a2eedea16ec40ad20/docs/environment-verification.md)

[Chỉ mục ảnh video và log setup](https://github.com/tbnguyen274/redis-seminar/blob/938f9d1ad8dd30a1ded0ab6a2eedea16ec40ad20/docs/screenshots/00-environment-setup/vmware-2026-10-20/README.md)

Nguồn khái niệm: Redis Get started và FAQ; Cache-aside; Leaderboards. Dùng các liên kết nguồn trong tài liệu overview, đặt nguồn ở notes hoặc tài liệu tham khảo chung của deck.

