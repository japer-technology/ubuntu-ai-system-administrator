# Optional component plans (`options/`)

This directory is the **design surface** for Ubuntu Zombie's opt-in
software components. It holds no runnable code. Each file is a written
specification for a capability that a future change could add to
[`scripts/install.sh`](../scripts/install.sh) as a public component target
with a compatible `ZOMBIE_INSTALL_<COMPONENT>` selector — off by default,
idempotent, non-interactive-capable, audited, and reversible by
[`scripts/uninstall.sh`](../scripts/uninstall.sh).

[`ghosts-in-the-machine-plan.md`](ghosts-in-the-machine-plan.md) is the
deliberate exception. It records the direction for an independent family
of AI-agent products, not optional components. Those products have their
own releases, installers, updates, security credentials, and lifecycles;
they do not use Ubuntu Zombie's component registry. Their source is
co-located under independent `products/<product-id>/` roots in this
repository. Their normative definitions, implementation contract, and
hand-authored template live in [`docs/ai-agent/`](../ai-agent/). Ubuntu
Zombie is the root-level family manager and invokes each product's
independently owned lifecycle interface.

Runnable components follow the registry contract in
[`scripts/component-registry.sh`](../scripts/component-registry.sh):
isolated configuration and validators; install, verify, doctor, repair,
and uninstall hooks; explicit dependencies; target-scoped review and
dry-run rendering; component-owned receipt and manifest data; and
health-before-manifest ordering. Shared code validates dependency names
and trusted hook functions, then dispatches in registry order (reversed
for uninstall). Dependencies must be registered before their dependants,
and installing a component automatically selects its registered
dependencies. Adding a component must not change parser or dispatcher
conditionals. Environment selectors remain an additive compatibility
surface rather than the execution model.

The premise, argued in [`brainstorm.md`](brainstorm.md) and
[`docs/VISION.md`](../docs/VISION.md), is simple: once a machine carries
a private, root-capable AI Systems Administrator that can `verify`,
`doctor`, `repair`, and *explain* its own software under human approval
and audit, whole classes of software that were previously "too complex
to run unattended on a personal machine" become realistic **opt-in**
components. These plans triage and specify those candidates.

## How the files fit together

- [`brainstorm.md`](brainstorm.md) — the map of record. It catalogues
  candidate components, groups them into tiers, and carries the
  **candidate index** table that tracks each one from idea to spec. Start
  here.
- `plan-optional-<slug>.md` — one worked specification per component.
  A candidate graduates from a bullet in the brainstorm to its own plan
  file once it clears the triage bar (see below).
- [`PLAN.md`](PLAN.md) — the cross-cutting implementation roadmap: how to
  sequence and build these components so shared foundations land before
  the things that depend on them.

## Plans in this directory

Grouped by the operator need they serve. Every flag defaults to `0`.

### Data safety and recovery

- [`plan-optional-backup.md`](plan-optional-backup.md) —
  `ZOMBIE_INSTALL_BACKUP`. Scheduled `restic` snapshots of
  operator-nominated paths to an operator-supplied repository, with
  agent-assisted health checks and operator-driven restore.
- [`plan-optional-snapshots.md`](plan-optional-snapshots.md) —
  `ZOMBIE_INSTALL_SNAPSHOTS`. Filesystem snapshots and a pre-`apt` hook
  so a bad upgrade is one boot rollback away. Configures the distro's own
  tooling; never converts a root filesystem in place.

### Observability and self-knowledge

- [`plan-optional-observability.md`](plan-optional-observability.md) —
  `ZOMBIE_INSTALL_OBSERVABILITY`. A curated Prometheus + Grafana + Loki
  stack, loopback/tailnet-bound, so the agent can read its own metrics
  and logs to answer "why is the machine slow?" with evidence.
- [`plan-optional-inventory.md`](plan-optional-inventory.md) —
  `ZOMBIE_INSTALL_INVENTORY`. A periodic, queryable snapshot of packages,
  services, and config drift — a read-only change journal that
  complements the audit log.

### Networking and remote access

- [`plan-optional-proxy.md`](plan-optional-proxy.md) —
  `ZOMBIE_INSTALL_PROXY`. A host-wide `Caddy` front door that terminates
  TLS and routes to every opt-in web component from one domain.
- [`plan-optional-dns.md`](plan-optional-dns.md) —
  `ZOMBIE_INSTALL_DNS`. A curated single-host `Unbound` resolver with
  ad/tracker blocklists and DNS-over-TLS upstream, with health checks
  that never let DNS go dark.
- [`plan-optional-remote.md`](plan-optional-remote.md) —
  `ZOMBIE_INSTALL_REMOTE`. Re-introduces the full remote-access surface
  (SSH, Tailscale, `fail2ban`, `x11vnc`) as one feature-gated,
  closed-by-default component.

### Personal application stacks

- [`plan-optional-nextcloud.md`](plan-optional-nextcloud.md) —
  `ZOMBIE_INSTALL_NEXTCLOUD`. A single-operator Nextcloud (files, sync,
  docs) as a curated container stack with PostgreSQL, where the agent
  owns the day-2 upkeep Nextcloud is infamous for.

### Local AI / compute

- [`plan-optional-localllm.md`](plan-optional-localllm.md) —
  `ZOMBIE_INSTALL_LOCALLLM`. Installs and manages a local LLM runtime
  (`Ollama` by default, `llama.cpp` alternative) with optional GPU
  enablement, wired into the existing provider plumbing so the agent can
  run on a model it also maintains.

### Developer and build infrastructure

- [`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md) —
  `ZOMBIE_INSTALL_FORGEJO` (server). A self-hosted Forgejo server backed
  by PostgreSQL, with an optional local Actions runner on the same host.
- [`plan-optional-forgejo-society.md`](plan-optional-forgejo-society.md) —
  seeds the Forgejo-Society content (organisations, role repositories,
  conformance suite, workflows) **on top of** an installed Forgejo
  server. Hard-depends on the server plan.

### Independent AI-agent family

- [`docs/ai-agent/`](../ai-agent/) — the readable catalogue and canonical
  family definitions for Ubuntu Zombie, Imaginary Friend, Curriculum Flame,
  and ERIC, the in-repository implementation contract, and the template for
  future agents. Ubuntu Zombie has the designated God-level host-management
  role; the existing named products remain unprivileged and independently
  packaged, while a future product may declare and justify full root authority.
- [`ghosts-in-the-machine-plan.md`](ghosts-in-the-machine-plan.md) —
  records the rationale and implementation plan for a family of separate
  products:
  the root-capable Ubuntu Zombie, the less-privileged Imaginary Friend,
  Curriculum Flame, ERIC (Evolving Record of Identity and Cognition), and
  future helpful agents. ERIC records who one consenting person is, what they
  know, and how they think while preserving source provenance; it can later
  ground an authorised but explicitly non-conscious simulation after death.
  Each product owns its
  installer, updater, runtime, policy, security password and other
  credentials, state, audit trail, and release. There is no shared ghost
  registry, capability tier, payload, or lifecycle implementation; Ubuntu
  Zombie manages them by verifying and invoking their product-owned
  interfaces under operator approval and dual audit.
  The authoritative Curriculum Flame product definition is
  [`docs/ai-agent/curriculum-flame.md`](../ai-agent/curriculum-flame.md);
  [`curriculum-gates-local-ai-for-children.md`](curriculum-gates-local-ai-for-children.md)
  remains its earlier requirements study.

Candidates still at the brainstorm stage — secrets manager
(`ZOMBIE_INSTALL_VAULT`), local SSO (`ZOMBIE_INSTALL_SSO`), wiki
(`ZOMBIE_INSTALL_WIKI`), curated app platform (`ZOMBIE_INSTALL_APPS`),
and registry/cache (`ZOMBIE_INSTALL_REGISTRY`) — are described in
[`brainstorm.md`](brainstorm.md) and have no plan file yet.

## The shape every plan shares

Each `plan-optional-*.md` is written against the same section order so
they can be read and reviewed uniformly:

> Goal · why AI assistance is the unlock · what "maximum" means ·
> behaviour and options · non-negotiables (from
> [`AGENTS.md`](../AGENTS.md)) · implementation steps ·
> validation before hand-off · out of scope / risks.

Every component, when built, reuses the same touch-points:

- option parsing + validators + `usage()` env block;
- an interactive parameter-review row and toggle;
- a dry-run plan and pre-flight banner lines;
- guarded install `section` blocks that check current state first
  (idempotent) and early-return when the flag is off;
- generated secrets written to root-owned files, surfaced only as
  set/unset fingerprints in the receipt;
- `verify`/`doctor`/`repair` checks that emit JSON records;
- `uninstall.sh` reversal, with destructive steps behind the
  confirmation phrase;
- a policy class in [`payload/etc/policy.yaml`](../payload/etc/policy.yaml)
  and handling in [`payload/agent/policy.py`](../payload/agent/policy.py)
  for anything the agent may later drive;
- `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, and `README.md`
  updates; a `CHANGELOG.md` entry and a `VERSION` bump.

## Naming and promotion workflow

- **One spec per file**, named `plan-optional-<slug>.md`, where `<slug>`
  is the master flag's component name in lower kebab-case
  (`ZOMBIE_INSTALL_BACKUP` → `plan-optional-backup.md`).
- A candidate graduates from a brainstorm bullet to a real spec when it
  clears the triage bar in
  [`brainstorm.md`](brainstorm.md#how-to-triage-these-into-real-plans):
  it fits the single-host, single-operator, beside-not-over model; its
  difficulty is genuinely operational; it can be expressed as the shared
  checklist above; and its blast radius is bounded and reversible.
- When a candidate is promoted, update its row in the candidate index in
  [`brainstorm.md`](brainstorm.md) to point at the new file, so the
  brainstorm stays the map of record.

## Boundaries these plans respect

Drawn from [`docs/VISION.md`](../docs/VISION.md) and
[`AGENTS.md`](../AGENTS.md):

- **One machine, one operator, one trust boundary** — no fleet
  orchestration, no multi-tenant control planes.
- **Beside the user, not over them** — components install alongside the
  operator's session; they never replace logins, files, or the desktop.
- **Every privileged action through the policy gate and audit log** — no
  new `sudo` path bypasses the gate.
- **Idempotent, non-interactive-capable, reversible** — each component is
  one or more guarded sections, drivable end-to-end under
  `ZOMBIE_NONINTERACTIVE=1`, and undone by `uninstall.sh`.
- **No secrets in the repo; British/Commonwealth spelling; the
  `[i]/[+]/[!]/[x]` and `[ok]/[!]/[x]/[~]` glyph vocabulary.**

## Status

The **Forgejo server** plan is implemented: `ZOMBIE_INSTALL_FORGEJO`
(and `ZOMBIE_INSTALL_FORGEJO_RUNNER`) exist in `scripts/install.sh`,
together with the shared optional-component mechanism (the `9) Options`
review sub-menu, dry-run/banner/receipt stanzas, verify/doctor/repair
checks, and `uninstall.sh` reversal). See
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md)
for the as-built deltas and
[`docs/CONFIGURATION.md`](../docs/CONFIGURATION.md#optional-components-ubuntu-zombie--options)
for operator documentation. Every other flag here remains design, not
implementation; see [`PLAN.md`](PLAN.md) for the recommended order.
