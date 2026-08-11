#compdef install.sh
# zsh completion for ubuntu-zombie install.sh
#
# Usage:
#   Put scripts/completions/ on your $fpath, then:
#     autoload -U compinit && compinit
#
# Static completion: it does not execute install.sh.

_ubuntu_zombie_install() {
  local -a verbs components common_flags uninstall_flags flags used_components remaining_components
  local seen_verb component word
  verbs=(
    'install:Install and harden selected components'
    'verify:Check that selected components are healthy'
    'doctor:Diagnose host/config problems for selected components'
    'repair:Re-apply idempotent fixes for selected components'
    'uninstall:Remove selected component configuration'
  )
  components=(
    'zombie:Ubuntu Zombie account, runtime, chat UI, policy, and services'
    'forgejo:Forgejo + PostgreSQL option target'
    'forgejo-runner:Forgejo Actions runner with its Forgejo dependency'
    'llama:Standalone PC-wide llama.cpp server'
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
    '--archive[Archive /opt/ai-zombie before removing it]'
    '--keep-agent[Do not remove the agent user account]'
  )

  seen_verb=''
  used_components=()
  for word in "${words[@]:1:CURRENT-1}"; do
    case "${word}" in
      install|verify|doctor|repair|uninstall) [[ -z "${seen_verb}" ]] && seen_verb="${word}" ;;
      zombie|forgejo|forgejo-runner|llama) used_components+=("${word}") ;;
    esac
  done

  flags=("${common_flags[@]}")
  [[ "${seen_verb}" == 'uninstall' ]] && flags+=("${uninstall_flags[@]}")

  if [[ -z "${seen_verb}" ]]; then
    _arguments -C "${common_flags[@]}" '1:verb:->verb' '*:: :->args'
  else
    remaining_components=()
    for component in "${components[@]}"; do
      # (r) returns the matching array value, so a non-empty result means the
      # component target has already been used and should not be suggested.
      [[ -n "${used_components[(r)${component%%:*}]}" ]] && continue
      remaining_components+=("${component}")
    done
    _arguments -C "${flags[@]}" '*:component:->component'
  fi

  case "${state}" in
    verb)      _describe -t commands 'verb' verbs ;;
    component) _describe -t components 'component' remaining_components ;;
    args)      _arguments "${flags[@]}" ;;
  esac
}

_ubuntu_zombie_install "$@"
