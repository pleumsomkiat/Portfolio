#!/usr/bin/env bash
# Validate the supported local development target. No package is installed here.
set -u

failed=0

pass() { printf '[PASS] %s\n' "$1"; }
fail() { printf '[FAIL] %s\n' "$1" >&2; failed=1; }

if [[ -r /etc/os-release ]]; then
  # shellcheck disable=SC1091
  . /etc/os-release
  if [[ "${ID:-}" == "ubuntu" && "${VERSION_ID:-}" == "22.04" ]]; then
    pass "Ubuntu ${VERSION_ID} (${PRETTY_NAME})"
  else
    fail "ต้องใช้ Ubuntu 22.04 แต่พบ ${PRETTY_NAME:-unknown}"
  fi
else
  fail "ไม่พบ /etc/os-release"
fi

if command -v python3 >/dev/null 2>&1; then
  python_version="$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if [[ "$python_version" == "3.10" ]]; then
    pass "Python $python_version"
  else
    fail "ต้องใช้ Python 3.10 แต่พบ Python $python_version"
  fi
else
  fail "ไม่พบ python3"
fi

for tool in git cmake g++ ffmpeg; do
  if command -v "$tool" >/dev/null 2>&1; then
    pass "$tool: $(command -v "$tool")"
  else
    fail "ไม่พบ $tool"
  fi
done

if command -v node >/dev/null 2>&1; then
  node_version="$(node --version | sed 's/^v//')"
  node_major="${node_version%%.*}"
  node_rest="${node_version#*.}"
  node_minor="${node_rest%%.*}"
  if (( node_major > 20 || (node_major == 20 && node_minor >= 9) )); then
    pass "Node.js v$node_version"
  else
    fail "ต้องใช้ Node.js >= 20.9 แต่พบ v$node_version"
  fi
else
  fail "ไม่พบ node (ต้องใช้ Node.js >= 20.9)"
fi

if command -v npm >/dev/null 2>&1 && npm_version="$(npm --version 2>/dev/null)" && [[ -n "$npm_version" ]]; then
  pass "npm: $npm_version"
else
  fail "ไม่พบ npm ที่ใช้งานได้ภายใน Ubuntu"
fi

if (( failed )); then
  echo "Environment ยังไม่พร้อม — ดูขั้นตอนติดตั้งใน README.th.md" >&2
  exit 1
fi

echo "Environment พร้อมสำหรับ Unitree G1 Thai Chatbot (ยังไม่ได้ตรวจเครือข่าย G1)"
