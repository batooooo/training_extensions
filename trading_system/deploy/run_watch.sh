#!/usr/bin/env bash
# Wrapper for launchd/cron: load .env and run the real-time fill watcher.
# Resolves paths relative to this script so it works wherever the repo lives.
set -euo pipefail
cd "$(dirname "$0")/.."          # -> trading_system/
set -a; . ./.env; set +a         # load ALPACA_* and TELEGRAM_* keys
exec .venv/bin/python scripts/watch.py
