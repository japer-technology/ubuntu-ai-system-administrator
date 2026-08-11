# Ubuntu AI System Administrator — Debian packaging

This directory holds the metadata used by `make deb` to produce an
installable `ubuntu-zombie` compatibility package of the source tree.

The `.deb` is intentionally a **stage-1** package: it copies the
installer, payload, and documentation to `/usr/share/ubuntu-zombie/`
and exposes a thin wrapper at `/usr/sbin/ubuntu-zombie` that delegates
to `scripts/install.sh`. It deliberately does **not** run the full
installer at `apt install` time, because the installer creates a
root-capable service account, writes sudoers and systemd configuration,
installs runtime dependencies, and creates state under
`/opt/ai-zombie` and `/etc/ubuntu-zombie`. Those changes require an
explicit operator decision.

After installing the package:

```bash
sudo apt install ./ubuntu-zombie_<version>_all.deb
sudo ubuntu-zombie install
```

`sudo ubuntu-zombie {install|verify|doctor|repair|uninstall|--dry-run}`
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
