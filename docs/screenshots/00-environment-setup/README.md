# 00 — Setup môi trường chung

Thư mục này lưu **minh chứng của giai đoạn chuẩn bị và kiểm tra môi trường Redis**: settings VM, cài đặt, service, cấu hình/port, cách ly, thời hạn key và normal restart. Đây không phải kết quả đầy đủ của bốn demo chuyên đề.

```text
00-environment-setup/
├── README.md                    # Chỉ mục minh chứng setup
├── vmware-2026-10-20/            # Lần setup/kiểm tra trên VMware
│   ├── README.md                # Giải thích từng ảnh và mốc recording
│   ├── screenshots/             # 01 settings → 08 normal restart
│   ├── logs/                    # Setup, checker và session lệnh/output
│   ├── original-logs.tar.gz      # Archive gốc
│   ├── source-manifest.json      # Nguồn và SHA256
│   └── video-metadata.json
└── wsl-rehearsal.txt             # Lần rehearsal WSL trước VMware
```

- Chạy lại demo setup: [lệnh và giải thích từng bước](../../../linux/environment-demo.md).
- Xem ảnh/log VMware và mốc video: [VMware 20/10/2026](vmware-2026-10-20/README.md).
- Xem kết luận và phạm vi đã kiểm tra: [environment-verification.md](../../environment-verification.md).

Tên cũ của thư mục là `00-environment`; đổi thành `00-environment-setup` để thấy rõ giai đoạn setup ngay trong cây thư mục. Nội dung ảnh và log gốc được giữ nguyên.
