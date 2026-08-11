# Social Posts

Ready-to-edit copy per platform. Replace `[LINK]`, `[SCREENSHOT]`, and dates
before posting. Keep British spelling. One idea per post; lead with control and
honesty, not hype (see [`../brand/VOICE-AND-TONE.md`](../brand/VOICE-AND-TONE.md)).

---

## X / Twitter

### Launch post
> Ubuntu Zombie: a private, root-capable AI Systems Administrator that lives
> inside your Ubuntu desktop.
>
> Ask it to fix your machine in plain English → it shows the exact commands →
> you approve → it runs them → every step is logged.
>
> Open source, MIT. [LINK]
> [SCREENSHOT: local chat proposing a fix]

### Thread (5 posts)
1. Most of us own computers we can't safely operate. When something breaks, the
   gap between "it's broken" and "here's the exact fix" is a forum thread or a
   paid technician. We built Ubuntu Zombie to close that gap on the machine
   itself. 🧵
2. It adds a dedicated, root-capable Linux account — the operating identity of
   an AI Systems Administrator. You open a private chat on 127.0.0.1 and ask in
   plain language.
3. Anything privileged passes through a local policy gate and waits for YOUR
   approval before it runs. You see exactly what's proposed first.
4. Everything is audit-logged: what was asked, proposed, approved, and done.
   The only network surface is a password-protected chat on 127.0.0.1 — no
   SSH, no VNC, no inbound remote access.
5. You own the API key, the chat password, and the kill switch. It even has a
   built-in Time to Live: unless you renew it, it disables itself. `uninstall`
   reverses it. It's a transparent bash installer — inspect every line. [LINK]

### Single-feature posts (schedule across the week)
- "Preview before you commit: `install --dry-run` shows the entire plan and
  changes nothing." [SCREENSHOT]
- "`doctor` explains failures. `repair` fixes known-safe drift. `verify` is a
  read-only state check — per component." [SCREENSHOT]
- "Every action it takes is written to an audit log you can read." [SCREENSHOT]
- "No cloud key? No problem. The installer auto-detects LM Studio, Ollama, or
  llama.cpp on your LAN and runs fully offline." [SCREENSHOT]
- "It expires by design. A built-in Time to Live disables the administrator
  unless you renew it — and `/ttl --die` kills it instantly." [SCREENSHOT]
- "Optional: a self-hosted Forgejo git forge at https://your-pc.local, with
  PostgreSQL and an Actions runner. One command, fully reversible." [SCREENSHOT]

---

## Bluesky
> Your Ubuntu PC, with a sysadmin living inside it. Ask it to diagnose and fix
> things in plain English — it proposes, you approve, it acts, it logs.
> Root-capable but never autonomous. Open source (MIT). [LINK]

---

## Mastodon (fediverse — technical, no hype)
> #UbuntuZombie adds a private, root-capable AI Systems Administrator to Ubuntu
> Desktop LTS. Plain-language chat on 127.0.0.1 (password-protected, the only
> network surface), a policy gate that needs your approval before any
> privileged action, full audit logging, a built-in Time to Live, and support
> for fully local LLMs (LM Studio / Ollama / llama.cpp). Transparent bash
> installer, MIT-licensed. Trust model is documented up front.
> #Linux #Ubuntu #FOSS #SelfHosted
> [LINK]

---

## LinkedIn
> **You own computers you can't fully operate. Ubuntu Zombie helps you operate
> them — on your terms.**
>
> It installs a private, root-capable AI Systems Administrator onto a supported
> Ubuntu Desktop LTS machine. You ask the computer, in plain language, to
> diagnose, configure, repair, or operate itself. It proposes the exact
> commands; you approve; it acts; every step is audit-logged.
>
> What makes it different from a chatbot: it has hands on the real machine.
> What makes it safe: a policy gate, explicit approval, a password-protected
> loopback-only chat as the sole network surface, a built-in Time to Live, and
> a kill switch the operator holds — not a vendor. It can even run fully
> offline against a local LLM.
>
> Open source, MIT-licensed. Read the trust model before you run it. [LINK]
>
> #Linux #Ubuntu #OpenSource #SysAdmin #AI

---

## Reddit (see community/ for full launch posts)
Keep Reddit community-first and disclose authorship. Drafts live in
[`../community/REDDIT.md`](../community/REDDIT.md).
