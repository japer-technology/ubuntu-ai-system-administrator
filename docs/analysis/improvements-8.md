# Analysis pass 8 — external adversarial review (Spock/Hermes)

External review performed 2026-07-21 against commit `5ad3d6e` by three
independent reviewers (security, architecture/code-quality,
process/documentation), orchestrated by Spock (Hermes Agent) on behalf
of the repository owner. The two code reviewers converged independently
on finding F1 below; the headline claim was then verified directly
against the source before this file was written.

Structure follows the earlier passes: each finding lists evidence,
severity, a recommended solution, and a status. Nothing in this file
has been implemented; every entry is **proposed** for owner decision.

## F1 (CRITICAL) — Mediated tool path is dead code; the shipped bridge
## bypasses the policy gate, approval flow, and per-turn budgets

Evidence (verified directly):

- `payload/agent/pi-mono-bridge.mjs:246-270` spawns
  `pi --mode json -p` and pushes `--tools ${PI_BUILTIN_TOOLS}` — pi's
  real built-in tools (`read, bash, edit, write, grep, find, ls`),
  which pi executes **in-process**.
- `payload/agent/pi-mono-bridge.mjs:341-345` states the bypass
  explicitly: pi runs its own tools in this mode, "so we only *log*
  any `tool_execution_*` events rather than re-dispatching them
  through Python — re-dispatching would double-execute and the model
  would never see Python's result anyway."
- `payload/agent/pi_mono.py:313` mediates only `kind == "tool_call"`.
  The real bridge never emits that event type, so
  `payload/agent/server.py:736` (`on_tool_call`: schema validation →
  `policy.classify_tool` → approval queue → audit) is never invoked on
  the production path. It fires only under
  `tests/fixtures/stub-pi-mono.mjs`.
- `tests/fixtures/fake-pi-json.mjs:103-106` documents the bypass as
  intended behaviour for the real-bridge tests.
- Consequences: the `max_tool_calls` budget, the elevated-call budget,
  the destructive-confirmation phrase, the path allow-lists in
  `payload/agent/tools.py`, and per-command audit records are all
  unenforced. The model runs `bash` as a `NOPASSWD:ALL` user
  (`scripts/install.sh:3093`). Prompt injection in any file the agent
  reads becomes unmediated root.
- `SECURITY.md` claims output executes only through the approval gate;
  that is not true for the shipped path. The system prompt
  (`payload/agent/server.py:132-139`) further encourages sudo use.
- History: `pi-mono-bridge.mjs:137-139` records that
  `--no-builtin-tools` was tried and abandoned because the agent had
  zero usable tools and emitted tool-call-shaped text; `--mode rpc`
  was skipped as "brittle" (`:24-26`). The security model was traded
  for implementation convenience.

Recommended solution (in order of preference):

1. **Move the bridge to `--mode rpc`.** Round-trip every tool call
   through the existing `tool_call` / `tool_result` protocol so
   `on_tool_call` mediates each one. The RPC protocol is documented
   upstream (`packages/coding-agent/docs/rpc.md` in the pi repo). The
   brittleness noted at `pi-mono-bridge.mjs:24-26` should be addressed
   by pinning behaviour to the locked bridge version
   (`bridge-dependencies.lock`) and asserting the version at bridge
   startup, not by bypassing mediation.
2. **Interim hard stop:** run pi with `--no-builtin-tools` and expose
   only the closed registry. To avoid the "zero usable tools"
   regression, register Python-mediated tools as *custom* pi tools via
   an extension (pi supports extension-defined tools), so the model
   sees real tools that round-trip through Python.
3. **Until either lands:** state plainly in `README.md` and
   `SECURITY.md` that the shipped path is unmediated, and treat the
   chat as fully trusted operator-only (it is loopback + password, but
   see F4). Do not claim gate/approval protection in docs or promotion.

Status: **open — decision required.**

## F2 (HIGH) — Test suite certifies the stub path, not production

- `tests/smoke.sh` exercises mediation almost exclusively through
  `stub-pi-mono.mjs`, which emits `tool_call` events the real bridge
  never produces. The strongest assertions (schema rejection, policy
  classification, approval queueing) cover a path that does not run in
  production.

Recommended solution:

- Add one end-to-end smoke group that runs the **real**
  `pi-mono-bridge.mjs` against `fake-pi-json.mjs` and asserts that any
  tool execution either (a) arrived through `on_tool_call` with a
  policy classification and audit record, or (b) fails the test with a
  loud "unmediated tool execution" error. After F1 is fixed, flip the
  assertion to require (a) unconditionally.

Status: open.

## F3 (HIGH) — Authentication fails open; no login throttling

- `payload/agent/auth.py:69-79`: when `ZOMBIE_ADMIN_PASSWORD_HASH` is
  unset, every request is allowed. The one control guarding a
  root-capable chat fails open.
- `payload/agent/auth.py:27` + `scripts/install.sh:83`: default
  password `braaaains` is a public constant.
- `payload/agent/server.py:442-451`: failed logins are logged but
  never throttled, delayed, or locked out.

Recommended solution:

1. Fail closed: if no password hash is configured, refuse all chat
   requests with a tombstone-style "not configured" page.
2. Require a non-default password in both interactive and
   `ZOMBIE_NONINTERACTIVE=1` installs (exit 64 if the default is
   reused, matching existing missing-env behaviour).
3. Add exponential backoff + lockout (e.g. 5 failures → 60 s lock,
   doubling to a cap) in `login()`; log lockout events to the audit
   log.

Status: open.

## F4 (HIGH) — TTL tombstone is defeatable by the agent it bounds

- `payload/agent/lifecycle.py` state lives at
  `/opt/ai-zombie/state/lifecycle.json` (0600) owned by the agent
  account, which holds passwordless sudo. The agent (or an injection
  driving it) can rewrite/delete the tombstone or reinitialize TTL.

Recommended solution:

- Root-own the lifecycle state and the service unit's write path
  (agent reads via a root-mediated helper, or the service runs a tiny
  root sidecar for lifecycle writes), and/or set the tombstone file
  immutable (`chattr +i`) on death with the attribute documented in
  `docs/ARCHITECTURE.md`. Note this only matters after F1 is fixed;
  today the agent already has unmediated root regardless.

Status: open.

## F5 (MEDIUM) — `server.py` god-object and duplicated event triple

- `payload/agent/server.py` (2013 lines) is HTTP handler, agent-loop
  orchestrator, policy enforcer, approval state machine, provider
  probe, discovery scanner, and prompt renderer. The `on_tool_call`
  closure (`:736-893`) duplicates the audit-event / history-event /
  SSE-event triple across five exit branches.

Recommended solution:

- Extract `AgentTurn` (orchestration), `ToolMediator`
  (schema/policy/approval/audit per call), and thin HTTP handlers.
  Single helper for the audit/history/SSE emission. Do this **after**
  F1, since F1 changes what `ToolMediator` must be.

Status: open.

## F6 (MEDIUM) — Bridge schema fragility and error swallowing

- Both bridges hand-parse pi's private, evolving `--mode json` event
  schema, pinned to `0.80.10`. Malformed lines are swallowed
  (`pi-mono-bridge.mjs:374` `catch { return; }`), so upstream schema
  drift surfaces as an empty `final`, not an error.
- `pi-ai-bridge.mjs:220-242` resolves `@earendil-works/pi-ai` by
  walking broad global module dirs; a writable earlier entry (or
  poisoned `NODE_PATH`) is an import-hijack vector in agent context.

Recommended solution:

- Assert the bridge/dependency version at startup and fail loudly on
  mismatch; on any unparseable terminal sequence emit
  `{"type":"error"}` rather than an empty `final`.
- Resolve the pi-ai module from the single pinned install location
  only; ignore `NODE_PATH` from the secrets env.

Status: open.

## F7 (MEDIUM) — Idle watchdog default is effectively "never"; looped
## turns escape it entirely

- `payload/agent/pi_mono.py:73`: `DEFAULT_TURN_TIMEOUT = 86400.0`
  (24 h). Every event resets the idle watchdog, so a model stuck in a
  fast tool-call loop never trips it — only the (currently unenforced,
  F1) call budget would.

Recommended solution:

- Add a **wall-clock** turn ceiling (distinct from the idle watchdog),
  e.g. 30-60 min default, operator-configurable, and lower the idle
  default to something an interactive operator would actually wait for
  (minutes, not a day). Enforce the call budget in the bridge or
  mediator once F1 lands.

Status: open.

## F8 (MEDIUM) — Approval state is not durable across restarts

- Pending approvals live in an in-memory dict
  (`payload/agent/server.py:822-823`) while `pending_tool_call` mirrors
  to SQLite. A restart leaves a pending call visible in history that
  can never be approved.

Recommended solution:

- Rebuild the pending map from SQLite on startup, or expire orphaned
  pending calls to a terminal "abandoned (service restart)" audit +
  history state at boot.

Status: open.

## F9 (MEDIUM) — Supply-chain gaps

- `payload/bin/verify-release` (cosign + SLSA) exists but is not wired
  into the install path; nothing requires it before install.
- `scripts/install.sh` pulls `npm@latest` (`:3367`) and
  `yarn pnpm typescript ts-node` (`:3413`) unpinned.
- The active provider key is forwarded into the environment of every
  child the agent spawns (`payload/agent/pi_mono.py:184-186` keeps the
  active key; children of the agent's bash inherit it).
- The audit log is agent-writable (`payload/agent/audit.py:149-155`,
  0640, agent-owned): no append-only attribute, no remote shipping.

Recommended solution:

- Offer a `verify`-first documented flow and consider refusing
  `install` from an unverified downloaded release (opt-out flag for
  source checkouts).
- Pin the npm tool versions alongside the bridge pins and verify them
  in `scripts/verify-bridge-pins.sh`.
- Scrub provider keys from the environment passed to spawned tool
  subprocesses once F1 restores mediation (the registry executes tools
  itself, so this becomes natural).
- `chattr +a` the audit log (append-only) where the filesystem
  supports it; document the limitation where it does not.

Status: open.

## F10 (MEDIUM) — Changelog discipline is performative

- The project states date-time versioning, but `CHANGELOG.md` has only
  two versioned sections — both SemVer. A ~970-line `## [Unreleased]`
  never rolls over, and `.github/workflows/release.yml:184` greps for
  a version section that never matches, so every release ships the
  fallback one-line notes.

Recommended solution:

- Teach the release workflow to promote `## [Unreleased]` into
  `## [<VERSION>]` at tag time (the workflow already knows the
  version). Mechanical, removes the ritual-vs-reality gap.

Status: open.

## F11 (MEDIUM) — Scope contract is stale in both directions

- `docs/VISION.md` still declares the one-sentence MVP and forbids
  out-of-scope PRs, naming `ROADMAP.md` as the gate — which does not
  exist. Meanwhile Forgejo, llama.cpp serving, and 12 `options/` plans
  ship or are planned. VISION mentions none of them.

Recommended solution:

- Rewrite VISION to describe the components-and-options reality (core
  chat + gated optional components), or restore a real ROADMAP/gate
  and hold options/ to it. Either way, delete the dangling reference.

Status: open.

## F12 (LOW) — Reference-integrity sediment

- Stale parent-directory `AGENTS.md` (outside the repo, in
  `Documents/`) describes the pre-"Zombie Zero" account name and
  removed features (SSH/Tailscale/firewall).
- `AGENTS.md` + VISION reference `docs/design-notes/` — missing.
- CHANGELOG cites `docs/policy-new.yaml` / `policy-new-v2.yaml`;
  actual files are `policy-new-v1-5.5-pro.yaml`,
  `policy-new-v2-fable-5.yaml`, `policy-old.yaml` — three model-tagged
  drafts with no authoritative marker.
- `docs/analysis/README.md` indexes 4 files; the directory holds 9+.
- `ci.yml:88` exempts `CHANGELOG.md` from the secret scan — the
  highest-churn file is where a pasted key would hide.

Recommended solution:

- One focused "reference integrity" PR: fix or delete the stale
  AGENTS.md, remove the design-notes references, reconcile policy file
  names (and mark one authoritative or delete the drafts), update the
  analysis index, and replace the CHANGELOG secret-scan exemption with
  a placeholder allow-list.

Status: open.

## What is genuinely strong (recorded so future passes don't re-flag)

- Fail-closed policy classifier (unknown → `destructive`), argv-aware
  sudo/env-prefix stripping, well unit-tested in isolation.
- Closed tool registry with dependency-free schema validation and
  deliberate `bool`-is-not-`int` rejection.
- PBKDF2-SHA256/200k + `hmac.compare_digest`; layered audit redaction;
  stderr-drain deadlock avoidance; active-provider-only key crossing.
- Release engineering: VERSION-driven tags, SLSA provenance, cosign
  keyless, SPDX SBOM, sha256+SRI-pinned bridges with fail-closed
  verification, hardened `llama-server.service`.
- Component-registry installer design (uniform
  validate/review/dry-run/install/verify/doctor/repair hooks) makes
  idempotence auditable per component.

## Suggested sequencing

1. **F1** — everything else is unreachable until mediation is real.
2. **F2** — so the suite can never certify a stub-only path again.
3. **F3, F4** — the controls that guard the surface meanwhile.
4. **F7, F8** — correctness of long turns and restarts.
5. **F5, F6, F9** — structural hardening.
6. **F10-F12** — documentation/reference integrity (independent of the
   above; can run in parallel at any time).

## Method note

Three parallel read-only reviews (security; architecture/code-quality;
process/documentation) each read disjoint file sets and reported
independently. F1 was found by both code reviewers independently and
then verified by direct source inspection of
`payload/agent/pi-mono-bridge.mjs`, `payload/agent/pi_mono.py`, and
`payload/agent/server.py` before inclusion. No runtime testing was
performed (per `AGENTS.md`, the installer was not executed); F1's
runtime confirmation — a live turn showing tool execution with no
mediation events — is the natural first step of its remediation.
