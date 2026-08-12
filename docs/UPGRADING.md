# Upgrading

Ubuntu AI System Administrator is distributed as repository scripts and payload files.
There is no in-place package manager upgrade path yet.

## Recommended process

1. Read `CHANGELOG.md`.
2. Back up `/opt/ai-system-administrator/secrets/env`, `/opt/ai-system-administrator/state/`, and
   `/var/log/ubuntu-ai-system-administrator/audit.log` if you need to keep them.
3. Pull or unpack the new release.
4. Run `sudo ./scripts/install.sh install` from the new tree.
5. Run `sudo ./scripts/install.sh verify` and
   `/opt/ai-system-administrator/bin/health-check`.

The installer is intended to be idempotent. Re-running it re-renders
runtime configuration, redeploys built-in skills, and restarts the chat
service without changing provider secrets.

## Downgrades

Downgrades are not supported. Restore from your backup or uninstall and
install the desired release on a disposable machine.
