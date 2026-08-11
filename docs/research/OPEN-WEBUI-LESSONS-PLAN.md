# Implementation plan: lessons from Open WebUI

This document turns the distilled shortlist in
[`OPEN-WEBUI-LESSONS.md`](OPEN-WEBUI-LESSONS.md) into a concrete,
phased implementation plan against the current codebase. Each work
item names the files it touches, the design it should follow, the
policy/audit obligations it inherits, the tests and docs it must
ship with, and an acceptance check. Like every file in
`docs/research/`, this is a research/planning note, not product
documentation, and it may drift from the code once work begins.

Plan basis: repository state as of 2026-07-09 (VERSION
`2026.07.09.01.50.59`), lessons note research date 2026-07-09.

---

## 1. Ground truth: what the chat is today

The plan below is only meaningful against the current baseline:

- **Server.** `payload/agent/server.py` is a stdlib
  `http.server.ThreadingHTTPServer` bound to `127.0.0.1`. A chat
  turn is one synchronous `POST /api/message` → `app.post_message()`
  → `pi_mono.run_turn()` round trip; the browser receives nothing
  until the full reply (and every inline tool call) has finished.
  There is no SSE, no WebSocket, no chunked responses.
- **UI.** `payload/agent/templates/index.html` is a single
  dependency-free page. Assistant messages already pass through a
  small hand-rolled, escape-first markdown renderer (fenced code,
  inline code, bold/italic, headings, lists, quotes, safe links).
  A large client-side slash-command surface (`/help`, `/compress`,
  `/export`, `/approve`, …) already exists per
  [`HERMES-CHAT-COMMANDS-SELECTED.md`](HERMES-CHAT-COMMANDS-SELECTED.md).
- **History.** `payload/agent/history.py` is SQLite with three
  tables (`conversations`, `messages`, `events`). No FTS, no tags.
  `compress_conversation` exists but is operator-triggered only and
  produces a deterministic local summary injected via
  `latest_summary()`.
- **Tools/policy/audit.** `payload/agent/tools.py` is a closed
  registry (`fs.read`, `fs.list`, `svc.status`, `skill.load`, …)
  with JSON-schema validation; `payload/agent/policy.py` classifies
  every call into `read_only` … `destructive` (fail-closed) with an
  approval queue for anything above auto; `payload/agent/audit.py`
  writes JSON-lines audit entries with token/env-var redaction
  already built in.
- **Skills.** `payload/agent/skill_loader.py` selects markdown
  skills by trigger words from the last four user messages and
  appends them to the system prompt with provenance headers.
- **Providers.** `payload/agent/providers.py` + the pi-ai bridge
  support cloud providers plus `lmstudio`; the installer
  (`scripts/install.sh`) does a LAN `/24` scan on the LM Studio
  port at install time. No Ollama support, no streaming anywhere in
  the provider path.
- **Proactive machinery.** `payload/systemd/` already ships a
  health timer (`ubuntu-zombie-health.timer`, every 15 minutes)
  and the installer knows how to install units and optional
  components (`ZOMBIE_INSTALL_<COMPONENT>` flags, review menu,
  receipts, uninstall reversal).

## 2. Constraints that bind every item

Restated from `AGENTS.md`, [`../VISION.md`](../VISION.md), and
[`../ARCHITECTURE.md`](../ARCHITECTURE.md); each work item below is
scoped to satisfy all of these:

1. **Stdlib only.** No new Python runtime dependencies, no vendored
   JS libraries in `index.html`. FTS5 counts as stdlib (it ships in
   Ubuntu's `sqlite3` build) but must be feature-detected.
2. **Policy gate + audit log.** Every new privileged behaviour goes
   through `policy.py` classification and is written by `audit.py`.
   No new code path may call `sudo` or read operator files outside
   the existing tool registry.
3. **Installer idempotence + `ZOMBIE_NONINTERACTIVE=1`.** Any
   installer change (timers, state files, discovery) must converge
   on re-run and work headless; missing required env exits 64.
4. **Single operator, approvals are clicks.** Nothing in this plan
   adds users, plugins, remote surfaces, or new approval channels.
5. **Every user-visible change** updates `docs/`, `README.md` where
   relevant, `CHANGELOG.md`, and `VERSION`; `make lint` and
   `make test` must pass at every phase boundary.

## 3. Phasing

The shortlist order in the lessons note is roughly the value order;
this plan re-groups it into five phases so that shared plumbing is
built once and each phase lands independently shippable:

| Phase | Work items (shortlist # / lesson) | Theme |
|-------|-----------------------------------|-------|
| A | SSE streaming (#1); input never lost (Lesson 3, unranked) | liveness plumbing |
| B | Rendering polish (Lesson 2, unranked); `#` context injection (#2); `/` presets (#5) | input/output ergonomics |
| C | FTS + tags (#6); auto-compaction (#8); audit-grounded export (#7) | continuity |
| D | Machine memory (#4); deterministic filters (#10) | memory + hygiene |
| E | Scheduled check-ups (#3); Ollama discovery (#9) | proactivity + installer |

Phases B–E have no hard dependency on A except where noted; A is
first because it changes the turn transport that several later
items (tool-activity display, check-up reports) benefit from.

---

## Phase A — liveness plumbing

### A1. SSE streaming of tokens and tool activity (shortlist #1)

**Goal.** During a turn the operator sees tokens as they arrive and
a live line per tool call ("running `systemctl status nginx`…"),
instead of a silent page until completion.

**Touch points.** `payload/agent/server.py`,
`payload/agent/pi_mono.py`, `payload/agent/pi-mono-bridge.mjs`,
`payload/agent/providers.py`, `payload/agent/templates/index.html`,
`docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md`, `tests/smoke.sh`.

**Design.**

- Add a `GET /api/stream/{turn_id}` endpoint on the existing
  handler that emits `text/event-stream`. `ThreadingHTTPServer`
  already gives each request its own thread, so one long-lived SSE
  response per active turn is safe; enforce exactly one active
  stream (single operator).
- Restructure `app.post_message()` into a two-step protocol:
  `POST /api/message` registers the turn and returns a `turn_id`
  immediately; the browser then opens the SSE stream; the existing
  synchronous JSON response is kept as the fallback path when the
  client does not open a stream (and for tests).
- Define a small event vocabulary carried over SSE, mirroring what
  is already stored in `events`: `token` (model delta),
  `tool_start`/`tool_end` (name, classification, duration),
  `pending_approval`, `turn_done` (carries the same final payload
  the synchronous path returns), `turn_error`.
- Thread a per-turn queue between the `on_tool_call` callback and
  the SSE writer. Tool activity events are produced from the same
  code that already logs `tool_call`/`tool_observation`, so the
  stream can never show something the audit log does not record.
- Token-level streaming requires the pi-mono bridge to forward
  provider deltas. Scope this as best-effort: stream tool activity
  and turn phases first (pure Python, works with every provider),
  then extend `pi-mono-bridge.mjs` to emit token deltas where the
  underlying provider supports it. If the bridge cannot stream,
  the UI still shows live phase/tool events — most of the
  perceived-liveness win.
- Client side: `EventSource` in `index.html`, appending tokens into
  the in-progress assistant bubble and rendering tool events as the
  same event rows the conversation reload already draws. On stream
  error, fall back to the current poll-once behaviour so the chat
  never regresses below today's baseline.

**Policy/audit.** No new privileged behaviour; the stream is a view
over events already gated and audited. The SSE endpoint must sit
behind the existing session-cookie auth (`auth.py`) exactly like
`/api/message`.

**Tests.** Smoke additions: python compile already covers the new
code; add a `standards` check that `server.py` declares the SSE
endpoint and that `index.html` references `EventSource` with a
fallback. Manual VM checklist: long multi-tool turn shows live tool
lines; killing the stream mid-turn leaves history intact.

**Acceptance.** A turn that runs three tool calls shows at least
three live status updates before the final reply; with streaming
unavailable the chat behaves exactly as today.

### A2. Never lose the operator's words (Lesson 3)

**Goal.** Typing during a busy turn can never silently vanish.

**Touch points.** `payload/agent/templates/index.html` only.

**Design.** Keep the textarea enabled during a turn (it already is,
for slash commands). Add a one-deep client-side queue: if the
operator submits while a turn is in flight, hold the message in a
visible "queued" bubble and send it when `turn_done` arrives; a
second submit replaces the queued item with an explicit notice.
No server change, no persistence — refresh drops the queue, and the
queued bubble says so.

**Tests.** None automatable in smoke; document the behaviour in
`docs/CHAT.md` (or the chat section of `README.md`) and in the
`/help` output.

**Acceptance.** Submit during a running turn → message visibly
queued → auto-sent at turn end.

---

## Phase B — input/output ergonomics

### B1. Sysadmin-grade rendering (Lesson 2)

**Goal.** Diffs, tables, and log excerpts render with enough visual
structure that an operator can review a proposed change at a glance.

**Touch points.** `payload/agent/templates/index.html` (renderer +
CSS only).

**Design.** Extend the existing hand-rolled `renderMarkdown()`:

- Pipe-table support (header row + separator → `<table>`), bounded
  to modest column counts to avoid pathological input.
- Diff-aware code fences: inside a fence tagged `diff` (or whose
  lines start with `+`/`-`/`@@`), colour added/removed/hunk lines
  via CSS classes. Escape-first ordering is preserved: classify on
  the escaped line's first character, never inject unescaped input.
- A copy button per fenced block (clipboard API, no library).
- Explicitly out of scope, per the lessons note: Mermaid, KaTeX,
  syntax highlighting beyond diffs, any vendored JS.

**Tests.** Add a `standards` smoke assertion that `index.html`
contains no external `<script src=` / CDN references (guarding the
no-deps rule this item is most tempted to break).

**Acceptance.** A unit-file diff proposed by the agent shows green
added lines and red removed lines before the operator approves it.

### B2. `#` context injection (shortlist #2)

**Goal.** The operator can pin machine state into a turn with one
token: `#/var/log/syslog`, `#systemd:nginx.service`, `#pkg:nginx`.

**Touch points.** `payload/agent/server.py` (message pre-parse),
`payload/agent/tools.py` (reuse, not extend),
`payload/agent/templates/index.html` (completion UI),
`docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, `tests/smoke.sh`,
plus the chat-command reference in
[`HERMES-CHAT-COMMANDS-SELECTED.md`](HERMES-CHAT-COMMANDS-SELECTED.md)
(or whatever user-facing command doc supersedes it by then).

**Design.**

- Parse `#references` server-side in `post_message()` before the
  model sees the prompt. Grammar: `#<path>` (absolute path),
  `#systemd:<unit>`, `#journal:<unit-or-boot>`, `#pkg:<name>`.
  Unknown schemes are left as literal text.
- Resolution reuses the existing read-only shims — `fs.read` for
  paths (which already enforces the read allow-list and 64 KiB
  clip), `svc.status` for units, `pkg.query` for packages — invoked
  through the same `on_tool_call` pipeline so classification,
  clipping, and audit happen identically to a model-initiated call.
  The only difference is provenance: the event records
  `origin: operator_reference`.
- Injected content is added as a clearly-delimited system message
  ("Operator attached `/var/log/syslog` (clipped to 64 KiB)…") and
  stored in history so the transcript shows exactly what the model
  saw.
- A reference that resolves to a non-`read_only` classification
  (possible via `tool_classes` overrides in policy) is refused with
  an explanatory chat notice — operator references never enqueue
  approvals.
- Client side: on typing `#`, offer scheme completion only (no
  filesystem browsing from the browser); resolution and errors stay
  server-side.
- No embeddings, no indexing, no new tools — this is deterministic
  reference, per the lessons note.

**Tests.** Smoke: extend the python checks with a unit-style
invocation asserting the parser extracts references and leaves
non-matching `#hashtags` alone (pattern: pure function in
`server.py`, testable via `python3 -c` like existing policy
regressions in `tests/smoke.sh`).

**Acceptance.** `#systemd:ssh.service what's wrong?` produces an
audited `svc.status` event and a system message containing the unit
status, before the model answers.

### B3. `/` prompt presets (shortlist #5)

**Goal.** Canned sysadmin prompts — `/checkup`, `/why-slow`,
`/updates`, `/disk` — teach the chat's range from inside the chat.

**Touch points.** `payload/agent/templates/index.html` (command
table + dispatch), optionally a small static preset table served at
`/api/presets` from `server.py` if server-side reuse (E1's check-up
prompt) is wanted; docs.

**Design.** Presets are static prompt templates, not new tools:
selecting `/disk` inserts a pre-written prompt (visible to the
operator, editable before send) into the input box rather than
side-channelling text to the model. This keeps the "operator sees
everything the model is asked" property. Add them to the existing
client-side command registry so `/help` and `/commands` list them
under a "Presets" category. Start with four; the E1 check-up prompt
should be the same text as `/checkup` so scheduled and manual runs
are comparable.

**Tests.** None beyond existing UI conventions; update the command
docs and `/help`.

**Acceptance.** A new operator can discover and run all four
presets from `/help` without reading any documentation.

---

## Phase C — continuity

### C1. Conversation FTS + tags (shortlist #6)

**Goal.** "When did we change the DNS settings?" is answerable from
the chat.

**Touch points.** `payload/agent/history.py` (schema v2 +
migration), `payload/agent/server.py` (`/api/search`, tag
endpoints), `payload/agent/templates/index.html` (`/search`,
`/tag`, filter in `/conversations`), docs.

**Design.**

- Bump `SCHEMA_VERSION` to 2 with an in-place migration: add a
  `tags` TEXT column (JSON array) to `conversations`, and create an
  FTS5 virtual table over `messages(content)` kept in sync by
  triggers. Feature-detect FTS5 at open time
  (`sqlite3` compile options); if absent, fall back to `LIKE`
  search so the feature degrades rather than fails — Ubuntu LTS
  builds ship FTS5, so the fallback is belt-and-braces.
- Migration must be idempotent and safe on an existing
  `conversations.db` (the installer's repair path should not be
  needed; `history.py` migrates on open, as schema v1 code already
  initialises on first open).
- New read-only endpoints: `GET /api/search?q=` returning matching
  messages with conversation id/title/timestamp snippets;
  `POST /api/conversation/{id}/tags` to set tags. Both behind the
  session gate; tag writes logged as `conversation_tagged` audit
  events (consistent with existing `conversation_*` audit types).
- UI: `/search <terms>` slash command rendering grouped hits that
  link to `/load <id>`; `/tag <id> <tag…>`; `/conversations`
  gains an optional tag filter argument.

**Tests.** Smoke: a python one-liner regression that creates a
temp DB, inserts a message, and asserts search finds it under both
FTS5 and the LIKE fallback (env-forced).

**Acceptance.** After tagging a conversation `dns` and searching
`resolv.conf`, both `/search` and the tag filter locate it.

### C2. Auto-compaction (shortlist #8)

**Goal.** Long conversations degrade gracefully without the
operator knowing what a context window is.

**Touch points.** `payload/agent/server.py` (trigger in
`post_message`), `payload/agent/policy.py` /
`payload/etc/policy.yaml` only if thresholds become configurable,
docs.

**Design.** The summariser already exists
(`compress_conversation` → `_local_summary`); only the trigger is
missing. Before building `history_payload`, estimate turn size
(message count and total characters — a deterministic proxy; no
tokenizer dependency). Past a threshold (e.g. 40 messages or a
character budget derived from `max_turn_seconds`-era defaults,
configurable via a `ZOMBIE_COMPACT_AFTER_MESSAGES`-style env or
policy key), call the existing compression path automatically,
record a `conversation_summary` event flagged `auto: true`, and
surface a one-line notice in chat ("Older turns summarised to keep
context small — `/history` still shows everything"). Original
messages are never deleted (matching current `/compress`
semantics); only the payload sent to the model shrinks by relying
on `latest_summary()` plus a recent window of messages.

**Tests.** Python regression in smoke: seed a conversation past the
threshold, call the pre-turn hook, assert a summary system message
appears and the constructed history payload is bounded.

**Acceptance.** A 60-message conversation continues to work and the
transcript shows an automatic summary event; short conversations
see no behaviour change.

### C3. Audit-grounded export (shortlist #7)

**Goal.** `/export` produces a markdown transcript with the audit
trail interleaved — every command proposed, approved, and run.

**Touch points.** `payload/agent/server.py` (new
`GET /api/conversation/{id}/export`), `payload/agent/history.py`
(merged message+event iterator), `payload/agent/audit.py` (read
path filtered by `conversation_id`), `index.html` (`/export`
upgrade), docs.

**Design.** Build the export server-side (the client-side `/export`
today only sees what the browser has). Merge `messages` and
`events` by timestamp/id into one markdown document: dialogue as
quoted turns; each tool call as a compact block showing tool,
classification, decision (auto/approved/denied), exit code, and
duration, cross-referenced by the audit entry id so the operator
can locate the full record in `/var/log/ubuntu-zombie/audit.log`.
The export must pass through the same redaction used by `audit.py`
(see D2) so a pasted-to-a-forum transcript cannot leak secrets.
Offer two forms: `/export` (chat-visible markdown, copyable) and a
download response (`Content-Disposition: attachment`).

**Tests.** Python regression: exported document for a seeded
conversation contains the tool block and no string matching the
redaction patterns when a fake secret is planted in an observation.

**Acceptance.** An exported conversation that included one approved
`system_change` shows the command, the approval, and the exit code
inline, with zero secrets.

---

## Phase D — memory and hygiene

### D1. Plain-text machine memory (shortlist #4)

**Goal.** Facts learned while working persist across sessions in a
form the operator can read, edit, and wipe.

**Touch points.** New `payload/agent/memory.py`;
`payload/agent/server.py` (prelude injection + endpoints);
`payload/agent/tools.py` (one new tool); `payload/etc/policy.yaml`
+ `payload/agent/policy.py` (classification for the new tool);
`scripts/install.sh` (create the state file, uninstall removes
it); `index.html` (`/memory` commands); `docs/ARCHITECTURE.md`,
`docs/CONFIGURATION.md`; `tests/smoke.sh`.

**Design.**

- Storage: a single plain-text markdown file,
  `/opt/ai-zombie/state/memory.md`, one fact per line/bullet,
  size-bounded (e.g. 16 KiB / 200 facts; oldest evicted with an
  audited notice). Plain text is the point — no DB, per the
  lessons note's legibility rule.
- Write path: a new `memory.append` tool in the registry so the
  *model* can propose remembering a fact. Classification:
  `user_change` (it changes future agent behaviour), therefore
  approval-gated by default policy — the operator clicks to accept
  each remembered fact. Every append/evict/wipe is audited.
- Read path: injected into the system prompt prelude (next to the
  machine-facts block `_render_index`/`post_message` already
  build), clearly delimited with provenance, always in full (it is
  bounded, so no retrieval logic).
- Operator controls: `/memory` (show), `/memory add <fact>`
  (operator-initiated append, no approval needed since the operator
  typed it — still audited), `/memory forget <n>`, `/memory wipe`.
  The file is also editable directly with any editor as root,
  which the docs should state explicitly.
- Installer: create the file empty (idempotently) with sane
  ownership; `scripts/uninstall.sh` removes it with the rest of
  state; `verify`/`doctor` check ownership/mode.

**Tests.** Smoke: compile; a python regression for the bound/evict
logic; `subcommands`/noninteractive untouched but re-run because
`install.sh` changed. Verify no `sudo` in `memory.py`.

**Acceptance.** A fact approved in one conversation influences a
fresh conversation after service restart, is visible via
`/memory`, and disappears after `/memory wipe` — with all four
steps present in the audit log.

### D2. Deterministic redaction/clipping filters (shortlist #10)

**Goal.** Chat output is scrubbed of secret-shaped strings by
construction; tool output entering the prompt is clipped and
screened. Fixed code paths, never a plugin API.

**Touch points.** `payload/agent/audit.py` (export its `redact()`
for reuse or lift patterns into a shared module),
`payload/agent/server.py` (outbound filter on replies, inbound
filter on tool observations), docs.

**Design.**

- Outbound: run the reply (and streamed tokens at flush boundaries,
  once A1 lands) through the same secret patterns `audit.py`
  already maintains (`sk-…`, `sk-ant-…`, key-like env values, ssh
  keys) before it reaches the browser or history. Redactions are
  visible (`***REDACTED***`) and counted in an audit event so the
  operator knows scrubbing happened.
- Inbound: tool observations are already size-clipped by the shims;
  add a light prompt-injection heuristic on observation text
  (flag, don't block: strings like "ignore previous instructions"
  produce a system-note annotation in the observation so the model
  and the operator both see the warning). Keep heuristics few,
  fixed, and documented — this is a tripwire, not a security
  boundary, and docs must say so.
- Single source of truth for patterns: refactor so `audit.py`,
  the outbound filter, and C3's export all call one function.

**Tests.** Python regression: a reply containing a planted
`sk-`-style token is redacted in the API response and in history;
audit shows the redaction event.

**Acceptance.** The agent echoing a secret from a file read can no
longer put that secret on screen or in the DB unredacted.

---

## Phase E — proactivity and installer work

### E1. Scheduled read-only check-ups (shortlist #3)

**Goal.** A systemd timer runs a canned `read_only` prompt (disk,
failed units, pending security updates) and leaves the report in
chat history for the operator's next visit.

**Touch points.** New `payload/systemd/ubuntu-zombie-checkup.timer`
+ `.service`; new `payload/bin/checkup` helper (bash) or a
`server.py --checkup` / small CLI entry in the agent; likely a new
`POST /api/checkup` (localhost + session-gated, or a socket-free
in-process path via a one-shot python invocation);
`scripts/install.sh` (+ uninstall + verify/doctor/repair);
`payload/etc/policy.yaml` (no change to classes — the constraint
is enforced in code); `README.md` subcommands/options if exposed
as an option; `docs/CONFIGURATION.md`; `CHANGELOG.md`;
`tests/smoke.sh`.

**Design.**

- Follow the existing health-timer pattern
  (`ubuntu-zombie-health.timer`): `OnCalendar=daily`,
  `Persistent=true`, oneshot service running as the agent user.
- The check-up entry point posts the canned `/checkup` preset (same
  text as B3) into a **new conversation** tagged `checkup` (reusing
  C1 tags), via the normal `post_message` pipeline — same policy,
  same budgets, same audit — but with a hard override for this
  invocation: `requires_approval` is never bypassed, and
  additionally any non-`read_only` tool call is refused outright
  (not queued silently — queued as pending approval, surfaced in
  `/pending`, per the lessons note: "queued as a pending approval,
  never executed").
- Make it an optional component only if it needs opt-in; the
  lessons note frames it as core chat behaviour, so default-on with
  `ZOMBIE_CHECKUP_ONCALENDAR` / `ZOMBIE_CHECKUP_DISABLE=1` env
  knobs is the better fit than the `ZOMBIE_INSTALL_<X>` pattern —
  decide at implementation time with the option-contract memory in
  mind (dry-run/receipt stanzas, uninstall reversal apply either
  way).
- Installer work must keep `install` idempotent (unit files
  compared before copy, `systemctl daemon-reload` only on change)
  and extend `verify`/`doctor`/`repair` to know the new units.

**Tests.** Smoke `subcommands` unchanged; `standards` gains a check
that the new unit files exist in `payload/systemd/`; noninteractive
path re-verified. Manual VM: run the service once, confirm a tagged
conversation appears with a report and zero executed non-read-only
actions.

**Acceptance.** The morning after install, `/conversations` shows a
`checkup` conversation summarising disk, failed units, and pending
updates; the audit log shows only `read_only` decisions for it.

### E2. Ollama discovery parity with LM Studio (shortlist #9)

**Goal.** An operator already running Ollama gets the same
no-cloud-key experience LM Studio users get.

**Touch points.** `scripts/install.sh` (LAN scan),
`payload/agent/providers.py` (provider spec / models.json
handling), `docs/CONFIGURATION.md`, `tests/smoke.sh` (import smoke
per the provider recipe in `CONTRIBUTING.md`), `CHANGELOG.md`.

**Design.**

- Extend the existing install-time LAN scan to also probe the
  Ollama port (11434): Ollama exposes an OpenAI-compatible
  endpoint at `/v1`, so discovery can reuse the same
  `GET /v1/models` probe with a second port, honouring
  `ZOMBIE_SKIP_LLM_SCAN` and adding `ZOMBIE_OLLAMA_SCAN_PORT`.
- Because the endpoint is OpenAI-compatible, prefer reusing the
  `lmstudio`-style custom-provider path (base URL written to
  `~/.pi/agent/models.json`) over adding a distinct provider class;
  add an explicit `ollama` `_ProviderSpec` only if the bridge needs
  provider-specific behaviour. Document env vars
  (`OLLAMA_API_KEY`-equivalent placeholder, model override)
  following the table pattern in `docs/CONFIGURATION.md`.
- Non-interactive mode: discovery results are advisory; explicit
  env config always wins; nothing new becomes *required* env.

**Tests.** Per the `CONTRIBUTING.md` provider recipe: add the
import smoke test; `noninteractive` smoke re-run to prove no new
required env.

**Acceptance.** On a LAN with an Ollama host, install discovers it
and the chat works with no cloud key; on a LAN without one, install
behaviour is unchanged.

---

## 4. Cross-cutting workstream (applies to every phase)

- **Lint/test discipline.** `make lint` and `make test` after every
  change; new shell helpers under `payload/bin/` keep the bash
  shebang and ShellCheck cleanliness.
- **Docs.** Each phase updates `docs/CONFIGURATION.md` (new env
  vars), `docs/ARCHITECTURE.md` (new endpoints, memory, check-up
  flow), `README.md` (subcommands/options if any), and the chat
  command documentation; `CHANGELOG.md` + `VERSION`
  (`date -u +%Y.%m.%d.%H.%M.%S > VERSION`) per release checklist.
- **Idempotence audits.** Phases D1 and E1/E2 touch
  `scripts/install.sh`; each must re-verify `install` convergence
  and the `ZOMBIE_NONINTERACTIVE=1` path before handing back.
- **Negative-lesson guardrails** (from Group 5 of the lessons
  note) are standing review criteria for every PR in this plan:
  no new dependencies, no plugin surface, no multi-user concepts,
  no ambient content injection, approvals remain explicit UI
  interactions, and any future embedding of/into Open WebUI
  re-reads its license first.

## 5. Open questions to settle before Phase A starts

1. **Streaming depth.** Is tool-activity streaming alone acceptable
   for A1's first release, with token streaming following once the
   pi-mono bridge grows delta support — or is token streaming a
   hard requirement for the phase?
   ANSWER: Not Hard!
   
2. **Check-up default.** Should E1 be default-on (env-disable) or
   an opt-in `ZOMBIE_INSTALL_CHECKUP` optional component? The
   lessons note leans core; the options contract leans opt-in.
   ANSWER: Optional!
   
3. **Memory approval ergonomics.** Is one approval click per
   remembered fact acceptable, or should `memory.append` get an
   `auto` policy default with the audit log as the safety net?
   (Plan assumes approval-gated; relaxing it is a policy.yaml edit,
   not a code change.)
   ANSWER: auto and log!
   
4. **Tag storage shape.** JSON-array column (planned) versus a
   normalised `tags` table — the former is simpler; the latter is
   only needed if tag queries grow beyond C1's filter.
   ANSWER: JSON!
   
5. **`#journal:` scope.** Should journal references land with B2 or
   be deferred until a `journalctl` read-only shim exists in
   `tools.py`? (Plan text assumes it ships with B2 via `shell.run`
   being avoided and a small dedicated shim added instead — confirm
   appetite for one new read-only tool.)
   ANSWER: Confirmed!

---

*Companion to [`OPEN-WEBUI-LESSONS.md`](OPEN-WEBUI-LESSONS.md) and
[`OPEN-WEBUI-POSSIBILITIES.md`](OPEN-WEBUI-POSSIBILITIES.md). Like
all files in `docs/research/`, this is a planning note, not product
documentation, and it may drift from the code once implementation
begins.*
