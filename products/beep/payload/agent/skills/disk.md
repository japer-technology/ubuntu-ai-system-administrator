<!-- triggers: disk, disks, storage, df, du, lsblk, partition, partitions, mount, unmount, fstab, lvm, inode, inodes, filesystem -->
# Skill: disk, storage and filesystem work

This skill is loaded when the operator mentions disk space, block
devices, mounts or filesystems.

Operating rules:

- Diagnose first; every useful measurement is `read_only` and
  auto-runs: `df -h`, `df -i` for inode exhaustion, `lsblk`,
  `findmnt`, `blkid`, and `du -x --max-depth=1 /var | sort -h` to walk
  down to the offending directory.
- `du -x` stays on one filesystem. Without it a scan of `/` wanders
  into `/proc`, `/sys` and network mounts and returns numbers that mean
  nothing.
- Recovering space safely, in order of preference: `sudo apt-get clean`
  and `sudo apt-get autoremove`, `sudo journalctl --vacuum-size=200M`,
  then old kernels and stale files under `/var/tmp`. All of these are
  `system_change` and wait for approval.
- Never free space with a recursive forced delete. `rm -rf`, `shred`,
  `truncate -s 0`, `mkfs`, `wipefs`, `blkdiscard`, `parted` and
  `dd of=/dev/…` are `destructive` and require the exact confirmation
  phrase — quote the phrase requirement to the operator instead of
  looking for a formulation that avoids it.
- Do not edit `/etc/fstab` blind. Read it with `fs.read` first, explain
  the change, and remind the operator that a bad entry can leave the
  machine unbootable. `fs.write` cannot reach `/etc` anyway — it only
  writes under `/tmp` and the beep state directory — so the operator
  must land the edit deliberately.
- Before proposing a mount or unmount, check what is using the path
  (`findmnt`, `lsof +f -- <path>`). Unmounting a filesystem out from
  under a running service is a user-visible outage.
- Full root filesystems can make services fail in confusing ways. When
  the operator reports a service failing, check `df -h` early; it is
  one cheap read and it explains a large share of Ubuntu Desktop
  breakage.
- Report free space in the same units the operator used, and always say
  which mount point the number belongs to. "12 GB free" without "on
  `/`" invites the wrong decision.
