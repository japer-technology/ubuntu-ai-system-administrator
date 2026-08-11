# Recovery

Start with read-only evidence:

```bash
llama-manage status --json
sudo llama-manage verify --json
llama-manage doctor
systemctl status llama-server.service
journalctl -u llama-server.service
```

Use `repair --dry-run` before `repair --yes`. Repair revalidates ownership,
catalogues, runtime and model checksums, protected files, service intent, and
loopback health. It does not adopt unknown paths, select an arbitrary model, or
change versions.

An interrupted first install leaves a root-owned transaction marker so the
same trusted product source can converge safely. Do not create or edit that
marker by hand. If ownership validation fails, preserve the host and reconcile
the unexpected resource before retrying.

Retained-state uninstall keeps the model and a protected configuration
snapshot. Running `install` restores the runtime around that state. A complete
purge has no automatic state recovery; restore only from an operator-controlled
backup. Audit evidence and its protected ownership marker remain under
`/var/log/llama.cpp`, so that evidence does not block a later clean install.

If an update health gate fails, correct the immediate service problem or use
the saved `rollback` operation. Never repoint `/opt/llama.cpp/current` manually
without validating the target tree manifest.
