# bash completion for ubuntu-zombie install.sh
#
# Usage:
#   source scripts/completions/install.bash
#
# Completes the verbs, component targets, and flags accepted by scripts/install.sh.
# This is static completion (it does not execute install.sh), so it is safe to
# load from an interactive shell.

_ubuntu_zombie_install() {
  local cur verbs components common_flags uninstall_flags flags seen_verb=""
  cur="${COMP_WORDS[COMP_CWORD]}"

  verbs="install verify doctor repair uninstall"
  components="zombie forgejo forgejo-runner llama"
  common_flags="-h --help -v --version -n --dry-run -y --yes -q --quiet \
                --verbose --debug --no-color --no-colour --strict --json"
  uninstall_flags="--archive --keep-agent"
  flags="${common_flags}"

  local i word used_components=" "
  for (( i = 1; i < COMP_CWORD; i++ )); do
    word="${COMP_WORDS[i]}"
    case "${word}" in
      install|verify|doctor|repair|uninstall)
        [[ -z "${seen_verb}" ]] && seen_verb="${word}" ;;
      zombie|forgejo|forgejo-runner|llama)
        used_components+="${word} " ;;
    esac
  done

  [[ "${seen_verb}" == "uninstall" ]] && flags+=" ${uninstall_flags}"

  if [[ "${cur}" == -* ]]; then
    mapfile -t COMPREPLY < <(compgen -W "${flags}" -- "${cur}")
    return 0
  fi

  if [[ -z "${seen_verb}" ]]; then
    mapfile -t COMPREPLY < <(compgen -W "${verbs} ${common_flags}" -- "${cur}")
    return 0
  fi

  local remaining="" component
  for component in ${components}; do
    [[ "${used_components}" == *" ${component} "* ]] && continue
    remaining+=" ${component}"
  done
  mapfile -t COMPREPLY < <(compgen -W "${remaining} ${flags}" -- "${cur}")
  return 0
}

# Register for the common invocation names.
complete -F _ubuntu_zombie_install install.sh ./install.sh
