# FAQ

## What does Ubuntu Zombie install?

A dedicated local Linux account, a loopback-only chat service, pi-mono
runtime files, operator helpers, policy, audit logging, and systemd
units. It does not install remote-access, VNC, Docker, autologin, or GUI
automation stacks.

## How do I access it?

Open `http://127.0.0.1:7878/` on the Ubuntu Zombie machine. The service
binds to loopback only. If you need remote access, provide it outside
Ubuntu Zombie.

## Does the agent have root?

Yes. The agent account has passwordless sudo by design. The policy gate,
approval flow, TTL, and audit log are the safety controls.

## Where do provider keys go?

Use:

```bash
sudo /opt/ai-zombie/bin/secrets-edit
sudo systemctl restart ubuntu-zombie-chat.service
```

The secrets file is mode `0600`; diagnostics and audit logging redact
provider keys and token-shaped values.

## Can I add more skills?

Yes. Place Markdown skill briefs in `/etc/ubuntu-zombie/skills.d/`.
Skills can guide the model but cannot add tools; the closed registry is
implemented in `payload/agent/tools.py`.

## How do I remove it?

Run:

```bash
sudo ./scripts/install.sh uninstall
```

Shared runtime packages such as Node and Python are left alone because
other software may depend on them.
