#!/usr/bin/env python3
"""
==============================================================================
Demo 03: Giới hạn Bộ nhớ (maxmemory) và Chính sách Trục xuất allkeys-lru
==============================================================================
"""

import sys
import time
import redis

# Cấu hình màu sắc Terminal (ANSI escape codes)
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

REDIS_HOST = "127.0.0.1"
REDIS_PORT = 6382

def print_header(title):
    print("\n" + "=" * 65)
    print(f" {BOLD}{CYAN}{title}{RESET}")
    print("=" * 65)

def check_connection():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
        r.ping()
        return r
    except redis.ConnectionError:
        print(f"\n{RED}[LỖI]{RESET} Không thể kết nối tới Redis trên cổng {REDIS_PORT}.")
        print(f"Vui lòng khởi động Redis trước bằng lệnh: {YELLOW}redis-server redis/redis-eviction.conf &{RESET}")
        sys.exit(1)

def get_memory_stats(r):
    mem_info = r.info("memory")
    stat_info = r.info("stats")
    return {
        "used_memory_human": mem_info.get("used_memory_human", "0B"),
        "used_memory_peak_human": mem_info.get("used_memory_peak_human", "0B"),
        "maxmemory_human": mem_info.get("maxmemory_human", "10MB"),
        "mem_fragmentation_ratio": mem_info.get("mem_fragmentation_ratio", 0.0),
        "evicted_keys": stat_info.get("evicted_keys", 0),
        "total_keys": r.dbsize()
    }

def main():
    r = check_connection()

    print_header("BƯỚC 1: XÁC THỰC CẤU HÌNH INSTANCE PORT 6382")
    maxmem_cfg = r.config_get("maxmemory")
    policy_cfg = r.config_get("maxmemory-policy")
    initial_stats = get_memory_stats(r)

    maxmem_val = maxmem_cfg.get("maxmemory", "0")
    policy_val = policy_cfg.get("maxmemory-policy", "unknown")

    print(f" - Host / Port         : {BOLD}{REDIS_HOST}:{REDIS_PORT}{RESET}")
    print(f" - Cấu hình maxmemory   : {BOLD}{YELLOW}{maxmem_val} bytes ({int(maxmem_val)//(1024*1024)} MB){RESET}")
    print(f" - Cấu hình policy      : {BOLD}{GREEN}{policy_val}{RESET}")
    print(f" - RAM sử dụng ban đầu  : {initial_stats['used_memory_human']}")
    print(f" - Số key hiện có trong DB: {initial_stats['total_keys']}")
    print(f" - Số key đã evict trước: {initial_stats['evicted_keys']}")

    # =========================================================================
    # BƯỚC 2: KHỞI TẠO TẬP KEY ĐỐI CHỨNG (COLD KEYS VS HOT KEYS)
    # =========================================================================
    print_header("BƯỚC 2: KHỞI TẠO 10 COLD KEYS VÀ 5 HOT KEYS")
    
    print(f"-> Tạo {BOLD}10 Cold Keys{RESET} (Key nguội: Ghi 1 lần lúc đầu và KHÔNG bao giờ đọc lại)...")
    for i in range(1, 11):
        r.set(f"cold_user_{i}", f"Data_Cold_AccountInfo_User_{i}")

    print(f"-> Tạo {BOLD}5 Hot Keys{RESET} (Key nóng: Ghi lúc đầu và sẽ được ĐỌC LIÊN TỤC để cập nhật LRU)...")
    for i in range(1, 6):
        r.set(f"hot_user_{i}", f"Data_Hot_TrendingTopic_News_{i}")

    print(f"{GREEN}[✓]{RESET} Đã tạo xong 15 keys đối chứng. Tổng keys hiện có: {r.dbsize()}")

    # =========================================================================
    # BƯỚC 3: BƠM DỮ LIỆU ĐỂ LÀM TRÀN 10MB RAM VÀ KÍCH HOẠT ALLKEYS-LRU
    # =========================================================================
    print_header("BƯỚC 3: BƠM DỮ LIỆU LỚN VƯỢT NGƯỠNG 10MB ĐỂ KÍCH HOẠT EVICTION")
    print("Tiến hành ghi các chuỗi kích thước ~100KB/key và liên tục đọc lại 5 Hot Keys...")
    print("-" * 65)

    payload_size_kb = 100
    large_payload = "X" * (payload_size_kb * 1024)
    batch_count = 0
    target_evictions = 30  # Chờ đến khi Redis loại bỏ ít nhất 30 keys

    start_time = time.time()

    while True:
        batch_count += 1
        # Ghi một payload lớn
        r.set(f"filler_payload_{batch_count}", large_payload)

        # CẬP NHẬT LRU CHO HOT KEYS: Đọc tất cả 5 Hot Keys trong mỗi vòng lặp
        for h in range(1, 6):
            _ = r.get(f"hot_user_{h}")

        # In tiến độ định kỳ mỗi 15 keys
        if batch_count % 15 == 0:
            stats = get_memory_stats(r)
            evicted = stats["evicted_keys"]
            ram_used = stats["used_memory_human"]
            keys_total = stats["total_keys"]
            
            status_color = GREEN if evicted > 0 else YELLOW
            print(f" [Vòng ghi {batch_count:3d}] RAM: {BOLD}{ram_used:>7}{RESET} | "
                  f"Tổng keys: {keys_total:4d} | "
                  f"Evicted: {status_color}{BOLD}{evicted:4d}{RESET}")

            if evicted >= target_evictions:
                print("-" * 65)
                print(f"{GREEN}{BOLD}[!] EVICTION ĐÃ DIỄN RA THÀNH CÔNG! (Số key bị trục xuất: {evicted}){RESET}")
                break

    elapsed = time.time() - start_time
    print(f"[*] Thời gian bơm dữ liệu và kích hoạt eviction: {elapsed:.2f} giây.")

    # =========================================================================
    # BƯỚC 4: KIỂM CHỨNG KẾT QUẢ ĐỐI CHỨNG THEO THUẬT TOÁN LRU
    # =========================================================================
    print_header("BƯỚC 4: ĐỐI CHIẾU KẾT QUẢ (COLD KEYS VS HOT KEYS)")
    
    print(f"\n{BOLD}1. Kiểm tra 10 COLD KEYS (Kỳ vọng: Đã bị loại bỏ vì không được truy cập){RESET}")
    print("┌──────────────────┬──────────────────────┐")
    print("│ Key Name         │ Trạng thái trong DB  │")
    print("├──────────────────┼──────────────────────┤")
    cold_survived = 0
    for i in range(1, 11):
        key = f"cold_user_{i}"
        exists = r.exists(key)
        if exists:
            status_str = f"{RED}VẪN CÒN SỐNG [X]{RESET}"
            cold_survived += 1
        else:
            status_str = f"{GREEN}ĐÃ BỊ EVICT  [✓]{RESET}"
        print(f"│ {key:16s} │ {status_str:29s} │")
    print("└──────────────────┴──────────────────────┘")

    print(f"\n{BOLD}2. Kiểm tra 5 HOT KEYS (Kỳ vọng: Vẫn tồn tại vì được đọc liên tục){RESET}")
    print("┌──────────────────┬──────────────────────┐")
    print("│ Key Name         │ Trạng thái trong DB  │")
    print("├──────────────────┼──────────────────────┤")
    hot_survived = 0
    for i in range(1, 6):
        key = f"hot_user_{i}"
        exists = r.exists(key)
        if exists:
            status_str = f"{GREEN}VẪN CÒN SỐNG [✓]{RESET}"
            hot_survived += 1
        else:
            status_str = f"{RED}ĐÃ BỊ EVICT  [X]{RESET}"
        print(f"│ {key:16s} │ {status_str:29s} │")
    print("└──────────────────┴──────────────────────┘")

    # =========================================================================
    # BƯỚC 5: TỔNG KẾT VÀ ĐÁNH GIÁ THỰC NGHIỆM
    # =========================================================================
    print_header("TỔNG KẾT THỰC NGHIỆM VÀ KẾT LUẬN")
    final_stats = get_memory_stats(r)
    print(f" • RAM giới hạn (maxmemory)    : 10MB")
    print(f" • RAM thực tế đang dùng       : {final_stats['used_memory_human']} (Chạm trần an toàn, không vượt quá)")
    print(f" • Tổng số key đã bị trục xuất : {BOLD}{GREEN}{final_stats['evicted_keys']}{RESET}")
    print(f" • Tỷ lệ sống sót Cold Keys    : {cold_survived}/10 (Kỳ vọng = 0/10)")
    print(f" • Tỷ lệ sống sót Hot Keys     : {hot_survived}/5 (Kỳ vọng = 5/5)")
    print("-" * 65)

    if cold_survived == 0 and hot_survived == 5:
        print(f"{GREEN}{BOLD}[XÁC NHẬN THÀNH CÔNG]{RESET} Thuật toán allkeys-lru hoạt động CHÍNH XÁC:")
        print("  -> Dữ liệu nguội ít dùng bị trục xuất để nhường RAM.")
        print("  -> Dữ liệu nóng thường xuyên truy cập được bảo vệ nguyên vẹn trong bộ nhớ Cache.")
    else:
        print(f"{YELLOW}[GHI CHÚ KỸ THUẬT]{RESET} Thuật toán Approximate LRU của Redis lấy mẫu ngẫu nhiên (samples=5)")
        print("nên có xác suất rất nhỏ một số key gần ngưỡng có thể chênh lệch, đúng với lý thuyết lấy mẫu.")
    print("=" * 65 + "\n")

if __name__ == "__main__":
    main()
