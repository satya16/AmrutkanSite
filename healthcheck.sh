#!/bin/bash
set -uo pipefail

STATE_FILE="$HOME/audio-site/.healthcheck_state"
LOG_FILE="$HOME/audio-site/healthcheck.log"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') $1" >> "$LOG_FILE"
}

check_url() {
  # one retry after a short wait, to avoid flagging a sub-5s network blip
  curl -fsS -o /dev/null -m 10 "$1" && return 0
  sleep 5
  curl -fsS -o /dev/null -m 10 "$1" && return 0
  return 1
}

local_ok=false
check_url "http://localhost:8080/" && local_ok=true

tunnel_url="https://amrutkan.org"

tunnel_ok=false
check_url "$tunnel_url/" && tunnel_ok=true

prev_state="unknown"
[ -f "$STATE_FILE" ] && prev_state=$(cat "$STATE_FILE")

if $local_ok && $tunnel_ok; then
  new_state="healthy"
else
  new_state="unhealthy"
fi

if [ "$new_state" != "$prev_state" ]; then
  if [ "$new_state" = "unhealthy" ]; then
    reason=""
    $local_ok || reason="app.py localhost:8080 वर उत्तर देत नाही. "
    $tunnel_ok || reason="${reason}Tunnel पोहोचता येत नाही (url: ${tunnel_url:-unknown})."
    log "UNHEALTHY: $reason"
    notify-send -u critical "अमृतकण साइट डाउन आहे" "$reason" 2>>"$LOG_FILE" || true
  elif [ "$prev_state" = "unhealthy" ]; then
    log "RECOVERED: local=$local_ok tunnel=$tunnel_ok url=$tunnel_url"
    notify-send "अमृतकण साइट पुन्हा सुरू झाली" "$tunnel_url" 2>>"$LOG_FILE" || true
  else
    log "first run, state=$new_state"
  fi
fi

echo "$new_state" > "$STATE_FILE"
