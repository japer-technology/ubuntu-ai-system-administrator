# Recovery

A useful Forgejo recovery set contains both `app.ini` and the PostgreSQL dump.
The configuration carries database credentials and application encryption
material; repositories alone are not sufficient for a complete recovery.

`forgejo-manage update` records the pre-update archive in protected rollback
metadata. The archive is accepted only for the product instance that created
it. Run:

```bash
sudo forgejo-manage rollback --yes
```

Rollback is intentionally destructive to the current Forgejo database and
mutable state. It first creates a new `pre-rollback` backup so the transition
can be reversed.

If `app.ini` is lost while its database or role remains, install and repair
fail closed. Restore the original configuration and a matching database
backup; do not generate replacement encryption secrets over existing data.
