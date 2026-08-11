# Security

Ubuntu Zombie installs a privileged AI Systems Administrator on a
normal Ubuntu PC. This is a meaningful security posture and you should
read it before running the installer.

## Trust boundary

The operator owns:

- the physical machine,
- the LLM provider account and API key,
- the chat-UI password,
- `/opt/ai-zombie/secrets/env`.

The token provider (cloud LLM vendor) authenticates the AI Systems
Administrator. The provider does **not** own the machine.

The `agent` Linux user is the operating identity of the AI Systems
Administrator. `agent` holds passwordless `sudo`. Any compromise of
`agent` or of the provider API key is equivalent to root on the
machine.

Treat these credentials with root-level care:

- the LLM provider API key in `/opt/ai-zombie/secrets/env`;
- the chat-UI password (stored only as a PBKDF2 hash in
  `/opt/ai-zombie/secrets/env`).

## What the provider sees

The chat service sends to the provider:

- the operator's typed prompts;
- visible synthetic prompts previously scheduled by `timer.reactivation`;
- the current conversation history;
- selected local context (e.g. `uname`, package versions, summarised
  command output) that the assistant explicitly chose to include.

The provider may see, in summarised form, the **output** of commands
the assistant runs on the machine. Treat the provider as a third
party with read access to whatever local state the assistant decides
to share with it.

The agent can schedule one future continuation. It is bounded by the configured
minimum and maximum delay and the remaining TTL, appears in the authenticated
chat UI with a cancel control, and starts a normal policy-gated turn. Scheduling
does not execute tools, inherit approvals, bypass authentication, or bypass the
TTL. A malicious prompt or file could still persuade the model to request a
future turn, so operators should cancel unexpected reactivations or disable the
feature with `/reactivation off`.

The provider does not see:

- the LLM API key beyond your own account scope;
- the chat-UI password;
- files under `/opt/ai-zombie/secrets/`;
- audit log contents (the audit log is local-only).

## What the `agent` user can do

- Run any command as root via `sudo`, without a password prompt.
- Read and write any file the desktop session can reach.
- Listen on `127.0.0.1` for the chat UI.

The MVP adds a policy gate (`/etc/ubuntu-zombie/policy.yaml`) and an
approval flow between the AI and `sudo`. Read-only diagnostics run
automatically; everything else requires approval; destructive actions
require a confirmation phrase. See `ARCHITECTURE.md` for the classes.

## Network exposure

- Chat (default port 7878): bound to `127.0.0.1` only.
- Optional standalone llama.cpp (port 8080): bound to `127.0.0.1` only
  and intentionally available to every local user.

The default install does not provision SSH, Tailscale, VNC, a
configured firewall, or any other inbound network surface. The default
listener is the loopback-only chat service; the opt-in standalone llama
component adds only a loopback listener. To reach the chat remotely,
forward the loopback port
over a transport you control (for example an SSH tunnel you set up
yourself).

## Rotating credentials

| Credential          | How to rotate                                   |
| ------------------- | ----------------------------------------------- |
| LLM provider key    | `sudo /opt/ai-zombie/bin/secrets-edit`, then `systemctl restart ubuntu-zombie-chat` |
| Chat-UI password    | Use the `/password` chat command, or re-run the installer |

## Revoking the agent

Minimum: remove every provider API key, then restart the chat
service. The chat will load but refuse to reach a provider.

Stronger: `sudo systemctl disable --now ubuntu-zombie-chat.service`.

Strongest: `sudo ./scripts/install.sh uninstall`. The uninstaller removes
the chat service, sudoers drop-in, and generated helpers, optionally
removing the `agent` user and archiving state.

## Known risks

- **Passwordless sudo.** Intentional, but it means compromise of
  `agent` is compromise of root. Mitigated by the loopback-only chat
  surface, the chat-UI password gate, the policy gate, and audit
  logging.
- **Cloud provider trust.** Prompts and selected machine state cross
  to the provider. Sensitive files should not be opened or summarised
  through the chat.
- **API cost.** Long sessions can become expensive. The first-run UI
  warns about this.
- **Provider prompt injection.** The provider's output is executed
  only through the approval gate; review proposed commands before
  approving.

## Audit and observability

- `/var/log/ubuntu-zombie/audit.log` — JSON-lines record of prompts,
  proposed actions, approvals, commands, exit codes, and verification
  results. Rotated by `logrotate`. Secrets are redacted at write
  time.
- `/opt/ai-zombie/bin/audit-recent` — quick view of recent activity.
- `/opt/ai-zombie/bin/health-check` — one-shot health summary.
- `/opt/ai-zombie/bin/collect-diagnostics` — bundle for bug reports;
  secrets are redacted.

## Responsible disclosure

Please report security issues privately to the maintainers of this
repository via a GitHub Security Advisory:

<https://github.com/japer-technology/ubuntu-zombie/security/advisories/new>

Do not file public issues for vulnerabilities. A 90-day coordinated
disclosure window is the default.
