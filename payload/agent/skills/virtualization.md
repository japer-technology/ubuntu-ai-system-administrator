<!-- triggers: vm, vms, virtualisation, virtualization, hypervisor, kvm, qemu, libvirt, virsh, virt-manager, virtualbox, vagrant, multipass, passthrough -->
# Skill: virtual machines and hypervisors

This skill is loaded when the operator mentions VMs, KVM/QEMU,
libvirt, VirtualBox or Multipass. Containers are the `containers`
skill.

Operating rules:

- Check what is installed and what is running before proposing
  anything: `virsh list --all`, `virsh net-list --all`,
  `vboxmanage list vms runningvms`, `multipass list` and
  `systemctl status libvirtd` are `read_only` and auto-run. Also check
  `lscpu | grep -i virtualisation` and `kvm-ok` — a machine with
  virtualisation disabled in firmware cannot run KVM at all, and that
  is a BIOS/UEFI change only the operator can make.
- Do not mix hypervisors casually. VirtualBox and KVM both want the
  hardware virtualisation extensions; running one while the other holds
  them produces confusing failures. Say which is in use and pick one.
- Membership of `libvirt`, `kvm` or `vboxusers` grants control over
  guests and their disks — effectively broad access to the host's
  storage. Treat adding a user to those groups as a security decision,
  state it plainly, and remember it only takes effect at next login.
- Guest disks are data. `virsh undefine --remove-all-storage`,
  `virsh vol-delete`, `vboxmanage unregistervm --delete` and deleting
  a `.qcow2`/`.vdi` file destroy the guest's filesystem irreversibly;
  they are `destructive` and need the exact confirmation phrase.
  Snapshot or copy first and say where the copy is.
- Forcing a guest off is not a shutdown. `virsh shutdown` asks the
  guest; `virsh destroy` pulls the plug and risks filesystem damage
  inside it. Prefer the graceful verb, say what unsaved state is at
  risk, and never power-cycle a guest the operator did not name.
- Guest images are large and grow. Measure before creating one
  (`df -h` on the storage pool, `qemu-img info` for actual versus
  virtual size), and remember that a thin `qcow2` can outgrow the host
  filesystem long after it was created.
- Guest networking changes the host. A bridge, a NAT network or a
  forwarded port is a `network_change` on this machine and can expose a
  guest service to the LAN. Default to the isolated/NAT network and
  never publish a guest port outward without saying what it exposes.
- Never enable shared clipboard, shared folders, or PCI/USB passthrough
  by default. Each one punches a hole in the isolation the operator
  chose a VM for; describe the trade-off and let them ask.
- Nested virtualisation, GPU passthrough and IOMMU changes touch kernel
  parameters and can leave the host without a display. That is boot
  work — see the `kernel` skill — and a reboot is the test.
- Guest images from the internet are unverified binaries. Prefer an
  official cloud image with a published checksum, verify it, and say
  where it came from.
- A VM is a whole machine with its own patching, its own logs and its
  own snapshots. Do not answer host questions with guest measurements
  or the reverse; say explicitly which one you inspected.
