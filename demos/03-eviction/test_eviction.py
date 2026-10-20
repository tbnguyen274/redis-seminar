#!/usr/bin/env python3
"""
==============================================================================
Test Suite: Kiểm thử tự động Demo 03 (Redis Memory & allkeys-lru Eviction)
==============================================================================
"""

import sys
import time
import redis

# ANSI Colors
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REDIS_PORT = 6382
EXPECTED_MAXMEMORY = 10 * 1024 * 1024  # 10MB = 10485760 bytes
EXPECTED_POLICY = "allkeys-lru"

passed_tests = 0
failed_tests = 0

def log_test(test_name, passed, detail=""):
    global passed_tests, failed_tests
    if passed:
        passed_tests += 1
        print(f"  [{GREEN}PASS{RESET}] {test_name} {CYAN}{detail}{RESET}")
    else:
        failed_tests += 1
        print(f"  [{RED}FAIL{RESET}] {test_name} - {RED}{detail}{RESET}")

def main():
    print("\n" + "=" * 65)
    print(f" {BOLD}KIỂM THỬ TỰ ĐỘNG DEMO 03 (PORT {REDIS_PORT}){RESET}")
    print("=" * 65)

    # 1. Test kết nối
    try:
        r = redis.Redis(host="127.0.0.1", port=REDIS_PORT, decode_responses=True)
        r.ping()
        log_test("Test 1: Kết nối Redis port 6382", True, "PONG thành công")
    except Exception as e:
        log_test("Test 1: Kết nối Redis port 6382", False, f"Không thể kết nối ({e})")
        print(f"\n{RED}[DỪNG]{RESET} Hãy khởi động Redis trước: redis-server redis/redis-eviction.conf &\n")
        sys.exit(1)

    # 2. Test cấu hình maxmemory
    cfg_maxmem = int(r.config_get("maxmemory").get("maxmemory", 0))
    is_maxmem_ok = (cfg_maxmem == EXPECTED_MAXMEMORY)
    log_test("Test 2: Kiểm tra cấu hình maxmemory 10MB", is_maxmem_ok, f"Thực tế: {cfg_maxmem} bytes")

    # 3. Test cấu hình maxmemory-policy
    cfg_policy = r.config_get("maxmemory-policy").get("maxmemory-policy", "")
    is_policy_ok = (cfg_policy.lower() == EXPECTED_POLICY)
    log_test("Test 3: Kiểm tra cấu hình policy allkeys-lru", is_policy_ok, f"Thực tế: {cfg_policy}")

    # 4. Test dọn dẹp ban đầu
    r.flushall()
    r.config_resetstat()
    dbsize_initial = r.dbsize()
    log_test("Test 4: Reset DB sạch sẽ (FLUSHALL)", dbsize_initial == 0, f"Số key ban đầu: {dbsize_initial}")

    # 5. Test ghi nhận Cold keys và Hot keys
    print(f"\n[*] Đang khởi tạo 10 Cold Keys...")
    cold_payload = "C" * (50 * 1024)  # 50KB payload
    for i in range(1, 11):
        r.set(f"test_cold_{i}", cold_payload)

    # Chờ 3 giây để Redis LRU clock (độ phân giải 1s) ghi nhận idle time thực tế cho Cold Keys
    print("[*] Tạm dừng 3 giây để LRU clock ghi nhận idle time cho Cold Keys...")
    time.sleep(3)

    print("[*] Đang khởi tạo 5 Hot Keys...")
    hot_payload = "H" * (50 * 1024)   # 50KB payload
    for i in range(1, 6):
        r.set(f"test_hot_{i}", hot_payload)
    
    total_keys = r.dbsize()
    log_test("Test 5: Tạo 15 keys đối chứng", total_keys == 15, f"Tổng keys: {total_keys}/15")

    # 6. Test cơ chế Eviction khi bơm dữ liệu lớn
    print(f"\n[*] Đang bơm dữ liệu mô phỏng (~100KB/key) để kích hoạt Eviction...")
    payload = "T" * (100 * 1024)
    batch = 0
    eviction_triggered = False

    while batch < 200:
        batch += 1
        # Cập nhật LRU cho 5 Hot Keys trước và sau khi ghi filler
        for h in range(1, 6):
            _ = r.get(f"test_hot_{h}")

        r.set(f"test_filler_{batch}", payload)

        for h in range(1, 6):
            _ = r.get(f"test_hot_{h}")

        if batch % 5 == 0:
            evicted = int(r.info("stats").get("evicted_keys", 0))
            if evicted >= 15:
                eviction_triggered = True
                break

    log_test("Test 6: Kích hoạt thành công Eviction (evicted_keys >= 15)", eviction_triggered, 
             f"Đã trục xuất {r.info('stats').get('evicted_keys', 0)} keys")

    # 7. Test kiểm tra Cold Keys bị xóa
    cold_evicted_count = 0
    for i in range(1, 11):
        if not r.exists(f"test_cold_{i}"):
            cold_evicted_count += 1
    
    # Do đặc tính lấy mẫu xấp xỉ (samples=5), tối thiểu 8/10 Cold Keys bị xóa
    is_cold_evicted = (cold_evicted_count >= 8)
    log_test("Test 7: Cold Keys ít dùng bị trục xuất", is_cold_evicted, 
             f"Đã bị evict: {cold_evicted_count}/10 keys")

    # 8. Test kiểm tra Hot Keys được bảo toàn
    hot_survived_count = 0
    for i in range(1, 6):
        if r.exists(f"test_hot_{i}"):
            hot_survived_count += 1

    # Tối thiểu 4/5 hoặc 5/5 Hot Keys sống sót
    is_hot_survived = (hot_survived_count >= 4)
    log_test("Test 8: Hot Keys đọc liên tục được giữ lại", is_hot_survived, 
             f"Còn sống: {hot_survived_count}/5 keys")

    # 9. Test kiểm tra giới hạn RAM không bị vượt quá
    used_mem_bytes = int(r.info("memory").get("used_memory", 0))
    # RAM có thể vượt nhẹ một vài % do memory overhead tạm thời nhưng không được vượt quá 10.8MB
    is_ram_capped = used_mem_bytes <= (EXPECTED_MAXMEMORY * 1.08)
    used_human = r.info("memory").get("used_memory_human", "0M")
    log_test("Test 9: Giới hạn RAM được kiểm soát quanh 10MB", is_ram_capped, 
             f"RAM thực tế: {used_human}")

    # TỔNG KẾT
    print("\n" + "=" * 65)
    if failed_tests == 0:
        print(f" {GREEN}{BOLD}KẾT QUẢ: TẤT CẢ {passed_tests}/9 BÀI KIỂM THỬ ĐÃ ĐẠT (PASS)!{RESET}")
        print(f" {GREEN}Hệ thống đã sẵn sàng 100% để bạn quay video demo.{RESET}")
    else:
        print(f" {RED}{BOLD}KẾT QUẢ: CÓ {failed_tests} BÀI KIỂM THỬ THẤT BẠI (FAIL).{RESET}")
        print(f" Vui lòng kiểm tra lại log lỗi ở trên.")
    print("=" * 65 + "\n")

    sys.exit(0 if failed_tests == 0 else 1)

if __name__ == "__main__":
    main()
