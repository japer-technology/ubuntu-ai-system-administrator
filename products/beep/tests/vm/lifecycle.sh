#!/usr/bin/env bash
set -Eeuo pipefail

if [[ "${BEEP_DISPOSABLE_VM_TEST:-}" != "1" ]] \
  || [[ ! -f /run/beep-disposable-vm ]]; then
  echo "SKIP: requires BEEP_DISPOSABLE_VM_TEST=1 and /run/beep-disposable-vm" >&2
  exit 77
fi
if [[ "${EUID}" -ne 0 ]]; then
  echo "ERROR: disposable VM lifecycle test requires root" >&2
  exit 64
fi
if ! grep -q '^ID=ubuntu$' /etc/os-release; then
  echo "ERROR: disposable VM lifecycle test requires Ubuntu" >&2
  exit 69
fi

product_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd -P)"
password_file="$(mktemp /root/beep-test-password.XXXXXX)"
backup_root="$(mktemp -d /root/beep-test-backup.XXXXXX)"
cleanup() {
  rm -f -- "${password_file}"
  rm -rf -- "${backup_root}"
}
trap cleanup EXIT
chmod 0600 "${password_file}"
printf '%s\n' 'disposable-vm-password-only' >"${password_file}"

common=(
  --json
  --non-interactive
  --yes
)
export BEEP_ADMIN_PASSWORD_FILE="${password_file}"
export BEEP_DISPOSABLE_VM_TEST=1

"${product_root}/scripts/manage.sh" install "${common[@]}"
"${product_root}/scripts/manage.sh" install "${common[@]}"
"${product_root}/scripts/manage.sh" verify --json
export BEEP_BACKUP_DESTINATION="${backup_root}"
"${product_root}/scripts/manage.sh" backup "${common[@]}"
unset BEEP_BACKUP_DESTINATION
"${product_root}/scripts/manage.sh" suspend "${common[@]}"
"${product_root}/scripts/manage.sh" resume "${common[@]}"
"${product_root}/scripts/manage.sh" kill "${common[@]}"

if "${product_root}/scripts/manage.sh" resume "${common[@]}"; then
  echo "ERROR: resume revived a dead Beep" >&2
  exit 1
fi
"${product_root}/scripts/manage.sh" install "${common[@]}"
if "${product_root}/scripts/manage.sh" resume "${common[@]}"; then
  echo "ERROR: reinstall revived a dead Beep" >&2
  exit 1
fi
"${product_root}/scripts/manage.sh" uninstall "${common[@]}" --purge \
  --confirmation 'DELETE BEEP STATE'
