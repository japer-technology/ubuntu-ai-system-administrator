<!-- triggers: log, logs, logging, logfile, dmesg, syslog, kmsg, oom, crash, crashed, backtrace, coredump -->
# Skill: reading logs on Ubuntu

This skill is loaded when the operator mentions logs, the kernel ring
buffer, crashes or out-of-memory events.

Operating rules:

- Reading the journal is `read_only` and runs automatically, so
  inspection is cheap. `journalctl` only leaves that class when it is
  asked to mutate storage (`--rotate`, `--flush`, `--sync`,
  `--vacuum-*`), which is `system_change` and waits for approval.
- Always bound the output and always pass `--no-pager`. Useful shapes:
  `journalctl -u <unit> -n 100 --no-pager`,
  `journalctl -p err -b --no-pager`,
  `journalctl --since '30 min ago' --no-pager`,
  `journalctl -k --no-pager` for the kernel log.
- Never tail unbounded. A bare `journalctl` or `journalctl -f` either
  floods the transcript or never returns; both waste the operator's
  turn budget.
- `-b` is the current boot and `-b -1` the previous one. When the
  operator is investigating a crash or an unexpected reboot, compare
  the two rather than assuming the current boot holds the cause.
- Use `fs.read` for plain log files under `/var/log` — it is on the
  readable allow-list and the observation reports truncation honestly.
  Raise `max_bytes` deliberately rather than reading a rotated log in
  full.
- Compressed rotations (`*.gz`) need `shell.run` with `zcat`/`zgrep`;
  `fs.read` returns their bytes verbatim, not the decompressed text.
- Filter at the source. `journalctl -u <unit> -g <pattern>` or a piped
  `grep` keeps the observation small; pulling ten thousand lines back
  and reasoning over them in the reply does not.
- Logs frequently contain secrets, tokens and personal data. Quote only
  the lines that support the diagnosis and do not echo whole blocks of
  authentication or environment output back into the chat.
- Ubuntu AI System Administrator's own audit log lives at
  `/var/log/ubuntu-zombie/audit.log` and records every tool call. When
  the operator asks "what did you do?", read that rather than
  reconstructing the answer from memory.
