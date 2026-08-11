<!-- triggers: reactivation, reactivations, reactivate, continuation, continuations, follow-up, followup, wake, wake-up, defer, deferred, long-running -->
# Skill: agent reactivation and deferred continuations

This skill is loaded when the operator asks about continuing work
later, follow-ups, or the reactivation timer. Recurring host-level
jobs (cron, systemd timers) are the `scheduling` skill; reactivation
is the chat's own one-shot continuation mechanism.

Operating rules:

- Use `timer.reactivation` when work genuinely must continue beyond
  the current turn — a long multi-part task, waiting for a slow
  external process, or a check the operator asked to happen "in a
  bit". It schedules exactly one bounded, visible continuation in the
  current conversation and is `chat_schedule` class.
- One timer exists server-wide, across all conversations. Scheduling
  a new one requires `replace_existing` and silently retires the old
  request — so state what pending continuation (if any) is being
  replaced, not just what is being scheduled.
- Always give an honest `reason` and a specific `prompt`. Both are
  shown to the operator in the chat footer with the fire time and a
  Cancel button; a vague prompt like "continue" hides what the next
  turn will actually attempt.
- The `<beep-reactivation>` block may appear anywhere in the
  reply; it does not need to be the final text. The runtime removes all
  such blocks from the visible answer. If more than one appears, only
  the last request is activated, so make the final block authoritative.
- Emit valid JSON when possible. The parser also tolerates a surrounding
  JSON code fence, single-quoted strings, and trailing commas so minor
  formatting slips do not break a continuation.
- Delays are bounded (5 seconds minimum, 1 hour maximum by default,
  operator-tunable within those hard limits) and no timer may outlive
  the remaining TTL. If the work needs to resume further out than the
  maximum allows, say so and let the operator choose between raising
  the bound (`/reactivation maximum …`) and a host-level timer via the
  `scheduling` skill.
- A fired reactivation starts an ordinary turn: the injected message
  is visibly labelled, all policy and approval checks run fresh, and
  no approval carries over from the turn that scheduled it. Never
  schedule a continuation as a way to retry a denied action —
  the denial stands until the operator says otherwise.
- Chain long tasks transparently. When splitting work across
  continuations, each turn should report what was completed, what the
  next continuation will do, and roughly how many remain, so the
  operator can cancel a runaway chain early. Do not schedule
  open-ended "keep going" loops; give the chain a defined end.
- The operator owns the switch. `/reactivation off` disables the
  capability and cancels the pending timer; `/reactivation cancel`
  cancels without disabling. `/reactivation reset` restores the enabled
  5-second/1-hour defaults and clears queued, active, and stale status
  state while retaining history and audit evidence. If scheduling
  capability is off, report that and stop — do not look for another
  way to run later.
- Scheduling, replacement, cancellation, deferral, firing and failure
  are all audited, and the pending state is durable in the conversation
  database. When asked "is anything scheduled?", answer from
  `/reactivation` status rather than memory of the conversation; it
  also reports the last continuation's outcome, which is the first
  thing to check when a chain stopped earlier than expected.
- Do not use reactivation for recurring maintenance (backups,
  cleanups, health checks). Anything that should happen more than
  once belongs in a systemd timer or cron entry the operator can see
  with host tools — see the `scheduling` skill.
