#!/usr/bin/env bash
# ==============================================================================
# Script Reset Redis Instance cho Demo 03: Eviction (Port 6382)
# ==============================================================================

PORT=6382
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=========================================================="
echo " [RESET] Đang chuẩn bị dọn dẹp Redis instance port ${PORT}..."
echo "=========================================================="

# Kiểm tra Redis port 6382 có đang hoạt động không
if ! redis-cli -p ${PORT} ping > /dev/null 2>&1; then
    echo "[!] CẢNH BÁO: Không tìm thấy Redis instance đang chạy trên port ${PORT}."
    echo "[*] Đang thử khởi động Redis với cấu hình redis/redis-eviction.conf..."
    mkdir -p /tmp/redis-seminar/eviction
    redis-server "${PROJECT_ROOT}/redis/redis-eviction.conf" &
    sleep 1
    if ! redis-cli -p ${PORT} ping > /dev/null 2>&1; then
        echo "[LỖI] Không thể kết nối tới port ${PORT}. Vui lòng kiểm tra lại redis-server."
        exit 1
    fi
fi

# Xóa toàn bộ dữ liệu trong instance port 6382
redis-cli -p ${PORT} FLUSHALL > /dev/null 2>&1
# Reset các bộ đếm thống kê nếu cần
redis-cli -p ${PORT} CONFIG RESETSTAT > /dev/null 2>&1

echo "[✓] Đã chạy FLUSHALL và CONFIG RESETSTAT thành công."
echo "----------------------------------------------------------"
echo "THÔNG TIN KIỂM TRA HIỆN TẠI:"
echo " - Ping: $(redis-cli -p ${PORT} ping)"
echo " - Số lượng key hiện tại : $(redis-cli -p ${PORT} DBSIZE)"
echo " - Maxmemory cấu hình    : $(redis-cli -p ${PORT} config get maxmemory | tail -n 1) bytes (~10MB)"
echo " - Maxmemory-policy      : $(redis-cli -p ${PORT} config get maxmemory-policy | tail -n 1)"
echo " - RAM sử dụng ban đầu   : $(redis-cli -p ${PORT} info memory | grep used_memory_human | cut -d: -f2 | tr -d '\r')"
echo " - Evicted keys          : $(redis-cli -p ${PORT} info stats | grep evicted_keys | cut -d: -f2 | tr -d '\r')"
echo "=========================================================="
echo "[READY] Môi trường Demo 03 đã sạch sẽ, sẵn sàng chạy script!"
