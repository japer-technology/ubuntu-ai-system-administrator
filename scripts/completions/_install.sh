#compdef install.sh
# zsh completion for ubuntu-ai-system-administrator install.sh
#
# Usage:
#   Put scripts/completions/ on your $fpath, then:
#     autoload -U compinit && compinit
#
# Static completion: it does not execute install.sh.

_ubuntu_ai_system_administrator_install() {
  local -a verbs common_flags uninstall_flags flags
  local seen_verb word
  verbs=(
    'install:Install and harden Ubuntu AI System Administrator'
    'verify:Check that Ubuntu AI System Administrator is healthy'
    'doctor:Diagnose Ubuntu AI System Administrator host and configuration problems'
    'repair:Re-apply idempotent Ubuntu AI System Administrator fixes'
    'uninstall:Remove Ubuntu AI System Administrator configuration'
  )
  common_flags=(
    '(-h --help)'{-h,--help}'[Show help and exit]'
    '(-v --version)'{-v,--version}'[Print version and exit]'
    '(-n --dry-run)'{-n,--dry-run}'[Preview actions without changing the host]'
    '(-y --yes)'{-y,--yes}'[Skip the YES confirmation gate]'
    '(-q --quiet)'{-q,--quiet}'[Only print warnings and errors]'
    '--verbose[Trace execution to the transcript]'
    '--debug[Trace execution to the transcript]'
    '--no-color[Disable coloured output]'
    '--no-colour[Disable coloured output]'
    '--strict[Treat preflight warnings as errors]'
    '--json[Machine-readable output for verify/doctor]'
  )
  uninstall_flags=(
    '--archive[Archive the install root before removing it]'
    '--keep-agent[Do not remove the agent user account]'
  )

  seen_verb=''
  for word in "${words[@]:1:CURRENT-1}"; do
    case "${word}" in
      install|verify|doctor|repair|uninstall) [[ -z "${seen_verb}" ]] && seen_verb="${word}" ;;
    esac
  done

  flags=("${common_flags[@]}")
  [[ "${seen_verb}" == 'uninstall' ]] && flags+=("${uninstall_flags[@]}")

  if [[ -z "${seen_verb}" ]]; then
    _arguments -C "${common_flags[@]}" '1:verb:->verb' '*:: :->args'
  else
    _arguments -C "${flags[@]}"
  fi

  case "${state}" in
    verb) _describe -t commands 'verb' verbs ;;
    args) _arguments "${flags[@]}" ;;
  esac
}

_ubuntu_ai_system_administrator_install "$@"
