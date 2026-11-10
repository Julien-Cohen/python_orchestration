#!/usr/bin/env bash

# SPDX-FileCopyright: 2026 University of York
# SPDX-License: MIT

# Sends an A2A 1.0 JSON-RPC message request to the agent, with a
# single text part with the expression passed via the CLI.

set -euo pipefail
if test "$#" = 0; then
  echo "Usage: $0 expression" >&2
  exit 1
fi

generate_uuid() {
  (uuidgen 2>/dev/null || python3 -c 'import uuid; print(uuid.uuid4())') \
    | tr -d "-" \
    | tr '[:upper:]' '[:lower:]'
}

generate_half_uuid() {
  generate_uuid | head -c 16
}

EXPR="$@"

AGENT_URL="${AGENT_URL:-http://localhost:9001/}"
REQUEST_ID="$(generate_uuid)"
MESSAGE_ID="$(generate_uuid)"
ROOT_TASK_ID="$(generate_uuid)"
SUPER_TASK_ID="$(generate_half_uuid)"

curl -sS -X POST "$AGENT_URL" \
  -H 'Content-Type: application/json' \
  -H 'A2A-Version: 1.0' \
  -d @- <<EOF
{
  "jsonrpc": "2.0",
  "id": "${REQUEST_ID}",
  "method": "SendMessage",
  "params": {
    "message": {
      "messageId": "${MESSAGE_ID}",
      "role": "ROLE_USER",
      "parts": [
        {
          "text": "$EXPR"
        }
      ]
    },
    "metadata": {
      "mosaico-root-task-name": "send-request",
      "mosaico-root-task-id": "$ROOT_TASK_ID",
      "mosaico-super-task-id": "$SUPER_TASK_ID"
    }
  }
}
EOF
