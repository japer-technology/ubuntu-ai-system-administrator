# Multipliers — multiplying Ubuntu Zombie across platforms

This directory is an **analysis and design surface**, in the same
spirit as [`options/`](../options/README.md). It holds no runnable
code. It answers one question:

> How do we take the existing, working Ubuntu installation mechanism
> (`scripts/install.sh` + `payload/`) and multiply it across Windows
> and macOS, with cleaner, native delivery mechanisms (`.deb`, `.pkg`,
> `.exe`/MSI) instead of a long attended script run?

## The one-paragraph answer

The product is already split into a **portable core** (the Python
chat service under [`payload/agent/`](../payload/agent/)) and a
**platform shell** (the bash installer, systemd units, sudoers
drop-in and apt/NodeSource provisioning). The core can run anywhere
Python runs. The shell cannot and should not be ported line-by-line;
each OS gets a native shell that honours the same contract —
dedicated agent account, policy gate, audit log, idempotent
`install/verify/doctor/repair/uninstall` lifecycle, non-interactive
mode, receipts, and reversibility. Delivery then becomes a thin
per-platform packaging layer over that contract: a **stage-1
package** (already shipped for Ubuntu as `make deb`) that stages
files and a wrapper command, followed by an attended (or
`ZOMBIE_NONINTERACTIVE=1`) activation step. Two sibling
japer-technology projects already prototype the pieces: the
`lmstudio-vampire` repo's `packaging/` tree shows the per-platform
artifact layout, and the `forgejo-society` repo's
`FORGEJO-SOCIETY-INSTALLATION/` library shows the tiered
entry-point documentation model.

## Files in this directory

| File | Contents |
| ---- | -------- |
| [`01-current-state.md`](01-current-state.md) | What the delivery mechanism is today, and why it works. |
| [`02-portable-core.md`](02-portable-core.md) | What is portable, what is platform-specific, and the abstraction seam between them. |
| [`03-linux-packaging.md`](03-linux-packaging.md) | Finishing the Linux story: stage-2 `.deb`, apt repository, Debian-family support, snap/flatpak verdicts. |
| [`04-macos.md`](04-macos.md) | macOS port: launchd, hidden service account, `.pkg`, Homebrew, signing and notarisation. |
| [`05-windows.md`](05-windows.md) | Windows port: Windows Service, MSI/EXE via Inno Setup or WiX, winget, the UAC privilege model. |
| [`06-delivery-patterns.md`](06-delivery-patterns.md) | Cross-cutting delivery patterns and prior art from `forgejo-society` and `lmstudio-vampire`. |
| [`07-roadmap.md`](07-roadmap.md) | Phased roadmap, effort ordering, risks, and explicit non-goals. |

## Ground rules carried over from the trust model

Whatever the platform or the artifact format, these do not bend:

1. A package install **stages** files; it never silently activates a
   root-capable agent. Activation is a separate, explicit, logged,
   operator-approved step (the stage-1/stage-2 split proven by
   [`debian/README.md`](../debian/README.md)).
2. Every privileged action on every OS goes through the policy gate
   ([`payload/agent/policy.py`](../payload/agent/policy.py)) and the
   audit log ([`payload/agent/audit.py`](../payload/agent/audit.py)).
3. Installs are idempotent, verifiable (`verify`/`doctor`/`repair`),
   non-interactive-capable, receipted, and reversible on every OS.
4. The chat service binds loopback only, on every OS, by default.
