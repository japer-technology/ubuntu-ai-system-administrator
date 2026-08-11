# 01 — Current state of the delivery mechanism

Before multiplying anything, be precise about what exists and works
today. Everything below is verifiable in this repository. **This
document is the blueprint**: the fully functional mechanism described
here — portable core, platform shell, two-stage delivery, and the
invariants table — is exactly what the rest of this series
([`02`](02-portable-core.md)–[`07`](07-roadmap.md)) multiplies across
packages, platforms, and delivery channels.

## What the product is

Ubuntu Zombie installs a private, root-capable AI Systems
Administrator on Ubuntu Desktop LTS
([`docs/VISION.md`](../docs/VISION.md)). The installed shape
([`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md)):

- A dedicated Linux account (`zombie` by default) with passwordless
  `sudo` — the agent's operating identity.
- A Python chat service under `/opt/ai-zombie/agent/` served on
  `127.0.0.1:7878`, driving pi-mono Node bridges. The chat is
  password-protected, TTL-limited, streams live turn progress over
  server-sent events, and carries a full slash-command catalogue.
- A policy gate (`policy.py`), audit log (`audit.py`), SQLite
  history, TTL lifecycle, and a bounded `timer.reactivation`
  self-continuation tool.
- systemd units (chat service plus a health-check timer), a sudoers
  drop-in, logrotate rules, and operator helpers under
  `/opt/ai-zombie/bin/` (`verify`, `secrets-edit`, `health-check`,
  `audit-recent`, `collect-diagnostics`, `llama-manager`,
  `zombie-chat`, ...).
- Optional, individually installable components behind the same
  lifecycle: a self-hosted **Forgejo** forge (PostgreSQL, Caddy
  internal-CA HTTPS, optional Actions runner) and a standalone
  **llama.cpp** server on `127.0.0.1:8080` with a verified default
  model, so the product can run fully offline with no cloud key.

## How it is delivered today

Three mechanisms, in increasing order of polish:

1. **Git clone + script.** `sudo ./scripts/install.sh install`. The
   installer is ~4,800 lines of bash (plus shared libraries
   [`scripts/lib.sh`](../scripts/lib.sh) and
   [`scripts/component-registry.sh`](../scripts/component-registry.sh)):
   idempotent, dry-run capable, fully non-interactive with
   `ZOMBIE_NONINTERACTIVE=1`, and paired with `verify`, `doctor`,
   `repair`, and `uninstall` verbs. Every verb also accepts explicit
   component targets (`zombie`, `forgejo`, `llama`) dispatched
   through a component registry, so components install, verify, and
   uninstall independently.
2. **Release tarball.** `make package` produces
   `dist/ubuntu-zombie-$(VERSION).tar.gz` containing the same tree.
3. **Stage-1 `.deb`, shipped and signed.** `make deb`
   ([`scripts/build-deb.sh`](../scripts/build-deb.sh),
   [`debian/`](../debian/README.md)) builds
   `ubuntu-zombie_<version>_all.deb` with raw `dpkg-deb`. It stages
   the tree under `/usr/share/ubuntu-zombie/` and installs a
   `/usr/sbin/ubuntu-zombie` wrapper. It deliberately does **not**
   run the installer at `apt install` time; the operator runs
   `sudo ubuntu-zombie install` afterwards. This is no longer just a
   local build: every GitHub Release publishes the `.deb` alongside
   a `SHA256SUMS` file, keyless cosign signatures, and SLSA
   provenance ([`.github/workflows/release.yml`](../.github/workflows/release.yml)).

So the "just a Deb file" ambition is already half real: apt can
install the released, signed bits, and one command activates them.
The gap between today and the ideal is analysed in
[`03-linux-packaging.md`](03-linux-packaging.md).

## Why the two-stage split exists — and why it must survive porting

The installer mutates users, sudoers, systemd units, and package
state, and (for optional components) network-listening services.
Package managers run maintainer scripts unattended, often during
unrelated upgrade runs. Activating a root-capable agent from a
`postinst`/`.pkg` script/MSI custom action would:

- violate the "explicit human approval" promise in the vision;
- break on machines where required env (API keys) is absent;
- make `apt upgrade` a security-relevant event.

Every platform artifact proposed in this analysis therefore keeps
the split: **stage 1** = files on disk plus a wrapper command;
**stage 2** = an explicit, attended (or explicitly non-interactive)
activation that produces a receipt and is reversible.

## Properties the current mechanism has that ports must keep

| Property | Where it lives today |
| -------- | -------------------- |
| Idempotent converge-on-rerun | `scripts/install.sh` throughout |
| Non-interactive mode (exit `64` on missing env) | `ZOMBIE_NONINTERACTIVE=1` paths |
| Dry-run preview | `--dry-run` |
| State inspection and self-repair | `verify` / `doctor` / `repair` |
| Per-component lifecycle | `scripts/component-registry.sh`; `<verb> [zombie|forgejo|llama]` |
| Full reversal | `scripts/uninstall.sh` |
| Non-secret receipt + root-only secret receipt | `/var/log/ubuntu-zombie/` |
| Policy gate + audit before privilege | `payload/agent/policy.py`, `audit.py` |
| Loopback-only default surface | chat service binds `127.0.0.1` |
| Signed, checksummed release artifacts | `SHA256SUMS` + cosign bundles per release |

## What is explicitly unsupported today

Per [`docs/PLATFORMS.md`](../docs/PLATFORMS.md): supported means
Ubuntu Desktop 22.04/24.04 LTS on `amd64` (CI-exercised); `arm64`
and non-Ubuntu-Desktop flavours are best-effort. Everything else —
Ubuntu Server, Debian derivatives, non-LTS releases, WSL, and
containers without systemd — is unsupported. macOS and Windows are
not merely unsupported, they are unmentioned. That document becomes
the place where new platform tiers are declared as ports land.
