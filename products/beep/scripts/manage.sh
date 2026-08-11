#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="$(cd -- "${script_dir}/.." && pwd -P)"

if [[ -f "${source_root}/payload/agent/beep/management.py" ]]; then
  export BEEP_SOURCE_ROOT="${source_root}"
  export PYTHONPATH="${source_root}/payload/agent"
elif [[ -f /opt/beep/product/payload/agent/beep/management.py ]]; then
  export BEEP_SOURCE_ROOT="/opt/beep/product"
  export PYTHONPATH="/opt/beep/product/payload/agent"
else
  echo "Beep management code is unavailable." >&2
  exit 66
fi

exec python3 -m beep.management "$@"
