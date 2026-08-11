# Implementation plan for improvements 8

Source analysis: [`improvements-8.md`](improvements-8.md) — external
adversarial review of 2026-07-21 against commit `5ad3d6e`.

This plan turns every finding (F1–F12) into a sequence of reviewable
changes. Each section states the goal, the concrete work items, the
acceptance criteria, and the tests that must land with the change.
Nothing in this file is implemented; it is a remediation plan for
owner decision and phased delivery.

## Constraints that apply to every phase

- Preserve installer idempotence and the `ZOMBIE_NONINTERACTIVE=1`
  path (missing required non-interactive input exits `64`).
- Every new privileged behaviour goes through
  `payload/agent/policy.py` and is recorded by
  `payload/agent/audit.py`.
- No new runtime dependencies beyond what the installer already
  installs; Python standard library and Bash are sufficient for all
  work below.
- `make lint` and `make test` must pass after every phase.
- Do not run mutating installer paths outside a disposable Ubuntu
  Desktop LTS VM.

## Sequencing

Delivery order follows the analysis's own recommendation, because the
later phases depend on the shape of the F1 fix:

| Phase | Findings | Theme |
| ----- | -------- | ----- |
| 1 | F1 | Restore real tool mediation |
| 2 | F2 | Make the test suite certify the production path |
| 3 | F3, F4 | Harden the controls guarding the surface |
| 4 | F7, F8 | Correctness of long turns and restarts |
| 5 | F5, F6, F9 | Structural and supply-chain hardening |
| 6 | F10, F11, F12 | Documentation and reference integrity |

Phase 6 is independent of the rest and can be delivered in parallel at
any time. Phases 3–5 each assume the mediation shape chosen in
phase 1, so they must not start until the F1 decision is made.

## Phase 1 — F1 (CRITICAL): restore mediation on the shipped bridge

Today `payload/agent/pi-mono-bridge.mjs` launches `pi --mode json`
with pi's real built-in tools, which pi executes in-process. The
bridge only logs `tool_execution_*` events; it never emits the
`tool_call` event that `payload/agent/pi_mono.py` mediates, so
`on_tool_call` in `payload/agent/server.py` (schema validation →
`policy.classify_tool` → approval queue → audit) never runs on the
production path. Budgets, allow-lists, the destructive-confirmation
phrase, and per-command audit records are all unenforced while the
agent account holds passwordless sudo.

### Decision to make first

Choose between the two remediation shapes from the analysis. Both
restore the invariant "every tool execution round-trips through
`on_tool_call`"; they differ in where tool execution lives.

**Option A (preferred): move the bridge to `--mode rpc`.**

- Rewrite the pi invocation in `pi-mono-bridge.mjs` to use pi's RPC
  protocol so every tool call arrives as an observable request that
  the bridge forwards to Python as a `tool_call` event and answers
  with Python's `tool_result`.
- Address the recorded "brittle" concern (`pi-mono-bridge.mjs:24-26`)
  by pinning behaviour to the locked bridge version in
  `bridge-dependencies.lock` and asserting that version at bridge
  startup, failing loudly on mismatch (this also serves F6).
- Map the closed registry in `payload/agent/tools.py` to the tool
  surface pi expects, so the model keeps usable read/edit/run tools
  while Python executes them.

**Option B (interim hard stop): `--no-builtin-tools` plus
extension-registered custom tools.**

- Run pi with `--no-builtin-tools` and register the Python-mediated
  registry tools as custom pi tools via a pi extension, so the model
  sees real tools that round-trip through Python. This avoids the
  historical "zero usable tools" regression recorded at
  `pi-mono-bridge.mjs:137-139`.

**Option C (until either lands): honest documentation.** If neither A
nor B can ship immediately, amend `README.md`, `SECURITY.md`, and
`promotion/messaging/KEY-FEATURES.md` to state plainly that the
shipped path executes tools unmediated, and stop claiming
gate/approval protection anywhere. This is not a fix; it is the
minimum honest posture while one is built, and it must land in the
same window the decision is made.

### Work items (assuming option A)

1. Confirm the RPC surface of the pinned pi version against the
   upstream documentation (`packages/coding-agent/docs/rpc.md`) and
   record the confirmed contract in a comment block at the top of the
   bridge, replacing the current "brittle" note.
2. Rework `pi-mono-bridge.mjs` to: start pi in RPC mode, translate
   each incoming tool request to a `{"type":"tool_call"}` line on
   stdout, block that call until Python replies with a
   `tool_result` line on stdin, and return the result to pi.
3. Extend `payload/agent/pi_mono.py` so `run_turn()` forwards
   `tool_result` responses back into the bridge (today the mediation
   plumbing exists but is only exercised by the stub).
4. Remove the log-only handling of `tool_execution_*` events, or keep
   it strictly as a tripwire: if such an event ever arrives without a
   preceding mediated `tool_call`, terminate the turn with an
   `unmediated tool execution` error and write an audit record.
5. Re-point the system prompt (`payload/agent/server.py:132-139`) away
   from encouraging direct sudo use; describe the approval gate to the
   model instead.
6. Update `docs/ARCHITECTURE.md` and `SECURITY.md` to describe the
   restored mediated path, and update `CHANGELOG.md`.

### Acceptance criteria

- A live turn driven through the real bridge produces, for every tool
  execution: a schema-validated `tool_call`, a policy classification,
  an audit record, and (for gated classes) an approval round-trip.
- `max_tool_calls`, the elevated-call budget, the
  destructive-confirmation phrase, and the `payload/agent/tools.py`
  path allow-lists are demonstrably enforced on the production path.
- The tripwire converts any unmediated execution into a loud turn
  failure rather than silence.

## Phase 2 — F2 (HIGH): test the production path, not the stub

The strongest assertions in `tests/smoke.sh` (schema rejection,
policy classification, approval queueing) run only against
`tests/fixtures/stub-pi-mono.mjs`, which emits `tool_call` events the
real bridge never produced.

### Work items

1. Add a smoke group that runs the **real** `pi-mono-bridge.mjs`
   against `tests/fixtures/fake-pi-json.mjs` (extended to speak the
   RPC contract chosen in phase 1) and asserts that every tool
   execution arrived through `on_tool_call` with a policy
   classification and an audit record.
2. Until phase 1 lands, ship the weaker form first: the same group
   asserts that any tool execution either (a) was mediated, or
   (b) fails the test with a loud "unmediated tool execution" error —
   making the current bypass a permanently red test instead of an
   invisible gap. Flip the assertion to require (a) unconditionally
   as part of the phase 1 change.
3. Keep the stub-based groups: they remain useful unit-level coverage
   of the Python mediation machinery. Add a comment in `tests/smoke.sh`
   stating explicitly which groups certify the production path and
   which certify the stub.

### Acceptance criteria

- CI cannot pass again with a bridge that executes tools without
  emitting mediated `tool_call` events.
- The real bridge and the fake pi binary are exercised together in
  every CI run.

## Phase 3a — F3 (HIGH): authentication fails closed, with throttling

`payload/agent/auth.py` allows every request when
`ZOMBIE_ADMIN_PASSWORD_HASH` is unset (`check_password` returns
`True` with no stored hash); the default password `braaaains` is a
public constant; and `payload/agent/server.py` logs failed logins but
never throttles them.

### Work items

1. **Fail closed.** Change `check_password()` /
   `auth_required()` semantics so that a missing hash refuses all
   chat requests, and have `server.py` serve a tombstone-style
   "authentication not configured" page in that state. Keep a single
   explicit test-only escape hatch if the smoke tests need one, named
   so it cannot be mistaken for a production setting.
2. **Refuse the default password.** In `scripts/install.sh`, reject
   the known default in both interactive and
   `ZOMBIE_NONINTERACTIVE=1` installs; in non-interactive mode exit
   `64`, matching existing missing-env behaviour. Update
   `docs/CONFIGURATION.md` and the quickstart accordingly.
3. **Throttle failures.** Add exponential backoff with lockout to
   `login()` (e.g. 5 failures → 60 s lock, doubling to a documented
   cap), keyed on the loopback session, with lockout events written
   to the audit log.
4. Extend `tests/smoke.sh`: unset-hash refusal, default-password
   rejection (both modes), lockout progression, and audit records for
   lockouts.

### Acceptance criteria

- With no configured hash, no chat or approval endpoint responds
  with anything but the not-configured page.
- A fresh install cannot complete with the default password.
- Brute-force attempts hit the documented lockout curve and are
  audited.

## Phase 3b — F4 (HIGH): TTL tombstone survives the agent it bounds

`/opt/ai-zombie/state/lifecycle.json` is owned by the agent account,
which (until F1 is fixed, unconditionally) holds passwordless sudo, so
the agent can rewrite or delete its own tombstone.

### Work items

1. Root-own the lifecycle state directory and file; the service reads
   it but cannot write it directly.
2. Route lifecycle writes through a minimal root-mediated helper (a
   small root-owned script invoked via a dedicated, narrowly scoped
   sudoers entry, or a tiny root sidecar unit) so the only path that
   can advance or reset TTL state is not the agent process itself.
3. On death, set the tombstone immutable (`chattr +i`) where the
   filesystem supports it; document the attribute and the
   unsupported-filesystem limitation in `docs/ARCHITECTURE.md`.
4. Teach `install.sh verify`/`doctor` to check ownership, mode, and
   (where applicable) the immutable attribute; teach `repair` to
   restore them. Keep all steps idempotent.
5. Note explicitly in the change description that this control is
   only meaningful once F1 restores mediation; with unmediated root
   it is defence-in-depth at best.

### Acceptance criteria

- The agent account cannot modify lifecycle state through any path
  that bypasses the root-mediated helper.
- A dead tombstone survives an agent-initiated delete/rewrite attempt.
- Verify/doctor/repair converge on the hardened layout.

## Phase 4a — F7 (MEDIUM): real turn ceilings

`DEFAULT_TURN_TIMEOUT` in `payload/agent/pi_mono.py` is 86,400 s and
every event resets the idle watchdog, so a fast tool-call loop never
trips it.

### Work items

1. Add a **wall-clock** turn ceiling in `pi_mono.py`, distinct from
   the idle watchdog, with a 30–60 minute default and a
   `ZOMBIE_PI_MONO_WALL_CLOCK` (name final at implementation) env
   override; on expiry terminate the turn with a clear error event
   and an audit record.
2. Lower the idle default from 24 h to an interactive-scale value
   (minutes), keeping `ZOMBIE_PI_MONO_TIMEOUT` as the override for
   operators who deliberately run long local-model turns.
3. Enforce the per-turn call budget in the bridge/mediator on the
   mediated path delivered by phase 1, so a loop exhausts its budget
   before either clock matters.
4. Update `payload/etc/policy.yaml` comments,
   `docs/CONFIGURATION.md`, and the smoke tests that assert the
   current capacity numbers (`tests/smoke.sh` pins per-turn capacity
   today, so those assertions must be updated in the same change).

### Acceptance criteria

- A turn that loops on fast tool calls stops at the call budget or
  the wall clock, whichever comes first, with an operator-visible
  error and an audit record.
- Both ceilings are operator-configurable and documented.

## Phase 4b — F8 (MEDIUM): durable approval state

Pending approvals live in an in-memory dict in
`payload/agent/server.py` while `pending_tool_call` history rows are
mirrored to SQLite; a restart strands rows that can never be approved.

### Work items

1. On server startup, scan history for `pending_tool_call` events
   without a terminal outcome and either:
   - rebuild the in-memory pending map from SQLite so the approvals
     remain actionable, **or**
   - expire each orphan to a terminal "abandoned (service restart)"
     state with matching audit and history events.
   Prefer expiry: approving a call whose originating turn is gone has
   no consumer for the result, so resurrection adds complexity with
   no benefit.
2. Make the expiry idempotent (safe on repeated restarts) and surface
   the abandoned state in the chat history UI the same way denials
   appear.
3. Add a smoke test: create a pending approval via the stub, restart
   the server process against the same SQLite file, and assert the
   orphan reaches the terminal state with audit coverage.

### Acceptance criteria

- No `pending_tool_call` row can remain actionable-looking but
  unactionable after a restart.
- Restart handling is idempotent and audited.

## Phase 5a — F5 (MEDIUM): decompose `server.py`

`payload/agent/server.py` (~2,000 lines) mixes HTTP handling, turn
orchestration, policy enforcement, approval state, provider probing,
discovery scanning, and prompt rendering; the `on_tool_call` closure
duplicates the audit/history/SSE emission triple across five exit
branches.

### Work items

1. Extract a `ToolMediator` class owning the per-call pipeline
   (schema validation → classification → approval → audit), shaped by
   whatever phase 1 delivered. This is deliberately sequenced after
   F1 because F1 changes what the mediator must be.
2. Extract an `AgentTurn` orchestrator owning turn lifecycle, and
   reduce the HTTP handlers to thin request/response adapters.
3. Introduce a single emission helper for the audit-event /
   history-event / SSE-event triple and use it at every exit branch.
4. Move in mechanical, behaviour-preserving steps (one extraction per
   commit) so review stays tractable; no functional changes ride
   along.

### Acceptance criteria

- `make test` passes unchanged at every intermediate step.
- The audit/history/SSE triple is emitted from exactly one place.
- No mediation semantics change (phase 2's production-path test group
  guards this).

## Phase 5b — F6 (MEDIUM): bridge schema and resolution hardening

Both bridges hand-parse pi's private `--mode json` event schema;
malformed lines are silently swallowed (`catch { return; }`), so
schema drift surfaces as an empty `final`. `pi-ai-bridge.mjs`
resolves `@earendil-works/pi-ai` by walking broad global module
directories, an import-hijack vector.

### Work items

1. Assert the pinned bridge/dependency version (from
   `bridge-dependencies.lock`) at bridge startup and fail loudly on
   mismatch. (Shared with phase 1 if option A is chosen; land once.)
2. Track whether any terminal event parsed successfully; when a turn
   ends with unparseable or absent terminal output, emit
   `{"type":"error"}` with a diagnostic instead of an empty `final`.
   Keep per-line tolerance for genuinely mixed output, but count and
   report swallowed lines in the error diagnostic.
3. In `pi-ai-bridge.mjs`, resolve the module from the single pinned
   install location only, and ignore any `NODE_PATH` inherited from
   the secrets env when spawning/resolving.
4. Extend `tests/smoke.sh` with fixture cases: version mismatch →
   startup failure; garbage terminal output → error event, not empty
   final; poisoned `NODE_PATH` → pinned resolution still wins.

### Acceptance criteria

- Upstream schema drift produces a visible error, never a silent
  empty answer.
- Module resolution cannot be redirected by environment or
  earlier-on-path writable directories.

## Phase 5c — F9 (MEDIUM): supply-chain gaps

### Work items

1. **Verified installs.** Document a `verify-release`-first install
   flow in `README.md`/`docs/`, and make `scripts/install.sh` refuse
   to install from a downloaded release artifact that has not passed
   `payload/bin/verify-release`, with an explicit opt-out flag for
   source checkouts and air-gapped hosts (documented, audited in the
   receipt).
2. **Pin npm tooling.** Replace `npm@latest` and the unpinned
   `yarn pnpm typescript ts-node` installs in `scripts/install.sh`
   with exact versions recorded alongside the bridge pins, and extend
   `scripts/verify-bridge-pins.sh` to verify them.
3. **Scrub provider keys from tool subprocesses.** Once phase 1
   restores mediation (the registry executes tools itself), strip the
   active provider key from the environment passed to spawned tool
   subprocesses; only the bridge process that talks to the provider
   keeps it.
4. **Append-only audit log.** Apply `chattr +a` to the audit log
   where the filesystem supports it (installer sets it, logrotate
   handling adjusted to clear/reapply around rotation); document the
   limitation on unsupporting filesystems in `SECURITY.md`. Remote
   shipping is recorded as a future option, not built now.

### Acceptance criteria

- A tampered release artifact cannot be installed without an explicit
  documented opt-out.
- `make lint`/CI fail if the npm tool pins drift from the lock.
- Tool subprocesses demonstrably lack provider keys (smoke-testable
  with the stub bridge printing its environment).
- Audit log rotation still works with the append-only attribute.

## Phase 6a — F10 (MEDIUM): make the changelog mechanical

`CHANGELOG.md` carries a ~970-line `## [Unreleased]` that never rolls
over, and `.github/workflows/release.yml` greps for a version section
that never matches, so releases ship fallback one-line notes.

### Work items

1. Teach the release workflow to promote `## [Unreleased]` to
   `## [<VERSION>] — <UTC date>` at tag time (the workflow already
   knows the version), committing the rollover back or embedding it
   in the release artifact per existing workflow conventions.
2. Backfill: roll the current oversized Unreleased block into a dated
   section at the next release so the ledger reflects reality.
3. Verify the workflow's release-notes extraction now matches the
   promoted section, and delete the dead fallback path or keep it as
   a guarded safety net with a comment.

### Acceptance criteria

- The next tagged release ships real notes extracted from the
  promoted section, and `## [Unreleased]` restarts empty.

## Phase 6b — F11 (MEDIUM): re-align the scope contract

`docs/VISION.md` still declares the one-sentence MVP and gates scope
on a `ROADMAP.md` that does not exist, while Forgejo, llama.cpp
serving, and the `options/` plans ship or are planned.

### Work items

1. Rewrite `docs/VISION.md` to describe the components-and-options
   reality: a core chat product plus explicitly gated optional
   components (`ZOMBIE_INSTALL_<COMPONENT>` flags, default off), with
   the `options/` library as the design funnel for future components.
2. Either restore a real `ROADMAP.md` as the scope gate for new
   options, or delete the dangling reference and name `options/` as
   the gate. Pick one; do not leave both.
3. Sweep other docs (`AGENTS.md`, `CONTRIBUTING.md`, `README.md`) for
   language that still implies the one-sentence MVP scope.

### Acceptance criteria

- No document references a scope gate that does not exist.
- In-scope/out-of-scope statements match what the installer actually
  offers.

## Phase 6c — F12 (LOW): reference-integrity sweep

One focused PR:

1. The stale `AGENTS.md` reported by the review lives in the owner's
   local checkout parent directory (`Documents/`, outside this
   repository) and cannot be fixed from this repo; record in the
   repo's `AGENTS.md` that no out-of-tree agent guidance is
   authoritative, and notify the owner to delete or update the
   external file.
2. Remove or repair the `docs/design-notes/` references in
   `AGENTS.md` and `docs/VISION.md` (the directory does not exist);
   either restore the directory or drop the references — do not leave
   the dangling paths.
3. Reconcile the policy draft filenames: update `CHANGELOG.md`
   references (`docs/policy-new.yaml`, `docs/policy-new-v2.yaml`) to
   the actual files (`docs/policy-new-v1-5.5-pro.yaml`,
   `docs/policy-new-v2-fable-5.yaml`, `docs/policy-old.yaml`), and
   add a header line to each draft stating it is a non-authoritative
   design draft, naming `payload/etc/policy.yaml` as the live policy
   (or delete drafts that no longer serve a purpose).
4. Update `docs/analysis/README.md` to index every file in the
   directory, including this plan.
5. Replace the blanket `CHANGELOG.md` exemption in
   `.github/workflows/ci.yml`'s secret scan with a placeholder
   allow-list (e.g. permit only the documented `sk-...`-style
   placeholder forms), so the highest-churn file is scanned again.

### Acceptance criteria

- Every path referenced from repo documents exists.
- Exactly one policy file is marked authoritative.
- The secret scan covers `CHANGELOG.md` while still allowing the
  documented placeholders.

## What this plan deliberately does not change

The analysis records genuinely strong areas (fail-closed policy
classifier, closed tool registry, PBKDF2 + constant-time comparison,
release engineering, component-registry installer design). This plan
builds on those mechanisms rather than replacing them: phase 1 routes
the production path back *into* the existing classifier, registry,
and audit machinery, which is already well tested in isolation.

## Definition of done for the whole pass

- All findings F1–F12 either closed by a landed change or explicitly
  declined by the owner with the decision recorded in
  `improvements-8.md` (status line updated per finding).
- `tests/smoke.sh` contains the production-path mediation group from
  phase 2, so the F1 class of gap cannot silently reopen.
- `SECURITY.md`, `README.md`, and promotion copy accurately describe
  the enforcement that actually ships at every intermediate point —
  including the interim window before phase 1 lands (F1 option C).
