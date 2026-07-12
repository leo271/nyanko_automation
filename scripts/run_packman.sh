#!/bin/zsh

set -euo pipefail

ROOT="${0:A:h:h}"
cd "$ROOT"
mkdir -p logs

LOG_FILE="logs/packman-$(date +%Y%m%d-%H%M%S).log"

{
  echo "[launcher] initial battle start"
  uv run nyanko-auto run-snippet tap_battle_start --repeat 2 --live
  echo "[launcher] routine start"
  uv run nyanko-auto run \
    --routine packman \
    --from wait_battle_start \
    --forever \
    --live
} 2>&1 | tee "$LOG_FILE"
