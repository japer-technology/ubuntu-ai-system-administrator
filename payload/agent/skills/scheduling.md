<!-- triggers: cron, crontab, anacron, timer, timers, schedule, scheduled, scheduling, systemd-run, recurring -->
# Skill: scheduled and recurring work

This skill is loaded when the operator mentions cron, systemd timers,
or anything that should run on a schedule.

Operating rules:

- Look at what already runs before adding more:
  `systemctl list-timers --all`, `crontab -l`, `sudo crontab -l -u
  <user>`, and `ls /etc/cron.{d,daily,weekly,monthly}` are `read_only`
  and auto-run. A duplicate job is worse than a missing one.
- Prefer a systemd timer to a cron entry on Ubuntu: it is logged in the
  journal, has `Persistent=true` for missed runs on a laptop,
  supports `RandomizedDelaySec`, and its status is inspectable with
  `systemctl status <name>.timer`. Use cron when the operator already
  standardised on it.
- New units under `/etc/systemd/system/` are a system change and cannot
  be written with `fs.write`. Show the full unit text, land it through
  `shell.run` with `sudo`, then `sudo systemctl daemon-reload` and
  `sudo systemctl enable --now <name>.timer`. Validate with
  `systemd-analyze verify` and confirm the next elapse with
  `systemctl list-timers <name>.timer`.
- Cron's environment is not a login shell: no `PATH` beyond a minimal
  default, no profile, no display. Use absolute paths, redirect output
  explicitly, and remember that `%` is special in a crontab and must be
  escaped.
- Test the command by hand first, exactly as the schedule will run it.
  A job that only works interactively fails silently at 03:00, and the
  operator finds out weeks later.
- Say what the schedule costs. A minutely job that runs `apt-get
  update`, walks a filesystem, or hits the network is a standing load
  and a standing risk; propose the longest interval that meets the need.
- Never schedule anything that would require operator approval when run
  interactively. A timer that runs a `system_change` or `destructive`
  command unattended moves that decision outside the approval gate —
  describe it and let the operator land it deliberately.
- Do not schedule Ubuntu Zombie's own agent activity through cron.
  Bounded continuations belong to `timer.reactivation`, which stays
  inside the conversation, the audit log and the TTL kill switch.
- Removing a job is a change too. Show the exact entry or unit you
  propose to delete, keep a copy under `/tmp`, and confirm nothing else
  (a backup, a certificate renewal) depended on it.
- Verify after landing: `systemctl list-timers`, then read the first
  real run in the journal (`journalctl -u <name>.service --no-pager`)
  rather than assuming success.
