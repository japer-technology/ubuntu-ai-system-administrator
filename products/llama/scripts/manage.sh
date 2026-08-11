#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="$(cd -- "${script_dir}/.." && pwd -P)"

if [[ -f "${source_root}/payload/agent/llama/management.py" ]]; then
  export LLAMA_SOURCE_ROOT="${source_root}"
  export PYTHONPATH="${source_root}/payload/agent"
elif [[ -f /opt/llama.cpp/product/payload/agent/llama/management.py ]]; then
  export LLAMA_SOURCE_ROOT="/opt/llama.cpp/product"
  export PYTHONPATH="/opt/llama.cpp/product/payload/agent"
else
  echo "Llama management code is unavailable." >&2
  exit 66
fi

exec python3 -m llama.management "$@"
