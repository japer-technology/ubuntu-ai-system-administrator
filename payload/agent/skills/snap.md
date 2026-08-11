<!-- triggers: snap, snaps, snapd, flatpak, appimage, chromium, firefox, confinement -->
# Skill: snap, flatpak and AppImage packaging

This skill is loaded when the operator mentions snaps, flatpaks or
AppImages. APT packaging is covered by the `apt` skill; cross-format
package health and cleanup by the `packages` skill.

Operating rules:

- Inspection is `read_only` and auto-runs: `snap list`,
  `snap info <name>`, `snap connections <name>`, `flatpak list`. Use
  these before proposing anything, and note that `pkg.query` only knows
  about Debian packages — it will not find a snap.
- `snap install|remove|refresh|revert|enable|disable|connect|disconnect`
  and the equivalent `flatpak` subcommands are `system_change` and wait
  for operator approval.
- Several Ubuntu Desktop applications ship as snaps by default —
  Firefox and Chromium most visibly — so "install Firefox" via apt may
  install a transitional package that pulls the snap anyway. Say which
  packaging the operator is actually getting.
- Watch for duplicates. A snap and a `.deb` of the same application can
  both be installed with separate profiles, extensions and caches; the
  "settings did not save" complaint is often two copies, not a bug.
  Check both before changing configuration.
- Never install with `--devmode`, `--classic` or `--dangerous` to make
  something work. Those bypass confinement; they are a security
  decision the operator must make knowingly, with the reason stated.
- Snaps refresh themselves in the background. If the operator is
  chasing an application that changed behaviour without them acting,
  check `snap changes` and `snap info <name>` for the refresh history
  before hunting elsewhere.
- `snap revert <name>` is the cheap rollback after a bad refresh —
  prefer it over removing and reinstalling, which discards the
  application's data.
- Snap confinement is why a snap cannot see `/mnt`, removable media or
  files outside `$HOME` by default. That is expected behaviour; fix it
  with the documented interface (`snap connect …`), not by moving the
  operator's data.
- AppImages are unmanaged single files with no updates and no
  confinement. Treat running one as executing an unverified binary:
  say where it came from, keep it under the operator's own directory,
  and do not present it as equivalent to a packaged install.
