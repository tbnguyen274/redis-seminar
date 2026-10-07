# Troubleshooting checklist

## Dịch vụ không khởi động

1. Kiểm tra trạng thái: `sudo systemctl status redis-server`.
2. Đọc log: `sudo journalctl -u redis-server -n 100 --no-pager`.
3. Kiểm tra cú pháp/cấu hình bằng cách chạy `redis-server <config-file>` ở foreground.
4. Kiểm tra port đang được dùng: `sudo ss -lntp | grep 6379`.
5. Kiểm tra quyền ghi của `dir`, file RDB và thư mục AOF.

## Không kết nối được

- Xác nhận đúng host/port và tiến trình đang lắng nghe.
- Kiểm tra `bind`, `protected-mode`, firewall và thông tin xác thực.
- Không public Redis trực tiếp ra Internet. Chỉ mở mạng khi demo yêu cầu và phải giới hạn nguồn truy cập.

## Lỗi ghi dữ liệu

- Đọc `INFO memory` để kiểm tra `used_memory`, `maxmemory` và policy.
- Với `noeviction`, Redis trả lỗi ghi khi hết bộ nhớ; với `allkeys-lru`, theo dõi `evicted_keys` trong `INFO stats`.
- Đọc `INFO persistence` để phát hiện lỗi RDB/AOF và kiểm tra dung lượng đĩa.

## Sau crash test

- Chỉ dùng `kill -9` với instance demo độc lập.
- Khởi động lại bằng đúng config, port và `dir` đã dùng trước sự cố.
- Đếm key, kiểm tra `rdb_last_bgsave_status`, `aof_last_write_status` và lưu kết quả vào báo cáo.
