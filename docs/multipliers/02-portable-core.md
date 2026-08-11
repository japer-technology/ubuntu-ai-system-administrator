# 02 — Portable core vs platform shell

The key architectural observation: Ubuntu Zombie is *already* two
products glued together, and the glue line is exactly where the
porting seam belongs.

## Layer inventory

| Layer | Contents | Portability |
| ----- | -------- | ----------- |
| **Agent core** | `payload/agent/*.py` — server, policy, audit, history, lifecycle, tools, providers, skill loader | **High.** Pure Python 3 standard library + SQLite. Runs on any OS with Python ≥ 3.10. |
| **Node bridges** | `pi-mono-bridge.mjs`, `pi-ai-bridge.mjs`, pinned versions | **High.** Node 22 exists on all three OSes. |
| **Skills & templates** | `payload/agent/skills/`, templates, `payload/etc/policy.yaml` | **Medium.** Content is portable; `apt.md` and `systemd.md` are Ubuntu-specific and need per-OS siblings (`brew`/`launchd`, `winget`/`services`). |
| **Operator helpers** | `payload/bin/` (bash) | **Low.** Need per-OS rewrites or a move into Python. |
| **Service supervision** | `payload/systemd/`, logrotate | **None.** systemd → launchd (macOS) / Windows Service (SCM). |
| **Privilege plumbing** | sudoers drop-in, `zombie` account creation | **None.** Per-OS: sudoers vs. macOS admin/sudoers vs. Windows Administrators group + service account rights. |
| **Provisioning** | apt, NodeSource repo, user creation in `install.sh` | **None.** Per-OS installers own this. |

Roughly: everything under `payload/agent/` multiplies for free;
everything in `scripts/` and `payload/systemd/` is the per-OS cost.

## Platform assumptions currently baked into the core

An audit pass over `payload/agent/` should confirm and then isolate
these before any port starts:

1. **Hard-coded paths.** `/opt/ai-zombie/`, `/etc/ubuntu-zombie/`,
   `/var/log/ubuntu-zombie/`. Fix: a single `paths.py` (or extend the
   existing config surface in
   [`docs/CONFIGURATION.md`](../docs/CONFIGURATION.md)) that resolves
   an OS-appropriate prefix — `/opt/ai-zombie` on Linux,
   `/Library/Application Support/ai-zombie` on macOS,
   `%ProgramData%\ai-zombie` on Windows — overridable by env.
2. **`sudo` as the elevation verb.** The runner executes privileged
   commands via `sudo`. Fix: an `elevation` seam in `runner.py` —
   `sudo` on Linux/macOS, run-as-elevated-service on Windows (where
   the service itself runs with the needed rights and the policy
   gate is the *only* brake — which raises the policy stakes, see
   [`05-windows.md`](05-windows.md)).
3. **Policy classification vocabulary.** `policy.yaml` classifies
   commands like `apt`, `systemctl`, `ufw`. Fix: per-OS policy
   overlays (`policy.linux.yaml`, `policy.darwin.yaml`,
   `policy.windows.yaml`) merged over a shared base of universal
   classes (`rm`, `curl`, filesystem verbs). The action classes
   themselves (`read_only` … `destructive`) are OS-neutral and stay.
4. **Signals, permissions, file modes.** `chmod`/`chown` semantics,
   `0600` receipts. Fix: keep POSIX behaviour on Linux/macOS; map to
   NTFS ACLs on Windows behind the same helper.
5. **systemd health timer.** Fix: launchd `StartInterval` /
   Windows Scheduled Task expressing the same check.

None of these are rewrites; they are extractions of what the code
already does into named seams with per-OS implementations — the same
pattern `provider_from_env()` already uses for LLM providers.

## The contract every platform shell must implement

The platform shell (installer + service manager + privilege setup)
is rewritten per OS, but against one written contract:

1. Create/verify a dedicated, non-human agent account.
2. Grant it controlled elevation (sudoers / admin group / service
   rights) — and nothing else.
3. Stage the payload to the OS-conventional prefix.
4. Render runtime config; install and start the loopback service and
   health check under the native supervisor.
5. Support `install | verify | doctor | repair | uninstall`,
   `--dry-run`, and non-interactive mode with the same exit codes.
6. Write the non-secret receipt and root/Administrator-only secret
   receipt in OS-conventional log locations.
7. Reverse everything on `uninstall`.

This contract is exactly the "optional components" contract already
enforced inside `install.sh` (guarded idempotent sections, receipts,
verify/doctor/repair coverage, uninstall reversal) — promoted from
component level to platform level.

## Repository shape after the split

Following the layout proven in the `lmstudio-vampire` repo's
`packaging/` directory (`common/`, `ubuntu/`, `linux/`, `macos/`,
`windows/`, with build scripts under `scripts/packaging/`):

```
payload/agent/          # unchanged portable core
platform/
  linux/                # today's scripts/install.sh + systemd (moved or wrapped)
  macos/                # launchd plists, pkg scripts, macOS installer
  windows/              # service wrapper, PowerShell installer, MSI/EXE sources
packaging/
  common/               # icons, release metadata, shared smoke test
  ubuntu/               # existing debian/ metadata
  macos/                # pkgbuild/productbuild + Homebrew formula
  windows/              # Inno Setup / WiX sources, winget manifest
```

Migration can be incremental: `debian/` and `scripts/build-deb.sh`
stay where they are until a second platform actually lands; do not
reorganise ahead of need.
