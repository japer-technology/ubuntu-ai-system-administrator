# Quickstart

Ubuntu Zombie installs a local AI Systems Administrator account and a
password-protected chat service bound to `127.0.0.1`. It does not install
or configure SSH, Tailscale, VNC, Docker, graphical autologin, or GUI
browser automation.

## Before you start

Use a disposable Ubuntu Desktop LTS machine. The installer creates a
root-capable local account, sudoers policy, systemd units, logs, and
state under `/opt/ai-zombie`.

You need:

- sudo access on the target machine;
- network access to Ubuntu apt repositories, NodeSource, npm, and your
  selected LLM provider;
- an optional chat password to replace the default;
- an LLM provider API key to add after installation.

## Install

From the repository root:

```bash
sudo ./scripts/install.sh install
```

This command installs Ubuntu Zombie. The installer grammar is
`scripts/install.sh [verb] [flags]`.

Interactive installs open a parameter review before changing the host.
Accept the defaults or edit the agent user, install root, chat port,
chat password, Time to Live, receipt path, and local LLM settings.

For unattended installs:

```bash
sudo ZOMBIE_NONINTERACTIVE=1 \
     ZOMBIE_ADMIN_PASSWORD='replace-me' \
     ./scripts/install.sh install --yes
```

## Common install parameters

| Parameter | Default | Required |
| --------- | ------- | -------- |
| `ZOMBIE_USER` | `zombie` | No |
| `ZOMBIE_DIR` | `/opt/ai-zombie` | No |
| `ZOMBIE_CHAT_PORT` | `7878` | No |
| `ZOMBIE_ADMIN_PASSWORD` | `braaaains` | No |
| `ZOMBIE_TTL_DAYS` | `7` | No |
| `ZOMBIE_RECEIPT_FILE` | `/var/log/ubuntu-zombie/install-receipt.txt` | No |

## Add an LLM provider key

After install, edit the secrets file:

```bash
sudo /opt/ai-zombie/bin/secrets-edit
```

Set the provider variables documented in
[`CONFIGURATION.md`](CONFIGURATION.md#provider-keys), then
restart the service:

```bash
sudo systemctl restart ubuntu-zombie-chat.service
```

## Open chat

On the Ubuntu Zombie desktop, open:

```text
http://127.0.0.1:7878/
```

or run:

```bash
/opt/ai-zombie/bin/zombie-chat
```

The service is intentionally loopback-only. If you need remote access,
bring your own remote-access mechanism outside Ubuntu Zombie.

## Verify, doctor, repair

```bash
sudo ./scripts/install.sh verify
sudo ./scripts/install.sh doctor
sudo ./scripts/install.sh repair
```

- `verify` is read-only.
- `doctor` explains likely fixes.
- `repair` re-asserts permissions, re-renders runtime config, redeploys
  built-in skills, and restarts the chat service.

## Health and diagnostics

```bash
/opt/ai-zombie/bin/health-check
/opt/ai-zombie/bin/collect-diagnostics
```

Diagnostics are redacted before being bundled.

## Uninstall

```bash
sudo ./scripts/install.sh uninstall
```

The uninstaller removes Ubuntu Zombie services, sudoers entries,
payload files, policy, logrotate rules, and optionally the agent account
and archives. Shared packages such as Node and Python are left alone.
