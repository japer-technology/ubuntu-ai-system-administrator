# Launch & Newsletter Emails

Plain-text-friendly drafts. Replace bracketed fields. Keep subject lines short
and honest — no clickbait.

---

## Launch announcement email

**Subject lines (pick / A-B test):**
- Your Ubuntu PC can now administer itself — with your approval
- Introducing Ubuntu Zombie: an AI sysadmin that lives in your machine
- Ask your computer to fix itself (you approve every step)

**Preheader:** Open source, root-capable, audit-logged, and you hold the kill
switch.

**Body:**
> Hi [FIRST NAME],
>
> Today we're releasing **Ubuntu Zombie** — an open-source tool that adds a
> private, root-capable AI Systems Administrator to your Ubuntu Desktop LTS
> machine.
>
> Here's the whole idea: you open a private chat on your own machine, ask it —
> in plain English — to diagnose, configure, or repair something, and it shows
> you the exact commands it would run. You approve. It acts. Every step is
> written to an audit log.
>
> It's built around keeping you in control:
>
> • A local policy gate makes privileged actions wait for your approval
> • The only network surface is a password-protected chat on 127.0.0.1
> • A built-in Time to Live disables it unless you renew it — and you hold the kill switch
> • Bring your own cloud LLM key, or run fully offline with a local model
> • It's a transparent bash installer — inspect every line; `uninstall` reverses it all
>
> Want to look before you leap? Preview the entire install without changing
> anything:
>
>     sudo ./scripts/install.sh install --dry-run
>
> ▶ Get started: https://github.com/japer-technology/ubuntu-zombie
> ▶ Read the trust model first: SECURITY.md
>
> Questions? Just reply, or open a Discussion on GitHub.
>
> — [YOUR NAME], Japer Technology
>
> Ubuntu is a trademark of Canonical Ltd. Ubuntu Zombie is an independent
> project, not affiliated with Canonical. MIT-licensed.
> [Unsubscribe] · [View in browser]

---

## Developer-newsletter blurb (for inclusion in others' newsletters, ≤ 80 words)

> **Ubuntu Zombie** — A private, root-capable AI Systems Administrator for
> Ubuntu Desktop LTS. Ask your machine to diagnose and fix itself in plain
> English; it proposes the commands, you approve, it acts, and everything is
> audit-logged. Local-first (a password-protected chat on 127.0.0.1 is the only
> network surface), works with your own cloud key or a fully local LLM, expires
> unless renewed, MIT-licensed, fully reversible. Preview it with `--dry-run`.
> https://github.com/japer-technology/ubuntu-zombie

---

## Follow-up email (T+7, to non-openers / for engagement)

**Subject:** What people asked us about Ubuntu Zombie

> Hi [FIRST NAME],
>
> Since we launched Ubuntu Zombie last week, the most common question has been
> the most important one: *"A root-capable AI — is that safe?"*
>
> Short answer: nothing privileged runs without your approval, every action is
> logged, it expires unless you renew it, and the whole thing is reversible.
> The long answer — the full trust boundary and what the LLM provider sees —
> is in SECURITY.md, and it's worth five minutes before you install.
>
> If you haven't tried it yet, start with the no-changes preview:
> `sudo ./scripts/install.sh install --dry-run`.
>
> Repo & docs: https://github.com/japer-technology/ubuntu-zombie
>
> — [YOUR NAME]
