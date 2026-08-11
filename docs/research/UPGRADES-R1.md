# Upgrades, Round One

Candidate enhancements to make the Ubuntu Zombie chat more powerful —
more reach, more autonomy, better situational awareness, and a better
operator experience — **without** weakening the security model. Every
proposal below is scoped to fit the existing trust boundaries: a closed
tool registry, a policy gate before `sudo`, loopback-only binding, and
an audit record of every action.

This is a backlog of ideas, not a committed roadmap. Each entry states
*what* the feature is and the *case for* it.

## Where the chat stands today

The chat already does a great deal. A loopback HTTP server forwards
prompts to the pi-mono agent loop, mediated by a **closed tool
registry** (`shell.run`, `fs.*`, `pkg.*`, `svc.*`, `net.status`,
`gui.*`, `skill.*`), gated by a **policy classifier** with an approval
queue, persisted to SQLite, fully **audit-logged**, with runtime
model/provider switching and a rich set of client-side slash commands.

"More powerful" therefore means widening reach and autonomy while
keeping the controls that make the system trustworthy.

---

## 1. Real-time streaming and turn transparency

### Stream tokens and events to the UI
**Feature.** Stream the agent's output to the browser as it is produced
(SSE or chunked response on `/api/message`) instead of waiting for the
final reply. The bridge already emits `message_update`/`text_delta`
events; the server just needs to forward them.

**Case for.** Long turns currently feel like a black box. Streaming
makes the chat feel responsive and lets the operator judge whether the
agent is on the right track — and hit Stop early — instead of waiting
blind.

### Live tool-call timeline
**Feature.** Render each tool call, its policy classification, and its
result inline as it happens, not only in the final transcript.

**Case for.** The structured events are already persisted; surfacing
them live turns the chat into an observable operations console and makes
approvals easier to reason about in context.

### Token and cost meter
**Feature.** Show token usage and estimated cost per turn and per
conversation, using the usage data the provider returns.

**Case for.** Operators running hosted models want to see spend before
it surprises them, and the meter doubles as a signal that a turn has
gone off the rails.

---

## 2. Broaden capability while keeping the closed surface

### More first-class tools
**Feature.** Add structured tools instead of funnelling everything
through `shell.run`: for example `journald.query` (structured log
search), `proc.list`/`proc.signal`, `user.manage`, `timer.manage`
(cron/systemd timers), `disk.usage`, `apt.upgrade` with a changelog
preview, `firewall.rule` (ufw), and `tailscale.status`/`up`. Each new
tool ships with its own schema and classification.

**Case for.** First-class tools are easier for the policy gate to
classify precisely, easier to audit, and safer than free-form shell.
Adding one deliberately requires a code release — that friction *is* the
control point.

### Diagnostics bundles as tools
**Feature.** Expose the existing `collect-diagnostics` and
`health-check` helpers as callable tools.

**Case for.** Lets the agent self-diagnose *before* proposing a fix,
producing better-grounded suggestions and spending less tool budget
re-discovering the machine's state each turn.

### Policy-driven path allow-lists
**Feature.** Make the read/write path allow-lists in `tools.py`
configurable through policy instead of hard-coded, so operators can
widen or narrow file access without a code change.

**Case for.** Different machines have different sensitive paths.
Operator-tunable scope keeps the default tight while letting power users
extend reach safely and auditably.

---

## 3. Stronger autonomy with safety rails

### Plan-then-execute mode
**Feature.** Have the agent produce a numbered plan, let the operator
approve the *whole plan* once, then execute the steps with per-step
audit.

**Case for.** Reduces approval fatigue on multi-step jobs while keeping
a clear human checkpoint and a complete record of what was agreed before
anything ran.

### Batch approvals and trust profiles
**Feature.** Offer "approve all read-only in this turn" and selectable
policy **trust profiles** (e.g. relaxed for `user_change`, strict for
`destructive`) per session.

**Case for.** Most friction comes from approving obviously safe actions
one at a time. Profiles let the operator dial autonomy up or down to
match the task and their confidence.

### Dry-run / simulation for destructive tools
**Feature.** Where the underlying command supports it (`apt
--simulate`, `ufw --dry-run`), show the simulated result before the
confirmation phrase.

**Case for.** Lets the operator see the blast radius of a destructive
change before committing to it — turning the confirmation step into an
informed decision rather than a leap of faith.

### Rollback hooks
**Feature.** Snapshot affected config files before a `system_change`,
and offer a one-click revert tool.

**Case for.** Self-administration is only safe if it is reversible.
Automatic before-snapshots make "undo the last change" a real,
auditable operation.

---

## 4. Memory and context

### Curated machine-facts memory
**Feature.** An operator-visible, editable store of durable machine
facts (hardware, installed stack, prior decisions) injected into the
system prompt — distinct from the raw transcript history, and audited
when changed.

**Case for.** The agent re-learns the same machine every conversation.
A curated memory makes answers consistent and saves tool budget, while
staying transparent and under operator control.

### Automatic context gathering
**Feature.** Before answering a host question, pull a small, cached
system snapshot (OS version, failed units, disk pressure) into context.

**Case for.** Grounds answers in the machine's actual state without the
model spending a tool call every turn to rediscover it.

### Conversation search
**Feature.** Full-text search across the SQLite conversation history,
exposed as a slash command and an API endpoint.

**Case for.** Operators want to find "what did we change last week?"
without scrolling. The history is already stored; this makes it usable.

---

## 5. Multi-step reliability

### Resumable turns / checkpointing
**Feature.** When the turn watchdog kills a wedged bridge
(`max_turn_seconds`), let the operator resume from the last completed
tool rather than restarting the whole turn.

**Case for.** Long admin jobs are expensive to repeat. Resuming
preserves progress and avoids re-running side effects that already
succeeded.

### Visible budgets and rate awareness
**Feature.** Surface per-conversation tool budgets and provider rate
limits in the UI.

**Case for.** When the agent stops, the operator should see *why* —
budget exhausted, rate-limited, or finished — instead of guessing.

### Scheduled / recurring tasks
**Feature.** Let the operator promote a successful chat action into a
systemd timer ("run this health check nightly"), with each run audited.

**Case for.** Turns one-off fixes into durable maintenance, extending
the AI administrator's usefulness beyond the moment of the conversation.

---

## 6. Operator experience

### More slash commands
**Feature.** Add commands such as `/diagnose`, `/snapshot`,
`/rollback`, `/plan`, `/cost`, `/skills`, `/policy` (show current
classification rules), and `/export` (save a transcript).

**Case for.** Slash commands are fast, discoverable, and run
client-side without spending a turn. They make common operations
one keystroke away.

### Notifications
**Feature.** Desktop, email, or webhook notification when a turn
finishes or an approval is waiting.

**Case for.** Operators often drive the chat over an SSH tunnel and step
away during long jobs. A notification means they do not have to babysit
the tab.

### Denser approval panel and attachments
**Feature.** Show the exact argv, classification, and a diff for file
writes in the approval panel; allow the operator to paste a log snippet
or upload a file into the writable `/tmp` allow-list for analysis.

**Case for.** Better approval detail means safer, faster decisions.
Attachments let the operator bring evidence (a failing log) straight
into the conversation.

---

## 7. Skills ecosystem

### More shipped skills
**Feature.** Ship skills beyond the current apt/docker/gui/systemd/
tailscale/ufw set — e.g. networking (netplan), storage (LVM/fstab),
backups, certificates, and user management.

**Case for.** Skills steer behaviour *without* expanding the
deliberately closed tool surface, so they are the safest way to make the
agent competent at more tasks.

### Skill metadata and previews
**Feature.** Richer skill front-matter to sharpen the server's
automatic skill selection, plus a `/skill <name>` preview command.

**Case for.** Better metadata means the right guidance loads at the
right time; previews let operators see what a skill will inject before
relying on it.

---

## 8. Observability and trust

### Audit viewer upgrades
**Feature.** Filter the audit panel by classification, conversation, or
tool, and render a "what changed on this machine" timeline derived from
`system_change`/`destructive` events.

**Case for.** A machine that administers itself must be easy to inspect.
A change timeline answers the most important operator question — "what
did it do?" — at a glance.

### Self-test in chat
**Feature.** A `/selftest` command that runs `verify`/`doctor` and
reports inline.

**Case for.** Confirms the system is healthy without leaving the chat,
shortening the loop between "something feels off" and a diagnosis.

### Provider fallback
**Feature.** If the active provider errors, optionally fail over to a
configured secondary — for example the discovered `lmstudio` local
model.

**Case for.** Keeps the chat available during provider outages or
offline, which matters most precisely when the operator needs to fix the
network.

---

## Recommended starting point

The highest-leverage, lowest-risk wins are:

1. **Streaming + live tool timeline** (section 1) — the biggest jump in
   perceived power for the least risk.
2. **Plan-then-approve + dry-run for destructive tools** (section 3) —
   more autonomy with stronger, clearer safety rails.
3. **A handful of structured tools** such as `journald.query`,
   `firewall.rule`, and `timer.manage` (section 2) — real new
   capability inside the closed-registry model.

All three stay firmly inside the existing closed-registry, policy-gate,
and audit-everything model, so they make the chat dramatically more
capable without moving the trust boundary.
