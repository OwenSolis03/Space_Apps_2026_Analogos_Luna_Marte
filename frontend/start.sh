#!/usr/bin/env bash
#
# Start the Orbital Atlas development server.
#
# Usage:
#   ./start.sh              Start on the first free port from 5173 upwards.
#   PORT=8080 ./start.sh    Start on a specific port.
#   OPEN=1 ./start.sh       Force the browser to open.
#   OPEN=0 ./start.sh       Never open the browser.
#
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

PORT="${PORT:-5173}"
OPEN="${OPEN:-auto}"

if ! command -v npm >/dev/null 2>&1; then
  echo "Error: npm is required but was not found in PATH." >&2
  exit 1
fi

if [ ! -d node_modules ]; then
  echo "Installing dependencies (first run)..."
  npm install
fi

echo "Starting Orbital Atlas..."
echo "Press Ctrl+C to stop the server."
echo

ARGS=(--port "$PORT")

if [ "$OPEN" = "1" ]; then
  ARGS+=(--open)
elif [ "$OPEN" = "auto" ] && { [ -n "${DISPLAY:-}" ] || [ -n "${WAYLAND_DISPLAY:-}" ]; }; then
  ARGS+=(--open)
fi

exec npm run dev -- "${ARGS[@]}"
