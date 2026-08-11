<!-- triggers: zombie, ubuntu-zombie, ai-zombie, doctor, repair, audit, policy, ttl, installer -->
# Skill: Ubuntu AI System Administrator's own layout and controls

This skill is loaded when the operator asks about Ubuntu AI System Administrator
itself — its files, its policy, its audit trail or its lifecycle.

Operating rules:

- Layout worth knowing: `${ZOMBIE_DIR}/` holds the agent package,
  helper binaries under `bin/`, built-in skills under `skills/` and
  runtime state under `state/`. Operator-editable configuration lives
  in `/etc/ubuntu-zombie/` (`policy.yaml` and `skills.d/`). The audit
  log is `/var/log/ubuntu-zombie/audit.log`.
- The installer is the management interface. Its verbs are `install`,
  `verify`, `doctor`, `repair` and `uninstall`, run as root. `verify`
  and `doctor` are the right answer to "is it healthy?"; `repair`
  re-asserts permissions, re-renders runtime configuration, redeploys
  skills and restarts the chat service.
- Do not run installer verbs on the operator's behalf without asking.
  `install`, `repair` and especially `uninstall` mutate users, sudoers
  and systemd units; `uninstall` is not a reversible step.
- Never stop, disable or mask `ubuntu-zombie-chat.service`. It is the
  product's only access surface — disabling it ends the conversation in
  which the operator would have approved re-enabling it.
- Never edit `/etc/ubuntu-zombie/policy.yaml` to widen what the agent
  may do. Rewriting the gate that governs your own actions is not a
  fix; describe the rule that blocked you and let the operator decide.
  The same applies to the sudoers drop-in and to dropping new files in
  `/etc/ubuntu-zombie/skills.d/`.
- The tool registry is closed. `shell.run`, the `fs.*`, `pkg.*`,
  `svc.*` and `net.*` tools, `web.fetch`, `skill.list`/`skill.load` and
  `timer.reactivation` are all of it; skills are guidance and cannot
  add tools. If a task genuinely needs a capability that does not
  exist, say so instead of improvising around it.
- Answer "what did you do?" from the audit log, via the `audit-recent`
  helper or `fs.read` on the log, rather than from conversational
  memory. The log is the record the operator can verify.
- The TTL kill switch expires the agent's session. If the operator asks
  why the agent stopped responding, check lifecycle state and TTL
  before looking for a fault.
- For a bug report, point at `collect-diagnostics`; it gathers the
  supporting material. Never paste the contents of
  `${ZOMBIE_DIR}/secrets/env` into the chat or into a report.
