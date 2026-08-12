#!/usr/bin/env bash
#
# uninstall.sh
# ------------
# Reverse the Ubuntu AI System Administrator installer.
#
# Removes the chat service, sudoers drop-in, generated helpers, policy,
# logrotate rule, and (with
# confirmation) the agent user account (default name `ai-sys-admin`,
# overridable with AI_SYS_ADMIN_USER). Optionally archives the account's
# home directory and the configured install root's state to /var/backups/ before
# deletion.
#
# Usage:
#   sudo ./uninstall.sh                # interactive
#   sudo ./uninstall.sh -n|--dry-run   # preview
#   sudo ./uninstall.sh --archive      # archive then remove
#   sudo ./uninstall.sh -y|--yes       # skip confirmations
#   sudo ./uninstall.sh --keep-agent   # do not remove user
#   sudo ./uninstall.sh -q|--quiet     # warnings and errors only
#   sudo ./uninstall.sh --no-color     # disable ANSI colour
#   ./uninstall.sh -v|--version        # print the version and exit
#
# Environment:
#   AI_SYS_ADMIN_USER=<name>   override the account name (default `ai-sys-admin`).
#                        `AGENT_USER` is still accepted as a legacy
#                        alias so older installs can still be reversed.
#   AI_SYS_ADMIN_DIR=<path>    override the install root (default `/opt/ai-system-administrator`).
#   AI_SYS_ADMIN_COLOR=auto|always|never   colour policy (default auto;
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

AGENT_USER="${AI_SYS_ADMIN_USER:-${AGENT_USER:-ai-sys-admin}}"
AGENT_HOME="/home/${AGENT_USER}"
AI_SYS_ADMIN_DIR="${AI_SYS_ADMIN_DIR:-/opt/ai-system-administrator}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups}"

DRY_RUN=0
ARCHIVE=0
ASSUME_YES=0
KEEP_AGENT=0
# Track recoverable failures from the start so early cleanup can continue
# through later steps while still returning a non-zero final status.
UNINSTALL_EXIT=0
UNINSTALL_FAIL_COUNT=0

# Shared colours/logging come from lib.sh. Keep the legacy C_YEL alias so the
# inline printf calls below (e.g. the [dry] glyph) need no churn.
lib_setup_colors
C_YEL="${C_YELLOW}"
if [[ -f "${REPO_ROOT}/VERSION" ]]; then
  SCRIPT_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/VERSION")"
else
  SCRIPT_VERSION="0000.00.00.00.00.00"
fi

usage() {
  # Heredoc instead of `sed -n '2,30p' "$0"` so the help output cannot
  # drift into the executable preamble when the header comment grows or
  # shrinks. See FIX-1-08.
  cat <<'EOF'
uninstall.sh
------------
Reverse the Ubuntu AI System Administrator installer.

Removes the chat service, sudoers drop-in, generated helpers, policy,
logrotate rule, and (with
confirmation) the agent user account (default name `ai-sys-admin`,
overridable with AI_SYS_ADMIN_USER). Optionally archives the account's
home directory and the configured install root's state to
/var/backups/ before deletion.

Usage:
  sudo ./uninstall.sh                 # interactive
  sudo ./uninstall.sh -n|--dry-run    # preview
  sudo ./uninstall.sh --archive       # archive then remove
  sudo ./uninstall.sh -y|--yes       # skip confirmations
  sudo ./uninstall.sh --keep-agent   # do not remove user
  sudo ./uninstall.sh -q|--quiet     # warnings and errors only
  sudo ./uninstall.sh --no-color     # disable ANSI colour
  ./uninstall.sh -v|--version        # print the version and exit

Environment:
  AI_SYS_ADMIN_USER=<name>   override the account name (default `ai-sys-admin`).
                       `AGENT_USER` is still accepted as a legacy
                       alias so older installs can still be reversed.
  AI_SYS_ADMIN_DIR=<path>    override the install root (default `/opt/ai-system-administrator`).
  AI_SYS_ADMIN_COLOR=auto|always|never   colour policy (default auto;
                       NO_COLOR is also honoured).

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
    -q|--quiet)   AI_SYS_ADMIN_QUIET=1; shift ;;
    --no-color|--no-colour) export AI_SYS_ADMIN_COLOR=never; lib_setup_colors; C_YEL="${C_YELLOW}"; shift ;;
    --) shift
        (( $# == 0 )) || die "Unexpected argument: $1 (try --help)" 2
        break ;;
    -*)           die "Unknown argument: $1 (try --help)" 2 ;;
    *)            die "Unexpected argument: $1 (try --help)" 2 ;;
  esac
done

# The splash is printed only for a real uninstall run: after argument
# parsing (so --help/--version/bad-usage stay concise) and honouring
# --quiet, exactly like install.sh.
(( AI_SYS_ADMIN_QUIET )) || brand_splash "uninstall" "${SCRIPT_VERSION}"

# Validate user-controlled inputs before they are interpolated into any
# command string handed to `run` (which eval's it). Mirrors
# install.sh::validate_config so the uninstaller has the same guarantees.
# Runs before the EUID check so smoke tests can assert exit-code 2 for
# obviously-bad AI_SYS_ADMIN_USER values without needing root. See FIX-2-01.
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
  if ! is_safe_absolute_path "${AI_SYS_ADMIN_DIR}"; then
    printf '%s[x]%s AI_SYS_ADMIN_DIR must be an absolute path using only safe path characters; got %q\n' \
      "${C_RED}" "${C_RESET}" "${AI_SYS_ADMIN_DIR}" >&2
    exit 2
  fi
  if ! is_safe_absolute_path "${BACKUP_DIR}"; then
    printf '%s[x]%s BACKUP_DIR must be an absolute path using only safe path characters; got %q\n' \
      "${C_RED}" "${C_RESET}" "${BACKUP_DIR}" >&2
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

remove_ai_sys_admin() {
  local unit f orphan_name STAMP _pkg _shim _path _target _literal rc

  # -------------------------------------------------------------------
  # 1. Stop and disable the chat service + health timer.
  # -------------------------------------------------------------------
  info "Stopping ubuntu-ai-system-administrator services"
  run "systemctl disable --now ubuntu-ai-system-administrator-health.timer 2>/dev/null || true"
  run "systemctl disable --now ubuntu-ai-system-administrator-health.service 2>/dev/null || true"
  run "systemctl disable --now ubuntu-ai-system-administrator-chat.service   2>/dev/null || true"

  # -------------------------------------------------------------------
  # 2. Remove systemd units and sudoers drop-ins.
  # -------------------------------------------------------------------
  info "Removing systemd units and sudoers drop-ins"
  for unit in ubuntu-ai-system-administrator-chat.service ubuntu-ai-system-administrator-health.service ubuntu-ai-system-administrator-health.timer; do
    run "rm -f /etc/systemd/system/${unit}"
  done
  run_or_warn "systemctl daemon-reload" "systemctl daemon-reload"

  run "rm -f /etc/sudoers.d/90-${AGENT_USER}-ubuntu-ai-system-administrator"
  # Also remove drop-ins from any previous install that used a different
  # AI_SYS_ADMIN_USER, so a stale NOPASSWD:ALL entry cannot be left behind.
  # See FIX-2-04. The shell does the glob expansion locally; the only
  # metacharacters in $f come from the kernel's directory listing, and
  # FIX-2-01 guarantees AGENT_USER is safe so we cannot accidentally
  # delete the current-account drop-in twice via an odd glob expansion.
  shopt -s nullglob
  for f in /etc/sudoers.d/90-*-ubuntu-ai-system-administrator; do
    case "$f" in
      /etc/sudoers.d/90-"${AGENT_USER}"-ubuntu-ai-system-administrator) continue ;;
    esac
    orphan_name="${f#/etc/sudoers.d/90-}"
    orphan_name="${orphan_name%-ubuntu-ai-system-administrator}"
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
  run "rm -f /etc/logrotate.d/ubuntu-ai-system-administrator"

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
    info "Archiving ${AGENT_HOME} and ${AI_SYS_ADMIN_DIR}/state to ${BACKUP_DIR}"
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
      run "(umask 077 && tar -czf ${BACKUP_DIR}/ubuntu-ai-system-administrator-home-${STAMP}.tar.gz -C / home/${AGENT_USER})"
    fi
    if [[ -d "${AI_SYS_ADMIN_DIR}/state" ]]; then
      run "(umask 077 && tar -czf ${BACKUP_DIR}/ubuntu-ai-system-administrator-state-${STAMP}.tar.gz -C ${AI_SYS_ADMIN_DIR} state)"
    fi
  fi

  # -------------------------------------------------------------------
  # 5. Remove /opt/ai-system-administrator (state/secrets only with confirmation).
  # -------------------------------------------------------------------
  if [[ -d "${AI_SYS_ADMIN_DIR}" ]]; then
    if confirm "Remove ${AI_SYS_ADMIN_DIR} (includes secrets, state, and chat history)?"; then
      remove_tree_checked "${AI_SYS_ADMIN_DIR}" "${AI_SYS_ADMIN_DIR}"
    else
      warn "Keeping ${AI_SYS_ADMIN_DIR}. Privileged code under it is still on disk."
    fi
  fi

  # -------------------------------------------------------------------
  # 5b. Remove globally-installed npm packages we own.
  # -------------------------------------------------------------------
  # The installer pulls @earendil-works/pi-ai and
  # @earendil-works/pi-coding-agent via ``npm install -g``.
  # ``rm -rf /opt/ai-system-administrator`` removes our source tree but leaves the
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
  # install.sh adds these as `ln -sf ${AI_SYS_ADMIN_DIR}/bin/...` shims so the
  # CLI is on PATH for the operator. Without explicit cleanup they become
  # dangling symlinks after step 5 removes ${AI_SYS_ADMIN_DIR}. Only remove a
  # link if it is a symlink whose target lives under ${AI_SYS_ADMIN_DIR}, so we
  # never delete an operator-owned binary of the same name.
  info "Removing /usr/local/bin shims that point into ${AI_SYS_ADMIN_DIR}"
  for _shim in chat audit-recent secrets-edit ai-system-administrator-health ai-system-administrator-diagnostics ai-system-administrator-verify; do
    _path="/usr/local/bin/${_shim}"
    if [[ -L "${_path}" ]]; then
      _target="$(readlink -f "${_path}" 2>/dev/null || true)"
      case "${_target}" in
        "${AI_SYS_ADMIN_DIR}"/*) run "rm -f -- $(shell_quote "${_path}")" ;;
        "") # broken symlink; check the literal target instead.
          _literal="$(readlink "${_path}" 2>/dev/null || true)"
          case "${_literal}" in
            "${AI_SYS_ADMIN_DIR}"/*) run "rm -f -- $(shell_quote "${_path}")" ;;
          esac
          ;;
      esac
    fi
  done

  # -------------------------------------------------------------------
  # 6. Remove /etc/ubuntu-ai-system-administrator policy config.
  # -------------------------------------------------------------------
  if [[ -d /etc/ubuntu-ai-system-administrator ]]; then
    if confirm "Remove /etc/ubuntu-ai-system-administrator (policy.yaml)?"; then
      remove_tree_checked "/etc/ubuntu-ai-system-administrator" "/etc/ubuntu-ai-system-administrator"
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
}

(( AI_SYS_ADMIN_QUIET )) || printf '%s== ubuntu-ai-system-administrator uninstall ==%s\n\n' "${C_BOLD}" "${C_RESET}"
[[ "${DRY_RUN}" == "1" ]] && warn "Dry-run mode: nothing will be changed."
remove_ai_sys_admin

echo
if (( UNINSTALL_EXIT != 0 )); then
  warn "Uninstall finished with errors (exit ${UNINSTALL_EXIT})."
else
  ok "Uninstall complete."
fi
(( AI_SYS_ADMIN_QUIET )) || cat <<EOF

Left intact on purpose:
  - Node, Python, and other shared runtime packages
    (remove them with apt only if you know nothing else needs them).
  - The NodeSource apt repository (/etc/apt/sources.list.d/nodesource.sources,
    /usr/share/keyrings/nodesource.gpg, /etc/apt/preferences.d/nodejs) is
    kept so an installed Node keeps receiving updates. Remove those three
    files if you also remove the nodejs package.
  - /var/log/ubuntu-ai-system-administrator/ and /var/log/ubuntu-ai-system-administrator-install.log
    are retained for audit. Remove them with:
        sudo rm -rf /var/log/ubuntu-ai-system-administrator /var/log/ubuntu-ai-system-administrator-install.log
EOF

exit "${UNINSTALL_EXIT}"
