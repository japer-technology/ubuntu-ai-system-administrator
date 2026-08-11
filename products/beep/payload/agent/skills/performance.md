<!-- triggers: performance, cpu, memory, ram, load, iotop, htop, benchmark, throttling, bottleneck, latency, throughput, profiling -->
# Skill: performance triage

This skill is loaded when the operator asks why the machine is heavy,
what is consuming resources, or how to make something faster. Once a
specific process or tree is the suspect, the `process` skill covers
attribution, containment and safe termination.

Operating rules:

- Name the resource before proposing a fix. CPU, memory, disk I/O and
  network are four different problems with four different remedies;
  "it's slow" is a symptom. Say which one the measurements point to.
- The cheap first pass is all `read_only` and auto-runs:
  `uptime` for load average, `ps aux --sort=-%cpu | head -15`,
  `ps aux --sort=-%rss | head -15`, `free -h`, `vmstat 1 5`,
  `iostat -xz 1 5` (from `sysstat`) and
  `cat /proc/pressure/{cpu,io,memory}` for PSI. Bound every sampling
  command with a count so it terminates.
- Read load average against core count (`nproc`). A load of 4 on an
  8-core machine is not a problem; the same load on 2 cores is.
- Distinguish memory *used* from memory *unavailable*. Linux uses free
  RAM for cache by design; the number that matters in `free -h` is
  `available`. Quote it rather than alarming the operator with `used`.
- Interactive-only tools (`top`, `htop`, `iotop -o`, `atop`) need a
  batch form or they hang the turn: `top -b -n 1`, `iotop -b -n 2`.
  Never launch a plain interactive TUI through `shell.run`.
- Check the boring causes early: a full or nearly full filesystem
  (`df -h`), a thermally throttled CPU
  (`grep MHz /proc/cpuinfo`, `sensors`), swap thrashing, a stuck
  `apt`/`snapd` refresh, or a runaway browser tab. Desktop "slowness"
  is far more often one of these than a tuning deficiency.
- Boot slowness has its own tools: `systemd-analyze`,
  `systemd-analyze blame` and `systemd-analyze critical-chain`. Both
  are read-only and answer the question directly.
- Prefer removing the cause to tuning around it. Disabling a service
  that is genuinely doing work, raising limits, or setting a governor
  to `performance` all have costs — state them, including battery and
  thermal impact on a laptop.
- Never `kill -9` as an opening move. Identify the process, check what
  it belongs to (`systemctl status <pid>`), try a graceful stop, and
  tell the operator what unsaved state is at risk. Killing a desktop
  session process logs the operator out.
- Measure again after the change and report both numbers. A performance
  claim without a before and an after is an assertion, not a result.
