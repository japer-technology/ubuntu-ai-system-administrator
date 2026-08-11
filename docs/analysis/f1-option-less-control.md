# F1 option report — LESS control: accept the unmediated architecture,
# make every claim true, and add compensating controls

Companion to [`improvements-8.md`](improvements-8.md) finding F1.
This report covers the **other** legitimate resolution: keep pi's
built-in tools executing in-process (the architecture pi is designed
for), stop claiming mediation that does not exist, and harden the
controls that remain. The mediation-restoring alternative is
[`f1-option-more-control.md`](f1-option-more-control.md).

## 1. The decision being made

Under this option the trust model becomes, in one honest sentence:

> The chat **is** a root shell with an LLM typing. The boundary is the
> loopback surface, the password, and the TTL — nothing downstream of
> the model gates anything.

That is a defensible product (it is the OpenClaw/pi model: a capable
agent on a machine you own, behind a door only the operator opens).
What is not defensible is the current state: shipping that
architecture while the docs, the promotion tree, and `AGENTS.md`
describe a gate that never fires. This report's job is to close that
honesty gap and raise the floor of the controls that remain.

## 2. What must change, file by file

### 2.1 `SECURITY.md` — remove the gate as a mitigation

- `:95-98` — "Passwordless sudo … Mitigated by the loopback-only chat
  surface, the chat-UI password gate, **the policy gate**, and audit
  logging." → delete the policy gate from the mitigation list; the
  mitigations are the loopback surface, the password, and the TTL.
- `:105-107` — "The provider's output is executed only through the
  approval gate; review proposed commands before approving." →
  **false; rewrite**: the provider's output executes directly through
  pi's built-in tools as a passwordless-sudo user. The operative
  guidance becomes: prompt injection in any content the agent reads
  (files, logs, command output, fetched pages) can drive root actions;
  do not point the agent at untrusted content; use `/verbose on` to
  watch tool activity live.
- `:111-115` — audit section claims the log records "proposed
  actions, approvals". No approvals exist. Correct the description to
  what is actually recorded (prompts, plus whatever the bridge log
  captures — see 3.2).

### 2.2 `docs/ARCHITECTURE.md`

- `:6` ("runs everything behind a local policy gate"), `:52`
  ("Elevated actions require the configured approval path before
  running"), `:55` ("The policy gate …"), `:75` (`pending_approval`
  state) — all describe the unshipped path. Mark the
  registry/gate/approval layer as **present but not wired to the pi
  agent loop**, with a pointer to
  [`f1-option-more-control.md`](f1-option-more-control.md) if it is
  ever restored.

### 2.3 `README.md`

- `:26` — "see exactly what is proposed, **approve it**, and watch it
  happen." → remove the approval promise; replace with the live
  visibility story (`/verbose` streams every tool execution with
  args, outcome, timing).

### 2.4 Promotion tree (claims matrix)

- `promotion/messaging/KEY-FEATURES.md:17` — the policy-gate/approval
  row is an unapproved claim; delete or reword to the verbose
  observability story. `:18` and `:40` overstate the audit log's
  content (no approvals, no per-command policy records).
- `promotion/messaging/ELEVATOR-PITCH.md:9,21,37` — "you approve, and
  it acts", "wait for your approval", "the operator approves them
  before they run" — all three reworded.
- The claims matrix exists precisely to prevent this; F1 is the case
  where it matters.

### 2.5 `AGENTS.md` rule 3

"Any new privileged behaviour must go through `policy.py` and be
recorded by `audit.py`" is currently unimplementable on the agent
path. Annotate: the rule binds the **registry** path; the shipped pi
loop is exempt until mediation is restored, and contributors must not
add claims to the contrary.

### 2.6 `CHANGELOG.md`

The Unreleased entry "**Fail-closed policy restored**" is true of
`policy.yaml` semantics but reads as if the gate guards the agent.
Add one clause: "(the policy gate classifies registry-path calls; the
shipped pi agent loop does not currently route through it — see
docs/analysis/f1-option-less-control.md)". Same for the 1,000-call
budget entry, which implies enforcement.

## 3. Compensating controls (no mediation required)

Ranked by value per effort.

### 3.1 Make authentication load-bearing (from F3 — now the only gate)

With no downstream gate, the password is the **entire** boundary:
- fail closed when `ZOMBIE_ADMIN_PASSWORD_HASH` is unset
  (`payload/agent/auth.py:69-79`);
- refuse the default `braaaains` in interactive and
  `ZOMBIE_NONINTERACTIVE=1` installs (exit 64);
- exponential backoff + lockout in `login()`
  (`payload/agent/server.py:442-451`).

### 3.2 Make observability the audit substitute

The bridge already sees every tool execution and writes
`pi-mono.*.log`; `/verbose` streams them with args, outcome, timing,
output size, exit codes. Under this option that stream **is** the
audit trail, so:
- always write the bridge tool log (not gated on UI verbose mode),
  under logrotate with the audit log;
- route tool events through `audit.py`'s redaction before writing —
  today the bridge log bypasses the redaction layer;
- add a `/audit` view over the bridge logs alongside `audit-recent`.

### 3.3 Shrink the blast radius

- Replace `NOPASSWD:ALL` (`scripts/install.sh:3093`) with a scoped
  sudoers allow-list (systemctl, apt, journalctl, the operator helpers)
  — pragmatic version: keep `NOPASSWD:ALL` but document it as a
  deliberate "the agent is root" posture rather than a mitigated risk.
- Add a wall-clock turn ceiling (F7): with no call budget enforcement,
  time is the only bound on a looping agent.
- Confirm the lifecycle tombstone is at least operator-visible
  (`/ttl`), accepting F4's residual as documented.

### 3.4 Supply-chain floor (unchanged by this option, still required)

Wire `verify-release` into the documented install flow; pin the
unpinned npm tools (F9); the provider key remains inheritable by every
child the agent spawns — document rather than fix under this option.

## 4. What is permanently given up (sign here)

- No operator approval before any action, however destructive.
- No policy classification; `policy.py`, `tools.py`'s allow-lists, and
  the budgets remain registry-path-only code.
- No per-command records in `audit.log`; forensics depend on the
  bridge tool log (3.2) surviving the agent — and the agent is root,
  so a sufficiently steered agent can alter its own logs. If that
  residual is unacceptable, this option is the wrong choice.
- Prompt-injection-to-root is an accepted, documented risk.

## 5. Effort and sequencing

1. Auth hardening (3.1) — half day, do first: it is the boundary.
2. Doc sweep (section 2) — one focused PR; every file listed above is
   a small, exact edit.
3. Bridge-log-as-audit (3.2) — redaction routing + logrotate + view.
4. Turn ceiling + sudoers decision (3.3).
5. Re-release with the changelog annotation (2.6).

Total: roughly two to three days, no new runtime components, no pi
behaviour risk. The product keeps its current capability and gains an
honest perimeter.

## 6. The fork in the road, stated plainly

| | More control (A) | Less control (B) |
|---|---|---|
| Approvals before destructive actions | yes | never |
| Per-command policy/audit | yes | bridge log only |
| Injection-to-root | gated | accepted risk |
| Effort | ~1-2 weeks incl. tests | ~2-3 days |
| Depends on pi hook semantics | yes (spike first) | no |
| Docs changes needed | small (claims become true) | this report |

The two options share one requirement: **the current doc claims are
wrong today under either choice.** Section 2 of this report is the
mandatory common subset and should land regardless of which way F1 is
ultimately resolved.
