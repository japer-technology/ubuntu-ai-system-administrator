#!/usr/bin/env bash
# shellcheck shell=bash
#
# lib.sh
# ------
# Shared user-experience helpers for the Ubuntu Zombie shell scripts.
#
# This file is *sourced*, never executed directly. It centralises the
# colour/TTY logic, status vocabulary, retry/backoff, timing, spinner,
# and prompt helpers so install.sh, uninstall.sh, build-deb.sh, and the
# payload helpers all present an identical look and behaviour.
#
# Sourcing scripts keep their own `set -Eeuo pipefail`; this library does
# not change shell options so it is safe to source from `set -e` and
# non-`set -e` scripts alike. Helpers that need to exit do so via die().
#
# Colour selection honours, in order:
#   1. ZOMBIE_COLOR=always|never|auto  (or the legacy NO_COLOR=1 -> never)
#   2. the --no-color flag a caller maps onto ZOMBIE_COLOR=never
#   3. auto: colour only when stdout is a TTY.
#
# Status vocabulary (use these everywhere instead of ad-hoc glyphs):
#   info  "[i]"   cyan     neutral progress line
#   ok    "[+]"   green    an action succeeded
#   warn  "[!]"   yellow   non-fatal problem (always shown, to stderr)
#   die   "[x]"   red      fatal; prints and exits
#   status ok|warn|fail "label"   a single checklist bullet:
#                                   [ok] green / [!] yellow / [x] red

# Guard against double-sourcing.
if [[ -n "${_ZOMBIE_LIB_SOURCED:-}" ]]; then
  return 0 2>/dev/null || true
fi
_ZOMBIE_LIB_SOURCED=1

# ---------------------------------------------------------------------------
# Colour / TTY
# ---------------------------------------------------------------------------

# Quiet mode suppresses info/ok/log lines (warnings and errors still show).
ZOMBIE_QUIET="${ZOMBIE_QUIET:-0}"

lib_setup_colors() {
  local mode="${ZOMBIE_COLOR:-auto}"
  local enable=0
  case "${mode}" in
    always) enable=1 ;;
    never)  enable=0 ;;
    auto|*)
      if [[ -n "${NO_COLOR:-}" ]]; then
        enable=0
      elif [[ -t 1 ]]; then
        enable=1
      else
        enable=0
      fi
      ;;
  esac
  if (( enable )); then
    C_RESET=$'\033[0m'; C_BOLD=$'\033[1m'
    C_RED=$'\033[31m'; C_YELLOW=$'\033[33m'
    C_GREEN=$'\033[32m'; C_CYAN=$'\033[36m'
    # Brand / theme accent palette. The primary highlight is Zombie Orchid
    # #AC43D9 (RGB 172,67,217); the others are hand-picked to harmonise with
    # it: a lighter tint, a complementary teal, and a warm magenta. These use
    # 24-bit "truecolor" escapes; terminals without truecolor degrade to the
    # nearest colour and everything still reads cleanly. They honour the same
    # enable/disable policy as the base colours, so --no-color / NO_COLOR /
    # ZOMBIE_COLOR=never blank them out and emit no ANSI at all.
    # C_DIM/C_BRAND*/C_ACCENT/C_MAGENTA are consumed by sourcing scripts.
    # shellcheck disable=SC2034
    {
      C_DIM=$'\033[2m'
      C_BRAND=$'\033[38;2;172;67;217m'      # #AC43D9 primary highlight (orchid)
      C_BRAND2=$'\033[38;2;199;123;230m'    # #C77BE6 lighter tint
      C_ACCENT=$'\033[38;2;67;217;172m'     # #43D9AC complementary teal
      C_MAGENTA=$'\033[38;2;217;67;172m'    # #D943AC warm magenta
    }
  else
    C_RESET=""; C_BOLD=""; C_RED=""; C_YELLOW=""; C_GREEN=""; C_CYAN=""
    # shellcheck disable=SC2034
    {
      C_DIM=""; C_BRAND=""; C_BRAND2=""; C_ACCENT=""; C_MAGENTA=""
    }
  fi
}

# Initialise colours immediately on source; callers that parse a
# --no-color flag re-run lib_setup_colors after setting ZOMBIE_COLOR.
lib_setup_colors

# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

log()  { (( ZOMBIE_QUIET )) || printf '%s\n' "$*"; }
info() { (( ZOMBIE_QUIET )) || printf '%s[i]%s %s\n' "${C_CYAN}" "${C_RESET}" "$*"; }
ok()   { (( ZOMBIE_QUIET )) || printf '%s[+]%s %s\n' "${C_GREEN}" "${C_RESET}" "$*"; }
warn() { printf '%s[!]%s %s\n' "${C_YELLOW}" "${C_RESET}" "$*" >&2; }
die()  { printf '%s[x]%s %s\n' "${C_RED}" "${C_RESET}" "$1" >&2; exit "${2:-1}"; }

# A single checklist bullet with a unified glyph vocabulary. Replaces the
# historical mix of [ok]/[--] and [i]/[!]/[+]/[x] used across scripts.
status() {
  local kind="$1" label="$2"
  case "${kind}" in
    ok)   printf '  %s[ok]%s %s\n' "${C_GREEN}"  "${C_RESET}" "${label}" ;;
    warn) printf '  %s[!]%s  %s\n' "${C_YELLOW}" "${C_RESET}" "${label}" ;;
    fail) printf '  %s[x]%s  %s\n' "${C_RED}"    "${C_RESET}" "${label}" ;;
    info) printf '  %s[i]%s  %s\n' "${C_CYAN}"   "${C_RESET}" "${label}" ;;
    *)    printf '  %s\n' "${label}" ;;
  esac
}

section() {
  printf '\n%s============================================================%s\n' "${C_BOLD}" "${C_RESET}"
  printf '%s%s%s\n' "${C_BOLD}" "$*" "${C_RESET}"
  printf '%s============================================================%s\n' "${C_BOLD}" "${C_RESET}"
}

# ---------------------------------------------------------------------------
# Branded UI helpers (Zombie Orchid theme)
# ---------------------------------------------------------------------------

# brand_rule [width]
#   A thin horizontal rule drawn in the brand highlight colour.
# shellcheck disable=SC2120  # width is optional; callers may omit it
brand_rule() {
  local width="${1:-60}" line=""
  local i
  for (( i = 0; i < width; i++ )); do line+="─"; done
  printf '%s%s%s\n' "${C_BRAND}" "${line}" "${C_RESET}"
}

# brand_banner "Title"
#   A boxed, brand-coloured banner used to frame the setup experience.
brand_banner() {
  (( ZOMBIE_QUIET )) && return 0
  local title="$*"
  printf '\n'
  brand_rule
  printf '%s%s  %s%s\n' "${C_BRAND}" "${C_BOLD}" "${title}" "${C_RESET}"
  brand_rule
}

# _brand_panel_row WIDTH "text" [colour]
#   Internal helper for brand_splash: prints one "│ ... │" row of the panel,
#   left-indented by two spaces and right-padded so the trailing border lines
#   up. "text" is assumed ASCII so its byte length equals its column width.
_brand_panel_row() {
  local width="$1" text="$2" colour="${3:-${C_RESET}}"
  local pad=$(( width - 2 - ${#text} ))
  (( pad < 0 )) && pad=0
  printf '%s│%s  %s%s%s%*s%s│%s\n' \
    "${C_BRAND}" "${C_RESET}" "${colour}" "${text}" "${C_RESET}" \
    "${pad}" "" "${C_BRAND}" "${C_RESET}"
}

# brand_wordmark
#   Compact "UBUNTU ZOMBIE" sign, shared by startup screens.
brand_wordmark() {
  (( ZOMBIE_QUIET )) && return 0
  printf '%s' "${C_BRAND}"
  printf '%s\n' \
'╭──────────────────────────────────╮' \
'│  UBUNTU ZOMBIE                   │' \
'│  AI SYSTEMS ADMINISTRATOR        │' \
'╰──────────────────────────────────╯'
  printf '%s\n' "${C_RESET}"
}

# brand_splash "subtitle" "version"
#   The full-dress startup splash: a compact "UBUNTU ZOMBIE" sign in
#   the Zombie Orchid palette, framed by a rounded panel that states who the
#   account is, the version, and how to reach it. Used to open the installer
#   the way a polished agent CLI greets you. Honours ZOMBIE_QUIET and the
#   colour policy (degrades to plain text with no ANSI).
brand_splash() {
  (( ZOMBIE_QUIET )) && return 0
  local subtitle="${1:-}" version="${2:-}"
  printf '\n'
  brand_wordmark
  # Rounded info panel beneath the wordmark.
  local W=66 line="" i
  for (( i = 0; i < W; i++ )); do line+="─"; done
  printf '%s╭%s╮%s\n' "${C_BRAND}" "${line}" "${C_RESET}"
  _brand_panel_row "${W}" "AI Systems Administrator for Ubuntu Desktop LTS" "${C_BOLD}"
  local tagline="v${version}"
  [[ -n "${subtitle}" ]] && tagline+="  --  ${subtitle}"
  _brand_panel_row "${W}" "${tagline}" "${C_DIM}"
  _brand_panel_row "${W}" ""
  _brand_panel_row "${W}" "Ask the machine to diagnose, explain, configure, repair," "${C_ACCENT}"
  _brand_panel_row "${W}" "and operate itself - every action is audit-logged." "${C_ACCENT}"
  _brand_panel_row "${W}" ""
  _brand_panel_row "${W}" "Chat http://127.0.0.1:7878    You hold the kill switch." "${C_BRAND2}"
  printf '%s╰%s╯%s\n' "${C_BRAND}" "${line}" "${C_RESET}"
}

# field "Label" "value" [accent_color]
#   Render an aligned "label : value" row with a brand-coloured label and an
#   optionally accented value. Used by the parameter review screen so every
#   setting is presented in a consistent, glance-able way.
field() {
  local label="$1" value="$2" vcolor="${3:-${C_ACCENT}}"
  printf '  %s%-22s%s %s%s%s\n' \
    "${C_BRAND2}" "${label}" "${C_RESET}" "${vcolor}" "${value}" "${C_RESET}"
}

# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------

# fmt_duration <seconds>
#   Format a number of seconds as friendly, spelled-out English so timing
#   lines read naturally to an operator, e.g.:
#     0    -> "0 seconds"
#     1    -> "1 second"
#     35   -> "35 seconds"
#     60   -> "1 minute"
#     65   -> "1 minute 5 seconds"
#     3600 -> "1 hour"
#     3725 -> "1 hour 2 minutes 5 seconds"
#   Zero-valued middle/trailing units are omitted ("2 minutes", not
#   "2 minutes 0 seconds") and every unit is correctly singular/plural.
#   Non-numeric or negative input is clamped to 0 so callers never have
#   to sanity-check arithmetic edge cases (e.g. clock skew) themselves.
fmt_duration() {
  local s="${1:-0}"
  [[ "${s}" =~ ^[0-9]+$ ]] || s=0
  local h=$(( s / 3600 )) m=$(( (s % 3600) / 60 )) sec=$(( s % 60 ))
  local -a parts=()
  (( h > 0 ))   && parts+=("${h} $( (( h == 1 ))   && echo hour   || echo hours )")
  (( m > 0 ))   && parts+=("${m} $( (( m == 1 ))   && echo minute || echo minutes )")
  (( sec > 0 )) && parts+=("${sec} $( (( sec == 1 )) && echo second || echo seconds )")
  (( ${#parts[@]} == 0 )) && parts=("0 seconds")
  printf '%s' "${parts[*]}"
}

# ---------------------------------------------------------------------------
# Retry with exponential backoff
# ---------------------------------------------------------------------------
# Usage: retry <attempts> <sleep_base> -- cmd args...
retry() {
  local attempts="$1"; shift
  local base="$1"; shift
  [[ "$1" == "--" ]] && shift
  local n=1 delay="${base}"
  while true; do
    if "$@"; then
      return 0
    fi
    if (( n >= attempts )); then
      warn "Command failed after ${n} attempts: $*"
      return 1
    fi
    warn "Attempt ${n} failed, retrying in ${delay}s: $*"
    sleep "${delay}"
    n=$((n + 1))
    delay=$((delay * 2))
  done
}

# ---------------------------------------------------------------------------
# Spinner / heartbeat for long, otherwise-silent operations
# ---------------------------------------------------------------------------
# run_step "Label" -- cmd args...
#   Runs the command. On an interactive TTY (and when not in quiet mode),
#   shows a braille spinner with elapsed time so the operator can tell the
#   step is making progress rather than hung. On a non-TTY, in quiet mode,
#   or when ZOMBIE_NO_SPINNER=1, it simply runs the command with no
#   animation. Returns the command's exit status.
run_step() {
  local label="$1"; shift
  [[ "${1:-}" == "--" ]] && shift

  # Plain path: non-interactive, quiet, or spinner disabled.
  if [[ ! -t 2 ]] || (( ZOMBIE_QUIET )) || [[ -n "${ZOMBIE_NO_SPINNER:-}" ]]; then
    "$@"
    return $?
  fi

  local -a frames=('⠋' '⠙' '⠹' '⠸' '⠼' '⠴' '⠦' '⠧' '⠇' '⠏')
  local start now elapsed i=0 rc
  start="$(date +%s)"

  "$@" &
  local pid=$!
  while kill -0 "${pid}" 2>/dev/null; do
    now="$(date +%s)"
    elapsed=$(( now - start ))
    printf '\r%s %s%s%s (%s)\033[K' \
      "${frames[i % ${#frames[@]}]}" "${C_CYAN}" "${label}" "${C_RESET}" \
      "$(fmt_duration "${elapsed}")" >&2
    i=$((i + 1))
    sleep 0.2
  done
  wait "${pid}"; rc=$?
  printf '\r\033[K' >&2
  return "${rc}"
}

# ---------------------------------------------------------------------------
# JSON helper
# ---------------------------------------------------------------------------

# json_escape <string> -> escaped contents suitable for a JSON string literal
# (no surrounding quotes). Handles backslash, double-quote, and control
# characters so verify/doctor --json output is always valid.
json_escape() {
  local s="$1"
  s="${s//\\/\\\\}"
  s="${s//\"/\\\"}"
  s="${s//$'\n'/\\n}"
  s="${s//$'\r'/\\r}"
  s="${s//$'\t'/\\t}"
  printf '%s' "${s}"
}

# ---------------------------------------------------------------------------
# Prompt helpers
# ---------------------------------------------------------------------------
# prompt_until_valid "Prompt text: " VALIDATOR_FN OUTVAR [allow_empty]
#   Reads a line, runs VALIDATOR_FN on it, and re-prompts on failure with a
#   clear message instead of aborting the whole run. When allow_empty=1 an
#   empty answer is accepted (and returned) without validation, so callers
#   can offer a "leave blank to skip" escape hatch. The accepted value is
#   stored in the named OUTVAR. Returns non-zero only on EOF/Ctrl-D.
prompt_until_valid() {
  local prompt="$1" validator="$2" outvar="$3" allow_empty="${4:-0}"
  local answer
  while true; do
    if ! read -r -p "${prompt}" answer; then
      return 1
    fi
    if [[ -z "${answer}" ]]; then
      if (( allow_empty )); then
        printf -v "${outvar}" '%s' ""
        return 0
      fi
      warn "A value is required. Please try again (or Ctrl-C to cancel)."
      continue
    fi
    if "${validator}" "${answer}"; then
      printf -v "${outvar}" '%s' "${answer}"
      return 0
    fi
    warn "That did not look valid. Please try again (or Ctrl-C to cancel)."
  done
}
