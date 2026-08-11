#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="$(cd -- "${script_dir}/.." && pwd -P)"

if [[ -f "${source_root}/payload/agent/forgejo/management.py" ]]; then
  export FORGEJO_SOURCE_ROOT="${source_root}"
  export PYTHONPATH="${source_root}/payload/agent"
elif [[ -f /opt/forgejo/product/payload/agent/forgejo/management.py ]]; then
  export FORGEJO_SOURCE_ROOT="/opt/forgejo/product"
  export PYTHONPATH="/opt/forgejo/product/payload/agent"
else
  echo "Forgejo management code is unavailable." >&2
  exit 66
fi

exec python3 -m forgejo.management "$@"
