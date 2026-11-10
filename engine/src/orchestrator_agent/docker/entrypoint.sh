#!/usr/bin/env bash
set -euo pipefail

ENV_FILE="/app/.env"
if [ -f "$ENV_FILE" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    # trim whitespace
    line="${line#"${line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [ -z "$line" ] && continue
    case "$line" in \#*) continue;; esac
    line="${line#export }"
    [[ "$line" == *"="* ]] || continue
    key="${line%%=*}"
    val="${line#*=}"
    # trim key/val whitespace
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    val="${val#"${val%%[![:space:]]*}"}"
    val="${val%"${val##*[![:space:]]}"}"
    # strip surrounding single or double quotes
    if [[ "$val" =~ ^\".*\"$ ]] || [[ "$val" =~ ^\'.*\'$ ]]; then
      val="${val:1:${#val}-2}"
    fi
    # validate key is a shell identifier
    if ! [[ "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      continue
    fi
    # only set from .env if not already provided by docker -e / env-file
    if [ -z "${!key:-}" ]; then
      export "$key=$val"
    fi
  done < "$ENV_FILE"
fi

exec "$@"