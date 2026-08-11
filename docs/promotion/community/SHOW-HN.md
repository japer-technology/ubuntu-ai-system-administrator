# Show HN

Guidance: Hacker News rewards plain, technical, honest posts. Lead with what it
is and the trust model. Expect — and welcome — hard questions about security.
Disclose that you are the author. No marketing language.

## Title (≤ 80 chars, pick one)

- `Show HN: Ubuntu Zombie – a root-capable AI sysadmin for your Ubuntu desktop`
- `Show HN: An approval-gated, audit-logged AI sysadmin that lives in your PC`
- `Show HN: Ubuntu Zombie – ask your machine to fix itself, approve every step`

## Body (first comment)

> Hi HN — I'm the author.
>
> Ubuntu Zombie is a transparent bash installer that adds a private,
> root-capable AI Systems Administrator account to a supported Ubuntu Desktop
> LTS machine (22.04 / 24.04). You open a private, password-protected chat on
> 127.0.0.1, ask the machine — in plain English — to diagnose, explain,
> configure, repair, or operate itself, and it proposes the exact commands it
> would run. You approve; it acts; every action is written to an audit log.
>
> The design is built around keeping the operator in control:
>
> - A dedicated `zombie` Linux account (renameable) with passwordless sudo is
>   the operating identity of the agent — never a shared human login.
> - Privileged / destructive / networked actions are classified and pass
>   through a local policy gate that requires your approval before running.
> - The only network surface is the chat UI, bound to 127.0.0.1 and gated by a
>   password (stored only as a PBKDF2 hash). The installer provisions no SSH,
>   VNC, or other inbound access — remote reach is a tunnel you set up
>   yourself.
> - It expires by default: a Time to Live (default 7 days) permanently
>   disables the agent unless you renew it from the chat, and `/ttl --die`
>   kills it immediately.
> - Revocation is first-class: trip the TTL, rotate or remove the provider API
>   key, disable the service, or run `uninstall`, and the agent stops.
>
> Inference is bring-your-own: a cloud provider with your key (OpenAI,
> Anthropic, Gemini, xAI, Mistral, Groq, OpenRouter) or a local
> OpenAI-compatible server (LM Studio, Ollama, llama.cpp). The installer can
> auto-detect a local server on your LAN, so it runs fully offline with no
> cloud key at all.
>
> What it deliberately does NOT do: run autonomously, manage fleets, or
> replace the humans already using the desktop.
>
> You can preview the entire install with `sudo ./scripts/install.sh install
> --dry-run` (changes nothing), and `verify`/`doctor`/`repair` subcommands
> check and converge the install afterwards. Signed `.deb` releases are
> available with SHA-256 checksums and keyless cosign signatures.
>
> Trust model and what the provider sees: SECURITY.md. Vision and the explicit
> non-goals: docs/VISION.md.
>
> Repo: https://github.com/japer-technology/ubuntu-zombie
>
> Happy to answer questions about the policy gate, the audit log, the threat
> model, or anything else.

## Prepared answers (have these ready)

- **"Root-capable AI is terrifying."** Agreed it deserves caution — that's why
  nothing privileged runs without your approval, everything is logged, it
  expires unless renewed, and it's fully reversible. Point to `SECURITY.md`.
- **"What's actually sent to the LLM?"** Walk through the trust boundary in
  `SECURITY.md`; be specific and honest. With a local model, nothing leaves
  the machine.
- **"Why not local models?"** They're supported: point it at LM Studio,
  Ollama, or llama.cpp — the installer even scans the LAN for one. Cloud
  providers are optional.
- **"Isn't this just a wrapper around a chatbot + sudo?"** Explain the policy
  gate, action classification, approval flow, audit log, and TTL — that's the
  product, not the chat.
- **"Prompt injection?"** The provider's output only executes through the
  approval gate; review the proposed commands before approving. It's in
  `SECURITY.md` under known risks.

## Etiquette
- Post it yourself, engage in the thread for the first few hours.
- Never ask for upvotes; never use multiple accounts.
- Concede valid criticism gracefully — it builds more trust than defending.
