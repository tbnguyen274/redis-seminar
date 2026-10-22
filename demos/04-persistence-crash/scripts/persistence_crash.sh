#!/usr/bin/env bash
# Interactive Linux/Redis lesson, not an ACK-to-crash timing benchmark.
set -euo pipefail

auto=false
case "${1:-}" in
  --auto) auto=true ;;
  --help|-h)
    printf 'Usage: bash teach_crash.sh [--auto]\nPause at each lesson step; --auto skips pauses. Requires Bash 4+, Linux, Redis 7+.\n'
    exit 0 ;;
  '') ;;
  *) printf 'Unknown option: %s\n' "$1" >&2; exit 2 ;;
esac
[[ $# -le 1 ]] || { printf 'Too many arguments\n' >&2; exit 2; }
(( BASH_VERSINFO[0] >= 4 )) || { printf 'Bash 4+ required.\n' >&2; exit 1; }
[[ $OSTYPE == linux* && -r /proc/self/stat ]] || { printf 'Run in Linux/WSL Bash.\n' >&2; exit 1; }
if ! "$auto" && [[ ! -t 0 ]]; then
  printf 'Interactive mode needs a terminal. Use --auto to skip pauses.\n' >&2
  exit 1
fi
for tool in redis-server redis-cli ss awk tr mktemp tee ps timeout; do
  command -v "$tool" >/dev/null || { printf 'Missing command: %s\n' "$tool" >&2; exit 1; }
done
version=$(redis-server --version)
[[ $version =~ v=([0-9]+)\. && ${BASH_REMATCH[1]} -ge 7 ]] || { printf 'Redis 7+ required.\n' >&2; exit 1; }
for port in 6380 6381; do
  if [[ -n $(ss -H -ltn "sport = :$port") ]]; then
    printf 'Port %s is occupied; stop your own demo first.\n' "$port" >&2
    exit 1
  fi
done

script_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
demo_dir=$(cd -- "$script_dir/.." && pwd)
repo_dir=$(cd -- "$demo_dir/../.." && pwd)
mkdir -p -- "$demo_dir/results"
run_dir=$(mktemp -d "$demo_dir/results/lesson-$(date -u +%Y%m%d-%H%M%SZ)-XXXXXX")
exec > >(tee "$run_dir/lesson.log") 2>&1
declare -A ports=([rdb]=6380 [aof]=6381) pids=() births=() attempted=()
baseline=3
delta=2

show() { printf '\n$'; printf ' %q' "$@"; printf '\n'; "$@"; }
rcli() { timeout 5 redis-cli --raw -e -h 127.0.0.1 -p "$@"; }
field() { rcli "$1" INFO "$2" | tr -d '\r' | awk -F: -v key="$3" '$1 == key {print $2}'; }
step() {
  printf '\n========== %s ==========\n%s\n' "$1" "$2"
  if ! "$auto"; then
    read -r -p 'Nhan Enter de thuc hien buoc nay (Ctrl+C de dung): ' || exit 1
  fi
}
start_tick() {
  local stat rest
  IFS= read -r stat < "/proc/$1/stat" || return 1
  rest=${stat##*) }
  local -a fields
  read -r -a fields <<< "$rest"
  printf '%s\n' "${fields[19]}"
}
# Check INFO, runtime config, pidfile and Linux process identity before signals.
owned_pid() {
  local mode=$1 pid config comm
  pid=$(field "${ports[$mode]}" server process_id) || return 1
  [[ $pid =~ ^[0-9]+$ && $pid -gt 1 ]] || return 1
  [[ -f $run_dir/$mode/redis.pid ]] || return 1
  [[ $(< "$run_dir/$mode/redis.pid") == "$pid" ]] || return 1
  config=$(field "${ports[$mode]}" server config_file) || return 1
  [[ $config == "$run_dir/$mode/$mode.conf" ]] || return 1
  IFS= read -r comm < "/proc/$pid/comm" || return 1
  [[ $comm == redis-server* ]] || return 1
  if [[ -n ${pids[$mode]:-} ]]; then
    [[ $pid == "${pids[$mode]}" && $(start_tick "$pid") == "${births[$mode]:-}" ]] || return 1
  fi
  printf '%s\n' "$pid"
}
cleanup() {
  local status=$1 mode
  trap - EXIT
  set +e
  for mode in rdb aof; do
    if [[ -n ${attempted[$mode]:-} ]] && owned_pid "$mode" >/dev/null 2>&1; then
      printf '\nCleanup: redis-cli -p %s SHUTDOWN NOSAVE (sau phep thu).\n' "${ports[$mode]}"
      rcli "${ports[$mode]}" SHUTDOWN NOSAVE
    fi
  done
  printf '\nTai lieu va ket qua: %s\n' "$run_dir"
  exit "$status"
}
trap 'cleanup "$?"' EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

conf_path() {
  local value=$1
  value=${value//\\/\\\\}
  value=${value//\"/\\\"}
  printf '%s' "$value"
}
render_config() {
  local mode=$1 line
  mkdir -p -- "$run_dir/$mode/data"
  while IFS= read -r line || [[ -n $line ]]; do
    case "$line" in
      'pidfile @PID_FILE@') printf 'pidfile "%s"\n' "$(conf_path "$run_dir/$mode/redis.pid")" ;;
      'logfile @LOG_FILE@') printf 'logfile "%s"\n' "$(conf_path "$run_dir/$mode/redis.log")" ;;
      'dir @DATA_DIR@') printf 'dir "%s"\n' "$(conf_path "$run_dir/$mode/data")" ;;
      *) printf '%s\n' "$line" ;;
    esac
  done < "$repo_dir/redis/redis-$mode.conf" > "$run_dir/$mode/$mode.conf"
}
start_instance() {
  local mode=$1 attempt pid
  attempted[$mode]=1
  show redis-server "$run_dir/$mode/$mode.conf"
  for ((attempt=0; attempt<100; attempt++)); do
    if pid=$(owned_pid "$mode" 2>/dev/null); then
      pids[$mode]=$pid
      births[$mode]=$(start_tick "$pid")
      show redis-cli -p "${ports[$mode]}" PING
      show ps -p "$pid" -o pid,comm,args
      return
    fi
    sleep 0.1
  done
  printf 'Startup failed: inspect %s/%s/redis.log\n' "$run_dir" "$mode" >&2
  return 1
}
write_group() {
  local group=$1 count=$2 mode i reply
  for mode in rdb aof; do
    for ((i=1; i<=count; i++)); do
      printf '\n$ redis-cli -p %s SET lesson:%s:%s %s-%s\n' "${ports[$mode]}" "$group" "$i" "$group" "$i"
      reply=$(rcli "${ports[$mode]}" SET "lesson:$group:$i" "$group-$i")
      printf '%s\n' "$reply"
      [[ $reply == OK ]] || return 1
    done
  done
}

printf 'BASH LESSON: process crash, KHONG phai cat nguon may.\n'
printf 'Moi lan chay co thu muc lesson-* rieng; khong thay so lieu Python.\n'
printf 'Moi lenh redis-cli va moi diem dung deu lam tang thoi gian truoc SIGKILL.\n'
step '1. Moi truong Linux/Redis' 'Quan sat phien ban va hai port rieng 6380/6381.'
show uname -sr
show redis-server --version
show ss -ltn

step '2. Cau hinh va thu muc du lieu' 'Dung template chung trong redis/; thay PID, log, dir theo lan chay.'
for mode in rdb aof; do render_config "$mode"; show cat "$run_dir/$mode/$mode.conf"; done

step '3. Khoi dong hai instance' 'redis-server doc config; PING va ps xac nhan server/process.'
for mode in rdb aof; do start_instance "$mode"; done
show redis-cli -p 6380 CONFIG GET save
show redis-cli -p 6380 CONFIG GET appendonly
show redis-cli -p 6381 CONFIG GET appendfsync

step '4. Ghi baseline' 'Ghi 3 key giong nhau vao hai instance; moi SET phai tra OK.'
write_group baseline "$baseline"
for port in 6380 6381; do show redis-cli -p "$port" DBSIZE; done

step '5. Checkpoint RDB' 'BGSAVE chay nen: phai doi snapshot hoan thanh, khong chi doi lenh duoc chap nhan.'
saves_before=$(field 6380 persistence rdb_saves)
[[ $saves_before =~ ^[0-9]+$ ]] || { printf 'Invalid rdb_saves response.\n' >&2; exit 1; }
reply=$(show redis-cli -p 6380 BGSAVE)
printf '%s\n' "$reply"
[[ $reply == *'Background saving started'* ]] || exit 1
snapshot_ok=false
for ((attempt=0; attempt<100; attempt++)); do
  if [[ $(field 6380 persistence rdb_bgsave_in_progress) == 0 ]]; then
    [[ $(field 6380 persistence rdb_last_bgsave_status) == ok ]] || exit 1
    saves_after=$(field 6380 persistence rdb_saves)
    if [[ $saves_after =~ ^[0-9]+$ && $saves_after -gt $saves_before && -s $run_dir/rdb/data/dump.rdb ]]; then
      snapshot_ok=true; break
    fi
  fi
  sleep 0.1
done
"$snapshot_ok" || { printf 'Checkpoint did not complete.\n' >&2; exit 1; }
show redis-cli -p 6380 INFO persistence
show ls -lh "$run_dir/rdb/data/dump.rdb"

step '6. Ghi delta' 'Ghi them 2 key. RDB khong tao snapshot moi; AOF tiep tuc ghi nhat ky.'
write_group delta "$delta"
for port in 6380 6381; do show redis-cli -p "$port" DBSIZE; show redis-cli -p "$port" GET lesson:delta:1; done

step '7. SIGKILL' 'Nhan Enter se kill AOF truoc, RDB sau. Diem dung nay co the cho AOF them thoi gian fsync.'
for mode in aof rdb; do
  pid=$(owned_pid "$mode") || { printf 'PID verification failed; refusing signal.\n' >&2; exit 1; }
  show kill -9 "$pid"
done
for port in 6380 6381; do
  for ((attempt=0; attempt<100; attempt++)); do
    [[ -z $(ss -H -ltn "sport = :$port") ]] && break
    sleep 0.1
  done
  [[ -z $(ss -H -ltn "sport = :$port") ]] || { printf 'Port still open: %s\n' "$port" >&2; exit 1; }
done
unset 'pids[rdb]' 'pids[aof]' 'births[rdb]' 'births[aof]'
show find "$run_dir" -type f

step '8. Restart' 'Khoi dong bang DUNG config va data directory cu; quan sat PID moi.'
for mode in rdb aof; do start_instance "$mode"; done

step '9. Kiem tra phuc hoi' 'GET/EXISTS tung key: phan biet baseline, delta, va value sai.'
printf 'mode,expected_before,dbsize_after,verified_correct,missing_baseline,missing_delta,wrong_values\n' > "$run_dir/summary.csv"
for mode in rdb aof; do
  correct=0; missing_baseline=0; missing_delta=0; wrong=0
  for group in baseline delta; do
    count=$baseline; [[ $group == delta ]] && count=$delta
    for ((i=1; i<=count; i++)); do
      key="lesson:$group:$i"
      exists=$(rcli "${ports[$mode]}" EXISTS "$key")
      printf '\n$ redis-cli -p %s GET %s\n' "${ports[$mode]}" "$key"
      value=$(rcli "${ports[$mode]}" GET "$key")
      if [[ $exists == 0 ]]; then
        printf '%s: %s -> (nil)\n' "$mode" "$key"
        if [[ $group == baseline ]]; then missing_baseline=$((missing_baseline+1)); else missing_delta=$((missing_delta+1)); fi
      else
        printf '%s\n' "$value"
        if [[ $value == "$group-$i" ]]; then correct=$((correct+1)); else wrong=$((wrong+1)); fi
      fi
    done
  done
  size=$(rcli "${ports[$mode]}" DBSIZE)
  printf '%s,%s,%s,%s,%s,%s,%s\n' "$mode" "$((baseline+delta))" "$size" "$correct" "$missing_baseline" "$missing_delta" "$wrong" >> "$run_dir/summary.csv"
done
show cat "$run_dir/summary.csv"

step '10. Doc log va ket luan' 'RDB du kien giu baseline; AOF co the giu du 5 key sau process crash.'
for mode in rdb aof; do show tail -n 18 "$run_dir/$mode/redis.log"; done
printf '\nKhong dung run nay de ket luan do tre ACK-to-kill hay mat dien that.\n'
printf 'Dung run_trials.py de do va lap bang so lieu thuc nghiem.\n'
