# Ubuntu AI System Administrator — Debian packaging

This directory holds the metadata used by `make deb` to produce an
installable `ubuntu-ai-system-administrator` compatibility package of the source tree.

The `.deb` is intentionally a **stage-1** package: it copies the
installer, payload, and documentation to `/usr/share/ubuntu-ai-system-administrator/`
and exposes a thin wrapper at `/usr/sbin/ubuntu-ai-system-administrator` that delegates
to `scripts/install.sh`. It deliberately does **not** run the full
installer at `apt install` time, because the installer creates a
root-capable service account, writes sudoers and systemd configuration,
installs runtime dependencies, and creates state under
`/opt/ai-system-administrator` and `/etc/ubuntu-ai-system-administrator`. Those changes require an
explicit operator decision.

After installing the package:

```bash
sudo apt install ./ubuntu-ai-system-administrator_<version>_all.deb
sudo ubuntu-ai-system-administrator install
```

`sudo ubuntu-ai-system-administrator {install|verify|doctor|repair|uninstall|--dry-run}`
behaves identically to invoking `scripts/install.sh` directly from a
git clone.

## Files in this directory

| File         | Purpose                                                         |
| ------------ | --------------------------------------------------------------- |
| `control.in` | dpkg control template (`__VERSION__` is substituted).           |
| `postinst`   | Sets executable bits and prints the next-steps message.          |
| `prerm`      | Refuses removal while the system is still configured.            |
| `copyright`  | MIT copyright notice in machine-readable format.                 |
| `changelog`  | Stub Debian changelog (real history lives in `/CHANGELOG.md`).   |
| `README.md`  | This file.                                                       |
