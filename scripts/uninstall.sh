#!/usr/bin/env bash
#
# uninstall.sh
# ------------
# Reverse the Ubuntu Zombie installer.
#
# Removes the chat service, sudoers drop-in, generated helpers, policy,
# logrotate rule, and (with
# confirmation) the agent user account (default name `zombie`,
# overridable with ZOMBIE_USER). Optionally archives the account's
# home directory and /opt/ai-zombie/state/ to /var/backups/ before
# deletion.
#
# Usage:
#   sudo ./uninstall.sh                # interactive (remove all managed components)
#   sudo ./uninstall.sh zombie         # remove only the zombie component
#   sudo ./uninstall.sh forgejo        # remove only the Forgejo component
#   sudo ./uninstall.sh forgejo-runner # remove only the Forgejo runner
#   sudo ./uninstall.sh llama          # remove only the standalone llama
#   sudo ./uninstall.sh -n|--dry-run   # preview
#   sudo ./uninstall.sh --archive      # archive then remove
#   sudo ./uninstall.sh -y|--yes       # skip confirmations
#   sudo ./uninstall.sh --keep-agent   # do not remove user
#   sudo ./uninstall.sh -q|--quiet     # warnings and errors only
#   sudo ./uninstall.sh --no-color     # disable ANSI colour
#   ./uninstall.sh -v|--version        # print the version and exit
#
# Environment:
#   ZOMBIE_USER=<name>   override the account name (default `zombie`).
#                        `AGENT_USER` is still accepted as a legacy
#                        alias so older installs can still be reversed.
#   ZOMBIE_COLOR=auto|always|never   colour policy (default auto;
#                        NO_COLOR is also honoured).
#
# This script intentionally does NOT remove Node, Python, or other base
# packages — those are normal Ubuntu software
# that other things may depend on.

set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
# shellcheck source=scripts/lib.sh
if [[ -r "${SCRIPT_DIR}/lib.sh" ]]; then
  . "${SCRIPT_DIR}/lib.sh"
else
  printf 'uninstall.sh: cannot find required library %s\n' "${SCRIPT_DIR}/lib.sh" >&2
  exit 1
fi

AGENT_USER="${ZOMBIE_USER:-${AGENT_USER:-zombie}}"
AGENT_HOME="/home/${AGENT_USER}"
ZOMBIE_DIR="${ZOMBIE_DIR:-/opt/ai-zombie}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups}"

DRY_RUN=0
ARCHIVE=0
ASSUME_YES=0
KEEP_AGENT=0
TARGET_ARGS=()
readonly COMPONENT_ZOMBIE="zombie"
readonly COMPONENT_FORGEJO="forgejo"
readonly COMPONENT_FORGEJO_RUNNER="forgejo-runner"
readonly COMPONENT_LLAMA="llama"
COMPONENT_MANIFEST_DIR="${ZOMBIE_COMPONENT_MANIFEST_DIR:-/var/lib/ubuntu-zombie/components}"
LLAMA_PRODUCT_ROOT="${LLAMA_PRODUCT_ROOT:-${REPO_ROOT}/products/llama}"
FORGEJO_PRODUCT_ROOT="${FORGEJO_PRODUCT_ROOT:-${REPO_ROOT}/products/forgejo}"
# Track recoverable failures from the start so early cleanup can continue
# through later steps while still returning a non-zero final status.
UNINSTALL_EXIT=0
# Count of cleanup failures: used for per-component manifest-retention checks
# so that failures from one component cannot mask failures in a subsequent one.
UNINSTALL_FAIL_COUNT=0

llama_product_entrypoint() {
  if [[ -x "${LLAMA_PRODUCT_ROOT}/scripts/manage.sh" ]]; then
    printf '%s\n' "${LLAMA_PRODUCT_ROOT}/scripts/manage.sh"
  elif [[ -x /usr/local/sbin/llama-manage ]]; then
    printf '%s\n' /usr/local/sbin/llama-manage
  else
    return 66
  fi
}

llama_product_manage() {
  local entrypoint
  entrypoint="$(llama_product_entrypoint)" || return $?
  "${entrypoint}" "$@"
}

llama_product_lifecycle() {
  local response
  response="$(llama_product_manage status --json 2>/dev/null)" || return $?
  python3 -c \
    'import json,sys; print(json.load(sys.stdin)["details"]["llama"]["lifecycle"])' \
    <<<"${response}"
}

forgejo_product_entrypoint() {
  if [[ -x "${FORGEJO_PRODUCT_ROOT}/scripts/manage.sh" ]]; then
    printf '%s\n' "${FORGEJO_PRODUCT_ROOT}/scripts/manage.sh"
  elif [[ -x /usr/local/sbin/forgejo-manage ]]; then
    printf '%s\n' /usr/local/sbin/forgejo-manage
  else
    return 66
  fi
}

forgejo_product_manage() {
  local entrypoint
  entrypoint="$(forgejo_product_entrypoint)" || return $?
  (
    local variable
    for variable in "${!FORGEJO_@}"; do
      case "${variable}" in
        FORGEJO_ARTIFACT_SHA256|FORGEJO_DISPOSABLE_VM_TEST|FORGEJO_TEST_RELEASE_BASE)
          ;;
        *) unset "${variable}" ;;
      esac
    done
    FORGEJO_MIGRATION_MANIFEST="/var/lib/ubuntu-zombie/components/forgejo" \
      FORGEJO_NONINTERACTIVE="$((ASSUME_YES || DRY_RUN))" \
      "${entrypoint}" "$@"
  )
}

forgejo_product_lifecycle() {
  local response
  response="$(forgejo_product_manage status --json 2>/dev/null)" || return $?
  python3 -c \
    'import json,sys; print(json.load(sys.stdin)["details"]["forgejo"]["lifecycle"])' \
    <<<"${response}"
}

# Shared colours/logging come from lib.sh. Keep the legacy C_YEL alias so the
# inline printf calls below (e.g. the [dry] glyph) need no churn.
lib_setup_colors
C_YEL="${C_YELLOW}"
if [[ -f "${REPO_ROOT}/VERSION" ]]; then
  SCRIPT_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/VERSION")"
else
  SCRIPT_VERSION="0000.00.00.00.00.00"
fi

# shellcheck source=scripts/component-registry.sh
. "${SCRIPT_DIR}/component-registry.sh"
component_remove_zombie() { remove_component_zombie; }
component_remove_forgejo() { remove_component_forgejo; }
component_remove_forgejo_runner() { remove_component_forgejo_runner; }
component_remove_llama() { remove_component_llama; }
register_component "${COMPONENT_ZOMBIE}" "" remove=component_remove_zombie
register_component "${COMPONENT_FORGEJO}" "" remove=component_remove_forgejo
register_component "${COMPONENT_FORGEJO_RUNNER}" "${COMPONENT_FORGEJO}" \
  remove=component_remove_forgejo_runner
register_component "${COMPONENT_LLAMA}" "" remove=component_remove_llama

component_names() {
  printf '%s' "${PUBLIC_COMPONENTS[*]}"
}

is_public_component() {
  local candidate="$1" component
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    [[ "${candidate}" == "${component}" ]] && return 0
  done
  return 1
}

validate_targets() {
  local target
  declare -A seen_targets=()
  for target in "${TARGET_ARGS[@]}"; do
    if ! is_public_component "${target}"; then
      die "Unknown component target '${target}'. Valid components: $(component_names)" 2
    fi
    if [[ -n "${seen_targets[${target}]+x}" ]]; then
      die "Duplicate component target '${target}'." 2
    fi
    seen_targets["${target}"]=1
  done
}


is_target_selected() {
  local candidate="$1" target
  (( ${#TARGET_ARGS[@]} == 0 )) && return 0
  for target in "${TARGET_ARGS[@]}"; do
    [[ "${candidate}" == "${target}" ]] && return 0
  done
  return 1
}

component_manifest_path() {
  local component="$1"
  is_public_component "${component}" || die "Unknown or invalid component name: ${component}. Valid components: $(component_names)" 2
  printf '%s/%s' "${COMPONENT_MANIFEST_DIR}" "${component}"
}

remove_component_manifest() {
  local component="$1" path manifest_parent_dir
  path="$(component_manifest_path "${component}")"
  manifest_parent_dir="$(dirname "${COMPONENT_MANIFEST_DIR}")"
  [[ "${DRY_RUN}" == "1" ]] && return 0
  rm -f -- "${path}"
  rmdir --ignore-fail-on-non-empty "${COMPONENT_MANIFEST_DIR}" 2>/dev/null || true
  rmdir --ignore-fail-on-non-empty "${manifest_parent_dir}" 2>/dev/null || true
}

clear_forgejo_runner_suboption() {
  local path="${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO}"
  local tmp
  [[ -f "${path}" ]] || return 0
  grep -Fqx 'suboptions=runner' "${path}" || return 0
  if (( DRY_RUN )); then
    run "clear the legacy runner suboption from the Forgejo manifest"
    return 0
  fi
  tmp="$(mktemp "${COMPONENT_MANIFEST_DIR}/.forgejo.XXXXXX")"
  awk '
    $0 == "suboptions=runner" { print "suboptions="; next }
    { print }
  ' "${path}" > "${tmp}"
  install -m 644 -o root -g root "${tmp}" "${path}"
  rm -f "${tmp}"
}

warn_remaining_components() {
  local target
  (( ${#TARGET_ARGS[@]} > 0 )) || return 0
  for target in "${PUBLIC_COMPONENTS[@]}"; do
    is_target_selected "${target}" && continue
    if [[ -e "$(component_manifest_path "${target}")" ]]; then
      warn "Component '${target}' remains installed; its manifest entry was preserved."
    fi
  done
}
usage() {
  # Heredoc instead of `sed -n '2,30p' "$0"` so the help output cannot
  # drift into the executable preamble when the header comment grows or
  # shrinks. See FIX-1-08.
  cat <<'EOF'
uninstall.sh
------------
Reverse the Ubuntu Zombie installer.

Removes the chat service, sudoers drop-in, generated helpers, policy,
logrotate rule, and (with
confirmation) the agent user account (default name `zombie`,
overridable with ZOMBIE_USER). Optionally archives the account's
home directory and /opt/ai-zombie/state/ to /var/backups/ before
deletion.

Usage:
  sudo ./uninstall.sh [component ...] # interactive
  sudo ./uninstall.sh -n|--dry-run    # preview
  sudo ./uninstall.sh forgejo --dry-run
                                      # remove only the Forgejo component
  sudo ./uninstall.sh forgejo-runner
                                      # remove only the Forgejo runner
  sudo ./uninstall.sh llama
                                      # remove only standalone llama.cpp
  sudo ./uninstall.sh zombie
                                      # remove only the zombie component
  sudo ./uninstall.sh --archive       # archive then remove
  sudo ./uninstall.sh -y|--yes       # skip confirmations
  sudo ./uninstall.sh --keep-agent   # do not remove user
  sudo ./uninstall.sh -q|--quiet     # warnings and errors only
  sudo ./uninstall.sh --no-color     # disable ANSI colour
  ./uninstall.sh -v|--version        # print the version and exit

Environment:
  ZOMBIE_USER=<name>   override the account name (default `zombie`).
                       `AGENT_USER` is still accepted as a legacy
                       alias so older installs can still be reversed.
  ZOMBIE_COLOR=auto|always|never   colour policy (default auto;
                       NO_COLOR is also honoured).

Notes:
  --archive and --keep-agent are only valid when the `zombie`
  component is being removed.
  Llama removal delegates to its product lifecycle and retains models and
  state. Complete purge requires llama-manage and its exact confirmation.

This script intentionally does NOT remove Node, Python, or other base
packages — those are normal Ubuntu software
that other things may depend on.
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)    usage; exit 0 ;;
    -v|--version) printf 'uninstall.sh %s\n' "${SCRIPT_VERSION}"; exit 0 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    --archive)    ARCHIVE=1; shift ;;
    --yes|-y)     ASSUME_YES=1; shift ;;
    --keep-agent) KEEP_AGENT=1; shift ;;
    -q|--quiet)   ZOMBIE_QUIET=1; shift ;;
    --no-color|--no-colour) export ZOMBIE_COLOR=never; lib_setup_colors; C_YEL="${C_YELLOW}"; shift ;;
    --) shift; TARGET_ARGS+=("$@"); break ;;
    -*)           die "Unknown argument: $1 (try --help)" 2 ;;
    *)            TARGET_ARGS+=("$1"); shift ;;
  esac
done
validate_targets

if (( ARCHIVE || KEEP_AGENT )); then
  if (( ${#TARGET_ARGS[@]} > 0 )) && ! is_target_selected "${COMPONENT_ZOMBIE}"; then
    (( ARCHIVE ))    && die "--archive is only valid when the zombie component is being removed." 2
    (( KEEP_AGENT )) && die "--keep-agent is only valid when the zombie component is being removed." 2
  fi
fi

# The splash is printed only for a real uninstall run: after argument
# parsing (so --help/--version/bad-usage stay concise) and honouring
# --quiet, exactly like install.sh.
(( ZOMBIE_QUIET )) || brand_splash "uninstall" "${SCRIPT_VERSION}"

# Validate user-controlled inputs before they are interpolated into any
# command string handed to `run` (which eval's it). Mirrors
# install.sh::validate_config so the uninstaller has the same guarantees.
# Runs before the EUID check so smoke tests can assert exit-code 2 for
# obviously-bad ZOMBIE_USER values without needing root. See FIX-2-01.
is_supported_agent_username() {
  [[ "$1" =~ ^[a-z]([a-z0-9_-]{0,30}[a-z0-9]|[a-z0-9]{0,31})$ ]] || return 1
  [[ "$1" != "root" && "$1" != "nobody" ]]
}

is_safe_absolute_path() {
  [[ "$1" == /* ]] || return 1
  [[ "$1" =~ ^/[A-Za-z0-9._/+:-]+$ ]] || return 1
  # Reject path traversal: no '..' component anywhere in the path.
  [[ "$1" == */../* || "$1" == *"/.." ]] && return 1
  return 0
}

validate_config() {
  if ! is_supported_agent_username "${AGENT_USER}"; then
    printf '%s[x]%s Invalid agent username %q. Use a non-reserved lowercase Linux username (letters first; then letters, digits, underscore, hyphen; max 32 chars; no trailing punctuation).\n' \
      "${C_RED}" "${C_RESET}" "${AGENT_USER}" >&2
    exit 2
  fi
  if ! is_safe_absolute_path "${ZOMBIE_DIR}"; then
    printf '%s[x]%s ZOMBIE_DIR must be an absolute path using only safe path characters; got %q\n' \
      "${C_RED}" "${C_RESET}" "${ZOMBIE_DIR}" >&2
    exit 2
  fi
  if ! is_safe_absolute_path "${BACKUP_DIR}"; then
    printf '%s[x]%s BACKUP_DIR must be an absolute path using only safe path characters; got %q\n' \
      "${C_RED}" "${C_RESET}" "${BACKUP_DIR}" >&2
    exit 2
  fi
  if ! is_safe_absolute_path "${COMPONENT_MANIFEST_DIR}"; then
    printf '%s[x]%s ZOMBIE_COMPONENT_MANIFEST_DIR must be an absolute safe path without path traversal; got %q\n' \
      "${C_RED}" "${C_RESET}" "${COMPONENT_MANIFEST_DIR}" >&2
    exit 2
  fi
}
validate_config

(( DRY_RUN )) || [[ ${EUID} -eq 0 ]] || die "Run with sudo: sudo $0"

run() {
  # Defensive guard: callers must pass exactly one composed command string,
  # not argv-style arguments (which would be silently dropped under
  # `eval "$1"`). See FIX-2-11.
  if (( $# != 1 )); then
    printf '%s[x]%s run() takes exactly one composed command string; got %d args: %s\n' \
      "${C_RED}" "${C_RESET}" "$#" "$*" >&2
    exit 1
  fi
  if [[ "${DRY_RUN}" == "1" ]]; then
    printf '%s[dry]%s %s\n' "${C_YEL}" "${C_RESET}" "$1"
  else
    # Callers pass a single string with shell metacharacters (redirections,
    # `||`, globbing). Re-evaluate that one string so the quoting survives.
    # See FIX-1-06.
    # shellcheck disable=SC2294 # eval on a single composed command string is intentional.
    eval "$1"
  fi
}

shell_quote() {
  # Quote a single token before embedding it in any composed command string
  # that will be evaluated. Bash printf %q uses backslash-style escaping,
  # which keeps dry-run output readable while preserving safety.
  if (( $# != 1 )); then
    printf '%s[x]%s shell_quote() takes exactly one token; got %d args: %s\n' \
      "${C_RED}" "${C_RESET}" "$#" "$*" >&2
    exit 1
  fi
  printf '%q' "$1"
}

run_or_warn() {
  # Run a non-critical cleanup command. Failures are reported in the final
  # exit code, but they must not stop later uninstall steps from running.
  local description="$1"
  local command="$2"
  if [[ "${DRY_RUN}" == "1" ]]; then
    run "${command}"
    return 0
  fi
  set +e
  # shellcheck disable=SC2294 # Execute the composed cleanup command after shell_quote expansions.
  eval "${command}"
  local rc=$?
  set -e
  if (( rc != 0 )); then
    warn "${description} failed (exit ${rc}); continuing cleanup."
    UNINSTALL_FAIL_COUNT=$((UNINSTALL_FAIL_COUNT + 1))
    UNINSTALL_EXIT=1
  fi
  return 0
}

remove_tree_checked() {
  # Remove a directory tree and verify it is actually gone before reporting
  # success; stubborn paths are errors, but cleanup should still continue.
  local path="$1"
  local label="$2"
  local quoted
  quoted="$(shell_quote "${path}")"
  if [[ "${DRY_RUN}" == "1" ]]; then
    run "rm -rf -- ${quoted}"
    ok "Would remove ${label}"
    return 0
  fi
  set +e
  rm -rf -- "${path}"
  local rc=$?
  set -e
  if (( rc != 0 )); then
    warn "Failed to remove ${label} (exit ${rc}); continuing cleanup."
    UNINSTALL_FAIL_COUNT=$((UNINSTALL_FAIL_COUNT + 1))
    UNINSTALL_EXIT=1
    return 0
  fi
  if [[ -e "${path}" ]]; then
    warn "Failed to remove ${label}; path still exists: ${path}"
    UNINSTALL_FAIL_COUNT=$((UNINSTALL_FAIL_COUNT + 1))
    UNINSTALL_EXIT=1
    return 0
  fi
  ok "Removed ${label}"
  return 0
}

confirm() {
  local prompt="$1"
  [[ "${ASSUME_YES}" == "1" ]] && return 0
  read -r -p "${prompt} Type YES to proceed: " ans
  [[ "${ans}" == "YES" ]]
}

remove_component_forgejo_runner() {
  local fail_count_before="${UNINSTALL_FAIL_COUNT}"

  if [[ -f /etc/systemd/system/forgejo-runner.service \
      || -x /usr/local/bin/forgejo-runner \
      || -d /var/lib/forgejo-runner \
      || -f "${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO_RUNNER}" ]]; then
    info "Removing Forgejo runner component"
    run "systemctl disable --now forgejo-runner.service 2>/dev/null || true"
    run "rm -f /etc/systemd/system/forgejo-runner.service"
    run_or_warn "systemctl daemon-reload" "systemctl daemon-reload"
    run "rm -f /usr/local/bin/forgejo-runner"
    if [[ -d /var/lib/forgejo-runner ]]; then
      remove_tree_checked \
        "/var/lib/forgejo-runner" \
        "/var/lib/forgejo-runner (runner state)"
    fi
    if id forgejo-runner >/dev/null 2>&1; then
      if confirm "Remove the forgejo-runner system user?"; then
        run_or_warn "Remove user forgejo-runner" \
          "deluser forgejo-runner >/dev/null 2>&1 || userdel forgejo-runner"
      fi
    fi
    ok "Forgejo runner component removal finished."
  fi

  if (( UNINSTALL_FAIL_COUNT == fail_count_before )); then
    clear_forgejo_runner_suboption
    remove_component_manifest "${COMPONENT_FORGEJO_RUNNER}"
  else
    warn "Keeping Forgejo runner manifest because removal finished with errors."
  fi
  warn_remaining_components
}

remove_component_forgejo() {
  local fail_count_before="${UNINSTALL_FAIL_COUNT}" lifecycle="" manifest
  local -a product_arguments=(uninstall)
  manifest="${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO}"
  if (( ${#TARGET_ARGS[@]} == 0 )) && [[ ! -e "${manifest}" ]]; then
    lifecycle="$(forgejo_product_lifecycle 2>/dev/null || true)"
    [[ "${lifecycle}" == "legacy" || "${lifecycle}" == "active" \
        || "${lifecycle}" == "suspended" || "${lifecycle}" == "retained" ]] \
      || return 0
  fi
  if [[ -f /etc/systemd/system/forgejo-runner.service \
      || -x /usr/local/bin/forgejo-runner \
      || -d /var/lib/forgejo-runner ]]; then
    remove_component_forgejo_runner
  fi
  (( DRY_RUN )) && product_arguments+=(--dry-run)
  if (( ASSUME_YES )); then
    product_arguments+=(
      --yes
      --purge
      --confirmation "DELETE FORGEJO STATE"
      --non-interactive
    )
  fi
  info "Delegating standalone Forgejo removal to its product lifecycle"
  if ! forgejo_product_manage "${product_arguments[@]}"; then
    warn "Independent Forgejo product removal failed."
    UNINSTALL_FAIL_COUNT=$((UNINSTALL_FAIL_COUNT + 1))
    UNINSTALL_EXIT=1
  fi
  if (( UNINSTALL_FAIL_COUNT == fail_count_before )); then
    remove_component_manifest "${COMPONENT_FORGEJO_RUNNER}"
    remove_component_manifest "${COMPONENT_FORGEJO}"
  else
    warn "Keeping Forgejo manifest because removal finished with errors."
  fi
  warn_remaining_components
}

remove_component_llama() {
  local fail_count_before="${UNINSTALL_FAIL_COUNT}"
  local lifecycle="" manifest
  local -a arguments=(uninstall)
  manifest="${COMPONENT_MANIFEST_DIR}/${COMPONENT_LLAMA}"
  if (( ${#TARGET_ARGS[@]} == 0 )) && [[ ! -e "${manifest}" ]]; then
    lifecycle="$(llama_product_lifecycle 2>/dev/null || true)"
    [[ "${lifecycle}" == "legacy" ]] || return 0
  fi
  (( DRY_RUN )) && arguments+=(--dry-run)
  (( ASSUME_YES )) && arguments+=(--yes)

  info "Delegating standalone Llama removal to its product lifecycle"
  if ! llama_product_manage "${arguments[@]}"; then
    warn "Independent Llama product removal failed."
    UNINSTALL_FAIL_COUNT=$((UNINSTALL_FAIL_COUNT + 1))
    UNINSTALL_EXIT=1
  fi
  if (( UNINSTALL_FAIL_COUNT == fail_count_before )); then
    remove_component_manifest "${COMPONENT_LLAMA}"
  else
    warn "Keeping llama manifest because removal finished with errors."
  fi
  warn_remaining_components
}

remove_component_zombie() {
  local fail_count_before="${UNINSTALL_FAIL_COUNT}"
  local unit f orphan_name STAMP _pkg _shim _path _target _literal rc

  # -------------------------------------------------------------------
  # 1. Stop and disable the chat service + health timer.
  # -------------------------------------------------------------------
  info "Stopping ubuntu-zombie services"
  run "systemctl disable --now ubuntu-zombie-health.timer 2>/dev/null || true"
  run "systemctl disable --now ubuntu-zombie-health.service 2>/dev/null || true"
  run "systemctl disable --now ubuntu-zombie-chat.service   2>/dev/null || true"

  # -------------------------------------------------------------------
  # 2. Remove systemd units and sudoers drop-ins.
  # -------------------------------------------------------------------
  info "Removing systemd units and sudoers drop-ins"
  for unit in ubuntu-zombie-chat.service ubuntu-zombie-health.service ubuntu-zombie-health.timer; do
    run "rm -f /etc/systemd/system/${unit}"
  done
  run_or_warn "systemctl daemon-reload" "systemctl daemon-reload"

  run "rm -f /etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie"
  # Also remove drop-ins from any previous install that used a different
  # ZOMBIE_USER, so a stale NOPASSWD:ALL entry cannot be left behind.
  # See FIX-2-04. The shell does the glob expansion locally; the only
  # metacharacters in $f come from the kernel's directory listing, and
  # FIX-2-01 guarantees AGENT_USER is safe so we cannot accidentally
  # delete the current-account drop-in twice via an odd glob expansion.
  shopt -s nullglob
  for f in /etc/sudoers.d/90-*-ubuntu-zombie; do
    case "$f" in
      /etc/sudoers.d/90-"${AGENT_USER}"-ubuntu-zombie) continue ;;
    esac
    orphan_name="${f#/etc/sudoers.d/90-}"
    orphan_name="${orphan_name%-ubuntu-zombie}"
    warn "Removing orphaned sudoers drop-in for user '${orphan_name}': ${f}"
    if id "${orphan_name}" >/dev/null 2>&1; then
      warn "  account '${orphan_name}' still exists; remove it manually if no longer wanted."
    fi
    run "rm -f -- $(shell_quote "${f}")"
  done
  shopt -u nullglob

  # -------------------------------------------------------------------
  # 3. Remove policy/logrotate and legacy desktop artefacts.
  # -------------------------------------------------------------------
  info "Removing policy, logrotate rule, and legacy desktop artefacts"
  run "rm -f /etc/logrotate.d/ubuntu-zombie"

  # Reverse the installer's "Prevent sleep, suspend, and screen lock"
  # masking so the desktop can sleep again after the product is gone.
  info "Unmasking sleep/suspend targets"
  run "systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true"

  # Remove the installer-specific unattended-upgrades reboot policy so
  # the machine no longer auto-reboots at 04:00 after uninstall. The
  # stock 20auto-upgrades file is left as-is: unattended upgrades are a
  # sensible default and other software may rely on them.
  if [[ -f /etc/apt/apt.conf.d/52unattended-upgrades-local ]]; then
    info "Removing installer unattended-upgrades auto-reboot policy"
    run "rm -f /etc/apt/apt.conf.d/52unattended-upgrades-local"
  fi

  # -------------------------------------------------------------------
  # 4. Archive user data if requested.
  # -------------------------------------------------------------------
  STAMP="$(date -u +%Y%m%d-%H%M%S)"
  if [[ "${ARCHIVE}" == "1" ]]; then
    info "Archiving ${AGENT_HOME} and ${ZOMBIE_DIR}/state to ${BACKUP_DIR}"
    # Only assert mode when creating the directory new; otherwise leave the
    # existing mode/ownership alone (e.g. /var/backups must stay 0755 so dpkg,
    # cracklib, and audit collectors keep working). See FIX-1-04.
    if [[ ! -d "${BACKUP_DIR}" ]]; then
      run "install -d -m 700 ${BACKUP_DIR}"
    fi
    # Create the tarballs with mode 0600 so provider tokens and other
    # secrets are not world-readable when BACKUP_DIR itself
    # is 0755 (the Ubuntu default for /var/backups). See FIX-2-02.
    if [[ -d "${AGENT_HOME}" ]]; then
      run "(umask 077 && tar -czf ${BACKUP_DIR}/ubuntu-zombie-home-${STAMP}.tar.gz -C / home/${AGENT_USER})"
    fi
    if [[ -d "${ZOMBIE_DIR}/state" ]]; then
      run "(umask 077 && tar -czf ${BACKUP_DIR}/ubuntu-zombie-state-${STAMP}.tar.gz -C ${ZOMBIE_DIR} state)"
    fi
  fi

  # -------------------------------------------------------------------
  # 5. Remove /opt/ai-zombie (state/secrets only with confirmation).
  # -------------------------------------------------------------------
  if [[ -d "${ZOMBIE_DIR}" ]]; then
    if confirm "Remove ${ZOMBIE_DIR} (includes secrets, state, and chat history)?"; then
      remove_tree_checked "${ZOMBIE_DIR}" "${ZOMBIE_DIR}"
    else
      warn "Keeping ${ZOMBIE_DIR}. Privileged code under it is still on disk."
    fi
  fi

  # -------------------------------------------------------------------
  # 5b. Remove globally-installed npm packages we own.
  # -------------------------------------------------------------------
  # The installer pulls @earendil-works/pi-ai and
  # @earendil-works/pi-coding-agent via ``npm install -g``.
  # ``rm -rf /opt/ai-zombie`` removes our source tree but leaves the
  # Node packages installed system-wide. Uninstall them explicitly so
  # the host is left clean.
  if command -v npm >/dev/null 2>&1; then
    for _pkg in @earendil-works/pi-coding-agent @earendil-works/pi-ai; do
      if npm ls -g --depth=0 "${_pkg}" >/dev/null 2>&1; then
        if confirm "Remove global npm package ${_pkg}?"; then
          run_or_warn "Remove global npm package ${_pkg}" \
            "npm uninstall -g $(shell_quote "${_pkg}")"
        fi
      fi
    done
  fi

  # -------------------------------------------------------------------
  # 5c. Remove /usr/local/bin symlinks installed by install.sh.
  # -------------------------------------------------------------------
  # install.sh adds these as `ln -sf ${ZOMBIE_DIR}/bin/...` shims so the
  # CLI is on PATH for the operator. Without explicit cleanup they become
  # dangling symlinks after step 5 removes ${ZOMBIE_DIR}. Only remove a
  # link if it is a symlink whose target lives under ${ZOMBIE_DIR}, so we
  # never delete an operator-owned binary of the same name.
  info "Removing /usr/local/bin shims that point into ${ZOMBIE_DIR}"
  for _shim in zombie-chat audit-recent secrets-edit zombie-health zombie-diagnostics zombie-verify; do
    _path="/usr/local/bin/${_shim}"
    if [[ -L "${_path}" ]]; then
      _target="$(readlink -f "${_path}" 2>/dev/null || true)"
      case "${_target}" in
        "${ZOMBIE_DIR}"/*) run "rm -f -- $(shell_quote "${_path}")" ;;
        "") # broken symlink; check the literal target instead.
          _literal="$(readlink "${_path}" 2>/dev/null || true)"
          case "${_literal}" in
            "${ZOMBIE_DIR}"/*) run "rm -f -- $(shell_quote "${_path}")" ;;
          esac
          ;;
      esac
    fi
  done

  # -------------------------------------------------------------------
  # 6. Remove /etc/ubuntu-zombie policy config.
  # -------------------------------------------------------------------
  if [[ -d /etc/ubuntu-zombie ]]; then
    if confirm "Remove /etc/ubuntu-zombie (policy.yaml)?"; then
      remove_tree_checked "/etc/ubuntu-zombie" "/etc/ubuntu-zombie"
    fi
  fi

  # -------------------------------------------------------------------
  # 7. Remove the agent user (last, so its home is still owned).
  # -------------------------------------------------------------------
  if [[ "${KEEP_AGENT}" == "1" ]]; then
    info "Keeping user ${AGENT_USER} (--keep-agent)."
  elif id "${AGENT_USER}" >/dev/null 2>&1; then
    if confirm "Remove the ${AGENT_USER} user and ${AGENT_HOME} ?"; then
      # Kill any session first so userdel does not refuse.
      run "loginctl terminate-user ${AGENT_USER} 2>/dev/null || true"
      run "pkill -KILL -u ${AGENT_USER} 2>/dev/null || true"
      sleep 1
      # FIX-2-05: do not swallow removal failures. Capture the rc and verify
      # the account is actually gone before printing the success line.
      if [[ "${DRY_RUN}" == "1" ]]; then
        run "deluser --remove-home ${AGENT_USER} 2>/dev/null || userdel -r ${AGENT_USER}"
        ok "Would remove user ${AGENT_USER}"
      else
        set +e
        deluser --remove-home "${AGENT_USER}" >/dev/null 2>&1
        rc=$?
        if (( rc != 0 )); then
          userdel -r "${AGENT_USER}" >/dev/null 2>&1
          rc=$?
        fi
        set -e
        if (( rc == 0 )) && ! id "${AGENT_USER}" >/dev/null 2>&1; then
          ok "Removed user ${AGENT_USER}"
          # FIX-2-12: drop the now-orphaned primary group so a future
          # `adduser` of the same name does not pick up unexpected file
          # ownership. --only-if-empty makes this safe.
          if getent group "${AGENT_USER}" >/dev/null 2>&1; then
            run "delgroup --only-if-empty ${AGENT_USER} >/dev/null 2>&1 || true"
          fi
          # Older installs wrote /var/lib/AccountsService/users/${AGENT_USER}
          # to pin the XSession; userdel does not clean it up, leaving a
          # stale AccountsService entry referencing a missing account.
          # Remove it (existence-guarded) once the user is actually gone.
          if [[ -f "/var/lib/AccountsService/users/${AGENT_USER}" ]]; then
            run "rm -f /var/lib/AccountsService/users/${AGENT_USER}"
          fi
        else
          warn "Failed to remove user ${AGENT_USER}; see 'who', 'loginctl list-sessions',"
          warn "  'lsof +D ${AGENT_HOME}' and re-run after the processes are gone."
          UNINSTALL_FAIL_COUNT=$((UNINSTALL_FAIL_COUNT + 1))
          UNINSTALL_EXIT=1
        fi
      fi
    else
      warn "Keeping user ${AGENT_USER}. Its home and authorized_keys remain."
    fi
  fi

  if (( UNINSTALL_FAIL_COUNT == fail_count_before )); then
    remove_component_manifest "${COMPONENT_ZOMBIE}"
  else
    warn "Keeping zombie manifest because removal finished with errors."
  fi
  warn_remaining_components
}

(( ZOMBIE_QUIET )) || printf '%s== ubuntu-zombie uninstall ==%s\n\n' "${C_BOLD}" "${C_RESET}"
[[ "${DRY_RUN}" == "1" ]] && warn "Dry-run mode: nothing will be changed."
if (( ${#TARGET_ARGS[@]} > 0 )); then
  info "Selected components: ${TARGET_ARGS[*]}"
else
  info "Selected components: ${PUBLIC_COMPONENTS[*]}"
fi

# Execute component removal in reverse registry order so future dependants are
# removed before the components they may rely on.
validate_component_registry "remove"
for (( component_index = ${#PUBLIC_COMPONENTS[@]} - 1; component_index >= 0; component_index-- )); do
  component="${PUBLIC_COMPONENTS[component_index]}"
  is_target_selected "${component}" || continue
  component_dispatch_hook "${component}" remove
done

echo
if (( UNINSTALL_EXIT != 0 )); then
  warn "Uninstall finished with errors (exit ${UNINSTALL_EXIT})."
else
  ok "Uninstall complete."
fi
(( ZOMBIE_QUIET )) || cat <<EOF

Left intact on purpose:
  - Node, Python, and other shared runtime packages
    (remove them with apt only if you know nothing else needs them).
  - The NodeSource apt repository (/etc/apt/sources.list.d/nodesource.sources,
    /usr/share/keyrings/nodesource.gpg, /etc/apt/preferences.d/nodejs) is
    kept so an installed Node keeps receiving updates. Remove those three
    files if you also remove the nodejs package.
  - /var/log/ubuntu-zombie/ and /var/log/ubuntu-zombie-install.log
    are retained for audit. Remove them with:
        sudo rm -rf /var/log/ubuntu-zombie /var/log/ubuntu-zombie-install.log
EOF

exit "${UNINSTALL_EXIT}"
