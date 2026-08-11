#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
needs_root=1
skip_next=0

for argument in "$@"; do
  if (( skip_next )); then
    skip_next=0
    continue
  fi
  case "${argument}" in
    --) break ;;
    --dry-run|-h|--help) needs_root=0 ;;
    --request-file|--correlation-id|--plan-digest)
      skip_next=1
      ;;
  esac
done

if (( EUID != 0 && needs_root )); then
  command -v sudo >/dev/null || {
    echo "Imaginary Friend installation requires root; rerun this installer as root." >&2
    exit 73
  }
  exec sudo -- "${script_dir}/manage.sh" install "$@"
fi

exec "${script_dir}/manage.sh" install "$@"
