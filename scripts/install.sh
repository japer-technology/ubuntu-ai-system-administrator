#!/usr/bin/env bash
#
# install.sh
# ----------
# Ubuntu AI System Administrator: baseline installer + chat service.
#
# Turn a normal Ubuntu Desktop LTS PC into a machine with a resident
# AI Systems Administrator, authenticated by the configured token
# provider, contactable through a private loopback chat UI.
#
# Read README.md before running.
#
# Subcommands:
#   install     Full install (default). Idempotent.
#   verify      Read-only state check (no mutation).
#   doctor      Explain what is wrong and likely fixes.
#   repair      Apply known-safe fixes for common drift.
#   uninstall   Delegate to uninstall.sh.
#
# Common env vars (run `install.sh --help` for the full list):
#   ZOMBIE_NONINTERACTIVE=1     skip prompts for fully unattended installs.
#   ZOMBIE_USER="zombie"        name of the local account created as the
#                               operating identity of the AI Systems
#                               Administrator. Defaults to `zombie`. The
#                               legacy name `AGENT_USER` is still
#                               accepted for backward compatibility.
#   ZOMBIE_CHAT_PORT=7878       loopback-only chat UI port.

set -Eeuo pipefail

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

readonly SCRIPT_NAME="install.sh"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly SCRIPT_DIR
# Repository root is one level above scripts/. The installer reads VERSION and
# the payload from the repo root so it can be invoked from anywhere.
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
readonly REPO_ROOT

# Shared UX helpers (colours, status vocabulary, retry, timing, spinner,
# prompt loops). Sourced so install.sh, uninstall.sh, and build-deb.sh
# present an identical look and behaviour.
# shellcheck source=scripts/lib.sh
if [[ -r "${SCRIPT_DIR}/lib.sh" ]]; then
  . "${SCRIPT_DIR}/lib.sh"
else
  printf 'install.sh: required library %s/lib.sh not found.\n' "${SCRIPT_DIR}" >&2
  exit 1
fi

if [[ -f "${REPO_ROOT}/VERSION" ]]; then
  SCRIPT_VERSION="$(tr -d '[:space:]' < "${REPO_ROOT}/VERSION")"
else
  SCRIPT_VERSION="0000.00.00.00.00.00"
fi
readonly SCRIPT_VERSION

AGENT_USER="${ZOMBIE_USER:-${AGENT_USER:-zombie}}"
AGENT_HOME="/home/${AGENT_USER}"
ZOMBIE_DIR="${ZOMBIE_DIR:-/opt/ai-zombie}"
ZOMBIE_ETC="/etc/ubuntu-zombie"
ZOMBIE_LOG_DIR="/var/log/ubuntu-zombie"
CHAT_PORT="${ZOMBIE_CHAT_PORT:-7878}"
LOG_FILE="${LOG_FILE:-/var/log/ubuntu-zombie-install.log}"

# Install receipt: a human-readable record of every parameter, written once
# when the install starts and finalised with the outcome when it finishes.
# Set ZOMBIE_RECEIPT=0 to disable, or point ZOMBIE_RECEIPT_FILE elsewhere.
ZOMBIE_RECEIPT="${ZOMBIE_RECEIPT:-1}"
RECEIPT_FILE="${ZOMBIE_RECEIPT_FILE:-${ZOMBIE_LOG_DIR}/install-receipt.txt}"

ZOMBIE_NONINTERACTIVE="${ZOMBIE_NONINTERACTIVE:-0}"

# Ubuntu AI System Administrator chat-UI password gate and Time-to-Live (TTL) kill switch.
# The chat service is reachable by every local user on http://127.0.0.1:PORT,
# so it is protected by a shared password (only a PBKDF2 hash is stored in
# secrets/env). The TTL bounds the lifetime of the root-capable agent: once
# it elapses (or the operator runs `/ttl --die`) the zombie is permanently
# disabled until its lifecycle state is deliberately reinitialised. Routine
# reinstalls preserve the existing countdown and tombstone.
ZOMBIE_ADMIN_PASSWORD_DEFAULT="braaaains"
ADMIN_PASSWORD="${ZOMBIE_ADMIN_PASSWORD:-}"
# 1 once the operator has explicitly chosen a password (env or prompt), so a
# re-install does not silently overwrite a customised password with the default.
ADMIN_PASSWORD_SET=0
[[ -n "${ADMIN_PASSWORD}" ]] && ADMIN_PASSWORD_SET=1
TTL_DAYS="${ZOMBIE_TTL_DAYS:-7}"

# Local LLM discovery. During an interactive install the script can scan the
# host's IPv4 /24 (all 256 addresses) for an OpenAI-compatible local LLM
# server — LM Studio, Ollama, llama.cpp, etc. — answering on
# http://<ip>:PORT/v1 and offer the models it advertises as the starting
# model. Set ZOMBIE_SKIP_LLM_SCAN=1 to skip the scan, ZOMBIE_LLM_SCAN_PORT to
# probe a different port (default 1234, LM Studio's default), and
# ZOMBIE_LOCAL_LLM_API_KEY to record a non-default key for the local server
# (most ignore it).
ZOMBIE_SKIP_LLM_SCAN="${ZOMBIE_SKIP_LLM_SCAN:-0}"
ZOMBIE_LLM_SCAN_PORT="${ZOMBIE_LLM_SCAN_PORT:-1234}"
ZOMBIE_LOCAL_LLM_API_KEY="${ZOMBIE_LOCAL_LLM_API_KEY:-local}"
# Selection populated by discover_local_llms (empty when none is chosen).
LOCAL_LLM_ENDPOINT=""
LOCAL_LLM_BASE_URL=""
LOCAL_LLM_MODEL=""

provider_credential_configured() {
  grep -Eq \
    '^(OPENAI|ANTHROPIC|GEMINI|XAI|OPENROUTER|MISTRAL|GROQ|LMSTUDIO)_API_KEY=..+' \
    "$1" 2>/dev/null
}

model_selection_configured() {
  local key
  for key in ZOMBIE_MODEL ZOMBIE_OPENAI_MODEL ZOMBIE_ANTHROPIC_MODEL \
      ZOMBIE_GEMINI_MODEL ZOMBIE_XAI_MODEL ZOMBIE_MISTRAL_MODEL \
      ZOMBIE_GROQ_MODEL ZOMBIE_OPENROUTER_MODEL; do
    if [[ -v "${key}" && -n "${!key}" ]]; then
      return 0
    fi
  done
  grep -Eq \
    '^[[:space:]]*(export[[:space:]]+)?ZOMBIE_(MODEL|(OPENAI|ANTHROPIC|GEMINI|XAI|MISTRAL|GROQ|OPENROUTER)_MODEL)[[:space:]]*=[[:space:]]*[^[:space:]#]' \
    "${ZOMBIE_DIR}/secrets/env" 2>/dev/null
}

# UX flags (set by argument parsing below; env provides the defaults).
#   ASSUME_YES   skip the interactive "Type YES" confirmation but keep
#                interactive prompts for any still-missing inputs.
#   STRICT       treat preflight warnings as fatal.
#   JSON_OUTPUT  emit machine-readable JSON from verify/doctor.
#   VERBOSE      enable xtrace into the transcript.
ASSUME_YES="${ZOMBIE_ASSUME_YES:-0}"
STRICT="${ZOMBIE_STRICT:-0}"
JSON_OUTPUT=0
VERBOSE="${ZOMBIE_VERBOSE:-0}"
# Set to 1 once the operator has reviewed (and possibly edited) the install
# parameters interactively, so the later confirmation gate is not asked twice.
REVIEWED=0

# Idempotency transparency: count how many idempotent steps were already in
# place versus newly applied, so a re-run does not look like a fresh install.
STEPS_SATISFIED=0
STEPS_CHANGED=0
note_satisfied() { STEPS_SATISFIED=$((STEPS_SATISFIED + 1)); }
note_changed()   { STEPS_CHANGED=$((STEPS_CHANGED + 1)); }

PAYLOAD_DIR="${PAYLOAD_DIR:-${REPO_ROOT}/payload}"
# Known-good versions of the Node bridges. The install path replaces these
# globals with versions resolved from npm before embedding them in the
# deployed version files and verifier. Other subcommands use the source-tree
# values only as informational fallbacks.
read_bridge_version_fallback() {
  local file="$1"
  if [[ -r "${file}" ]]; then
    tr -d '[:space:]' < "${file}"
  else
    printf 'unknown'
  fi
}
PI_AI_VERSION="$(read_bridge_version_fallback "${PAYLOAD_DIR}/agent/pi-ai.version")"
PI_MONO_VERSION="$(read_bridge_version_fallback "${PAYLOAD_DIR}/agent/pi-mono.version")"

# Exit codes:
#   0  ok
#   1  generic failure
#   2  bad usage
#   64 missing required environment (non-interactive)
#   65 incompatible host
#   66 network preflight failure

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------
#
# The colour/TTY logic and the log/info/warn/ok/die/section/status/retry/
# run_step/prompt_until_valid helpers all live in scripts/lib.sh, sourced
# above, so every script in the suite shares one vocabulary.

# diagnose_failure <exit_code> — map a few common failure signatures onto a
# single targeted, copy-pasteable hint. Best-effort: every probe is guarded
# so this never itself aborts the error handler.
diagnose_failure() {
  local code="${1:-1}"
  case "${code}" in
    66) printf '    Likely cause: network/DNS preflight. Check connectivity and re-run.\n' >&2; return ;;
    64) printf '    Likely cause: missing required environment for non-interactive mode (see hints above).\n' >&2; return ;;
    65) printf '    Likely cause: unsupported host (need Ubuntu 22.04/24.04 LTS on amd64/arm64).\n' >&2; return ;;
  esac
  if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 \
     || fuser /var/lib/apt/lists/lock >/dev/null 2>&1 \
     || fuser /var/lib/dpkg/lock >/dev/null 2>&1; then
    printf '    Likely cause: apt/dpkg is locked by another process (e.g. unattended-upgrades).\n' >&2
    printf '    Fix: wait for it to finish, then re-run the installer (it is idempotent).\n' >&2
    return
  fi
  local avail_kb
  avail_kb="$(df -P / 2>/dev/null | awk 'NR==2 {print $4}')"
  if [[ -n "${avail_kb:-}" && "${avail_kb}" -lt 1000000 ]]; then
    printf '    Likely cause: the root filesystem is nearly full (%s MB free).\n' "$((avail_kb/1024))" >&2
    printf '    Fix: free up space (e.g. `sudo apt-get clean`) and re-run.\n' >&2
    return
  fi
  if ! getent hosts archive.ubuntu.com >/dev/null 2>&1 \
     && ! getent hosts deb.debian.org >/dev/null 2>&1; then
    printf '    Likely cause: DNS resolution looks broken (cannot resolve archive.ubuntu.com).\n' >&2
    printf '    Fix: check /etc/resolv.conf and outbound connectivity, then re-run.\n' >&2
    return
  fi
}

on_error() {
  local exit_code=$?
  local line=$1
  printf '\n%s[x] %s failed on line %s with exit code %s.%s\n' \
    "${C_RED}" "${SCRIPT_NAME}" "${line}" "${exit_code}" "${C_RESET}" >&2
  printf '%s    Full transcript: %s%s\n' "${C_RED}" "${LOG_FILE}" "${C_RESET}" >&2
  diagnose_failure "${exit_code}" || true
  printf '%s    Exit codes: 1 generic · 2 usage · 64 missing env · 65 bad host · 66 network.%s\n' \
    "${C_RED}" "${C_RESET}" >&2
  exit "${exit_code}"
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

usage() {
  cat <<EOF
${SCRIPT_NAME} ${SCRIPT_VERSION}

Install and manage Ubuntu AI System Administrator for Ubuntu
Desktop LTS.

Usage:
  sudo ./${SCRIPT_NAME} [VERB] [FLAGS]

Verbs:
  install     Install Ubuntu AI System Administrator (default). Interactive runs open an
              editable parameter review before any change is made.
  verify      Read-only state check. Does not change state.
  doctor      Explain failures and likely fixes.
  repair      Apply known-safe fixes and restart the chat service.
  uninstall   Remove Ubuntu AI System Administrator (delegates to uninstall.sh).

Flags:
  -n, --dry-run     Print the install/uninstall plan without changing the host.
  -y, --yes         Skip the capitalized YES confirmation.
  -q, --quiet       Only show warnings and errors.
      --verbose,
      --debug       Write shell xtrace to the transcript.
      --no-color    Disable ANSI colour (NO_COLOR is also honoured).
      --strict      Treat preflight warnings as fatal.
      --json        Machine-readable output for verify and doctor.
      --archive     Archive the install root before uninstalling.
      --keep-agent  Keep the Zombie account during uninstall.
  -h, --help        Show this help and exit.
  -v, --version     Print the version and exit.

Environment variables (see docs/CONFIGURATION.md for the full reference):
  ZOMBIE_NONINTERACTIVE=1       skip prompts for unattended installs.
  ZOMBIE_USER=<name>            local account name (default zombie).
  ZOMBIE_CHAT_PORT=<n>          loopback chat port (default 7878).
  ZOMBIE_RECEIPT=0              disable the install receipt.
  ZOMBIE_RECEIPT_FILE=<path>    override the install receipt path.
  ZOMBIE_SKIP_LLM_SCAN=1        skip discovery of an existing local
                                OpenAI-compatible LLM server.
  ZOMBIE_ADMIN_PASSWORD=<value> chat password (only a hash is stored).
  ZOMBIE_TTL_DAYS=<n>           lifetime in days (default 7).

Examples:
  sudo ./${SCRIPT_NAME} install --dry-run
  sudo ./${SCRIPT_NAME} install
  sudo ZOMBIE_NONINTERACTIVE=1 ./${SCRIPT_NAME} install
  ./${SCRIPT_NAME} verify --json
  ./${SCRIPT_NAME} doctor
  sudo ./${SCRIPT_NAME} repair
  sudo ./${SCRIPT_NAME} uninstall --dry-run

Shell completion:
  Bash:  source scripts/completions/install.bash
  Zsh:   add scripts/completions/ to \$fpath, then run compinit

See README.md, docs/QUICKSTART.md, and SECURITY.md.
EOF
}

SUBCOMMAND="install"
SUBCOMMAND_SEEN=0
DRY_RUN=0
UNINSTALL_ARCHIVE=0
UNINSTALL_KEEP_AGENT=0
while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help)    usage; exit 0 ;;
    -v|--version) printf '%s %s\n' "${SCRIPT_NAME}" "${SCRIPT_VERSION}"; exit 0 ;;
    -n|--dry-run) DRY_RUN=1; shift ;;
    -y|--yes)     ASSUME_YES=1; shift ;;
    -q|--quiet)   ZOMBIE_QUIET=1; shift ;;
    --verbose|--debug) VERBOSE=1; shift ;;
    --no-color|--no-colour) export ZOMBIE_COLOR=never; lib_setup_colors; shift ;;
    --strict)     STRICT=1; shift ;;
    --json)       JSON_OUTPUT=1; shift ;;
    --archive)    UNINSTALL_ARCHIVE=1; shift ;;
    --keep-agent) UNINSTALL_KEEP_AGENT=1; shift ;;
    install|verify|doctor|repair|uninstall)
                  if (( SUBCOMMAND_SEEN )); then
                    die "Unexpected lifecycle verb after ${SUBCOMMAND}: $1" 2
                  fi
                  SUBCOMMAND="$1"; SUBCOMMAND_SEEN=1; shift ;;
    --) shift
        (( $# == 0 )) || die "Unexpected argument: $1 (try --help)" 2
        break ;;
    -*) die "Unknown flag: $1 (try --help)" 2 ;;
    *)  die "Unexpected argument: $1 (try --help)" 2 ;;
  esac
done
readonly DRY_RUN

if (( JSON_OUTPUT )) \
    && [[ "${SUBCOMMAND}" != "verify" && "${SUBCOMMAND}" != "doctor" ]]; then
  die "--json only applies to the verify and doctor subcommands." 2
fi

if [[ "${SUBCOMMAND}" == "install" ]] && ! (( ZOMBIE_QUIET )); then
  brand_splash "install" "${SCRIPT_VERSION}"
fi

# ---------------------------------------------------------------------------
# Helpers shared across subcommands
# ---------------------------------------------------------------------------

require_root() {
  [[ ${EUID} -eq 0 ]] || die "Run with sudo: sudo ./${SCRIPT_NAME} ${SUBCOMMAND}" 2
}

# `retry` (exponential backoff) is provided by scripts/lib.sh.

wait_for_apt_lock() {
  local waited=0 max=300
  while fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 \
     || fuser /var/lib/apt/lists/lock     >/dev/null 2>&1 \
     || fuser /var/lib/dpkg/lock          >/dev/null 2>&1; do
    if (( waited >= max )); then
      warn "Timed out waiting ${max}s for apt/dpkg lock."
      return 1
    fi
    info "Waiting for apt/dpkg lock (${waited}s/${max}s)..."
    sleep 5
    waited=$((waited + 5))
  done
  return 0
}

_apt_get_once() {
  # Re-check the dpkg lock before *every* attempt so unattended-upgrades
  # waking up between retries does not cause spurious failures. See
  # FIX-2-07.
  wait_for_apt_lock || true
  env DEBIAN_FRONTEND=noninteractive apt-get \
    -o Dpkg::Options::=--force-confdef \
    -o Dpkg::Options::=--force-confold \
    "$@"
}

apt_get() {
  retry 4 5 -- _apt_get_once "$@"
}

apt_install() {
  apt_get install -y "$@"
}

curl_get() {
  retry 5 3 -- curl -fsSL --retry 3 --retry-delay 2 "$@"
}

is_supported_agent_username() {
  # Either 2-32 chars starting with a letter and ending alphanumeric, with
  # underscore/hyphen allowed in the middle, or 1-32 alphanumeric chars.
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

is_valid_tcp_port() {
  [[ "$1" =~ ^[0-9]+$ ]] || return 1
  (( "$1" >= 1 && "$1" <= 65535 ))
}

# A Time-to-Live in whole days: a positive integer from 1 to 36500
# (a century is plenty; the upper bound keeps the expiry timestamp sane).
is_valid_ttl_days() {
  [[ "$1" =~ ^[0-9]+$ ]] || return 1
  (( "$1" >= 1 && "$1" <= 36500 ))
}

# A boolean opt-in flag: exactly "0" or "1".
is_valid_option_flag() {
  [[ "$1" == "0" || "$1" == "1" ]]
}

# Component-specific validation hooks.
validate_zombie_config() {
  if ! is_supported_agent_username "${AGENT_USER}"; then
    die "Invalid agent username '${AGENT_USER}'. Use a non-reserved lowercase Linux username (letters first; then letters, digits, underscore, hyphen; max 32 chars; no trailing punctuation)." 2
  fi
  if ! is_safe_absolute_path "${ZOMBIE_DIR}"; then
    die "ZOMBIE_DIR must be an absolute path using only letters, digits, dot, underscore, slash, plus, colon, and hyphen." 2
  fi
  if ! is_valid_tcp_port "${CHAT_PORT}"; then
    die "ZOMBIE_CHAT_PORT must be an integer from 1 to 65535." 2
  fi
  if ! is_valid_ttl_days "${TTL_DAYS}"; then
    die "ZOMBIE_TTL_DAYS must be an integer number of days from 1 to 36500." 2
  fi
}

# Validate common settings for Ubuntu AI System Administrator.
validate_config() {
  if ! is_safe_absolute_path "${LOG_FILE}"; then
    die "LOG_FILE must be an absolute path using only letters, digits, dot, underscore, slash, plus, colon, and hyphen." 2
  fi
  if ! is_valid_option_flag "${ZOMBIE_RECEIPT}"; then
    die "ZOMBIE_RECEIPT must be 0 or 1." 2
  fi
  if [[ "${ZOMBIE_RECEIPT}" == "1" ]] && ! is_safe_absolute_path "${RECEIPT_FILE}"; then
    die "ZOMBIE_RECEIPT_FILE must be an absolute path using only letters, digits, dot, underscore, slash, plus, colon, and hyphen." 2
  fi
  validate_zombie_config
}

# Source /etc/os-release into the current shell.
load_os_release() {
  if [[ -r /etc/os-release ]]; then
    # shellcheck disable=SC1091
    . /etc/os-release || true
  fi
}

# ---------------------------------------------------------------------------
# Preflight
# ---------------------------------------------------------------------------

preflight() {
  load_os_release
  local errors=0 warnings=0 required_disk_kb=3000000 required_disk_label="3 GB"
  local memory_context="agent runtime"

  # Compact result table: parallel arrays of status (ok|warn|fail|info) and
  # a short label, rendered as a glance-able summary before the YES prompt.
  local -a pf_status=() pf_label=()
  pf() { pf_status+=("$1"); pf_label+=("$2"); }

  if [[ "${ID:-}" != "ubuntu" ]]; then
    warn "Not Ubuntu. Detected: ${PRETTY_NAME:-unknown}. Unsupported."
    warnings=$((warnings + 1)); pf warn "OS is Ubuntu"
  else
    pf ok "OS is Ubuntu"
  fi
  case "${VERSION_ID:-}" in
    22.04|24.04) pf ok "Ubuntu version ${VERSION_ID} (LTS)" ;;
    "")          warn "Could not detect Ubuntu version."; warnings=$((warnings + 1))
                 pf warn "Ubuntu version detected" ;;
    *)           warn "Recommended versions: 22.04 LTS or 24.04 LTS. Detected: ${VERSION_ID}."
                 warnings=$((warnings + 1)); pf warn "Ubuntu version ${VERSION_ID} (recommend LTS)" ;;
  esac

  local arch
  arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"
  case "${arch}" in
    amd64|arm64) pf ok "Architecture ${arch}" ;;
    *) warn "Unusual architecture ${arch}; some upstream apt repos may not match."
       warnings=$((warnings + 1)); pf warn "Architecture ${arch}" ;;
  esac

  # The Zombie runtime and its Node/Python toolchain need at least 3 GB.
  local avail_kb
  avail_kb="$(df -P / | awk 'NR==2 {print $4}')"
  if [[ "${avail_kb:-0}" -lt "${required_disk_kb}" ]]; then
    warn "Less than ${required_disk_label} free under / ($((avail_kb/1024)) MB). Install may fail."
    warnings=$((warnings + 1)); pf warn "Disk >= ${required_disk_label} free ($((avail_kb/1024)) MB)"
  else
    pf ok "Disk free $((avail_kb/1024)) MB"
  fi

  # Memory: 2 GB minimum recommended.
  local mem_kb
  mem_kb="$(awk '/MemTotal/ {print $2}' /proc/meminfo 2>/dev/null || echo 0)"
  if [[ "${mem_kb:-0}" -lt 2000000 ]]; then
    warn "Less than 2 GB RAM ($((mem_kb/1024)) MB). The ${memory_context} may be tight."
    warnings=$((warnings + 1)); pf warn "RAM >= 2 GB ($((mem_kb/1024)) MB)"
  else
    pf ok "RAM $((mem_kb/1024)) MB"
  fi

  # DNS
  if ! getent hosts deb.debian.org >/dev/null 2>&1 \
     && ! getent hosts archive.ubuntu.com >/dev/null 2>&1; then
    warn "DNS resolution looks broken (cannot resolve archive.ubuntu.com)."
    warnings=$((warnings + 1)); pf warn "DNS resolution"
  else
    pf ok "DNS resolution"
  fi

  # Outbound connectivity. Keep this to one bounded attempt: curl_get is the
  # retrying download helper and can otherwise add 45 seconds of backoff before
  # the fallback probes run on an offline host.
  if ! curl -fsSL -o /dev/null -m 8 https://archive.ubuntu.com/ >/dev/null 2>&1 \
     && ! ping -c1 -W2 1.1.1.1 >/dev/null 2>&1 \
     && ! ping -c1 -W2 8.8.8.8 >/dev/null 2>&1; then
    warn "No outbound connectivity detected. Package installation will fail."
    if [[ "${SUBCOMMAND}" == "install" ]]; then
      errors=$((errors + 1)); pf fail "Outbound connectivity"
    else
      pf warn "Outbound connectivity"
    fi
  else
    pf ok "Outbound connectivity"
  fi

  # apt/dpkg lock
  if fuser /var/lib/dpkg/lock-frontend >/dev/null 2>&1 \
     || fuser /var/lib/apt/lists/lock >/dev/null 2>&1; then
    info "apt/dpkg lock currently held; install will wait up to 5 minutes."
    pf info "apt/dpkg lock (will wait)"
  fi

  # Render the compact summary table.
  if ! (( ZOMBIE_QUIET )); then
    printf '\n%sPreflight summary:%s\n' "${C_BOLD}" "${C_RESET}"
    local i
    for (( i = 0; i < ${#pf_status[@]}; i++ )); do
      status "${pf_status[i]}" "${pf_label[i]}"
    done
    echo
  fi

  # --strict turns warnings into hard failures so unattended pipelines can
  # refuse to continue on a marginal host.
  if (( STRICT )) && (( warnings > 0 )); then
    die "Preflight: ${warnings} warning(s) and --strict is set. Aborting." 66
  fi

  if (( errors > 0 )); then
    die "Preflight failed (${errors} error(s), ${warnings} warning(s)). See above." 66
  fi
  if (( warnings > 0 )); then
    info "Preflight: ${warnings} warning(s). Continuing."
  else
    ok "Preflight: clean."
  fi
}

# ---------------------------------------------------------------------------
# Subcommand: verify
# ---------------------------------------------------------------------------

verify_zombie() {
  # Keep lifecycle verification in this script. A deployed verifier may come
  # from an older release and must not be able to break current verify output.
  id "${AGENT_USER}" >/dev/null 2>&1 \
    && vr ok zombie user "User ${AGENT_USER} exists." \
    || vr fail zombie user "User ${AGENT_USER} missing. Run 'sudo ./${SCRIPT_NAME} install' first."
  [[ -f "/etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie" ]] \
    && vr ok zombie sudoers "Sudoers drop-in present." \
    || vr fail zombie sudoers "Sudoers drop-in missing. Run 'sudo ./${SCRIPT_NAME} repair'."
  [[ -d "${ZOMBIE_DIR}" ]] \
    && vr ok zombie install_root "${ZOMBIE_DIR} present." \
    || vr fail zombie install_root "${ZOMBIE_DIR} missing. Run 'sudo ./${SCRIPT_NAME} install' first."
  [[ -x "${ZOMBIE_DIR}/bin/verify" ]] \
    && vr ok zombie verify_script "${ZOMBIE_DIR}/bin/verify present." \
    || vr fail zombie verify_script "${ZOMBIE_DIR}/bin/verify not found. Run 'sudo ./${SCRIPT_NAME} install' first."
  systemctl is-active --quiet ubuntu-zombie-chat.service 2>/dev/null \
    && vr ok zombie chat_service "Chat service active." \
    || vr fail zombie chat_service "Chat service not active. Run: sudo systemctl start ubuntu-zombie-chat"
}

cmd_verify() {
  local -a v_status=() v_component=() v_id=() v_msg=()
  vr() { v_status+=("$1"); v_component+=("$2"); v_id+=("$3"); v_msg+=("$4"); }
  verify_zombie

  local n="${#v_status[@]}" i failed=0 passed=0
  for (( i = 0; i < n; i++ )); do
    case "${v_status[i]}" in
      ok) passed=$((passed + 1)) ;;
      *)  failed=$((failed + 1)) ;;
    esac
  done
  if (( JSON_OUTPUT )); then
    printf '{"tool":"verify","passed":%d,"failed":%d,"checks":[' "${passed}" "${failed}"
    for (( i = 0; i < n; i++ )); do
      printf '{"component":"%s","id":"%s","status":"%s","message":"%s"}' \
        "$(json_escape "${v_component[i]}")" "$(json_escape "${v_id[i]}")" \
        "${v_status[i]}" "$(json_escape "${v_msg[i]}")"
      [[ $i -lt $((n - 1)) ]] && printf ','
    done
    printf ']}\n'
  else
    printf '%s== ubuntu-zombie verify ==%s\n\n' "${C_BOLD}" "${C_RESET}"
    for (( i = 0; i < n; i++ )); do
      if [[ "${v_status[i]}" == "ok" ]]; then
        ok "${v_msg[i]}"
      else
        printf '%s[x]%s %s\n' "${C_RED}" "${C_RESET}" "${v_msg[i]}"
      fi
    done
  fi
  (( failed == 0 ))
}

# ---------------------------------------------------------------------------
# Subcommand: doctor
# ---------------------------------------------------------------------------

cmd_doctor() {
  load_os_release
  local -a d_status=() d_msg=() d_id=() d_component=()
  dr() { d_status+=("$1"); d_component+=("$2"); d_id+=("$3"); d_msg+=("$4"); }
  local host_arch perms
  host_arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"

  if id "${AGENT_USER}" >/dev/null 2>&1; then
    dr ok zombie user "User ${AGENT_USER} exists."
  else
    dr warn zombie user "User ${AGENT_USER} missing. Fix: sudo ./${SCRIPT_NAME} install"
  fi
  if [[ -f "/etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie" ]]; then
    dr ok zombie sudoers "Sudoers drop-in present."
  else
    dr warn zombie sudoers "Sudoers drop-in missing. Fix: sudo ./${SCRIPT_NAME} repair"
  fi
  if [[ -d "${ZOMBIE_DIR}" ]]; then
    dr ok zombie install_root "${ZOMBIE_DIR} present."
  else
    dr warn zombie install_root "${ZOMBIE_DIR} missing. Fix: sudo ./${SCRIPT_NAME} install"
  fi
  if [[ -f "${ZOMBIE_DIR}/secrets/env" ]]; then
    perms="$(stat -c %a "${ZOMBIE_DIR}/secrets/env" 2>/dev/null || echo ???)"
    if [[ "${perms}" == "600" ]]; then
      dr ok zombie secrets_perms "secrets/env permissions 600."
    else
      dr warn zombie secrets_perms "secrets/env permissions ${perms} (must be 600). Fix: sudo ./${SCRIPT_NAME} repair"
    fi
    if provider_credential_configured "${ZOMBIE_DIR}/secrets/env"; then
      dr ok zombie provider_token "Provider credential present."
    else
      dr warn zombie provider_token "No provider credential. Fix: sudo ${ZOMBIE_DIR}/bin/secrets-edit"
    fi
  else
    dr warn zombie secrets_env "secrets/env missing. Fix: sudo ./${SCRIPT_NAME} install"
  fi
  if systemctl list-unit-files ubuntu-zombie-chat.service >/dev/null 2>&1; then
    if systemctl is-active --quiet ubuntu-zombie-chat.service; then
      dr ok zombie chat_service "Chat service active."
    else
      dr warn zombie chat_service "Chat service installed but not running. Fix: sudo systemctl start ubuntu-zombie-chat"
    fi
  else
    dr warn zombie chat_service "Chat service unit missing. Fix: sudo ./${SCRIPT_NAME} install"
  fi

  local n="${#d_status[@]}" i warns=0
  for (( i = 0; i < n; i++ )); do
    [[ "${d_status[i]}" == "warn" ]] && warns=$((warns + 1))
  done
  if (( JSON_OUTPUT )); then
    printf '{\n'
    printf '  "tool": "doctor",\n'
    printf '  "host": {"id": "%s", "version": "%s", "arch": "%s"},\n' \
      "$(json_escape "${ID:-}")" "$(json_escape "${VERSION_ID:-}")" "$(json_escape "${host_arch}")"
    printf '  "warnings": %d,\n' "${warns}"
    printf '  "checks": [\n'
    for (( i = 0; i < n; i++ )); do
      printf '    {"component": "%s", "id": "%s", "status": "%s", "message": "%s"}' \
        "$(json_escape "${d_component[i]}")" "$(json_escape "${d_id[i]}")" \
        "${d_status[i]}" "$(json_escape "${d_msg[i]}")"
      [[ $i -lt $((n - 1)) ]] && printf ','
      printf '\n'
    done
    printf '  ]\n}\n'
    return 0
  fi

  printf '%s== ubuntu-zombie doctor ==%s\n\n' "${C_BOLD}" "${C_RESET}"
  printf '%sHost:%s %s %s on %s\n\n' "${C_BOLD}" "${C_RESET}" \
    "${ID:-?}" "${VERSION_ID:-?}" "${host_arch}"
  for (( i = 0; i < n; i++ )); do
    case "${d_status[i]}" in
      ok)   ok   "${d_msg[i]}" ;;
      warn) warn "${d_msg[i]}" ;;
      *)    info "${d_msg[i]}" ;;
    esac
  done
  echo
  info "For a runtime health summary: ${ZOMBIE_DIR}/bin/health-check"
}

# ---------------------------------------------------------------------------
# Subcommand: repair
# ---------------------------------------------------------------------------

cmd_repair() {
  section "Repair"
  local _facts f
  if id "${AGENT_USER}" >/dev/null 2>&1; then
    if [[ -f "${ZOMBIE_DIR}/secrets/env" ]]; then
      chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/secrets/env"
      chmod 600 "${ZOMBIE_DIR}/secrets/env"
      ok "Re-asserted secrets/env permissions."
    fi
    [[ -d "${ZOMBIE_DIR}" ]] && chown -R "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}"
  fi
  if systemctl list-unit-files ubuntu-zombie-chat.service >/dev/null 2>&1; then
    systemctl daemon-reload
    systemctl restart ubuntu-zombie-chat.service \
      || warn "Chat service failed to restart; see journalctl -u ubuntu-zombie-chat"
    ok "Chat service restarted."
  fi
  if [[ -d "${ZOMBIE_DIR}/agent/templates" ]]; then
    install -d -m 755 -o root -g root "${ZOMBIE_DIR}/pi"
    install -d -m 750 -o "${AGENT_USER}" -g "${AGENT_USER}" \
      "${ZOMBIE_DIR}/state/logs" "${ZOMBIE_DIR}/state/pi-mono-sessions" 2>/dev/null || true
    if [[ -f "${ZOMBIE_DIR}/agent/templates/settings.json.tmpl" ]]; then
      sed -e "s|__ZOMBIE_DIR__|${ZOMBIE_DIR}|g" \
        "${ZOMBIE_DIR}/agent/templates/settings.json.tmpl" \
        | install -m 644 /dev/stdin "${ZOMBIE_DIR}/pi/settings.json"
    fi
    if [[ -f "${ZOMBIE_DIR}/agent/templates/APPEND_SYSTEM.md.tmpl" ]]; then
      _facts="hostname=$(hostname) os=$(. /etc/os-release 2>/dev/null && echo "${PRETTY_NAME:-Linux}")"
      sed -e "s|__AGENT_USER__|${AGENT_USER}|g" -e "s|__FACTS__|${_facts}|g" \
        "${ZOMBIE_DIR}/agent/templates/APPEND_SYSTEM.md.tmpl" \
        | install -m 644 /dev/stdin "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md"
    fi
    ok "pi-mono runtime configs re-rendered."
  fi
  if [[ -d "${PAYLOAD_DIR}/agent/skills" ]]; then
    install -d -m 755 -o root -g root "${ZOMBIE_DIR}/skills"
    shopt -s nullglob
    for f in "${PAYLOAD_DIR}/agent/skills/"*.md; do
      install -m 644 -o root -g root "${f}" "${ZOMBIE_DIR}/skills/$(basename "${f}")"
    done
    shopt -u nullglob
    install -d -m 755 -o root -g root "${ZOMBIE_ETC}/skills.d"
    ok "Skill catalogue re-deployed."
  fi
}

# ---------------------------------------------------------------------------
# Subcommand: uninstall
# ---------------------------------------------------------------------------

cmd_uninstall() {
  if [[ -x "${SCRIPT_DIR}/uninstall.sh" ]]; then
    local -a fwd=()
    (( DRY_RUN ))              && fwd+=(--dry-run)
    (( ASSUME_YES ))           && fwd+=(--yes)
    (( ZOMBIE_QUIET ))         && fwd+=(--quiet)
    (( UNINSTALL_ARCHIVE ))    && fwd+=(--archive)
    (( UNINSTALL_KEEP_AGENT )) && fwd+=(--keep-agent)
    [[ "${ZOMBIE_COLOR:-}" == "never" ]] && fwd+=(--no-color)
    exec "${SCRIPT_DIR}/uninstall.sh" "${fwd[@]}"
  fi
  die "uninstall.sh not found alongside ${SCRIPT_NAME}." 1
}

# ---------------------------------------------------------------------------
# Dry-run summary (no host mutation; safe without sudo).
# ---------------------------------------------------------------------------

print_dry_run_plan() {
  load_os_release
  cat <<EOF
${SCRIPT_NAME} ${SCRIPT_VERSION}  —  dry-run

A real install would install Ubuntu AI System Administrator on:

  Host:           ${ID:-?} ${VERSION_ID:-?} on $(dpkg --print-architecture 2>/dev/null || uname -m)
  Transcript:     ${LOG_FILE}
  Receipt:        $([[ "${ZOMBIE_RECEIPT}" == "1" ]] && echo "${RECEIPT_FILE}" || echo "(disabled)")
EOF
  print_zombie_dry_run
  cat <<EOF

Nothing has been changed. To proceed for real:

  sudo ./${SCRIPT_NAME} install

See docs/QUICKSTART.md and docs/ARCHITECTURE.md for the full picture.
EOF
}

print_zombie_dry_run() {
  cat <<EOF

Ubuntu AI System Administrator:
  Agent user:     ${AGENT_USER}  (home: ${AGENT_HOME})
  Install root:   ${ZOMBIE_DIR}
  Etc dir:        ${ZOMBIE_ETC}
  Log dir:        ${ZOMBIE_LOG_DIR}
  Chat port:      ${CHAT_PORT}/tcp (loopback only)
  Mode:           $([[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && echo non-interactive || echo interactive)

Apt package groups installed:
  base            sudo, curl, git, editors, Python 3/venv, build-essential,
                  ripgrep, jq, logrotate, unattended-upgrades, …
  nodejs          Node 22.x from deb.nodesource.com (signed-by keyring)

Files & directories created / re-asserted:
  /etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie   (NOPASSWD: ALL for ${AGENT_USER})
  ${ZOMBIE_DIR}/                                  (755, ${AGENT_USER}:${AGENT_USER})
  ${ZOMBIE_DIR}/secrets/                          (700, env file 600)
  ${ZOMBIE_DIR}/bin/                              (verify, health-check, secrets-edit, audit-recent, …)
  ${ZOMBIE_DIR}/agent/                            (Python package + templates + skills + pi bridge)
  ${ZOMBIE_DIR}/pi/                               (rendered pi-mono settings + APPEND_SYSTEM.md)
  ${ZOMBIE_DIR}/skills/                           (built-in markdown skills)
  ${ZOMBIE_ETC}/skills.d/                         (operator-supplied skills)
  ${ZOMBIE_LOG_DIR}/                              (750, ${AGENT_USER}:${AGENT_USER}, logrotate'd)
  /etc/systemd/system/ubuntu-zombie-chat.service
  /etc/systemd/system/ubuntu-zombie-health.service
  /etc/systemd/system/ubuntu-zombie-health.timer
  /etc/logrotate.d/ubuntu-zombie
EOF
}

# ---------------------------------------------------------------------------
# Interactive parameter review (Zombie Orchid setup experience)
# ---------------------------------------------------------------------------
# A branded, editable summary of every install parameter. The operator can
# tweak any field and re-review until satisfied, then accept. Skipped in
# non-interactive / --yes runs and when stdin is not a TTY, so automated
# installs are unaffected.

# Render the current parameters as a glance-able, brand-coloured table.
print_parameter_table() {
  load_os_release
  local receipt_state
  if [[ "${ZOMBIE_RECEIPT}" == "1" ]]; then
    receipt_state="${RECEIPT_FILE}"
  else
    receipt_state="disabled"
  fi

  brand_banner "Ubuntu AI System Administrator — setup parameters"
  printf '  %sReview every setting below, edit any of them, then accept when happy.%s\n\n' \
    "${C_DIM}" "${C_RESET}"
  field "1) Agent user"      "${AGENT_USER}"
  field "   Agent home"      "${AGENT_HOME}" "${C_DIM}"
  field "2) Install root"    "${ZOMBIE_DIR}"
  field "3) Chat port"       "${CHAT_PORT}/tcp (loopback only)"
  field "4) Transcript log"  "${LOG_FILE}"
  field "5) Receipt file"    "${receipt_state}"
  field "6) Chat password"   "$([[ "${ADMIN_PASSWORD_SET}" == "1" ]] && echo 'set (hidden)' || printf 'default (%s)' "${ZOMBIE_ADMIN_PASSWORD_DEFAULT}")"
  field "7) Time to Live"    "${TTL_DAYS} day(s) then permanently disabled"
  if [[ -n "${LOCAL_LLM_MODEL}" ]]; then
    field "8) Local LLM"     "${LOCAL_LLM_MODEL} @ ${LOCAL_LLM_BASE_URL}"
  elif model_selection_configured; then
    field "8) Local LLM"     "skipped (an existing model is configured)" "${C_DIM}"
  else
    field "8) Local LLM"     "none (scan LAN for an OpenAI-compatible server)" "${C_DIM}"
  fi
  field "   Host"            "${ID:-?} ${VERSION_ID:-?} ($(dpkg --print-architecture 2>/dev/null || uname -m))" "${C_DIM}"
  printf '\n'
}

# Individual field editors. Each keeps the current value when the operator
# presses Enter (allow_empty=1), and re-prompts on invalid input rather than
# aborting the whole run.
_edit_agent_user() {
  local v
  if prompt_until_valid "$(printf 'New agent user [%s]: ' "${AGENT_USER}")" \
       is_supported_agent_username v 1 && [[ -n "${v}" ]]; then
    AGENT_USER="${v}"; AGENT_HOME="/home/${AGENT_USER}"
  fi
}
_edit_zombie_dir() {
  local v
  if prompt_until_valid "$(printf 'New install root [%s]: ' "${ZOMBIE_DIR}")" \
       is_safe_absolute_path v 1 && [[ -n "${v}" ]]; then
    ZOMBIE_DIR="${v}"
  fi
}
_edit_chat_port() {
  local v
  if prompt_until_valid "$(printf 'New chat port [%s]: ' "${CHAT_PORT}")" \
       is_valid_tcp_port v 1 && [[ -n "${v}" ]]; then
    CHAT_PORT="${v}"
  fi
}
_edit_log_file() {
  local v
  if prompt_until_valid "$(printf 'New transcript log path [%s]: ' "${LOG_FILE}")" \
       is_safe_absolute_path v 1 && [[ -n "${v}" ]]; then
    LOG_FILE="${v}"
  fi
}
_toggle_receipt() {
  if [[ "${ZOMBIE_RECEIPT}" == "1" ]]; then
    local v
    printf 'Receipt is ON. Press Enter to turn it OFF, or type a new path: '
    if read -r v && [[ -n "${v}" ]]; then
      if is_safe_absolute_path "${v}"; then
        RECEIPT_FILE="${v}"; info "Receipt path set to ${RECEIPT_FILE}."
      else
        warn "Not a safe absolute path; receipt unchanged."
      fi
    else
      ZOMBIE_RECEIPT=0; info "Receipt disabled."
    fi
  else
    ZOMBIE_RECEIPT=1; info "Receipt enabled: ${RECEIPT_FILE}."
  fi
}
_edit_admin_password() {
  local p1 p2
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" || ! -t 0 ]] && return 0
  if ! read -r -s -p "New chat password (blank to keep the default '${ZOMBIE_ADMIN_PASSWORD_DEFAULT}'): " p1; then
    echo
    warn "No input (EOF); chat password unchanged."
    return 0
  fi
  echo
  if [[ -z "${p1}" ]]; then
    info "Chat password left at the default."
    return 0
  fi
  if ! read -r -s -p "Confirm chat password: " p2; then
    echo
    warn "No input (EOF); chat password unchanged."
    return 0
  fi
  echo
  if [[ "${p1}" != "${p2}" ]]; then
    warn "Passwords did not match; chat password unchanged."
    return 0
  fi
  ADMIN_PASSWORD="${p1}"
  ADMIN_PASSWORD_SET=1
  ok "Chat password recorded."
}
_edit_ttl_days() {
  local v
  if prompt_until_valid "$(printf 'New Time to Live in days [%s]: ' "${TTL_DAYS}")" \
       is_valid_ttl_days v 1 && [[ -n "${v}" ]]; then
    TTL_DAYS="${v}"; ok "Time to Live set to ${TTL_DAYS} day(s)."
  fi
}

# ---------------------------------------------------------------------------
# Local LLM discovery on the LAN
# ---------------------------------------------------------------------------
# Probe every address in the host's IPv4 /24 for an OpenAI-compatible LLM
# server (LM Studio, Ollama, llama.cpp, …) answering on
# http://<ip>:PORT/v1/models, then offer the advertised models as the
# starting model. Entirely best-effort: a missing curl/python3, an
# undetectable subnet, or an empty result simply leaves the selection unset.

# Print the host's primary global IPv4 /24 prefix (first three octets), or
# nothing when it cannot be determined.
_local_ipv4_prefix() {
  local cidr ip
  cidr="$(ip -4 -o addr show scope global up 2>/dev/null \
            | awk '{print $4; exit}')"
  ip="${cidr%/*}"
  if [[ -z "${ip}" ]]; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  [[ "${ip}" =~ ^([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})\.([0-9]{1,3})$ ]] || return 0
  printf '%s.%s.%s' "${BASH_REMATCH[1]}" "${BASH_REMATCH[2]}" "${BASH_REMATCH[3]}"
}

# Parse the model ids from a /v1/models JSON body on stdin, one per line.
# Only ids made of a conservative, shell/env-safe character set are emitted:
# the values are later written verbatim into secrets/env, so a hostile or
# malformed local server must not be able to inject newlines or other
# characters that would smuggle extra assignments into that file.
_parse_model_ids() {
  python3 -c '
import json, re, sys
SAFE = re.compile(r"\A[A-Za-z0-9._:/+@-]{1,200}\Z")
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
items = data.get("data") if isinstance(data, dict) else None
if not isinstance(items, list):
    sys.exit(0)
seen = set()
for item in items:
    if not isinstance(item, dict):
        continue
    mid = item.get("id")
    if isinstance(mid, str):
        mid = mid.strip()
        if mid and mid not in seen and SAFE.match(mid):
            seen.add(mid)
            print(mid)
' 2>/dev/null || true
}

# Probe a single host:port for an OpenAI-compatible /v1/models endpoint and,
# on success, append "host<TAB>port<TAB>model" lines to ``outfile``.
_probe_llm_host() {
  local host="$1" port="$2" outfile="$3"
  local body model
  body="$(curl -fsS --connect-timeout 1 --max-time 3 \
            "http://${host}:${port}/v1/models" 2>/dev/null)" || return 0
  [[ -n "${body}" ]] || return 0
  while IFS= read -r model; do
    [[ -n "${model}" ]] && printf '%s\t%s\t%s\n' "${host}" "${port}" "${model}" >> "${outfile}"
  done < <(printf '%s' "${body}" | _parse_model_ids)
}

# Write the `pi` custom-provider config so the agent loop reaches a local
# OpenAI-compatible server through the 'lmstudio' provider. pi reads
# ${AGENT_HOME}/.pi/agent/models.json (homedir() + ~/.pi/agent), so the server
# URL lives here rather than in an environment variable. Args: base URL, model.
write_pi_models_json() {
  local base_url="$1" model="$2" dir="${AGENT_HOME}/.pi/agent" file
  file="${dir}/models.json"
  install -d -m 700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${AGENT_HOME}/.pi" "${dir}"
  install -m 600 -o "${AGENT_USER}" -g "${AGENT_USER}" /dev/null "${file}"
  cat > "${file}" <<EOF
{
  "providers": {
    "lmstudio": {
      "baseUrl": "$(json_escape "${base_url}")",
      "api": "openai-completions",
      "apiKey": "LMSTUDIO_API_KEY",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        { "id": "$(json_escape "${model}")" }
      ]
    }
  }
}
EOF
  chown "${AGENT_USER}:${AGENT_USER}" "${file}"
  chmod 600 "${file}"
}

# Compute the PBKDF2 hash for the chat-UI password without exposing the
# plaintext on a command line (it is piped to auth.py over stdin). An empty
# password makes auth.py fall back to the documented default.
admin_password_hash() {
  printf '%s\n' "$1" | python3 "${PAYLOAD_DIR}/agent/auth.py"
}

# Ensure secrets/env carries a ZOMBIE_ADMIN_PASSWORD_HASH line. The hash is
# (re)written when it is missing, or when the operator explicitly chose a
# password this run (ADMIN_PASSWORD_SET=1); an existing hash is otherwise
# preserved so a plain re-install never resets a customised password.
ensure_admin_password_hash() {
  local file="$1" hash has_line=0
  grep -q '^ZOMBIE_ADMIN_PASSWORD_HASH=' "${file}" 2>/dev/null && has_line=1
  if [[ "${has_line}" -eq 1 && "${ADMIN_PASSWORD_SET}" != "1" ]]; then
    return 0
  fi
  if ! hash="$(admin_password_hash "${ADMIN_PASSWORD:-${ZOMBIE_ADMIN_PASSWORD_DEFAULT}}")"; then
    die "Failed to hash the chat password." 1
  fi
  if [[ "${has_line}" -eq 1 ]]; then
    sed -i -E '/^ZOMBIE_ADMIN_PASSWORD_HASH=/d' "${file}"
  fi
  [[ -s "${file}" ]] && [[ "$(tail -c1 "${file}" 2>/dev/null)" != $'\n' ]] && printf '\n' >> "${file}"
  printf 'ZOMBIE_ADMIN_PASSWORD_HASH=%s\n' "${hash}" >> "${file}"
}

# Initialise the Time-to-Live kill switch on first install. Reinstalls preserve
# valid lifecycle state, including extensions and tombstones, so an upgrade
# cannot silently change an operator's existing TTL decision.
init_lifecycle_state() {
  local state="${ZOMBIE_DIR}/state/lifecycle.json" current
  if [[ -s "${state}" ]]; then
    chown "${AGENT_USER}:${AGENT_USER}" "${state}"
    chmod 600 "${state}"
    if current="$(runuser -u "${AGENT_USER}" -- env \
          ZOMBIE_LIFECYCLE_STATE="${state}" \
          python3 "${ZOMBIE_DIR}/agent/lifecycle.py" status 2>/dev/null)" \
        && grep -Eq '"configured":[[:space:]]*true' <<<"${current}"; then
      ok "Preserving existing Time to Live state."
      return 0
    fi
    warn "Existing Time-to-Live state is invalid; creating a fresh countdown."
  fi
  if ! runuser -u "${AGENT_USER}" -- env \
        ZOMBIE_LIFECYCLE_STATE="${state}" \
        python3 "${ZOMBIE_DIR}/agent/lifecycle.py" init --days "${TTL_DAYS}" >/dev/null; then
    die "Failed to initialise the Time-to-Live state." 1
  fi
  chown "${AGENT_USER}:${AGENT_USER}" "${state}"
  chmod 600 "${state}"
  ok "Time to Live set: ${TTL_DAYS} day(s) until the zombie is disabled."
}
# DISCOVERED_MODELS (parallel index) with every advertised model.
DISCOVERED_ENDPOINTS=()
DISCOVERED_MODELS=()
scan_local_llms() {
  DISCOVERED_ENDPOINTS=()
  DISCOVERED_MODELS=()
  if ! command -v curl >/dev/null 2>&1 || ! command -v python3 >/dev/null 2>&1; then
    warn "Local LLM scan needs curl and python3; skipping."
    return 1
  fi
  local prefix port
  prefix="$(_local_ipv4_prefix)"
  port="${ZOMBIE_LLM_SCAN_PORT}"
  if ! is_valid_tcp_port "${port}"; then
    warn "ZOMBIE_LLM_SCAN_PORT='${port}' is not a valid TCP port (1-65535); skipping LLM discovery."
    return 1
  fi
  if [[ -z "${prefix}" ]]; then
    warn "Could not determine a local IPv4 /24 to scan; skipping LLM discovery."
    return 1
  fi
  info "Scanning ${prefix}.0/24 on port ${port} for OpenAI-compatible LLM servers…"
  local resfile pids n max=64
  resfile="$(mktemp 2>/dev/null)" || { warn "Could not create a temp file for the scan."; return 1; }
  chmod 600 "${resfile}" 2>/dev/null || true
  pids=()
  for n in $(seq 0 255); do
    _probe_llm_host "${prefix}.${n}" "${port}" "${resfile}" &
    pids+=("$!")
    if (( ${#pids[@]} >= max )); then
      wait "${pids[@]}" 2>/dev/null || true
      pids=()
    fi
  done
  (( ${#pids[@]} )) && { wait "${pids[@]}" 2>/dev/null || true; }

  local host hport hmodel
  while IFS=$'\t' read -r host hport hmodel; do
    [[ -n "${host}" && -n "${hmodel}" ]] || continue
    DISCOVERED_ENDPOINTS+=("${host}:${hport}")
    DISCOVERED_MODELS+=("${hmodel}")
  done < <(sort -u "${resfile}" 2>/dev/null)
  rm -f "${resfile}" 2>/dev/null || true

  if (( ${#DISCOVERED_MODELS[@]} == 0 )); then
    info "No local LLM servers found on ${prefix}.0/24:${port}."
    return 1
  fi
  return 0
}

# Interactive picker: scan, present the discovered models, and record the
# operator's choice in LOCAL_LLM_ENDPOINT / LOCAL_LLM_BASE_URL /
# LOCAL_LLM_MODEL. Skipped on non-interactive / --yes / non-TTY runs and when
# ZOMBIE_SKIP_LLM_SCAN=1.
discover_local_llms() {
  local force="${1:-0}"
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && return 0
  (( ASSUME_YES )) && return 0
  [[ -t 0 ]] || return 0
  [[ "${ZOMBIE_SKIP_LLM_SCAN}" == "1" ]] && return 0
  if [[ "${force}" != "1" ]] && model_selection_configured; then
    info "A model is already configured; preserving it and skipping local LLM discovery."
    return 0
  fi

  scan_local_llms || return 0

  local i choice
  while true; do
    brand_banner "Local LLM servers discovered on your network"
    printf '  %sPick a model to use as the starting model, or skip to configure a%s\n' "${C_DIM}" "${C_RESET}"
    printf '  %scloud provider later in %s/secrets/env.%s\n\n' "${C_DIM}" "${ZOMBIE_DIR}" "${C_RESET}"
    for i in "${!DISCOVERED_MODELS[@]}"; do
      printf '  %s%2d)%s %s%s  @  http://%s/v1%s\n' \
        "${C_BRAND2}" "$((i + 1))" "${C_RESET}" "${C_ACCENT}" \
        "${DISCOVERED_MODELS[$i]}" "${DISCOVERED_ENDPOINTS[$i]}" "${C_RESET}"
    done
    printf '\n  %s[1-%d]%s use a model    %s[r]%s rescan    %s[s]%s skip\n' \
      "${C_BRAND2}" "${#DISCOVERED_MODELS[@]}" "${C_RESET}" \
      "${C_ACCENT}" "${C_RESET}" "${C_YELLOW}" "${C_RESET}"
    if ! read -r -p "$(printf '%s➜%s your choice [s]: ' "${C_BRAND}" "${C_RESET}")" choice; then
      info "No input (EOF); skipping local LLM selection."
      return 0
    fi
    case "${choice,,}" in
      ""|s|skip|n|no)
        info "No local LLM selected."
        return 0 ;;
      r|rescan)
        scan_local_llms || return 0
        continue ;;
      *)
        if [[ "${choice}" =~ ^[0-9]+$ ]] && (( choice >= 1 && choice <= ${#DISCOVERED_MODELS[@]} )); then
          LOCAL_LLM_ENDPOINT="${DISCOVERED_ENDPOINTS[$((choice - 1))]}"
          LOCAL_LLM_MODEL="${DISCOVERED_MODELS[$((choice - 1))]}"
          LOCAL_LLM_BASE_URL="http://${LOCAL_LLM_ENDPOINT}/v1"
          ok "Local LLM ${LOCAL_LLM_MODEL} (${LOCAL_LLM_BASE_URL}) chosen as the starting model."
          return 0
        fi
        warn "Unrecognised choice: '${choice}'. Enter 1-${#DISCOVERED_MODELS[@]}, 'r', or 's'." ;;
    esac
  done
}

_edit_local_llm() {
  discover_local_llms 1
}

review_parameters() {
  # Automated paths skip the review entirely.
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && return 0
  (( ASSUME_YES )) && return 0
  [[ -t 0 ]] || return 0

  local choice
  while true; do
    print_parameter_table
    printf '  %s[a]%s accept and install    %s[1-8]%s edit a field    %s[q]%s cancel\n' \
      "${C_ACCENT}" "${C_RESET}" "${C_BRAND2}" "${C_RESET}" "${C_YELLOW}" "${C_RESET}"
    if ! read -r -p "$(printf '%s➜%s your choice [a]: ' "${C_BRAND}" "${C_RESET}")" choice; then
      info "No input (EOF); cancelling."; exit 0
    fi
    case "${choice,,}" in
      ""|a|accept|y|yes)
        # Edits are validated as they are entered, so this is a belt-and-
        # braces final check before committing to the install.
        validate_config
        REVIEWED=1
        ok "Parameters accepted."
        return 0 ;;
      q|quit|cancel|n|no)
        info "Cancelled."; exit 0 ;;
      1)  _edit_agent_user ;;
      2)  _edit_zombie_dir ;;
      3)  _edit_chat_port ;;
      4)  _edit_log_file ;;
      5)  _toggle_receipt ;;
      6)  _edit_admin_password ;;
      7)  _edit_ttl_days ;;
      8)  _edit_local_llm ;;
      *)  warn "Unrecognised choice: '${choice}'. Enter a number 1-8, 'a', or 'q'." ;;
    esac
  done
}

# ---------------------------------------------------------------------------
# Install receipt (start + finish records)
# ---------------------------------------------------------------------------
# A human-readable record of the install. Written once when the run starts
# (every non-secret parameter) and finalised with the outcome when it ends.
# The file is root-only (mode 600), but credentials are never written to it.

receipt_start_zombie() {
  printf 'Agent user       : %s\n' "${AGENT_USER}"
  printf 'Agent home       : %s\n' "${AGENT_HOME}"
  printf 'Install root     : %s\n' "${ZOMBIE_DIR}"
  printf 'Etc dir          : %s\n' "${ZOMBIE_ETC}"
  printf 'Log dir          : %s\n' "${ZOMBIE_LOG_DIR}"
  printf 'Chat port        : %s/tcp (loopback only)\n' "${CHAT_PORT}"
  printf 'Local LLM        : %s\n' \
    "$([[ -n "${LOCAL_LLM_MODEL}" ]] && printf '%s @ %s' "${LOCAL_LLM_MODEL}" "${LOCAL_LLM_BASE_URL}" || echo 'none')"
}

receipt_finish_zombie() {
  printf 'Provider token   : %s\n' "$([[ "${PROVIDER_OK:-0}" == "1" ]] && echo present || echo missing)"
  printf 'Chat service     : %s\n' "$([[ "${CHAT_OK:-0}" == "1" ]] && echo running || echo 'not running')"
}

write_receipt_start() {
  [[ "${ZOMBIE_RECEIPT}" == "1" ]] || return 0
  load_os_release
  if ! mkdir -p "$(dirname "${RECEIPT_FILE}")" 2>/dev/null; then
    warn "Could not create receipt directory; receipt disabled for this run."
    ZOMBIE_RECEIPT=0
    return 0
  fi
  if [[ -f "${RECEIPT_FILE}" ]]; then
    chmod 600 "${RECEIPT_FILE}" 2>/dev/null || true
  elif ! install -m 600 /dev/null "${RECEIPT_FILE}" 2>/dev/null; then
    warn "Could not create the install receipt at ${RECEIPT_FILE}."
    ZOMBIE_RECEIPT=0
    return 0
  fi

  if ! {
    printf '============================================================\n'
    printf 'Ubuntu AI System Administrator — install receipt\n'
    printf '============================================================\n'
    printf 'Phase            : START\n'
    printf 'Started (UTC)    : %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'Installer        : %s %s\n' "${SCRIPT_NAME}" "${SCRIPT_VERSION}"
    printf 'Host             : %s %s (%s)\n' "${ID:-?}" "${VERSION_ID:-?}" \
      "$(dpkg --print-architecture 2>/dev/null || uname -m)"
    printf 'Invoked by       : %s (uid %s)\n' "${SUDO_USER:-$(id -un)}" "$(id -u)"
    printf 'Mode             : %s\n' \
      "$([[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && echo non-interactive || echo interactive)"
    printf '\n-- Parameters --\n'
    receipt_start_zombie
    printf 'Transcript log   : %s\n' "${LOG_FILE}"
    printf 'Receipt file     : %s\n' "${RECEIPT_FILE}"
    printf '============================================================\n'
  } >> "${RECEIPT_FILE}" 2>/dev/null; then
    warn "Could not write the install receipt to ${RECEIPT_FILE}."
    ZOMBIE_RECEIPT=0
    return 0
  fi
  chmod 600 "${RECEIPT_FILE}" 2>/dev/null || true
  info "Install receipt opened: ${RECEIPT_FILE}"
}

write_receipt_finish() {
  [[ "${ZOMBIE_RECEIPT}" == "1" ]] || return 0
  [[ -f "${RECEIPT_FILE}" ]] || return 0
  {
    printf '\n-- Finish --\n'
    printf 'Phase            : FINISH\n'
    printf 'Result           : SUCCESS\n'
    printf 'Finished (UTC)   : %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [[ -n "${INSTALL_T0:-}" ]]; then
      printf 'Duration         : %s\n' "$(fmt_duration "$(( $(date +%s) - INSTALL_T0 ))")"
    fi
    receipt_finish_zombie
    printf 'Steps satisfied  : %s\n' "${STEPS_SATISFIED}"
    printf 'Steps applied    : %s\n' "${STEPS_CHANGED}"
    [[ -n "${NEXT_STEP:-}" ]] && printf 'Next step        : %s\n' "${NEXT_STEP}"
    printf '============================================================\n'
  } >> "${RECEIPT_FILE}" 2>/dev/null || {
    warn "Could not finalise the install receipt at ${RECEIPT_FILE}."
    return 0
  }
  ok "Install receipt finalised: ${RECEIPT_FILE}"
}

# Append a short failure record to the receipt from the error trap.
write_receipt_fail() {
  [[ "${ZOMBIE_RECEIPT}" == "1" ]] || return 0
  [[ -f "${RECEIPT_FILE}" ]] || return 0
  {
    printf '\n-- Finish --\n'
    printf 'Phase            : FINISH\n'
    printf 'Result           : FAILED (line %s, exit %s)\n' "${1:-?}" "${2:-?}"
    printf 'Finished (UTC)   : %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    if [[ -n "${INSTALL_T0:-}" ]]; then
      printf 'Duration         : %s\n' "$(fmt_duration "$(( $(date +%s) - INSTALL_T0 ))")"
    fi
    printf 'Transcript log   : %s\n' "${LOG_FILE}"
    printf '============================================================\n'
  } >> "${RECEIPT_FILE}" 2>/dev/null || true
}

# ---------------------------------------------------------------------------
# Dispatch non-install subcommands early.
# ---------------------------------------------------------------------------

trap 'on_error ${LINENO}' ERR

validate_config

if [[ "${SUBCOMMAND}" != "uninstall" ]] \
    && (( UNINSTALL_ARCHIVE || UNINSTALL_KEEP_AGENT )); then
  die "--archive/--keep-agent only apply to the uninstall subcommand." 2
fi

case "${SUBCOMMAND}" in
  verify)    trap - ERR; cmd_verify; exit $? ;;
  doctor)    cmd_doctor; exit $? ;;
  repair)    require_root; cmd_repair; exit $? ;;
  uninstall) (( DRY_RUN )) || require_root; cmd_uninstall; exit $? ;;
  install)   ;;
  *)         die "Unknown subcommand: ${SUBCOMMAND}" 2 ;;
esac

if (( DRY_RUN )); then
  print_dry_run_plan
  exit 0
fi

# =============================================================================
# install — the rest of the file
# =============================================================================

require_root

# Bootstrap prerequisites: a fresh Ubuntu Desktop image ships without curl,
# and a minimal image can also lack python3. Both are needed before the main
# package phase — the local LLM scan, the preflight connectivity check, and
# every curl_get download rely on them — so install whichever is missing now.
# Idempotent: does nothing when both commands are already present.
bootstrap_prerequisites() {
  local missing=()
  command -v curl    >/dev/null 2>&1 || missing+=(curl)
  command -v python3 >/dev/null 2>&1 || missing+=(python3)
  (( ${#missing[@]} )) || return 0
  info "Installing missing prerequisite package(s): ${missing[*]}…"
  apt_get update -qq \
    || warn "apt-get update failed; attempting the install anyway."
  apt_install "${missing[@]}" \
    || die "Could not install prerequisite package(s): ${missing[*]}. Install them manually (apt-get install ${missing[*]}) and re-run." 1
  ok "Prerequisite package(s) installed: ${missing[*]}"
}
bootstrap_prerequisites

# Local LLM discovery: scan the host's IPv4 /24 for an OpenAI-compatible LLM
# server and offer the models it advertises as the starting model. Runs before
# the parameter review so the choice shows up in the table. No-op for
# --yes / non-interactive / non-TTY runs, when ZOMBIE_SKIP_LLM_SCAN=1, or when
# an environment or installed secrets file already selects a model.
discover_local_llms
review_parameters
preflight

# Transcript logging
mkdir -p "$(dirname "${LOG_FILE}")"
touch "${LOG_FILE}"
chmod 600 "${LOG_FILE}"
exec > >(tee -a "${LOG_FILE}") 2>&1

# Step-trace breadcrumb: every section() call writes to this file so a
# crashed install leaves a clear trail of which step failed and which
# steps preceded it. on_error() includes the tail in its diagnostic.
STEP_LOG="${LOG_FILE%.log}.steps"
mkdir -p "$(dirname "${STEP_LOG}")"
: > "${STEP_LOG}"
chmod 600 "${STEP_LOG}" 2>/dev/null || true

# Enable shell xtrace into the transcript only (not the console) when the
# operator asked for --verbose/--debug. BASH_XTRACEFD keeps the noisy trace
# out of the live terminal while preserving it for post-mortem debugging.
if (( VERBOSE )); then
  exec {_TRACE_FD}>>"${LOG_FILE}"
  BASH_XTRACEFD="${_TRACE_FD}"
  set -x
fi

# Phase counter: count the Zombie install sections so phase numbering remains
# accurate as the installer evolves.
ZOMBIE_PHASE=0
SECTION_RULE_WIDTH=60
count_zombie_phases() {
  awk '/^# install — the rest of the file/{f=1} f && /^section "/{c++} END{print c+0}' \
    "${BASH_SOURCE[0]}" 2>/dev/null || echo 0
}
ZOMBIE_PHASE_TOTAL="$(count_zombie_phases)"
_SECTION_T0=""

# Re-define section() to record a breadcrumb, number each phase, and report
# how long the previous phase took in a plain-English "Completed in …" line,
# without surrounding every transition in three heavy separator lines.
section() {
  local now; now="$(date +%s)"
  if [[ -n "${_SECTION_T0}" ]]; then
    (( ZOMBIE_QUIET )) || printf '%s    Completed in %s%s\n' \
      "${C_DIM}" "$(fmt_duration "$(( now - _SECTION_T0 ))")" "${C_RESET}"
  fi
  _SECTION_T0="${now}"
  ZOMBIE_PHASE=$(( ZOMBIE_PHASE + 1 ))
  printf '%s\t%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$*" >> "${STEP_LOG}" || true
  (( ZOMBIE_QUIET )) && return 0
  local counter
  if (( ZOMBIE_PHASE_TOTAL > 0 )); then
    counter="[${ZOMBIE_PHASE}/${ZOMBIE_PHASE_TOTAL}]"
  else
    counter="[${ZOMBIE_PHASE}]"
  fi
  printf '\n%s%sPhase %s%s  %s\n' \
    "${C_BRAND}" "${C_BOLD}" "${counter}" "${C_RESET}" "$*"
  brand_rule "${SECTION_RULE_WIDTH}"
}

# Augment on_error() with the step trail so an operator pasting the
# failure into an issue has both the line number AND the last few
# completed install phases.
on_error() {
  local exit_code=$?
  local line=$1
  printf '\n%s[x] %s failed on line %s with exit code %s.%s\n' \
    "${C_RED}" "${SCRIPT_NAME}" "${line}" "${exit_code}" "${C_RESET}" >&2
  printf '%s    Full transcript: %s%s\n' "${C_RED}" "${LOG_FILE}" "${C_RESET}" >&2
  if [[ -s "${STEP_LOG}" ]]; then
    printf '%s    Steps completed before failure (last 5):%s\n' "${C_RED}" "${C_RESET}" >&2
    tail -n 5 "${STEP_LOG}" | sed 's/^/      /' >&2 || true
    printf '%s    Full step trail: %s%s\n' "${C_RED}" "${STEP_LOG}" "${C_RESET}" >&2
  fi
  diagnose_failure "${exit_code}" || true
  write_receipt_fail "${line}" "${exit_code}" || true
  printf '%s    Exit codes: 1 generic · 2 usage · 64 missing env · 65 bad host · 66 network.%s\n' \
    "${C_RED}" "${C_RESET}" >&2
  printf '%s    Recovery: re-run the installer (it is idempotent), or %ssudo ./%s doctor%s for guidance.%s\n' \
    "${C_RED}" "${C_BOLD}" "${SCRIPT_NAME}" "${C_RESET}${C_RED}" "${C_RESET}" >&2
  exit "${exit_code}"
}

# Record the install start so the run can report total elapsed time at the
# end. The title is printed as a plain banner so it is not counted as a
# numbered phase.
INSTALL_T0="$(date +%s)"

info "Log file: ${LOG_FILE}"
info "Agent user: ${AGENT_USER}"
info "Install root: ${ZOMBIE_DIR}"
info "Chat port: ${CHAT_PORT} (loopback only)"
info "Mode: $([[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && echo non-interactive || echo interactive)"
info "Phases: ${ZOMBIE_PHASE_TOTAL}. Typical run takes ~10–20 min depending on network speed."
cat <<EOF

This installer will:
  - Create the ${AGENT_USER} user (operating identity of the AI Systems Administrator) with passwordless sudo
  - Install Python and Node agent runtimes
  - Install the loopback chat service (ubuntu-zombie-chat.service)
  - Install policy, audit log, and helper scripts
  - Enable automatic security updates

Run this from the physical Ubuntu machine, not over public SSH.

EOF

if [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]]; then
  info "Non-interactive mode: proceeding without confirmation."
elif (( ASSUME_YES )); then
  info "--yes: proceeding without confirmation."
elif (( REVIEWED )); then
  info "Parameters reviewed and accepted: proceeding."
else
  read -r -p "Continue? Type YES to proceed: " CONFIRM
  [[ "${CONFIRM}" == "YES" ]] || { info "Cancelled."; exit 0; }
fi

# Open the install receipt now that every parameter is finalised and the
# operator has committed to the run.
write_receipt_start

# ---------------------------------------------------------------------------
# System packages
# ---------------------------------------------------------------------------

install_zombie_base() {
section "Update the operating system"

apt_get update
apt_get -y upgrade

section "Install system dependencies"

apt_install \
  sudo \
  curl \
  wget \
  ca-certificates \
  gnupg \
  lsb-release \
  software-properties-common \
  apt-transport-https \
  git \
  vim \
  nano \
  tmux \
  htop \
  unzip \
  zip \
  jq \
  iputils-ping \
  unattended-upgrades \
  logrotate \
  python3 \
  python3-pip \
  python3-venv \
  pipx \
  build-essential \
  ripgrep \
  fd-find \
  tree \
  rsync \
  cron \
  pwgen \
  psmisc

# ---------------------------------------------------------------------------
# Agent user and sudo
# ---------------------------------------------------------------------------

section "Configure the ${AGENT_USER} agent identity"

if id "${AGENT_USER}" >/dev/null 2>&1; then
  info "User ${AGENT_USER} already exists."
else
  adduser --gecos "" --disabled-password "${AGENT_USER}"
  ok "Created user ${AGENT_USER}."
fi

usermod -aG sudo "${AGENT_USER}"

SUDOERS_FILE="/etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie"
SUDOERS_TMP="$(mktemp "${SUDOERS_FILE}.XXXXXX")"
cat > "${SUDOERS_TMP}" <<EOF
# Managed by ${SCRIPT_NAME}. Grants ${AGENT_USER} passwordless root.
${AGENT_USER} ALL=(ALL) NOPASSWD:ALL
EOF
if ! visudo -cf "${SUDOERS_TMP}" >/dev/null; then
  rm -f "${SUDOERS_TMP}"
  die "Generated sudoers drop-in failed validation." 1
fi
install -m 0440 "${SUDOERS_TMP}" "${SUDOERS_FILE}"
rm -f "${SUDOERS_TMP}"
ok "Configured passwordless sudo for ${AGENT_USER}."

# ---------------------------------------------------------------------------
# Security services and unattended upgrades
# ---------------------------------------------------------------------------

section "Configure automatic security updates"

systemctl enable --now unattended-upgrades >/dev/null || true

cat > /etc/apt/apt.conf.d/20auto-upgrades <<'EOF'
APT::Periodic::Update-Package-Lists "1";
APT::Periodic::Unattended-Upgrade "1";
APT::Periodic::AutocleanInterval "7";
EOF

cat > /etc/apt/apt.conf.d/52unattended-upgrades-local <<'EOF'
Unattended-Upgrade::Automatic-Reboot "true";
Unattended-Upgrade::Automatic-Reboot-Time "04:00";
Unattended-Upgrade::Remove-Unused-Kernel-Packages "true";
Unattended-Upgrade::Remove-Unused-Dependencies "true";
EOF

ok "Automatic security updates enabled (reboots at 04:00 if required)."

section "Keep the desktop available"

systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target >/dev/null 2>&1 || true

ok "Sleep and suspend targets masked."

# ---------------------------------------------------------------------------
# Workspace at ${ZOMBIE_DIR}
# ---------------------------------------------------------------------------

section "Prepare application state"

install -d -m 755 -o "${AGENT_USER}" -g "${AGENT_USER}" "${ZOMBIE_DIR}" \
  "${ZOMBIE_DIR}/bin" "${ZOMBIE_DIR}/logs" "${ZOMBIE_DIR}/state" \
  "${ZOMBIE_DIR}/scripts" "${ZOMBIE_DIR}/tools" "${ZOMBIE_DIR}/agent" \
  "${ZOMBIE_DIR}/agent/templates"
install -d -m 700 -o "${AGENT_USER}" -g "${AGENT_USER}" "${ZOMBIE_DIR}/secrets"
install -d -m 755 "${ZOMBIE_ETC}"
install -d -m 750 -o "${AGENT_USER}" -g "${AGENT_USER}" "${ZOMBIE_LOG_DIR}"

if [[ ! -f "${ZOMBIE_DIR}/secrets/env" ]]; then
  install -m 600 -o "${AGENT_USER}" -g "${AGENT_USER}" /dev/null "${ZOMBIE_DIR}/secrets/env"
  cat > "${ZOMBIE_DIR}/secrets/env" <<EOF
# Token provider credentials and runtime environment for the AI Systems Administrator.
# Pick ONE provider line and paste the key. The same provider + model
# selection drives BOTH the agent loop (pi-mono / the actual chat
# answers) and the status banner — there is a single source of truth.
#   OPENAI_API_KEY=sk-...
#   ANTHROPIC_API_KEY=sk-ant-...
#   GEMINI_API_KEY=...
#   XAI_API_KEY=...
#   OPENROUTER_API_KEY=...
#   MISTRAL_API_KEY=...
#   GROQ_API_KEY=...
#
# Optional:
#   ZOMBIE_PROVIDER=openai      # openai|anthropic|gemini|xai|openrouter|mistral|groq|lmstudio
#   ZOMBIE_MODEL=gpt-4o-mini    # model for the agent loop + chat (required for openrouter/lmstudio)
#   LMSTUDIO_API_KEY=local      # local OpenAI-compatible server (LM Studio, Ollama,
#                               # llama.cpp). Pair with ZOMBIE_PROVIDER=lmstudio; the
#                               # server URL lives in ~/.pi/agent/models.json.
#   ZOMBIE_CHAT_PORT=${CHAT_PORT}

DISPLAY=:0
ZOMBIE_DIR=${ZOMBIE_DIR}
AGENT_USER=${AGENT_USER}
AGENT_HOME=${AGENT_HOME}
ZOMBIE_CHAT_PORT=${CHAT_PORT}
EOF
  if [[ -n "${LOCAL_LLM_MODEL}" ]]; then
    cat >> "${ZOMBIE_DIR}/secrets/env" <<EOF

# Local LLM auto-discovered on the LAN during install: an OpenAI-compatible
# server at ${LOCAL_LLM_BASE_URL}. The agent loop (pi-mono / the actual chat
# answers) reaches it through the custom 'lmstudio' provider defined in
# ${AGENT_HOME}/.pi/agent/models.json, which carries the server URL. Most local
# servers ignore the API key; replace it if yours requires one.
ZOMBIE_PROVIDER=lmstudio
ZOMBIE_MODEL=${LOCAL_LLM_MODEL}
LMSTUDIO_API_KEY=${ZOMBIE_LOCAL_LLM_API_KEY}
EOF
  fi
  chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/secrets/env"
  chmod 600 "${ZOMBIE_DIR}/secrets/env"
  if [[ -n "${LOCAL_LLM_MODEL}" ]]; then
    write_pi_models_json "${LOCAL_LLM_BASE_URL}" "${LOCAL_LLM_MODEL}"
    ok "Created ${ZOMBIE_DIR}/secrets/env with local LLM ${LOCAL_LLM_MODEL} at ${LOCAL_LLM_BASE_URL}."
  else
    ok "Created ${ZOMBIE_DIR}/secrets/env (edit with: sudo ${ZOMBIE_DIR}/bin/secrets-edit)."
  fi
else
  info "Preserving existing ${ZOMBIE_DIR}/secrets/env."
  if grep -q '^ZOMBIE_CHAT_PORT=' "${ZOMBIE_DIR}/secrets/env"; then
    sed -i -E "s|^ZOMBIE_CHAT_PORT=.*$|ZOMBIE_CHAT_PORT=${CHAT_PORT}|" "${ZOMBIE_DIR}/secrets/env"
  else
    [[ -s "${ZOMBIE_DIR}/secrets/env" ]] && [[ "$(tail -c1 "${ZOMBIE_DIR}/secrets/env" 2>/dev/null)" != $'\n' ]] && printf '\n' >> "${ZOMBIE_DIR}/secrets/env"
    printf 'ZOMBIE_CHAT_PORT=%s\n' "${CHAT_PORT}" >> "${ZOMBIE_DIR}/secrets/env"
  fi
  # When a local LLM was discovered during this run, also apply the
  # lmstudio provider settings to the existing secrets/env so a
  # re-install picks up the new backend instead of silently keeping
  # whatever provider was previously selected (the chat banner would
  # otherwise still show e.g. "openai" even though the operator
  # intends to use the local server).
  if [[ -n "${LOCAL_LLM_MODEL}" ]]; then
    # Drop any prior provider/model/key lines so we can append fresh
    # values without sed-escaping the operator-supplied key (which may
    # contain characters that would otherwise terminate the s|||
    # expression).
    sed -i -E '/^(ZOMBIE_PROVIDER|ZOMBIE_MODEL|LMSTUDIO_API_KEY)=/d' \
      "${ZOMBIE_DIR}/secrets/env"
    [[ -s "${ZOMBIE_DIR}/secrets/env" ]] && [[ "$(tail -c1 "${ZOMBIE_DIR}/secrets/env" 2>/dev/null)" != $'\n' ]] && printf '\n' >> "${ZOMBIE_DIR}/secrets/env"
    {
      printf 'ZOMBIE_PROVIDER=lmstudio\n'
      printf 'ZOMBIE_MODEL=%s\n' "${LOCAL_LLM_MODEL}"
      printf 'LMSTUDIO_API_KEY=%s\n' "${ZOMBIE_LOCAL_LLM_API_KEY}"
    } >> "${ZOMBIE_DIR}/secrets/env"
    write_pi_models_json "${LOCAL_LLM_BASE_URL}" "${LOCAL_LLM_MODEL}"
    ok "Applied local LLM ${LOCAL_LLM_MODEL} at ${LOCAL_LLM_BASE_URL} to existing secrets/env."
  fi
  chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/secrets/env"
  chmod 600 "${ZOMBIE_DIR}/secrets/env"
fi

# Stamp the chat-UI password hash into secrets/env (idempotent: keeps an
# existing hash unless the operator chose a new password this run).
ensure_admin_password_hash "${ZOMBIE_DIR}/secrets/env"
chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/secrets/env"
chmod 600 "${ZOMBIE_DIR}/secrets/env"
# ---------------------------------------------------------------------------
# Python cloud-agent runtime
# ---------------------------------------------------------------------------

section "Build the Python runtime"

# Stage the venv setup helper into ${ZOMBIE_DIR}/bin early so the
# unprivileged setup below can exec it. The rest of the operator
# helpers are installed in the "Deploy chat service" section below.
# Extracted in FIX-1-12 so the body is lintable by ShellCheck.
install -m 755 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${PAYLOAD_DIR}/bin/setup-agent-venv" "${ZOMBIE_DIR}/bin/setup-agent-venv"

# Build the venv and install Python packages as the agent user. On an
# interactive TTY show a heartbeat spinner and route the detail to the
# transcript, while non-interactive/CI runs keep the full output streaming.
if [[ -t 2 ]] && ! (( ZOMBIE_QUIET )); then
  run_step "Building Python venv" -- \
    bash -c 'runuser -l "$1" -- "$2" >>"$3" 2>&1' \
    _ "${AGENT_USER}" "${ZOMBIE_DIR}/bin/setup-agent-venv" "${LOG_FILE}"
else
  runuser -l "${AGENT_USER}" -- "${ZOMBIE_DIR}/bin/setup-agent-venv"
fi

ok "Python venv ready at ${AGENT_HOME}/agent-env."

# ---------------------------------------------------------------------------
# Node runtime
# ---------------------------------------------------------------------------

section "Build the Node agent runtime"

# The npm bundled with Ubuntu's apt-provided `nodejs` (Node 18 on
# 22.04/24.04) is too old to self-upgrade to npm@latest, which now
# requires Node ^20.17.0 || >=22.9.0. Install Node 22.x from the
# official NodeSource apt repository so the global npm install below —
# and the pi-ai / pi-coding-agent globals that follow — see a Node
# runtime they actually support. Pattern uses the standard signed-by
# keyring + sources.list.d drop-in apt repository setup.
NODESOURCE_KEYRING="/usr/share/keyrings/nodesource.gpg"
NODESOURCE_SOURCES="/etc/apt/sources.list.d/nodesource.sources"
NODESOURCE_PREF="/etc/apt/preferences.d/nodejs"
NODE_MAJOR="22"
NODE_ARCH="$(dpkg --print-architecture)"
case "${NODE_ARCH}" in
  amd64|arm64) : ;;
  *) die "NodeSource supports only amd64/arm64; detected '${NODE_ARCH}'." 65 ;;
esac
install -d -m 755 "$(dirname "${NODESOURCE_KEYRING}")"
# Remove any legacy one-line NodeSource list left by an older install
# or manual setup; we now manage the source via the deb822 file below.
rm -f /etc/apt/sources.list.d/nodesource.list
curl_get https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key \
  | gpg --dearmor --yes -o "${NODESOURCE_KEYRING}"
chmod 0644 "${NODESOURCE_KEYRING}"
cat > "${NODESOURCE_SOURCES}" <<EOF
Types: deb
URIs: https://deb.nodesource.com/node_${NODE_MAJOR}.x
Suites: nodistro
Components: main
Architectures: ${NODE_ARCH}
Signed-By: ${NODESOURCE_KEYRING}
EOF
# Pin nodejs to the NodeSource origin so apt always prefers it over the
# older Ubuntu archive package on subsequent upgrades.
cat > "${NODESOURCE_PREF}" <<EOF
Package: nodejs
Pin: origin deb.nodesource.com
Pin-Priority: 600
EOF
apt_get update
apt_install nodejs

# Upgrading npm in place is booby-trapped on recent Node releases:
# `npm install -g npm@latest` makes npm reinstall *itself*, and partway
# through the reify pipeline it removes its own `node_modules` (including
# transitive deps such as `promise-retry`) before arborist's rebuild step
# lazily `require()`s them — so the command dies with
#   MODULE_NOT_FOUND / Cannot find module 'promise-retry'
# (see nodejs/node#62425, npm/cli#9151, actions/runner-images#13883).
#
# This is NOT merely an incomplete-bundle problem: the self-upgrade crashes
# even when the running npm is complete (verified against the official
# nodejs.org tarball, which does ship promise-retry). Repairing the bundle
# and re-running the self-upgrade therefore just re-triggers the same race.
#
# So we never ask npm to upgrade itself. Instead we fetch the latest npm
# release straight from the npm registry — whose published tarball bundles
# all of npm's dependencies — verify its Subresource Integrity hash, and drop
# it into the global node_modules ourselves. No reify, no self-deletion race,
# and the result is a complete, current npm. The retry wrapper around this
# only has to cover transient network failures.
npm_install_root() {
  local npm_cmd="$1"
  node -e '
    const fs = require("fs");
    const path = require("path");
    let dir;
    try {
      dir = path.dirname(fs.realpathSync(process.argv[1]));
    } catch (_) {
      process.exit(1);
    }
    while (true) {
      if (path.basename(dir) === "npm" &&
          fs.existsSync(path.join(dir, "package.json"))) {
        console.log(dir);
        process.exit(0);
      }
      const parent = path.dirname(dir);
      if (parent === dir) {
        process.exit(1);
      }
      dir = parent;
    }
  ' "${npm_cmd}"
}

# Install the latest npm release from the npm registry without going through
# npm's self-upgrade (see the long note above for why that self-destructs).
# The registry's published tarball bundles every npm dependency, so unpacking
# it straight into the global node_modules yields a complete, current npm with
# no reify step. We require and verify the registry-provided Subresource
# Integrity hash before extracting as root, and parse the packument with node
# (already installed) to avoid pulling in a jq dependency. Transient network
# errors bubble up as a non-zero return so the retry wrapper can try again.
install_npm_latest() {
  local npm_cmd npm_root tmp_dir version tarball_url integrity tarball
  npm_cmd="$(command -v npm)" || die "npm command missing after nodejs install." 1
  npm_root="$(npm_install_root "${npm_cmd}")" \
    || die "Could not resolve npm install root for ${npm_cmd}." 1
  tmp_dir="$(mktemp -d)"
  curl_get "https://registry.npmjs.org/npm/latest" -o "${tmp_dir}/latest.json" \
    || { rm -rf "${tmp_dir}"; return 1; }
  node -e '
    const m = require(process.argv[1]);
    if (!m.version || !m.dist || !m.dist.tarball || typeof m.dist.integrity !== "string") process.exit(1);
    const sri = m.dist.integrity;
    const i = sri.indexOf("-");
    if (i <= 0 || i === sri.length - 1) process.exit(1);
    process.stdout.write([m.version, m.dist.tarball, sri].join("\n") + "\n");
  ' "${tmp_dir}/latest.json" > "${tmp_dir}/meta.txt" \
    || { rm -rf "${tmp_dir}"; die "npm registry metadata for the latest npm release was missing a valid integrity hash." 1; }
  version="$(sed -n 1p "${tmp_dir}/meta.txt")"
  tarball_url="$(sed -n 2p "${tmp_dir}/meta.txt")"
  integrity="$(sed -n 3p "${tmp_dir}/meta.txt")"
  [[ -n "${version}" && -n "${tarball_url}" && -n "${integrity}" ]] \
    || { rm -rf "${tmp_dir}"; die "npm registry metadata for the latest npm release was incomplete." 1; }
  tarball="${tmp_dir}/npm.tgz"
  curl_get "${tarball_url}" -o "${tarball}" \
    || { rm -rf "${tmp_dir}"; return 1; }
  # Verify the registry's SRI hash (e.g. "sha512-<base64>") before trusting the
  # archive. A mismatch means a corrupt or tampered download, so we abort hard
  # rather than retrying a request that would keep failing the same way.
  node -e '
    const fs = require("fs"), crypto = require("crypto");
    const sri = process.argv[1], file = process.argv[2];
    const i = sri.indexOf("-");
    if (i <= 0 || i === sri.length - 1) process.exit(1);
    const algo = sri.slice(0, i);
    const expected = sri.slice(i + 1);
    const got = crypto.createHash(algo).update(fs.readFileSync(file)).digest("base64");
    process.exit(got === expected ? 0 : 1);
  ' "${integrity}" "${tarball}" \
    || { rm -rf "${tmp_dir}"; die "Integrity check failed for npm@${version} from the npm registry." 1; }
  tar -xzf "${tarball}" -C "${tmp_dir}" \
    || { rm -rf "${tmp_dir}"; return 1; }
  [[ -d "${tmp_dir}/package" ]] \
    || { rm -rf "${tmp_dir}"; die "npm registry tarball for npm@${version} had an unexpected layout." 1; }
  rm -rf "${npm_root}"
  mkdir -p "$(dirname "${npm_root}")"
  cp -a "${tmp_dir}/package" "${npm_root}"
  rm -rf "${tmp_dir}"
  npm --version >/dev/null \
    || die "npm broken after installing npm@${version} from the registry." 1
  log "Installed npm@${version} from the npm registry."
}
retry 4 5 -- install_npm_latest
retry 4 5 -- npm install -g --ignore-scripts yarn pnpm typescript ts-node

install_latest_node_bridge() {
  local name="$1" package="$2" metadata_url="$3"
  local tmp_dir version tarball_url integrity tarball
  tmp_dir="$(mktemp -d)"
  curl_get "${metadata_url}" -o "${tmp_dir}/latest.json" \
    || { rm -rf "${tmp_dir}"; return 1; }
  node -e '
    const m = require(process.argv[1]);
    if (!m.version || !m.dist || !m.dist.tarball ||
        typeof m.dist.integrity !== "string") {
      console.error("metadata is missing version, tarball, or integrity");
      process.exit(1);
    }
    let tarball;
    try {
      tarball = new URL(m.dist.tarball);
    } catch {
      console.error("metadata contains an invalid tarball URL");
      process.exit(1);
    }
    if (tarball.protocol !== "https:" ||
        tarball.hostname !== "registry.npmjs.org") {
      console.error("metadata tarball URL is outside the npm registry");
      process.exit(1);
    }
    const i = m.dist.integrity.indexOf("-");
    if (i <= 0 || i === m.dist.integrity.length - 1 ||
        m.dist.integrity.slice(0, i) !== "sha512") {
      console.error("metadata must contain a sha512 integrity value");
      process.exit(1);
    }
    process.stdout.write(
      [m.version, m.dist.tarball, m.dist.integrity].join("\n") + "\n"
    );
  ' "${tmp_dir}/latest.json" > "${tmp_dir}/meta.txt" \
    || { rm -rf "${tmp_dir}"; die "npm metadata for latest ${package} was invalid." 1; }
  version="$(sed -n 1p "${tmp_dir}/meta.txt")"
  tarball_url="$(sed -n 2p "${tmp_dir}/meta.txt")"
  integrity="$(sed -n 3p "${tmp_dir}/meta.txt")"
  [[ -n "${version}" && -n "${tarball_url}" && -n "${integrity}" ]] \
    || { rm -rf "${tmp_dir}"; die "npm metadata for latest ${package} was incomplete." 1; }

  tarball="${tmp_dir}/${name}.tgz"
  curl_get "${tarball_url}" -o "${tarball}" \
    || { rm -rf "${tmp_dir}"; return 1; }
  node -e '
    const fs = require("fs"), crypto = require("crypto");
    const sri = process.argv[1], file = process.argv[2];
    const i = sri.indexOf("-");
    if (i <= 0 || i === sri.length - 1 || sri.slice(0, i) !== "sha512") {
      console.error("malformed or unsupported integrity value");
      process.exit(1);
    }
    const got = crypto.createHash(sri.slice(0, i))
      .update(fs.readFileSync(file)).digest("base64");
    if (got !== sri.slice(i + 1)) {
      console.error("tarball integrity does not match registry metadata");
      process.exit(1);
    }
  ' "${integrity}" "${tarball}" \
    || { rm -rf "${tmp_dir}"; die "Integrity check failed for ${package}@${version}." 1; }

  log "Installing latest ${package} (${version}) from its integrity-verified tarball."
  npm install -g --ignore-scripts "${tarball}" \
    || { rm -rf "${tmp_dir}"; return 1; }
  rm -rf "${tmp_dir}"
  npm ls -g --depth=0 "${package}@${version}" >/dev/null \
    || die "${package}@${version} was not installed successfully." 1
  # name is the stable internal bridge label, not necessarily the npm package
  # basename (pi-mono maps to @earendil-works/pi-coding-agent).
  case "${name}" in
    pi-ai) PI_AI_VERSION="${version}" ;;
    pi-mono) PI_MONO_VERSION="${version}" ;;
    *) die "Unknown Earendil module label: ${name}." 1 ;;
  esac
}

# Resolve both Earendil modules at install time so every install and repair
# converges on the newest npm release. Registry-provided SRI is verified before
# npm sees either tarball.
retry 4 5 -- install_latest_node_bridge \
  pi-ai @earendil-works/pi-ai \
  "https://registry.npmjs.org/@earendil-works%2Fpi-ai/latest"

# pi-mono is the agent loop the chat service drives via
# payload/agent/pi-mono-bridge.mjs.
retry 4 5 -- install_latest_node_bridge \
  pi-mono @earendil-works/pi-coding-agent \
  "https://registry.npmjs.org/@earendil-works%2Fpi-coding-agent/latest"
}

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# Deploy payload: chat service, helpers, policy, systemd, logrotate.
# ---------------------------------------------------------------------------

install_zombie_runtime() {
section "Deploy the agent runtime"

if [[ ! -d "${PAYLOAD_DIR}" ]]; then
  die "Payload directory ${PAYLOAD_DIR} not found. Re-clone the repository." 1
fi

# Chat service source.
install -d -m 755 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${ZOMBIE_DIR}/agent" "${ZOMBIE_DIR}/agent/templates"
for f in server.py providers.py policy.py audit.py runner.py history.py tools.py pi_mono.py skill_loader.py auth.py lifecycle.py examples.md; do
  install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
    "${PAYLOAD_DIR}/agent/${f}" "${ZOMBIE_DIR}/agent/${f}"
done
# The pi-ai bridge and its version pin travel with the Python sources
# so providers.py can find them at the default path. Bridge is
# read-only; only root mutates the agent tree.
install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${PAYLOAD_DIR}/agent/pi-ai-bridge.mjs" "${ZOMBIE_DIR}/agent/pi-ai-bridge.mjs"
printf '%s\n' "${PI_AI_VERSION}" > "${ZOMBIE_DIR}/agent/pi-ai.version"
chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/agent/pi-ai.version"
chmod 644 "${ZOMBIE_DIR}/agent/pi-ai.version"
# Deploy the payload VERSION alongside the agent tree so the chat
# service can report it via /api/version (the /version chat command).
if [[ -f "${REPO_ROOT}/VERSION" ]]; then
  install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
    "${REPO_ROOT}/VERSION" "${ZOMBIE_DIR}/VERSION"
fi
# pi-mono bridge + version pin live alongside the pi-ai ones for the
# same reasons.
install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${PAYLOAD_DIR}/agent/pi-mono-bridge.mjs" "${ZOMBIE_DIR}/agent/pi-mono-bridge.mjs"
printf '%s\n' "${PI_MONO_VERSION}" > "${ZOMBIE_DIR}/agent/pi-mono.version"
chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/agent/pi-mono.version"
chmod 644 "${ZOMBIE_DIR}/agent/pi-mono.version"
install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${PAYLOAD_DIR}/agent/templates/index.html" "${ZOMBIE_DIR}/agent/templates/index.html"
install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${PAYLOAD_DIR}/agent/templates/settings.json.tmpl" "${ZOMBIE_DIR}/agent/templates/settings.json.tmpl"
install -m 644 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${PAYLOAD_DIR}/agent/templates/APPEND_SYSTEM.md.tmpl" "${ZOMBIE_DIR}/agent/templates/APPEND_SYSTEM.md.tmpl"

# Initialise the Time-to-Live kill switch now that lifecycle.py is deployed,
# preserving valid state from an existing installation.
init_lifecycle_state

# Render pi-mono runtime configs into ${ZOMBIE_DIR}/pi/. Root-owned,
# world-readable; the chat service reads them but does not need to
# mutate them.
install -d -m 755 -o root -g root "${ZOMBIE_DIR}/pi"
install -d -m 750 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${ZOMBIE_DIR}/state/logs" "${ZOMBIE_DIR}/state/pi-mono-sessions"
sed -e "s|__ZOMBIE_DIR__|${ZOMBIE_DIR}|g" \
  "${PAYLOAD_DIR}/agent/templates/settings.json.tmpl" \
  | install -m 644 /dev/stdin "${ZOMBIE_DIR}/pi/settings.json"
# Render APPEND_SYSTEM.md via the chat-service helper so a single
# implementation is the source of truth for the rendered text.
if (cd "${PAYLOAD_DIR}/agent" && python3 server.py --render-append-system) \
       > "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md.tmp" 2>/dev/null; then
  install -m 644 "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md.tmp" \
    "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md"
  rm -f "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md.tmp"
else
  # Fallback: substitute placeholders from the template directly.
  rm -f "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md.tmp"
  sed -e "s|__AGENT_USER__|${AGENT_USER}|g" \
      -e "s|__FACTS__|hostname=$(hostname) os=$(. /etc/os-release && echo "${PRETTY_NAME}")|g" \
      "${PAYLOAD_DIR}/agent/templates/APPEND_SYSTEM.md.tmpl" \
    | install -m 644 /dev/stdin "${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md"
fi

# Snapshot the conversations DB *before* the chat-service binary runs
# the schema migration. The migration is additive (forward-only,
# behind PRAGMA user_version) but a snapshot lets operators roll back
# without losing history. The bak file name embeds the timestamp.
if [[ -f "${ZOMBIE_DIR}/state/conversations.db" ]]; then
  _ts="$(date -u +%Y%m%dT%H%M%SZ)"
  cp -a "${ZOMBIE_DIR}/state/conversations.db" \
        "${ZOMBIE_DIR}/state/conversations.db.bak.${_ts}" \
    || warn "Could not snapshot conversations.db (continuing)."
fi

section "Install policy and operator tools"

# Operator helpers.
for f in audit-recent health-check collect-diagnostics secrets-edit zombie-chat setup-agent-venv verify-release; do
  install -m 755 -o "${AGENT_USER}" -g "${AGENT_USER}" \
    "${PAYLOAD_DIR}/bin/${f}" "${ZOMBIE_DIR}/bin/${f}"
done
# Also make secrets-edit and audit-recent reachable on PATH.
ln -sf "${ZOMBIE_DIR}/bin/zombie-chat"          /usr/local/bin/zombie-chat
ln -sf "${ZOMBIE_DIR}/bin/audit-recent"         /usr/local/bin/audit-recent
ln -sf "${ZOMBIE_DIR}/bin/secrets-edit"         /usr/local/bin/secrets-edit
ln -sf "${ZOMBIE_DIR}/bin/health-check"         /usr/local/bin/zombie-health
ln -sf "${ZOMBIE_DIR}/bin/collect-diagnostics"  /usr/local/bin/zombie-diagnostics

# Policy.
if [[ ! -f "${ZOMBIE_ETC}/policy.yaml" ]]; then
  install -m 644 "${PAYLOAD_DIR}/etc/policy.yaml" "${ZOMBIE_ETC}/policy.yaml"
  ok "Installed default policy at ${ZOMBIE_ETC}/policy.yaml."
else
  info "Preserving existing ${ZOMBIE_ETC}/policy.yaml."
fi

# Ship the built-in skill catalogue to ${ZOMBIE_DIR}/skills/
# (root-owned, world-readable) and provision the operator-extensible
# /etc/ubuntu-zombie/skills.d/ tree with the same mode/owner contract
# as policy.yaml. Skills are static markdown read at chat-turn time;
# the loader never mutates them.
install -d -m 755 -o root -g root "${ZOMBIE_DIR}/skills"
if [[ -d "${PAYLOAD_DIR}/agent/skills" ]]; then
  shopt -s nullglob
  for f in "${PAYLOAD_DIR}/agent/skills/"*.md; do
    install -m 644 -o root -g root "${f}" "${ZOMBIE_DIR}/skills/$(basename "${f}")"
  done
  shopt -u nullglob
  ok "Installed built-in skills to ${ZOMBIE_DIR}/skills/."
fi
install -d -m 755 -o root -g root "${ZOMBIE_ETC}/skills.d"

# logrotate. Render the chosen account and install root.
sed -e "s|__AGENT_USER__|${AGENT_USER}|g" \
    -e "s|__ZOMBIE_DIR__|${ZOMBIE_DIR}|g" \
    "${PAYLOAD_DIR}/logrotate/ubuntu-zombie" \
    | install -m 644 /dev/stdin /etc/logrotate.d/ubuntu-zombie

# Audit log seed file (so chat service can open it without race).
if [[ ! -f "${ZOMBIE_LOG_DIR}/audit.log" ]]; then
  install -m 640 -o "${AGENT_USER}" -g "${AGENT_USER}" /dev/null "${ZOMBIE_LOG_DIR}/audit.log"
fi

section "Enable background services"

# systemd units. The shipped unit files use the literal placeholders
# `__AGENT_USER__` and `__AGENT_HOME__` so the chosen account name is
# substituted in at install time. This keeps the units valid for the
# default `zombie` account and any operator-chosen override.
render_unit() {
  local src="$1" dest="$2"
  # NOTE (FIX-1-17): The `s|…|${AGENT_USER}|g` substitution is only safe
  # because `is_supported_agent_username` (see validate_config) forbids the
  # sed-special characters `|`, `&`, and `\` in the username. If that
  # validator is ever relaxed, escape AGENT_USER/AGENT_HOME for sed here.
  sed -e "s|__AGENT_USER__|${AGENT_USER}|g" \
      -e "s|__AGENT_HOME__|${AGENT_HOME}|g" \
      -e "s|__ZOMBIE_DIR__|${ZOMBIE_DIR}|g" \
      "${src}" | install -m 644 /dev/stdin "${dest}"
}
render_unit "${PAYLOAD_DIR}/systemd/ubuntu-zombie-chat.service"   /etc/systemd/system/ubuntu-zombie-chat.service
render_unit "${PAYLOAD_DIR}/systemd/ubuntu-zombie-health.service" /etc/systemd/system/ubuntu-zombie-health.service
install -m 644 "${PAYLOAD_DIR}/systemd/ubuntu-zombie-health.timer"   /etc/systemd/system/ubuntu-zombie-health.timer
systemctl daemon-reload
systemctl enable ubuntu-zombie-chat.service >/dev/null 2>&1 \
  || warn "Could not enable the chat service; see journalctl -u ubuntu-zombie-chat"
# Use restart, not just start: on an in-place upgrade the agent tree
# (server.py, templates/index.html, VERSION) has just been overwritten,
# but `enable --now` would leave an already-running unit untouched, so
# the old process would keep serving the new template — rendering a
# literal "v{{VERSION}}" footer and a UI that no longer matches its API.
# Restart is idempotent: it starts the unit if it is stopped.
systemctl restart ubuntu-zombie-chat.service \
  || warn "Chat service did not start; see journalctl -u ubuntu-zombie-chat"
systemctl enable --now ubuntu-zombie-health.timer || true
ok "Chat service installed and enabled."

# ---------------------------------------------------------------------------
# Verification script
# ---------------------------------------------------------------------------

section "Install health checks"

cat > "${ZOMBIE_DIR}/bin/verify" <<EOF
#!/usr/bin/env bash
set -uo pipefail

ZOMBIE_DIR="${ZOMBIE_DIR}"
AGENT_USER="${AGENT_USER}"
AGENT_HOME="${AGENT_HOME}"
PI_AI_VERSION="${PI_AI_VERSION}"
PI_MONO_VERSION="${PI_MONO_VERSION}"

JSON="\${ZOMBIE_JSON:-0}"

if [[ -t 1 && "\${JSON}" != "1" ]]; then
  C_RESET=\$'\\033[0m'; C_RED=\$'\\033[31m'; C_GREEN=\$'\\033[32m'; C_BOLD=\$'\\033[1m'; C_YEL=\$'\\033[33m'
else
  C_RESET=""; C_RED=""; C_GREEN=""; C_BOLD=""; C_YEL=""
fi

PASS=0; FAIL=0
JSON_ITEMS=""

json_escape() {
  local s="\$1"
  s="\${s//\\\\/\\\\\\\\}"
  s="\${s//\\"/\\\\\\"}"
  printf '%s' "\${s}"
}

record() {
  # record <ok|fail|skip> <label>
  local st="\$1" label="\$2"
  case "\${st}" in
    ok)   PASS=\$((PASS+1)) ;;
    fail) FAIL=\$((FAIL+1)) ;;
  esac
  local item
  item="{\\"status\\": \\"\${st}\\", \\"label\\": \\"\$(json_escape "\${label}")\\"}"
  if [[ -z "\${JSON_ITEMS}" ]]; then JSON_ITEMS="\${item}"; else JSON_ITEMS="\${JSON_ITEMS},\${item}"; fi
}

# hd <text> — print a human-readable group header (suppressed in JSON mode).
hd() { [[ "\${JSON}" == "1" ]] || printf '%s\\n' "\$1"; }

check() {
  local label="\$1"; shift
  if "\$@" >/dev/null 2>&1; then
    record ok "\${label}"
    [[ "\${JSON}" == "1" ]] || printf '  %s[ok]%s %s\\n' "\${C_GREEN}" "\${C_RESET}" "\${label}"
  else
    record fail "\${label}"
    [[ "\${JSON}" == "1" ]] || printf '  %s[x]%s  %s\\n' "\${C_RED}" "\${C_RESET}" "\${label}"
  fi
}

[[ "\${JSON}" == "1" ]] || printf '\\n%s== ubuntu-zombie verify ==%s\\n' "\${C_BOLD}" "\${C_RESET}"
[[ "\${JSON}" == "1" ]] || echo

hd "User and sudo:"
check "running as \${AGENT_USER}"          test "\$(id -un)" = "\${AGENT_USER}"
check "passwordless sudo"                  sudo -n true
[[ "\${JSON}" == "1" ]] || echo

hd "Network and services:"
check "loopback chat port configured"         test -n "${ZOMBIE_CHAT_PORT:-${CHAT_PORT}}"
[[ "\${JSON}" == "1" ]] || echo

hd "Runtime:"
check "Python venv exists"                 test -x \${AGENT_HOME}/agent-env/bin/python
check "node and tsc present"               bash -c "command -v node && command -v tsc"
check "pi-ai bridge deployed"              test -r \${ZOMBIE_DIR}/agent/pi-ai-bridge.mjs
check "pi-ai installed (any version)"      bash -c "npm ls -g --depth=0 @earendil-works/pi-ai >/dev/null"
check "pi-ai pinned to \${PI_AI_VERSION}"     bash -c "npm ls -g --depth=0 @earendil-works/pi-ai 2>/dev/null | grep -q '@earendil-works/pi-ai@\${PI_AI_VERSION}'"
check "pi-mono bridge deployed"            test -r \${ZOMBIE_DIR}/agent/pi-mono-bridge.mjs
check "pi-mono installed (any version)"    bash -c "npm ls -g --depth=0 @earendil-works/pi-coding-agent >/dev/null"
check "pi-mono pinned to \${PI_MONO_VERSION}" bash -c "npm ls -g --depth=0 @earendil-works/pi-coding-agent 2>/dev/null | grep -q '@earendil-works/pi-coding-agent@\${PI_MONO_VERSION}'"
check "pi-mono settings rendered"          test -r \${ZOMBIE_DIR}/pi/settings.json
check "pi-mono APPEND_SYSTEM rendered"     test -r \${ZOMBIE_DIR}/pi/APPEND_SYSTEM.md
check "pi-mono log dir present"            test -d \${ZOMBIE_DIR}/state/logs
check "built-in skills directory present"  test -d \${ZOMBIE_DIR}/skills
for skill in ai-agents apt backup certificates containers css database \
             desktop dev disk files git hardware hermes-agent html \
             journal json kernel llm locale network obsidian openclaw-agent \
             packages performance pi-mono-agent process reactivation \
             scheduling secrets security services snap sql systemd \
             troubleshoot ubuntu users virtualization web zombie zram; do
  check "skill \${skill}.md deployed"        test -r \${ZOMBIE_DIR}/skills/\${skill}.md
done
check "operator skills.d/ present"         test -d /etc/ubuntu-zombie/skills.d
check "agent tools.py compiles"            \${AGENT_HOME}/agent-env/bin/python -m py_compile \${ZOMBIE_DIR}/agent/tools.py
check "agent pi_mono.py compiles"          \${AGENT_HOME}/agent-env/bin/python -m py_compile \${ZOMBIE_DIR}/agent/pi_mono.py
check "agent skill_loader.py compiles"     \${AGENT_HOME}/agent-env/bin/python -m py_compile \${ZOMBIE_DIR}/agent/skill_loader.py
[[ "\${JSON}" == "1" ]] || echo

hd "Chat service and policy:"
check "policy.yaml present"                test -r /etc/ubuntu-zombie/policy.yaml
check "audit log writable for ${AGENT_USER}"  bash -c "test -w /var/log/ubuntu-zombie/audit.log || sudo -n test -w /var/log/ubuntu-zombie/audit.log"
check "ubuntu-zombie-chat.service active"  systemctl is-active ubuntu-zombie-chat.service
check "chat listening on 127.0.0.1:${CHAT_PORT}" bash -c "ss -ltn 'sport = :${CHAT_PORT}' | grep -q 127.0.0.1"
check "agent server.py compiles"           \${AGENT_HOME}/agent-env/bin/python -m py_compile \${ZOMBIE_DIR}/agent/server.py
[[ "\${JSON}" == "1" ]] || echo

if [[ "\${JSON}" == "1" ]]; then
  printf '{"tool": "verify", "passed": %d, "failed": %d, "checks": [%s]}\\n' "\$PASS" "\$FAIL" "\${JSON_ITEMS}"
  [[ \$FAIL -gt 0 ]] && exit 1
  exit 0
fi

echo
printf '%sResult:%s %d passed, %d failed.\\n' "\${C_BOLD}" "\${C_RESET}" "\$PASS" "\$FAIL"

if [[ \$FAIL -gt 0 ]]; then
  echo
  echo "Tips:"
  echo "  - If the chat service is not active: sudo systemctl status ubuntu-zombie-chat"
  exit 1
fi
EOF

chmod +x "${ZOMBIE_DIR}/bin/verify"
chown "${AGENT_USER}:${AGENT_USER}" "${ZOMBIE_DIR}/bin/verify"
ln -sf "${ZOMBIE_DIR}/bin/verify" /usr/local/bin/zombie-verify

# ---------------------------------------------------------------------------
# First-run status summary
# ---------------------------------------------------------------------------

section "Verify the installation"

PROVIDER_OK=0
if provider_credential_configured "${ZOMBIE_DIR}/secrets/env"; then
  PROVIDER_OK=1
fi

CHAT_OK=0
if systemctl is-active --quiet ubuntu-zombie-chat.service; then
  CHAT_OK=1
fi

bullet() {
  local ok="$1" label="$2"
  if [[ "${ok}" == "1" ]]; then
    status ok "${label}"
  else
    status warn "${label}"
  fi
}

bullet "${PROVIDER_OK}"  "Provider credential present in secrets/env"
bullet "${CHAT_OK}"      "Chat service running on 127.0.0.1:${CHAT_PORT}"
}

install_zombie() {
  install_zombie_base
  install_zombie_runtime
}

final_zombie_summary() {
  if [[ "${PROVIDER_OK}" != "1" ]]; then
    NEXT_STEP="sudo ${ZOMBIE_DIR}/bin/secrets-edit   # paste a supported provider API key"
  elif [[ "${CHAT_OK}" != "1" ]]; then
    NEXT_STEP="sudo systemctl start ubuntu-zombie-chat.service"
  else
    NEXT_STEP="sudo reboot"
  fi
  printf 'Chat:    http://127.0.0.1:%s/ (localhost only, after reboot)\n' "${CHAT_PORT}"
  printf 'Check:   %s/bin/verify  ·  %s/bin/audit-recent\n' "${ZOMBIE_DIR}" "${ZOMBIE_DIR}"
}

install_zombie
echo

NEXT_STEP=""
INSTALL_DURATION="$(fmt_duration "$(( $(date +%s) - INSTALL_T0 ))")"
printf '\n%s%sInstall complete in %s.%s\n' \
  "${C_GREEN}" "${C_BOLD}" "${INSTALL_DURATION}" "${C_RESET}"
final_zombie_summary
cat <<EOF
Next:    ${C_BOLD}${NEXT_STEP}${C_RESET}
Records: ${LOG_FILE}
         $([[ "${ZOMBIE_RECEIPT}" == "1" ]] && echo "${RECEIPT_FILE}" || echo "receipt disabled")
Remove:  sudo ${SCRIPT_DIR}/uninstall.sh --dry-run
EOF

if [[ "${NEXT_STEP}" != "sudo reboot" ]]; then
  info "Reboot after completing the next step: sudo reboot"
fi

if (( STEPS_SATISFIED + STEPS_CHANGED > 0 )); then
  info "Idempotent steps: ${STEPS_SATISFIED} already satisfied, ${STEPS_CHANGED} applied this run."
fi

write_receipt_finish
