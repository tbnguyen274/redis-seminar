#!/usr/bin/env bash
set -euo pipefail

# Read-only checks. Start all five demo instances before running this script.
printf 'Checked at: '
date -u '+%Y-%m-%d %H:%M:%S UTC'
grep -E '^(PRETTY_NAME|VERSION_ID)=' /etc/os-release
uname -r
printf 'Logical CPUs: '
nproc
free -h
redis-server --version
python3 --version
systemctl is-active redis-server

for port in 6379 6380 6381 6382 6383 6384; do
  reply="$(redis-cli -e --raw -h 127.0.0.1 -p "$port" PING)"
  [[ "$reply" == "PONG" ]]
  printf 'Port %s: %s\n' "$port" "$reply"
  redis-cli -e --raw -p "$port" INFO server | grep '^process_id:'
done

expect_config() {
  local port="$1" setting="$2" expected="$3" actual
  actual="$(redis-cli -e --raw -p "$port" CONFIG GET "$setting" | tail -n 1)"
  if [[ "$actual" != "$expected" ]]; then
    printf 'FAIL port %s %s: expected %s, got %s\n' "$port" "$setting" "$expected" "$actual" >&2
    exit 1
  fi
  printf 'Port %s: %s=%s\n' "$port" "$setting" "$actual"
}

expect_config 6380 dir /tmp/redis-seminar/rdb
expect_config 6380 appendonly no
expect_config 6381 dir /tmp/redis-seminar/aof
expect_config 6381 appendonly yes
expect_config 6381 appendfsync everysec
expect_config 6381 save ''
expect_config 6382 maxmemory 10485760
expect_config 6382 maxmemory-policy allkeys-lru
for pair in '6382 eviction' '6383 data-structures' '6384 cache-aside'; do
  read -r port name <<< "$pair"
  expect_config "$port" dir "/tmp/redis-seminar/$name"
  expect_config "$port" save ''
  expect_config "$port" appendonly no
done

ss -lnt | grep -E ':6379 |:638[0-4] '
printf 'PASS: service, ports and demo configuration checks.\n'
