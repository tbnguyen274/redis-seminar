# Tổng quan Redis

## Redis là gì?

Một ứng dụng thường phải đọc lại cùng một thông tin nhiều lần, chẳng hạn giá của một sản phẩm trên trang bán hàng. Nếu mỗi lượt xem đều phải thực hiện lại việc tìm kiếm và xử lý dữ liệu, ứng dụng sẽ tốn thêm thời gian và tài nguyên. Redis là một công cụ có thể hỗ trợ trong tình huống này.

Redis là một hệ thống lưu trữ dữ liệu, giữ dữ liệu đang phục vụ chủ yếu trong **RAM**, tức bộ nhớ làm việc của máy tính. Nhờ đó, Redis có thể đáp ứng nhanh các yêu cầu đọc và ghi. [S1]

Dữ liệu trong Redis được tìm bằng **key (khóa)**, là tên dùng để nhận diện dữ liệu. Phần thông tin gắn với khóa được gọi là **value (giá trị)**. Ví dụ, khóa `san-pham:42` có thể gắn với tên và giá của sản phẩm số 42. Khi cần thông tin của sản phẩm này, ứng dụng dùng khóa đó để lấy giá trị tương ứng.

## Vì sao dùng Redis làm cache?

Trong ví dụ trang bán hàng, cơ sở dữ liệu chính vẫn giữ thông tin sản phẩm. Redis có thể giữ thêm một bản thông tin thường được đọc để ứng dụng dùng lại. Bản dữ liệu này đóng vai trò **cache (bộ nhớ đệm)**; việc lưu và dùng lại kết quả như vậy gọi là **caching**. [S2]

Khi có yêu cầu xem sản phẩm, ứng dụng kiểm tra Redis trước. Nếu thông tin đã có trong cache, ứng dụng có thể dùng ngay; trường hợp này gọi là **cache hit**. Nếu chưa có, đó là **cache miss**: ứng dụng phải lấy thông tin từ cơ sở dữ liệu chính, rồi có thể lưu lại trong Redis cho những lần đọc sau.

Lợi ích của cách làm này là giảm công việc phải lặp lại ở nguồn dữ liệu. Tuy nhiên, nếu giá sản phẩm đã thay đổi mà cache vẫn giữ giá cũ, ứng dụng có thể trả thông tin không còn đúng. Vì vậy, sử dụng cache cũng cần xác định khi nào bản lưu phải được cập nhật hoặc xóa. Cách phối hợp các bước này sẽ được trình bày trong phần demo riêng.

## Redis hỗ trợ những tình huống nào?

Cache là một cách sử dụng phổ biến, nhưng Redis còn cho phép thao tác trực tiếp trên dữ liệu có cấu trúc. Chẳng hạn, với một bảng xếp hạng trò chơi, ứng dụng cần cập nhật điểm và lấy danh sách người chơi theo thứ tự điểm. Redis có cấu trúc dữ liệu hỗ trợ nhu cầu đó, thay vì chỉ lưu từng giá trị rời rạc. Phần cấu trúc dữ liệu sẽ minh họa cụ thể hơn. [S3]

Việc chọn Redis cần gắn với nhu cầu thực tế. Cache hữu ích khi dữ liệu được đọc lặp lại và việc lấy dữ liệu từ nguồn tốn nhiều công sức. Đồng thời, RAM có giới hạn nên cần quyết định dữ liệu nào nên giữ khi bộ nhớ đầy. Đó cũng là một trong những tình huống được khảo sát trong seminar.

## Từ tổng quan đến các demo

Các phần tiếp theo sẽ lần lượt minh họa cách tổ chức dữ liệu và đặt thời hạn lưu, cách dùng cache để giảm thời gian chờ, cách Redis xử lý khi chạm giới hạn bộ nhớ, rồi khả năng phục hồi dữ liệu sau sự cố. Mỗi phần sẽ giải thích cơ chế cùng kết quả quan sát được.

Để các thử nghiệm có thể chạy độc lập, mỗi demo sử dụng một tiến trình Redis riêng, tức một chương trình Redis đang chạy, với cổng kết nối và thư mục dữ liệu riêng. Video môi trường sẽ giới thiệu cách bố trí này trước khi chuyển sang demo đầu tiên.

Lệnh cài đặt và vận hành nằm trong [hướng dẫn môi trường](../linux/commands.md). Thời lượng phần mở đầu, gồm video môi trường, được bố trí trong [ghi chú trình bày](../docs/presentation-notes/01-overview-environment.md).

## Nguồn tham khảo

Đối chiếu ngày 20/10/2026.

- **S1:** [Redis — Get started](https://redis.io/docs/latest/develop/get-started/) và [Redis FAQ](https://redis.io/docs/latest/develop/get-started/faq/).
- **S2:** [Redis — Cache-aside](https://redis.io/docs/latest/develop/use-cases/cache-aside/).
- **S3:** [Redis — Leaderboards](https://redis.io/docs/latest/develop/use-cases/leaderboard/).
