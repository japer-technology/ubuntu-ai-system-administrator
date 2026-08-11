# Phase A implementation plan: liveness plumbing

This note expands Phase A of
[`OPEN-WEBUI-LESSONS-PLAN.md`](OPEN-WEBUI-LESSONS-PLAN.md) into a
step-by-step implementation plan grounded in the code as it exists
today. Phase A has two work items:

- **A1 — SSE streaming of tokens and tool activity** (shortlist #1):
  during a turn the operator sees live progress instead of a silent
  page.
- **A2 — never lose the operator's words** (Lesson 3): typing during
  a busy turn can never silently vanish.

Like every file in `docs/research/`, this is a research/planning
note, not product documentation, and it may drift from the code once
work begins.

Plan basis: repository state as of 2026-07-09 (VERSION
`2026.07.09.02.13.22`). The parent plan's open question 1 is
answered: **token streaming is not a hard requirement** — tool
activity and turn phases stream first; token deltas are best-effort.

---

## 1. Ground truth: how a turn flows today

Everything below was read from the current code; the design leans on
these exact seams.

### 1.1 Server side

- `payload/agent/server.py` runs a stdlib
  `http.server.ThreadingHTTPServer` on `127.0.0.1` — **each request
  gets its own thread**, so one long-lived response per active turn
  is structurally safe.
- `POST /api/message` (handler `do_POST`) calls
  `app.post_message(conv_id, prompt)` **synchronously** and only
  then writes one JSON body containing `conversation_id`, `reply`,
  and the full `events` + `messages` snapshots. The browser sees
  nothing until the entire turn — including every inline tool call
  and every queued approval — has finished.
- `post_message()` builds the system prompt (machine facts, latest
  `/compress` summary, skill blocks), assembles `history_payload`,
  loads the policy budgets (`max_tool_calls_per_turn`,
  `max_elevated_calls_per_turn`, `max_turn_seconds`), and defines a
  closure `on_tool_call(call_id, name, args)` that validates against
  the closed registry, classifies via `policy.classify_tool`, writes
  `log_tool_call` audit entries and `history.add_event` rows
  (`tool_call`, `pending_tool_call`, `tool_observation`), queues
  approvals into `self.pending`, and dispatches auto-approved
  read-only tools inline.
- Auth: `_guard()` sends 401 for any path not in `_PUBLIC_PATHS`
  unless the `zombie_session` cookie is valid. The cookie is
  `HttpOnly; SameSite=Strict; Path=/`, which browsers send on
  same-origin `EventSource` requests automatically.
- Lifecycle: `post_message` refuses with `dead: true` (HTTP 410)
  when the TTL tombstone has tripped.

### 1.2 The pi-mono layer

- `payload/agent/pi_mono.py` `run_turn()` spawns the bridge
  subprocess, writes one `start` JSON line, then loops on
  `proc.stdout.readline()`. It handles `tool_call` (invokes
  `on_tool_call`, writes back `tool_result`), `final`, and `error`.
  **Unknown event types are appended to `events` and skipped** —
  the exact forward-compatibility hook streaming needs. Every event
  also refreshes the idle-watchdog deadline via `_touch()`, so a
  chatty streaming bridge naturally keeps the watchdog happy.
- `run_turn` returns only after `final`; nothing is surfaced to the
  caller mid-turn. There is **no per-event callback today** — that
  is the first thing A1 must add.
- `payload/agent/pi-mono-bridge.mjs` spawns `pi --mode json -p` and
  already **parses the events streaming needs but discards them**:
  - `message_update` with
    `assistantMessageEvent.type === "text_delta"` — token deltas,
    currently only accumulated into `assistantText`;
  - `tool_execution_start` / `tool_execution_end` — pi executes its
    own built-in tools in `--mode json`, and the bridge currently
    only writes these to its log file (`logLine("pi_tool", …)`).
- The stub bridge `tests/fixtures/stub-pi-mono.mjs` drives the
  Python-mediated `tool_call`/`tool_result` protocol in smoke tests.

### 1.3 Client side

- `payload/agent/templates/index.html` sends turns via
  `uzSendPrompt()`: one `fetch("/api/message")` guarded by an
  `AbortController` and `CLIENT_TURN_TIMEOUT_MS` (720 s), a
  "thinking" placeholder (`showThinking`), then renders `reply`
  through the escape-first `renderMarkdown()` and each event through
  `renderEvent()` plus `renderTurnCounter()`.
- `setBusy(true)` disables the **send button** (the textarea stays
  enabled) and shows the Stop button, which aborts the fetch.
- The `form` submit handler starts with
  `if (sendBtn.disabled) return;` — **a submit during a running
  turn is silently dropped today.** This is the exact bug A2 fixes.
- Slash commands (`handleSlashCommand`) run client-side and are not
  blocked by a running turn once A2 removes the early return —
  their dispatch happens before any network send.

---

## 2. A1 — SSE streaming of tokens and tool activity

### 2.1 Event vocabulary

One SSE stream per turn. Events are JSON objects sent as
`event: <type>` + `data: <json>` frames. The vocabulary mirrors what
`history.events` and the audit log already record, so **the stream
can never show something the audit log does not**:

| SSE event | Payload | Source |
|-----------|---------|--------|
| `phase` | `{"phase": "model"\|"tools"\|"finalising"}` | bridge progress / server transitions |
| `token` | `{"delta": str}` | bridge `message_update` text deltas (best-effort) |
| `tool_start` | `{"tool", "classification", "decision"}` | same code path that writes the `tool_call` history event |
| `tool_end` | `{"tool", "ok", "exit_code"?, "duration_ms"?}` | same code path that writes `tool_observation` |
| `pending_approval` | same fields as the `pending_tool_call` history event | approval queue |
| `turn_done` | the exact JSON body the synchronous path returns today | end of `post_message` |
| `turn_error` | `{"error": str}` (+ `dead` when applicable) | `BridgeError` / exception paths |

Plus SSE comment lines (`: keepalive`) every ~15 s so proxies and
the browser do not time the connection out.

### 2.2 Two-step turn protocol (server)

`payload/agent/server.py`:

1. **Turn registry.** Add to `App` a `self.turns` dict guarded by
   the existing `self._lock`: `turn_id` (uuid hex) → a small state
   record holding a stdlib `queue.Queue` of pending SSE events, the
   conversation id, a `done` flag, and the final payload. Bound the
   queue (e.g. 1000 events) and drop oldest `token` events on
   overflow — phase/tool events are never dropped. Completed turns
   are retained briefly (final payload only) so a stream that
   connects late, or reconnects, receives an immediate `turn_done`
   replay; evict entries after a short TTL or when the next turn
   starts (single operator ⇒ at most a handful live).
2. **`POST /api/message` gains an opt-in `"stream": true` field.**
   Without it the behaviour is byte-for-byte today's synchronous
   path — this keeps every existing smoke test, `curl` usage, and
   the A2 fallback working. With it, the handler:
   - performs the same validations up front (empty prompt, TTL
     dead — refuse *before* registering a turn);
   - registers the turn, spawns a worker `threading.Thread`
     (daemon, named `turn-<id>`) running `post_message` with an
     `emit` callback, and immediately returns
     `{"turn_id", "conversation_id"?}`.
3. **`GET /api/stream/{turn_id}`** on the existing handler:
   - **not** in `_PUBLIC_PATHS` — `_guard()` applies exactly as it
     does to `/api/message`; the session cookie rides along on the
     same-origin `EventSource` request.
   - Sends `200` with `Content-Type: text/event-stream`,
     `Cache-Control: no-store`, no `Content-Length`, then blocks on
     the turn's queue with a timeout used for keepalive comments,
     writing frames until `turn_done`/`turn_error`, then closes.
   - Unknown or already-evicted `turn_id` → single `turn_error`
     frame (or 404 before headers) so the client falls back.
   - **Exactly one active stream per turn** (single operator):
     a second concurrent `GET` for the same turn receives an
     immediate `turn_error` ("stream already attached"); the first
     connection keeps the turn. Client disconnect (broken pipe on
     write) must be swallowed: the worker thread keeps running and
     the queue keeps filling — killing the stream mid-turn must
     leave history intact (acceptance criterion).
4. **Wiring events.** `post_message` grows an optional
   `emit: Callable[[str, dict], None]` parameter (no-op default so
   the synchronous path is unchanged):
   - `on_tool_call` calls `emit("tool_start", …)` right where it
     writes the `tool_call` history event, `emit("tool_end", …)`
     where it writes `tool_observation`, and
     `emit("pending_approval", …)` where it writes
     `pending_tool_call` — one emit next to each existing
     `history.add_event`, never a new code path.
   - the `except BridgeError` / generic-exception arms emit
     `turn_error` with the same error text they persist;
   - the success tail emits `turn_done` with the same dict it
     returns.
   Emits happen **after** the corresponding audit/history write so
   a crash between the two can only under-report to the stream,
   never over-report.

### 2.3 Bridge progress events (pi-mono layer)

1. **`payload/agent/pi-mono-bridge.mjs`.** Emit two new
   bridge-protocol event types on stdout, both already parsed
   internally:
   - `{"type": "progress", "kind": "tool_start"|"tool_end",
      "name": <toolName>, "id": <toolCallId>}` from the existing
     `tool_execution_start`/`tool_execution_end` arm (today it only
     logs). This is what makes live tool lines work in production,
     where pi runs its own built-in tools and Python's
     `on_tool_call` is not exercised per call.
   - `{"type": "token", "delta": str}` from the existing
     `message_update` `text_delta` arm (keep accumulating
     `assistantText` exactly as today). This is the best-effort
     token stream; providers that do not delta simply never emit
     it. Coalesce very small deltas (flush on ~50 ms or ~64 chars)
     so a fast provider cannot flood stdout line-by-character.
   Document both in the protocol comment blocks at the top of the
   bridge **and** of `payload/agent/pi_mono.py` (they must stay in
   sync).
2. **`payload/agent/pi_mono.py` `run_turn()`** gains an optional
   `on_event: Callable[[dict], None] | None` parameter. In the read
   loop, after `events.append(event)`, call `on_event(event)` for
   `token` and `progress` types (wrapped in a broad try/except so a
   streaming bug can never kill a turn). No other change: unknown
   types already fall through, `_touch()` already refreshes the
   watchdog per event, and old bridges/stubs that never emit these
   types keep working unmodified.
3. **`server.py` glue.** `post_message` passes an `on_event` that
   translates bridge `token` → SSE `token` and bridge `progress` →
   SSE `tool_start`/`tool_end`. Bridge-reported tool activity for
   pi's built-in tools is *display-only* provenance (pi's `--mode
   json` execution is already the audited path via the bridge log
   and the turn's final accounting); events mediated by Python's
   `on_tool_call` continue to carry classification/decision fields.

### 2.4 Client (`payload/agent/templates/index.html`)

1. **Streaming send path.** Extend `uzSendPrompt()`:
   - `POST /api/message` with `stream: true`; on `{turn_id}`, set
     `conversationId` if returned, replace the "thinking" bubble
     with an empty in-progress assistant bubble plus a one-line
     live status row, and open
     `new EventSource("/api/stream/" + turnId)`.
   - `token` events append the delta as **plain text** (via
     `textContent`, preserving escape-first safety) into the
     in-progress bubble; on `turn_done` the bubble is re-rendered
     once through the existing `renderMarkdown()` so the final
     display is identical to a non-streamed reply.
   - `tool_start`/`tool_end`/`pending_approval`/`phase` update the
     status row ("running `svc.status`…") and append the same event
     rows `renderEvent()` already draws on conversation reload, so
     streamed and reloaded transcripts look the same.
   - `turn_done` carries the synchronous payload: run the exact
     post-processing the fetch path runs today (tombstone check,
     `conversation_id`, error/reply rendering, event rows, turn
     counter), close the `EventSource`, `setBusy(false)`.
2. **Fallback, never a regression.** If the `POST` response has no
   `turn_id` (older server, error), or `EventSource` errors before
   `turn_done`, or `turn_error` arrives with no persisted reply:
   close the stream and fall back to a single
   `GET /api/conversation/{id}` reload (the "poll-once" behaviour)
   so the chat never ends below today's baseline. A
   `window.EventSource` feature check guards ancient browsers by
   simply using today's synchronous `fetch` path.
3. **Timeouts and Stop.** Keep `CLIENT_TURN_TIMEOUT_MS` as the
   outer deadline, rearmed on every received SSE event (an *idle*
   deadline, mirroring the server watchdog). The Stop button closes
   the `EventSource` and shows today's "the agent may still finish
   in the background" notice — closing the stream must not kill the
   server-side turn.
4. **401/410 handling.** A 401 on the initial POST behaves as
   today (`showLogin`); a `turn_error` with `dead: true` routes to
   `showTombstone`.

### 2.5 Policy, audit, security posture

- **No new privileged behaviour.** The stream is a read-only view
  over events the policy gate and audit log already produce; no new
  tool, no new classification, no `sudo`.
- The SSE endpoint sits behind the same session gate as
  `/api/message` (`_guard()`); it is *not* added to
  `_PUBLIC_PATHS`. The server still binds `127.0.0.1` only.
- Token deltas are model output, the same text that lands in
  history today — no new data class crosses the boundary. When
  Phase D2's outbound redaction lands, the flush boundaries in the
  bridge/`emit` path are the designated hook (noted here so A1's
  code leaves a single choke point: all SSE frames funnel through
  one `emit`/writer function).
- Bounded queue + single-stream rule mean a stuck browser cannot
  grow server memory without bound.

### 2.6 Tests

`tests/smoke.sh` additions (all runnable non-root, no `pi`
required):

- **python compile** already covers the new/changed modules.
- **standards** checks: `server.py` declares the `/api/stream`
  route; `index.html` references `EventSource` *and* the fallback
  reload path; `index.html` still contains no external
  `<script src=`/CDN reference; the bridge and `pi_mono.py`
  protocol doc blocks both mention `progress` and `token`.
- **stub-driven regression** (pattern of the existing
  `pi_mono.run_turn` stub test): extend
  `tests/fixtures/stub-pi-mono.mjs` to emit a `progress` pair and a
  couple of `token` events before `final`; assert via `python3 -c`
  that `run_turn(on_event=…)` invokes the callback in order and
  that the returned `final`/`events` are unchanged — proving old
  callers (no `on_event`) still work.
- **sync-path regression:** `post_message` without `stream` returns
  the same shape as today (guarding the fallback).

Manual VM checklist (documented, not automated): a long multi-tool
turn shows live tool lines; killing the stream mid-turn leaves
history intact and the reply appears on reload; a provider without
delta support still shows phase/tool events.

### 2.7 Docs

- `docs/ARCHITECTURE.md`: extend the chat-service section with the
  two-step turn protocol, the SSE event vocabulary, and the
  fallback guarantee.
- `docs/CONFIGURATION.md`: no new *required* env; document any
  tuning knob actually added (keepalive interval and queue bound
  should be constants, not env, unless implementation shows a need
  — prefer zero new configuration).
- `CHANGELOG.md` Unreleased entry + `VERSION` bump
  (`date -u +%Y.%m.%d.%H.%M.%S > VERSION`).

### 2.8 Acceptance

A turn that runs three tool calls shows at least three live status
updates before the final reply; with streaming unavailable (old
bridge, `EventSource` failure, `stream` flag omitted) the chat
behaves exactly as today.

---

## 3. A2 — never lose the operator's words

### 3.1 The actual bug

`index.html`'s submit handler begins
`if (sendBtn.disabled) return;` — while a turn is in flight
(`setBusy(true)`), pressing Enter discards the typed prompt with no
feedback. The textarea itself is never disabled, so the operator can
type freely and reasonably expects the message to go somewhere.

### 3.2 Design (client-only; `index.html` is the sole touch point)

1. **One-deep queue.** Module-level `queuedPrompt` (string or
   null) plus a reference to its "queued" bubble node.
2. **Submit handler rework.** When a turn is in flight and the
   input is *not* a slash command:
   - first submit: clear the textarea, render a visibly distinct
     "queued" bubble ("Queued — will be sent when the current turn
     finishes; a page refresh discards it."), store the prompt;
   - second submit: replace the queued prompt and update the bubble
     with an explicit notice that the previous queued message was
     replaced (the replaced text is shown so nothing vanishes
     silently).
   Slash commands keep executing immediately during a turn (they
   are client-side; this also preserves `/approve` and `/deny`
   mid-turn, which streaming's `pending_approval` makes more
   likely).
3. **Drain point.** In `uzSendPrompt`'s `finally` block (which both
   the streaming and fallback paths funnel through), after
   `setBusy(false)`: if `queuedPrompt` is set, remove the queued
   bubble, clear the variable, and call `uzSendPrompt(queued)`
   asynchronously. Draining from `finally` means errored/aborted
   turns also release the queue rather than stranding it.
4. **Cancel affordance.** The queued bubble includes a small
   "discard" control; Stop does not clear the queue (stopping the
   current turn and abandoning the next message are different
   intents).
5. **No persistence, by design.** Refresh drops the queue and the
   bubble text says so. No server change, no storage, no multi-item
   queue — one slot, per the parent plan.

### 3.3 Tests and docs

- Not smoke-automatable (browser behaviour); add a **standards**
  grep only if cheap (e.g. `index.html` contains the queued-bubble
  marker class) — optional, low value.
- Document the behaviour in the chat section of `README.md` /
  `docs/CHAT.md` (whichever holds chat usage by then) and in the
  client-side `/help` output (a "Queued messages" line under a
  general-behaviour note).
- `CHANGELOG.md` entry (may share the Phase A entry with A1).

### 3.4 Acceptance

Submit during a running turn → message visibly queued → auto-sent
at turn end; a second submit mid-turn replaces the queued item with
an explicit notice; nothing is ever dropped without a visible trace.

---

## 4. Sequencing and deliverables

A2 is independent of A1 and much smaller; land it first for an
immediate win and to exercise the submit-handler seam A1's client
work also touches.

| Step | Deliverable | Files | Gate |
|------|-------------|-------|------|
| 1 | A2 queued-input fix | `payload/agent/templates/index.html`, chat docs, `/help` | `make lint`, `make test`, manual browser check |
| 2 | Bridge `progress`/`token` events + protocol docs | `payload/agent/pi-mono-bridge.mjs`, `payload/agent/pi_mono.py` (doc block) | `make lint`, `make test` (python compile; bridge behaviour covered by step 3's stub regression) |
| 3 | `run_turn(on_event=…)` + stub-bridge regression | `payload/agent/pi_mono.py`, `tests/fixtures/stub-pi-mono.mjs`, `tests/smoke.sh` | `make test` |
| 4 | Turn registry, `stream: true`, `GET /api/stream/{id}`, `emit` wiring | `payload/agent/server.py`, `tests/smoke.sh` (standards + sync regression) | `make lint`, `make test` |
| 5 | Client `EventSource` path + fallback | `payload/agent/templates/index.html`, `tests/smoke.sh` standards | `make lint`, `make test`, manual VM checklist |
| 6 | Docs + release hygiene | `docs/ARCHITECTURE.md`, `docs/CONFIGURATION.md`, `CHANGELOG.md`, `VERSION` | phase-boundary `make lint` + `make test` |

Each step is independently revertable; steps 2–3 change nothing
observable until step 4 consumes them, and step 4 changes nothing
for clients that do not send `stream: true` until step 5 ships.

## 5. Risks and mitigations

- **Thread-safety of History/SQLite from the worker thread.** The
  turn now runs off the request thread. `History` is already called
  from multiple request threads (`ThreadingHTTPServer`), but verify
  its connection handling (per-call connections or a lock) before
  step 4; if it relies on request-thread serialisation anywhere,
  guard the worker with the same `App._lock` discipline.
- **Two writers to `pending`.** Approvals (`/api/approve`) already
  run on a different thread than the turn; the existing
  `self._lock` usage covers the new arrangement — re-read it during
  step 4 rather than assuming.
- **Bridge flooding.** Token deltas are coalesced in the bridge and
  the server queue drops oldest `token` events on overflow;
  phase/tool events are small and bounded by the per-turn tool-call
  budgets.
- **Silent divergence between streamed and stored transcript.** The
  `turn_done` payload is the synchronous payload, and the client
  re-renders the final bubble from it — the stream is cosmetic; the
  store stays authoritative.
- **Scope creep toward WebSockets/chunked JSON.** Out of scope:
  SSE only, one direction, stdlib `http.server` — no new
  dependencies anywhere in this phase.
