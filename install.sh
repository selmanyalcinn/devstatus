#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
if command -v uv >/dev/null 2>&1; then
  uv tool install --force .
elif command -v pipx >/dev/null 2>&1; then
  pipx install --force .
else
  echo "devstatus requires uv or pipx for the recommended isolated install." >&2
  echo "Install uv (https://docs.astral.sh/uv/) or pipx, then rerun ./install.sh." >&2
  exit 1
fi
echo
echo "Installed. Run: devstatus"
