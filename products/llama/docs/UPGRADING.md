# Updating and rolling back

Llama versions are independent from Ubuntu Zombie. Preview and execute an
update from the reviewed candidate product source:

```bash
products/llama/scripts/manage.sh update --dry-run --json
sudo products/llama/scripts/manage.sh update --yes
sudo llama-manage verify
```

For managed automation, pass the preview's `plan_digest` back with
`--plan-digest`. Execution recomputes it while holding the product lock and
fails if ownership, inputs, version, or ordered steps changed.

Before switching, update writes a verified configuration backup under
`/var/backups/llama.cpp` and a previous-version rollback snapshot below
`/opt/llama.cpp/rollback`. It retains old runtime versions and model files so a
compatible rollback does not re-download them.

```bash
sudo llama-manage rollback --dry-run
sudo llama-manage rollback --yes
sudo llama-manage verify
```

`update` refuses an older candidate. Use the explicit rollback operation for a
saved previous version. Repair never crosses versions and cannot replace an
update or rollback.
