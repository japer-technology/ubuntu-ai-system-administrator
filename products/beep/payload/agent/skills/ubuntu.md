<!-- triggers: ubuntu, ubuntu-pro, ubuntu-drivers, do-release-upgrade, release-upgrade, motd-news -->
# Skill: Ubuntu system management

This skill is loaded for Ubuntu-wide maintenance that spans narrower
package, service, kernel, desktop, storage or security skills.

Operating rules:

- Identify the release and support state first with `/etc/os-release`,
  `uname -r`, `ubuntu-security-status` and `pro status`. Do not assume an
  LTS point release, hardware enablement stack or Ubuntu Pro attachment.
- Start with read-only health evidence: failed units, pending package
  actions, disk pressure, recent high-priority journal entries and reboot
  requirements. Use the relevant focused skill before changing a subsystem.
- Keep package work in the `apt` skill, services in `systemd`, release and
  kernel work in `kernel`, user changes in `users`, and firewall or interface
  work in `network`/`security`. This brief coordinates; it does not bypass
  their safeguards or approval classes.
- Never start `do-release-upgrade`, attach or detach Ubuntu Pro, change
  package origins, or enable unattended upgrades without an explicit
  operator request. These are system-wide changes with rollback and service
  restart consequences; use the `security` skill for unattended-upgrade
  policy.
- Before a release upgrade, verify supported source and target releases,
  free space, package-manager consistency, third-party repositories, backups
  and console access. Recommend a tested restore path; do not treat an
  in-place distribution upgrade as an ordinary package update.
- Respect Ubuntu's configuration ownership. Inspect local changes before
  replacing files under `/etc`, preserve permissions and ownership, validate
  the result, and show the operator the intended diff.
- Use Ubuntu archive packages where practical. Do not add PPAs, vendor
  repositories, snaps or downloaded installers merely because a package is
  absent; explain the options and trust implications first.
- Never disable the Beep chat service, widen its policy, or mutate
  its managed runtime while performing general maintenance.
- Finish with focused verification and report what changed, what still needs
  a reboot or operator action, and the rollback path.
