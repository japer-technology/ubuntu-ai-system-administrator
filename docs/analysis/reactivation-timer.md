# Analysis — timer primitive and agent re-activation requests

Date: 2026-07-21

This note analyzes a proposed mechanism that lets the AI Agent ask the
chat system to re-activate it later instead of ending a task at the hard
boundary of the current model turn. The motivating example is a request
whose useful answer cannot fit in one turn, such as "write a 100,000 word
essay about why the sky is blue." Rather than pretending the response is
complete, the agent should be able to schedule a non-terminal continuation
that the local chat daemon later injects back into the same conversation.

Implementation status: shipped. The runtime follows this design with one
global pending timer, durable SQLite settings, authenticated UI visibility and
cancellation, policy and audit mediation, and ordinary same-conversation turns.

## Problem statement

Ubuntu Zombie currently models chat as explicit operator turns. A browser
posts a user message, the server starts one model turn, tools may run
inside that turn, and the final assistant message terminates that cycle.
That shape is simple and auditable, but it forces every long-running or
multi-part task to either:

- finish prematurely;
- ask the human to manually send "continue"; or
- hide continuation state in prose that the system treats as ordinary
  assistant text.

The requested feature is a first-class escape hatch from that turn-based
constraint: the agent can emit a structured re-activation request as part
of its output. The system parses that request as a scheduled task, stores
at most one pending continuation, and later re-enters the chat with an
automatic queued request. When the queued request is sent to chat, the
pending re-activation record is cleared.

## Desired semantics

A correct design should provide these semantics:

1. **Structured, non-terminal request.** Re-activation is not inferred from
   prose such as "I will continue later." It is emitted through an explicit
   primitive in the agent capability set.
2. **Timer capability.** The agent receives a new primitive capability,
   `timer`, whose first use case is a `reactivation` operation. The name
   may be exposed as `timer.reactivation` in the closed registry or as a
   narrower `reactivation` tool backed by the timer subsystem; either way
   it is not a shell command.
3. **Single pending continuation.** Only one pending re-activation may
   exist per conversation, and likely per chat service instance. A new
   request replaces, updates, or rejects the existing one according to an
   explicit policy; silent accumulation is forbidden.
4. **Clear-on-fire.** The pending record is deleted before or atomically
   with injecting the automatic continuation into chat. If the daemon or
   provider fails after injection, the record must not loop forever unless
   the agent schedules a new one.
5. **Same conversation.** The continuation belongs to the conversation that
   scheduled it, preserving history, summaries, tool events, and audit
   context.
6. **Visible to the operator.** The UI should show that a continuation is
   queued, who scheduled it, when it will fire, and what prompt will be
   inserted. The automatic request should look like a system-generated
   queued user request rather than an invisible daemon action.
7. **Policy and audit coverage.** Scheduling, replacing, firing, clearing,
   and cancelling a re-activation are auditable events. The timer primitive
   should be policy-classified even if it is normally auto-approved.
8. **No privilege bypass.** Re-activation must only start another ordinary
   chat turn. It must not execute tools directly, bypass approval, bypass
   TTL, bypass authentication boundaries, or grant extra per-turn budgets.

## Proposed model

Treat re-activation as a durable pending chat request owned by the server,
not as text owned by the assistant message.

A minimal record would contain:

- a stable `id`;
- `conversation_id`;
- `created_at` and `fire_at` timestamps;
- the assistant turn or message that scheduled it;
- a short reason visible to the operator;
- the continuation prompt to inject;
- status fields such as `pending`, `firing`, `fired`, `cancelled`, or
  `failed`;
- optional retry metadata for daemon-level delivery errors, not model
  task continuation.

The agent-facing primitive should accept bounded fields, for example:

- delay or absolute time, clamped to a configured range;
- continuation prompt, capped to a small size;
- reason or title, capped to a smaller size;
- optional replace behavior: `replace_existing: true|false`.

The primitive returns a normal tool result telling the model whether the
request was accepted, replaced, rejected because one is already pending, or
rejected by policy. The final assistant response can then truthfully say
that a continuation has been scheduled.

## Timer versus reactivation naming

The problem statement asks for a new primitive capability set `timer` and
also names a `reactivation` tool. The clean split is:

- `timer` is the capability family: server-owned delayed work that never
  executes arbitrary shell or privileged code.
- `timer.reactivation` is the first concrete operation: schedule a future
  chat turn in the current conversation.

If the current bridge or model UI cannot present dotted tool names well,
`reactivation` can be a compatibility alias, but it should still dispatch
to the timer subsystem internally. That keeps future timer operations,
such as reminders or deadline cancellation, from being confused with
continuation-specific behavior.

## Background chat daemon

The daemon can be a thread inside `server.py` or a small companion process
managed by the same chat service unit. A thread is simpler and preserves
single-process access to in-memory locks, but a companion process can keep
scheduler code isolated. Either form needs the same contract:

1. Load the one pending re-activation record on startup.
2. Sleep until `fire_at`, with jitter or a short polling interval.
3. Re-check TTL, conversation existence, and pending status under a lock.
4. Atomically clear or mark the record as `firing` so only one daemon loop
   can consume it.
5. Insert a synthetic queued request into the conversation, such as:
   "Continue the prior task from the scheduled re-activation request."
6. Start a normal chat turn using the same path as `POST /api/message`, but
   with metadata marking the user message as `auto_reactivation`.
7. Audit the fire and final outcome.

The injected request should be represented in history as a user-role
message with metadata rather than as an assistant message. That makes the
conversation understandable: the assistant scheduled work, the system
queued a follow-up request, and the assistant answered it in the next turn.
The UI can render the synthetic user message with a distinct badge such as
"queued by timer" so it does not look like the human typed it.

## Storage options

There are two natural storage choices.

Default recommendation: add a table to `conversations.db` for the first
implementation. Re-activation is conversation-scoped, and SQLite gives the
server one transactional place to clear the pending record and insert the
synthetic queued user request.

### Add a table to `conversations.db`

The existing SQLite history database already stores conversations,
messages, and structured events. Adding a `reactivations` table keeps the
feature close to chat history and makes it easy to display pending state in
conversation APIs.

Recommended if re-activation is conversation-scoped.

### Add a separate state file

A JSON file under `/opt/ai-zombie/state/` would be easy to inspect and
repair manually, but it would duplicate locking, migration, and consistency
logic already handled by SQLite. It also makes atomic clear-and-inject
harder because the scheduled record and message history live in different
stores.

Recommended only if the timer subsystem is expected to become independent
of chat history.

## Single-pending policy

The statement says only one pending re-activation can be stored at any
time. The safest interpretation is one pending record per conversation and
one daemon-visible global due item at a time. A stricter global singleton
is easier to reason about but can surprise users who have multiple active
conversations.

Whichever scope is chosen, the tool result must be explicit:

- `accepted` when no pending record existed;
- `replaced` when the caller requested replacement and policy allows it;
- `rejected_pending_exists` when a pending record exists and replacement
  was not requested or not allowed;
- `rejected_policy` for schedule bounds, TTL, or capability denial.

The UI should also expose a cancel action. Human cancellation should always
win over an agent's scheduled continuation.

## Policy class

`timer.reactivation` does not mutate the host OS, but it does spend model
budget, can create unattended follow-up activity, and can annoy or confuse
the operator if abused. It should therefore not be treated as ordinary
`read_only` inspection.

A new policy class such as `chat_schedule` would make the distinction
clear. A conservative default could auto-approve short, bounded
continuations but require approval for long delays, immediate loops, or
replacement of an existing pending request. If adding a new class is too
large for the first implementation, classify it as `user_change` and add a
specific rule documenting why it can auto-run.

Important constraints:

- minimum delay, such as 5-30 seconds, to prevent tight self-loops;
- maximum delay, such as 24 hours or the remaining TTL, whichever is
  smaller;
- maximum continuation prompt size;
- maximum automatic re-activation chain length per root human request;
- no inherited approval from the prior turn;
- no direct tool execution at fire time.

## Audit and history events

At minimum, audit these events:

- `reactivation_scheduled` with conversation id, fire time, reason, and a
  redacted prompt summary;
- `reactivation_replaced` or `reactivation_rejected`;
- `reactivation_cancelled` with actor `operator`, `agent`, or `system`;
- `reactivation_fired` when the queued chat request is inserted;
- `reactivation_failed` if the daemon could not start the follow-up turn.

History should also store display events so the browser can show the
queued state without scraping audit logs.

## UI behavior

A clear UI model is essential because invisible self-activation would feel
surprising for an operator-owned root-capable assistant.

Recommended UI elements:

- a pending continuation banner in the active conversation;
- fire time, reason, and a short prompt preview;
- cancel and possibly "run now" controls;
- a distinct synthetic user bubble when the timer fires;
- a visible assistant note when a continuation was accepted or rejected.

The problem statement's idea of a runtime-inserted queued request maps
well to this model: the UI should present the fired record as a queued
request inserted by the agent runtime, not as a hidden background process.

## Failure modes and safeguards

The design must avoid these failure modes:

- **Infinite continuation loops.** Mitigate with minimum delay, max chain
  length, and clear-on-fire semantics.
- **Silent background autonomy.** Mitigate with visible banners, synthetic
  messages, cancellation, and audit entries.
- **Prompt injection persistence.** A malicious file could convince the
  model to schedule follow-ups. Treat scheduling as policy-controlled and
  bounded; consider requiring approval if the prompt references privileged
  work.
- **Duplicate fires after restart.** Use SQLite transactions or a compare-
  and-set status transition from `pending` to `firing`.
- **Bypassing per-turn budgets.** Each fired continuation starts a new
  ordinary turn with fresh per-turn budgets, but chain-level limits should
  bound aggregate work caused by one human request.
- **TTL bypass.** The daemon must refuse to fire after tombstone or after
  the remaining TTL can no longer cover the requested delay.

## Implementation outline

A future implementation should land in small phases:

1. Define the timer primitive schema, naming, policy classification, and
   audit vocabulary.
2. Add durable pending re-activation storage with a migration and helper
   methods for set, replace, clear, cancel, and fetch.
3. Register `timer.reactivation` in the closed tool registry and dispatch
   it through the same schema, policy, budget, and audit path as other
   tools.
4. Add the background daemon loop that consumes the pending record and
   injects a synthetic queued user request into the normal chat turn path.
5. Update the browser APIs and templates to display pending state,
   cancellation, and fired synthetic messages.
6. Add smoke tests for single-pending behavior, clear-on-fire, restart
   recovery, policy rejection, and prevention of immediate self-looping.
7. Document operator-facing behavior in the configuration and architecture
   docs once the implementation exists.

## Recommendation

Proceed with `timer.reactivation` as a first-class, policy-mediated tool
rather than parsing assistant prose. Store the pending record in the chat
SQLite database, display it prominently in the UI, and have a background
chat daemon convert it into a synthetic queued user request that follows
the existing message path. Enforce one pending record, clear it when it is
fired, and require the agent to schedule another continuation only if more
work genuinely remains.
