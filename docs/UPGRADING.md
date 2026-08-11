# Upgrading

Ubuntu Zombie is distributed as repository scripts and payload files.
There is no in-place package manager upgrade path yet.

## Recommended process

1. Read `CHANGELOG.md`.
2. Back up `/opt/ai-zombie/secrets/env`, `/opt/ai-zombie/state/`, and
   `/var/log/ubuntu-zombie/audit.log` if you need to keep them.
3. Pull or unpack the new release.
4. Run `sudo ./scripts/install.sh install` from the new tree.
5. Run `sudo ./scripts/install.sh verify` and
   `/opt/ai-zombie/bin/health-check`.

The installer is intended to be idempotent. Re-running it re-renders
runtime configuration, redeploys built-in skills, and restarts the chat
service without changing provider secrets.

Forgejo updates report existing service and PostgreSQL state before touching
it. Approving each exact, capitalized `YES` prompt updates Forgejo in place
without dropping repositories or database data. Unattended updates must set
`FORGEJO_CONFIRM_UPDATE=YES` and
`FORGEJO_CONFIRM_DATABASE_REUSE=YES`; `--yes` alone cannot bypass these
data-safety gates.

## Downgrades

Downgrades are not supported. Restore from your backup or uninstall and
install the desired release on a disposable machine.
