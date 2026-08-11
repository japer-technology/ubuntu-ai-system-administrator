# Brainstorm: complex Ubuntu solutions made feasible by a resident AI admin

## Why this document exists

The existing option plans —
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md),
[`plan-optional-forgejo-society.md`](plan-optional-forgejo-society.md),
and [`plan-optional-backup.md`](plan-optional-backup.md) — prove a
general point: once a machine carries a private, root-capable AI Systems
Administrator that can install, verify, repair, and explain its own
software *under human approval and audit*, whole classes of software that
were previously "too complex to run unattended on a personal machine"
become realistic **opt-in** components.

This file is a brainstorm, not a commitment. It catalogues candidate
"very complex Ubuntu solutions" that the AI assistance described in
[`docs/VISION.md`](../docs/VISION.md) makes newly feasible, so they can
be triaged into real `plan-optional-*.md` specs later. Each idea is
sketched against the same opt-in shape the existing plans use; it is
deliberately light on implementation detail and heavy on *why AI
assistance changes the calculus*. Candidate **A** (backup/restore) has
already been promoted to a full spec
([`plan-optional-backup.md`](plan-optional-backup.md)) as the worked
example of how an entry here graduates into a plan.

### Promotion workflow and naming

A candidate graduates from a bullet in this file to a real spec by
clearing the bar in "How to triage these into real plans" (below) and
being written up against the shared component checklist. Conventions:

- **One spec per file**, named `plan-optional-<slug>.md` in this
  `options/` directory, where `<slug>` is the master flag's component
  name in lower kebab-case (e.g. `ZOMBIE_INSTALL_BACKUP` →
  `plan-optional-backup.md`).
- Each spec follows the **same section order** the existing plans use:
  Goal · why AI assistance is the unlock · what "maximum" means ·
  behaviour and options · non-negotiables (from `AGENTS.md`) ·
  implementation steps · validation before hand-off · out of scope /
  risks.
- When a candidate is promoted, update its row in the index table below
  to point at the new file so this brainstorm stays the map of record.

## The thesis: what AI assistance actually changes

Self-hosting a serious stack has always been possible on Ubuntu. What
stopped most owners was not the install command — it was everything
*around* it: reading the docs, sequencing prerequisites, generating and
rotating secrets, wiring TLS, opening exactly the right firewall holes,
diagnosing the failure at 11pm, and knowing when an upgrade will break.
A resident administrator that can do `verify`/`doctor`/`repair`, read
the audit log, and explain the next step in plain language collapses
that operating cost. So the interesting candidates are the stacks whose
*difficulty was operational, not conceptual*.

Three multipliers matter:

1. **Day-2 operations become conversational.** Backups, restores,
   certificate renewal, log triage, and capacity questions are exactly
   the "diagnose, explain, configure, repair, operate" loop the MVP
   already promises. Stacks that are easy to install but punishing to
   *run* are the best fit.
2. **Idempotent, audited convergence.** The
   `ZOMBIE_INSTALL_<COMPONENT>=0|1` pattern plus the policy gate and
   receipt means a complex multi-service stack can be declared as data,
   converged by code, and reversed by `uninstall.sh`. Complexity that
   used to live in a human's head becomes a reviewable manifest.
3. **Safe secret handling by default.** Generated DB passwords, tokens,
   and keys land in root-owned files and are surfaced only as
   set/unset fingerprints in the receipt. Stacks with many secrets
   (which is most of them) stop being a footgun.

## Boundaries this brainstorm must respect

These come straight from [`docs/VISION.md`](../docs/VISION.md) and
[`AGENTS.md`](../AGENTS.md), and every candidate below is scoped to fit
them. Ideas that cannot fit are listed in "Explicitly out of scope" so
the line stays bright.

- **One machine, one operator, one trust boundary.** No fleet
  orchestration, no multi-tenant control planes. A candidate that only
  makes sense across many hosts does not belong here.
- **Beside the user, not over them.** Optional components must not
  disrupt existing logins, files, or the desktop session.
- **Every privileged action through the policy gate and audit log.** A
  new component that wants the agent to drive it post-install must add a
  matching policy class in [`payload/etc/policy.yaml`](../payload/etc/policy.yaml)
  and be handled by [`payload/agent/policy.py`](../payload/agent/policy.py);
  no new `sudo` path bypasses the gate.
- **Idempotent, non-interactive-capable, reversible.** Each component is
  one or more guarded `section` blocks that early-return when their flag
  is off, drive end-to-end from env under `ZOMBIE_NONINTERACTIVE=1`, and
  are undone by `uninstall.sh`.
- **No secrets in the repo; British/Commonwealth spelling; the
  `[i]/[+]/[!]/[x]` and `[ok]/[!]/[x]/[~]` glyph vocabulary.**

## A shared "maximum component" checklist

Every candidate, if promoted to a real plan, reuses the same
touch-points the Forgejo server plan enumerates, so they are listed once
here and referenced by each idea:

- option parsing + validators + `usage()` env block;
- interactive parameter-review row and toggle;
- dry-run plan and pre-flight banner lines;
- guarded install `section` blocks (idempotent state checks first);
- generated secrets to root-owned files, fingerprints in the receipt;
- `verify`/`doctor`/`repair` checks with JSON records;
- `uninstall.sh` reversal (destructive steps require the confirmation
  phrase);
- policy/audit classification of anything the agent may later drive;
- `docs/CONFIGURATION.md` + `docs/ARCHITECTURE.md` + `README.md`
  updates; `CHANGELOG.md` entry and a `VERSION` bump.

Where it helps, a component exposes a `*_PROFILE=minimum|maximum`
meta-flag (as the Forgejo plan does) that switches a family of
sub-flags on together while leaving each independently overridable.

---

## Candidate solutions

Grouped by the operator need they serve. Each entry gives the proposed
master flag, what it installs, *why AI assistance is the unlock*, and the
sharpest risk to weigh in a future plan.

### Candidate index

A quick triage map. **Tier** is the group letter; **value-to-risk** is a
rough ranking for sequencing (★★★ = best first mover); **status** links
to a spec once promoted. Flags all default to `0`.

| Tier | Candidate | Master flag | Value-to-risk | Status |
| --- | --- | --- | --- | --- |
| A | Whole-machine backup/restore | `ZOMBIE_INSTALL_BACKUP` | ★★★ | [`plan-optional-backup.md`](plan-optional-backup.md) |
| A | FS snapshots + boot rollback | `ZOMBIE_INSTALL_SNAPSHOTS` | ★★ | [`plan-optional-snapshots.md`](plan-optional-snapshots.md) |
| B | Self-hosted secrets manager | `ZOMBIE_INSTALL_VAULT` | ★★ | candidate |
| B | Local single-sign-on (OIDC) | `ZOMBIE_INSTALL_SSO` | ★ | candidate |
| C | Metrics + logs + dashboards | `ZOMBIE_INSTALL_OBSERVABILITY` | ★★★ | [`plan-optional-observability.md`](plan-optional-observability.md) |
| C | Host inventory + change journal | `ZOMBIE_INSTALL_INVENTORY` | ★★★ | [`plan-optional-inventory.md`](plan-optional-inventory.md) |
| D | Reverse proxy + automatic HTTPS | `ZOMBIE_INSTALL_PROXY` | ★★ | [`plan-optional-proxy.md`](plan-optional-proxy.md) |
| D | Self-hosted DNS / ad-block resolver | `ZOMBIE_INSTALL_DNS` | ★ | candidate |
| E | Files + sync + docs | `ZOMBIE_INSTALL_NEXTCLOUD` | ★ | [`plan-optional-nextcloud.md`](plan-optional-nextcloud.md) |
| E | Read-it-later / wiki | `ZOMBIE_INSTALL_WIKI` | ★★ | candidate |
| E | Curated container app platform | `ZOMBIE_INSTALL_APPS` | ★ | candidate |
| F | Local LLM serving | `ZOMBIE_INSTALL_LOCALLLM` | ★ | [`plan-optional-localllm.md`](plan-optional-localllm.md) |
| G | CI cache / artefact store / registry | `ZOMBIE_INSTALL_REGISTRY` | ★ | candidate |


### A. Data safety and recovery — the highest-value, lowest-risk tier

These directly extend the "diagnose, repair, operate" loop and have the
best effort-to-value ratio.

- **Whole-machine backup and restore** —
  `ZOMBIE_INSTALL_BACKUP`. **Promoted to a full spec:**
  [`plan-optional-backup.md`](plan-optional-backup.md). Scheduled
  `restic`/`borg` snapshots of operator-nominated paths to an
  operator-supplied repository, via a systemd timer; the Forgejo plan
  already sketches `restic` for a single service, so this generalises it
  to the host. *Unlock:* the agent can answer "is my backup healthy?",
  run a test restore on request, and explain a failed snapshot — the part
  people never do. *Risk:* restore is destructive; gate it behind the
  confirmation phrase and never auto-restore.
- **ZFS or Btrfs root with snapshots + boot rollback** —
  `ZOMBIE_INSTALL_SNAPSHOTS`. **Promoted to a full spec:**
  [`plan-optional-snapshots.md`](plan-optional-snapshots.md). Configure
  filesystem snapshots and a pre-`apt` snapshot hook so a bad upgrade is
  one rollback away.
  *Unlock:* the agent can take a labelled snapshot before any risky
  `system_change` it proposes, then offer rollback if `verify` regresses
  — closing the loop the audit log already opens. *Risk:* root-filesystem
  layout changes are deep; likely *new-install only* rather than
  in-place, and must not touch existing partitions without explicit
  consent.

### B. Identity, secrets, and access

- **Self-hosted secrets manager** —
  `ZOMBIE_INSTALL_VAULT` (e.g. a single-node Vault/OpenBao or
  `pass`-style store). Centralises the credentials the agent and its
  optional components consume. *Unlock:* the agent can rotate a leaked
  key on request and re-point dependent services, narrating each step —
  exactly the revocation story the MVP already prizes. *Risk:* a secrets
  store is a high-value target; it must bind to loopback/`tailscale0`,
  and the policy gate around "read/rotate secret" needs its own class.
- **Local single-sign-on / identity provider** —
  `ZOMBIE_INSTALL_SSO` (e.g. a lightweight OIDC provider). Gives the
  optional web services (Forgejo, dashboards, wikis) one login.
  *Unlock:* wiring OIDC clients is fiddly and error-prone by hand; the
  agent converging each service's client config from one manifest is the
  value. *Risk:* mis-scoped tokens are a real footgun — keep it strictly
  single-operator and document that this is *not* multi-tenant SSO.

### C. Observability and self-knowledge

- **Local metrics + logs + dashboards** —
  `ZOMBIE_INSTALL_OBSERVABILITY`. **Promoted to a full spec:**
  [`plan-optional-observability.md`](plan-optional-observability.md)
  (Node Exporter + a small Prometheus +
  Grafana or a Loki/Promtail log stack, all loopback/tailnet-bound). The
  Forgejo plan already proposes Node Exporter for one service; this is
  the host-wide version. *Unlock:* the agent can *read its own metrics*
  to answer "why is the machine slow?" with evidence instead of guesses,
  and pre-build dashboards a human would never assemble. *Risk:*
  monitoring stacks sprawl; ship a curated minimum and resist becoming a
  general TSDB appliance.
- **Structured host inventory + change journal** —
  `ZOMBIE_INSTALL_INVENTORY`. **Promoted to a full spec:**
  [`plan-optional-inventory.md`](plan-optional-inventory.md). A periodic,
  queryable snapshot of installed packages, services, and config drift,
  complementing the audit log. *Unlock:* "what changed since last week?"
  becomes a query the agent answers from data. *Risk:* low; mostly
  read-only, but keep collection best-effort (`|| true`) per the
  diagnostics convention.

### D. Networking and remote access (beyond the existing Tailscale option)

- **Reverse proxy + automatic HTTPS for all local services** —
  `ZOMBIE_INSTALL_PROXY` (Caddy). **Promoted to a full spec:**
  [`plan-optional-proxy.md`](plan-optional-proxy.md). Promotes the
  Forgejo plan's service-specific Caddy idea to a host-wide front door
  that terminates TLS for every opt-in web component on one `*_DOMAIN`.
  *Unlock:* certificate lifecycle and per-service routing are classic
  "install-is-easy, operate-is-hard" toil the agent can own. *Risk:*
  exposing `80`/`443` widens the surface; keep it deliberate and
  consistent with the project's Tailscale-only posture.
- **Self-hosted DNS / ad-blocking resolver** —
  `ZOMBIE_INSTALL_DNS` (e.g. a local recursive resolver with blocklists).
  **Promoted to a full spec:**
  [`plan-optional-dns.md`](plan-optional-dns.md).
  *Unlock:* the agent can explain a resolution failure and tune lists
  conversationally. *Risk:* breaking DNS breaks everything; `verify`
  must include a resolver health check and `doctor` an obvious revert.

### E. Personal application stacks (single-operator "homelab on one box")

These are the canonical "I'd love to self-host this but the upkeep
scared me off" applications. The agent's day-2 ownership is the whole
point.

- **Files + sync + docs** — `ZOMBIE_INSTALL_NEXTCLOUD` (or a lighter
  WebDAV/Syncthing pairing). **Promoted to a full spec:**
  [`plan-optional-nextcloud.md`](plan-optional-nextcloud.md). *Unlock:*
  Nextcloud is notorious for upgrade and PHP-tuning pain the agent can
  shepherd. *Risk:* data
  gravity — back it up (tier A) before enabling.
- **Read-it-later / knowledge base / wiki** —
  `ZOMBIE_INSTALL_WIKI`. Low-risk, high-utility, pairs naturally with
  the proxy and SSO candidates.
- **Local container application platform** —
  `ZOMBIE_INSTALL_APPS` — a *curated, declared* set of containerised
  apps on the Docker Engine the baseline already installs, defined by a
  manifest (echoing the Society's manifest-driven seeding). *Unlock:* the
  agent converges and updates the set and explains a crash-looping
  container. *Risk:* this is the easiest candidate to let sprawl into an
  unbounded PaaS; keep the catalogue small and explicitly enumerated.

### F. Local AI / compute workloads

- **Local LLM serving** — `ZOMBIE_INSTALL_LOCALLLM`. **Promoted to a
  full spec:** [`plan-optional-localllm.md`](plan-optional-localllm.md).
  The codebase *already* discovers and configures a local LLM as the
  `lmstudio` provider; this candidate *installs and manages* the serving
  stack (e.g. an Ollama/llama.cpp service, optional GPU drivers) rather
  than only discovering one. *Unlock:* GPU driver + runtime setup is a
  well-known Ubuntu pain the agent can own, and it dovetails with the
  existing provider plumbing so the agent could run on a model it also
  maintains. *Risk:* proprietary GPU drivers and kernel modules are the
  single most fragile area on desktop Ubuntu; treat driver changes as
  high-risk `system_change`, snapshot first (tier A), and keep CPU-only
  the safe default.

### G. Developer and build infrastructure (adjacent to the Forgejo options)

- **CI cache / artefact store / container registry** —
  `ZOMBIE_INSTALL_REGISTRY`. A natural companion to the Forgejo server +
  runner so builds have a local registry and cache. *Unlock:* registry
  GC, retention, and disk-pressure triage are ongoing chores the agent
  can run. *Risk:* unbounded disk growth; ship retention defaults and a
  `doctor` disk-pressure check.

---

## How to triage these into real plans

A candidate is ready to become a `plan-optional-*.md` when it clears
this bar:

1. **It fits the single-host, single-operator, beside-not-over model.**
   If it only makes sense as a fleet or multi-tenant system, drop it.
2. **Its difficulty is genuinely operational.** The clearer the "easy to
   install, hard to run" gap, the stronger the AI-assistance argument.
3. **It can be expressed as the shared component checklist above** —
   idempotent sections, generated secrets, `verify`/`doctor`/`repair`,
   reversible uninstall, policy class, receipt entry.
4. **Its blast radius is bounded and reversible**, with destructive
   steps behind the confirmation phrase.

Suggested first movers, by value-to-risk: **A (backup/restore)** and
**C (observability)** strengthen the core promise with little new
surface; **D (reverse proxy)** unlocks the whole web-app tier and is a
prerequisite many others share; **B (secrets)** is high value but needs
careful gating. The application stacks (E), local AI (F), and build
infrastructure (G) are best layered on *after* backup and the proxy
exist, so every stateful service is recoverable and reachable from the
moment it is installed. **The tier-A candidates (backup and snapshots),
C and its inventory companion, and D (the reverse proxy) are already
specified** in
[`plan-optional-backup.md`](plan-optional-backup.md),
[`plan-optional-snapshots.md`](plan-optional-snapshots.md),
[`plan-optional-observability.md`](plan-optional-observability.md),
[`plan-optional-inventory.md`](plan-optional-inventory.md) and
[`plan-optional-proxy.md`](plan-optional-proxy.md). With the web-app
tier's shared front door now in place, the natural next promotions are
the **B (secrets)** gate that several stacks want and the first **E**
application stack to ride the proxy.

## Explicitly out of scope (kept out on purpose)

These are tempting but break the boundaries above; listing them keeps the
line bright:

- **Fleet / multi-host orchestration** (Kubernetes clusters, config
  management of *other* machines, a control plane). One machine, one
  operator — full stop.
- **Multi-tenant hosting** of services for third parties, or anything
  that turns the desktop into a shared production server for outside
  users.
- **Replacing the desktop session or existing user accounts.** Optional
  components install *beside* the operator's environment.
- **Unbounded "install anything" app stores.** Every application tier is
  a *curated, enumerated* manifest, never an open-ended PaaS.
- **Pushing agent workloads or secrets to shared infrastructure.** Per
  the Society plan's compliance note, owned hardware is the runtime;
  shared forges and clouds are mirrors/sources only.
