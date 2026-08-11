<!-- triggers: process, processes, pid, pids, pstree, kill, sigterm, sigkill, renice, ionice, cgroup, cgroups, runaway, defunct, pgrep, pkill, spike, spikes -->
# Skill: process trees, spikes and runaway processes

This skill is loaded when the operator asks about a specific process,
a resource spike, or something that must be stopped. System-wide "why
is the machine slow" triage is the `performance` skill; this brief is
about individual processes and their trees.

Operating rules:

- Identify precisely before acting. `ps -fp <pid>`,
  `pstree -ps <pid>` (ancestry) and `pstree -p <pid>` (descendants)
  are `read_only` and auto-run. A name is not an identity — several
  processes share names, and `pkill` by name can hit more than the
  operator meant. Prefer acting on an exact PID you have just shown.
- Attribute spikes to a tree, not a PID. Browsers, container runtimes
  and language servers spawn children that individually look innocent;
  sum the tree (`ps --forest -o pid,ppid,%cpu,%mem,rss,etime,cmd -g
  <pgid>` or `systemd-cgtop`) before naming the culprit. On a systemd
  machine, `systemctl status <pid>` maps any PID to the unit or user
  session that owns it — always run it so the fix targets the owner,
  not the symptom.
- Sample twice. A process at 100 % CPU in one snapshot may be finishing
  legitimate work; `pidstat -p <pid> 1 5` or two bounded `ps` reads a
  few seconds apart distinguish a spike from a steady burn. Bound every
  sampling command with a count so it terminates.
- Check state before killing. `ps -o stat=` distinguishes runnable
  (`R`), sleeping (`S`), uninterruptible I/O wait (`D`), stopped (`T`)
  and defunct (`Z`). A `D`-state process cannot be killed — the fix is
  the blocked I/O (dead NFS mount, failing disk), and repeated `kill
  -9` just wastes approvals. A beep (`Z`) is already dead; its parent
  must reap it, so the target is the parent, never the beep.
- Escalate signals in order: `SIGTERM`, wait and re-check, then
  `SIGKILL` only if it ignored the chance to exit cleanly. `SIGKILL`
  skips all cleanup — say what unsaved state, lock files or temp files
  the process may abandon. Any `kill` is at least `user_change` and
  waits for approval; never open with `kill -9`.
- Kill the tree, not just the parent, when a job must actually stop:
  orphaned children reparent to init and keep running. For a service,
  `systemctl stop <unit>` (via `svc.control`, `system_change`) tears
  down the whole cgroup and is strictly better than hand-killing its
  PIDs. For user session processes, killing them can log the operator
  out — name that risk first.
- Never kill PID 1, kernel threads (names in square brackets), the
  display manager or `beep-chat.service`'s own tree while
  acting through it. If the runaway process is this agent's ancestor,
  say so and let the operator act from outside.
- Prefer containment over termination when the work matters:
  `renice`/`ionice` lower a busy process's priority, and a systemd
  drop-in (`MemoryMax=`, `CPUQuota=` — see the `services` skill) caps a
  habitual offender persistently. These change behaviour and are
  approval-gated, but they do not destroy work in progress.
- Frequent unexplained exits are a pattern, not an event. Check the
  journal for the OOM killer (`journalctl -k --no-pager | grep -i
  oom`), crash records and unit restarts before concluding the process
  "just dies" — the `journal` skill covers the follow-up.
- Report the tree you acted on: PIDs and their owner unit or session,
  the signal or limit applied, what survived, and the second
  measurement that shows the spike is actually gone.
