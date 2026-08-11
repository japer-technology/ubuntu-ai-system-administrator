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

This is equivalent to the explicit component form
`sudo ./scripts/install.sh install zombie`. The canonical grammar is
`scripts/install.sh <verb> [component ...] [flags]`; valid component
targets are `zombie`, `forgejo`, `forgejo-runner`, and `llama`.

Interactive installs open a parameter review before changing the host.
Accept the defaults or edit the agent user, install root, chat port,
chat password, Time to Live, receipt path, and local LLM settings.

### Install Forgejo without zombie

To install only Forgejo and PostgreSQL:

```bash
sudo ./scripts/install.sh install forgejo
```

This path does not create a root-capable zombie account or install the
agent, Node runtime, policy, audit log, chat services, or desktop power
settings. It keeps only installer-owned transcript and receipt records
under `/var/log/`. Generated Forgejo credentials are recorded in the
root-only receipt. It also installs Avahi and Caddy: Forgejo listens on
loopback, while Caddy serves
`https://<lowercase-machine-hostname>.local/` with a locally issued
certificate.

Before opening Forgejo from another LAN device, copy
`/etc/forgejo/caddy-local-ca.crt` from the host over an authenticated
channel and import it into that device's trusted root certificate store.
See [Configuration](CONFIGURATION.md#trust-the-forgejo-local-certificate-authority)
for the trust and removal guidance.

To install both components in registry order:

```bash
sudo ./scripts/install.sh install zombie forgejo
```

The legacy `ZOMBIE_INSTALL_FORGEJO=1 ./scripts/install.sh install` form
remains equivalent to that combined command.

To install Forgejo with its co-located Actions runner:

```bash
sudo ./scripts/install.sh install forgejo-runner
```

The runner target automatically selects the required `forgejo` component.
It does not select or install the zombie account and runtime.

### Install the independent Llama product

To install a CPU local model for applications and users on this PC:

```bash
products/llama/scripts/manage.sh install --dry-run
sudo products/llama/scripts/manage.sh install --yes
llama-manage status
llama-manager status
```

The compatibility command `sudo ./scripts/install.sh install llama` delegates
to the same product-owned lifecycle. Llama exposes an OpenAI-compatible API at
`http://127.0.0.1:8080/v1`. It does not create or modify the Zombie
account or runtime. See [`products/llama/docs/INSTALLATION.md`](../products/llama/docs/INSTALLATION.md)
for update, rollback, retained-state removal, and complete purge commands.

For unattended installs:

```bash
sudo ZOMBIE_NONINTERACTIVE=1 \
     ZOMBIE_ADMIN_PASSWORD='replace-me' \
     ./scripts/install.sh install --yes
```

## Parameters required to allow the install to proceed

| Parameter | Default | Required |
| --------- | ------- | -------- |
| `ZOMBIE_USER` | `zombie` | No |
| `ZOMBIE_DIR` | `/opt/ai-zombie` | No |
| `ZOMBIE_CHAT_PORT` | `7878` | No |
| `ZOMBIE_ADMIN_PASSWORD` | `braaaains` | No |
| `ZOMBIE_TTL_DAYS` | `7` | No |
| `ZOMBIE_RECEIPT_FILE` | `/var/log/ubuntu-zombie/install-receipt.txt` | No |
| `ZOMBIE_LOCAL_LLM_MODE` | `auto` | No |

## Add an LLM provider key

After install, edit the secrets file:

```bash
sudo /opt/ai-zombie/bin/secrets-edit
```

Set the provider variables documented in
[`CONFIGURATION.md`](CONFIGURATION.md#llm-provider-configuration), then
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

# Optional explicit component targets:
sudo ./scripts/install.sh verify zombie
sudo ./scripts/install.sh doctor forgejo
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
# Remove everything (default):
sudo ./scripts/install.sh uninstall

# Remove only the zombie account and runtime, leave Forgejo running:
sudo ./scripts/install.sh uninstall zombie

# Remove only the Forgejo component, leave zombie running:
sudo ./scripts/install.sh uninstall forgejo

# Remove only the Forgejo Actions runner:
sudo ./scripts/install.sh uninstall forgejo-runner

# Safely remove the Llama runtime while retaining its models and state:
sudo ./scripts/install.sh uninstall llama
```

Selective uninstall targets only the named component. `--archive` and
`--keep-agent` are valid only when the `zombie` component is being
removed. Complete Llama state deletion requires the product command and its
exact destructive confirmation; see the product installation guide above.

The uninstaller removes Ubuntu Zombie services, sudoers entries,
payload files, policy, logrotate rules, and optionally the agent account
and archives. Shared packages such as Node and Python are left alone.
