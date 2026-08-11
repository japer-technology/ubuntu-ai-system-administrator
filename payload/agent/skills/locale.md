<!-- triggers: locale, locales, timezone, timedatectl, ntp, chrony, clock, hostname, hostnamectl, keyboard, keymap, language, i18n -->
# Skill: time, locale, keyboard and hostname

This skill is loaded when the operator mentions the clock, time
synchronisation, timezone, locale, keyboard layout or hostname.

Operating rules:

- Read the current state first — `timedatectl`, `localectl`,
  `hostnamectl` and `locale` are all `read_only` and auto-run. They
  also answer most questions outright, without any change at all.
- Time sync on Ubuntu is `systemd-timesyncd` by default; `chrony` is
  the common replacement on servers. Do not install one while the other
  is active — `timedatectl show -p NTP` says which is in charge.
- A wrong clock breaks TLS, apt, and authentication in confusing ways.
  When certificate or repository errors appear, check the clock early;
  it is one cheap read and it explains a whole class of failures.
- Prefer `sudo timedatectl set-timezone <Area/City>` over editing
  `/etc/localtime` by hand, and validate the name against
  `timedatectl list-timezones`. Changing the timezone reinterprets
  every timestamp the operator is about to read — say so when
  correlating logs.
- Dual-boot machines usually want the RTC in UTC. `timedatectl
  set-local-rtc 1` exists for Windows compatibility and is a
  documented source of clock drift; state the trade-off rather than
  flipping it silently.
- Generating locales: install the language pack
  (`sudo apt-get install language-pack-<code>`), or uncomment the entry
  in `/etc/locale.gen` and run `sudo locale-gen`, then set the system
  default with `sudo localectl set-locale LANG=<locale>`. A locale that
  is set but never generated produces `Cannot set LC_ALL` warnings in
  every subsequent command.
- Locale changes only take effect in new sessions. Tell the operator to
  log out and back in rather than letting them conclude the change
  failed.
- Keyboard layout has two halves: the console (`localectl
  set-keymap`) and the graphical session (`localectl set-x11-keymap`,
  or GNOME's own input-source setting for the logged-in user). Say
  which one you changed — fixing the console does not fix the desktop.
- Renaming the host touches `/etc/hostname` *and* `/etc/hosts`. Use
  `sudo hostnamectl set-hostname <name>` and then confirm `/etc/hosts`
  still maps `127.0.1.1` to the new name; a mismatch makes `sudo` slow
  and breaks local name resolution. Warn that certificates, monitoring
  and remote access configured against the old name will need
  updating. If the optional Forgejo component is installed, the rename
  also changes its advertised `<hostname>.local` URL and the Caddy
  route that serves it — see the `forgejo` skill.
- After any change, prove it with the same read-only command you
  started from, and report both the old and new values.
