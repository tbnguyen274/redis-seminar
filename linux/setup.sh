#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script with sudo or as root." >&2
  exit 1
fi

if [[ "$(ps -p 1 -o comm=)" != "systemd" ]]; then
  echo "This setup requires systemd. See linux/troubleshooting.md for WSL2 setup." >&2
  exit 1
fi

apt-get update
apt-get install -y redis-server redis-tools python3 python3-venv iproute2 procps

demo_user="${SUDO_USER:-root}"
demo_group="$(id -gn "$demo_user")"
for name in rdb aof eviction data-structures cache-aside; do
  install -d -o "$demo_user" -g "$demo_group" "/tmp/redis-seminar/$name"
done

systemctl enable redis-server
systemctl restart redis-server

redis-cli -e -h 127.0.0.1 -p 6379 PING
redis-server --version
python3 --version
