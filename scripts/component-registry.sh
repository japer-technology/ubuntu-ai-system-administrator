#!/usr/bin/env bash

# Shared, data-only component registry helpers. Callers register trusted
# function names, then dispatch through component_dispatch_hook().

PUBLIC_COMPONENTS=()
declare -A COMPONENT_DEPENDENCIES=()
declare -A COMPONENT_HOOKS=()

valid_component_ownership_marker() {
  local path="$1" component="$2"
  [[ -f "${path}" ]] \
    && [[ "$(stat -c '%U:%G %a' "${path}" 2>/dev/null)" == "root:root 644" ]] \
    && grep -Fqx "component=${component}" "${path}" \
    && grep -Fqx 'format=1' "${path}"
}

register_component() {
  local component="$1" dependencies="$2"
  shift 2
  [[ "${component}" =~ ^[a-z][a-z0-9-]*$ ]] \
    || die "Invalid component registry name: ${component}" 2
  [[ -z "${COMPONENT_DEPENDENCIES[${component}]+x}" ]] \
    || die "Duplicate component registry entry: ${component}" 2

  # Dependencies must already be registered. Because dispatch follows
  # registration order, this guarantees every dependency runs before its
  # dependants and makes dependency cycles unrepresentable.
  local dependency
  for dependency in ${dependencies}; do
    [[ "${dependency}" != "${component}" ]] \
      || die "Component '${component}' cannot depend on itself." 2
    [[ -n "${COMPONENT_DEPENDENCIES[${dependency}]+x}" ]] \
      || die "Component '${component}' dependency '${dependency}' must be registered first." 2
  done

  PUBLIC_COMPONENTS+=("${component}")
  COMPONENT_DEPENDENCIES["${component}"]="${dependencies}"

  local entry field hook
  for entry in "$@"; do
    [[ "${entry}" == *=* ]] \
      || die "Invalid registry hook for ${component}: ${entry}" 2
    field="${entry%%=*}"
    hook="${entry#*=}"
    [[ "${field}" =~ ^[a-z_]+$ && "${hook}" =~ ^[a-zA-Z_][a-zA-Z0-9_]*$ ]] \
      || die "Invalid registry hook for ${component}: ${entry}" 2
    [[ -z "${COMPONENT_HOOKS[${component}:${field}]+x}" ]] \
      || die "Duplicate '${field}' hook for component ${component}." 2
    COMPONENT_HOOKS["${component}:${field}"]="${hook}"
  done
}

component_registry_hook() {
  local component="$1" field="$2"
  printf '%s' "${COMPONENT_HOOKS[${component}:${field}]:-}"
}

validate_component_registry() {
  local required_fields="$1" component dependency field hook
  declare -A registered=()
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    registered["${component}"]=1
  done
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    for dependency in ${COMPONENT_DEPENDENCIES[${component}]}; do
      [[ "${dependency}" != "${component}" ]] \
        || die "Component '${component}' cannot depend on itself." 2
      [[ -n "${registered[${dependency}]+x}" ]] \
        || die "Component '${component}' has unknown dependency '${dependency}'." 2
    done
    for field in ${required_fields}; do
      hook="$(component_registry_hook "${component}" "${field}")"
      [[ -n "${hook}" ]] \
        || die "Component '${component}' is missing required '${field}' hook." 2
      declare -F "${hook}" >/dev/null \
        || die "Component '${component}' ${field} hook is not a function: ${hook}" 2
    done
  done
}

# Print the requested components plus every transitive registry dependency,
# one per line, in registry order. Rejects unregistered names.
resolve_component_targets() {
  local component dependency
  declare -A wanted=()
  local -a queue=()
  for component in "$@"; do
    [[ -n "${COMPONENT_DEPENDENCIES[${component}]+x}" ]] \
      || die "Unknown component target '${component}'." 2
    if [[ -z "${wanted[${component}]+x}" ]]; then
      wanted["${component}"]=1
      queue+=("${component}")
    fi
  done
  while (( ${#queue[@]} > 0 )); do
    component="${queue[0]}"
    queue=("${queue[@]:1}")
    for dependency in ${COMPONENT_DEPENDENCIES[${component}]}; do
      if [[ -z "${wanted[${dependency}]+x}" ]]; then
        wanted["${dependency}"]=1
        queue+=("${dependency}")
      fi
    done
  done
  for component in "${PUBLIC_COMPONENTS[@]}"; do
    [[ -n "${wanted[${component}]+x}" ]] && printf '%s\n' "${component}"
  done
  return 0
}

component_dispatch_hook() {
  local component="$1" field="$2"
  shift 2
  local hook
  hook="$(component_registry_hook "${component}" "${field}")"
  [[ -n "${hook}" ]] \
    || die "Component '${component}' is missing required '${field}' hook." 2
  declare -F "${hook}" >/dev/null \
    || die "Component '${component}' ${field} hook is not a function: ${hook}" 2
  "${hook}" "$@"
}
