## Todos:

- [ ] Complete the theory

- [ ] Write app.py for demo

- [ ] Emulate:
  - [ ] Low speed database
  - [ ] Đọc Redis trước
  - [ ] Khi miss thì đọc database giả lập, ghi cache có TTL và trả dữ liệu
  - [ ] Khi hit thì trả trực tiếp
  - [ ] Dùng bộ đếm thời gian
  - [ ] Thêm lệnh xóa cache và chạy nhiều lần để lấy kết quả ổn định

## Cache-Aside

### Concepts

- Cache Hit
- Cache Miss
- Cache-Aside
- TTL
- cache invalidation
- các rủi ro cache

### Explanations

- Vẽ và giải thích luồng Cache-Aside
- phân tích thời điểm đọc Redis và database
- giải thích vì sao cần TTL
- nêu vấn đề stale data
- giới thiệu cache penetration và cache stampede
- trình bày cách đo hiệu quả cache
