# 06 — Delivery patterns and prior art

Two sibling japer-technology repositories have already worked parts
of this problem. Steal from both.

## Prior art 1: `lmstudio-vampire/packaging/`

<https://github.com/japer-technology/lmstudio-vampire/tree/main/packaging>

A Python product packaged as native artifacts per platform. What to
reuse directly:

- **Directory layout.** `packaging/{common,linux,ubuntu,macos,windows}`
  with build scripts in `scripts/packaging/` invoked from the repo
  root — adopted in [`02-portable-core.md`](02-portable-core.md).
- **Shared assets.** `common/icons/` (`.ico`, `.icns`, `.png`) and
  `common/release-metadata/` (release notes, signing, store
  metadata templates) — one source of truth for branding and
  release text across all artifacts.
- **A written cross-platform smoke test.** `common/smoke-test.md`:
  every artifact is verified on a clean VM for its platform before
  publishing. Ubuntu Zombie should adopt the same document plus
  automated equivalents of `tests/smoke.sh` per platform.
- **Toolchain choices.** PyInstaller for macOS `.app`/Windows
  `.exe`, Inno Setup for the Windows installer, `debian/` control
  files for `dpkg-buildpackage`, AppImage for generic Linux desktop
  delivery.
- **The honest constraint.** "PyInstaller is not a cross-compiler:
  build each native artifact on the platform it targets." CI must
  run macOS and Windows runners for release builds.

Key difference to respect: Vampire is a user-level desktop launcher;
Zombie is a privileged system daemon. Vampire's `.app`/AppImage
double-click model does not transfer — but its packaging
scaffolding, icon pipeline, and per-platform build scripts do.

## Prior art 2: `forgejo-society/FORGEJO-SOCIETY-INSTALLATION/`

<https://github.com/japer-technology/forgejo-society/tree/main/FORGEJO-SOCIETY-INSTALLATION>

A documentation *library* for installing a complex multi-host
platform — including its own `ubuntu-zombie/` minimum-install
guide and a `scripts/` suite that mirrors this repo's
`install/verify/doctor/repair/uninstall` vocabulary. What to reuse:

- **Tiered entry points by operator effort.** `quick-start/` →
  `bootstrap/` (one-line `curl | bash` with a banner and guided
  options) → `easy-install/` (two scripts) → `scripts/` (full
  subcommand-driven installer) → `install/` (component-level
  deep-dives). Multiplied across OSes, Ubuntu Zombie's docs should
  offer the same ladder per platform: *package manager one-liner* →
  *downloadable artifact* → *bootstrap script* → *git clone*.
- **Checklist-first navigation.** `TASK-LISTS.md` as a parallel
  index into the same material. As platform count grows from one to
  three, a per-platform checklist index prevents the docs from
  becoming a maze.
- **The subcommand vocabulary is already a shared convention**
  across japer-technology installers. Keep it identical on macOS
  and Windows so operator knowledge transfers
  (`mac-zombie doctor`, `zombie.exe repair`).
- **Conformance assets.** Their `CONFORMANCE/` pattern — drop-in
  assets that *prove* an installation is ready — maps to shipping
  `verify` as a first-class, platform-native artifact everywhere.

## The resulting delivery matrix

| Channel | Ubuntu/Linux | macOS | Windows |
| ------- | ------------ | ----- | ------- |
| Package manager | apt repo / PPA (`apt install ubuntu-zombie`) | Homebrew tap | winget |
| Single artifact | signed `.deb` | signed + notarised `.pkg` | signed Inno EXE (MSI later) |
| Bootstrap script | `curl \| bash` | `curl \| bash` | `irm \| iex` (PowerShell) |
| Source | git clone + `install.sh` | git clone + `platform/macos` shell | git clone + `platform/windows` shell |

Every cell keeps the two-stage contract (stage-1 files + wrapper,
explicit activation), with the Windows wizard allowed to fold the
stages into one attended flow with an explicit opt-in
([`05-windows.md`](05-windows.md)).

## Release engineering common to all channels

1. **One version, many artifacts.** The existing `VERSION`
   timestamp stamps every artifact; a tag triggers CI matrix builds
   (ubuntu, macos, windows runners) that attach all artifacts to
   one GitHub release.
2. **Signing inventory.** apt repo GPG key, Apple Developer ID +
   notarisation, Authenticode certificate. All organisational
   prerequisites; start acquisition early because they gate
   everything public.
3. **Checksums + provenance.** Publish SHA-256 sums; the repo's
   existing supply-chain posture
   ([`docs/OPENSSF-SCORECARD.md`](../docs/OPENSSF-SCORECARD.md),
   pinned bridge inputs via `make verify-bridge-pins`) extends
   naturally to artifact attestation (GitHub artifact attestations
   are nearly free in Actions).
4. **Clean-VM smoke test per artifact** before release, per the
   Vampire `smoke-test.md` discipline.
