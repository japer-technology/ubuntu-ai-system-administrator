# Delivery scripts

These scripts run on the *operator's* side of the trust boundary: they
deliver, verify, package, and remove the product that lives in
[`../payload/`](../payload/). Nothing here stays on the target after
install — the running system uses only what the installer copies to
`/opt/ai-zombie/`.

> **Warning:** `install.sh install` and `uninstall.sh` mutate users,
> sudoers, and systemd units on the machine they run on. Only run them
> on a disposable Ubuntu Desktop LTS VM. See
> [`../docs/QUICKSTART.md`](../docs/QUICKSTART.md).

## What's here

- [`install.sh`](install.sh) — the main installer. Idempotent, with
  subcommands `install` (default), `verify`, `doctor`, `repair`, and
  `uninstall`, plus `--dry-run`, `--help`, and a fully unattended
  `ZOMBIE_NONINTERACTIVE=1` mode. Run
  `./scripts/install.sh --help` for the complete flag and
  environment-variable reference.
- [`uninstall.sh`](uninstall.sh) — removes everything the installer
  created; `install.sh uninstall` delegates here.
- [`lib.sh`](lib.sh) — shared bash helpers (colours, logging,
  prompts) sourced by the other scripts. Not runnable on its own.
- [`build-deb.sh`](build-deb.sh) — builds the stage-1 `.deb` package
  described in [`../debian/README.md`](../debian/README.md);
  `make deb` calls this.
- [`verify-bridge-pins.sh`](verify-bridge-pins.sh) — re-downloads the
  checksum-pinned Node bridge dependencies and verifies them against
  `payload/agent/bridge-dependencies.lock`; `make verify-bridge-pins`
  calls this.
- [`completions/`](completions/) — shell completion for `install.sh`
  (`install.bash` for bash, `_install.sh` for zsh); `install.sh
  --help` shows how to enable them.

Every script answers `--help`. All of them are ShellCheck-clean at
`--severity=warning` and covered by [`../tests/smoke.sh`](../tests/smoke.sh);
run `make lint` and `make test` after editing.
