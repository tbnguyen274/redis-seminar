#!/usr/bin/env bash
# Demo 01 - Redis Data Structures & TTL
# Chạy:   bash demos/01-data-structures/run.sh            (dừng chờ Enter giữa các phần)
#         bash demos/01-data-structures/run.sh --no-pause (chạy liền mạch, dùng khi quay video)
#         bash demos/01-data-structures/run.sh --reset    (chỉ xóa dữ liệu demo rồi thoát)
# Biến môi trường: REDIS_HOST (mặc định 127.0.0.1), REDIS_PORT (mặc định 6383), TTL_SECONDS (mặc định 5)
set -euo pipefail

HOST="${REDIS_HOST:-127.0.0.1}"
PORT="${REDIS_PORT:-6383}"
TTL_SECONDS="${TTL_SECONDS:-5}"
PAUSE=1
RESET_ONLY=0

for arg in "$@"; do
  case "$arg" in
    --no-pause) PAUSE=0 ;;
    --reset)    RESET_ONLY=1 ;;
    -h|--help)  sed -n '2,6p' "$0"; exit 0 ;;
    *) echo "Tham số không hợp lệ: $arg (dùng --help)" >&2; exit 1 ;;
  esac
done

# Màu chỉ dùng in đậm/gạch chân để dễ đọc trên nền sáng (light mode) khi trình chiếu.
if [[ -t 1 ]]; then B=$'\e[1m'; U=$'\e[4m'; N=$'\e[0m'; else B=""; U=""; N=""; fi

cli() { redis-cli -h "$HOST" -p "$PORT" "$@"; }

# In lệnh như đang gõ trong redis-cli, rồi chạy và in kết quả.
# --no-raw giữ định dạng giống redis-cli tương tác: (integer) 5, (nil), 1) "bob"...
r() {
  local shown="" a
  for a in "$@"; do
    if [[ "$a" =~ [[:space:]\"\{\}] ]]; then shown+=" '$a'"; else shown+=" $a"; fi
  done
  printf '%s127.0.0.1:%s>%s%s\n' "$B" "$PORT" "$N" "$shown"
  cli --no-raw "$@" | sed 's/^/    /'
}

section() {
  echo
  echo "${B}${U}== $1 ==${N}"
  if [[ -n "${2:-}" ]]; then echo "   $2"; fi
}

note() { echo "   -> $*"; }

pause() {
  if [[ "$PAUSE" -eq 1 ]]; then
    read -r -p "   [Enter để tiếp tục] " _ </dev/tty || true
  fi
}

# ---------- Kiểm tra an toàn ----------
if ! command -v redis-cli >/dev/null 2>&1; then
  echo "Chưa có redis-cli. Chạy: sudo bash linux/setup.sh" >&2; exit 1
fi
if [[ "$PORT" == "6379" ]]; then
  echo "Từ chối chạy trên port 6379 (instance mặc định) vì demo sẽ FLUSHDB." >&2; exit 1
fi
if ! cli PING >/dev/null 2>&1; then
  echo "Không kết nối được Redis tại $HOST:$PORT." >&2
  echo "Khởi động instance demo: redis-server redis/redis-data-structures.conf" >&2
  exit 1
fi

reset_data() {
  cli FLUSHDB >/dev/null
  echo "Đã xóa dữ liệu demo trên $HOST:$PORT (DBSIZE = $(cli DBSIZE))."
}

if [[ "$RESET_ONLY" -eq 1 ]]; then reset_data; exit 0; fi

START=$(date +%s)
stat() { cli INFO stats | tr -d '\r' | awk -F: -v k="$1" '$1==k {print $2}'; }
EXPIRED_BEFORE=$(stat expired_keys)

section "0. Chuẩn bị" "Kết nối instance demo riêng (port $PORT) và làm sạch dữ liệu cũ"
r PING
printf '%s127.0.0.1:%s>%s INFO server  (lọc version/port)\n' "$B" "$PORT" "$N"
cli INFO server | grep -E '^(redis_version|tcp_port):' | tr -d '\r' | sed 's/^/    /' || true
reset_data
pause

# ---------- 1. String ----------
section "1. STRING - cache và bộ đếm" "Kiểu đơn giản nhất: 1 key -> 1 giá trị (text, số, JSON...), tối đa 512 MB"
r SET cache:product:1001 '{"id":1001,"name":"Ban phim co","price":890000}' EX 60
r GET cache:product:1001
r TTL cache:product:1001
note "SET ... EX 60: ghi cache và gán TTL 60 giây trong CÙNG MỘT lệnh (nguyên tử)."
r INCR stats:page:home:views
r INCR stats:page:home:views
r INCRBY stats:page:home:views 10
r GET stats:page:home:views
note "INCR là thao tác nguyên tử: 1000 client cùng tăng cũng không bị mất lượt đếm."
pause

# ---------- 2. List ----------
section "2. LIST - hàng đợi công việc (queue)" "Danh sách có thứ tự CHÈN; thêm/lấy ở 2 đầu O(1)"
r RPUSH queue:emails "job:1 gui mail chao mung" "job:2 gui OTP" "job:3 gui hoa don"
r LRANGE queue:emails 0 -1
r LLEN queue:emails
note "Worker lấy việc từ đầu kia (FIFO: RPUSH vào cuối, LPOP ra ở đầu):"
r LPOP queue:emails
r LRANGE queue:emails 0 -1
note "Thực tế worker dùng BLPOP để chờ (block) đến khi có việc mới, không phải hỏi liên tục."
pause

# ---------- 3. Hash ----------
section "3. HASH - lưu thông tin user" "1 key chứa nhiều cặp field -> value, giống một object/row"
r HSET user:1001 name "Viet Toan" email "toan@example.com" role "member" login_count 0
r HGET user:1001 email
r HINCRBY user:1001 login_count 1
r HSET user:1001 role "admin"
r HGETALL user:1001
note "Sửa 1 field không cần đọc - ghi lại cả object như khi lưu JSON trong String."
pause

# ---------- 4. Sorted Set ----------
section "4. SORTED SET - bảng xếp hạng (leaderboard)" "Mỗi member có 1 score; Redis luôn giữ thứ tự theo score, member không trùng"
r ZADD leaderboard:game 1500 alice 2300 bob 1800 carol 900 dave 2100 eve
r ZREVRANGE leaderboard:game 0 2 WITHSCORES
note "carol thắng thêm một trận, được cộng 600 điểm:"
r ZINCRBY leaderboard:game 600 carol
r ZREVRANGE leaderboard:game 0 2 WITHSCORES
r ZREVRANK leaderboard:game carol
note "ZREVRANK đếm từ 0 -> carol đang hạng $(( $(cli ZREVRANK leaderboard:game carol) + 1 ))."
r ZSCORE leaderboard:game carol
r ZRANGEBYSCORE leaderboard:game 1000 2000 WITHSCORES
note "ZADD lại member đã có chỉ cập nhật score, không tạo bản trùng:"
r ZADD leaderboard:game 1000 dave
r ZCARD leaderboard:game
pause

# ---------- 5. List vs Sorted Set ----------
section "5. So sánh nhanh LIST và SORTED SET" "Cùng dữ liệu điểm số, hai cách lưu cho kết quả khác nhau"
r RPUSH compare:list 1500 2300 1800 2300
r LRANGE compare:list 0 -1
r ZADD compare:zset 1500 alice 2300 bob 1800 carol 2300 bob
r ZREVRANGE compare:zset 0 -1 WITHSCORES
note "LIST: giữ thứ tự chèn, cho phép trùng -> hợp với queue, lịch sử, timeline."
note "SORTED SET: tự sắp theo score, member duy nhất -> hợp với xếp hạng, ưu tiên, lịch hẹn giờ."
pause

# ---------- 6. TTL ----------
section "6. TTL - thời gian sống của key" "Redis tự xóa key khi hết hạn"
r SET session:abc123 "user:1001" EX "$TTL_SECONDS"
r TTL session:abc123
note "Key không có hạn sử dụng -> TTL trả về -1:"
r TTL user:1001
note "Gán TTL cho key ĐÃ tồn tại bằng EXPIRE:"
r EXPIRE user:1001 300
r TTL user:1001
note "Bỏ TTL, key thành vĩnh viễn trở lại bằng PERSIST:"
r PERSIST user:1001
r TTL user:1001
note "Bẫy hay gặp: SET lại giá trị sẽ XÓA TTL cũ (trừ khi thêm KEEPTTL):"
r SET cache:product:1001 '{"id":1001,"price":850000}'
r TTL cache:product:1001
r EXPIRE cache:product:1001 60
r SET cache:product:1001 '{"id":1001,"price":800000}' KEEPTTL
r TTL cache:product:1001
pause

section "7. Chờ session:abc123 hết hạn" "Quan sát TTL giảm dần rồi key biến mất"
while :; do
  t=$(cli TTL session:abc123)
  printf '   TTL session:abc123 = %s\n' "$t"
  [[ "$t" -lt 0 ]] && break
  sleep 1
done
r GET session:abc123
r TTL session:abc123
r EXISTS session:abc123
note "-2 nghĩa là key KHÔNG tồn tại (đã hết hạn hoặc chưa từng có); GET trả về (nil)."
pause

# ---------- Tổng kết ----------
section "8. Tổng kết" "Các key còn lại và kiểu dữ liệu của chúng"
for k in $(cli --scan | sort); do
  printf '   %-28s %-6s TTL=%s\n' "$k" "$(cli TYPE "$k")" "$(cli TTL "$k")"
done
r DBSIZE
printf '%s127.0.0.1:%s>%s INFO stats  (lọc expired_keys / evicted_keys)\n' "$B" "$PORT" "$N"
cli INFO stats | grep -E '^(expired_keys|evicted_keys):' | tr -d '\r' | sed 's/^/    /' || true
note "Lần chạy này có $(( $(stat expired_keys) - EXPIRED_BEFORE )) key bị xóa do HẾT TTL (expired), 0 key bị loại do THIẾU RAM (evicted, xem Demo 03)."
END=$(date +%s)
echo
echo "${B}Hoàn thành demo trong $((END - START)) giây.${N} Chạy lại từ đầu: bash demos/01-data-structures/run.sh"
echo "Chỉ dọn dữ liệu: bash demos/01-data-structures/run.sh --reset"
