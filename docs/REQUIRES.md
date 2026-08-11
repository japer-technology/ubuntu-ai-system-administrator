# Requirements

Ubuntu Zombie targets Ubuntu Desktop LTS and installs one local access
surface: the password-protected chat UI bound to `127.0.0.1`.

## Host

- Ubuntu Desktop 22.04 LTS or 24.04 LTS (`amd64` supported; `arm64`
  best-effort).
- `systemd`.
- `sudo` access for installation.
- Outbound HTTPS to Ubuntu apt mirrors, NodeSource, npm, PyPI, and the
  configured LLM provider.

## Operator inputs

Interactive installs prompt through a parameter review. Non-interactive
installs may set these environment variables:

| Variable | Purpose |
| -------- | ------- |
| `ZOMBIE_USER` | Agent account name; default `zombie`. |
| `ZOMBIE_DIR` | Install root; default `/opt/ai-zombie`. |
| `ZOMBIE_CHAT_PORT` | Loopback chat port; default `7878`. |
| `ZOMBIE_ADMIN_PASSWORD` | Chat password; default `braaaains`. |
| `ZOMBIE_TTL_DAYS` | Initial Time to Live; default `7`. |
| `ZOMBIE_LOCAL_LLM_MODE` | Local LLM detection mode; default `auto`. |

Provider API keys are added after installation with
`/opt/ai-zombie/bin/secrets-edit`.

## Installed package families

The installer uses Ubuntu packages for Python, systemd integration,
common build/runtime tools, and NodeSource Node.js 22.x for the pi
bridges. It no longer installs SSH server hardening, Tailscale, VNC,
Docker, graphical autologin, browser automation, or GUI-control package
sets.
