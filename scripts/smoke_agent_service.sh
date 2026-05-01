#!/usr/bin/env bash
set -euo pipefail

# Smoke-test the local agent HTTP service (health, optional authenticated chat).
# GET {base}/agent/health always runs.
# When --auth-header is set, POST {base}/agent/chat with JSON ChatRequest
# (patient_id, user_message, messages). Exits 1 on failure.

usage() {
  echo "Usage: $0 [--base-url URL] [--auth-header TOKEN_OR_BEARER] [--patient-id ID] [--user-message MSG]" >&2
  exit 1
}

trim() {
  local s="${1:-}"
  s="${s#"${s%%[![:space:]]*}"}"
  s="${s%"${s##*[![:space:]]}"}"
  printf '%s' "$s"
}

authorization_value() {
  local raw
  raw="$(trim "${1:-}")"
  if [[ -z "$raw" ]]; then
    printf '%s' ""
    return
  fi
  shopt -s nocasematch
  if [[ "$raw" == "Bearer"* ]]; then
    printf '%s' "$raw"
  else
    printf 'Bearer %s' "$raw"
  fi
  shopt -u nocasematch
}

BASE_URL="http://127.0.0.1:8080"
AUTH_HEADER=""
PATIENT_ID=""
USER_MESSAGE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --base-url)
      [[ $# -lt 2 ]] && usage
      BASE_URL="$2"
      shift 2
      ;;
    --auth-header)
      [[ $# -lt 2 ]] && usage
      AUTH_HEADER="$2"
      shift 2
      ;;
    --patient-id)
      [[ $# -lt 2 ]] && usage
      PATIENT_ID="$2"
      shift 2
      ;;
    --user-message)
      [[ $# -lt 2 ]] && usage
      USER_MESSAGE="$2"
      shift 2
      ;;
    -h | --help)
      usage
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage
      ;;
  esac
done

base="$(trim "$BASE_URL")"
base="${base%/}"

health_uri="${base}/agent/health"
http_code=""
if ! http_code="$(curl -fsS -o /dev/null -w '%{http_code}' "$health_uri")"; then
  echo "FAIL: GET /agent/health" >&2
  exit 1
fi
echo "GET ${health_uri} -> ${http_code}"

auth_trimmed="$(trim "$AUTH_HEADER")"
if [[ -n "$auth_trimmed" ]]; then
  default_patient_id="smoke-test-patient"
  default_user_message="smoke: hello from smoke_agent_service.sh"

  effective_patient="$(trim "$PATIENT_ID")"
  effective_message="$(trim "$USER_MESSAGE")"
  [[ -z "$effective_patient" ]] && effective_patient="$default_patient_id"
  [[ -z "$effective_message" ]] && effective_message="$default_user_message"

  if [[ ${#effective_patient} -lt 1 || ${#effective_message} -lt 1 ]]; then
    echo "FAIL: patient_id and user_message must be non-empty for ChatRequest." >&2
    exit 1
  fi

  if command -v jq >/dev/null 2>&1; then
    chat_body="$(jq -n --arg p "$effective_patient" --arg m "$effective_message" \
      '{patient_id: $p, user_message: $m, messages: []}')"
  elif command -v python3 >/dev/null 2>&1; then
    chat_body="$(
      python3 -c 'import json, sys
print(json.dumps({"patient_id": sys.argv[1], "user_message": sys.argv[2], "messages": []}))
' "$effective_patient" "$effective_message"
    )"
  else
    echo "FAIL: jq or python3 is required to build JSON for POST /agent/chat." >&2
    exit 1
  fi

  auth_value="$(authorization_value "$auth_trimmed")"
  chat_uri="${base}/agent/chat"

  chat_code=""
  if ! chat_code="$(
    curl -fsS -o /dev/null -w '%{http_code}' \
      -X POST "$chat_uri" \
      -H "Content-Type: application/json; charset=utf-8" \
      -H "Authorization: ${auth_value}" \
      --data-binary "$chat_body"
  )"; then
    echo "FAIL: POST /agent/chat" >&2
    exit 1
  fi
  echo "POST ${chat_uri} -> ${chat_code}"
fi

exit 0
