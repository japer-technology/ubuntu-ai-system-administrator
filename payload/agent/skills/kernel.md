<!-- triggers: kernel, kernels, module, modules, modprobe, grub, initramfs, initrd, boot, bootloader, uefi, secureboot, sysctl, hwe, dkms -->
# Skill: kernel, modules and boot

This skill is loaded when the operator mentions the kernel, kernel
modules, boot, GRUB or sysctl tuning.

Operating rules:

- Establish the current state first: `uname -r`, `dpkg -l 'linux-image-*'`,
  `lsmod`, `cat /proc/cmdline` and `journalctl -k -b --no-pager` are
  `read_only` and auto-run. Say which kernel is running versus which is
  installed — they differ after every kernel upgrade until reboot.
- Ubuntu LTS desktops track the HWE kernel
  (`linux-generic-hwe-<release>`). Do not pin, hold or install a
  mainline kernel to chase a fix without saying what the operator gives
  up: HWE kernels receive Ubuntu security updates, mainline builds do
  not.
- Never remove the running kernel or the last remaining kernel.
  `sudo apt-get autoremove --purge` is the supported way to clear old
  kernels; check `uname -r` against the removal list and quote it back
  before the operator approves.
- Anything that edits `/etc/default/grub` or files under
  `/etc/grub.d/` can make the machine unbootable. Read the file first,
  show the exact one-line change, keep a timestamped `.bak`, and run
  `sudo update-grub` so the generated config is regenerated. Recovery
  from a bad boot line needs physical access — say so.
- Boot parameters are a last resort, not a first fix. Prefer a driver
  or firmware update over `nomodeset`, `acpi=off` or `pci=noaer`, and
  state the trade-off when a parameter is genuinely needed.
- Kernel modules: inspect with `modinfo` and `lsmod`, load with
  `sudo modprobe <mod>` for a live test, and persist with a file under
  `/etc/modules-load.d/` or `/etc/modprobe.d/` only after the live test
  worked. Blacklisting a module that a disk or network device depends
  on is a boot failure in waiting.
- Out-of-tree modules (`dkms`) rebuild per kernel. After a kernel
  upgrade, check `dkms status` before declaring the upgrade clean, and
  remember that Secure Boot requires those modules to be signed —
  `mokutil --sb-state` reports whether it is enforcing.
- Rebuild the initramfs (`sudo update-initramfs -u`) after changing
  anything it embeds: crypto keys, modprobe rules, resume settings.
  Skipping it produces a system that boots from a stale image and
  "ignores" the change.
- `sysctl` changes: test with `sudo sysctl -w key=value`, persist in a
  file under `/etc/sysctl.d/` rather than editing `/etc/sysctl.conf`,
  and report the previous value so the operator can revert.
- After any boot-affecting change, tell the operator plainly that a
  reboot is the test, and offer the rollback command before they
  reboot rather than after.
