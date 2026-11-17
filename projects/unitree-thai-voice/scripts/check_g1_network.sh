#!/usr/bin/env bash
# Read-only network inspection. This script does not initialize Unitree SDK2.
set -euo pipefail

probe=""
if [[ "${1:-}" == "--probe" ]]; then
  probe="${2:-}"
  if [[ -z "$probe" ]]; then
    echo "Usage: $0 [--probe G1_IP]" >&2
    exit 2
  fi
fi

echo "== Linux / WSL =="
uname -a
echo
echo "== Network interfaces =="
ip -brief link
ip -brief addr
echo
echo "== Routes =="
ip route

if [[ -n "$probe" ]]; then
  echo
  echo "== Route to $probe =="
  ip route get "$probe" || true
  echo
  echo "== ICMP probe (2 packets) =="
  ping -c 2 -W 2 "$probe" || true
else
  echo
  echo "No G1 IP supplied. Run: $0 --probe <G1_IP>"
fi
