#!/usr/bin/env bash
# ==============================================================================
# Script kiểm thử tự động Demo 03: Memory & Eviction (Port 6382)
# Cách dùng: bash test/test_demo_03.sh
# ==============================================================================

set -e

PORT=6382
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${PROJECT_ROOT}"

echo "=========================================================="
echo "    BẮT ĐẦU KIỂM THỬ TỰ ĐỘNG DEMO 03: MEMORY & EVICTION"
echo "=========================================================="

# 1. Kiểm tra môi trường hệ điều hành
echo "[1/4] Kiểm tra công cụ cần thiết..."
if ! command -v redis-server &> /dev/null; then
    echo "[LỖI] Chưa tìm thấy 'redis-server'. Vui lòng chạy: sudo apt install -y redis-server"
    exit 1
fi

if ! command -v redis-cli &> /dev/null; then
    echo "[LỖI] Chưa tìm thấy 'redis-cli'. Vui lòng chạy: sudo apt install -y redis-tools"
    exit 1
fi

if ! command -v redis-benchmark &> /dev/null; then
    echo "[LỖI] Chưa tìm thấy 'redis-benchmark'. Vui lòng chạy: sudo apt install -y redis-tools"
    exit 1
fi

if ! command -v python3 &> /dev/null; then
    echo "[LỖI] Chưa tìm thấy 'python3'. Vui lòng chạy: sudo apt install -y python3 python3-pip python3-redis"
    exit 1
fi
echo "[✓] Các công cụ cần thiết đã sẵn sàng."

# 2. Khởi tạo thư mục tạm và khởi động Redis instance 6382 nếu chưa chạy
echo "[2/4] Kiểm tra tiến trình Redis trên port ${PORT}..."
mkdir -p /tmp/redis-seminar/eviction

if ! redis-cli -p ${PORT} ping &> /dev/null; then
    echo " -> Đang khởi động Redis port ${PORT} với cấu hình redis/redis-eviction.conf..."
    redis-server "${PROJECT_ROOT}/redis/redis-eviction.conf" &
    sleep 1
    if ! redis-cli -p ${PORT} ping &> /dev/null; then
        echo "[LỖI] Không thể khởi động Redis port ${PORT}."
        exit 1
    fi
fi
echo "[✓] Redis port ${PORT} đang hoạt động bình thường (PONG)."

# 3. Kiểm tra dependency python
echo "[3/4] Kiểm tra thư viện Python (redis)..."
if ! python3 -c "import redis" &> /dev/null; then
    echo " -> Chưa tìm thấy thư viện 'redis'. Đang thử cài đặt qua pip..."
    if command -v pip3 &> /dev/null; then
        pip3 install -r "${PROJECT_ROOT}/demos/03-eviction/requirements.txt" 2>/dev/null || \
        pip3 install --break-system-packages -r "${PROJECT_ROOT}/demos/03-eviction/requirements.txt" 2>/dev/null || \
        pip3 install --user -r "${PROJECT_ROOT}/demos/03-eviction/requirements.txt" 2>/dev/null || true
    elif command -v pip &> /dev/null; then
        pip install -r "${PROJECT_ROOT}/demos/03-eviction/requirements.txt" 2>/dev/null || \
        pip install --break-system-packages -r "${PROJECT_ROOT}/demos/03-eviction/requirements.txt" 2>/dev/null || true
    fi
fi

if ! python3 -c "import redis" &> /dev/null; then
    echo "[LỖI] Chưa cài đặt được thư viện 'redis' cho Python."
    echo "Vui lòng chạy lệnh cài đặt trên Linux Mint:"
    echo "    sudo apt install -y python3-redis"
    echo "hoặc:"
    echo "    pip3 install -r demos/03-eviction/requirements.txt"
    exit 1
fi
echo "[✓] Thư viện Python đã sẵn sàng."

# 4. Chạy bộ kiểm thử tự động
echo "[4/4] Đang thực thi bộ kiểm thử test_eviction.py..."
python3 "${PROJECT_ROOT}/demos/03-eviction/test_eviction.py"

echo "=========================================================="
echo " [HOÀN TẤT] Bạn có thể quay video demo bất kỳ lúc nào!"
echo "=========================================================="
