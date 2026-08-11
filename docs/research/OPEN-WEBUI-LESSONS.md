# Lessons from Open WebUI

This document is a companion to
[`OPEN-WEBUI-POSSIBILITIES.md`](OPEN-WEBUI-POSSIBILITIES.md), in the
same way that [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md)
distils [`ALTERNATIVES.md`](ALTERNATIVES.md). The possibilities note
catalogues Open WebUI's capabilities feature by feature; this file
asks the harder, narrower question:

> **Ubuntu Zombie's only interface is the local chat. What must that
> chat learn from the most successful self-hosted chat surface in the
> ecosystem to be world class — without importing a single one of
> Open WebUI's ~120 dependencies or weakening the trust model in
> [`VISION.md`](../VISION.md) and
> [`ARCHITECTURE.md`](../ARCHITECTURE.md)?**

Every lesson below is a *borrow* (re-implement the idea in Zombie's
stdlib codebase) or a *translate* (reshape the concept for a
single-operator, root-capable agent) from the possibilities note.
Ideas the research marked *defer* appear only where the lesson is
worth recording now; ideas marked *refuse* appear only in the
negative-lessons section. Section references (§) point into
`OPEN-WEBUI-POSSIBILITIES.md`.

Research basis: Open WebUI 0.10.2, examined 2026-07-09.

---

## The frame: one chat, or nothing

Open WebUI can afford a mediocre feature because it has fifty others.
Ubuntu Zombie cannot: the local chat (`payload/agent/server.py` and
`templates/index.html`) is the *entire* operator experience — every
approval, every diagnosis, every explanation flows through it. That
asymmetry converts Open WebUI's feature list from a bill of materials
into a quality bar. The lessons split into four groups:

1. **Perceived liveness** — the chat must feel alive, not batch.
2. **Context ergonomics** — getting machine state *into* a turn must
   be one keystroke, not a copy-paste ritual.
3. **Continuity** — the chat must remember, find, and export what it
   has done.
4. **Proactivity** — a world-class sysadmin chat starts conversations,
   not just answers them.

Plus a fifth group Open WebUI teaches by counterexample: **what a
world-class chat refuses to become.**

## Group 1 — Perceived liveness

### Lesson 1: Stream everything (borrow, §3.10)

The single largest gap between Zombie's chat and a modern chat
surface is that Zombie's answers arrive whole. During a long
diagnostic turn — a multi-tool investigation of a failing unit — the
operator stares at a static page and cannot distinguish "working"
from "hung." Open WebUI streams tokens and even streams `<thinking>`
blocks, and that is most of why it *feels* premium.

The lesson is precise: **liveness is a trust feature, not a
cosmetic.** An agent with root capability that goes silent for
ninety seconds trains the operator to distrust it. Server-sent
events are pure stdlib (`text/event-stream` on the existing
`http.server` handler), so this is the highest-value ergonomic item
in the entire study, at near-zero dependency cost. Streaming should
cover not only model tokens but *tool activity* — "running
`systemctl status nginx`…" as it happens — which Open WebUI's
event-emitter pattern (status updates pushed mid-turn) demonstrates
and which maps naturally onto Zombie's audited tool calls.

### Lesson 2: Render sysadmin output like it matters (partial borrow, §3.10)

Open WebUI renders markdown, tables, code fences, Mermaid, and KaTeX.
Zombie does not need math typesetting, but a sysadmin chat lives on
unit files, diffs, fstab tables, and log excerpts. The lesson:
**high-quality `<pre>`, fenced-code, and table rendering is table
stakes**; a diff the operator is about to approve deserves syntax
distinction between added and removed lines. Do this in the existing
single `index.html` with plain CSS and small hand-rolled rendering —
vendoring a JS rendering stack would violate the no-new-deps spirit
for marginal gain (Mermaid/KaTeX stay out until proven necessary).

### Lesson 3: Never lose an operator's words (defer, recorded, §3.10)

Open WebUI queues messages typed while the model is busy. Zombie's
single-operator flow makes this niche, but the underlying lesson
generalises: **the input box must never silently drop or block.**
Whatever is cheapest — disable-with-explanation or a one-deep queue —
the failure mode "I typed during a turn and it vanished" is
disqualifying for a chat that is the machine's only interface.

## Group 2 — Context ergonomics

### Lesson 4: The `#` command, re-aimed at the machine (translate, §3.2)

Open WebUI's `#` command pins a document into a turn. Zombie's
"documents" are `/etc`, `/var/log`, `journalctl`, and `dpkg -l` — and
the agent can already read them through policy-gated tools, but the
*operator* cannot cheaply say "look at this specific thing."
Translating `#` — `#/var/log/syslog`, `#systemd:nginx.service` — to
inject a policy-checked, size-clipped file or unit status into the
prompt reuses the existing `fs_read` tooling with no embeddings and
no new dependencies.

The possibilities note calls this "arguably the highest ratio of
power gained to code written" in the whole study, and the general
lesson deserves stating: **world-class context handling on a sysadmin
box is deterministic reference, not statistical retrieval.** The
operator names the artifact; the policy gate clips and admits it; the
audit log records it. That beats a vector index on every axis Zombie
cares about — reviewability, secret hygiene, and zero dependencies.

### Lesson 5: Curated knowledge beats retrieved knowledge (borrow the emphasis, §3.2)

Open WebUI's RAG stack is its single heaviest subsystem — nine vector
stores, rerankers, extraction engines. Zombie's markdown skills
(`payload/agent/skills/`, `skill_loader.py`) *are* its RAG: curated,
auditable, diffable. Open WebUI 0.10 adding "skills" alongside its
tools validates the direction. The lesson is to **invest in the skill
library as the knowledge strategy** — networking, disk, GPU drivers,
backup, upgrade playbooks — because a grown skill library is cheaper,
safer, and more predictable than any embedding index, and every
skill is one more area where the chat answers like a specialist.

### Lesson 6: Compact context automatically (borrow, §3.2)

Zombie already has manual `compress_conversation`; Open WebUI ships
auto-triggered compaction past a token threshold. The lesson: **an
operator should never have to know what a context window is.** A
world-class chat degrades gracefully on long conversations by
summarising old turns automatically, and Zombie already owns the
summariser — only the trigger is missing.

### Lesson 7: Meet the operator's local models (borrow, §3.1)

Open WebUI's native Ollama management is heavyweight, but the kernel
of it — *the chat works with whatever inference the operator already
runs, no cloud key required* — is worth matching. Zombie already
discovers LM Studio and network inference during install; extending
the same discovery to a local Ollama daemon is a small borrow that
keeps the "private machine, private model" story strong.

## Group 3 — Continuity

### Lesson 8: Machine memory, on paper (translate, §3.8)

Open WebUI's two-tier persistent memory (long-lived personal memories
plus per-conversation context, user-editable) translates into what
the possibilities note calls the feature that "compounds the agent's
usefulness across sessions more than any single feature": an
operator-visible **machine memory** — facts learned while working
("this laptop dual-boots," "operator prefers `ufw`," "the nvidia
driver hold is deliberate") kept as plain reviewable text under
`/opt/ai-zombie/state/` and injected into the prelude.

The translation rules are the lesson: **memory on a root-capable
agent must be legible and governable** — plain text, not a database
the operator won't open; appends audited like any other action;
bounded in size; editable and wipeable by the operator. Open WebUI's
user-visible memory editing is the right instinct; Zombie's version
must be *more* transparent, not less, because its memories steer an
agent with sudo.

### Lesson 9: Find anything ever said (borrow, §3.10)

A chat that is also the machine's administrative record needs recall.
Open WebUI has full-text search across conversations; Zombie's
`history.py` is already SQLite, and FTS5 ships in Ubuntu's stdlib
`sqlite3` build. Add tags/folders (a `tags` column and a filter bar)
and the operator can answer "when did we change the DNS settings?"
from the chat itself. **Borrow both; they are small.**

### Lesson 10: Export as evidence, not just text (borrow and improve, §3.10)

Open WebUI exports conversations. Zombie can do something Open WebUI
structurally cannot: export a conversation *with its audit trail* —
every command proposed, approved, and run, interleaved with the
dialogue. A markdown transcript like that is a forum post, a bug
report, or a change record. The lesson: **Zombie's chat should treat
"the machine explains itself" as an exportable artifact** — this is
the one ergonomic where the appliance can beat the platform.

## Group 4 — Proactivity

### Lesson 11: Scheduled check-ups, inside the gate (translate, §3.11)

Open WebUI schedules prompts on a recurrence (APScheduler plus a
calendar UI). The Zombie translation is better-fitting than the
original: a **systemd timer** (the installer already manages units
and a health timer) running a canned `read_only` prompt — "daily:
disk, failed units, pending security updates; summarise" — leaving
the report in chat history for the operator's next visit.

This converts the chat from reactive to proactive, and the safety
rule *is* the lesson: **autonomy is only ever granted to the
`read_only` class.** Anything stronger the check-up discovers gets
queued as a pending approval, never executed. A world-class sysadmin
chat greets the operator with "here's what I noticed" — and a
trustworthy one never acted on it alone. (Outbound notifications of
those findings are the natural sequel but need their own
policy/secret story first — §3.12.)

### Lesson 12: `/` presets make the product feel deliberate (borrow, §3.9)

Open WebUI's prompt library with `/` completion, translated: a small
set of canned sysadmin prompts — `/checkup`, `/why-slow`, `/updates`,
`/disk` — as static templates on the Hermes-style command surface
Zombie already ships. The lesson is about audience: Zombie's operator
is explicitly a non-expert ([`VISION.md`](../VISION.md)), and **a
blank input box is a cost you charge the user.** Presets are the
cheapest way to teach the chat's range from inside the chat.

### Lesson 13: Fixed filters, not a filter API (translate narrowly, §3.4)

Open WebUI's inlet/outlet filter hooks are arbitrary code; the shape
worth keeping is a deterministic filter *stage* on both directions of
the conversation: secret redaction on the way out (extend what
`audit.py` already does to chat responses), size clipping, and
prompt-injection heuristics on tool output on the way in. **Fixed
code paths, never a plugin API.** A world-class chat on a root box is
one that scrubs its own output by construction.

## Group 5 — What the chat must refuse to become

Open WebUI's negative lessons (§5) compress into rules for the chat:

1. **The feature list is a menu, never a bill of materials.** 120
   dependencies and 3–5 GB installed is what maximalism costs; every
   dependency on a passwordless-sudo machine is attack surface. Each
   lesson above is implementable in stdlib Python inside the existing
   payload — that is a constraint, and it is also the moat.
2. **No plugin marketplace, ever.** Open WebUI's own docs say "don't
   fetch random pipelines," and its maintainers wrote "DO NOT USE
   PIPELINES" atop one of their four extension systems. On a machine
   where the agent holds sudo, operator-loaded code is a supply-chain
   attack with a UI. Zombie's closed, policy-classed tool registry
   (`tools.py`, `policy.py`) is the correct shape; extension is
   reviewed tools and markdown skills — data, not code.
3. **One operator, one accountability chain.** Multi-user, RBAC,
   groups, and channels would fracture the single-human approval
   model that makes passwordless sudo defensible. World class here
   means deeper for one person, not wider for many.
4. **No ambient injection of live content.** Web results, if ever
   added, arrive as a policy-classed, audited *tool* the model must
   ask for — never as automatic context. Ambient injection into a
   root-capable agent's prompt is a prompt-injection funnel.
5. **Approvals are clicks, not vibes.** Whatever the chat grows —
   streaming, voice (§3.6), remote front-ends (§4) — approval of a
   privileged action remains an explicit interaction in the trusted
   UI. A spoken "yes" or a wire-format workaround is not an approval
   signal.
6. **Re-check licenses at decision time.** Open WebUI went from MIT
   to BSD-3-with-branding-clause within months. Ideas are free;
   code and UI embedding are not (§2.1). Any future integration —
   including the deferred OpenAI-compatible shim that would let
   Zombie appear inside Open WebUI itself (§4) — must re-read the
   license then, not trust this note.

## The distilled shortlist

If the chat team implements nothing else, implement these, in order —
each is a borrow/translate from the ranked table in
`OPEN-WEBUI-POSSIBILITIES.md` §6, all stdlib-only, all behind the
existing policy gate and audit log:

| # | Lesson | What it buys | Section |
|---|--------|--------------|---------|
| 1 | SSE streaming of tokens and tool activity | the chat feels alive | §3.10 |
| 2 | `#` context injection of files/units/logs | one-keystroke grounding | §3.2 |
| 3 | Scheduled read-only check-ups via systemd timer | a proactive administrator | §3.11 |
| 4 | Plain-text, audited machine memory | usefulness compounds across sessions | §3.8 |
| 5 | `/` prompt presets for common asks | discoverability for non-experts | §3.9 |
| 6 | Conversation FTS + tags | the chat as searchable record | §3.10 |
| 7 | Audit-grounded conversation export | the machine explains itself, portably | §3.10 |
| 8 | Auto-compaction of long conversations | graceful long sessions | §3.2 |
| 9 | Ollama discovery parity with LM Studio | no-cloud-key story stays strong | §3.1 |
| 10 | Deterministic redaction/clipping filters | output hygiene by construction | §3.4 |

And one sentence to keep above the backlog: **Open WebUI shows how
much power a chat can carry; Zombie's job is to carry the
sysadmin-shaped subset of it inside a trust boundary Open WebUI never
had to build.** World class, here, means the operator never wants a
different front door — because this one streams, remembers, searches,
schedules, explains, and still asks permission.

---

*Derived entirely from
[`OPEN-WEBUI-POSSIBILITIES.md`](OPEN-WEBUI-POSSIBILITIES.md)
(research date 2026-07-09, Open WebUI 0.10.2). Like all files in
`docs/research/`, this is a research note, not product documentation,
and may drift from both codebases.*
