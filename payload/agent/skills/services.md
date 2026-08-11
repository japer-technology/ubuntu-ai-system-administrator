<!-- triggers: services, dependency, dependencies, startup, autostart, restart, restarts, reload, degraded, target, targets, mask, unmask, watchdog -->
# Skill: service dependencies, startup and health

This skill is loaded when the operator asks about service
relationships, startup ordering, recurring failures or coordinated
restarts. Single-unit start/stop/status mechanics are covered by the
`systemd` skill; this brief is about the connections between units.

Operating rules:

- Map before you move. `systemctl list-dependencies <unit>` shows what
  a unit pulls in; `systemctl list-dependencies --reverse <unit>` shows
  what breaks when it stops. Both are `read_only` and auto-run. Quote
  the reverse list to the operator before any restart so the blast
  radius is explicit, not discovered.
- Distinguish *wants* from *requires*. A `Wants=` dependency survives
  the other unit failing; a `Requires=`/`BindsTo=` dependency does not.
  When two services fail together, `systemctl show <unit> -p
  Requires,Wants,After,Before,BindsTo,PartOf` names the coupling.
- `systemctl is-system-running` reporting `degraded` means at least one
  unit has failed. `systemctl --failed` lists them; triage those before
  tuning anything else, because a failed dependency explains most
  "service will not start" reports.
- Startup ordering problems (`After=`/`Before=`) show up as races that
  only bite at boot. `systemd-analyze critical-chain <unit>` and
  `systemd-analyze blame` are `read_only` and answer "why is this slow
  to come up" directly. Do not fix ordering with `sleep` in an
  `ExecStartPre=`; state the missing `After=` instead.
- Health trends live in the journal. `journalctl -u <unit> --since
  -7d --no-pager | grep -c` restart/failure markers, and `systemctl
  show <unit> -p NRestarts,ExecMainStartTimestamp` reveal whether a
  unit is flapping. A service that restarts nightly is not healthy just
  because it is active right now — report the trend, not the snapshot.
- A flapping unit usually means `Restart=` is papering over a real
  fault. Read the exit code (`systemctl show <unit> -p
  ExecMainStatus,Result`) and the last crash in the journal before
  proposing a restart-policy change.
- Coordinated restarts have an order. Restart dependencies bottom-up
  (database before application, network before both) and verify each
  layer (`svc.status`, then a bounded health probe) before touching the
  next. Every `svc.control` action is `system_change` and waits for
  operator approval — batch the plan into one description so the
  operator approves a sequence they have seen in full.
- `systemctl reload` (or `reload-or-restart`) applies configuration
  without dropping connections when the service supports it. Prefer it
  over a full restart, and say when a unit does *not* support reload so
  the operator is not surprised by a restart.
- Masking (`systemctl mask`) is stronger than disabling: it blocks
  manual and dependency starts alike. Use it only when something keeps
  resurrecting a unit, say so explicitly, and record the unmask step in
  the same plan. Never mask `ubuntu-zombie-chat.service`.
- Enabling or disabling a unit at boot (`systemctl enable|disable`) is
  a standing change to the machine, distinct from starting or stopping
  it now. State which of the two the operator asked for; "stop it" does
  not imply "keep it stopped after reboot".
- Watchdog and resource limits (`WatchdogSec=`, `MemoryMax=`,
  `CPUQuota=`) belong in a drop-in (`/etc/systemd/system/<unit>.d/`),
  not in the vendor unit file. Describe the drop-in and ask the
  operator to land it deliberately; then `systemctl daemon-reload`
  before the change takes effect.
- After any reconfiguration, verify with `systemd-analyze verify
  <unit>` and a real status check, and report before/after: what was
  failing, what changed, and what the unit reports now.
