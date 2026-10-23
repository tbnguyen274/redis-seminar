#!/usr/bin/env bash
# ==============================================================================
# Script khởi chạy Demo 03: Eviction (Port 6382)
# ==============================================================================

set -e

PORT=6382
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/../.." && pwd)"

echo "=========================================================="
echo "    KHỞI CHẠY DEMO 03: REDIS MEMORY & EVICTION"
echo "=========================================================="

# 1. Kiểm tra môi trường thư mục tạm
mkdir -p /tmp/redis-seminar/eviction

# 2. Kiểm tra Redis server trên port 6382
if ! redis-cli -p ${PORT} ping > /dev/null 2>&1; then
    echo "[*] Đang khởi động Redis instance trên port ${PORT}..."
    redis-server "${PROJECT_ROOT}/redis/redis-eviction.conf" &
    sleep 1
    if ! redis-cli -p ${PORT} ping > /dev/null 2>&1; then
        echo "[LỖI] Không thể khởi động Redis port ${PORT}. Vui lòng kiểm tra lại cấu hình."
        exit 1
    fi
    echo "[✓] Redis instance port ${PORT} đã sẵn sàng."
fi

# 3. Dọn dẹp dữ liệu cũ
echo "[*] Đang chạy reset.sh để dọn sạch dữ liệu trước khi chạy..."
bash "${SCRIPT_DIR}/reset.sh"

# 4. Kiểm tra thư viện python redis
if ! python3 -c "import redis" > /dev/null 2>&1; then
    echo "[*] Đang cài đặt thư viện redis cho Python..."
    if command -v pip3 > /dev/null 2>&1; then
        pip3 install -r "${SCRIPT_DIR}/requirements.txt" 2>/dev/null || \
        pip3 install --break-system-packages -r "${SCRIPT_DIR}/requirements.txt" 2>/dev/null || \
        pip3 install --user -r "${SCRIPT_DIR}/requirements.txt" 2>/dev/null || true
    elif command -v pip > /dev/null 2>&1; then
        pip install -r "${SCRIPT_DIR}/requirements.txt" 2>/dev/null || \
        pip install --break-system-packages -r "${SCRIPT_DIR}/requirements.txt" 2>/dev/null || true
    fi
fi

if ! python3 -c "import redis" > /dev/null 2>&1; then
    echo "[LỖI] Chưa cài đặt được thư viện 'redis' cho Python."
    echo "Vui lòng chạy: sudo apt install -y python3-redis"
    exit 1
fi

# 5. Chạy kịch bản chính
echo ""
echo "[*] Bắt đầu thực thi script fill_memory.py..."
python3 "${SCRIPT_DIR}/fill_memory.py"

echo ""
echo "=========================================================="
echo " [HOÀN TẤT] Demo 03 đã thực thi xong thành công."
echo "=========================================================="
