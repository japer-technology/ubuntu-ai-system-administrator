# Configuration

## Interactive installation

Run `./scripts/install.sh` from the product directory. The installer asks for
the administrator name and email, PostgreSQL database and role names, Forgejo
version, and boot preference. Press Enter to accept a displayed default.
Database and initial administrator credentials are generated securely unless
protected secret files are supplied.

The installer shows the public URL, selected values, generated plan digest,
and every mutation step before asking for approval.

## Unattended installation

Direct lifecycle inputs use the `FORGEJO_` prefix:

| Variable | Default | Purpose |
|---|---|---|
| `FORGEJO_ADMIN_USER` | `forgejo-admin` | Initial administrator name |
| `FORGEJO_ADMIN_EMAIL` | `forgejo-admin@localhost.localdomain` | Initial administrator email |
| `FORGEJO_DB_NAME` | `forgejo` | PostgreSQL database |
| `FORGEJO_DB_USER` | `forgejo` | PostgreSQL role |
| `FORGEJO_VERSION` | `latest` on first install | Upstream release pin |
| `FORGEJO_BOOT` | `enabled` | Boot enablement |
| `FORGEJO_HTTP_PORT` | `3000` | Fixed compatibility assertion |
| `FORGEJO_ADMIN_PASSWORD_FILE` | generated | Root-private secret input |
| `FORGEJO_DB_PASSWORD_FILE` | generated | Root-private secret input |
| `FORGEJO_BACKUP_DESTINATION` | `/var/backups/forgejo` | Manual backup target |

Use `--yes --non-interactive` with automation. `--yes` skips both setup
questions and plan approval, so omitted inputs use the defaults above.

Secret references must be absolute, root-owned regular files with no group or
other access. Raw passwords are not accepted by the direct product.

The public host is the existing valid `app.ini` domain or the machine's
single-label hostname plus `.local`. The backend address and port are fixed.
Unknown `FORGEJO_` variables fail closed.

Generated initial administrator credentials are written once to
`/etc/forgejo/bootstrap-admin-password` with mode 0600. Generated database and
application recovery material remains only in root-protected `app.ini`.

`FORGEJO_MIGRATION_MANIFEST` is reserved for external migration adapters. It
must name a canonical absolute path to a root-owned manifest and does not
enable adoption without the exact `ADOPT FORGEJO` confirmation.
