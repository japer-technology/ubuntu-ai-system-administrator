# 04 — macOS: "Mac Zombie"

macOS is the closer of the two ports: POSIX userland, `sudo` and
sudoers exist, Python and Node install cleanly, and the agent core
runs unmodified. The work is the platform shell and the packaging.

## Platform mapping

| Ubuntu concept | macOS equivalent |
| -------------- | ---------------- |
| `useradd` agent account | `sysadminctl -addUser` / `dscl` hidden account (UID < 500 hides it from the login window) |
| `/etc/sudoers.d/` drop-in | Same — macOS ships sudo with `#includedir /private/etc/sudoers.d` |
| systemd service | launchd `LaunchDaemon` plist in `/Library/LaunchDaemons/` (`KeepAlive`, `RunAtLoad`) |
| systemd health timer | launchd `StartInterval` job |
| `/opt/ai-zombie/` | `/Library/Application Support/ai-zombie/` (or keep `/opt/ai-zombie` — Homebrew normalised `/opt` on Apple Silicon) |
| `/etc/ubuntu-zombie/` overlays | `/Library/Preferences/ai-zombie/` or an `etc/` under the prefix |
| `/var/log/ubuntu-zombie/` + logrotate | `/Library/Logs/ai-zombie/` + `newsyslog.d` rules |
| apt + NodeSource | Homebrew (`brew install python@3.12 node@22`) or bundled runtimes in the `.pkg` |
| `apt.md` / `systemd.md` skills | `brew.md` / `launchctl.md` / `softwareupdate.md` skills |
| ufw policy classes | `pfctl` / `socketfilterfw` classes in `policy.darwin.yaml` |

## Things with no Ubuntu analogue (the real port cost)

1. **TCC / privacy permissions.** Full Disk Access, Accessibility,
   and Screen Recording are per-app grants a script cannot
   self-grant. A sysadmin agent that reads other users' files or
   drives the GUI needs the operator to approve the agent binary in
   System Settings. The installer must detect missing grants and
   walk the operator through them (`doctor` output).
2. **SIP.** System paths are immutable; anything touching
   `/System` is off the table. Policy classes must reflect that
   `csrutil`-adjacent suggestions are `destructive`/refused.
3. **Signing + notarisation.** Any distributed `.pkg` or binary must
   be Developer-ID-signed and notarised or Gatekeeper blocks it.
   This is an organisational prerequisite (Apple Developer account,
   signing certs in CI) before any public artifact ships.
4. **No stable "Desktop LTS" notion.** Support the current and
   previous macOS major versions; state this in
   [`docs/PLATFORMS.md`](../docs/PLATFORMS.md).

## Delivery mechanisms, best-first

1. **`.pkg` installer (the "just a file" answer).** Built with
   `pkgbuild`/`productbuild`. Stage-1 semantics: the pkg lays files
   under the prefix and installs a `/usr/local/sbin/mac-zombie`
   wrapper; `postinstall` prints next steps only. Activation stays
   `sudo mac-zombie install`. The `lmstudio-vampire` repo's
   `packaging/macos/` (PyInstaller `.app`, `Info.plist`,
   entitlements) is the sibling reference for bundling and signing,
   though Zombie is a daemon-first product, so a plain `.pkg` beats
   an `.app` bundle here.
2. **Homebrew.** `brew install japer-technology/tap/mac-zombie`
   from a project tap — near-zero infrastructure (a formula in a
   `homebrew-tap` repo), ideal for the technical early-adopter
   audience. Formula installs the tree + wrapper; caveats text tells
   the operator to run the activation step. Note Homebrew is
   per-user/unprivileged, so activation still elevates via sudo.
3. **`curl | bash` bootstrap.** Same script pattern as the
   `forgejo-society` `bootstrap/` entry point; acceptable as the
   git-clone equivalent, not the headline mechanism.

Mac App Store distribution is impossible (sandboxing) and is a
non-goal.

## Installer implementation choice

Write the macOS shell as a fresh, smaller
`platform/macos/install.sh` implementing the contract in
[`02-portable-core.md`](02-portable-core.md), rather than threading
`if darwin` through 3,200 lines of the Ubuntu installer. Bash 3.2 is
what macOS ships; either target it, require the Homebrew bash, or —
better long-term — write new shells in Python since the runtime is
a hard dependency anyway. Reuse `tests/smoke.sh` patterns for a
`tests/smoke-macos.sh`, and add a `macos-latest` CI job for lint,
syntax, python compile, and `--dry-run`.

## Deliverables

1. `platform/macos/` shell: account, sudoers, LaunchDaemons, prefix
   staging, `install/verify/doctor/repair/uninstall`, receipts.
2. `policy.darwin.yaml` overlay + `brew`/`launchctl` skills.
3. Signed, notarised `.pkg` from CI; Homebrew tap formula.
4. TCC-permission walkthrough in `doctor` and docs.
5. Platform tier entry in `docs/PLATFORMS.md`.
