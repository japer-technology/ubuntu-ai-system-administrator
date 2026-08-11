<!-- triggers: packages, repository, repositories, mirror, mirrors, autoremove, autoclean, purge, orphan, orphans, orphaned, apt-mark, unhold, downgrade, pinning, unmet -->
# Skill: cross-format package health and repositories

This skill is loaded when the operator asks about package health
across formats, broken or unmet dependencies, repositories and
mirrors, or routine cleanup. Day-to-day Debian installs are the `apt`
skill; snaps, flatpaks and AppImages are the `snap` skill; language
package managers are the `dev` skill. This brief covers the layer
above: keeping all of them coherent on one machine.

Operating rules:

- Inventory before judging. One application can exist as a `.deb`, a
  snap and a flatpak simultaneously, each with its own version and
  data. `pkg.query` (Debian), `snap list` and `flatpak list` are
  `read_only` and auto-run; check all three before declaring anything
  installed, missing or duplicated.
- The broken-dependency triage order for Debian packages is:
  `apt-get check`, then `dpkg --audit`, then
  `apt-get install -f --dry-run` — all read-only in that form. Show the
  operator what the fix *would* do before running the real
  `apt-get install -f`, which is `system_change` and waits for
  approval.
- "Unmet dependencies" usually means a foreign repository or a manually
  installed `.deb` pinned the system into a corner. Read
  `apt-cache policy <pkg>` to see which repository each candidate comes
  from before proposing force or removal; the right fix is often
  disabling the offending source, not forcing the package.
- Never use `dpkg -i --force-*`, `apt-get -o APT::Force-LoopBreak` or
  removal of `Essential` packages to break a dependency knot. If the
  solver refuses, quote its output and ask the operator; a forced
  install trades a visible error for silent corruption.
- Repository changes are security changes. Adding a PPA, editing
  `/etc/apt/sources.list` or files under `/etc/apt/sources.list.d/`,
  or importing a signing key extends who can put code on the machine —
  do it only with explicit operator consent, and prefer the modern
  `.sources` (deb822) format with a `Signed-By` key over a global
  keyring.
- GPG/`NO_PUBKEY` errors identify a repository whose key is missing or
  expired. Name the repository, not just the key ID, and let the
  operator decide between fixing the key and dropping the source.
- Held and pinned packages explain "why does it not upgrade".
  `apt-mark showhold` and `apt-cache policy` are read-only and answer
  this directly. Setting or clearing a hold (`apt-mark hold|unhold`)
  changes upgrade behaviour machine-wide and is `system_change`.
- Downgrades (`apt-get install pkg=version`) fight the solver and can
  cascade. State which dependent packages the downgrade drags along,
  and whether the older version will be re-upgraded on the next
  unattended run unless it is also held.
- Routine cleanup, in increasing blast radius: `apt-get autoclean`
  (cache of superseded packages), `apt-get clean` (whole cache),
  `apt-get autoremove` (packages nothing depends on), then snap
  revision pruning (`snap set system refresh.retain=2`) and
  `flatpak uninstall --unused`. Always show `autoremove`'s package
  list with `--dry-run` first — kernel packages in that list deserve a
  comment, since removing all old kernels leaves no fallback.
- Orphaned configuration lingers after removal without purge.
  `dpkg -l | grep '^rc'` lists them; purging is `system_change` and
  deletes configuration the operator may want, so name the packages
  before acting.
- Automating cleanup (a timer that runs `autoremove`, snap retention
  settings, unattended-upgrades tweaks) is a standing change. Describe
  the schedule and what it will delete over time before landing it —
  see the `scheduling` skill for the timer mechanics.
- Report in the operator's terms: which format the package came from,
  which repository supplied it, what was actually changed, and how much
  disk was reclaimed (`df -h` before and after for cleanups).
