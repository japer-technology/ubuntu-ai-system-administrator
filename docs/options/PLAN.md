# Implementation plan for the optional components

This is the cross-cutting roadmap for turning the specifications in this
directory into working code. Each `plan-optional-*.md` file describes
*one* component in full; this file describes **how best to build them
together** — what to build first, what depends on what, and the shared
mechanism every component should ride on.

Read [`README.md`](README.md) for the catalogue and
[`brainstorm.md`](brainstorm.md) for the thesis. Read
[`AGENTS.md`](../AGENTS.md) before writing any code: the non-negotiables
there (idempotence, non-interactive mode, policy gate + audit,
no secrets, no new runtime deps, reversibility) bound every phase below.

## Guiding principle: build the mechanism once, then the components

Every plan repeats the same touch-points — option parsing, an
interactive review row, a dry-run banner line, guarded `section` blocks,
root-owned secret files with receipt fingerprints,
`verify`/`doctor`/`repair`, `uninstall.sh` reversal, a policy class, and
docs. The single biggest risk to this whole effort is re-implementing
that scaffolding twelve slightly different ways.

So **Phase 0 extracts the shared "optional component" mechanism first**,
then every subsequent component is a thin, declarative addition to it.
The backup plan already frames this as a reusable "scheduled maintenance
job" pattern; the proxy plan frames its config as "declared as data".
Generalise those into one internal contract before the second component
ships.

## Phase 0 — the shared opt-in mechanism (prerequisite for all)

Deliver these as a foundation, ideally alongside the first component so
the abstraction is validated by a real user, not designed in a vacuum:

1. **A component registry** in `scripts/install.sh`: a table of
   `ZOMBIE_INSTALL_<COMPONENT>` flags with their defaults (`0`),
   validators, `usage()` env-block text, and interactive review rows,
   so adding a component is data, not copy-paste.
2. **The guarded-`section` convention**: each component's install work is
   one or more `section` blocks that check current state first
   (idempotent) and early-return when the flag is off. Confirm the
   `ZOMBIE_NONINTERACTIVE=1` path drives every flag from env and exits
   `64` on missing required input.
3. **Secret handling**: a helper that writes generated secrets to
   root-owned files and records only set/unset fingerprints in the
   receipt. No component invents its own scheme.
4. **`verify`/`doctor`/`repair` plumbing**: a per-component hook that
   emits JSON records, so the agent can read component health uniformly.
5. **Uninstall symmetry**: a matching reversal hook in
   `scripts/uninstall.sh`, with destructive steps behind the
   confirmation phrase.
6. **Policy + audit**: extend
   [`payload/etc/policy.yaml`](../payload/etc/policy.yaml) and
   [`payload/agent/policy.py`](../payload/agent/policy.py) with the
   pattern for a component-owned policy class, so anything the agent
   later drives is gated and logged from day one.

**Exit criteria:** one component ships end-to-end on this mechanism and
`make lint`, `make test`, and `make package` are green.

## Sequencing: value-to-risk, and dependencies

The brainstorm's triage argues for leading with capabilities that
strengthen the core promise while adding little new surface, then
layering stateful and network-exposed things on top of foundations that
make them recoverable and reachable. The order below follows that logic.

### Phase 1 — data safety (recoverability first)

Ship these before any stateful application, so every later component is
recoverable from the moment it exists.

- [`plan-optional-backup.md`](plan-optional-backup.md) —
  `ZOMBIE_INSTALL_BACKUP`. Highest value-to-risk (★★★) and the best
  worked example of the Phase 0 mechanism. Restore is destructive: gate
  it behind the confirmation phrase and never auto-restore.
- [`plan-optional-snapshots.md`](plan-optional-snapshots.md) —
  `ZOMBIE_INSTALL_SNAPSHOTS`. Configure the distro's snapshot tooling and
  a pre-`apt` hook; **configure, never convert** a root filesystem in
  place, and treat it as new-install-friendly rather than retrofitting
  partitions.

### Phase 2 — observability and self-knowledge

- [`plan-optional-observability.md`](plan-optional-observability.md) —
  `ZOMBIE_INSTALL_OBSERVABILITY` (★★★). Gives the agent evidence instead
  of guesses. Ship a curated minimum; resist becoming a general TSDB.
- [`plan-optional-inventory.md`](plan-optional-inventory.md) —
  `ZOMBIE_INSTALL_INVENTORY` (★★★). Low-risk, mostly read-only; keep
  collection best-effort (`|| true`) per the diagnostics convention.

### Phase 3 — the web front door (unlocks the app tier)

- [`plan-optional-proxy.md`](plan-optional-proxy.md) —
  `ZOMBIE_INSTALL_PROXY` (★★). A host-wide `Caddy` front door that
  terminates TLS and routes to every opt-in web component from one
  domain. Many later components share it as a prerequisite, so build it
  before them. Keep exposure deliberate and consistent with the
  Tailscale-only posture.

### Phase 4 — network resolution and remote access (optional, gated)

- [`plan-optional-dns.md`](plan-optional-dns.md) —
  `ZOMBIE_INSTALL_DNS` (★). Breaking DNS breaks everything: `verify`
  must include a resolver health check and `doctor` an obvious revert.
- [`plan-optional-remote.md`](plan-optional-remote.md) —
  `ZOMBIE_INSTALL_REMOTE`. Re-introduces SSH, Tailscale, `fail2ban`, and
  `x11vnc` as one closed-by-default component. Every door it opens must
  be audited; keep it off unless explicitly enabled.

### Phase 5 — stateful application and compute stacks

Layer these last, once backup (Phase 1) and the proxy (Phase 3) exist,
so every stateful service is recoverable and reachable from install.

- [`plan-optional-nextcloud.md`](plan-optional-nextcloud.md) —
  `ZOMBIE_INSTALL_NEXTCLOUD` (★). Curated container stack with
  PostgreSQL; back it up (Phase 1) before enabling. Data gravity is the
  main risk.
- [`plan-optional-localllm.md`](plan-optional-localllm.md) —
  `ZOMBIE_INSTALL_LOCALLLM` (★). Wire into the existing provider
  plumbing. GPU drivers are the single most fragile area on desktop
  Ubuntu: treat driver changes as high-risk `system_change`, snapshot
  first (Phase 1), and keep CPU-only the safe default.
- [`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md) —
  `ZOMBIE_INSTALL_FORGEJO`. Forgejo + PostgreSQL + optional local runner.
- [`plan-optional-forgejo-society.md`](plan-optional-forgejo-society.md) —
  seeds Forgejo-Society content. **Hard-depends** on the server option;
  it must refuse to run without an installed, healthy Forgejo server.

### Later — candidates still at brainstorm stage

Promote and specify these only after the phases above land, following the
triage bar in [`brainstorm.md`](brainstorm.md): secrets manager
(`ZOMBIE_INSTALL_VAULT`, high value but needs careful gating), local SSO
(`ZOMBIE_INSTALL_SSO`), wiki (`ZOMBIE_INSTALL_WIKI`), curated app
platform (`ZOMBIE_INSTALL_APPS`), and registry/cache
(`ZOMBIE_INSTALL_REGISTRY`).

## Dependency summary

- **Backup** underpins every stateful component (Phase 5 should not be
  enabled without it).
- **Snapshots** underpins risky `system_change` work, especially the
  local-LLM GPU path.
- **Proxy** is a shared prerequisite for the web-facing app tier.
- **Forgejo-Society** hard-depends on **Forgejo server**.
- **Vault/SSO** (future) are prerequisites several later web stacks will
  want; specify them before the second and third application stacks.

## Per-component definition of done

A component is finished only when it satisfies the shared checklist from
[`README.md`](README.md) *and* the plan's own
"Validation before hand-off" section. Concretely:

- flag defaults to `0`; off is a no-op; on is idempotent on re-run;
- drives fully under `ZOMBIE_NONINTERACTIVE=1`; missing required env
  exits `64`;
- secrets land in root-owned files; only fingerprints in the receipt;
- `verify`/`doctor`/`repair` emit JSON records; `uninstall.sh` reverses
  it, destructive steps behind the confirmation phrase;
- any agent-driven behaviour has a policy class and is audit-logged;
- `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, and `README.md`
  reflect the new flag and env vars;
- `CHANGELOG.md` has an unreleased entry and `VERSION` is bumped in
  `yyyy.mm.dd.hh.nn.ss` UTC format;
- the `subcommands`/import/standards checks in
  [`tests/smoke.sh`](../tests/smoke.sh) are extended where the plan says
  so, and `make lint` / `make test` / `make package` are green.

## What to leave alone

Everything under [`docs/design-notes/`](../docs) is historical context —
read-only. Do not widen scope beyond a component's plan: the boundaries
in [`brainstorm.md`](brainstorm.md#explicitly-out-of-scope-kept-out-on-purpose)
(no fleet orchestration, no multi-tenant hosting, no desktop replacement,
no open-ended app stores, no pushing workloads to shared infrastructure)
apply to every phase.
