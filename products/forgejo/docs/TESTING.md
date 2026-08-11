# Testing

From `products/forgejo`:

```bash
make lint
make test
make package
```

Unit tests cover configuration, Caddy ownership, adoption, archive safety, and
the same-host runner boundary. Integration tests exercise the CLI and family
contract. Root smoke tests verify compatibility delegation.

`tests/vm/lifecycle.sh` is destructive. It runs only as root on a supported
Ubuntu VM with `FORGEJO_DISPOSABLE_VM_TEST=1`, no pre-existing Forgejo state,
and an explicit test sentinel. It uses local checksum-pinned fake Forgejo
binaries while exercising real PostgreSQL, Caddy, Avahi, systemd, CA trust,
backup, update, migration-failure recovery, rollback, repair, suspension,
runner coordination, isolation, and uninstall.
