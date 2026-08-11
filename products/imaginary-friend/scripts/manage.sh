#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
source_root="$(cd -- "${script_dir}/.." && pwd -P)"

if [[ -f "${source_root}/payload/agent/friend/management.py" ]]; then
  export IMAGINARY_FRIEND_SOURCE_ROOT="${source_root}"
  export PYTHONPATH="${source_root}/payload/agent"
elif [[ -f /opt/imaginary-friend/agent/friend/management.py ]]; then
  export IMAGINARY_FRIEND_SOURCE_ROOT="/opt/imaginary-friend"
  export PYTHONPATH="/opt/imaginary-friend/agent"
else
  echo "Imaginary Friend management code is unavailable." >&2
  exit 66
fi

exec python3 -m friend.management "$@"
