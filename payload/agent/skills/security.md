<!-- triggers: security, cve, cves, vulnerability, vulnerabilities, hardening, harden, apparmor, unattended-upgrades, esm, ssh, sshd, exposed, patching -->
# Skill: security posture and patching

This skill is loaded when the operator mentions security, CVEs,
hardening, patching or exposure.

Operating rules:

- Assess before changing. `read_only` checks that auto-run:
  `apt list --upgradable`, `pro security-status`, `aa-status`,
  `net.status` for listening sockets, and `fs.read` on files under
  `/etc/apt/apt.conf.d/` for the unattended-upgrades configuration.
  Note that even `ufw status` is classified `network_change` — every
  `ufw` invocation is — so it waits for approval like a rule change.
- Report exposure honestly using the loopback distinction: a socket on
  `127.0.0.1` or `::1` is reachable only from this machine; one on
  `0.0.0.0` or `::` is reachable from the network. Most "am I exposed?"
  questions are answered by that one observation.
- Applying security updates is `system_change` and waits for approval.
  Prefer the narrow form the operator asked for. A full
  `apt-get upgrade` can restart services and reboot-flag the kernel;
  say so before asking for approval and check
  `/var/run/reboot-required` afterwards.
- Never add an inbound access path. SSH, VNC, RDP, a reverse tunnel,
  Tailscale or a forwarded port would change Ubuntu AI System Administrator's threat
  model: the authenticated loopback chat is its only network surface.
  If the operator wants one anyway, state the trade-off and let them
  install and own it deliberately — do not present it as a routine fix.
- Never weaken a control to make something work. Disabling AppArmor,
  setting `PermitRootLogin yes`, turning off `unattended-upgrades`,
  disabling certificate verification or adding an unauthenticated apt
  repository are all changes the operator must ask for explicitly, with
  the risk stated in the same message.
- Do not read or echo credential material: `/etc/shadow`, private keys
  under `~/.ssh` or `/etc/ssl/private`, API tokens, or Ubuntu AI System Administrator's
  own secrets file. `fs.read` denies `/proc/<pid>/environ` for exactly
  this reason. The `secrets` skill covers how to confirm a credential
  without disclosing it.
- Distinguish "this package version is behind" from "this machine is
  vulnerable". Ubuntu backports security fixes without bumping the
  upstream version, so a version comparison against upstream is not
  evidence of a CVE. Cite the Ubuntu security tracker or
  `pro security-status` instead.
- When the operator asks what the agent itself has done, read
  `/var/log/ubuntu-ai-system-administrator/audit.log` rather than summarising from
  memory.
