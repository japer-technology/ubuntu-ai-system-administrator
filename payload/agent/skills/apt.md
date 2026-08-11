<!-- triggers: apt, apt-get, dpkg, package, install, uninstall, upgrade, ppa -->
# Skill: APT package management on Ubuntu

This skill is loaded when the operator's recent prompts mention APT,
package installs, or related Debian package terms. Cross-format
package health — broken dependencies, repositories and mirrors, and
routine cleanup — is covered by the `packages` skill.

Operating rules:

- Prefer the typed `pkg.query` and `pkg.install` tools over `shell.run`
  when answering "is X installed?" or "install X". They are gated by
  the same policy classes but produce cleaner observations.
- For investigation, `pkg.query` wraps `dpkg -s` and `apt-cache policy`.
  Use it before suggesting installs so the operator sees the current
  state.
- For installs, `pkg.install` runs `apt-get install -y` and is
  classified `system_change`; it always waits for operator approval.
- Never call `apt-get update && apt-get upgrade` unattended unless the
  operator explicitly asked for a system upgrade. Upgrades can restart
  services.
- Do not edit `/etc/apt/sources.list` or files under
  `/etc/apt/sources.list.d/` without explicit operator consent; new
  repositories are a security change.
- Some applications (for example Google Chrome) are not in the Ubuntu
  archive and ship a vendor `.deb`. With explicit operator consent the
  approved install path is: download the official `.deb` into a scratch
  directory under `/tmp`, then install it with
  `sudo apt-get install -y ./<file>.deb` — `apt-get` resolves its
  dependencies, so prefer this over a bare `dpkg -i`, which does not.
  This runs as `system_change` and still waits for approval. Do not add
  the vendor's apt repository or pipe a `curl | bash` installer to
  achieve the same result. If the install still fails (for example a
  dependency the vendor needs is not in the Ubuntu archive), report the
  exact apt error to the operator and ask how to proceed rather than
  forcing the package on with `dpkg -i --force-depends`.
- Language ecosystems have their own package managers (`pip`, `npm`,
  `cargo`). They are not apt's business and must not be run as root
  against the system interpreter — see the `dev` skill.
- If a package is missing on the system, report it and ask the
  operator how to proceed. Read-only web lookups (`web.fetch`, or
  `curl`/`wget` to stdout) are fine for checking an upstream version or
  release note, but never fall back to a `curl | bash` install — that
  pattern is forbidden by the threat model. See the `web` skill.
