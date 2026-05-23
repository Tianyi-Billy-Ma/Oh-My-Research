#!/usr/bin/env bash
# Load a project-local .env file (if present) into the environment, then exec
# the given command. Variables already set in the parent shell take precedence
# over .env entries, so users who export keys in ~/.zshrc don't get overridden
# by a stale .env.
#
# Used by Oh-My-Research's .mcp.json to give every MCP server the same env
# resolution: shell env first, .env second.

set -euo pipefail

env_file="${PWD}/.env"

if [ -f "$env_file" ]; then
  while IFS= read -r line || [ -n "$line" ]; do
    case "$line" in
      ''|\#*) continue ;;
    esac
    if [[ "$line" != *=* ]]; then
      continue
    fi
    key="${line%%=*}"
    value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    key="${key#export }"
    if [[ ! "$key" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]]; then
      continue
    fi
    if [ -n "${!key:-}" ]; then
      continue
    fi
    if [[ "$value" == \"*\" ]] || [[ "$value" == \'*\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    export "$key=$value"
  done < "$env_file"
fi

exec "$@"
