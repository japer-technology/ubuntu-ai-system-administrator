# 03 — Linux: finishing the clean-install story

Linux is the cheapest multiplier because the mechanism already
exists. The work is polish and distribution, not porting.

## Step 1 — harden the stage-1 `.deb` (exists today)

`make deb` already produces a working stage-1 package
([`debian/README.md`](../debian/README.md)). Improvements worth
making before wider distribution:

- **Build with `dpkg-buildpackage`/debhelper** instead of raw
  `dpkg-deb`, gaining lintian checks, proper maintainer-script
  snippets, and md5sums/conffile handling. The `lmstudio-vampire`
  repo's `packaging/ubuntu/debian/` takes this route.
- **Declare real dependencies.** `Depends:` currently covers bash,
  sudo, curl, ca-certificates. python3 belongs there too; Node stays
  out (installed at stage 2 from NodeSource by operator choice).
- **Ship a `.changes`/signed release.** Sign packages with a project
  key so an apt repository (below) is trustworthy.

## Step 2 — an apt repository (the real "just apt install" feel)

A tarball or attached `.deb` still means "download a file". The
clean end-state is:

```bash
sudo add-apt-repository ppa:japer-technology/ubuntu-zombie   # or a
# self-hosted deb repo (aptly/reprepro) behind HTTPS
sudo apt install ubuntu-zombie
sudo ubuntu-zombie install
```

Options, in increasing control: Launchpad PPA (free, Ubuntu-only,
builds from source recipes), a static aptly/reprepro repo published
from CI on GitHub Pages/object storage, or — dogfooding — a repo
served by the optional Forgejo component
([`options/plan-optional-forgejo-server.md`](../options/plan-optional-forgejo-server.md)),
mirroring how the `forgejo-society` project treats Forgejo as the
distribution hub. CI already builds on every push; adding a
`make deb` + publish job to
[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) on tag is
a small change.

## Step 3 — optional stage-2 preseeding via debconf

For fleet-ish or automation users who *want* one-shot installs, a
debconf-driven mode can let `apt install` also activate — but only
when the operator has explicitly preseeded
`ubuntu-zombie/activate=true` plus the required env. Default remains
stage-1 only. This keeps the trust model (activation is an explicit
operator decision) while enabling `ZOMBIE_NONINTERACTIVE=1`-grade
automation through native packaging.

## Debian-family support (Mint, Pop!_OS, Debian proper)

The installer currently refuses unless `ID=ubuntu`
([`docs/PLATFORMS.md`](../docs/PLATFORMS.md)). Since a `.deb` invites
Debian-family users, decide deliberately:

- Cheap middle ground: accept `ID_LIKE` containing `ubuntu`/`debian`
  behind an explicit `ZOMBIE_ALLOW_DERIVATIVE=1` acknowledgement,
  keeping the support matrix honest (Best-effort tier).
- Blockers to audit first: NodeSource repo availability, desktop
  environment assumptions, and Ubuntu-specific package names.

## Snap and Flatpak: assessed and rejected for the core product

| Mechanism | Verdict | Reason |
| --------- | ------- | ------ |
| Snap | **No** | Strict confinement is the antithesis of a root-capable sysadmin agent; a classic snap needs manual store approval and still fights the model. |
| Flatpak | **No** | Sandboxed, desktop-app oriented; no sane path to creating users, sudoers, and systemd units. |
| AppImage | **No** for the agent | Same confinement mismatch; AppImage suits the self-contained *desktop client* case (`lmstudio-vampire` uses it for exactly that), not a system installer. |

The `.deb` + apt repo path is the correct and sufficient Linux
answer. Effort spent on containerised formats would be spent
fighting the product's own trust model.

## Summary of Linux deliverables

1. debhelper-based build replacing raw `dpkg-deb` (keep `make deb`).
2. Signed packages + apt repository published from CI on tag.
3. Optional debconf preseed path for explicit one-shot activation.
4. A documented decision on Debian derivatives with an
   `ID_LIKE` escape hatch if accepted.
