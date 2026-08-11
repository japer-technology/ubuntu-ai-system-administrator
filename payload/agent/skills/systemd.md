<!-- triggers: systemd, systemctl, service, unit, journal, journalctl, daemon -->
# Skill: systemd service management

This skill is loaded when the operator mentions systemd, services,
units, or the journal. Dependency analysis, startup ordering, health
trends and coordinated multi-unit restarts are covered in more depth
by the `services` skill.

Operating rules:

- Use `svc.status` (wraps `systemctl status` / `is-active`) to inspect
  a unit before suggesting changes. It is `read_only` and runs
  automatically.
- Use `svc.control` for `start`, `stop`, `restart`, `enable`,
  `disable`. It is `system_change` and requires operator approval.
- Reading the journal is `read_only`; prefer
  `shell.run` with `journalctl -u <unit> -n 100 --no-pager` over
  unbounded tails. Always include `--no-pager` so the output is
  captured.
- Never disable `ubuntu-zombie-chat.service` without explicit operator
  approval; it is the product's only access surface.
- For new units, do not write directly into `/etc/systemd/system/`;
  describe the change and ask the operator to land it through the
  installer or a configuration management workflow.
- When restarting a unit, summarise what depends on it (use
  `systemctl list-dependencies --reverse`) so the operator can weigh
  the blast radius before approving.
