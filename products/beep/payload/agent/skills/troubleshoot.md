<!-- triggers: troubleshoot, troubleshooting, diagnose, diagnosis, debug, broken, failing, failed, slow, stuck, hang, hangs, freeze, unresponsive, sluggish -->
# Skill: diagnosing before changing

This skill is loaded when the operator reports something broken, slow
or failing rather than naming a specific subsystem.

Operating rules:

- Gather state before proposing a change. The `read_only` tools run
  without waiting for approval, so there is no cost to looking first:
  `svc.status` for a unit, `net.status` for interfaces and listening
  ports, `pkg.query` for package state, `fs.read`/`fs.list` for
  configuration, and `shell.run` with `journalctl`, `df -h`, `free -h`
  or `ps` for everything else.
- State one hypothesis before acting. "The unit fails because its
  config references a missing path" is actionable; "let me try
  restarting things" is not.
- Propose one reversible change at a time and say how to undo it. A
  turn that stacks four mutations makes the operator approve a blast
  radius nobody has measured.
- Say which policy class the change falls into and why the operator is
  about to be asked to approve it. `system_change` and
  `network_change` need ordinary approval; `destructive` needs the
  exact confirmation phrase.
- Unrecognised commands are classified `destructive` by the fail-closed
  default. If a proposal trips the confirmation phrase unexpectedly,
  that is a signal to look for a narrower, better-known command rather
  than to talk the operator through confirming it.
- Prefer the typed tools over `shell.run` whenever one exists. The
  observation is cleaner and the audit entry names the operation
  instead of an opaque command string.
- Report negative results explicitly. "The unit is active, disk is at
  41%, and the journal shows no errors since boot" is a useful turn;
  silently moving on to the next guess is not.
- When the cause is outside the machine (an upstream outage, a vendor
  bug, hardware) say so and stop, rather than mutating local state to
  produce the appearance of progress.
