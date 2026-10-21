#!/usr/bin/env bash
set -u

REPO="$HOME/project/puj/respos/dragons_project_analitycs"
cd "$REPO" || exit 2

mkdir -p logs/sync
LOCK_FILE="logs/sync/auto_sync_incremental_outputs.lock"
LOG_FILE="logs/sync/auto_sync_incremental_outputs.log"
INTERVAL_SECONDS="${INTERVAL_SECONDS:-14400}"

exec >> "$LOG_FILE" 2>&1

if [ -f "$LOCK_FILE" ]; then
  old_pid="$(cat "$LOCK_FILE" 2>/dev/null || true)"
  if [ -n "$old_pid" ] && kill -0 "$old_pid" 2>/dev/null; then
    echo "[$(date -Is)] Another auto sync is already running with PID $old_pid. Exiting."
    exit 0
  fi
fi

echo $$ > "$LOCK_FILE"
cleanup() {
  rm -f "$LOCK_FILE"
}
trap cleanup EXIT INT TERM

active_workers() {
  pgrep -af "scripts/run_pilot_processing.py" \
    | grep -E "full_parallel_all_variables_llm_remote_v3_media_cloud_s[0-9]+of5|full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s[0-9]+of6" \
    | grep -v grep \
    | wc -l
}

run_sync() {
  echo "[$(date -Is)] Starting incremental sync."
  .venv/bin/python scripts/sync_incremental_outputs.py \
    --run-glob 'full_parallel_all_variables_llm_remote_v3_media_cloud_s*of5' \
    --run-glob 'full_parallel_gliner25_multi_no_llm_repair_peft_v1_media_cloud_s*of6'
  rc=$?
  echo "[$(date -Is)] Sync finished with rc=$rc."
  return "$rc"
}

echo "[$(date -Is)] Auto sync started. interval_seconds=$INTERVAL_SECONDS repo=$REPO"

while true; do
  workers="$(active_workers)"
  echo "[$(date -Is)] Active target workers before sync: $workers"

  run_sync || true

  workers="$(active_workers)"
  echo "[$(date -Is)] Active target workers after sync: $workers"
  if [ "$workers" -eq 0 ]; then
    echo "[$(date -Is)] No target workers remain. Auto sync completed and will stop."
    exit 0
  fi

  echo "[$(date -Is)] Sleeping $INTERVAL_SECONDS seconds before next sync."
  sleep "$INTERVAL_SECONDS"
done
