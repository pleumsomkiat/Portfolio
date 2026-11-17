#!/usr/bin/env bash
set -e

if [[ -s "$HOME/.nvm/nvm.sh" ]]; then
  . "$HOME/.nvm/nvm.sh"
fi

project_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$project_root/frontend"

# Windows edits on /mnt/d do not reliably emit Linux file-watch events. Use
# Webpack's polling watcher so the served client stays in sync with the source.
export WATCHPACK_POLLING="${WATCHPACK_POLLING:-1000}"
exec npm run dev -- --webpack --hostname 0.0.0.0 --port 3000 "$@"
