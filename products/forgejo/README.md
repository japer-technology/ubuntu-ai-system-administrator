# Forgejo

This directory is the independently versioned Forgejo infrastructure product.
It owns the private Forgejo server, PostgreSQL role and database, Caddy route,
local CA export, host trust, Avahi advertisement, and `forgejo.service`.

An Actions runner is intentionally outside this product. The lifecycle safely
coordinates a co-located `forgejo-runner.service` when one is present.

## Install

On a supported Ubuntu Desktop 22.04 or 24.04 LTS host, run:

```bash
./scripts/install.sh
```

The installer obtains root privileges with `sudo` when needed, asks the setup
questions, displays the complete plan, and applies it only after approval.
Press Enter to accept the secure defaults.

## Trust boundary

Forgejo listens only on `127.0.0.1:3000`. Caddy is the LAN-facing HTTPS edge
on the host's `.local` name. `app.ini` remains root-owned and group-readable
by `git`; its database and application secrets never enter lifecycle JSON,
receipts, or audit events.

The lifecycle runs as root because it manages packages, PostgreSQL, shared
Caddy configuration, host certificate trust, systemd, and service identities.
It has no authority outside the resources declared in `PRODUCT.json` and the
shared PostgreSQL, Caddy, Avahi, and host-trust integrations described here.

## Manage

From this directory:

```bash
./scripts/manage.sh describe --json
./scripts/manage.sh install --dry-run
sudo forgejo-manage verify
sudo forgejo-manage backup --yes
sudo forgejo-manage update --yes
sudo forgejo-manage rollback --yes
sudo forgejo-manage suspend --yes
sudo forgejo-manage resume --yes
sudo forgejo-manage uninstall --yes
```

For unattended installation, provide any desired `FORGEJO_*` inputs and run
`sudo ./scripts/manage.sh install --yes --non-interactive`.

Uninstall retains repositories, database state, and recovery secrets by
default. Complete deletion additionally requires `--purge` and
`--confirmation "DELETE FORGEJO STATE"`.

See `docs/INSTALLATION.md`, `docs/CONFIGURATION.md`, and
`docs/ARCHITECTURE.md`.
