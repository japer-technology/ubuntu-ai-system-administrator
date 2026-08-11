<!-- triggers: gnome, gsettings, dconf, desktop, gdm, gdm3, wayland, x11, xorg, monitor, monitors, resolution, wallpaper, theme, screensaver, nautilus -->
# Skill: Ubuntu Desktop session and GNOME settings

This skill is loaded when the operator mentions the desktop session,
GNOME, displays or session services.

Operating rules:

- The chat service runs as the local agent account under systemd, not
  inside the operator's graphical session. It has no `DISPLAY`, no
  `WAYLAND_DISPLAY` and no session D-Bus address, so `gsettings`,
  `dconf`, `xrandr`, `notify-send` and GUI launches fail or silently
  write to the wrong profile when run naively.
- Because of that, prefer *reporting* the correct command for the
  operator to run in their own terminal over trying to force it through
  a service context with a hand-built `DBUS_SESSION_BUS_ADDRESS`. Say
  which user the command must run as.
- Inspection that does work from the service context: `loginctl
  list-sessions` and `loginctl show-session <id>` for the session type
  (`x11` or `wayland`), `fs.read` on `/etc/gdm3/custom.conf`,
  `svc.status` on `gdm.service`, and the journal for the display
  manager and the user session.
- `gsettings`/`dconf` writes are `user_change` and apply per user
  profile. Never apply them as root "so they stick"; that writes to
  root's profile and changes nothing the operator can see.
- Never restart or stop `gdm`/`gdm3` on a machine somebody is using.
  It terminates the graphical session and everything running in it.
  Warn explicitly and let the operator choose the moment; a display
  manager restart is a `system_change` with a session-sized blast
  radius.
- Wayland is the Ubuntu default. Advice that depends on `xrandr`, X11
  screen-capture or X11 input tooling may simply not apply — check the
  session type before recommending it.
- Graphics-driver changes (`ubuntu-drivers`, adding a proprietary
  driver, editing `/etc/X11/xorg.conf`) can leave the machine without a
  usable desktop. Recommend that the operator has a way back in — a TTY
  or a recovery boot — before approving.
- Display, keyboard-layout and theme preferences are personal state.
  Read them out and confirm the intended value rather than assuming the
  operator wants the "correct" setting.
