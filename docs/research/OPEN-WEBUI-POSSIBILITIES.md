# Open WebUI Possibilities (`open-webui/open-webui`)

This document is a research note in the same family as
[`ALTERNATIVES.md`](ALTERNATIVES.md) and the `ALTERNATIVE-*.md` deep
dives, but it asks a different question. The alternatives essays read
*competitors* — other attempts to put an AI sysadmin on a Linux box.
[Open WebUI](https://github.com/open-webui/open-webui) is not a
competitor. It is the most successful self-hosted **chat surface** in
the ecosystem (~145k stars at the time of writing), and the question
here is:

> **What could Ubuntu Zombie's chat learn from, borrow from, or
> integrate with Open WebUI to become far more powerful — without
> betraying the trust model in [`VISION.md`](../VISION.md) and
> [`ARCHITECTURE.md`](../ARCHITECTURE.md)?**

The answer is examined capability by capability, with the same
verdict vocabulary the alternative essays use: **borrow** (re-implement
the idea in Zombie's small stdlib codebase), **translate** (adopt the
concept but reshape it for a single-operator root-capable agent),
**integrate** (connect the two products at an API boundary), **defer**
(good idea, wrong time), and **refuse** (incompatible with the trust
model).

Research date: 2026-07-09. Version examined: Open WebUI 0.10.2.

---

## 1. What Open WebUI actually is, in one paragraph

Open WebUI (formerly Ollama WebUI) is a self-hosted, offline-capable
AI chat platform: a FastAPI + SQLAlchemy Python backend (~120 direct
dependencies, SQLite or PostgreSQL, optional Redis) serving a
SvelteKit/Svelte 5 single-page app. It speaks to any inference backend
that exposes the OpenAI `/v1/chat/completions` wire format — Ollama
natively, plus OpenAI, Anthropic, Gemini, Groq, OpenRouter, LM Studio,
vLLM, and anything else via configurable connections — and it exposes
its *own* OpenAI-compatible API back out. On top of that chat core it
layers RAG with nine vector-store backends, twenty-plus web-search
providers, an in-process Python plugin system ("Functions": filters,
pipes, actions, event hooks), model-callable "Tools" including MCP and
OpenAPI tool servers, an external "Pipelines" plugin server, browser-
side Python execution via Pyodide, STT/TTS and voice calls, image
generation bridges, multi-user RBAC with groups, real-time channels,
persistent user memory, a model builder for custom agents, prompt
libraries, calendars and scheduled automations, webhooks, analytics
dashboards, and enterprise auth (OAuth/OIDC, LDAP, SCIM, trusted-header
SSO). It is deliberately maximalist: every feature ships in the
default install.

Ubuntu Zombie's chat, by contrast, is ~4,700 lines of stdlib Python
(`payload/agent/`): a single-user, password-gated, loopback-only HTTP
server (`server.py`) with SQLite history (`history.py`), a closed tool
registry (`tools.py`), a policy gate (`policy.py`), an audit log
(`audit.py`), a TTL lifecycle (`lifecycle.py`), and a pi-mono bridge
for the agent loop and provider fan-out (`providers.py`,
`pi_mono.py`). That asymmetry — a hundred-plus-dependency platform
versus a zero-dependency appliance — is the frame for everything
below.

## 2. Two facts that constrain everything

Before the feature safari, two structural facts decide what is even
on the table.

### 2.1 The license is no longer plain open source

Since 2025-04-18 (commit `60d84a3`), Open WebUI's license is BSD-3
plus a **branding clause**: licensees may not alter or remove "Open
WebUI" branding in any deployment except (i) deployments with ≤ 50
users in a rolling 30-day period, (ii) written permission, or (iii) an
enterprise license. For Ubuntu Zombie this cuts two ways:

- **Forking or embedding Open WebUI's UI as "the Zombie chat" is
  effectively off the table.** Zombie is exactly the kind of rebrand
  the clause exists to prevent, and even though a single-operator
  machine is under the 50-user threshold, shipping a rebranded fork
  *as a product* to many operators is precisely the aggregate case
  the clause targets. Legal ambiguity is not something a
  security-posture project should ship.
- **Running an unmodified Open WebUI beside Zombie is fine.** The
  license permits use; it restricts rebranding. Integration at an
  API boundary (§4) carries no license risk.
- **Learning from it is unrestricted.** Ideas, UX patterns, and API
  shapes are not licensable. Re-implementation in Zombie's own code
  is the default path for everything worth having.

Note that the companion `open-webui/pipelines` repository remains MIT.

### 2.2 The dependency footprints are irreconcilable

Open WebUI's `requirements.txt` lists ~120 direct dependencies —
PyTorch-adjacent ML stacks, Playwright with a bundled Chromium, nine
vector-DB clients, a full OpenTelemetry suite — for an installed size
around 3–5 GB. Ubuntu Zombie's contract
([`CONTRIBUTING.md`](../../CONTRIBUTING.md), `AGENTS.md`) is **no new
runtime dependencies** beyond what the installer already provisions,
and the whole payload is a few hundred kilobytes. Any "just vendor
the relevant module" instinct dies here: nothing in Open WebUI can be
lifted as code. Every borrow below means *re-implement the idea in
stdlib Python*, and every integrate means *talk HTTP across a
boundary*.

## 3. The feature safari: what Open WebUI has, and what Zombie should do about it

### 3.1 Multi-backend model connectivity — mostly already translated

Open WebUI's headline trick is treating any OpenAI-compatible
endpoint as a backend and multiplexing many of them at once. Zombie
already has the important half of this: `providers.py` registers
OpenAI, Anthropic, Gemini, xAI, Mistral, Groq, OpenRouter, and LM
Studio through the pi-ai bridge, and the server exposes model listing
and switching endpoints. What Open WebUI adds on top:

- **Multiple simultaneous connections with per-connection config**
  (`OPENAI_API_CONFIGS`). For a single-operator sysadmin agent this
  is low value. **Defer.**
- **Multi-model conversations** — the same prompt answered by
  several models side-by-side. Genuinely useful for the operator
  deciding which provider to trust with the machine ("ask two models
  before a risky change"), but it doubles cost and complicates the
  approval flow (whose tool call gets approved?). **Defer**, and if
  ever built, restrict it to `read_only`-class turns.
- **Native Ollama management** (pull/delete models from the UI).
  Zombie already discovers local LM Studio / network inference
  during install; extending the same courtesy to a local Ollama
  daemon is a small, high-value **borrow** — it keeps the "works
  with no cloud key" story strong.

### 3.2 RAG, knowledge collections, and the `#` command — translate small

Open WebUI's RAG stack (nine vector stores, hybrid BM25+vector
search, rerankers, extraction engines) is the single biggest source
of its dependency weight. Zombie must not want the stack. But it
should want three of the *ideas*:

- **Grounding the model in local documents.** Zombie's equivalent of
  a "knowledge collection" is not a PDF library — it is
  `/etc`, `/var/log`, `journalctl`, and `dpkg -l`. The agent already
  reads these through policy-gated tools. What is missing is the
  ergonomic: Open WebUI's **`#` command** lets a user pin a document
  into a turn. A Zombie translation would let the operator type
  `#/var/log/syslog` or `#systemd:nginx.service` to inject a
  policy-checked, size-clipped file or unit status into the prompt
  — reusing the existing `fs_read` tooling, no embeddings, no new
  deps. **Translate.** This is arguably the highest ratio of power
  gained to code written in this whole document.
- **Skills as knowledge.** Zombie already has markdown skills
  (`payload/agent/skills/`, `skill_loader.py`) — that *is* its RAG,
  curated instead of retrieved. Open WebUI validates the direction;
  growing the skill library (networking, disk, GPU drivers, backup)
  is cheaper and more auditable than any vector store. **Borrow the
  emphasis, not the mechanism.**
- **Automatic context compaction** past a token threshold. Zombie
  already has manual `compress_conversation`; Open WebUI ships it
  auto-triggered (off by default). Auto-triggering Zombie's existing
  summarizer when history approaches the model window is a small
  **borrow**.

Full vector RAG over the filesystem: **refuse** for now. It would
require embedding models (new deps), and a root-readable embedding
index of the whole machine is a new secret-leakage surface the threat
model in [`SECURITY.md`](../../SECURITY.md) does not need.

### 3.3 Web search — defer, and route through policy if ever

Twenty search providers injected into context is Open WebUI's answer
to stale model knowledge. Zombie's answer today is
[`docs/INTERNET-ACCESS.md`](../INTERNET-ACCESS.md): network actions
are policy-classed. A `web_fetch`/`web_search` *tool* (not a RAG
layer) that goes through `policy.py` as a `network`-class action and
gets audit-logged like everything else would be the faithful
translation — the model asks, the policy gate decides, the operator
sees it. Useful for "look up this errata / CVE / package changelog"
moments. **Defer** until a concrete need, and when built, build it as
one more closed tool in `tools.py`, never as an ambient context
injector — ambient injection of live web content into a root-capable
agent's prompt is a prompt-injection funnel.

### 3.4 Functions, Tools, Pipelines — the extensibility lesson

This is the most instructive part of Open WebUI, including its
failure modes.

Open WebUI has *four* overlapping extension systems (in-process
Functions with filter/pipe/action/event types; model-callable Tools;
external MCP/OpenAPI tool servers; the external Pipelines server) —
so many that the Pipelines README now opens with "**DO NOT USE
PIPELINES**" and redirects people to Functions. All of them execute
arbitrary Python, with `RestrictedPython` explicitly not a security
boundary, and the docs warn "don't fetch random pipelines from
sources you don't trust." On a machine where the agent has
passwordless sudo, an arbitrary-code plugin marketplace is not a
feature; it is a supply-chain attack with a UI.

Verdicts:

- **Arbitrary-code plugins (Functions/Pipelines model): refuse.**
  Zombie's closed tool registry with schema validation and policy
  classes (`tools.py`, `policy.py`) is the *correct* shape for a
  root-capable agent. Extension happens by shipping reviewed tools
  in the payload, not by loading operator-supplied code.
- **The filter concept (inlet/outlet hooks): translate, narrowly.**
  A deterministic, non-programmable filter stage — secret redaction
  on the way out (already in `audit.py`; extend to chat responses),
  size clipping, prompt-injection heuristics on tool output — is
  worth having as *fixed code paths*, not a plugin API.
- **MCP/OpenAPI tool servers: defer with interest.** MCP is becoming
  the industry socket for tools. A future where Zombie *consumes* a
  read-only MCP server (as LinuxAgent exposes one — see
  [`ALTERNATIVE-LINUXAGENT.md`](ALTERNATIVE-LINUXAGENT.md)) or
  *exposes* its own policy-classify/audit-verify surfaces over MCP
  is plausible. Any consumed tool must still pass through the policy
  gate, which likely means wrapping remote tools in local policy
  classes. Not MVP.
- **Skills as a first-class extension unit: already aligned.** Open
  WebUI 0.10 adds "skills" alongside tools; Zombie's markdown skills
  plus `/etc/ubuntu-zombie/` overlays already give the operator a
  safe (data, not code) extension point. **Keep.**

### 3.5 Code execution — Zombie already has the grown-up version

Open WebUI's code execution is browser-side Pyodide (sandboxed,
harmless, and therefore useless for sysadmin work) or the external
`open-terminal` companion (an agentic shell with no policy gate).
Zombie's `shell_run` behind policy classes and operator approval *is*
the sysadmin-grade version of this feature. Nothing to borrow;
if anything, `open-terminal` is a cautionary tale about shipping
execution without a policy vocabulary. **Keep.**

### 3.6 Voice — a surprisingly good fit, later

Open WebUI ships STT (local faster-whisper or cloud) and TTS
(multiple engines, including in-browser `kokoro-js` and the plain
**Web Speech API**). For Zombie's actual persona — a machine you
*talk to* about itself — voice is on-vision ("ask the computer a
question"). The dependency-free translation exists: the **Web Speech
API is browser-side** — `webkitSpeechRecognition` for dictation and
`speechSynthesis` for read-aloud run entirely in the operator's
browser, need zero server dependencies, and would touch only
`templates/index.html`. Approvals must remain click-only (voice
"yes" is not an approval signal). **Defer, but flag as the cheapest
"far more powerful"-feeling upgrade available** after §3.2's `#`
command.

### 3.7 Multi-user, RBAC, channels — refuse

Open WebUI is a multi-tenant platform: users, groups, granular
permissions, SCIM provisioning, shared channels where humans and
models mingle. Ubuntu Zombie is one operator, one machine, one
password, one audit trail — [`VISION.md`](../VISION.md) is explicit
that the agent account is "never a shared human login," and the
whole approval model assumes a single accountable human. Multi-user
would fracture the accountability chain that makes passwordless sudo
defensible. **Refuse** (channels, groups, RBAC, SCIM alike). If a
household ever needs two operators, that is a future policy design
problem, not a UI feature.

### 3.8 Persistent memory — translate as "machine facts," carefully

Open WebUI 0.10 has a two-tier memory: long-lived personal memories
plus per-conversation context, with structured add/update/delete and
user-visible editing. Zombie already injects `machine_facts()`
(hostname, OS, hardware) into the system prompt. The valuable
translation is a small, operator-visible **machine memory**: facts
the agent learns while working ("this laptop dual-boots," "operator
prefers `ufw` over raw nftables," "the 2026-06 nvidia driver hold is
deliberate") stored as plain reviewable text under
`/opt/ai-zombie/state/`, injected into the prelude, editable and
wipeable by the operator. Rules that keep it honest: append is an
audited action, the file is plain text (not a DB the operator won't
open), and it is bounded in size. **Translate** — this compounds the
agent's usefulness across sessions more than any single feature.

### 3.9 Model builder, prompt presets, `/` commands — borrow the small ones

- **Prompt presets with a `/` command**: Zombie already ships
  Hermes-style chat commands (see
  [`HERMES-CHAT-COMMANDS-SELECTED.md`](HERMES-CHAT-COMMANDS-SELECTED.md));
  a handful of canned sysadmin prompts (`/checkup`, `/why-slow`,
  `/updates`, `/disk`) implemented as static prompt templates is a
  cheap **borrow** that makes the product feel deliberate to
  non-experts — the exact audience [`VISION.md`](../VISION.md)
  names.
- **Custom agents / model builder**: wrapping a base model with a
  persona, knowledge, and tool set is what the whole Zombie payload
  *is*. One agent, one job. **Refuse** the general mechanism.
- **Dynamic prompt variables** (`{{CURRENT_DATE}}`, etc.): already
  effectively present via the prelude template. **Keep.**

### 3.10 Chat ergonomics — the humbling section

Here Open WebUI is simply better, and almost all of it is
license-free UX that Zombie's stdlib server could adopt
incrementally. Zombie already has branching, retry, undo, titles,
and compression in `server.py` — ahead of most small chats. Still
missing, in rough value order:

1. **Streaming responses.** Open WebUI streams tokens (and even
   streams `<thinking>` blocks). Zombie's chat answers arrive whole.
   For long diagnostic turns, streaming is the difference between
   "alive" and "hung." Server-sent events are pure stdlib
   (`text/event-stream` over the existing handler). **Borrow** —
   highest-value ergonomic item.
2. **Full-text search across conversations.** SQLite FTS5 is in the
   stdlib `sqlite3` build on Ubuntu; `history.py` is already
   SQLite. **Borrow.**
3. **Conversation tags/folders.** A `tags` column and a filter bar.
   **Borrow, small.**
4. **Message queuing** while the agent is busy. Nice; niche.
   **Defer.**
5. **Markdown/Mermaid/KaTeX rendering.** Zombie's UI is a single
   `index.html`; rendering fenced code and tables well matters for
   sysadmin output (unit files, diffs). Mermaid/KaTeX would mean
   vendoring JS libraries — weigh against the no-new-deps spirit;
   plain high-quality `<pre>`/table rendering first. **Partial
   borrow.**
6. **Export/share.** Export a conversation (with its audit trail!)
   as markdown for a forum post or bug report — very on-mission for
   "the machine explains itself." A shareable *audit-grounded*
   transcript is something Open WebUI does not have. **Borrow and
   improve.**

### 3.11 Calendar, automations, scheduled prompts — translate into systemd

Open WebUI can schedule prompts to run on a recurrence (APScheduler)
and shows runs on a calendar. The Zombie translation is obvious and
better-fitting: **scheduled check-ups** — a systemd timer (the
install already manages units and a health timer) that runs a canned
`read_only` prompt ("daily: disk, failed units, pending security
updates; write a summary") and leaves the report in the chat history
for the operator's next visit. No new deps, and it converts Zombie
from reactive to proactive within the policy gate — auto-run must be
hard-limited to `read_only` class, with anything stronger queued as
a pending approval. **Translate** — this is the second structural
"far more powerful" item after §4.

### 3.12 Webhooks and events — defer

Outbound webhooks on system events would let Zombie ping the
operator's phone ("3 security updates pending; reply in chat to
approve"). Valuable, but it is an outbound network channel from a
root-capable box and needs its own policy/secret story. **Defer**
behind the scheduled check-ups of §3.11, which produce the content a
notification would carry.

### 3.13 Observability, analytics, arenas — refuse

OpenTelemetry suites, usage dashboards, model ELO arenas: platform
concerns for platform operators. Zombie's observability is the audit
log, and its analytics is `journalctl`. **Refuse.**

## 4. The integration option: Zombie as an OpenAI-compatible endpoint

There is one integration (not imitation) possibility worth recording
carefully, because it is how the whole Open WebUI ecosystem composes:
**anything that speaks `/v1/chat/completions` and `/v1/models` can be
an Open WebUI backend.** Pipelines works this way; LiteLLM works this
way; vLLM works this way.

If Zombie's server ever grew a small, loopback-only, token-guarded
OpenAI-compatible shim — `/v1/models` returning one model
(`ubuntu-zombie`) and `/v1/chat/completions` mapping onto
`post_message` — then an operator who already runs Open WebUI (or
*any* OpenAI-compatible client: desktop apps, editors, phones over
Tailscale) could talk to their machine's administrator from the chat
front-end they already live in. Zombie would remain the policy gate,
audit log, and execution engine; Open WebUI would be merely a
prettier telephone.

Honest constraints, so this note doesn't oversell it:

- **Approvals don't fit the wire format.** OpenAI's protocol has no
  "pause for human approval" verb. The shim would have to either
  (a) restrict the endpoint to `read_only` behaviour, (b) return
  "approval required — open the Zombie chat" messages with pending
  calls parked for the real UI, or (c) abuse tool-call round-trips
  in ways clients won't render. Option (b) is the only defensible
  one.
- **Authentication must not weaken.** A bearer token distinct from
  the chat password, loopback/Tailscale-only, covered by the same
  TTL lifecycle.
- **It inverts nothing.** Zombie pointing *at* Open WebUI as a
  provider is useless (Open WebUI proxies models; Zombie already
  reaches models directly). The value flows one way: Zombie as
  backend.

**Defer**, but this is the single highest-leverage line item in this
document if the goal is "far more powerful chat" — it buys Zombie
every front-end ergonomic in §3.10 (streaming UIs, mobile PWAs,
voice, rendering) for the cost of one adapter, while keeping every
safety property server-side where it already lives.

## 5. What Open WebUI teaches by negative example

The alternative essays each end with a warning; Open WebUI's are:

1. **Maximalism has a price Zombie cannot pay.** 120 dependencies,
   3–5 GB installed, Playwright-with-Chromium in a chat app. Every
   dependency on a passwordless-sudo machine is attack surface. The
   correct reading of Open WebUI's feature list is a menu of ideas,
   never a bill of materials.
2. **Plugin marketplaces and root do not mix.** `RestrictedPython`
   disclaimers, "don't fetch random pipelines," in-process arbitrary
   code as the *recommended* extension path — acceptable for a chat
   platform, disqualifying for a system administrator. Zombie's
   closed, policy-classed tool registry is a feature; keep it
   closed.
3. **First-user-becomes-admin is a warning label.** Open WebUI's
   fresh-install takeover pattern is exactly why Zombie's installer
   sets the chat password non-interactively and binds to loopback
   before anything else listens.
4. **License drift is real.** A project can be MIT in January,
   BSD-3 in spring, and source-available-with-branding-restrictions
   by April. Any future decision to depend on an external UI must
   re-check the license *at that time*, not trust this note.
5. **Even the maintainers prune.** "DO NOT USE PIPELINES" is a
   mature project telling users its own extension system was one
   layer too many. Zombie should read that as permission to keep
   saying no.

## 6. Ranked shortlist

If the goal is "make the chat with the zombie far more powerful,"
this research supports, in order of value per unit of risk:

| # | Possibility | Verdict | Cost | Section |
|---|-------------|---------|------|---------|
| 1 | SSE streaming of agent turns | borrow | small | §3.10 |
| 2 | `#` context injection (files, units, logs) via existing tools | translate | small | §3.2 |
| 3 | Scheduled read-only check-ups via systemd timer | translate | medium | §3.11 |
| 4 | Operator-visible machine memory file | translate | small | §3.8 |
| 5 | `/` prompt presets for common sysadmin asks | borrow | small | §3.9 |
| 6 | Conversation FTS + tags | borrow | small | §3.10 |
| 7 | Audit-grounded conversation export | borrow | small | §3.10 |
| 8 | Auto-compaction of long conversations | borrow | small | §3.2 |
| 9 | Ollama discovery parity with LM Studio | borrow | small | §3.1 |
| 10 | OpenAI-compatible endpoint shim (Zombie as backend) | defer/integrate | large | §4 |
| 11 | Browser-native voice (Web Speech API) | defer | small | §3.6 |
| 12 | Policy-gated web fetch/search tool | defer | medium | §3.3 |
| 13 | MCP consumption/exposure | defer | large | §3.4 |
| — | Vector RAG, plugins, multi-user/RBAC/channels, webhooks-first, OTEL/analytics, UI fork/embed | refuse | — | §§3.2, 3.4, 3.7, 3.12, 3.13, 2.1 |

Everything in the borrow/translate rows is implementable inside the
existing payload with no new runtime dependencies, behind the
existing policy gate and audit log, without touching the trust
model. That is the real conclusion: Open WebUI shows how much
*power* a chat can carry; Zombie's job is to carry the sysadmin-
shaped subset of it inside a boundary Open WebUI never had to build.

---

*Sources: `open-webui/open-webui` (README, CHANGELOG 0.10.x,
`LICENSE`, `LICENSE_HISTORY`, `backend/requirements.txt`,
`package.json`, `docs/SECURITY.md`), `open-webui/pipelines` (README,
example scaffolds), companion repos `open-webui/mcpo`,
`open-webui/open-terminal`, `open-webui/openapi-servers`,
`open-webui/oikb`. Version examined: 0.10.2 (2026-07-01). Like all
files in `docs/research/`, this is a research note, not product
documentation, and may drift from both codebases.*
