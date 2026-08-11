<!-- triggers: hardware, driver, drivers, gpu, nvidia, amdgpu, lspci, lsusb, bluetooth, audio, sound, microphone, printer, cups, scanner, battery, firmware, fwupd, webcam, touchpad, thermal -->
# Skill: hardware, drivers and peripherals

This skill is loaded when the operator mentions hardware, drivers,
graphics, audio, printing, Bluetooth or power.

Operating rules:

- Identify the device before naming a driver. `lspci -nnk`, `lsusb`,
  `lshw -short`, `sensors`, `upower -i $(upower -e | grep BAT)` and
  `dmesg | grep -i firmware` are `read_only` and auto-run. Quote the
  PCI/USB ID you matched on — a guess about "the wifi chip" wastes the
  operator's time.
- Prefer Ubuntu's own driver paths. `ubuntu-drivers devices` lists the
  recommended packages; installing them with
  `sudo ubuntu-drivers install` or `apt-get install` keeps the driver
  in the update stream. Vendor `.run` installers (notably NVIDIA's)
  break on every kernel upgrade — do not use one without explicit
  operator consent and a stated recovery plan.
- Graphics changes can end in a black screen. After installing or
  switching a GPU driver, say that a reboot is the test, name the
  fallback (`nomodeset`, a previous kernel entry, or a TTY via
  Ctrl+Alt+F3), and check `journalctl -b -u gdm3 --no-pager` if the
  session fails to come up.
- Audio on modern Ubuntu is PipeWire with a WirePlumber session
  manager. Inspect with `wpctl status` and `pactl info`; restart the
  *user* services (`systemctl --user restart wireplumber
  pipewire pipewire-pulse`) rather than the system ones, and remember
  those run as the desktop user, not as the agent.
- Bluetooth: check `rfkill list` for a soft block before touching
  `bluetoothctl` — a blocked radio explains most "Bluetooth is broken"
  reports and needs no configuration change at all.
- Printing: `lpstat -t` and `lpinfo -v` describe the current queues and
  backends. Ubuntu drives most modern printers driverless over
  IPP/Everywhere via `cups` and `avahi`; install a vendor driver only
  after driverless discovery has actually failed.
- Firmware updates through `fwupdmgr` are real, sometimes irreversible
  device changes. `fwupdmgr get-devices`/`get-updates` are safe reads;
  `fwupdmgr update` needs explicit approval, mains power, and a warning
  that some firmware cannot be downgraded.
- Thermal and battery complaints are measurements, not opinions.
  Report `sensors` output, the battery's design versus full-charge
  capacity, and `cat /sys/class/thermal/thermal_zone*/temp` before
  suggesting TLP, fan control or a power profile change.
- Suspend/resume failures live in the journal across the boot boundary:
  compare `journalctl -b -0` with `-b -1`. Hardware that fails to
  resume is usually a driver or firmware issue, not a desktop setting.
- When the fault is genuinely the hardware — a failing disk in
  `smartctl -a`, a dead port, a swollen battery — say so and stop.
  Reinstalling packages does not repair silicon.
