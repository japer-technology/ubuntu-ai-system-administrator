<!-- triggers: zram, zramctl, zram-config, zswap, swap, swapfile, swapfiles, swappiness, hibernate, hibernation -->
# Skill: zram, swap and memory pressure

This skill is loaded when the operator mentions zram, swap files,
swappiness or hibernation.

Operating rules:

- Measure before changing anything. `free -h`, `swapon --show`,
  `zramctl`, `cat /proc/pressure/memory` and
  `journalctl -k -g 'Out of memory' --no-pager` are all `read_only`
  and auto-run. "Add swap" is not a diagnosis; a leaking process or a
  too-small RAM allocation is.
- Know which mechanism is in play. Ubuntu Desktop ships a swap *file*
  at `/swapfile` by default. zram provides a compressed swap device in
  RAM (`/dev/zram0`), configured either by the `systemd-zram-generator`
  package via `/etc/systemd/zram-generator.conf` or by the older
  `zram-config` package. zswap is a kernel compressed cache in front of
  a real swap device — it is not zram, and running both without
  thought wastes memory.
- Prefer `systemd-zram-generator` on modern Ubuntu. Install it
  (`system_change`), then write `/etc/systemd/zram-generator.conf`
  with a `[zram0]` section setting `zram-size` (commonly
  `min(ram / 2, 4096)`) and `compression-algorithm` (`zstd` is a good
  default), and activate with
  `sudo systemctl daemon-reload && sudo systemctl start
  systemd-zram-setup@zram0.service`. `fs.write` cannot reach `/etc`, so
  the file goes through `shell.run` with `sudo`.
- Size zram against real RAM, not a rule of thumb. Half of RAM is a
  common ceiling; more than that can push the system into reclaiming
  memory in order to compress and store it in zram. Report the numbers you used.
- zram wants a higher `vm.swappiness` than a disk swap file — values
  around 100–180 are normal for zram-only systems because swapping to
  RAM is cheap. Set it in `/etc/sysctl.d/` rather than editing
  `/etc/sysctl.conf`, and show the operator the current value
  (`sysctl vm.swappiness`) before and after.
- Removing swap is not free. `sudo swapoff /swapfile` must fit the
  swapped pages back into RAM and can stall or OOM the machine on a
  loaded system; check `free -h` first and say so. Deleting
  `/swapfile` or its `/etc/fstab` entry needs the same care as any
  boot-affecting edit — back the file up and validate.
- Hibernation needs a *disk* swap area at least as large as RAM and a
  matching `resume=` boot parameter. zram cannot back hibernation. If
  the operator wants hibernation, say that plainly rather than
  enlarging zram.
- After a change, prove it: `zramctl`, `swapon --show` and
  `sysctl vm.swappiness` again, and confirm the configuration survives
  a reboot (or tell the operator it will not).
- If the machine is OOM-killing processes, the honest answer is often
  "this workload needs more RAM" or "this process leaks". Compression
  buys headroom; it does not create memory.
