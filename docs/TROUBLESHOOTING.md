# Troubleshooting

## Start with doctor and health-check

```bash
sudo ./scripts/install.sh doctor
/opt/ai-system-administrator/bin/health-check
```

`doctor` explains installer/runtime drift. `health-check` gives a local
summary of the chat service, provider token state, disk space, audit log,
secrets file permissions, agent venv, and pi binaries.

## Chat does not load

Check the service:

```bash
sudo systemctl status ubuntu-ai-system-administrator-chat.service
sudo journalctl -u ubuntu-ai-system-administrator-chat.service -n 100 --no-pager
```

The chat service intentionally binds to `127.0.0.1` only. Open it from
the Ubuntu AI System Administrator machine at `http://127.0.0.1:57878/`, or
use your own remote-access mechanism outside Ubuntu AI System Administrator.

## Provider errors

Edit provider secrets and restart the chat service:

```bash
sudo /opt/ai-system-administrator/bin/secrets-edit
sudo systemctl restart ubuntu-ai-system-administrator-chat.service
```

Then inspect recent audit/provider records:

```bash
/opt/ai-system-administrator/bin/audit-recent -t provider_error -t tool_call
```

## Installer drift

Re-apply known-safe files and permissions:

```bash
sudo ./scripts/install.sh repair
```

This re-asserts ownership/modes, re-renders pi-mono configuration,
redeploys built-in skills, and restarts the chat service.

## Collect diagnostics

```bash
/opt/ai-system-administrator/bin/collect-diagnostics
```

The bundle redacts provider keys, token-shaped strings, private keys,
password assignments, and the secrets-file path before writing a tarball
under `/tmp`.
