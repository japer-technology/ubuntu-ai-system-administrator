# 07 — Roadmap, risks, and non-goals

## Sequencing principle

Do the cheap multiplier first (Linux polish), extract the seams
second (they de-risk both ports), then port in order of proximity
(macOS before Windows). Never let a port fork the agent core.

## Phase 0 — Linux delivery polish (no porting)

1. Move `.deb` build to debhelper; keep `make deb` as the entry.
2. Sign packages; publish an apt repository from CI on tag.
3. Decide the Debian-derivative stance
   ([`03-linux-packaging.md`](03-linux-packaging.md)).
4. Adopt the `packaging/common/` shared-asset + clean-VM smoke-test
   discipline from `lmstudio-vampire`.

Exit: `sudo apt install ubuntu-zombie` works from a hosted repo.

## Phase 1 — extract the portability seams (still Ubuntu-only)

1. Centralise path resolution; remove hard-coded `/opt`, `/etc`,
   `/var/log` literals from `payload/agent/`.
2. Introduce the elevation seam in `runner.py`.
3. Split `policy.yaml` into shared base + `policy.linux.yaml`.
4. Write down the platform-shell contract
   ([`02-portable-core.md`](02-portable-core.md)) as a testable
   document, and add core unit runs to CI on macOS and Windows
   runners (python compile + agent tests only — proving core
   portability continuously *before* any shell exists).

Exit: Ubuntu behaviour unchanged (`make lint`/`make test`/container
install all green); agent core compiles and passes tests on all
three OS runners.

## Phase 2 — macOS port

Per [`04-macos.md`](04-macos.md): platform shell, launchd, hidden
account, `policy.darwin.yaml`, skills, `.pkg` + Homebrew tap,
signing/notarisation, TCC walkthrough, PLATFORMS.md tier.

Exit: `brew install` + `sudo mac-zombie install` on a clean macOS VM
passes the ported smoke suite; `.pkg` notarised.

## Phase 3 — Windows port

Per [`05-windows.md`](05-windows.md): policy/de-elevation design
review **first**, then service wrapper, PowerShell shell,
`policy.windows.yaml`, skills, PyInstaller + Inno EXE, signing,
winget manifest.

Exit: signed EXE installs, activates via explicit opt-in, and
passes the ported smoke suite on a clean Windows VM.

## Phase 4 — convergence

1. Unified release job: one tag → deb + apt repo, pkg + tap bump,
   exe + winget PR, checksums + attestations.
2. Tiered per-platform doc ladder + checklist index, following the
   `forgejo-society` documentation model
   ([`06-delivery-patterns.md`](06-delivery-patterns.md)).
3. Naming decision: "Ubuntu Zombie" stops fitting at Phase 2 —
   whether ports live in this repo under a family name or as
   sibling repos (`macos-zombie`, `windows-zombie`, matching the
   japer-technology one-product-per-repo pattern) is an explicit
   Phase 2 entry decision.

## Top risks

| Risk | Phase | Mitigation |
| ---- | ----- | ---------- |
| Windows policy gate as sole privilege brake | 3 | Design review before code; de-elevated child execution; strict default policy |
| Signing/notarisation lead time (Apple, Authenticode) | 2–3 | Start certificate acquisition during Phase 1 |
| Seam extraction regressing Ubuntu | 1 | It only refactors; full existing CI + nightly container install must stay green |
| Port drift from the core | 2–3 | One `payload/agent/` tree, platform overlays only; CI runs core tests on all OSes |
| Support-surface explosion | all | PLATFORMS.md tiering (Supported/Best-effort/Unsupported) applied per OS from day one |
| macOS TCC blocking agent usefulness | 2 | Treat missing grants as a `doctor`-diagnosable state, documented, never auto-worked-around |

## Non-goals

- Snap, Flatpak, Mac App Store, Microsoft Store: confinement models
  incompatible with a root-capable system agent.
- WSL or containers as a "Windows/portable version".
- Auto-activation from any package maintainer script without an
  explicit operator opt-in.
- Fleet management — still out of scope per
  [`docs/VISION.md`](../docs/VISION.md); multiplying *platforms* is
  not multiplying *tenancy*.
