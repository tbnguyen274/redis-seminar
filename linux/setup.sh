#!/usr/bin/env bash
set -euo pipefail

if [[ "${EUID}" -ne 0 ]]; then
  echo "Please run this script with sudo or as root." >&2
  exit 1
fi

apt-get update
apt-get install -y redis-server redis-tools

systemctl enable redis-server
systemctl restart redis-server

redis-cli ping
redis-server --version
