#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
if command -v node >/dev/null 2>&1; then
  exec node tools/start_local.mjs
fi
exec ./runtime/node-v22.23.3-linux-x64/bin/node tools/start_local.mjs
