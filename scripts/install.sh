#!/usr/bin/env bash
#
# install.sh
# ----------
# Ubuntu Zombie: baseline installer + chat service.
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

# Ubuntu Zombie chat-UI password gate and Time-to-Live (TTL) kill switch.
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

# ---------------------------------------------------------------------------
# Optional components ("Ubuntu Zombie + Options")
# ---------------------------------------------------------------------------
# Every opt-in component is governed by a ZOMBIE_INSTALL_<COMPONENT> flag
# that defaults to 0, so the baseline install is unchanged unless the
# operator explicitly opts in. Each component follows the same contract:
# validated settings, an entry in the interactive Options menu (item 9 of
# the parameter review), a dry-run stanza, guarded idempotent install
# sections, receipt records, verify/doctor/repair checks, and a reversal
# path in uninstall.sh. Forgejo is the first component; more will follow.
#
# Forgejo: a self-hosted git forge backed by PostgreSQL. Forgejo itself stays
# on loopback; Caddy is the LAN-facing HTTPS endpoint. Optionally a Forgejo
# Actions runner is co-located on the same host using the Docker executor.
ZOMBIE_INSTALL_FORGEJO="${ZOMBIE_INSTALL_FORGEJO:-0}"
ZOMBIE_INSTALL_FORGEJO_RUNNER="${ZOMBIE_INSTALL_FORGEJO_RUNNER:-0}"
ZOMBIE_INSTALL_LLAMA="${ZOMBIE_INSTALL_LLAMA:-0}"
LLAMA_PORT="${LLAMA_PORT:-8080}"
LLAMA_MODEL_ID="${LLAMA_MODEL_ID:-smollm2-360m-instruct-q4_k_m}"
LLAMA_CONTEXT_SIZE="${LLAMA_CONTEXT_SIZE:-2048}"
LLAMA_CPU_THREADS="${LLAMA_CPU_THREADS:-$(nproc 2>/dev/null || echo 1)}"
LLAMA_BOOT="${LLAMA_BOOT:-enabled}"
FORGEJO_HTTP_PORT="${FORGEJO_HTTP_PORT:-3000}"
FORGEJO_ADMIN_USER="${FORGEJO_ADMIN_USER:-forgejo-admin}"
FORGEJO_ADMIN_EMAIL="${FORGEJO_ADMIN_EMAIL:-forgejo-admin@localhost.localdomain}"
FORGEJO_DB_NAME="${FORGEJO_DB_NAME:-forgejo}"
FORGEJO_DB_USER="${FORGEJO_DB_USER:-forgejo}"
# Compatibility password values are converted to root-private temporary files
# for the independent product. Generated values never enter the root receipt.
FORGEJO_ADMIN_PASSWORD="${FORGEJO_ADMIN_PASSWORD:-}"
FORGEJO_DB_PASSWORD="${FORGEJO_DB_PASSWORD:-}"
# Existing Forgejo state is never adopted implicitly. This legacy exact-value
# acknowledgement is mapped to the product's ADOPT FORGEJO confirmation.
FORGEJO_CONFIRM_UPDATE="${FORGEJO_CONFIRM_UPDATE:-}"
# Where each compatibility password came from during parameter review.
FORGEJO_ADMIN_PASSWORD_SOURCE=""
FORGEJO_DB_PASSWORD_SOURCE=""
[[ -n "${FORGEJO_ADMIN_PASSWORD}" ]] && FORGEJO_ADMIN_PASSWORD_SOURCE="operator"
[[ -n "${FORGEJO_DB_PASSWORD}" ]] && FORGEJO_DB_PASSWORD_SOURCE="operator"
FORGEJO_VERSION="${FORGEJO_VERSION:-}"
FORGEJO_RUNNER_VERSION="${FORGEJO_RUNNER_VERSION:-}"
FORGEJO_RUNNER_LABELS="${FORGEJO_RUNNER_LABELS:-ubuntu-latest:docker://node:20-bookworm}"
# Populated at install time once the release tag is resolved.
FORGEJO_RESOLVED_VERSION=""
FORGEJO_RUNNER_RESOLVED_VERSION=""

# True when at least one optional component is enabled — used to keep the
# default dry-run/receipt/banner output byte-for-byte unchanged otherwise.
any_option_enabled() {
  [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" \
    || "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" \
    || "${ZOMBIE_INSTALL_LLAMA}" == "1" ]]
}

# One-line label for where an optional-component password will come from,
# shared by the dry-run stanza, options table, and receipt start record.
password_source_label() {
  case "$1" in
    operator) echo 'set by operator; passed through a private file' ;;
    *) echo 'generated by the product; not recorded in this receipt' ;;
  esac
}

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
LLAMA_PRODUCT_ROOT="${LLAMA_PRODUCT_ROOT:-${REPO_ROOT}/products/llama}"
FORGEJO_PRODUCT_ROOT="${FORGEJO_PRODUCT_ROOT:-${REPO_ROOT}/products/forgejo}"

llama_catalog_release() {
  local catalogue="${LLAMA_PRODUCT_ROOT}/payload/etc/llama-builds.json"
  [[ -r "${catalogue}" ]] || catalogue="/etc/llama.cpp/builds.json"
  [[ -r "${catalogue}" ]] || return 1
  awk -F'"' '/"release":[[:space:]]*"/ {print $4; exit}' \
    "${catalogue}"
}

llama_product_entrypoint() {
  if [[ -x "${LLAMA_PRODUCT_ROOT}/scripts/manage.sh" ]]; then
    printf '%s\n' "${LLAMA_PRODUCT_ROOT}/scripts/manage.sh"
  elif [[ -x /usr/local/sbin/llama-manage ]]; then
    printf '%s\n' /usr/local/sbin/llama-manage
  else
    printf 'Llama product lifecycle is unavailable. Use the independent Llama artifact or a complete source checkout.\n' >&2
    return 66
  fi
}

llama_product_manage() {
  local entrypoint
  entrypoint="$(llama_product_entrypoint)" || return $?
  env \
    LLAMA_MODEL_ID="${LLAMA_MODEL_ID}" \
    LLAMA_CONTEXT_SIZE="${LLAMA_CONTEXT_SIZE}" \
    LLAMA_CPU_THREADS="${LLAMA_CPU_THREADS}" \
    LLAMA_BOOT="${LLAMA_BOOT}" \
    LLAMA_PORT="${LLAMA_PORT}" \
    LLAMA_NONINTERACTIVE="${ZOMBIE_NONINTERACTIVE}" \
    "${entrypoint}" "$@"
}

forgejo_product_entrypoint() {
  if [[ -x "${FORGEJO_PRODUCT_ROOT}/scripts/manage.sh" ]]; then
    printf '%s\n' "${FORGEJO_PRODUCT_ROOT}/scripts/manage.sh"
  elif [[ -x /usr/local/sbin/forgejo-manage ]]; then
    printf '%s\n' /usr/local/sbin/forgejo-manage
  else
    printf 'Forgejo product lifecycle is unavailable. Use the independent Forgejo artifact or a complete source checkout.\n' >&2
    return 66
  fi
}

forgejo_product_manage() {
  local entrypoint admin_secret="" database_secret="" result argument
  local forward_secrets=1
  local -a product_environment=()
  entrypoint="$(forgejo_product_entrypoint)" || return $?
  if (( EUID != 0 )); then
    for argument in "$@"; do
      [[ "${argument}" == "--dry-run" ]] && forward_secrets=0
    done
  fi
  if (( forward_secrets )) && [[ -n "${FORGEJO_ADMIN_PASSWORD}" ]]; then
    admin_secret="$(mktemp)"
    chmod 600 "${admin_secret}"
    printf '%s' "${FORGEJO_ADMIN_PASSWORD}" > "${admin_secret}"
    product_environment+=("FORGEJO_ADMIN_PASSWORD_FILE=${admin_secret}")
  fi
  if (( forward_secrets )) && [[ -n "${FORGEJO_DB_PASSWORD}" ]]; then
    database_secret="$(mktemp)"
    chmod 600 "${database_secret}"
    printf '%s' "${FORGEJO_DB_PASSWORD}" > "${database_secret}"
    product_environment+=("FORGEJO_DB_PASSWORD_FILE=${database_secret}")
  fi
  product_environment+=(
    "FORGEJO_ADMIN_USER=${FORGEJO_ADMIN_USER}"
    "FORGEJO_ADMIN_EMAIL=${FORGEJO_ADMIN_EMAIL}"
    "FORGEJO_DB_NAME=${FORGEJO_DB_NAME}"
    "FORGEJO_DB_USER=${FORGEJO_DB_USER}"
    "FORGEJO_VERSION=${FORGEJO_VERSION}"
    "FORGEJO_HTTP_PORT=${FORGEJO_HTTP_PORT}"
    "FORGEJO_NONINTERACTIVE=${ZOMBIE_NONINTERACTIVE}"
    "FORGEJO_MIGRATION_MANIFEST=/var/lib/ubuntu-zombie/components/forgejo"
  )
  if (
    local variable
    for variable in "${!FORGEJO_@}"; do
      case "${variable}" in
        FORGEJO_ARTIFACT_SHA256|FORGEJO_DISPOSABLE_VM_TEST|FORGEJO_TEST_RELEASE_BASE)
          ;;
        *) unset "${variable}" ;;
      esac
    done
    env "${product_environment[@]}" "${entrypoint}" "$@"
  ); then
    result=0
  else
    result=$?
  fi
  rm -f -- "${admin_secret}" "${database_secret}"
  return "${result}"
}

forgejo_product_value() {
  local key="$1"
  forgejo_product_manage status --json 2>/dev/null \
    | python3 -c \
      'import json,sys; value=json.load(sys.stdin)["details"]["forgejo"]["configuration"].get(sys.argv[1]); print("" if value is None else value)' \
      "${key}"
}

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


# Public component targets accepted after the lifecycle verb. Component
# application logic stays in named hooks; shared infrastructure only walks
# this ordered registry.
readonly COMPONENT_ZOMBIE="zombie"
readonly COMPONENT_FORGEJO="forgejo"
readonly COMPONENT_FORGEJO_RUNNER="forgejo-runner"
readonly COMPONENT_LLAMA="llama"
readonly COMPONENT_MANIFEST_FORMAT_VERSION="1"
COMPONENT_MANIFEST_DIR="${ZOMBIE_COMPONENT_MANIFEST_DIR:-/var/lib/ubuntu-zombie/components}"
TARGET_ARGS=()
SELECTED_COMPONENTS=()
EXPLICIT_TARGETS=0

# shellcheck source=scripts/component-registry.sh
. "${SCRIPT_DIR}/component-registry.sh"

component_validate_zombie() { validate_zombie_config; }
component_validate_forgejo() {
  local validation
  validate_forgejo_config
  if ! validation="$(forgejo_product_manage install --dry-run --json 2>&1)"; then
    die "Forgejo product configuration validation failed: ${validation}" 2
  fi
}
component_validate_forgejo_runner() { validate_forgejo_runner_config; }
component_validate_llama() {
  local validation
  if ! validation="$(llama_product_manage install --dry-run --json 2>&1)"; then
    die "Llama product configuration validation failed: ${validation}" 2
  fi
}
component_review_zombie() { review_parameters; }
component_review_forgejo() { review_forgejo_parameters; }
component_review_forgejo_runner() { review_forgejo_runner_parameters; }
component_review_llama() { :; }
component_dry_run_zombie() { print_zombie_dry_run; }
component_dry_run_forgejo() { forgejo_product_manage install --dry-run; }
component_dry_run_forgejo_runner() { print_forgejo_runner_dry_run; }
component_dry_run_llama() { llama_product_manage install --dry-run; }
component_receipt_start_zombie() { receipt_start_zombie; }
component_receipt_start_forgejo() { receipt_start_forgejo; }
component_receipt_start_forgejo_runner() { receipt_start_forgejo_runner; }
component_receipt_start_llama() { receipt_start_llama; }
component_receipt_finish_zombie() { receipt_finish_zombie; }
component_receipt_finish_forgejo() { receipt_finish_forgejo; }
component_receipt_finish_forgejo_runner() { receipt_finish_forgejo_runner; }
component_receipt_finish_llama() { receipt_finish_llama; }
component_install_zombie() { install_zombie; }
component_install_forgejo() {
  local -a arguments=(install --yes --confirmation "ADOPT FORGEJO")
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && arguments+=(--non-interactive)
  forgejo_product_manage "${arguments[@]}"
  FORGEJO_RESOLVED_VERSION="$(forgejo_product_value upstream_version)"
  FORGEJO_URL_HOST="$(forgejo_product_value host)"
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
      && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}"; then
    install_forgejo_runner
  fi
}
component_install_forgejo_runner() { install_forgejo_runner; }
component_install_llama() {
  local -a arguments=(install --yes)
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && arguments+=(--non-interactive)
  llama_product_manage "${arguments[@]}"
}
component_manifest_zombie() { write_zombie_manifest; }
component_manifest_forgejo() { write_forgejo_manifest; }
component_manifest_forgejo_runner() { write_forgejo_runner_manifest; }
component_manifest_llama() { write_llama_manifest; }
component_final_zombie() { final_zombie_summary; }
component_final_forgejo() { final_forgejo_summary; }
component_final_forgejo_runner() { final_forgejo_runner_summary; }
component_final_llama() { final_llama_summary; }
component_legacy_zombie() { legacy_zombie_present; }
component_legacy_forgejo() { legacy_forgejo_present; }
component_legacy_forgejo_runner() { legacy_forgejo_runner_present; }
component_legacy_llama() { legacy_llama_present; }
component_verify_zombie() { verify_zombie; }
component_verify_forgejo() {
  if forgejo_product_manage verify --json >/dev/null 2>&1; then
    vr ok forgejo delegated "Independent Forgejo product verification passed."
  else
    vr fail forgejo delegated \
      "Independent Forgejo verification failed. Run: sudo forgejo-manage verify"
  fi
}
component_verify_forgejo_runner() { verify_forgejo_runner; }
component_verify_llama() {
  if llama_product_manage verify --json >/dev/null 2>&1; then
    vr ok llama delegated "Independent Llama product verification passed."
  else
    vr fail llama delegated \
      "Independent Llama verification failed. Run: sudo llama-manage verify"
  fi
}
component_doctor_zombie() { doctor_zombie; }
component_doctor_forgejo() {
  local response
  if response="$(forgejo_product_manage doctor --json 2>/dev/null)" \
      && python3 -c \
        'import json,sys; raise SystemExit(json.load(sys.stdin)["status"] != "ok")' \
        <<<"${response}"; then
    dr ok forgejo delegated "Independent Forgejo product reports healthy."
  else
    dr warn forgejo delegated \
      "Independent Forgejo product reports drift. Run: forgejo-manage doctor"
  fi
}
component_doctor_forgejo_runner() { doctor_forgejo_runner; }
component_doctor_llama() {
  local response
  if response="$(llama_product_manage doctor --json 2>/dev/null)" \
      && python3 -c \
        'import json,sys; raise SystemExit(json.load(sys.stdin)["status"] != "ok")' \
        <<<"${response}"; then
    dr ok llama delegated "Independent Llama product reports healthy."
  else
    dr warn llama delegated \
      "Independent Llama product reports drift. Run: llama-manage doctor"
  fi
}
component_repair_zombie() { repair_zombie; }
component_repair_forgejo() {
  if [[ -f /var/lib/forgejo/installation.json ]]; then
    forgejo_product_manage repair --yes --non-interactive
  else
    forgejo_product_manage install --yes --non-interactive \
      --confirmation "ADOPT FORGEJO"
  fi
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
      && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}"; then
    repair_forgejo_runner
  fi
}
component_repair_forgejo_runner() { repair_forgejo_runner; }
component_repair_llama() {
  llama_product_manage repair --yes --non-interactive
}
component_phase_count_zombie() { count_zombie_phases; }
component_phase_count_forgejo() { printf '1\n'; }
component_phase_count_forgejo_runner() { count_forgejo_runner_phases; }
component_phase_count_llama() { printf '1\n'; }

register_component "${COMPONENT_ZOMBIE}" "" \
  validate=component_validate_zombie review=component_review_zombie \
  dry_run=component_dry_run_zombie receipt_start=component_receipt_start_zombie \
  receipt_finish=component_receipt_finish_zombie install=component_install_zombie \
  manifest=component_manifest_zombie final=component_final_zombie \
  legacy=component_legacy_zombie verify=component_verify_zombie \
  doctor=component_doctor_zombie repair=component_repair_zombie \
  phase_count=component_phase_count_zombie
register_component "${COMPONENT_FORGEJO}" "" \
  validate=component_validate_forgejo review=component_review_forgejo \
  dry_run=component_dry_run_forgejo receipt_start=component_receipt_start_forgejo \
  receipt_finish=component_receipt_finish_forgejo install=component_install_forgejo \
  manifest=component_manifest_forgejo final=component_final_forgejo \
  legacy=component_legacy_forgejo verify=component_verify_forgejo \
  doctor=component_doctor_forgejo repair=component_repair_forgejo \
  phase_count=component_phase_count_forgejo
register_component "${COMPONENT_FORGEJO_RUNNER}" "${COMPONENT_FORGEJO}" \
  validate=component_validate_forgejo_runner review=component_review_forgejo_runner \
  dry_run=component_dry_run_forgejo_runner \
  receipt_start=component_receipt_start_forgejo_runner \
  receipt_finish=component_receipt_finish_forgejo_runner \
  install=component_install_forgejo_runner \
  manifest=component_manifest_forgejo_runner final=component_final_forgejo_runner \
  legacy=component_legacy_forgejo_runner verify=component_verify_forgejo_runner \
  doctor=component_doctor_forgejo_runner repair=component_repair_forgejo_runner \
  phase_count=component_phase_count_forgejo_runner
register_component "${COMPONENT_LLAMA}" "" \
  validate=component_validate_llama review=component_review_llama \
  dry_run=component_dry_run_llama receipt_start=component_receipt_start_llama \
  receipt_finish=component_receipt_finish_llama install=component_install_llama \
  manifest=component_manifest_llama final=component_final_llama \
  legacy=component_legacy_llama verify=component_verify_llama \
  doctor=component_doctor_llama repair=component_repair_llama \
  phase_count=component_phase_count_llama

component_names() {
  printf '%s' "${PUBLIC_COMPONENTS[*]}"
}

is_lifecycle_verb() {
  case "$1" in
    install|verify|doctor|repair|uninstall) return 0 ;;
    *) return 1 ;;
  esac
}

is_public_component() {
  local candidate="$1" component
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    [[ "${candidate}" == "${component}" ]] && return 0
  done
  return 1
}

is_selected_component() {
  local candidate="$1" component
  for component in "${SELECTED_COMPONENTS[@]}"; do
    [[ "${candidate}" == "${component}" ]] && return 0
  done
  return 1
}

add_selected_component() {
  local component="$1"
  is_selected_component "${component}" || SELECTED_COMPONENTS+=("${component}")
}


component_manifest_path() {
  local component="$1"
  is_public_component "${component}" || die "Unknown or invalid component name: ${component}. Valid components: $(component_names)" 2
  printf '%s/%s' "${COMPONENT_MANIFEST_DIR}" "${component}"
}

validate_component_manifest_dir() {
  is_safe_absolute_path "${COMPONENT_MANIFEST_DIR}" \
    || die "ZOMBIE_COMPONENT_MANIFEST_DIR must be an absolute safe path." 2
}

ensure_component_manifest_dir() {
  validate_component_manifest_dir
  (( DRY_RUN )) && return 0
  install -d -m 755 -o root -g root "${COMPONENT_MANIFEST_DIR}"
}

write_component_manifest() {
  local component="$1" component_version="${2:-}" suboptions="${3:-}"
  local path tmp
  is_public_component "${component}" || die "Unknown manifest component: ${component}" 2
  ensure_component_manifest_dir
  (( DRY_RUN )) && return 0
  path="$(component_manifest_path "${component}")"
  tmp="${path}.tmp.$$"
  {
    printf 'format=%s\n' "${COMPONENT_MANIFEST_FORMAT_VERSION}"
    printf 'component=%s\n' "${component}"
    printf 'ubuntu_zombie_version=%s\n' "${SCRIPT_VERSION}"
    printf 'converged_utc=%s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'component_version=%s\n' "${component_version}"
    printf 'suboptions=%s\n' "${suboptions}"
  } > "${tmp}"
  chown root:root "${tmp}" 2>/dev/null || true
  chmod 644 "${tmp}"
  mv -f "${tmp}" "${path}"
}

remove_component_manifest() {
  local component="$1" path manifest_parent_dir
  path="$(component_manifest_path "${component}")"
  manifest_parent_dir="$(dirname "${COMPONENT_MANIFEST_DIR}")"
  (( DRY_RUN )) && return 0
  rm -f -- "${path}"
  rmdir --ignore-fail-on-non-empty "${COMPONENT_MANIFEST_DIR}" 2>/dev/null || true
  rmdir --ignore-fail-on-non-empty "${manifest_parent_dir}" 2>/dev/null || true
}

_read_manifest_value() {
  local file="$1" key="$2"
  # Match lines starting with `key=`, return everything after the first
  # equals sign, and exit 1 if the key is absent.
  awk -v want="${key}" '
    index($0, want "=") == 1 {
      print substr($0, length(want) + 2)
      found = 1
    }
    END { if (!found) exit 1 }
  ' "${file}" 2>/dev/null
}

valid_component_manifest_entry() {
  local file="$1" component="$2"
  local -A seen=()
  local key value line
  [[ -f "${file}" ]] || return 1
  while IFS= read -r line; do
    # Skip blank lines
    [[ -n "${line}" ]] || continue
    # A valid line must contain '=' and have a non-empty key before it.
    # Lines without '=' (key == whole line) are malformed.
    key="${line%%=*}"
    value="${line#*=}"
    [[ -n "${key}" && "${key}" != "${line}" ]] || return 1
    # Keys must use only lowercase letters and underscores.
    [[ "${key}" =~ ^[a-z_]+$ ]] || return 1
    # Values must not contain carriage returns (guard against CRLF files).
    # Null bytes cannot be stored in bash variables; skip that check.
    [[ "${value}" =~ $'\r' ]] && return 1
    case "${key}" in
      format|component|ubuntu_zombie_version|converged_utc|component_version|suboptions)
        # Reject any duplicate key.
        [[ -n "${seen[${key}]+x}" ]] && return 1
        seen["${key}"]=1
        ;;
      *) return 1 ;;
    esac
  done < "${file}"
  # Require exactly one occurrence of every one of the six defined keys.
  for key in format component ubuntu_zombie_version converged_utc component_version suboptions; do
    [[ -n "${seen[${key}]+x}" ]] || return 1
  done
  # Validate format version, component name, and component/path match.
  [[ "$(_read_manifest_value "${file}" format)" == "${COMPONENT_MANIFEST_FORMAT_VERSION}" ]] || return 1
  local file_component
  file_component="$(_read_manifest_value "${file}" component)"
  [[ "${file_component}" == "${component}" ]] || return 1
  # Ensure the stored component name is itself a known safe value so a
  # crafted manifest cannot inject an arbitrary string into the component
  # path even if component_manifest_path is called again later.
  is_public_component "${file_component}" || return 1
  return 0
}

list_manifest_components() {
  local component path
  validate_component_manifest_dir
  [[ -d "${COMPONENT_MANIFEST_DIR}" ]] || return 0
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    path="$(component_manifest_path "${component}")"
    if [[ -e "${path}" ]]; then
      if valid_component_manifest_entry "${path}" "${component}"; then
        printf '%s\n' "${component}"
      else
        warn "Ignoring malformed component manifest: ${path}"
      fi
    fi
  done
  shopt -s nullglob
  for path in "${COMPONENT_MANIFEST_DIR}"/*; do
    component="$(basename -- "${path}")"
    is_public_component "${component}" || warn "Ignoring unknown component manifest: ${path}"
  done
  shopt -u nullglob
}

legacy_zombie_present() {
  [[ -d "${ZOMBIE_DIR}" || -f "/etc/systemd/system/ubuntu-zombie-chat.service" || -d "${ZOMBIE_ETC}" ]]
}

legacy_forgejo_present() {
  [[ -f /etc/systemd/system/forgejo.service || -d /etc/forgejo \
    || -x /usr/local/bin/forgejo \
    || -f /etc/systemd/system/forgejo-runner.service \
    || -x /usr/local/bin/forgejo-runner \
    || -d /var/lib/forgejo || -d /var/lib/forgejo-runner \
    || -f "${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO}" ]]
}

legacy_forgejo_runner_present() {
  [[ -f /etc/systemd/system/forgejo-runner.service \
    || -x /usr/local/bin/forgejo-runner \
    || -d /var/lib/forgejo-runner \
    || -f "${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO_RUNNER}" ]]
}

llama_installation_is_managed() {
  local marker
  if [[ -e /var/lib/llama.cpp/installation.json ]] \
      && llama_product_manage verify --json >/dev/null 2>&1; then
    return 0
  fi
  for marker in /etc/llama.cpp/managed-by-ubuntu-zombie \
      /var/lib/llama.cpp/managed-by-ubuntu-zombie; do
    valid_component_ownership_marker "${marker}" "${COMPONENT_LLAMA}" && return 0
  done
  return 1
}

legacy_llama_present() {
  llama_installation_is_managed
}

resolve_lifecycle_targets_from_manifest() {
  local component found="${#SELECTED_COMPONENTS[@]}"
  (( EXPLICIT_TARGETS )) && return 0
  [[ "${SUBCOMMAND}" == "verify" || "${SUBCOMMAND}" == "doctor" || "${SUBCOMMAND}" == "repair" ]] || return 0
  while IFS= read -r component; do
    [[ -n "${component}" ]] || continue
    add_selected_component "${component}"
    found=1
  done < <(list_manifest_components)
  if (( ! found )); then
    for component in "${PUBLIC_COMPONENTS[@]}"; do
      if component_dispatch_hook "${component}" legacy; then
        add_selected_component "${component}"
      fi
    done
  fi
}

component_selected_for_lifecycle() {
  is_selected_component "$1"
}

validate_and_resolve_targets() {
  local target component
  declare -A seen_targets=()
  for target in "${TARGET_ARGS[@]}"; do
    if is_lifecycle_verb "${target}"; then
      die "Lifecycle verb cannot be used as a component target after ${SUBCOMMAND}: ${target}" 2
    fi
    if ! is_public_component "${target}"; then
      die "Unknown component target '${target}'. Valid components: $(component_names)" 2
    fi
    if [[ -n "${seen_targets[${target}]+x}" ]]; then
      die "Duplicate component target '${target}'." 2
    fi
    seen_targets["${target}"]=1
    SELECTED_COMPONENTS+=("${target}")
  done

  (( ${#TARGET_ARGS[@]} > 0 )) && EXPLICIT_TARGETS=1

  if (( ! EXPLICIT_TARGETS )) && [[ "${SUBCOMMAND}" == "install" ]]; then
    add_selected_component "${COMPONENT_ZOMBIE}"
  fi

  if forgejo_config_selected; then
    add_selected_component "${COMPONENT_FORGEJO}"
  fi
  if forgejo_runner_config_selected; then
    add_selected_component "${COMPONENT_FORGEJO_RUNNER}"
  fi
  if llama_config_selected; then
    add_selected_component "${COMPONENT_LLAMA}"
  fi

  # Installing a component also installs its registered dependencies.
  # verify/doctor/repair/uninstall keep operating on the explicit targets
  # only, matching the documented selection rules.
  if [[ "${SUBCOMMAND}" == "install" ]] && (( ${#SELECTED_COMPONENTS[@]} > 0 )); then
    local -a resolved_targets=()
    while IFS= read -r component; do
      [[ -n "${component}" ]] && resolved_targets+=("${component}")
    done < <(resolve_component_targets "${SELECTED_COMPONENTS[@]}")
    SELECTED_COMPONENTS=("${resolved_targets[@]}")
  fi

  # Execution order follows the registry, not the order targets were typed.
  # This also makes legacy flags equivalent to explicit component selection.
  declare -A requested_components=()
  for target in "${SELECTED_COMPONENTS[@]}"; do
    requested_components["${target}"]=1
  done
  SELECTED_COMPONENTS=()
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    [[ -n "${requested_components[${component}]+x}" ]] \
      && SELECTED_COMPONENTS+=("${component}")
  done

  # Compatibility mapping only: explicit registry selection keeps the legacy
  # environment selectors coherent for component-owned code.
  is_selected_component "${COMPONENT_FORGEJO}" && ZOMBIE_INSTALL_FORGEJO=1
  is_selected_component "${COMPONENT_FORGEJO_RUNNER}" \
    && ZOMBIE_INSTALL_FORGEJO_RUNNER=1
  is_selected_component "${COMPONENT_LLAMA}" && ZOMBIE_INSTALL_LLAMA=1
  return 0
}

zombie_config_selected() {
  is_selected_component "${COMPONENT_ZOMBIE}" && return 0
  (( EXPLICIT_TARGETS )) && return 1
  # This is validation fallback only. Target selection for install happens in
  # validate_and_resolve_targets(); no-target non-install verbs keep the legacy
  # zombie-centric validation path until the component manifest lands. No-target
  # uninstall delegates to uninstall.sh.
  [[ "${SUBCOMMAND}" != "uninstall" ]]
}

forgejo_config_selected() {
  is_selected_component "${COMPONENT_FORGEJO}" && return 0
  [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]]
}

forgejo_runner_config_selected() {
  is_selected_component "${COMPONENT_FORGEJO_RUNNER}" && return 0
  [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]]
}

llama_config_selected() {
  is_selected_component "${COMPONENT_LLAMA}" && return 0
  [[ "${ZOMBIE_INSTALL_LLAMA}" == "1" ]]
}

selected_components_label() {
  if (( ${#SELECTED_COMPONENTS[@]} == 0 )); then
    case "${SUBCOMMAND}" in
      uninstall) printf 'all managed artefacts (compatibility mode)' ;;
      *) printf 'installed components (manifest discovery pending)' ;;
    esac
  else
    printf '%s' "${SELECTED_COMPONENTS[*]}"
  fi
}

# ---------------------------------------------------------------------------
# Argument parsing
# ---------------------------------------------------------------------------

usage() {
  cat <<EOF
${SCRIPT_NAME} ${SCRIPT_VERSION}

Ubuntu Zombie baseline installer + AI Systems Administrator chat service.

Usage:
  sudo ./${SCRIPT_NAME} [VERB] [COMPONENT ...] [FLAGS]

Verbs:
  install     Full install (default). With no component target, installs the
              zombie baseline. Interactive runs open an editable parameter
              review before any change is made.
  verify      Read-only state check. Does not change state.
  doctor      Explain failures and likely fixes.
  repair      Apply known-safe fixes (re-assert permissions, restart
              the chat service).
  uninstall   Reverse the install (delegates to uninstall.sh). With no target,
              keeps the current all-managed-artefacts behaviour.

Components:
  zombie      The Ubuntu Zombie account, runtime, chat UI, policy, and services.
  forgejo     Forgejo + PostgreSQL, independently installable without zombie.
  forgejo-runner
              Forgejo Actions runner for an existing local Forgejo installation.
  llama       PC-wide llama.cpp server on 127.0.0.1:8080, independent of zombie.

Selection rules:
  install with no component target selects zombie. Explicit targets select
  exactly those components, plus any enabled legacy ZOMBIE_INSTALL_* options.
  verify/doctor/repair targets are accepted now; no-target discovery falls back
  to current legacy checks until the component manifest lands.

Flags:
  Behaviour
    -n, --dry-run     Print the plan without touching the host.
                      Meaningful with 'install' and 'uninstall'.
    -y, --yes         Skip the "Type YES" confirmation. Still prompts for
                      any missing inputs (use ZOMBIE_NONINTERACTIVE=1 to
                      skip every prompt for fully unattended installs).
        --strict      Treat preflight warnings as fatal.
  Uninstall only
        --archive     Archive /opt/ai-zombie before removing it.
        --keep-agent  Do not remove the agent user account.
  Output
    -q, --quiet       Only show warnings and errors.
        --verbose,
        --debug       Write shell xtrace to the transcript for debugging.
        --no-color    Disable ANSI colour (NO_COLOR is also honoured).
        --json        Machine-readable JSON output (verify, doctor only).
  Other
    -h, --help        Show this help and exit.
    -v, --version     Print the version and exit.

Environment variables (selected; see docs/CONFIGURATION.md for all):
  ZOMBIE_NONINTERACTIVE=1     skip prompts for fully unattended installs.
  ZOMBIE_USER=<name>          name of the local agent account (default
                              'zombie'). Must be set on every later
                              install/verify/doctor/repair/uninstall
                              run that targets a non-default account.
  ZOMBIE_COLOR=auto|always|never   colour policy (default auto). The setup
                              UI uses the Zombie Orchid highlight (#AC43D9)
                              and compatible accents when colour is enabled.
  ZOMBIE_RECEIPT=0            disable the start/finish install receipt
                              (written by default).
  ZOMBIE_RECEIPT_FILE=<path>  override the receipt path (default
                              /var/log/ubuntu-zombie/install-receipt.txt).
  ZOMBIE_SKIP_LLM_SCAN=1     skip the interactive LAN scan that looks for an
                              OpenAI-compatible local LLM server and offers
                              its models as the starting model. The scan is
                              also skipped when a model is already configured.
  ZOMBIE_LLM_SCAN_PORT=<n>    port probed for the local LLM scan (default
                              1234, LM Studio's default).
  ZOMBIE_LOCAL_LLM_API_KEY=<k>  API key recorded for the discovered local LLM
                              (default 'local'; most local servers ignore it).
  ZOMBIE_ADMIN_PASSWORD       Chat-UI password gate (default 'braaaains';
                              only a hash is stored).
  ZOMBIE_TTL_DAYS=<n>         Time to Live in days before the zombie is
                              permanently disabled (default 7).

Optional components (all default 0 / off; see options/ for the roadmap):
  ZOMBIE_INSTALL_LLAMA=1      also install the standalone llama component.
  LLAMA_MODEL_ID=<id>         approved model (default
                              smollm2-360m-instruct-q4_k_m).
  LLAMA_CONTEXT_SIZE=<n>      context tokens (default 2048).
  LLAMA_CPU_THREADS=<n>       CPU inference threads (default: detected CPUs).
  LLAMA_BOOT=enabled|disabled start the server at boot (default enabled).
  ZOMBIE_INSTALL_FORGEJO=1    also install a self-hosted Forgejo git forge
                              backed by PostgreSQL, reachable over LAN HTTPS
                              through Caddy and mDNS/Avahi.
  ZOMBIE_INSTALL_FORGEJO_RUNNER=1  also install a Forgejo Actions runner on
                              the same host (restricted Docker executor).
                              Requires ZOMBIE_INSTALL_FORGEJO=1.
  FORGEJO_HTTP_PORT=3000      Forgejo loopback backend port (fixed at 3000).
  FORGEJO_ADMIN_USER=<name>   initial admin account (default forgejo-admin).
  FORGEJO_ADMIN_EMAIL=<addr>  admin email (default forgejo-admin@localhost.localdomain).
  FORGEJO_ADMIN_PASSWORD=<p>  initial admin password (default: generated into
                              /etc/forgejo/bootstrap-admin-password).
  FORGEJO_DB_NAME=<name>      PostgreSQL database (default forgejo).
  FORGEJO_DB_USER=<name>      PostgreSQL role (default forgejo).
  FORGEJO_DB_PASSWORD=<p>     PostgreSQL role password (default: generated and
                              retained only in root-protected app.ini).
  FORGEJO_VERSION=<x.y.z>     pin the Forgejo release (default: latest).
  FORGEJO_RUNNER_VERSION=<x.y.z>  pin the runner release (default: latest).
  FORGEJO_RUNNER_LABELS=<labels>  runner labels (default
                              ubuntu-latest:docker://node:20-bookworm).

Examples:
  # Preview the plan before granting anything:
  sudo ./${SCRIPT_NAME} install --dry-run

  # Minimal interactive install:
  sudo ./${SCRIPT_NAME} install

  # Attended, but skip the YES gate:
  sudo ./${SCRIPT_NAME} install --yes

  # Fully unattended (CI / cloud-init):
  sudo ZOMBIE_NONINTERACTIVE=1 ./${SCRIPT_NAME} install

  # Canonical component form for the baseline:
  sudo ./${SCRIPT_NAME} install zombie

  # Baseline plus a Forgejo forge with a co-located Actions runner
  # (environment flags remain supported for automation):
  sudo ZOMBIE_INSTALL_FORGEJO=1 ZOMBIE_INSTALL_FORGEJO_RUNNER=1 \\
    ./${SCRIPT_NAME} install

  # Equivalent component-target preview for the combined install:
  sudo ./${SCRIPT_NAME} install zombie forgejo --dry-run

  # Install Forgejo + PostgreSQL without the zombie account/runtime:
  sudo ./${SCRIPT_NAME} install forgejo

  # Install a standalone local llama.cpp service without zombie:
  sudo ./${SCRIPT_NAME} install llama

  # Machine-readable health for monitoring:
  ./${SCRIPT_NAME} verify --json

Shell completion:
  Bash:  source scripts/completions/install.bash
  Zsh:   add scripts/completions/ to \$fpath, then: autoload -U compinit && compinit

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
    --) shift; TARGET_ARGS+=("$@"); break ;;
    -*) die "Unknown flag: $1 (try --help)" 2 ;;
    *)  TARGET_ARGS+=("$1"); shift ;;
  esac
done
readonly DRY_RUN
validate_and_resolve_targets

if [[ "${SUBCOMMAND}" == "install" ]] && ! (( ZOMBIE_QUIET )); then
  brand_splash "install" "${SCRIPT_VERSION}"
fi

# ---------------------------------------------------------------------------
# Helpers shared across subcommands
# ---------------------------------------------------------------------------

require_root() {
  [[ ${EUID} -eq 0 ]] || die "Run with sudo: sudo ./${SCRIPT_NAME} ${SUBCOMMAND}" 2
}

# Existing service and database state needs a stronger acknowledgement than
# the general install confirmation. Only an exact, capitalized YES is accepted;
# --yes deliberately does not bypass this gate.
require_capitalized_yes() {
  local variable="$1" prompt="$2" answer="${!1:-}"
  if [[ "${answer}" == "YES" ]]; then
    info "${variable}=YES: ${prompt}"
    return 0
  fi
  if [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] || (( ASSUME_YES )) || [[ ! -t 0 ]]; then
    die "${prompt} Set ${variable}=YES (capitalized exactly) to continue." 64
  fi
  if ! read -r -p "${prompt} Type YES to continue: " answer; then
    info "No input (EOF); cancelled."
    exit 0
  fi
  [[ "${answer}" == "YES" ]] || { info "Cancelled; existing data was left unchanged."; exit 0; }
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

# A Forgejo account / database identifier: conservative because the value
# is interpolated into psql statements and CLI invocations. 1-40 chars,
# starts with a letter, ends alphanumeric, underscore/hyphen in the middle.
is_valid_forgejo_name() {
  [[ "$1" =~ ^[a-z]([a-z0-9_-]{0,38}[a-z0-9])?$ ]]
}

# A plausible email for the Forgejo admin account (conservative subset).
is_valid_forgejo_email() {
  [[ "$1" =~ ^[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+$ ]]
}

# An optional Forgejo release pin like "11.0.3" (empty means "latest").
is_valid_forgejo_version() {
  [[ -z "$1" || "$1" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.]+)?$ ]]
}

# Runner labels like "ubuntu-latest:docker://node:20-bookworm". Conservative
# because the value is interpolated into the runner-registration command:
# no whitespace, quotes, or shell metacharacters.
is_valid_forgejo_runner_labels() {
  # BSD regcomp (used by macOS bash) rejects bounded repetitions above
  # 255, so enforce the length separately and keep the regex simple.
  (( ${#1} >= 1 && ${#1} <= 512 )) || return 1
  [[ "$1" =~ ^[A-Za-z0-9._:/,+-]+$ ]]
}

# An optional operator-supplied password (empty means "generate randomly").
# Conservative because the value is interpolated into psql literals, app.ini
# lines, and CLI arguments: 8-256 printable characters, no control characters
# or newlines.
is_valid_forgejo_password() {
  [[ -z "$1" ]] && return 0
  (( ${#1} >= 8 && ${#1} <= 256 )) || return 1
  [[ "$1" =~ ^[[:print:]]+$ ]]
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

validate_forgejo_config() {
  if ! is_valid_option_flag "${ZOMBIE_INSTALL_FORGEJO_RUNNER}"; then
    die "ZOMBIE_INSTALL_FORGEJO_RUNNER must be 0 or 1." 2
  fi
  if ! is_valid_tcp_port "${FORGEJO_HTTP_PORT}"; then
    die "FORGEJO_HTTP_PORT must be an integer from 1 to 65535." 2
  fi
  if ! is_valid_forgejo_name "${FORGEJO_ADMIN_USER}"; then
    die "FORGEJO_ADMIN_USER must be a lowercase identifier (letters first; then letters, digits, underscore, hyphen; max 40 chars)." 2
  fi
  if ! is_valid_forgejo_email "${FORGEJO_ADMIN_EMAIL}"; then
    die "FORGEJO_ADMIN_EMAIL must look like an email address." 2
  fi
  if ! is_valid_forgejo_name "${FORGEJO_DB_NAME}"; then
    die "FORGEJO_DB_NAME must be a lowercase identifier (letters first; then letters, digits, underscore, hyphen; max 40 chars)." 2
  fi
  if ! is_valid_forgejo_name "${FORGEJO_DB_USER}"; then
    die "FORGEJO_DB_USER must be a lowercase identifier (letters first; then letters, digits, underscore, hyphen; max 40 chars)." 2
  fi
  if ! is_valid_forgejo_password "${FORGEJO_ADMIN_PASSWORD}"; then
    die "FORGEJO_ADMIN_PASSWORD must be 8-256 printable characters (or empty to auto-generate)." 2
  fi
  if ! is_valid_forgejo_password "${FORGEJO_DB_PASSWORD}"; then
    die "FORGEJO_DB_PASSWORD must be 8-256 printable characters (or empty to auto-generate)." 2
  fi
  if ! is_valid_forgejo_version "${FORGEJO_VERSION}"; then
    die "FORGEJO_VERSION must be a release like 11.0.3 (or empty for latest)." 2
  fi
  if ! is_valid_forgejo_version "${FORGEJO_RUNNER_VERSION}"; then
    die "FORGEJO_RUNNER_VERSION must be a release like 6.3.1 (or empty for latest)." 2
  fi
  if ! is_valid_forgejo_runner_labels "${FORGEJO_RUNNER_LABELS}"; then
    die "FORGEJO_RUNNER_LABELS must use only letters, digits, and . _ : / , + - (no spaces or quotes; max 512 chars)." 2
  fi
}

validate_forgejo_runner_config() {
  if ! is_valid_option_flag "${ZOMBIE_INSTALL_FORGEJO_RUNNER}"; then
    die "ZOMBIE_INSTALL_FORGEJO_RUNNER must be 0 or 1." 2
  fi
  if ! is_valid_forgejo_version "${FORGEJO_RUNNER_VERSION}"; then
    die "FORGEJO_RUNNER_VERSION must be a release like 6.3.1 (or empty for latest)." 2
  fi
  if ! is_valid_forgejo_runner_labels "${FORGEJO_RUNNER_LABELS}"; then
    die "FORGEJO_RUNNER_LABELS must use only letters, digits, and . _ : / , + - (no spaces or quotes; max 512 chars)." 2
  fi
}

# Validate common settings, then dispatch only the selected components.
validate_config() {
  if ! is_safe_absolute_path "${LOG_FILE}"; then
    die "LOG_FILE must be an absolute path using only letters, digits, dot, underscore, slash, plus, colon, and hyphen." 2
  fi
  # Receipt is a core setting and is validated for every selected component,
  # even when Forgejo credentials make it mandatory rather than optional.
  if ! is_valid_option_flag "${ZOMBIE_RECEIPT}"; then
    die "ZOMBIE_RECEIPT must be 0 or 1." 2
  fi
  if [[ "${ZOMBIE_RECEIPT}" == "1" ]] && ! is_safe_absolute_path "${RECEIPT_FILE}"; then
    die "ZOMBIE_RECEIPT_FILE must be an absolute path using only letters, digits, dot, underscore, slash, plus, colon, and hyphen." 2
  fi
  validate_component_manifest_dir
  local component
  local -a validation_components=("${SELECTED_COMPONENTS[@]}")
  if ! is_valid_option_flag "${ZOMBIE_INSTALL_FORGEJO}"; then
    die "ZOMBIE_INSTALL_FORGEJO must be 0 or 1." 2
  fi
  if ! is_valid_option_flag "${ZOMBIE_INSTALL_LLAMA}"; then
    die "ZOMBIE_INSTALL_LLAMA must be 0 or 1." 2
  fi
  if (( ${#validation_components[@]} == 0 )) && [[ "${SUBCOMMAND}" != "uninstall" ]]; then
    validation_components=("${PUBLIC_COMPONENTS[0]}")
  fi
  for component in "${validation_components[@]}"; do
    component_dispatch_hook "${component}" validate
  done
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
  local errors=0 warnings=0 required_disk_kb=1000000 required_disk_label="1 GB"
  local memory_context="selected services"
  if is_selected_component "${COMPONENT_ZOMBIE}"; then
    required_disk_kb=3000000
    required_disk_label="3 GB"
    memory_context="agent runtime"
  fi
  if is_selected_component "${COMPONENT_ZOMBIE}" \
      && is_selected_component "${COMPONENT_FORGEJO}"; then
    required_disk_kb=4000000
    required_disk_label="4 GB"
  fi

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

  # Disk capacity follows the selected components. The zombie runtime and its
  # Node/Python toolchain need more room than standalone Forgejo.
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
# Validate non-interactive required env early.
# ---------------------------------------------------------------------------

validate_noninteractive() {
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] || return 0
}

forgejo_runner_config_is_managed() {
  local host
  [[ -r "${PAYLOAD_DIR}/etc/forgejo-runner-config.yaml" \
      && -r /var/lib/forgejo-runner/config.yaml ]] || return 1
  host="$(forgejo_runner_public_host)" || return 1
  cmp -s \
    <(sed "s|__FORGEJO_HOST__|${host}|g" \
      "${PAYLOAD_DIR}/etc/forgejo-runner-config.yaml") \
    /var/lib/forgejo-runner/config.yaml
}

forgejo_runner_public_host() {
  local host=""
  host="$(forgejo_product_value host 2>/dev/null || true)"
  [[ "${host}" =~ ^[a-z0-9]([a-z0-9.-]{0,251}[a-z0-9])?$ ]] \
    || return 1
  printf '%s\n' "${host}"
}

forgejo_manifest_has_runner() {
  local manifest="${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO}"
  valid_component_manifest_entry "${manifest}" "${COMPONENT_FORGEJO}" \
    && [[ "$(_read_manifest_value "${manifest}" suboptions)" == "runner" ]]
}

forgejo_runner_manifest_present() {
  local manifest="${COMPONENT_MANIFEST_DIR}/${COMPONENT_FORGEJO_RUNNER}"
  valid_component_manifest_entry "${manifest}" "${COMPONENT_FORGEJO_RUNNER}"
}

forgejo_runner_is_expected() {
  [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
    || forgejo_runner_manifest_present \
    || forgejo_manifest_has_runner \
    || [[ -x /usr/local/bin/forgejo-runner \
      || -f /etc/systemd/system/forgejo-runner.service ]]
}

forgejo_runner_is_forgejo_suboption() {
  forgejo_runner_is_expected \
    && ! forgejo_runner_manifest_present \
    && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}"
}

restore_forgejo_runner_intent() {
  is_selected_component "${COMPONENT_FORGEJO}" || return 0
  forgejo_runner_is_forgejo_suboption || return 0
  ZOMBIE_INSTALL_FORGEJO_RUNNER=1
}

forgejo_runner_drop_in_paths() {
  local loaded
  loaded="$(
    systemctl show forgejo-runner.service --property=DropInPaths --value \
      2>/dev/null || true
  )"
  {
    tr ' ' '\n' <<<"${loaded}"
    find /etc/systemd/system/forgejo-runner.service.d -maxdepth 1 \
      \( -type f -o -type l \) -name '*.conf' -print 2>/dev/null || true
  } | awk 'NF && !seen[$0]++'
}

_forgejo_runner_drop_in_is_obsolete() {
  local drop_in="$1"
  [[ -f "${drop_in}" ]] || return 1
  awk '
    /^[[:space:]]*($|#|;)/ { next }
    {
      line = $0
      sub(/^[[:space:]]+/, "", line)
      sub(/[[:space:]]+$/, "", line)
      content[++count] = line
    }
    END {
      exit !(count == 3 \
        && content[1] == "[Service]" \
        && content[2] == "ExecStart=" \
        && content[3] == "ExecStart=/usr/local/bin/forgejo-runner -c /var/lib/forgejo-runner/config.yaml daemon")
    }
  ' "${drop_in}"
}

remove_obsolete_forgejo_runner_drop_in() {
  local drop_in=/etc/systemd/system/forgejo-runner.service.d/override.conf
  _forgejo_runner_drop_in_is_obsolete "${drop_in}" || return 0
  rm -f "${drop_in}"
  rmdir /etc/systemd/system/forgejo-runner.service.d 2>/dev/null || true
  info "Removed the obsolete Forgejo runner systemd override."
  note_changed
}

forgejo_runner_uses_managed_config() {
  local exec_start expected
  expected="path=/usr/local/bin/forgejo-runner ; argv[]=/usr/local/bin/forgejo-runner -c /var/lib/forgejo-runner/config.yaml daemon ;"
  exec_start="$(
    systemctl show forgejo-runner.service --property=ExecStart --value \
      2>/dev/null || true
  )"
  [[ "${exec_start}" == *"${expected}"* ]]
}

forgejo_runner_in_docker_group() {
  id -nG forgejo-runner 2>/dev/null \
    | tr ' ' '\n' \
    | grep -Fx docker >/dev/null
}

forgejo_runner_has_docker_access() {
  if (( EUID == 0 )); then
    runuser -u forgejo-runner -- /usr/bin/docker info \
      --format '{{.ServerVersion}}' >/dev/null 2>&1
  else
    sudo -n -u forgejo-runner -- /usr/bin/docker info \
      --format '{{.ServerVersion}}' >/dev/null 2>&1
  fi
}

forgejo_runner_declared_successfully() {
  local invocation_id
  systemctl is-active --quiet forgejo-runner.service 2>/dev/null || return 1
  invocation_id="$(
    systemctl show forgejo-runner.service --property=InvocationID --value \
      2>/dev/null || true
  )"
  [[ "${invocation_id}" =~ ^[[:xdigit:]]{32}$ ]] || return 1
  if journalctl --quiet --no-pager \
      "_SYSTEMD_INVOCATION_ID=${invocation_id}" 2>/dev/null \
      | awk 'index($0, "declared successfully") { found = 1 }
             END { exit !found }'; then
    return 0
  fi
  (( EUID != 0 )) \
    && sudo -n journalctl --quiet --no-pager \
      "_SYSTEMD_INVOCATION_ID=${invocation_id}" 2>/dev/null \
      | awk 'index($0, "declared successfully") { found = 1 }
             END { exit !found }'
}

# ---------------------------------------------------------------------------
# Subcommand: verify}

# ---------------------------------------------------------------------------
# Subcommand: verify
# ---------------------------------------------------------------------------

verify_zombie() {
  # Keep lifecycle verification in this script. A deployed verifier may come
  # from an older release and must not be able to break current verify output.
  id "${AGENT_USER}" >/dev/null 2>&1 \
    && vr ok zombie user "User ${AGENT_USER} exists." \
    || vr fail zombie user "User ${AGENT_USER} missing. Run 'sudo ./${SCRIPT_NAME} install zombie' first."
  [[ -f "/etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie" ]] \
    && vr ok zombie sudoers "Sudoers drop-in present." \
    || vr fail zombie sudoers "Sudoers drop-in missing. Run 'sudo ./${SCRIPT_NAME} repair zombie'."
  [[ -d "${ZOMBIE_DIR}" ]] \
    && vr ok zombie install_root "${ZOMBIE_DIR} present." \
    || vr fail zombie install_root "${ZOMBIE_DIR} missing. Run 'sudo ./${SCRIPT_NAME} install zombie' first."
  [[ -x "${ZOMBIE_DIR}/bin/verify" ]] \
    && vr ok zombie verify_script "${ZOMBIE_DIR}/bin/verify present." \
    || vr fail zombie verify_script "${ZOMBIE_DIR}/bin/verify not found. Run 'sudo ./${SCRIPT_NAME} install zombie' first."
  systemctl is-active --quiet ubuntu-zombie-chat.service 2>/dev/null \
    && vr ok zombie chat_service "Chat service active." \
    || vr fail zombie chat_service "Chat service not active. Run: sudo systemctl start ubuntu-zombie-chat"
}

verify_forgejo_runner() {
  local component="${COMPONENT_FORGEJO_RUNNER}"
  local config_perms registration_perms drop_ins
  [[ -x /usr/local/bin/forgejo ]] \
    && vr ok "${component}" forgejo_binary "Required Forgejo server binary present." \
    || vr fail "${component}" forgejo_binary "Required Forgejo server binary missing."
  systemctl is-active --quiet forgejo.service 2>/dev/null \
    && vr ok "${component}" forgejo_service "Required Forgejo service active." \
    || vr fail "${component}" forgejo_service "Required Forgejo service is not active."
  [[ -x /usr/local/bin/forgejo-runner ]] \
    && vr ok "${component}" binary "Forgejo runner binary present." \
    || vr fail "${component}" binary "Forgejo runner binary missing."
  [[ -f /etc/systemd/system/forgejo-runner.service ]] \
    && vr ok "${component}" unit "Forgejo runner service unit present." \
    || vr fail "${component}" unit "Forgejo runner service unit missing."
  systemctl is-enabled --quiet forgejo-runner.service 2>/dev/null \
    && vr ok "${component}" enabled "Forgejo runner enabled at boot." \
    || vr fail "${component}" enabled "Forgejo runner is not enabled at boot."
  systemctl is-active --quiet forgejo-runner.service 2>/dev/null \
    && vr ok "${component}" service "Forgejo Actions runner active." \
    || vr fail "${component}" service "Forgejo Actions runner is not active."
  systemctl is-active --quiet docker.service 2>/dev/null \
    && vr ok "${component}" docker_service "Docker service active." \
    || vr fail "${component}" docker_service "Docker service is not active."
  forgejo_runner_in_docker_group \
    && vr ok "${component}" docker_group "forgejo-runner belongs to the docker group." \
    || vr fail "${component}" docker_group "forgejo-runner is not in the docker group."
  if [[ -s /var/lib/forgejo-runner/.runner ]]; then
    vr ok "${component}" registration "Forgejo runner registration is present."
  elif (( EUID != 0 )) \
      && [[ -d /var/lib/forgejo-runner && ! -x /var/lib/forgejo-runner ]]; then
    vr fail "${component}" registration "Runner registration is not inspectable without root. Re-run with sudo."
  else
    vr fail "${component}" registration "Forgejo runner registration is missing or empty."
  fi
  registration_perms="$(
    stat -c '%U:%G %a' /var/lib/forgejo-runner/.runner 2>/dev/null || true
  )"
  [[ "${registration_perms}" == "forgejo-runner:forgejo-runner 600" ]] \
    && vr ok "${component}" registration_perms "Runner registration permissions correct." \
    || vr fail "${component}" registration_perms "Runner registration permissions are incorrect or not inspectable."
  config_perms="$(
    stat -c '%U:%G %a' /var/lib/forgejo-runner/config.yaml 2>/dev/null || true
  )"
  [[ "${config_perms}" == "root:forgejo-runner 640" ]] \
    && forgejo_runner_config_is_managed \
    && vr ok "${component}" config "Managed runner configuration is active." \
    || vr fail "${component}" config "Runner configuration is missing, uninspectable, or unmanaged."
  forgejo_runner_uses_managed_config \
    && vr ok "${component}" exec "Runner service loads the managed configuration." \
    || vr fail "${component}" exec "Runner service does not load the managed configuration."
  drop_ins="$(forgejo_runner_drop_in_paths)"
  [[ -z "${drop_ins}" ]] \
    && vr ok "${component}" drop_ins "Runner service has no unmanaged systemd drop-ins." \
    || vr fail "${component}" drop_ins "Runner service has unmanaged systemd drop-ins: ${drop_ins//$'\n'/ }."
  if forgejo_runner_has_docker_access; then
    vr ok "${component}" docker_access "forgejo-runner can access the Docker daemon."
  elif (( EUID != 0 )); then
    vr fail "${component}" docker_access "Docker access is not inspectable without root. Re-run with sudo."
  else
    vr fail "${component}" docker_access "forgejo-runner cannot access the Docker daemon."
  fi
  forgejo_runner_declared_successfully \
    && vr ok "${component}" declared "Current runner invocation declared successfully to Forgejo." \
    || vr fail "${component}" declared "Current runner invocation has not declared successfully."
}

cmd_verify() {
  local -a v_status=() v_component=() v_id=() v_msg=()
  vr() { v_status+=("$1"); v_component+=("$2"); v_id+=("$3"); v_msg+=("$4"); }
  if (( ${#SELECTED_COMPONENTS[@]} == 0 )); then
    vr fail none manifest "No managed components found."
  fi
  local component
  for component in "${SELECTED_COMPONENTS[@]}"; do
    component_dispatch_hook "${component}" verify
  done

  local n="${#v_status[@]}" i failed=0 passed=0
  for (( i = 0; i < n; i++ )); do
    case "${v_status[i]}" in
      ok) passed=$((passed + 1)) ;;
      *) failed=$((failed + 1)) ;;
    esac
  done
  if (( JSON_OUTPUT )); then
    printf '{"tool":"verify","passed":%d,"failed":%d,"checks":[' "${passed}" "${failed}"
    for (( i = 0; i < n; i++ )); do
      printf '{"component":"%s","id":"%s","status":"%s","message":"%s"}' \
        "$(json_escape "${v_component[i]}")" "$(json_escape "${v_id[i]}")" "${v_status[i]}" "$(json_escape "${v_msg[i]}")"
      [[ $i -lt $((n - 1)) ]] && printf ','
    done
    printf ']}\n'
  else
    printf '%s== ubuntu-zombie verify ==%s\n\n' "${C_BOLD}" "${C_RESET}"
    printf '%sComponents:%s %s\n\n' "${C_BOLD}" "${C_RESET}" "$(selected_components_label)"
    for (( i = 0; i < n; i++ )); do
      if [[ "${v_status[i]}" == "ok" ]]; then
        ok "[${v_component[i]}] ${v_msg[i]}"
      else
        printf '%s[x]%s [%s] %s\n' "${C_RED}" "${C_RESET}" "${v_component[i]}" "${v_msg[i]}"
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

  local host_arch
  host_arch="$(dpkg --print-architecture 2>/dev/null || uname -m)"

  if (( ${#SELECTED_COMPONENTS[@]} == 0 )); then
    dr info none manifest "No managed components found. Run 'sudo ./${SCRIPT_NAME} install' to install Ubuntu Zombie."
  fi

  doctor_zombie() {
    if id "${AGENT_USER}" >/dev/null 2>&1; then
      dr ok zombie user "User ${AGENT_USER} exists."
    else
      dr warn zombie user "User ${AGENT_USER} missing. Fix: sudo ./${SCRIPT_NAME} install zombie"
    fi

    if [[ -f "/etc/sudoers.d/90-${AGENT_USER}-ubuntu-zombie" ]]; then
      dr ok zombie sudoers "Sudoers drop-in present."
    else
      dr warn zombie sudoers "Sudoers drop-in missing. Fix: sudo ./${SCRIPT_NAME} repair zombie"
    fi

    if [[ -d "${ZOMBIE_DIR}" ]]; then
      dr ok zombie install_root "${ZOMBIE_DIR} present."
    else
      dr warn zombie install_root "${ZOMBIE_DIR} missing. Fix: sudo ./${SCRIPT_NAME} install zombie"
    fi

    if [[ -f "${ZOMBIE_DIR}/secrets/env" ]]; then
      local perms
      perms="$(stat -c %a "${ZOMBIE_DIR}/secrets/env" 2>/dev/null || echo ???)"
      if [[ "${perms}" == "600" ]]; then
        dr ok zombie secrets_perms "secrets/env permissions 600."
      else
        dr warn zombie secrets_perms "secrets/env permissions ${perms} (must be 600). Fix: sudo ./${SCRIPT_NAME} repair zombie"
      fi
      if provider_credential_configured "${ZOMBIE_DIR}/secrets/env"; then
        dr ok zombie provider_token "Provider credential present."
      else
        dr warn zombie provider_token "No provider credential. Fix: sudo ${ZOMBIE_DIR}/bin/secrets-edit"
      fi
    else
      dr warn zombie secrets_env "secrets/env missing. Fix: sudo ./${SCRIPT_NAME} install zombie"
    fi

    if systemctl list-unit-files ubuntu-zombie-chat.service >/dev/null 2>&1; then
      if systemctl is-active --quiet ubuntu-zombie-chat.service; then
        dr ok zombie chat_service "Chat service active."
      else
        dr warn zombie chat_service "Chat service installed but not running. Fix: sudo systemctl start ubuntu-zombie-chat"
      fi
    else
      dr warn zombie chat_service "Chat service unit missing. Fix: sudo ./${SCRIPT_NAME} install zombie"
    fi
  }

  doctor_forgejo_runner() {
    local component="${COMPONENT_FORGEJO_RUNNER}"
    if ! legacy_forgejo_runner_present; then
      dr warn "${component}" missing \
        "Forgejo runner artefacts missing. Fix: sudo ./${SCRIPT_NAME} install forgejo-runner"
      return
    fi
    systemctl is-active --quiet forgejo.service 2>/dev/null \
      && dr ok "${component}" forgejo "Required Forgejo service active." \
      || dr warn "${component}" forgejo "Required Forgejo service is not active."
    systemctl is-active --quiet docker.service 2>/dev/null \
      && dr ok "${component}" docker "Docker service active." \
      || dr warn "${component}" docker "Docker service is not active."
    systemctl is-active --quiet forgejo-runner.service 2>/dev/null \
      && dr ok "${component}" service "Forgejo Actions runner active." \
      || dr warn "${component}" service "Forgejo Actions runner is not active."
    [[ -s /var/lib/forgejo-runner/.runner ]] \
      && dr ok "${component}" registration "Runner registration is present." \
      || dr warn "${component}" registration "Runner registration is missing, empty, or uninspectable."
    forgejo_runner_config_is_managed \
      && forgejo_runner_uses_managed_config \
      && dr ok "${component}" config "Managed runner configuration is active." \
      || dr warn "${component}" config "Runner configuration is missing or unmanaged."
    forgejo_runner_in_docker_group \
      && dr ok "${component}" docker_group "forgejo-runner belongs to the docker group." \
      || dr warn "${component}" docker_group "forgejo-runner is not in the docker group."
    forgejo_runner_declared_successfully \
      && dr ok "${component}" declared "Current runner invocation declared successfully." \
      || dr warn "${component}" declared "Current runner invocation has not declared successfully."
  }

  local component
  for component in "${SELECTED_COMPONENTS[@]}"; do
    component_dispatch_hook "${component}" doctor
  done

  local n="${#d_status[@]}" i warns=0
  for (( i = 0; i < n; i++ )); do
    [[ "${d_status[i]}" == "warn" ]] && warns=$((warns + 1))
  done

  if (( JSON_OUTPUT )); then
    printf '{\n'
    printf '  "tool": "doctor",\n'
    printf '  "host": {"id": "%s", "version": "%s", "arch": "%s"},\n' \
      "$(json_escape "${ID:-}")" "$(json_escape "${VERSION_ID:-}")" "$(json_escape "${host_arch}")"
    printf '  "components": "%s",\n' "$(json_escape "$(selected_components_label)")"
    printf '  "warnings": %d,\n' "${warns}"
    printf '  "checks": [\n'
    for (( i = 0; i < n; i++ )); do
      printf '    {"component": "%s", "id": "%s", "status": "%s", "message": "%s"}' \
        "$(json_escape "${d_component[i]}")" "$(json_escape "${d_id[i]}")" "${d_status[i]}" "$(json_escape "${d_msg[i]}")"
      [[ $i -lt $((n - 1)) ]] && printf ','
      printf '\n'
    done
    printf '  ]\n'
    printf '}\n'
    return 0
  fi

  printf '%s== ubuntu-zombie doctor ==%s\n\n' "${C_BOLD}" "${C_RESET}"
  printf '%sHost:%s %s %s on %s\n' "${C_BOLD}" "${C_RESET}" \
    "${ID:-?}" "${VERSION_ID:-?}" "${host_arch}"
  printf '%sComponents:%s %s\n\n' "${C_BOLD}" "${C_RESET}" "$(selected_components_label)"
  for (( i = 0; i < n; i++ )); do
    case "${d_status[i]}" in
      ok)   ok   "[${d_component[i]}] ${d_msg[i]}" ;;
      warn) warn "[${d_component[i]}] ${d_msg[i]}" ;;
      *)    info "[${d_component[i]}] ${d_msg[i]}" ;;
    esac
  done
  echo
  if component_selected_for_lifecycle "${COMPONENT_ZOMBIE}"; then
    info "For a runtime health summary: ${ZOMBIE_DIR}/bin/health-check"
  fi
}

# ---------------------------------------------------------------------------
# Subcommand: repair
# ---------------------------------------------------------------------------

cmd_repair() {
  section "Repair"

  repair_zombie() {
    if (( EXPLICIT_TARGETS )) && ! id "${AGENT_USER}" >/dev/null 2>&1 \
        && [[ ! -d "${ZOMBIE_DIR}" ]]; then
      warn "Component 'zombie' does not appear to be installed (user ${AGENT_USER} and ${ZOMBIE_DIR} absent)."
      warn "  To install: sudo ./${SCRIPT_NAME} install zombie"
    fi
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
      systemctl restart ubuntu-zombie-chat.service || warn "Chat service failed to restart; see journalctl -u ubuntu-zombie-chat"
      ok "Chat service restarted."
    fi
    if [[ -d "${ZOMBIE_DIR}/agent/templates" ]]; then
      install -d -m 755 -o root -g root "${ZOMBIE_DIR}/pi"
      install -d -m 750 -o "${AGENT_USER}" -g "${AGENT_USER}" \
        "${ZOMBIE_DIR}/state/logs" "${ZOMBIE_DIR}/state/pi-mono-sessions" 2>/dev/null || true
      [[ ! -f "${ZOMBIE_DIR}/agent/templates/settings.json.tmpl" ]] \
        || install -m 644 "${ZOMBIE_DIR}/agent/templates/settings.json.tmpl" "${ZOMBIE_DIR}/pi/settings.json"
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

  repair_forgejo_runner() {
    local runner_host
    if ! legacy_forgejo_runner_present; then
      warn "Component 'forgejo-runner' does not appear to be installed."
      warn "  To install: sudo ./${SCRIPT_NAME} install forgejo-runner"
      return
    fi
    [[ -x /usr/local/bin/forgejo && -s /etc/forgejo/app.ini ]] \
      || die "Forgejo runner repair requires a complete local Forgejo installation." 1
    systemctl is-active --quiet forgejo.service \
      || die "Forgejo must be active before its runner can be repaired." 1
    [[ -x /usr/local/bin/forgejo-runner ]] \
      || die "Forgejo runner binary is missing; re-run: sudo ./${SCRIPT_NAME} install forgejo-runner" 1
    id forgejo-runner >/dev/null 2>&1 \
      || die "Forgejo runner user is missing; re-run: sudo ./${SCRIPT_NAME} install forgejo-runner" 1
    [[ -s /var/lib/forgejo-runner/.runner ]] \
      || die "Forgejo runner registration is missing or empty; re-run: sudo ./${SCRIPT_NAME} install forgejo-runner" 1
    runner_host="$(forgejo_runner_public_host)" \
      || die "Forgejo must have a valid HTTPS public host before its runner can be repaired." 1
    usermod -aG docker forgejo-runner
    chown forgejo-runner:forgejo-runner /var/lib/forgejo-runner \
      /var/lib/forgejo-runner/.runner
    chmod 750 /var/lib/forgejo-runner
    chmod 600 /var/lib/forgejo-runner/.runner
    sed "s|__FORGEJO_HOST__|${runner_host}|g" \
      "${PAYLOAD_DIR}/etc/forgejo-runner-config.yaml" \
      | install -m 640 -o root -g forgejo-runner /dev/stdin \
        /var/lib/forgejo-runner/config.yaml
    install -m 644 "${PAYLOAD_DIR}/systemd/forgejo-runner.service" \
      /etc/systemd/system/forgejo-runner.service
    remove_obsolete_forgejo_runner_drop_in
    systemctl enable --now docker.service >/dev/null 2>&1 \
      || die "Docker Engine failed to start; see journalctl -u docker." 1
    systemctl daemon-reload
    local runner_drop_ins
    runner_drop_ins="$(forgejo_runner_drop_in_paths)"
    [[ -z "${runner_drop_ins}" ]] \
      || die "Refusing to start the Forgejo runner with unmanaged systemd drop-ins: ${runner_drop_ins//$'\n'/ }. Reconcile them, then re-run repair." 1
    forgejo_runner_uses_managed_config \
      || die "The effective forgejo-runner unit ignores the managed config; inspect systemd drop-ins." 1
    forgejo_runner_in_docker_group && forgejo_runner_has_docker_access \
      || die "forgejo-runner cannot access the Docker daemon after repair." 1
    systemctl enable forgejo-runner.service >/dev/null \
      || die "Could not enable forgejo-runner.service during repair." 1
    systemctl restart forgejo-runner.service \
      || die "Forgejo runner failed to restart; see journalctl -u forgejo-runner." 1
    retry 6 2 -- forgejo_runner_declared_successfully \
      || die "Forgejo runner restarted but did not declare successfully; see journalctl -u forgejo-runner." 1
    ok "Forgejo runner ownership, configuration, and service re-asserted."
  }

  local component
  for component in "${SELECTED_COMPONENTS[@]}"; do
    component_dispatch_hook "${component}" repair
  done
}

# ---------------------------------------------------------------------------
# Subcommand: uninstall
# ---------------------------------------------------------------------------

cmd_uninstall() {
  if [[ -x "${SCRIPT_DIR}/uninstall.sh" ]]; then
    # Forward the behaviour flags parsed by this wrapper so that
    # `install.sh uninstall --dry-run` really previews (and does not
    # perform a live uninstall), and `--yes`, `--quiet`, `--no-color`,
    # `--archive`, and `--keep-agent` reach the uninstaller.
    local -a fwd=()
    (( DRY_RUN ))              && fwd+=(--dry-run)
    (( ASSUME_YES ))           && fwd+=(--yes)
    (( ZOMBIE_QUIET ))         && fwd+=(--quiet)
    (( UNINSTALL_ARCHIVE ))    && fwd+=(--archive)
    (( UNINSTALL_KEEP_AGENT )) && fwd+=(--keep-agent)
    [[ "${ZOMBIE_COLOR:-}" == "never" ]] && fwd+=(--no-color)
    exec "${SCRIPT_DIR}/uninstall.sh" "${fwd[@]}" "${TARGET_ARGS[@]}"
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

A real install of the selected components would:

  Components:     $(selected_components_label)
  Host:           ${ID:-?} ${VERSION_ID:-?} on $(dpkg --print-architecture 2>/dev/null || uname -m)
  Transcript:     ${LOG_FILE}
  Receipt:        $([[ "${ZOMBIE_RECEIPT}" == "1" ]] && echo "${RECEIPT_FILE}" || echo "(disabled)")
EOF
  local component
  for component in "${SELECTED_COMPONENTS[@]}"; do
    component_dispatch_hook "${component}" dry_run
  done
  cat <<EOF

Nothing has been changed. To proceed for real:

  sudo ./${SCRIPT_NAME} install $(selected_components_label)

See docs/QUICKSTART.md and docs/ARCHITECTURE.md for the full picture.
EOF
}

print_zombie_dry_run() {
  cat <<EOF

Zombie component:
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

print_forgejo_runner_dry_run() {
  cat <<EOF

Forgejo runner component:
  Actions runner  co-located Forgejo Actions runner (restricted Docker executor)
                  Docker: reuse existing engine, otherwise apt: docker.io
                  binary: /usr/local/bin/forgejo-runner (${FORGEJO_RUNNER_VERSION:-latest release})
                  registers against 127.0.0.1:${FORGEJO_HTTP_PORT} with labels:
                    ${FORGEJO_RUNNER_LABELS}
                  unit: /etc/systemd/system/forgejo-runner.service
                  dependency: Forgejo server component
                  note: co-locating runner and forge is contrary to upstream
                        guidance and is enabled deliberately.
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

  brand_banner "Ubuntu Zombie — setup parameters"
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

# One-line summary of every enabled optional component, for row 9.
options_summary() {
  local parts=()
  if [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]]; then
    local runner_state="off"
    [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] && runner_state="on"
    parts+=("Forgejo server (port ${FORGEJO_HTTP_PORT}, admin ${FORGEJO_ADMIN_USER}, runner: ${runner_state})")
  fi
  local IFS='; '
  printf '%s' "${parts[*]}"
}

# Individual field editors.# Individual field editors. Each keeps the current value when the operator
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
# Optional components menu (item 9 of the parameter review)
# ---------------------------------------------------------------------------
# A nested, branded sub-menu that lists every opt-in component with its
# on/off state and settings. New components add one row here instead of
# renumbering the top-level review menu.

_edit_forgejo_port() {
  local v
  if prompt_until_valid "$(printf 'Forgejo web port [%s]: ' "${FORGEJO_HTTP_PORT}")" \
       is_valid_tcp_port v 1 && [[ -n "${v}" ]]; then
    FORGEJO_HTTP_PORT="${v}"; ok "Forgejo port set to ${FORGEJO_HTTP_PORT}."
  fi
}

_edit_forgejo_admin() {
  local v
  if prompt_until_valid "$(printf 'Forgejo admin username [%s]: ' "${FORGEJO_ADMIN_USER}")" \
       is_valid_forgejo_name v 1 && [[ -n "${v}" ]]; then
    FORGEJO_ADMIN_USER="${v}"; ok "Forgejo admin set to ${FORGEJO_ADMIN_USER}."
  fi
  if prompt_until_valid "$(printf 'Forgejo admin email [%s]: ' "${FORGEJO_ADMIN_EMAIL}")" \
       is_valid_forgejo_email v 1 && [[ -n "${v}" ]]; then
    FORGEJO_ADMIN_EMAIL="${v}"; ok "Forgejo admin email set to ${FORGEJO_ADMIN_EMAIL}."
  fi
  local p1 p2
  if ! read -r -s -p "Forgejo admin password (blank to generate a root-only bootstrap file): " p1; then
    printf '\n'
    warn "No input (EOF); Forgejo admin password unchanged."
    return 0
  fi
  printf '\n'
  if [[ -z "${p1}" ]]; then
    FORGEJO_ADMIN_PASSWORD=""
    FORGEJO_ADMIN_PASSWORD_SOURCE=""
    info "Forgejo admin password will be generated into a root-only bootstrap file."
    return 0
  fi
  if ! is_valid_forgejo_password "${p1}"; then
    warn "Password must be 8-256 printable characters; Forgejo admin password unchanged."
    return 0
  fi
  if ! read -r -s -p "Confirm Forgejo admin password: " p2; then
    printf '\n'
    warn "No input (EOF); Forgejo admin password unchanged."
    return 0
  fi
  printf '\n'
  if [[ "${p1}" != "${p2}" ]]; then
    warn "Passwords did not match; Forgejo admin password unchanged."
    return 0
  fi
  FORGEJO_ADMIN_PASSWORD="${p1}"
  FORGEJO_ADMIN_PASSWORD_SOURCE="operator"
  ok "Forgejo admin password accepted (not recorded)."
}

_edit_forgejo_database() {
  local v
  if prompt_until_valid "$(printf 'Forgejo PostgreSQL database name [%s]: ' "${FORGEJO_DB_NAME}")" \
       is_valid_forgejo_name v 1 && [[ -n "${v}" ]]; then
    FORGEJO_DB_NAME="${v}"; ok "Forgejo database set to ${FORGEJO_DB_NAME}."
  fi
  if prompt_until_valid "$(printf 'Forgejo PostgreSQL role (username) [%s]: ' "${FORGEJO_DB_USER}")" \
       is_valid_forgejo_name v 1 && [[ -n "${v}" ]]; then
    FORGEJO_DB_USER="${v}"; ok "Forgejo database role set to ${FORGEJO_DB_USER}."
  fi
  local p1 p2
  if ! read -r -s -p "Forgejo PostgreSQL role password (blank to generate privately): " p1; then
    printf '\n'
    warn "No input (EOF); Forgejo database password unchanged."
    return 0
  fi
  printf '\n'
  if [[ -z "${p1}" ]]; then
    FORGEJO_DB_PASSWORD=""
    FORGEJO_DB_PASSWORD_SOURCE=""
    info "Forgejo database password will be generated and retained only in app.ini."
    return 0
  fi
  if ! is_valid_forgejo_password "${p1}"; then
    warn "Password must be 8-256 printable characters; Forgejo database password unchanged."
    return 0
  fi
  if ! read -r -s -p "Confirm Forgejo PostgreSQL role password: " p2; then
    printf '\n'
    warn "No input (EOF); Forgejo database password unchanged."
    return 0
  fi
  printf '\n'
  if [[ "${p1}" != "${p2}" ]]; then
    warn "Passwords did not match; Forgejo database password unchanged."
    return 0
  fi
  FORGEJO_DB_PASSWORD="${p1}"
  FORGEJO_DB_PASSWORD_SOURCE="operator"
  ok "Forgejo database password accepted (not recorded)."
}

# Accepts a release pin like 11.0.3 or the keyword "latest" (clears the pin).
_forgejo_version_or_latest() {
  [[ "${1,,}" == "latest" ]] || is_valid_forgejo_version "$1"
}

_edit_forgejo_versions() {
  local v
  if prompt_until_valid "$(printf 'Forgejo release pin (x.y.z, or "latest") [%s]: ' "${FORGEJO_VERSION:-latest}")" \
       _forgejo_version_or_latest v 1 && [[ -n "${v}" ]]; then
    [[ "${v,,}" == "latest" ]] && v=""
    FORGEJO_VERSION="${v}"; ok "Forgejo version set to ${FORGEJO_VERSION:-latest release}."
  fi
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]]; then
    if prompt_until_valid "$(printf 'Runner release pin (x.y.z, or "latest") [%s]: ' "${FORGEJO_RUNNER_VERSION:-latest}")" \
         _forgejo_version_or_latest v 1 && [[ -n "${v}" ]]; then
      [[ "${v,,}" == "latest" ]] && v=""
      FORGEJO_RUNNER_VERSION="${v}"; ok "Runner version set to ${FORGEJO_RUNNER_VERSION:-latest release}."
    fi
    if prompt_until_valid "$(printf 'Runner labels [%s]: ' "${FORGEJO_RUNNER_LABELS}")" \
         is_valid_forgejo_runner_labels v 1 && [[ -n "${v}" ]]; then
      FORGEJO_RUNNER_LABELS="${v}"; ok "Runner labels set to ${FORGEJO_RUNNER_LABELS}."
    fi
  fi
}

_toggle_forgejo_runner() {
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]]; then
    ZOMBIE_INSTALL_FORGEJO_RUNNER=0
    info "Forgejo Actions runner disabled."
  else
    ZOMBIE_INSTALL_FORGEJO_RUNNER=1
    warn "Co-locating the runner with the forge is contrary to upstream guidance; enabling deliberately."
    info "Forgejo Actions runner enabled (restricted Docker executor)."
  fi
}

_toggle_forgejo() {
  if [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]]; then
    ZOMBIE_INSTALL_FORGEJO=0
    ZOMBIE_INSTALL_FORGEJO_RUNNER=0
    info "Forgejo server disabled."
  else
    ZOMBIE_INSTALL_FORGEJO=1
    info "Forgejo server enabled (PostgreSQL-backed, port ${FORGEJO_HTTP_PORT})."
  fi
}

# Render the current optional components as a glance-able sub-table.
print_options_table() {
  brand_banner "Ubuntu Zombie — optional components"
  printf '  %sEvery option is off by default and reversible by uninstall.sh.%s\n\n' \
    "${C_DIM}" "${C_RESET}"
  if [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]]; then
    field "1) Forgejo server"  "enabled"
    field "2) Forgejo port"    "${FORGEJO_HTTP_PORT}/tcp (loopback backend)"
    field "3) Forgejo admin"   "${FORGEJO_ADMIN_USER} <${FORGEJO_ADMIN_EMAIL}> (password $(password_source_label "${FORGEJO_ADMIN_PASSWORD_SOURCE}"))"
    field "4) Actions runner"  "$([[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] && echo 'enabled (restricted Docker executor, same host)' || echo 'disabled')"
    field "5) Database"        "PostgreSQL ${FORGEJO_DB_NAME} (role ${FORGEJO_DB_USER}, password $(password_source_label "${FORGEJO_DB_PASSWORD_SOURCE}"))"
    if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]]; then
      field "6) Versions"      "Forgejo ${FORGEJO_VERSION:-latest release}, runner ${FORGEJO_RUNNER_VERSION:-latest release} (labels ${FORGEJO_RUNNER_LABELS})"
    else
      field "6) Versions"      "Forgejo ${FORGEJO_VERSION:-latest release}"
    fi
  else
    field "1) Forgejo server"  "disabled (git forge + PostgreSQL, optional CI runner)" "${C_DIM}"
  fi
  printf '\n'
}

# The nested options review loop, entered from item 9 of review_parameters.
review_options() {
  local choice
  while true; do
    print_options_table
    printf '  %s[b]%s back to setup    %s[1-6]%s toggle or edit an option\n' \
      "${C_ACCENT}" "${C_RESET}" "${C_BRAND2}" "${C_RESET}"
    if ! read -r -p "$(printf '%s➜%s your choice [b]: ' "${C_BRAND}" "${C_RESET}")" choice; then
      return 0
    fi
    case "${choice,,}" in
      ""|b|back|q) return 0 ;;
      1) _toggle_forgejo ;;
      2) [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]] && _edit_forgejo_port \
           || warn "Enable the Forgejo server first (option 1)." ;;
      3) [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]] && _edit_forgejo_admin \
           || warn "Enable the Forgejo server first (option 1)." ;;
      4) [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]] && _toggle_forgejo_runner \
           || warn "Enable the Forgejo server first (option 1)." ;;
      5) [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]] && _edit_forgejo_database \
           || warn "Enable the Forgejo server first (option 1)." ;;
      6) [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]] && _edit_forgejo_versions \
           || warn "Enable the Forgejo server first (option 1)." ;;
      *) warn "Unrecognised choice: '${choice}'. Enter a number 1-6 or 'b'." ;;
    esac
  done
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

review_forgejo_parameters() {
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && return 0
  (( ASSUME_YES )) && return 0
  [[ -t 0 ]] || return 0

  local choice
  while true; do
    load_os_release
    brand_banner "Forgejo — setup parameters"
    field "1) Forgejo port"   "${FORGEJO_HTTP_PORT}/tcp (loopback backend)"
    field "2) Forgejo admin"  "${FORGEJO_ADMIN_USER} <${FORGEJO_ADMIN_EMAIL}> (password $(password_source_label "${FORGEJO_ADMIN_PASSWORD_SOURCE}"))"
    field "3) PostgreSQL database" "PostgreSQL ${FORGEJO_DB_NAME} (role ${FORGEJO_DB_USER}, password $(password_source_label "${FORGEJO_DB_PASSWORD_SOURCE}"))"
    field "4) Actions runner" "$([[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] && echo 'enabled (restricted Docker executor, same host)' || echo disabled)"
    field "5) Versions"       "Forgejo ${FORGEJO_VERSION:-latest release}"
    field "6) Core records"   "${LOG_FILE}; $([[ "${ZOMBIE_RECEIPT}" == "1" ]] && echo "${RECEIPT_FILE}" || echo 'receipt disabled')"
    field "   Host"           "${ID:-?} ${VERSION_ID:-?} ($(dpkg --print-architecture 2>/dev/null || uname -m))" "${C_DIM}"
    printf '\n  %s[a]%s accept and install    %s[1-6]%s edit a field    %s[q]%s cancel\n' \
      "${C_ACCENT}" "${C_RESET}" "${C_BRAND2}" "${C_RESET}" "${C_YELLOW}" "${C_RESET}"
    if ! read -r -p "$(printf '%s➜%s your choice [a]: ' "${C_BRAND}" "${C_RESET}")" choice; then
      info "No input (EOF); cancelling."; exit 0
    fi
    case "${choice,,}" in
      ""|a|accept|y|yes)
        validate_config
        REVIEWED=1
        ok "Parameters accepted."
        return 0 ;;
      q|quit|cancel|n|no) info "Cancelled."; exit 0 ;;
      1) _edit_forgejo_port ;;
      2) _edit_forgejo_admin ;;
      3) _edit_forgejo_database ;;
      4) _toggle_forgejo_runner ;;
      5) _edit_forgejo_versions ;;
      6) _edit_log_file; _toggle_receipt ;;
      *) warn "Unrecognised choice: '${choice}'. Enter a number 1-6, 'a', or 'q'." ;;
    esac
  done
}

review_forgejo_runner_parameters() {
  [[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && return 0
  (( ASSUME_YES )) && return 0
  [[ -t 0 ]] || return 0

  brand_banner "Forgejo runner — setup parameters"
  field "Version" "${FORGEJO_RUNNER_VERSION:-latest release}"
  field "Labels" "${FORGEJO_RUNNER_LABELS}"
  field "Executor" "restricted Docker executor, co-located with Forgejo"
  local choice
  if ! read -r -p "$(printf '%s➜%s install these settings? [Y/n]: ' "${C_BRAND}" "${C_RESET}")" choice; then
    info "No input (EOF); cancelling."
    exit 0
  fi
  case "${choice,,}" in
    ""|y|yes) REVIEWED=1 ;;
    *) info "Cancelled."; exit 0 ;;
  esac
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

receipt_start_forgejo() {
  printf 'Forgejo server   : independent product lifecycle\n'
  printf 'Forgejo backend  : 127.0.0.1:%s/tcp\n' "${FORGEJO_HTTP_PORT}"
  printf 'Forgejo admin    : %s <%s> (password %s)\n' \
    "${FORGEJO_ADMIN_USER}" "${FORGEJO_ADMIN_EMAIL}" \
    "$(password_source_label "${FORGEJO_ADMIN_PASSWORD_SOURCE}")"
  printf 'Forgejo database : %s (role %s; password %s)\n' \
    "${FORGEJO_DB_NAME}" "${FORGEJO_DB_USER}" \
    "$(password_source_label "${FORGEJO_DB_PASSWORD_SOURCE}")"
  printf 'Forgejo version  : %s\n' "${FORGEJO_VERSION:-latest (resolved at install)}"
  if ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}"; then
    printf 'Actions runner   : %s\n' \
      "$([[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] && echo 'enabled (co-located, restricted Docker executor)' || echo disabled)"
  fi
}

receipt_start_forgejo_runner() {
  printf 'Actions runner   : enabled (co-located, restricted Docker executor)\n'
  printf 'Runner version   : %s\n' \
    "${FORGEJO_RUNNER_VERSION:-latest (resolved at install)}"
  printf 'Runner labels    : %s\n' "${FORGEJO_RUNNER_LABELS}"
}

receipt_start_llama() {
  printf 'Llama component  : standalone PC-wide service\n'
  printf 'Llama API        : http://127.0.0.1:%s/v1 (loopback only)\n' "${LLAMA_PORT}"
  printf 'Llama runtime    : %s\n' "$(llama_catalog_release)"
  printf 'Llama model      : %s\n' "${LLAMA_MODEL_ID}"
  printf 'Llama context    : %s tokens; %s CPU threads\n' \
    "${LLAMA_CONTEXT_SIZE}" "${LLAMA_CPU_THREADS}"
}

receipt_finish_zombie() {
  printf 'Provider token   : %s\n' "$([[ "${PROVIDER_OK:-0}" == "1" ]] && echo present || echo missing)"
  printf 'Chat service     : %s\n' "$([[ "${CHAT_OK:-0}" == "1" ]] && echo running || echo 'not running')"
}

receipt_finish_forgejo() {
  printf 'Forgejo version  : %s\n' "${FORGEJO_RESOLVED_VERSION:-unknown}"
  printf 'Forgejo URL      : https://%s/\n' "${FORGEJO_URL_HOST:-unknown}"
  printf 'Forgejo service  : %s\n' \
    "$(systemctl is-active --quiet forgejo.service 2>/dev/null && echo running || echo 'not running')"
  printf 'Forgejo secrets  : not recorded; managed under /etc/forgejo\n'
  if [[ -f /etc/forgejo/bootstrap-admin-password ]]; then
    printf 'Admin credential : /etc/forgejo/bootstrap-admin-password (root only)\n'
  else
    printf 'Admin credential : operator supplied or existing; not recorded\n'
  fi
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
      && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}"; then
    printf 'Actions runner   : %s\n' \
      "$(systemctl is-active --quiet forgejo-runner.service 2>/dev/null && echo running || echo 'not running')"
  fi
}

receipt_finish_forgejo_runner() {
  printf 'Runner version   : %s\n' \
    "${FORGEJO_RUNNER_RESOLVED_VERSION:-unknown}"
  printf 'Actions runner   : %s\n' \
    "$(systemctl is-active --quiet forgejo-runner.service 2>/dev/null && echo running || echo 'not running')"
}

receipt_finish_llama() {
  printf 'Llama service    : %s\n' \
    "$(systemctl is-active --quiet llama-server.service 2>/dev/null && echo running || echo 'not running')"
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
    printf 'Ubuntu Zombie — install receipt\n'
    printf '============================================================\n'
    printf 'Phase            : START\n'
    printf 'Started (UTC)    : %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)"
    printf 'Installer        : %s %s\n' "${SCRIPT_NAME}" "${SCRIPT_VERSION}"
    printf 'Host             : %s %s (%s)\n' "${ID:-?}" "${VERSION_ID:-?}" \
      "$(dpkg --print-architecture 2>/dev/null || uname -m)"
    printf 'Invoked by       : %s (uid %s)\n' "${SUDO_USER:-$(id -un)}" "$(id -u)"
    printf 'Mode             : %s\n' \
      "$([[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && echo non-interactive || echo interactive)"
    printf 'Components       : %s\n' "$(selected_components_label)"
    printf '\n-- Parameters --\n'
    local component
    for component in "${SELECTED_COMPONENTS[@]}"; do
      component_dispatch_hook "${component}" receipt_start
    done
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
    local component
    for component in "${SELECTED_COMPONENTS[@]}"; do
      component_dispatch_hook "${component}" receipt_finish
    done
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

validate_component_registry \
  "validate review dry_run receipt_start receipt_finish install manifest final legacy verify doctor repair phase_count"
resolve_lifecycle_targets_from_manifest
restore_forgejo_runner_intent
validate_config

if [[ "${SUBCOMMAND}" != "uninstall" ]] \
  && (( UNINSTALL_ARCHIVE || UNINSTALL_KEEP_AGENT )); then
  die "--archive/--keep-agent only apply to the uninstall subcommand." 2
fi
if [[ "${SUBCOMMAND}" == "uninstall" ]] && (( EXPLICIT_TARGETS )) \
  && ! is_selected_component "${COMPONENT_ZOMBIE}" \
  && (( UNINSTALL_ARCHIVE || UNINSTALL_KEEP_AGENT )); then
  die "--archive/--keep-agent only apply to a zombie uninstall target." 2
fi

case "${SUBCOMMAND}" in
  # Verify reports failed health checks via its own output and exit status.
  # Do not let the install-time ERR trap re-label those expected failures as
  # installer crashes, especially when --json is feeding monitoring. Other
  # lifecycle subcommands keep the trap because their failures are mutations
  # or diagnostics that should retain the normal installer error context.
  verify)    trap - ERR; cmd_verify; exit $? ;;
  doctor)    cmd_doctor; exit $? ;;
  repair)    require_root; cmd_repair; exit $? ;;
  uninstall) (( DRY_RUN )) || require_root; cmd_uninstall; exit $? ;;
  install)   ;;
  *)         die "Unknown subcommand: ${SUBCOMMAND}" 2 ;;
esac

# Dry-run short-circuits the entire install path. It does not require
# root: the whole point is to let an operator preview what would happen
# before they grant sudo.
if (( DRY_RUN )); then
  print_dry_run_plan
  exit 0
fi

# =============================================================================
# install — the rest of the file
# =============================================================================

require_root
validate_noninteractive

if is_selected_component "${COMPONENT_FORGEJO}" \
    && [[ ! -f /var/lib/forgejo/installation.json ]] \
    && legacy_forgejo_present; then
  warn "An existing Forgejo installation was detected. The installer will update it in place and preserve repositories and database data."
  require_capitalized_yes FORGEJO_CONFIRM_UPDATE \
    "Allow Ubuntu Zombie to update the existing Forgejo installation?"
fi

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
if is_selected_component "${COMPONENT_ZOMBIE}"; then
  discover_local_llms
fi

# Interactive review: each selected component owns its parameter page. This
# keeps a zombie-only install from asking about unselected options.
for component in "${SELECTED_COMPONENTS[@]}"; do
  component_dispatch_hook "${component}" review
done
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

# Phase counter: count the install-path section banners so each one can be
# numbered "[n/total]". Derived from this file so it stays correct as
# phases are added or removed.
ZOMBIE_PHASE=0
SECTION_RULE_WIDTH=60
_count_option_sections() {
  awk -v m="$1" '
    $0 ~ "^ *# option-sections: " m " begin$" {f=1}
    f && /^ +section "/ {c++}
    $0 ~ "^ *# option-sections: " m " end$" {f=0}
    END {print c+0}
  ' "${BASH_SOURCE[0]}" 2>/dev/null || echo 0
}
count_zombie_phases() {
  awk '/^# install — the rest of the file/{f=1} f && /^section "/{c++} END{print c+0}' \
    "${BASH_SOURCE[0]}" 2>/dev/null || echo 0
}
count_forgejo_phases() {
  local count
  count="$(_count_option_sections forgejo)"
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
      && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}"; then
    count=$(( count + $(_count_option_sections forgejo-runner) ))
  fi
  printf '%s\n' "${count}"
}
count_forgejo_runner_phases() {
  _count_option_sections forgejo-runner
}
ZOMBIE_PHASE_TOTAL=0
for component in "${SELECTED_COMPONENTS[@]}"; do
  component_phase_count="$(component_dispatch_hook "${component}" phase_count)"
  [[ "${component_phase_count}" =~ ^[0-9]+$ ]] || component_phase_count=0
  ZOMBIE_PHASE_TOTAL=$(( ZOMBIE_PHASE_TOTAL + component_phase_count ))
done
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
info "Components: $(selected_components_label)"
if is_selected_component "${COMPONENT_ZOMBIE}"; then
  info "Agent user: ${AGENT_USER}"
  info "Install root: ${ZOMBIE_DIR}"
  info "Chat port: ${CHAT_PORT} (loopback only)"
fi
info "Mode: $([[ "${ZOMBIE_NONINTERACTIVE}" == "1" ]] && echo non-interactive || echo interactive)"
if (( ZOMBIE_PHASE_TOTAL > 0 )); then
  info "Phases: ${ZOMBIE_PHASE_TOTAL}. Typical run takes ~10–20 min depending on selected components and network speed."
else
  info "Typical run takes ~5–20 min depending on selected components and network speed."
fi

if is_selected_component "${COMPONENT_ZOMBIE}"; then
  cat <<EOF

This installer will:
  - Create the ${AGENT_USER} user (operating identity of the AI Systems Administrator) with passwordless sudo
  - Install Python and Node agent runtimes
  - Install the loopback chat service (ubuntu-zombie-chat.service)
  - Install policy, audit log, and helper scripts
  - Enable automatic security updates
EOF
elif is_selected_component "${COMPONENT_FORGEJO}"; then
  cat <<EOF

This installer will:
  - Delegate PostgreSQL, Forgejo, Caddy, and Avahi to products/forgejo
  - Keep the Forgejo backend on 127.0.0.1:3000 behind LAN HTTPS
  - Keep installer-owned transcript and root-only receipt records under /var/log
EOF
else
  cat <<EOF

This installer will:
  - Install a standalone llama.cpp CPU runtime and small default model
  - Run an OpenAI-compatible API on 127.0.0.1:8080
  - Install llama-manager without creating or changing a zombie account
EOF
fi
if [[ "${ZOMBIE_INSTALL_FORGEJO}" == "1" ]]; then
  printf '  - Install Forgejo + PostgreSQL with product-owned LAN HTTPS\n'
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]]; then
    printf '  - Install a co-located Forgejo Actions runner (restricted Docker executor)\n'
  fi
  if [[ "${ZOMBIE_INSTALL_LLAMA}" == "1" ]]; then
    printf '  - Install the independent PC-wide llama.cpp service on 127.0.0.1:8080\n'
  fi
fi
cat <<EOF

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
# Workspace at /opt/ai-zombie
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
# Optional component: Forgejo Actions runner
# ---------------------------------------------------------------------------
# The server lifecycle belongs exclusively to products/forgejo. The root suite
# retains its co-located runner lifecycle until the phase-5 extraction.

# Map dpkg architecture to the Forgejo release asset suffix. The uname -m
# names (x86_64/aarch64) only apply when dpkg is unavailable and the
# fallback runs.
forgejo_release_arch() {
  case "$(dpkg --print-architecture 2>/dev/null || uname -m)" in
    amd64|x86_64)  printf 'amd64' ;;
    arm64|aarch64) printf 'arm64' ;;
    *) return 1 ;;
  esac
}

# Candidate API origins for runner release metadata. Keep the legacy origin
# last for compatibility with older pinned releases.
forgejo_release_api_origins() {
  case "$1" in
    forgejo/runner)
      printf '%s\n' \
        "https://data.forgejo.org" \
        "https://code.forgejo.org" \
        "https://codeberg.org"
      ;;
    *)
      printf '%s\n' "https://codeberg.org"
      ;;
  esac
}

# Prefer Forgejo's canonical host, with Codeberg as a legacy fallback.
forgejo_release_download_bases() {
  case "$1" in
    forgejo/runner)
      printf '%s\n' \
        "https://code.forgejo.org" \
        "https://codeberg.org"
      ;;
    *)
      printf '%s\n' "https://codeberg.org"
      ;;
  esac
}

forgejo_release_tag_from_json() {
  python3 -c '
import json
import sys

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(1)

tag = data.get("tag_name") or data.get("name") or ""
if not tag:
    sys.exit(1)
print(tag)
'
}

# Resolve the latest release tag (e.g. "11.0.3") of a Forgejo repository.
forgejo_latest_release() {
  local repo="$1" origin json tag
  # Two short endpoint-local retries cover brief network flakes without
  # spending curl_get's full outer retry budget on an obsolete release host.
  local metadata_retry_count=2 metadata_retry_delay=2 metadata_max_time=15
  for origin in $(forgejo_release_api_origins "${repo}"); do
    # Use a bounded direct curl instead of curl_get here so a stale origin
    # fails over quickly. This trades curl_get's five outer attempts/logging for
    # one endpoint-local retry window before moving to the next origin. Forgejo
    # metadata origins have exposed the release version as either tag_name or
    # name, so accept both.
    json="$(curl -fsSL --retry "${metadata_retry_count}" \
              --retry-delay "${metadata_retry_delay}" \
              --max-time "${metadata_max_time}" \
              "${origin}/api/v1/repos/${repo}/releases/latest")" \
      || { warn "Release metadata unavailable from ${origin}; trying the next release origin."; continue; }
    tag="$(forgejo_release_tag_from_json <<<"${json}")" \
      || { warn "Release metadata malformed from ${origin}; trying the next release origin."; continue; }
    tag="${tag#v}"
    if [[ "${tag}" =~ ^[0-9]+\.[0-9]+\.[0-9]+(-[A-Za-z0-9.]+)?$ ]]; then
      printf '%s' "${tag}"
      return 0
    fi
    warn "Release metadata from ${origin} did not contain a valid semver tag; trying the next release origin."
  done
  return 1
}

# Download a Codeberg release asset and verify its published .sha256 sum.
# Usage: codeberg_fetch_verified <url> <dest_tmp_file>
codeberg_fetch_verified() {
  local url="$1" dest="$2" sum
  curl_get "${url}" -o "${dest}" || return 1
  sum="$(curl_get "${url}.sha256" | awk '{print $1}')" || return 1
  [[ "${sum}" =~ ^[0-9a-f]{64}$ ]] \
    || die "Could not fetch a valid checksum for ${url}." 1
  printf '%s  %s\n' "${sum}" "${dest}" | sha256sum -c - >/dev/null \
    || die "Checksum mismatch for ${url}." 1
}

# Download a Forgejo release asset from the canonical host with a legacy
# Codeberg fallback, verifying the adjacent .sha256 file from the same origin.
forgejo_fetch_release_asset() {
  local repo="$1" version="$2" asset="$3" dest="$4" base url
  for base in $(forgejo_release_download_bases "${repo}"); do
    url="${base}/${repo}/releases/download/v${version}/${asset}"
    if codeberg_fetch_verified "${url}" "${dest}"; then
      return 0
    fi
    warn "Release asset unavailable from ${base}; trying the next release origin."
  done
  return 1
}

ensure_forgejo_runner_docker_package() {
  local docker_cli="$1" containerd_status

  if [[ -x "${docker_cli}" ]]; then
    info "Docker CLI already installed; reusing the existing Docker Engine."
    note_satisfied
    return 0
  fi

  containerd_status="$(dpkg-query -W -f='${Status}' containerd.io 2>/dev/null || true)"
  if [[ "${containerd_status}" == "install ok installed" ]]; then
    die "Cannot install docker.io because containerd.io is installed. Existing packages were left unchanged; install a Docker Engine compatible with containerd.io or remove containerd.io, then re-run." 1
  fi

  apt_install docker.io
}

install_forgejo_runner() {
  local runner_arch installed_runner runner_tmp runner_token runner_drop_ins
  local runner_host

  # option-sections: forgejo-runner begin
  section "Install Forgejo runner"

  [[ -x /usr/local/bin/forgejo && -s /etc/forgejo/app.ini ]] \
    || die "Forgejo runner requires the local Forgejo server component. Run: sudo ./${SCRIPT_NAME} install forgejo-runner" 1
  systemctl is-active --quiet forgejo.service \
    || die "Forgejo must be active before its runner can be installed." 1
  runner_host="$(forgejo_runner_public_host)" \
    || die "Forgejo must have a valid HTTPS public host before its runner can be installed." 1
  [[ -s /etc/forgejo/caddy-local-ca.crt \
      && -s /usr/local/share/ca-certificates/forgejo-local-ca.crt ]] \
    || die "Forgejo local CA trust is missing. Run: sudo forgejo-manage repair" 1
  cmp -s /etc/forgejo/caddy-local-ca.crt \
      /usr/local/share/ca-certificates/forgejo-local-ca.crt \
    || die "Forgejo local CA trust is stale. Run: sudo forgejo-manage repair" 1
  runner_arch="$(forgejo_release_arch)" \
    || die "Forgejo runner releases support only amd64/arm64 hosts." 65

  warn "Co-locating the Actions runner with the forge is contrary to upstream guidance; enabled deliberately."
  ensure_forgejo_runner_docker_package /usr/bin/docker
  systemctl enable --now docker >/dev/null 2>&1 \
    || die "Docker Engine failed to start; see journalctl -u docker." 1
  if id forgejo-runner >/dev/null 2>&1; then
    info "User forgejo-runner already exists."
    note_satisfied
  else
    adduser --system --group --home /var/lib/forgejo-runner \
      --shell /bin/bash --gecos "Forgejo Actions runner" forgejo-runner
    ok "Created system user forgejo-runner."
    note_changed
  fi
  usermod -aG docker forgejo-runner
  install -d -m 750 -o forgejo-runner -g forgejo-runner /var/lib/forgejo-runner
  forgejo_runner_in_docker_group \
    || die "Could not add forgejo-runner to the docker group." 1
  forgejo_runner_has_docker_access \
    || die "forgejo-runner cannot access the Docker daemon after group setup." 1
  if [[ -n "${FORGEJO_RUNNER_VERSION}" ]]; then
    FORGEJO_RUNNER_RESOLVED_VERSION="${FORGEJO_RUNNER_VERSION}"
    info "Forgejo runner release pinned to ${FORGEJO_RUNNER_RESOLVED_VERSION}."
  else
    FORGEJO_RUNNER_RESOLVED_VERSION="$(forgejo_latest_release forgejo/runner)" \
      || die "Could not resolve the latest forgejo-runner release from Forgejo release metadata (pin FORGEJO_RUNNER_VERSION to proceed)." 66
    info "Latest forgejo-runner release: ${FORGEJO_RUNNER_RESOLVED_VERSION}."
  fi
  installed_runner=""
  if [[ -x /usr/local/bin/forgejo-runner ]]; then
    installed_runner="$(/usr/local/bin/forgejo-runner --version 2>/dev/null \
      | awk '{print $3}' | sed 's/^v//' || true)"
  fi
  if [[ "${installed_runner}" == "${FORGEJO_RUNNER_RESOLVED_VERSION}" ]]; then
    info "forgejo-runner ${FORGEJO_RUNNER_RESOLVED_VERSION} already installed."
    note_satisfied
  else
    runner_tmp="$(mktemp)"
    forgejo_fetch_release_asset forgejo/runner \
      "${FORGEJO_RUNNER_RESOLVED_VERSION}" \
      "forgejo-runner-${FORGEJO_RUNNER_RESOLVED_VERSION}-linux-${runner_arch}" \
      "${runner_tmp}" \
      || {
        rm -f "${runner_tmp}"
        die "Failed to download forgejo-runner ${FORGEJO_RUNNER_RESOLVED_VERSION}." 66
      }
    install -m 0755 -o root -g root "${runner_tmp}" \
      /usr/local/bin/forgejo-runner
    rm -f "${runner_tmp}"
    ok "Installed forgejo-runner ${FORGEJO_RUNNER_RESOLVED_VERSION} (checksum verified)."
    note_changed
  fi

  section "Register Forgejo runner"

  if forgejo_runner_config_is_managed \
      && [[ "$(stat -c '%U:%G %a' /var/lib/forgejo-runner/config.yaml \
        2>/dev/null || true)" == "root:forgejo-runner 640" ]]; then
    info "Managed same-host runner configuration already up to date."
    note_satisfied
  else
    sed "s|__FORGEJO_HOST__|${runner_host}|g" \
      "${PAYLOAD_DIR}/etc/forgejo-runner-config.yaml" \
      | install -m 640 -o root -g forgejo-runner /dev/stdin \
        /var/lib/forgejo-runner/config.yaml
    ok "Installed conservative same-host runner configuration."
    note_changed
  fi

  if [[ -s /var/lib/forgejo-runner/.runner ]]; then
    info "Runner already registered; skipping registration."
    note_satisfied
  else
    if [[ -f /etc/systemd/system/forgejo-runner.service ]]; then
      systemctl stop forgejo-runner.service \
        || die "Could not stop the existing Forgejo runner before re-registering it." 1
    fi
    rm -f /var/lib/forgejo-runner/.runner
    runner_token="$(runuser -u git -- /usr/local/bin/forgejo \
      --config /etc/forgejo/app.ini --work-path /var/lib/forgejo \
      actions generate-runner-token)"
    if ! runuser -u forgejo-runner -- /usr/local/bin/forgejo-runner \
        -c /var/lib/forgejo-runner/config.yaml register \
        --no-interactive \
        --instance "http://127.0.0.1:${FORGEJO_HTTP_PORT}/" \
        --token "${runner_token}" \
        --name "$(hostname)" \
        --labels "${FORGEJO_RUNNER_LABELS}"; then
      unset runner_token
      die "Forgejo runner registration failed." 1
    fi
    unset runner_token
    [[ -s /var/lib/forgejo-runner/.runner ]] \
      || die "Forgejo runner registration produced an empty state file." 1
    ok "Runner registered against 127.0.0.1:${FORGEJO_HTTP_PORT} with labels: ${FORGEJO_RUNNER_LABELS}"
    note_changed
  fi
  chown forgejo-runner:forgejo-runner /var/lib/forgejo-runner/.runner
  chmod 600 /var/lib/forgejo-runner/.runner
  install -m 644 "${PAYLOAD_DIR}/systemd/forgejo-runner.service" \
    /etc/systemd/system/forgejo-runner.service
  remove_obsolete_forgejo_runner_drop_in
  systemctl daemon-reload
  runner_drop_ins="$(forgejo_runner_drop_in_paths)"
  [[ -z "${runner_drop_ins}" ]] \
    || die "Refusing to start the Forgejo runner with unmanaged systemd drop-ins: ${runner_drop_ins//$'\n'/ }. Reconcile or remove them, then re-run install." 1
  forgejo_runner_uses_managed_config \
    || die "The effective forgejo-runner unit does not load the managed config; inspect systemd drop-ins." 1
  systemctl enable forgejo-runner.service >/dev/null \
    || die "Could not enable forgejo-runner.service." 1
  systemctl restart forgejo-runner.service \
    || die "forgejo-runner service did not start; see journalctl -u forgejo-runner." 1
  if ! retry 6 2 -- forgejo_runner_declared_successfully; then
    systemctl disable --now forgejo-runner.service >/dev/null 2>&1 \
      || warn "Could not disable the runner after its declaration failed."
    die "Forgejo runner did not declare successfully; it was stopped. See journalctl -u forgejo-runner." 1
  fi
  ok "Forgejo Actions runner declared successfully and is enabled."
  # option-sections: forgejo-runner end
}

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

# Render pi-mono runtime configs into /opt/ai-zombie/pi/. Root-owned,
# world-readable; the chat service reads them but does not need to
# mutate them.
install -d -m 755 -o root -g root "${ZOMBIE_DIR}/pi"
install -d -m 750 -o "${AGENT_USER}" -g "${AGENT_USER}" \
  "${ZOMBIE_DIR}/state/logs" "${ZOMBIE_DIR}/state/pi-mono-sessions"
install -m 644 "${PAYLOAD_DIR}/agent/templates/settings.json.tmpl" \
  "${ZOMBIE_DIR}/pi/settings.json"
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

# Ship the built-in skill catalogue to /opt/ai-zombie/skills/
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

# logrotate. The shipped file uses the ``__AGENT_USER__`` placeholder
# so the `create` line names the operator-chosen account (FIX-3-06).
sed -e "s|__AGENT_USER__|${AGENT_USER}|g" \
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
             desktop dev disk files forgejo git hardware hermes-agent html \
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

# Optional component: Forgejo. Detected from the installed config so the
# checks run (or stay silent) regardless of the caller's environment.
if sudo -n test -f /etc/forgejo/app.ini 2>/dev/null; then
  FORGEJO_PORT="\$(sudo -n awk -F' = ' '\$0=="[server]"{s=1;next} /^\\[/{s=0} s && \$1=="HTTP_PORT"{print \$2; exit}' /etc/forgejo/app.ini 2>/dev/null)"
  FORGEJO_PORT="\${FORGEJO_PORT:-3000}"
  FORGEJO_HOST="\$(sudo -n awk -F' = ' '\$0=="[server]"{s=1;next} /^\\[/{s=0} s && \$1=="DOMAIN"{print \$2; exit}' /etc/forgejo/app.ini 2>/dev/null)"
  FORGEJO_DB="\$(sudo -n awk -F' = ' '\$0=="[database]"{s=1;next} /^\\[/{s=0} s && \$1=="NAME"{print \$2; exit}' /etc/forgejo/app.ini 2>/dev/null)"
  FORGEJO_DB="\${FORGEJO_DB:-forgejo}"
  hd "Forgejo (optional component):"
  check "forgejo binary present"             test -x /usr/local/bin/forgejo
  check "forgejo reports a version"          /usr/local/bin/forgejo --version
  check "postgresql active"                  systemctl is-active postgresql
  check "forgejo database \${FORGEJO_DB} present" bash -c "sudo -n runuser -u postgres -- psql -tAc \"SELECT 1 FROM pg_database WHERE datname = '\${FORGEJO_DB}'\" | grep -q 1"
  check "forgejo config directory root:git 750" bash -c "test \"\$(sudo -n stat -c '%U:%G %a' /etc/forgejo)\" = 'root:git 750'"
  check "forgejo app.ini root:git 640"       bash -c "test \"\$(sudo -n stat -c '%U:%G %a' /etc/forgejo/app.ini)\" = 'root:git 640'"
  check "forgejo.service active"             systemctl is-active forgejo.service
  check "forgejo healthy on 127.0.0.1:\${FORGEJO_PORT}" curl -fsS -m 5 -o /dev/null "http://127.0.0.1:\${FORGEJO_PORT}/api/healthz"
  check "caddy binary present"                bash -c "command -v caddy"
  check "caddy.service unit present"          systemctl cat caddy.service
  check "caddy.service enabled"               systemctl is-enabled caddy.service
  check "caddy.service active"               systemctl is-active caddy.service
  check "Caddy configuration valid"           sudo -n caddy validate \
    --config /etc/caddy/Caddyfile --adapter caddyfile
  check "managed Caddy route markers unique"  bash -c \
    "test \"\$(sudo -n grep -Fxc '# BEGIN install.sh Forgejo' /etc/caddy/Caddyfile)\" = 1 \
      && test \"\$(sudo -n grep -Fxc '# END install.sh Forgejo' /etc/caddy/Caddyfile)\" = 1"
  if [[ -n "\${FORGEJO_HOST}" ]]; then
    check "Caddy route host matches \${FORGEJO_HOST}" sudo -n grep -Fqx \
      "https://\${FORGEJO_HOST} {" /etc/caddy/Caddyfile
    check "Caddy route uses internal TLS" sudo -n grep -Eq \
      '^[[:space:]]*tls internal[[:space:]]*$' /etc/caddy/Caddyfile
    check "Caddy route targets 127.0.0.1:\${FORGEJO_PORT}" sudo -n grep -Eq \
      "^[[:space:]]*reverse_proxy 127\\\\.0\\\\.0\\\\.1:\${FORGEJO_PORT}[[:space:]]*$" \
      /etc/caddy/Caddyfile
  fi
  check "legacy Forgejo Caddy fragment absent" sudo -n test ! -e \
    /etc/caddy/conf.d/forgejo.caddy
  check "avahi-daemon.service active"        systemctl is-active avahi-daemon.service
  check "Caddy local CA exported"            sudo -n test -r /etc/forgejo/caddy-local-ca.crt
  check "exported Caddy local CA is current"  sudo -n cmp -s \
    /var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt \
    /etc/forgejo/caddy-local-ca.crt
  if [[ -n "\${FORGEJO_HOST}" ]]; then
    check "forgejo HTTPS healthy at \${FORGEJO_HOST}" sudo -n curl -fsS -m 5 -o /dev/null \
      --cacert /etc/forgejo/caddy-local-ca.crt \
      --resolve "\${FORGEJO_HOST}:443:127.0.0.1" \
      "https://\${FORGEJO_HOST}/api/healthz"
  fi
  if [[ -f /etc/systemd/system/forgejo-runner.service ]]; then
    check "forgejo-runner.service active"    systemctl is-active forgejo-runner.service
    check "runner registration present"      sudo -n test -f /var/lib/forgejo-runner/.runner
  fi
  [[ "\${JSON}" == "1" ]] || echo
fi

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

write_zombie_manifest() {
  write_component_manifest "${COMPONENT_ZOMBIE}" "${SCRIPT_VERSION}" ""
}

write_forgejo_manifest() {
  FORGEJO_URL_HOST="${FORGEJO_URL_HOST:-$(forgejo_product_value host)}"
  FORGEJO_OK=0
  systemctl is-active --quiet forgejo.service && FORGEJO_OK=1
  if (( FORGEJO_OK )); then
    status ok "Forgejo ${FORGEJO_RESOLVED_VERSION:-} running at https://${FORGEJO_URL_HOST}/"
  else
    status warn "Forgejo ${FORGEJO_RESOLVED_VERSION:-} is not running"
  fi
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]]; then
    RUNNER_OK=0
    systemctl is-active --quiet forgejo-runner.service && RUNNER_OK=1
    if (( RUNNER_OK )); then
      status ok "Forgejo Actions runner registered and running"
    else
      status warn "Forgejo Actions runner is not running"
    fi
  fi
  forgejo_suboptions=""
  if [[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
      && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}" \
      && ! forgejo_runner_manifest_present; then
    forgejo_suboptions="runner"
  fi
  write_component_manifest "${COMPONENT_FORGEJO}" \
    "${FORGEJO_RESOLVED_VERSION:-${FORGEJO_VERSION:-}}" "${forgejo_suboptions}"
}

write_forgejo_runner_manifest() {
  RUNNER_OK=0
  systemctl is-active --quiet forgejo-runner.service && RUNNER_OK=1
  if (( RUNNER_OK )); then
    status ok "Forgejo Actions runner registered and running"
  else
    status warn "Forgejo Actions runner is not running"
  fi
  write_component_manifest "${COMPONENT_FORGEJO_RUNNER}" \
    "${FORGEJO_RUNNER_RESOLVED_VERSION:-${FORGEJO_RUNNER_VERSION:-}}" \
    "${FORGEJO_RUNNER_LABELS}"
}

write_llama_manifest() {
  write_component_manifest "${COMPONENT_LLAMA}" \
    "$(llama_catalog_release)" \
    "${LLAMA_MODEL_ID}"
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

final_forgejo_summary() {
  [[ -n "${NEXT_STEP}" ]] || NEXT_STEP="https://${FORGEJO_URL_HOST}/"
  printf 'Forgejo: https://%s/ (LAN mDNS + Caddy local CA%s)\n' \
    "${FORGEJO_URL_HOST}" \
    "$([[ "${ZOMBIE_INSTALL_FORGEJO_RUNNER}" == "1" ]] \
      && ! is_selected_component "${COMPONENT_FORGEJO_RUNNER}" \
      && echo ', runner enabled')"
  printf 'Trust CA: /etc/forgejo/caddy-local-ca.crt\n'
}

final_forgejo_runner_summary() {
  [[ -n "${NEXT_STEP}" ]] || NEXT_STEP="systemctl status forgejo-runner.service"
  printf 'Runner:  Forgejo Actions runner registered and enabled\n'
}

final_llama_summary() {
  [[ -n "${NEXT_STEP}" ]] || NEXT_STEP="llama-manager status"
  printf 'Llama:  http://127.0.0.1:%s/v1 (PC-wide loopback API)\n' "${LLAMA_PORT}"
  printf 'Manage: sudo llama-manager {start|stop|restart|enable|disable|test}\n'
}

for component in "${SELECTED_COMPONENTS[@]}"; do
  component_dispatch_hook "${component}" install
  component_dispatch_hook "${component}" manifest
done
echo

NEXT_STEP=""
INSTALL_DURATION="$(fmt_duration "$(( $(date +%s) - INSTALL_T0 ))")"
printf '\n%s%sInstall complete in %s.%s\n' \
  "${C_GREEN}" "${C_BOLD}" "${INSTALL_DURATION}" "${C_RESET}"
for component in "${SELECTED_COMPONENTS[@]}"; do
  component_dispatch_hook "${component}" final
done
cat <<EOF
Next:    ${C_BOLD}${NEXT_STEP}${C_RESET}
Records: ${LOG_FILE}
         $([[ "${ZOMBIE_RECEIPT}" == "1" ]] && echo "${RECEIPT_FILE}" || echo "receipt disabled")
Remove:  sudo ${SCRIPT_DIR}/uninstall.sh $(selected_components_label) --dry-run
EOF

if is_selected_component "${COMPONENT_ZOMBIE}" && [[ "${NEXT_STEP}" != "sudo reboot" ]]; then
  info "Reboot after completing the next step: sudo reboot"
fi

if (( STEPS_SATISFIED + STEPS_CHANGED > 0 )); then
  info "Idempotent steps: ${STEPS_SATISFIED} already satisfied, ${STEPS_CHANGED} applied this run."
fi

# Finalise the install receipt with the outcome of this run.
write_receipt_finish
