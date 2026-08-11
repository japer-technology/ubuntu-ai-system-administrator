---
title: "Ubuntu Zombie: your computer, with an administrator inside it"
slug: introducing-ubuntu-zombie
author: "[AUTHOR]"
date: "[YYYY-MM-DD]"
tags: [ubuntu, linux, ai, open-source, sysadmin]
description: >
  Ubuntu Zombie adds a private, root-capable AI Systems Administrator to your
  Ubuntu desktop — one that proposes, waits for your approval, acts, and logs.
canonical_url: "[CANONICAL URL]"
hero_image: "../assets/og-banner.png"
---

<!--
  DRAFT — launch announcement / blog post.
  Replace bracketed fields, drop in real screenshots from assets/, and read it
  aloud once for tone (calm, honest, concrete) before publishing.
-->

# Ubuntu Zombie: your computer, with an administrator inside it

Personal computers have become powerful enough to run real workloads — and
complex enough that most owners cannot safely operate them. When something
breaks, the distance between *"my laptop is broken"* and *"here is the exact
`systemd` unit, kernel parameter, or `apt` pin that fixes it"* gets filled by a
friend, a forum thread, or a paid technician.

**Ubuntu Zombie closes that gap on the machine itself.**

## What it is

Ubuntu Zombie is an open-source, transparent bash installer that adds a private,
root-capable **AI Systems Administrator** account to a supported Ubuntu Desktop
LTS machine (22.04 / 24.04). After it's installed, any local user can open a
private chat, ask the machine — in plain language — to do something, see exactly
what is proposed, approve it, and watch it happen. Every action is audit-logged.

It's still an ordinary Ubuntu PC for the human in front of it. It's also,
simultaneously, the home of an administrator that lives inside it. That's the
whole idea — and it's why the logo is a single head split down the middle: a
calm white robot fused to a weathered human skull, sharing one glowing purple
eye. (The full symbolism is in
[`LOGO-MEANING.md`](https://github.com/japer-technology/ubuntu-zombie/blob/main/LOGO-MEANING.md).)

> [SCREENSHOT: the local chat UI proposing a fix]

## How a request works

1. **You ask.** "Why is my Wi-Fi dropping after suspend?"
2. **It proposes.** The administrator explains the likely cause and shows the
   exact commands it would run.
3. **You approve.** Destructive, networked, or system-altering actions pass
   through a local policy gate and wait for your yes.
4. **It acts.** The commands run with real authority on the real machine.
5. **It logs.** What was asked, proposed, approved, and done — all written down
   and inspectable afterwards.

> [SCREENSHOT: an approval prompt + an audit-log excerpt]

## Built around keeping you in control

This project grants a root-capable identity on your machine, and it is honest
about that. Every design decision points back at the operator:

- A dedicated `zombie` Linux account (renameable) holds passwordless `sudo` and
  is the operating identity of the agent — never a shared human login.
- The **only** network surface is the chat UI, bound to `127.0.0.1` and gated
  by a password (stored only as a PBKDF2 hash). The installer provisions no
  SSH, no VNC, and no inbound remote access — remote reach is a tunnel you set
  up yourself. The public internet is never a control plane.
- It **expires by default**. A built-in Time to Live (default seven days)
  permanently disables the administrator unless you renew it from the chat —
  and `/ttl --die` trips the kill switch immediately.
- Revocation is first-class. Trip the TTL, rotate or remove the provider API
  key, disable the service, or run `uninstall`, and the agent stops.

You own the machine, the API key, the chat password, and the kill switch.

## Bring your own model — cloud or fully local

Inference is yours to choose. Configure a cloud provider with your own API key
(OpenAI, Anthropic, Gemini, xAI, Mistral, Groq, or OpenRouter) — or point it
at a local OpenAI-compatible server such as LM Studio, Ollama, or `llama.cpp`.
During an interactive install it will even scan your LAN, find a local server,
and offer its models, so the whole system can run **fully offline with no
cloud key at all**. At runtime, `/lmstudio` re-discovers a server, `/models`
lists what's available, and `/model` switches.

## What it deliberately does not do

- It is **not autonomous**. It listens, proposes, and waits.
- It does **not** manage fleets, and it does **not** replace the humans already
  using the desktop. It installs *beside* them, not *over* them.
- It does **not** stay around forever: unless you renew its Time to Live, it
  turns itself off.

## Optional extras, off by default

The baseline can be extended with opt-in components — all off by default,
idempotent, and individually removable. The first is a self-hosted **Forgejo**
git forge: PostgreSQL-backed, served over LAN HTTPS at your machine's `.local`
name, with an optional CI runner. `sudo ./scripts/install.sh install forgejo`
sets it up standalone; `uninstall forgejo` removes just that piece.

## Try it (safely) in two minutes

```bash
git clone https://github.com/japer-technology/ubuntu-zombie.git
cd ubuntu-zombie
chmod +x scripts/install.sh
sudo ./scripts/install.sh install --dry-run   # preview the plan, change nothing
```

When you're ready, drop the `--dry-run`. Prefer a package? Each release ships a
signed `ubuntu-zombie_<version>_all.deb` with a SHA-256 checksum and keyless
cosign signatures.

**Read [`SECURITY.md`](https://github.com/japer-technology/ubuntu-zombie/blob/main/SECURITY.md)
before you run the installer.** It documents the trust boundary and exactly what
the provider sees.

## Get involved

- ⭐ Star the repo: <https://github.com/japer-technology/ubuntu-zombie>
- Read the vision and non-goals:
  [`docs/VISION.md`](https://github.com/japer-technology/ubuntu-zombie/blob/main/docs/VISION.md)
- Ask questions in
  [Discussions](https://github.com/japer-technology/ubuntu-zombie/discussions)

*Ubuntu is a trademark of Canonical Ltd. Ubuntu Zombie is an independent,
third-party project and is not affiliated with Canonical. Released under the MIT
Licence by Japer Technology.*
