# Key Features & Approved Claims

The canonical list of claims the promotion kit is allowed to make, each with
the repository source that backs it. If a claim is not on this list (or in
[`../../README.md`](../../README.md) / [`../../docs/VISION.md`](../../docs/VISION.md)),
don't make it. When the product changes, update this file first, then the
channel copy.

## Approved claims

| Claim (safe wording) | Backed by |
| -------------------- | --------- |
| Adds a private, root-capable AI Systems Administrator account (default name `zombie`, renameable) to Ubuntu Desktop LTS 22.04 / 24.04 | `README.md`, `docs/PLATFORMS.md` |
| The only network surface is a password-protected chat UI on `127.0.0.1:7878`; no SSH, VNC, Tailscale, or other inbound access is provisioned | `SECURITY.md` → Network exposure |
| The chat password is stored only as a PBKDF2 hash | `SECURITY.md`, `docs/CONFIGURATION.md` → Chat access |
| The administrator has a Time to Live (default 7 days) and permanently disables itself unless renewed; `/ttl --die` trips the kill switch immediately | `README.md`, `docs/CONFIGURATION.md` → `/ttl` commands |
| Privileged actions are classified by a local policy gate and wait for operator approval; destructive actions need a confirmation phrase | `SECURITY.md`, `docs/ARCHITECTURE.md`, `payload/etc/policy.yaml` |
| Every prompt, proposal, approval, command, and result is written to a local-only, rotated audit log | `SECURITY.md` → Audit and observability |
| Works with the operator's own cloud key (OpenAI, Anthropic, Gemini, xAI, Mistral, Groq, OpenRouter) **or** a local LLM server (LM Studio, Ollama, `llama.cpp`) — fully offline is possible | `docs/CONFIGURATION.md` → Providers, Local LLM discovery |
| Interactive installs LAN-scan for a local OpenAI-compatible server and offer its models; `/lmstudio` re-discovers one at runtime, `/models` lists models, `/model` switches | `README.md`, `docs/CONFIGURATION.md` |
| `install --dry-run` previews the entire plan and changes nothing | `README.md` Quickstart |
| One command grammar: `install` / `verify` / `doctor` / `repair` / `uninstall`, per component (`zombie`, `forgejo`) | `README.md` → Installer command grammar |
| Optional, off-by-default components extend the baseline — first: a self-hosted Forgejo git forge (PostgreSQL, `.local` LAN HTTPS via Caddy's internal CA, optional Actions runner), installable standalone with `install forgejo` | `README.md` → Optional components, `docs/CONFIGURATION.md` |
| Fully reversible: `uninstall` removes services, sudoers rules, and helpers, and can remove the account and archive state | `SECURITY.md` → Revoking the agent |
| Releases ship a signed `.deb` with SHA-256 checksums and keyless cosign signatures | `README.md`, `docs/QUICKSTART.md` |
| Open source, MIT licence, readable bash + Python, no binaries | `LICENSE`, `README.md` |

## Claims we must NOT make

- ~~"Key-only SSH, root login disabled"~~ — the installer does not touch SSH.
- ~~"Remote access over Tailscale"~~ — no Tailscale; remote reach is a tunnel
  the operator sets up themselves.
- ~~"Emergency VNC / remote desktop"~~ — no VNC or secondary desktop path.
- ~~"Local inference is roadmap only"~~ — local LLMs are shipped, not roadmap.
- Anything implying autonomy, fleet management, or a hosted service.

## Feature-drip topics (for social scheduling)

1. `install --dry-run` — the whole plan, zero changes.
2. The audit log — everything asked, proposed, approved, done.
3. `verify` / `doctor` / `repair` — read-only checks and known-safe fixes.
4. Local LLM auto-discovery — fully offline, no cloud key.
5. Time to Live — the administrator that expires unless you renew it.
6. `/ttl --die` — the one-command kill switch.
7. Optional Forgejo forge — your own git server at `https://<host>.local`.
8. Signed `.deb` + checksums + cosign — verify before you install.
