# Phase 1 Option A — deep implementation analysis

Deep analysis of the best implementation of **Phase 1, Option A** of
[`improvements-8-plan.md`](improvements-8-plan.md) (move the shipped
`pi` bridge to `--mode rpc` so every tool execution round-trips
through the Python mediator). This document is design analysis only;
nothing here is implemented.

Owner requirements folded into this analysis, verbatim in intent:

1. **Control.** The chat UX must be able to run in the current
   "full root, make it happen" mode *and* in a mediated "router"
   mode, switchable by the operator.
2. **Truth in the chat UX.** The full reality of the AI agent's
   interaction with the machine must be available in the chat UI,
   especially in `/verbose` mode.
3. **Truthful documentation.** All docs must describe what actually
   ships, at every intermediate point.
4. **Complete `/export`.** `/export` must produce a full and complete
   dump — tool logs, decisions, audit trail, everything.

## 1. Ground truth today (verified against the tree)

The state the plan's Phase 1 starts from, re-verified for this
analysis at the current tree:

- `payload/agent/pi-mono-bridge.mjs` spawns
  `pi --mode json -p <rendered prompt>` with pi's real built-in tools
  (`read, bash, edit, write, grep, find, ls`) enabled
  (`PI_BUILTIN_TOOLS`, lines 141 and 265–271). pi executes those
  tools **in-process** as the agent account, which holds
  `NOPASSWD:ALL` sudo.
- The bridge only *logs* `tool_execution_*` events and re-emits them
  as advisory `progress` frames (lines 397–444). It never emits the
  `{"type":"tool_call"}` frame that `payload/agent/pi_mono.py`
  mediates (line 313), so `on_tool_call` in
  `payload/agent/server.py` (line 736: schema validation →
  `policy.classify_tool` → approval queue → audit) never runs on the
  production path. It runs only under
  `tests/fixtures/stub-pi-mono.mjs`.
- The system prompt (`server.py`, `APPEND_SYSTEM_TEMPLATE`) actively
  instructs the model to use `sudo` and to never conclude it lacks
  permissions.
- The chat UI (`payload/agent/templates/index.html`) renders bridge
  `progress` frames as `tool_start`/`tool_end` activity lines with
  `classification: "bridge"`, `decision: "running"` — labels that
  visually resemble the mediated vocabulary while nothing was
  classified or decided. These frames are SSE-only; they are **not**
  persisted to history, so a page reload silently erases the record
  of what the agent did.
- `/export` (`uzExportConversation`, `index.html` line 1538) fetches
  `GET /api/conversation/<id>` and downloads (a) a Markdown file
  containing only `user`/`assistant` messages and (b) the raw JSON of
  that one response. Tool activity, decisions, audit entries, and the
  per-turn bridge log (`pi-mono.<ts>.<pid>.log`) are all absent.
- `SECURITY.md` ("output executes only through the approval gate")
  and `docs/ARCHITECTURE.md` describe the mediated design, not the
  shipped behaviour.

Everything below has to repair this while preserving the thing the
owner values about the current shape: an agent that can actually do
the work.

## 2. What pi 0.80.10 actually provides (correcting an assumption)

The plan's Option A sketch ("pi's RPC protocol … every tool call
arrives as an observable request that the bridge … answers with
Python's `tool_result`") needs one correction, confirmed against the
upstream documentation for the pinned version
(`packages/coding-agent/docs/rpc.md` and
`packages/coding-agent/docs/extensions.md` in the pi repository;
pinned version `0.80.10` per `payload/agent/bridge-dependencies.lock`
and `payload/agent/pi-mono.version`):

- **RPC mode does not hand tool execution to the client.** `--mode
  rpc` is a JSON command/event protocol over stdio (`prompt`,
  `steer`, `abort`, `get_state`, …) with the same event stream as
  `--mode json` (`tool_execution_start/update/end`, `message_update`,
  `agent_end`, …). Built-in tools still execute inside the pi
  process. There is no stock "client answers tool calls" round-trip.
- **The interception point is the extension `tool_call` event.**
  pi extensions (TypeScript modules loaded with `pi -e <path>` or
  from an extensions directory) can subscribe to `tool_call`, which
  fires after `tool_execution_start` and **before the tool
  executes**, and can block it by returning
  `{ block: true, reason }`. Upstream documents this hook as
  fail-safe: an error thrown by a `tool_call` handler blocks the
  tool.
- **Extensions can converse with the RPC client synchronously.** The
  extension-UI sub-protocol (`ctx.ui.confirm` / `input` / `select`)
  emits `extension_ui_request` on stdout and blocks until the client
  writes a matching `extension_ui_response` on stdin. In RPC mode
  `ctx.hasUI` is `true` and this path is fully functional.
- **Extensions can also register custom tools** that execute inside
  the extension, and `tool_result` handlers can modify results.
- RPC mode is a **long-lived session**: the process stays up across
  turns, accepts `prompt` commands, and manages its own session
  state — unlike today's one-shot `-p` invocation that re-renders the
  whole history into a single prompt string each turn.

Consequence: the honest reading of "Option A" for this pi version is
**`--mode rpc` plus a shipped mediation extension**. The extension is
the enforcement point; RPC mode is the transport that (a) lets the
bridge answer the extension's blocking questions and (b) replaces the
fragile history-in-prompt rendering with a real session. This is not
a fallback to Option B: Option B's defining move is
`--no-builtin-tools` + replacing the tool surface; here pi's genuine
tools remain and are gated in place.

## 3. Candidate shapes and the recommendation

Two viable sub-shapes of Option A, given §2:

**A1 — gate-in-place (recommended).** pi keeps its built-in tools;
the shipped mediation extension intercepts every `tool_call`, ships
`{id, name, args}` to the bridge, the bridge forwards it to Python as
the existing `{"type":"tool_call"}` protocol frame, and Python's
`on_tool_call` pipeline (schema → classify → approve → audit) returns
a verdict. *Allow* → the extension returns nothing and pi executes
its own tool; *deny/queue* → the extension returns
`{ block: true, reason }` and the model sees the reason as the tool
error observation.

**A2 — full round-trip execution.** `--no-builtin-tools`, plus the
extension registers the closed `payload/agent/tools.py` registry
(`shell.run`, `fs.read`, `fs.list`, `fs.write`, …) as custom pi
tools whose handlers call back to Python, which executes via
`tools_mod.dispatch` and returns the result. Execution moves into
Python entirely.

| Dimension | A1 gate-in-place | A2 full round-trip |
| --------- | ---------------- | ------------------ |
| Mediation (classify/approve/audit) | full | full |
| Execution locus | pi built-ins | Python registry shims |
| Tool surface seen by model | pi's native, well-trained tools | custom re-implementations |
| "Zero usable tools" regression risk (`pi-mono-bridge.mjs:137-139`) | none — built-ins stay | real — the exact failure mode already recorded |
| Behavioural distance between router-on and router-off modes | minimal (same tools, gated vs not) | large (different tool surface per mode) |
| Streaming tool output (`tool_execution_update`) | preserved | lost unless registry shims re-implement streaming |
| Result truncation / arg drift between pi and registry | none | permanent dual-maintenance |
| Path allow-lists in `tools.py` | enforced at *decision* time via arg inspection, not at exec | enforced at exec |
| New code | extension + bridge rework + classifier adapter | all of A1 plus registry-as-pi-tools shim layer |

**Recommendation: A1**, for three reasons that align directly with
the owner's requirements:

1. **Control.** The two operator modes ("full root" and "router")
   become one code path differing only in whether the verdict is
   consulted. The model's capabilities, tool surface, prompt, and
   output are identical in both modes, so switching the router on
   does not degrade the agent into a different, worse product — it
   adds a gate in front of the same agent.
2. **Truth.** Because pi executes its own tools in both modes, the
   telemetry (`tool_execution_start/update/end`) is identical in both
   modes; the chat UX can show one honest vocabulary everywhere.
3. **Risk.** A2 re-runs the experiment that already failed once
   (`--no-builtin-tools` → tool-call-shaped text). A1 cannot lose
   tools because it never removes them.

Trade-off accepted knowingly: in A1 the `tools.py` shims stop being
the executor on the production path; the registry becomes the
*schema + classification adapter* (see §4.3). Execution-time
enforcement (e.g. `fs.write` allow-list checks at write time) is
approximated by decision-time argument inspection. For a root-capable
agent this is an acceptable trade: the policy gate was always an
approval gate, not a sandbox, and `SECURITY.md` already says the
operator is the last line of defence. If the owner later wants
execution-time enforcement too, A2 can be layered on for specific
tools (e.g. only `write`/`edit`) without reopening this design.

### 3.1 Extension ↔ bridge channel

Two candidate channels for the extension's blocking question:

- **(a) Extension-UI sub-protocol (recommended).** The extension
  calls `ctx.ui.input(JSON.stringify(question))` (or `confirm` with a
  structured title) with a reserved marker prefix; the bridge
  intercepts `extension_ui_request` frames carrying the marker,
  translates them to `{"type":"tool_call"}` protocol lines for
  Python, and answers with `extension_ui_response` when Python's
  `tool_result` arrives. Genuine (non-marker) UI requests are
  answered `cancelled: true` and logged. Pros: uses only the pinned,
  upstream-documented surface; inherits ordering with the event
  stream on the same stdio pair; zero new attack surface; no new
  dependencies. Cons: JSON-in-a-string envelope is inelegant and
  must be versioned.
- **(b) Side-channel Unix socket.** The bridge (or Python) listens on
  a private socket whose path is passed via env; the extension
  connects and speaks a clean framed protocol. Pros: clean framing.
  Cons: a second interface to create, permission, audit, and tear
  down; concurrency and ordering between socket and stdio must be
  reconciled; more code inside the pi process.

**Recommend (a)**, with the envelope documented in the bridge header
comment block (which the plan already requires as work item 1) and
covered by a fixture test. Revisit (b) only if a future pi version
breaks the extension-UI path.

### 3.2 Parallel tool calls

Upstream: sibling tool calls from one assistant message are
*preflighted sequentially* (so `tool_call` handlers fire one at a
time) and then executed concurrently. This matches Python's
single-threaded `run_turn` read loop: mediation questions arrive
serialized, verdicts return serialized, and only the already-approved
executions overlap. The bridge must therefore tolerate
`tool_execution_end` frames interleaving out of verdict order and key
everything by `toolCallId` (it already keys `toolStarts` by id).

## 4. Concrete work plan

### 4.1 Bridge rework (`payload/agent/pi-mono-bridge.mjs`)

1. Spawn `pi --mode rpc` with stdio pipes both ways, `--provider` /
   `--model` as today, `--append-system-prompt` as today, and
   `-e <path>` pointing at a new shipped extension
   `payload/agent/pi-mediator.ts` (installed under
   `/opt/ai-zombie/agent/`). Do **not** rely on auto-discovery
   directories (`~/.pi/agent/extensions/`): auto-discovery would also
   load anything an attacker drops there; pass the single pinned path
   explicitly and run pi with an isolated `PI_*` config location.
2. Replace the one-shot `-p` prompt with the RPC `prompt` command per
   turn. Near-term the bridge stays one-process-per-turn (the Python
   driver and history rendering already assume that); the RPC session
   makes a later persistent-session upgrade possible without another
   protocol change, but that is out of scope for phase 1.
3. Version tripwire (shared with F6, land once): at startup run the
   equivalent of `pi --version`, compare against
   `payload/agent/pi-mono.version` / `bridge-dependencies.lock`, and
   `fatal()` on mismatch before the first turn.
4. Translate frames:
   - `extension_ui_request` with the mediation marker →
     `{"type":"tool_call","id","name","args"}` to Python; hold the
     request open; on Python's `tool_result` reply with the matching
     `extension_ui_response` (allow, or block+reason).
   - `tool_execution_start/end` → keep today's enriched `progress`
     frames (args, duration, bytes, exit code) — these are now the
     *execution* record that pairs with the *decision* record.
   - **Tripwire:** a `tool_execution_start` whose `toolCallId` was
     never mediated (no marker round-trip seen) while the router is
     on aborts the turn with `{"type":"error","message":"unmediated
     tool execution: …"}` and pi is killed. This converts silent
     regression (extension failed to load, upstream renamed the
     event) into a loud failure, per the plan's work item 4.
   - `message_update` text deltas → `token` frames (unchanged).
   - terminal `agent_end` → `final` (unchanged, including retry
     handling).
5. Replace the "brittle" header comment (lines 24–39) with the
   confirmed RPC + extension contract for the pinned version, per
   plan work item 1.

### 4.2 Mediation extension (`payload/agent/pi-mediator.ts`)

Small, single-purpose, shipped and pinned alongside the bridge:

- `pi.on("tool_call", …)`: serialize `{id, toolName, args, mode}`
  into the marker envelope, ask via `ctx.ui.confirm`/`input`, parse
  the verdict; return `undefined` (allow) or
  `{ block: true, reason }`.
- Fail closed: any error, timeout, or malformed verdict blocks the
  call (upstream already blocks on handler errors; the extension
  must not catch-and-allow).
- No other behaviour. No custom tools, no commands, no network.
- Router-off mode: the extension still runs and still reports every
  call (so the truth requirements in §6 hold in both modes) but the
  verdict is decided by Python as auto-allow (§5). The extension
  itself has no mode logic — one code path, mode lives in Python.

### 4.3 Python side (`pi_mono.py`, `server.py`, `tools.py`)

1. `pi_mono.run_turn()` needs no protocol change: the bridge still
   emits `tool_call` and consumes `tool_result` (the plumbing already
   exists and is stub-tested). Extend the `start` message with
   `{"router": bool}` so the bridge/extension can label telemetry.
2. **Classifier adapter.** `on_tool_call` today validates against
   `TOOL_REGISTRY` logical names (`shell.run`, `fs.read`, …); pi
   sends its native names (`bash`, `read`, `write`, `edit`, `grep`,
   `find`, `ls`). Add an explicit mapping table in `tools.py`
   (pi name + args → logical registry name + normalized args), e.g.
   `bash{command}` → `shell.run{command}`, `write`/`edit` →
   `fs.write{path,...}`, `read` → `fs.read{path}`, `ls`/`find`/`grep`
   → read-only classes with path checks. Unknown pi tool names fail
   closed as `schema_rejected` (the registry stays closed). This
   keeps `policy.classify_tool`, the allow-lists, both per-turn
   budgets, and the destructive-confirmation phrase enforcement
   exactly where they are — `payload/etc/policy.yaml` rules match on
   the logical names and command text and need no rewrite.
3. **Approval semantics: hold-open.** Today a gated call returns
   `operator_approval_required … do not retry`, ends the model's
   attempt, and the approved execution later runs through
   `tools_mod.dispatch` in `server.approve()` — so the model never
   sees the result of an approved call. With A1, prefer **holding
   the mediation round-trip open** until the operator decides:
   `on_tool_call` blocks on the pending-approval entry, and approval
   releases the verdict so *pi executes the approved call itself and
   the model sees the real result*. Requirements:
   - a keepalive: while a pending approval exists, periodically
     `_touch()` the idle watchdog (Python) and reset the bridge idle
     timer, so a slow human does not trip the timeout;
   - a bound: after a configurable wait (default: the turn's idle
     timeout), auto-resolve to *deny (operator absent)* with audit +
     history events — never leave a zombie turn;
   - restart handling stays with Phase 4b (F8): orphaned pendings
     expire.
   The existing queue-then-`server.approve`-executes path is no
   longer needed as a fallback: after a hold-open deny (including the
   operator-absent timeout) the model has already been told. Delete
   the post-hoc `dispatch` execution path once hold-open lands so
   there is exactly one way an approved tool runs (through pi,
   mediated). This is a real semantics improvement over today and
   should be called out in the changelog.
4. **System prompt.** Rewrite `APPEND_SYSTEM_TEMPLATE` (plan work
   item 5) to be mode-aware and honest: router-on text describes the
   approval gate, the budgets, and the confirmation phrase; router-off
   text keeps the current "your sudo is real" guidance. Never show
   the router-on text while the router is off, or vice versa.

## 5. The router: operator control over mediation

The owner's requirement 1 is an explicit dual mode. Design:

- **Naming.** "Router" in the UI and docs; internally
  `mediation mode`: `router` (mediated) vs `direct` ("full root,
  make it happen" — the current behaviour).
- **State.** A server-side persisted setting (a `settings` row in the
  history DB or a small root-readable state file), *not* a
  browser-local flag: the mode changes what the machine enforces, so
  it must survive reloads and be one truth for all clients.
- **Controls.**
  - `/router [on|off]` slash command (registered in the `/help`
    catalog with alias support, matching the existing slash-command
    conventions in `index.html`), hitting a new
    `POST /api/router` endpoint;
  - `ZOMBIE_TOOL_ROUTER=0|1` env/secrets override for headless
    setups, and an installer option following the existing
    `ZOMBIE_NONINTERACTIVE=1` conventions (missing required input in
    non-interactive mode is not an issue here — the setting has a
    default).
- **Default: router ON.** F1 is the repo's one CRITICAL finding;
  shipping mediation-off-by-default would re-create it behind a
  flag. Direct mode is a deliberate, audited operator opt-out — the
  owner keeps the "make it happen" experience one command away.
- **Turning the router off is itself a privileged action.** Route
  the toggle through the policy gate: classify `router.off` as a
  gated class (approval required, no phrase) and `router.on` as
  auto. Both transitions write audit events
  (`router_mode_changed`, with actor = chat session) and a history
  event so the transcript shows exactly when the ground rules
  changed. This satisfies the non-negotiable "any new privileged
  behaviour goes through `policy.py` and `audit.py`".
- **Visibility.** The chat banner shows the current mode
  persistently (not only in verbose mode); every turn's events are
  labeled with the mode active when the turn started; `/status`-like
  surfaces and `install.sh verify`/`doctor` report it.
- **Mid-turn changes** take effect at the next turn; the mode is
  snapshotted into the `start` message so one turn is never
  half-and-half.
- **Direct mode is still observed and audited.** The extension and
  bridge report every call either way; Python records
  `tool_call`/`tool_observation` history events and audit entries
  with `decision: "direct"` instead of `auto/queued`. Budgets: keep
  the per-turn call budgets enforced even in direct mode (they bound
  runaway loops, not operator intent); only approvals and denials
  are disabled. Direct mode without observation would violate
  requirement 2.

## 6. Truth in the chat UX, especially `/verbose`

Principle: the UI never displays a mediated-sounding label for an
unmediated action, and everything shown live is also replayable.

1. **One honest event vocabulary.** Replace the current
   `classification: "bridge"` / `decision: "running"` pseudo-labels
   with the real values from the mediation pipeline:
   `classification` = policy class (or `unclassified` only for
   telemetry that genuinely precedes classification),
   `decision` ∈ `auto | queued | approved | denied | direct |
   schema_rejected | budget_exceeded | error`. In direct mode the
   activity line says `direct (router off)` — plainly, not dressed
   up.
2. **Persist tool telemetry.** Today `on_bridge_event` forwards
   `progress` frames to SSE only; a reload loses them. Write
   `tool_start`/`tool_end` (with args summary, duration, bytes, exit
   code, decision, classification, mode) into history events so
   `renderConversation` replays the same truth after reload. Bound
   growth with the existing `_truncate_obs` discipline.
3. **`/verbose` shows the full account.** Non-verbose keeps today's
   calm surface ("Working…"). Verbose shows, per tool call: tool
   name, full args (client already receives `args_summary`; add a
   `args_full` field on the SSE/history payload, bounded at a
   documented limit well above the 200-char summary), classification,
   decision and who decided (auto/operator), duration, exit code,
   stdout/stderr byte counts, and — new — a truncated result excerpt
   (reusing the 4,000-char `_truncate_obs` bound) with a pointer to
   the full record (`log_path` of the per-turn bridge log). Also
   show: mode banner per turn, budget counters
   (`elevated_calls/max`), skill injections (`skill_active` events
   already exist), and the system-prompt variant in effect.
4. **Turn provenance line.** In verbose mode, end each turn with the
   existing background-activity summary plus: mediated call count,
   direct call count (must be zero in router mode — if not, the
   tripwire fired), and the bridge log path.
5. **No silent drops.** Bridge frames that Python does not recognise
   are currently appended to `events` and ignored; in verbose mode
   surface a count of unrecognised frames so schema drift is visible
   in the UI, not only in the log file (complements F6).

## 7. `/export`: full and complete dump

Move export from "what the browser happens to have" to a
server-assembled bundle.

1. **New endpoint** `GET /api/conversation/<id>/export` returning one
   JSON document:
   - `meta`: product version (`VERSION`), bridge/pi pinned versions
     (`bridge-dependencies.lock` digest, `pi-mono.version`), export
     timestamp, hostname, agent user, router mode history for the
     conversation;
   - `conversation` + `messages`: as today (`get_messages`);
   - `events`: the full `get_events` stream — `tool_call`,
     `tool_observation`, `pending_tool_call`, `skill_active`, the new
     persisted `tool_start`/`tool_end` telemetry and
     `router_mode_changed` events;
   - `audit`: the slice of `/var/log/ubuntu-zombie/audit.log` whose
     entries carry this `conversation_id` (audit entries already
     record it; add a small scan-with-filter helper in `audit.py`,
     reading the current file plus rotated siblings best-effort);
   - `bridge_logs`: for each assistant message, the `log_path` meta
     already persisted (`server.py` line 969) — include the file
     content inline when readable, else the path and the reason it
     was skipped. These logs contain every raw pi event including
     full tool output, which is exactly the "truth of the AI Agent
     interaction" the owner wants preserved;
   - `policy`: the effective policy digest (path, sha256, key
     settings: default class, budgets, confirmation phrase) so a
     reader can interpret the decisions.
2. **Redaction before export.** Bridge logs and audit slices pass
   through the existing secret-redaction pass in `audit.py` (which
   already strips known key env values and bearer tokens) *again* at
   export time, because bridge logs are raw. Document that the export
   is operator-facing and may still contain sensitive file contents
   the agent read — that is inherent to a truthful dump.
3. **Size honesty.** No silent truncation: include per-section byte
   counts, and when a bridge log exceeds a cap (e.g. 10 MiB per
   file), include head+tail with an explicit
   `truncated: {omitted_bytes: N}` marker — never drop a file without
   saying so.
4. **Client.** `/export` (alias `/save`) downloads:
   - `…-transcript.md` — the Markdown transcript, now including a
     per-turn tool-activity section (tool, decision, classification,
     duration, exit code) so the human-readable file is also honest;
   - `…-full.json` — the export bundle above.
   Update the `/help` catalog entry ("Download the complete
   conversation record: transcript, tool calls, decisions, audit
   slice, and bridge logs.") so the description matches reality.
5. **Auth.** The endpoint sits behind the same password gate as every
   other `/api/*` route; nothing new is exposed on the loopback
   surface.

## 8. Documentation truthfulness

Per the plan's Option C obligation, honesty must hold **at every
commit**, not just at the end:

1. **Landing order.** The very first PR of this phase updates
   `SECURITY.md`, `README.md`, `docs/ARCHITECTURE.md`, and
   `promotion/messaging/KEY-FEATURES.md` to state plainly that the
   shipped path today executes tools unmediated (F1's Option C
   text). Subsequent PRs then walk the docs forward as behaviour
   actually changes. No document ever describes the router before it
   exists.
2. **End-state docs.**
   - `docs/ARCHITECTURE.md`: the RPC + extension mediation shape, the
     tripwire, the router modes, and the trust statement for each
     mode ("router off = the operator has chosen unmediated root").
   - `SECURITY.md`: replace "output executes only through the
     approval gate" with the two-mode truth and the default;
     document that direct mode is audited-but-unenforced.
   - `docs/CONFIGURATION.md`: `ZOMBIE_TOOL_ROUTER`, the approval
     hold-open timeout, export size caps, and the mode's interaction
     with the existing budget/timeout settings.
   - `README.md` Subcommands/quickstart and the `/help` text for
     `/router`, `/verbose`, `/export`.
   - `promotion/messaging/KEY-FEATURES.md`: claims must match the
     shipped default (router on) and disclose the opt-out (the
     stored repo convention: promotion claims must match
     KEY-FEATURES).
3. **Doc drift guard.** Extend the standards group in
   `tests/smoke.sh` with greps that fail CI if the known-false
   sentences reappear (e.g. the old `SECURITY.md` approval-gate claim
   text) — cheap, and it makes truthfulness regression-tested.

## 9. Testing plan

All non-root, matching `tests/smoke.sh` conventions:

1. **Fake pi speaks RPC + extension protocol.** Extend
   `tests/fixtures/fake-pi-json.mjs` (or add `fake-pi-rpc.mjs`) to:
   accept `prompt`, emit the event stream, load nothing but honour
   the mediation envelope by emitting `extension_ui_request` frames
   for scripted tool calls and executing/skipping based on the
   response. Scenarios: allow, deny, queue+approve (hold-open),
   queue+timeout, schema-rejected name, budget exhaustion,
   destructive phrase, parallel siblings, unmediated-execution
   tripwire, version mismatch at startup, malformed envelope →
   fail-closed block.
2. **Production-path group (Phase 2 alignment).** Run the **real**
   `pi-mono-bridge.mjs` against the fake pi and assert every executed
   tool has a matching mediated `tool_call` audit + history record;
   assert the tripwire turns an unmediated execution into a red test.
3. **Router tests.** Toggle via `/api/router`: off→on and on→off
   audit events; direct-mode calls recorded with `decision:
   "direct"`; budgets still enforced in direct mode; mode snapshot
   per turn.
4. **Export tests.** Create a conversation with mixed decisions via
   the stub; call the export endpoint; assert presence of messages,
   events, audit slice filtered to the conversation, bridge log
   content, redaction of a planted fake key, and explicit truncation
   markers for an oversized log.
5. **UI/replay tests.** History now contains tool telemetry: assert
   `GET /api/conversation/<id>` returns `tool_start`/`tool_end`
   events after a stubbed turn (reload truthfulness).
6. Keep the stub-based groups as unit coverage, labeled per the
   plan's Phase 2 work item 3.

## 10. Risks and mitigations

- **Upstream extension API drift.** Mitigated by the version
  tripwire (startup assert against `bridge-dependencies.lock`) and
  the fail-closed extension: if the `tool_call` hook stops firing,
  the execution tripwire aborts the turn rather than silently
  bypassing.
- **Extension fails to load** (syntax error, missing file): pi would
  run unmediated. Mitigation: the bridge requires a handshake — the
  extension emits one marker `extension_ui_request` at session start
  (`mediator_ready`); no handshake before the first `prompt` →
  bridge aborts (router mode) or logs prominently (direct mode).
- **Hold-open approvals vs watchdogs.** Keepalive touches plus a
  bounded auto-deny (§4.3.3) keep the three-layer deadline design
  intact; smoke-test the timeout path.
- **`ui.confirm` misuse collision.** A genuine extension UI dialog
  (none shipped, but future) could collide with the marker envelope;
  the marker is a UUID-ish reserved prefix recorded in the bridge
  header contract, and non-marker requests are answered
  `cancelled: true` and logged.
- **Performance.** One stdio round-trip per tool call (~ms) is noise
  against LLM latency; parallel siblings serialize only their
  preflight, matching upstream behaviour anyway.
- **Scope creep toward persistent sessions.** RPC enables it, phase 1
  does not do it; recorded as an explicit non-goal so review stays
  tractable.

## 11. Delivery sequence (reviewable slices)

1. **PR 1 — honesty first (Option C, no behaviour change):** doc
   corrections per §8.1 + smoke-test drift guards.
2. **PR 2 — bridge to RPC, no mediation yet:** `--mode rpc`
   transport, version tripwire, header contract, identical external
   behaviour; production-path smoke group lands in its weak (Phase 2
   interim) form.
3. **PR 3 — mediation extension + classifier adapter + tripwire:**
   router permanently on in this PR; hold-open approvals; system
   prompt rework; flip the smoke group to strict; docs advance.
4. **PR 4 — router toggle:** mode state, `/router`, policy class for
   the toggle, audit events, banner, direct-mode labeling; docs and
   `CONFIGURATION.md`.
5. **PR 5 — chat-UX truth:** persisted telemetry, verbose
   vocabulary, provenance lines, replay.
6. **PR 6 — full `/export`:** endpoint, redaction, client, help
   text, tests.

Each PR keeps `make lint` / `make test` green and its docs truthful
in isolation, satisfying the plan's per-phase constraints.

## 12. Acceptance criteria (superset of the plan's Phase 1 list)

- Every tool execution on the production path in router mode
  produces a schema-validated `tool_call`, a policy classification,
  an audit record, and (for gated classes) an operator approval
  round-trip whose result the model actually receives.
- Budgets, allow-lists, and the destructive-confirmation phrase are
  demonstrably enforced on the production path; the tripwire turns
  any unmediated execution into a loud turn failure.
- The operator can switch between router and direct mode from the
  chat; the switch is audited, visible in the banner, and honestly
  labeled on every event; direct mode remains fully observed and
  audited.
- `/verbose` shows the complete per-call account (args, class,
  decision, duration, exit code, bytes, result excerpt, log
  pointer), and the same record survives a reload.
- `/export` produces a complete, redacted, explicitly-truncation-
  marked bundle: transcript, events, decisions, audit slice, bridge
  logs, policy digest, versions.
- At every merged commit, `README.md`, `SECURITY.md`,
  `docs/ARCHITECTURE.md`, and promotion copy describe exactly the
  behaviour that ships at that commit.

## 13. Open questions for the owner

1. Default hold-open approval timeout before auto-deny (proposal:
   the turn idle timeout, i.e. effectively "wait for the operator").
2. Should `router off` require the destructive confirmation phrase
   in addition to approval? (Proposal: approval only — friction
   should not push operators to leave it off permanently.)
3. Export size cap per bridge log before head+tail truncation
   (proposal: 10 MiB).
4. Whether `/router off` should persist across service restarts
   (proposal: yes — it is an explicit operator decision — but it is
   re-announced in the banner and audit log at every startup).
