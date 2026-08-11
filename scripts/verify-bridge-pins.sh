#!/usr/bin/env bash
# Verify the checksum-pinned Node bridge inputs recorded in the release tree.
set -Eeuo pipefail

usage() {
  cat <<EOF
verify-bridge-pins.sh — verify the checksum-pinned Node bridge inputs.

Usage:
  bash scripts/verify-bridge-pins.sh [-h|--help]

Downloads each npm tarball recorded in
payload/agent/bridge-dependencies.lock and checks its version, resolved
URL, sha256, integrity, and license against the lock file. Exits
non-zero on any mismatch. Requires network access, npm, and sha256sum.
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  "") ;;
  *) echo "verify-bridge-pins.sh: unknown argument: $1" >&2; usage >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

LOCK_FILE="${ROOT}/payload/agent/bridge-dependencies.lock"

if [[ ! -s "${LOCK_FILE}" ]]; then
  echo "missing bridge dependency lock file: ${LOCK_FILE}" >&2
  exit 1
fi

tmp_dir="$(mktemp -d)"
trap 'rm -rf "${tmp_dir}"' EXIT

check_pin() {
  local name="$1" package="$2" version="$3" url="$4" sha256="$5" integrity="$6" license="$7"
  local version_file tarball got_version got_url got_integrity got_license

  case "${name}" in
    pi-ai) version_file="payload/agent/pi-ai.version" ;;
    pi-mono) version_file="payload/agent/pi-mono.version" ;;
    *) echo "unknown bridge dependency name: ${name}" >&2; exit 1 ;;
  esac

  got_version="$(tr -d '[:space:]' < "${version_file}")"
  if [[ "${got_version}" != "${version}" ]]; then
    echo "${version_file} contains ${got_version}, lock file contains ${version}" >&2
    exit 1
  fi

  got_url="$(npm view "${package}@${version}" dist.tarball)"
  got_integrity="$(npm view "${package}@${version}" dist.integrity)"
  got_license="$(npm view "${package}@${version}" license)"
  if [[ "${got_url}" != "${url}" ]]; then
    echo "${package}@${version} tarball URL drifted:" >&2
    echo "  lock: ${url}" >&2
    echo "  npm:  ${got_url}" >&2
    exit 1
  fi
  if [[ "${got_integrity}" != "${integrity}" ]]; then
    echo "${package}@${version} integrity drifted:" >&2
    echo "  lock: ${integrity}" >&2
    echo "  npm:  ${got_integrity}" >&2
    exit 1
  fi
  if [[ "${got_license}" != "${license}" ]]; then
    echo "${package}@${version} license drifted:" >&2
    echo "  lock: ${license}" >&2
    echo "  npm:  ${got_license}" >&2
    exit 1
  fi

  tarball="${tmp_dir}/${name}.tgz"
  curl -fsSL "${url}" -o "${tarball}"
  printf '%s  %s\n' "${sha256}" "${tarball}" | sha256sum -c -
  echo "verified ${package}@${version}"
}

while read -r name package version url sha256 integrity license; do
  [[ -z "${name:-}" || "${name:0:1}" == "#" ]] && continue
  check_pin "${name}" "${package}" "${version}" "${url}" "${sha256}" "${integrity}" "${license}"
done < "${LOCK_FILE}"
