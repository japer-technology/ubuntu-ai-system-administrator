<!-- triggers: backups, snapshot, snapshots, timeshift, rsync, restore, restores, tarball, archive, deja-dup, borg, restic, duplicity, borgmatic, rclone, retention, rotation, offsite -->
# Skill: backups, snapshots and restores

This skill is loaded when the operator mentions backups, snapshots,
restores, retention or backup rotation.

Operating rules:

- Ask what is being protected before choosing a tool. Timeshift
  snapshots the *system* (and by default excludes `/home`); Déjà Dup
  and Borg/Restic protect *user data*; `rsync` and `tar` are the
  general-purpose primitives. Backing up the wrong half is the most
  common failure.
- Inspect first, and say where the space will come from. `df -h` on the
  destination, `du -sh` on the source, and `timeshift --list` or the
  repository's own listing command are `read_only` and auto-run.
- Prefer `rsync -aAXH --info=progress2` for file-level copies: it
  preserves permissions, ACLs, xattrs and hard links. Test with
  `--dry-run` first and show the operator the summary before the real
  run.
- `rsync --delete` makes the destination match the source, which means
  it deletes. Treat any `--delete` run as high blast radius: dry-run
  it, name the files it would remove, and confirm the trailing-slash
  semantics of the source path (`src/` copies contents, `src` copies
  the directory).
- Restores overwrite. Never restore over live data without stating what
  will be replaced and confirming the destination path character by
  character. Prefer restoring to a scratch directory under `/tmp` and
  letting the operator move files into place.
- Timeshift restore and `timeshift --delete` are `destructive`-class
  operations that can roll back or remove system state; they need the
  exact confirmation phrase. Quote that requirement rather than
  reaching for a command that avoids it.
- Databases are not backed up by copying their files. Dump them with
  the engine's own tool while the server runs, and include the dump in
  the file-level backup — see the `database` skill. When orchestrating
  a combined run, order it: dump databases first, then the file-level
  pass that includes the dumps, so one snapshot is internally
  consistent.
- A backup nobody has restored is a hypothesis. After creating one,
  verify it: list the archive (`tar -tzf`, `borg list`,
  `restic snapshots`), check the byte count, run the tool's own
  integrity check where one exists (`borg check`, `restic check` —
  read-only), and restore one file to `/tmp` as a smoke test.
- Periodically rehearse the restore that matters, not just a file:
  restore a directory tree or a database dump into a scratch location
  and confirm the application-level content is usable. Do this as a
  simulation into `/tmp` or a spare directory — never over live data —
  and report what was restored and how long it took, because restore
  time is the number the operator needs during a real incident.
- Rotation and retention are policy, not defaults. Ask (or state) how
  many daily/weekly/monthly copies to keep before pruning anything.
  Express it in the tool's own terms (`borg prune --keep-daily 7
  --keep-weekly 4 --keep-monthly 6`, `restic forget --keep-*`) and
  always `--dry-run`/list first: pruning is deletion of history and is
  high blast radius. Never prune the only remaining copy to free
  space without saying that is what is happening.
- Retention needs a size forecast. Deduplicating tools (Borg, Restic)
  grow with change rate, not source size; show the repository's own
  accounting (`borg info`, `restic stats`) so the operator can see
  whether the destination will hold the policy they chose.
- The 3-2-1 shape (three copies, two media, one offsite) is the
  standard against which to describe any scheme. Do not claim it is
  met when it is not — a second directory on the same disk is one
  copy, and an offsite copy that has never synced is zero.
- Repository passphrases and cloud credentials are secrets. Read them
  from the operator's existing configuration, never echo them into the
  chat, and never write them into a script or a systemd unit in plain
  text.
- Backups on the same disk protect against mistakes, not hardware
  failure. If the destination is a partition of the source drive, say
  so — the operator may believe they are covered when they are not.
- Automate only what the operator asked for. A backup timer that runs
  unattended is a standing change to the machine; describe the schedule
  and retention it implies before landing it, and give the timer a
  failure path — a backup job that fails silently for months is the
  worst outcome, so check `systemctl list-timers` and the unit's last
  result when asked whether backups "are working".
