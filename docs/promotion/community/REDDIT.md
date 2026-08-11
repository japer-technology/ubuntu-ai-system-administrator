# Reddit Launch Posts

Reddit is community-first. Read each subreddit's rules and self-promotion
policy before posting. **Disclose that you are the author.** Don't reuse
identical text across subreddits — adapt to each community. Link the repo and
the docs, then answer questions honestly.

Good targets: r/linux, r/Ubuntu, r/selfhosted, r/sysadmin (read rules — strict),
r/opensource, r/LocalLLaMA (lead with the local-LLM story: LAN auto-discovery,
fully offline operation).

---

## r/linux / r/opensource

**Title:** Ubuntu Zombie: an open-source, approval-gated AI Systems
Administrator that lives inside your Ubuntu desktop

**Body:**
> I built Ubuntu Zombie (MIT, author here). It's a transparent bash installer
> that adds a private, root-capable AI Systems Administrator account to Ubuntu
> Desktop LTS (22.04 / 24.04).
>
> You open a private, password-protected chat on 127.0.0.1 and ask the
> machine, in plain English, to diagnose, explain, configure, repair, or
> operate itself. It proposes the exact commands; a local policy gate makes
> privileged actions wait for your approval; it runs them; everything is
> audit-logged and reversible.
>
> Control specifics: dedicated `zombie` account (renameable) holds the sudo
> authority — not a human login; the loopback chat is the only network surface
> (no SSH, VNC, or inbound access is provisioned); a built-in Time to Live
> disables the agent unless you renew it; `/ttl --die` is an instant kill
> switch; `uninstall` reverses everything.
>
> It deliberately is NOT autonomous and NOT a hosted service. Inference is
> bring-your-own: a cloud provider with your key, or a local LLM (LM Studio,
> Ollama, llama.cpp) for fully offline operation — the installer can
> auto-detect one on your LAN.
>
> Preview the whole thing with `install --dry-run` (no changes). Trust model:
> SECURITY.md. Repo: https://github.com/japer-technology/ubuntu-zombie
>
> Feedback welcome, especially on the security posture.

---

## r/selfhosted

**Title:** Self-hosted, root-capable AI sysadmin for Ubuntu LTS — local-first,
audit-logged, you hold the keys

**Body:**
> For the self-hosting crowd: Ubuntu Zombie installs a root-capable AI Systems
> Administrator onto your own Ubuntu LTS box. No third party holds the keys —
> you do. The only listener is a password-protected chat on 127.0.0.1; remote
> reach is a tunnel you set up yourself; and a built-in Time to Live disables
> the whole thing unless you renew it.
>
> You ask it (plain English) to fix or configure things; it proposes commands;
> you approve; it acts; it logs. It can run fully offline against LM Studio,
> Ollama, or llama.cpp — no cloud key needed. Optional extra: a self-hosted
> Forgejo git forge (PostgreSQL-backed, LAN HTTPS at your machine's `.local`
> name, optional CI runner), installable and removable on its own.
>
> Signed `.deb` releases with checksums + cosign signatures. MIT-licensed,
> open bash installer — inspect everything. Repo + docs:
> https://github.com/japer-technology/ubuntu-zombie — happy to answer anything.

---

## r/Ubuntu

**Title:** Made a tool that lets you ask your Ubuntu machine to fix itself (with
your approval, fully logged)

**Body:**
> Author here. Ubuntu Zombie adds a private AI Systems Administrator to Ubuntu
> Desktop LTS. When something breaks, you ask the machine in plain English; it
> shows you the exact commands it would run; you approve; it does it; and it
> keeps an audit log. The chat is password-protected and bound to localhost —
> the only network surface — and the whole thing expires unless you renew it.
> `uninstall` reverses it all.
>
> Supports 22.04 and 24.04. Open source (MIT). Works with your own cloud LLM
> key or a fully local model. Try `install --dry-run` first to see the plan
> with zero changes. https://github.com/japer-technology/ubuntu-zombie

---

## r/LocalLLaMA

**Title:** An approval-gated AI sysadmin for Ubuntu that runs against your
local LM Studio / Ollama / llama.cpp server — fully offline

**Body:**
> Author here. Ubuntu Zombie adds a root-capable AI Systems Administrator
> account to Ubuntu Desktop LTS, driven from a private loopback chat. The part
> this sub might care about: it's local-model-first friendly. During install
> it scans your LAN for an OpenAI-compatible server (LM Studio, Ollama,
> llama.cpp), offers the models it finds, and wires itself up to run fully
> offline — no cloud API key at all. At runtime, `/lmstudio` re-discovers a
> server (loopback first, then LAN), `/models` lists what's loaded, and
> `/model <id>` switches.
>
> Guardrails: every privileged action passes a local policy gate and waits for
> approval, everything is audit-logged, the chat is password-protected on
> 127.0.0.1, and a built-in TTL disables the agent unless renewed. MIT, open
> bash installer. https://github.com/japer-technology/ubuntu-zombie

---

## Etiquette reminders
- One post per subreddit; space them out; follow each sub's frequency rules.
- Reply to comments; treat criticism as a gift.
- Never vote-manipulate or use alt accounts.
