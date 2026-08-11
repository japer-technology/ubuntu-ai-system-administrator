# Positioning & Value Propositions

## Positioning statement

> **For** owners of Ubuntu Desktop LTS machines who maintain their own
> computers but aren't full-time sysadmins,
> **Ubuntu Zombie** is an AI Systems Administrator that lives inside the
> machine
> **that** lets them diagnose, repair, and operate the PC in plain language
> under explicit approval,
> **unlike** generic AI chat assistants or remote IT services,
> **because** it acts with real root authority on the actual machine, gates
> every privileged action behind the operator's approval, audit-logs
> everything, and leaves the operator holding every key and the kill switch.

## Target audiences

| Audience | Pain | What lands |
| -------- | ---- | ---------- |
| Tinkerers / homelab / self-hosters | Tedious diagnosis; fear of breaking the box | Dry-run plans, audit log, reversible install, optional self-hosted Forgejo forge |
| Small-business / solo operators | No IT department; downtime costs money | "A sysadmin on call inside the PC" |
| Linux-curious power users | Command-line friction | Plain-language chat that still shows the commands |
| Security-minded developers | Distrust of agentic AI | Policy gate, loopback-only chat, password gate, built-in TTL, open bash installer |
| Privacy-first / offline users | Won't send machine state to a cloud API | Local LLM support (LM Studio, Ollama, `llama.cpp`) — fully offline, no cloud key |

## Core value propositions

1. **It actually administers the machine.** Not advice you have to retype — a
   root-capable account that runs the commands, after you approve them.
2. **You approve before anything privileged happens.** A local policy gate
   classifies destructive/networked/system-altering actions and surfaces them
   first.
3. **Everything is audit-logged.** What was asked, proposed, approved, and done
   — all recorded and inspectable.
4. **You hold every key.** LLM API key, chat password, policy file, TTL, kill
   switch. Rotate or revoke any of them at any time.
5. **Local-first and private.** The only listener is a password-protected chat
   on `127.0.0.1`; the installer provisions no SSH, VNC, or inbound remote
   access. Pair it with a local LLM and it never touches the cloud.
6. **It expires by default.** A built-in Time to Live permanently disables the
   administrator unless you renew it from the chat — a dead-man's switch, not
   an unattended root daemon.
7. **Transparent and reversible.** A bash installer on a normal Ubuntu LTS
   system. Inspect every component; `uninstall` reverses it.

## Proof points (link these, don't just assert them)

- `install --dry-run` previews the entire plan with zero changes.
- `verify`, `doctor`, and `repair` subcommands for read-only checks and
  known-safe fixes — per component (`zombie`, `forgejo`).
- Interactive installs LAN-scan for an OpenAI-compatible local LLM server and
  can run fully offline; `/lmstudio` re-discovers one at runtime.
- Chat password stored only as a PBKDF2 hash; TTL default 7 days with
  `/ttl --die` as an immediate kill switch.
- Signed `.deb` releases with SHA-256 checksums and keyless cosign signatures.
- CI, CodeQL, and an OpenSSF Scorecard badge on the repository.
- Full trust boundary documented in [`../../SECURITY.md`](../../SECURITY.md).

## Objection handling

| Objection | Response |
| --------- | -------- |
| "Root-capable AI sounds dangerous." | Correct to be cautious. That's why every privileged action is gated behind your approval, audit-logged, TTL-limited, and reversible — read `SECURITY.md` before installing. |
| "Does it phone home / is it a hosted service?" | No. It's an open bash installer; the only listener is a loopback-only chat; you configure your own LLM provider key and can rotate or remove it. |
| "What if the AI does something wrong?" | Nothing privileged runs without your approval, and everything is logged. `doctor`/`repair`/`uninstall` are first-class. |
| "Local inference?" | Yes — point it at LM Studio, Ollama, or `llama.cpp`; the installer can auto-detect a local server on your LAN and run with no cloud key at all. Cloud providers remain an option. |
| "What if I forget it's installed?" | It forgets itself first: the built-in TTL permanently disables the administrator unless you renew it. |

## Competitive framing (neutral, factual)

- **vs. a generic AI chatbot:** Ubuntu Zombie has hands — it can run the fix on
  the real machine, gated by approval — not just describe one.
- **vs. remote IT / managed services:** No third party holds the keys; the
  operator does. It's local, private, and auditable.
- **vs. autonomous "agent" frameworks:** Deliberately *not* autonomous. One
  machine, one operator, approval before privilege — and a built-in expiry.
- **vs. a hosted "AI ops" platform:** Nothing leaves the machine unless you
  choose a cloud provider; with a local LLM it runs entirely offline.
