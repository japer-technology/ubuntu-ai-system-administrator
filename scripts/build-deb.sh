#!/usr/bin/env bash
# scripts/build-deb.sh — build a stage-1 .deb of Ubuntu AI System Administrator
# source tree using raw dpkg-deb (no debhelper required).
#
# Output: dist/ubuntu-ai-system-administrator_<version>_all.deb
#
# Usage:
#   bash scripts/build-deb.sh
#
# Idempotent: re-running rebuilds the package from scratch.
set -Eeuo pipefail

usage() {
  cat <<EOF
build-deb.sh — build a stage-1 .deb of the Ubuntu AI System Administrator source tree.

Usage:
  bash scripts/build-deb.sh [-h|--help]

Output:
  dist/ubuntu-ai-system-administrator_<version>_all.deb

Idempotent: re-running rebuilds the package from scratch. Requires
dpkg-deb; no debhelper needed. See debian/README.md for what the
package does (and deliberately does not do).
EOF
}

case "${1:-}" in
  -h|--help) usage; exit 0 ;;
  "") ;;
  *) echo "build-deb.sh: unknown argument: $1" >&2; usage >&2; exit 2 ;;
esac

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${ROOT}"

# shellcheck source=scripts/lib.sh
if [[ -r "${ROOT}/scripts/lib.sh" ]]; then
  . "${ROOT}/scripts/lib.sh"
  lib_setup_colors
else
  printf 'build-deb.sh: cannot find required library %s\n' "${ROOT}/scripts/lib.sh" >&2
  exit 1
fi

VERSION="$(tr -d '[:space:]' < VERSION)"
PKG="ubuntu-ai-system-administrator"
ARCH="all"
OUT_DIR="${ROOT}/dist"
STAGE="$(mktemp -d -t "${PKG}-deb.XXXXXX")"
trap 'rm -rf "${STAGE}"' EXIT

mkdir -p "${OUT_DIR}"
info "Building ${PKG} ${VERSION} in ${STAGE}"

# ---------------------------------------------------------------------------
# Lay out the file tree
# ---------------------------------------------------------------------------

# Payload installed under /usr/share/ubuntu-ai-system-administrator/ so it does not
# conflict with /opt/ai-system-administrator/ (which is created at `ubuntu-ai-system-administrator
# install` time, not at apt time).
INSTALL_ROOT="${STAGE}/usr/share/${PKG}"
DOC_ROOT="${STAGE}/usr/share/doc/${PKG}"
SBIN="${STAGE}/usr/sbin"
DEBIAN="${STAGE}/DEBIAN"

mkdir -p "${INSTALL_ROOT}" "${DOC_ROOT}" "${SBIN}" "${DEBIAN}"

# Copy only tracked source files when building from a clone, so ignored
# caches and other local artifacts cannot leak into a release. The tar
# fallback keeps `make deb` working from a source release without `.git`.
SOURCE_ITEMS=(
  scripts payload tests Makefile VERSION
  README.md CHANGELOG.md CONTRIBUTING.md CODE_OF_CONDUCT.md
  LICENSE SECURITY.md docs
)
GIT_ROOT="$(git -C "${ROOT}" rev-parse --show-toplevel 2>/dev/null || true)"
if [[ "${GIT_ROOT}" == "${ROOT}" ]]; then
  (
    cd "${ROOT}"
    git ls-files -z -- "${SOURCE_ITEMS[@]}" \
      | tar --null --files-from=- -cf -
  ) | tar -C "${INSTALL_ROOT}" -xf -
else
  (
    cd "${ROOT}"
    tar --exclude-vcs \
      --exclude='__pycache__' \
      --exclude='.pytest_cache' \
      --exclude='.mypy_cache' \
      --exclude='.ruff_cache' \
      --exclude='*.pyc' \
      --exclude='*.pyo' \
      -cf - "${SOURCE_ITEMS[@]}"
  ) | tar -C "${INSTALL_ROOT}" -xf -
fi

# Docs duplicated under /usr/share/doc/<pkg>/ so `dpkg -L` reveals
# them in the conventional location.
cp -a "${ROOT}/README.md" "${DOC_ROOT}/README.md"
cp -a "${ROOT}/CHANGELOG.md" "${DOC_ROOT}/changelog.upstream"
gzip -9n "${DOC_ROOT}/changelog.upstream"

cp -a "${ROOT}/debian/copyright" "${DOC_ROOT}/copyright"
cp -a "${ROOT}/debian/changelog" "${DOC_ROOT}/changelog.Debian"
gzip -9n "${DOC_ROOT}/changelog.Debian"

# Normalize archive permissions instead of inheriting the clone's umask.
# Re-apply executable bits only to tracked entrypoints.
find "${STAGE}" -type d -exec chmod 0755 {} +
find "${INSTALL_ROOT}" "${DOC_ROOT}" -type f -exec chmod 0644 {} +
while IFS= read -r -d '' source; do
  target="${INSTALL_ROOT}/${source#"${ROOT}/"}"
  chmod 0755 "${target}"
done < <(
  find "${ROOT}/scripts" "${ROOT}/payload" "${ROOT}/tests" \
    -type f -perm /111 -print0
)

# Wrapper that dispatches to the installer's CLI.
cat > "${SBIN}/${PKG}" <<EOF
#!/usr/bin/env bash
# ubuntu-ai-system-administrator — thin wrapper around scripts/install.sh.
# Installed by the .deb at /usr/sbin/ubuntu-ai-system-administrator.
set -Eeuo pipefail
INSTALLER="/usr/share/${PKG}/scripts/install.sh"
if [ ! -x "\${INSTALLER}" ]; then
  echo "ubuntu-ai-system-administrator: installer missing at \${INSTALLER}" >&2
  echo "  reinstall the package: sudo apt install --reinstall ${PKG}" >&2
  exit 1
fi
exec "\${INSTALLER}" "\$@"
EOF
chmod 0755 "${SBIN}/${PKG}"

# ---------------------------------------------------------------------------
# Control metadata
# ---------------------------------------------------------------------------

# control
sed "s/__VERSION__/${VERSION}/g" "${ROOT}/debian/control.in" > "${DEBIAN}/control"
# Compute Installed-Size (KiB) per Debian policy.
SIZE_KB="$(du -ks "${INSTALL_ROOT}" "${DOC_ROOT}" "${SBIN}" | awk '{s+=$1} END {print s}')"
printf 'Installed-Size: %s\n' "${SIZE_KB}" >> "${DEBIAN}/control"
chmod 0644 "${DEBIAN}/control"

cp -a "${ROOT}/debian/postinst" "${DEBIAN}/postinst"
cp -a "${ROOT}/debian/prerm"   "${DEBIAN}/prerm"
chmod 0755 "${DEBIAN}/postinst" "${DEBIAN}/prerm"

# md5sums for `dpkg --verify`.
( cd "${STAGE}" && find usr -type f -exec md5sum {} + > "${DEBIAN}/md5sums" )
chmod 0644 "${DEBIAN}/md5sums"

# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

DEB_NAME="${PKG}_${VERSION}_${ARCH}.deb"
dpkg-deb --root-owner-group --build "${STAGE}" "${OUT_DIR}/${DEB_NAME}"

echo
ok "Wrote ${OUT_DIR}/${DEB_NAME}"
dpkg-deb --info  "${OUT_DIR}/${DEB_NAME}" | head -30 || true
echo
info "Contents (first 20):"
# Pipe to cat first so dpkg-deb sees an unbroken pipe even when head
# closes early — otherwise SIGPIPE kills dpkg-deb under `set -o pipefail`.
dpkg-deb --contents "${OUT_DIR}/${DEB_NAME}" 2>/dev/null | head -20 || true
