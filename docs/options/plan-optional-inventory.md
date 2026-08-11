# Plan: optional host inventory and change journal (`ZOMBIE_INSTALL_INVENTORY`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that gives the host
a structured, queryable **inventory** — a periodic snapshot of installed
packages, running services, listening ports, kernel/firmware, and the
configuration files that matter — together with a **change journal** that
records the *diff* between snapshots so "what changed since last week?"
becomes a question the agent answers from data. This is the worked-out
promotion of candidate **C** ("Structured host inventory + change
journal", `ZOMBIE_INSTALL_INVENTORY`, ★★★) from
[`brainstorm.md`](brainstorm.md): with backup
([`plan-optional-backup.md`](plan-optional-backup.md)) and observability
([`plan-optional-observability.md`](plan-optional-observability.md))
already specified, inventory is the natural next promotion because it is
the lowest-risk, mostly read-only **C companion** that strengthens the
core "diagnose, explain, operate" promise and complements the audit log
without adding any service surface or operator data to lose.

The capability follows the same shape as the existing optional
components (Tailscale, the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md),
backup and observability): off by default, toggled by an environment
variable, surfaced in the interactive parameter review, honoured in the
dry-run plan, recorded in the receipt, idempotent on re-run, gated
through the policy/audit model, verifiable by `verify`/`doctor`/`repair`,
and reversible by `uninstall.sh`. It generalises the one-shot
`payload/bin/collect-diagnostics` snapshot into a *scheduled, retained,
diffable* record, reusing the diagnostics convention of best-effort
(`|| true`) collection under `set -Eeuo pipefail`.

## Why AI assistance is the unlock

The data here has always been collectable — `dpkg -l`, `systemctl
list-units`, `ss -ltnp`, `apt` history are one command each. What nobody
does is *keep* those snapshots, *diff* them over time, and *correlate* a
"the machine started misbehaving on Tuesday" complaint with the package
that changed or the service that appeared. A resident administrator that
can read a structured inventory and its change journal answers "what
changed since last week?", "when did this port start listening?", and
"which upgrade preceded this regression?" with *evidence* — a concrete
diff between two dated snapshots — instead of guesses. It pairs directly
with the audit log (which records what *the agent* did) by recording what
changed on the host *regardless of cause*, so an unexplained drift is
visible even when it came from `apt`, a desktop update, or the operator's
own hand. Inventory is therefore the sharpest low-risk demonstration of
the project's self-knowledge value, and unlike the application tiers it
adds *no* network service and *no* irreplaceable operator data.

## Design principle: a read-only journal, not a CMDB

The brainstorm's risk note for this candidate is explicit: *low; mostly
read-only, but keep collection best-effort (`|| true`) per the
diagnostics convention.* This plan honours that by being a **collector +
local store + query helper**, never an enforcement or remediation
engine:

- **Collect, never change.** The collector only *reads* host state. It
  never installs, removes, or reconfigures anything. The change journal
  records drift; it never "corrects" it.
- **Best-effort by construction.** Every external probe is guarded so a
  single failing tool never aborts a snapshot, exactly as
  `payload/bin/collect-diagnostics` already does. A partial snapshot is
  better than none.
- **Local, bounded, no service.** Snapshots and the journal live in a
  root-owned data dir on the host; there is **no** listening daemon, **no**
  web UI, and **no** remote collection. Querying is a local CLI the agent
  invokes through the policy gate.
- **Not a configuration-management database.** Drift detection of *other*
  machines, declarative desired-state enforcement, and agent/server fleet
  models are out of scope (see the final section) — they break the
  one-machine boundary in [`brainstorm.md`](brainstorm.md).

## What "maximum" means

The **minimum** viable inventory is: a scheduled collector (systemd
timer) that writes a timestamped, structured snapshot of the core facts —
installed packages, enabled/active services, listening sockets, kernel
and OS release, and disk/mount layout — to a retained store, plus a query
helper that lists snapshots and shows the diff between any two, and a
`verify` check that the timer is active and a recent snapshot exists. A
**maximum** role rounds that out, each piece an independently overridable
sub-flag under a `ZOMBIE_INVENTORY_PROFILE=minimum|maximum` meta-flag
(mirroring the Forgejo, backup and observability plans' profile flag):

- **Config-file tracking** — `ZOMBIE_INVENTORY_CONFIG`. Hash (and, for an
  enumerated allow-list of non-secret files, snapshot) key configuration
  under `/etc` so the journal can show *which* config changed, not just
  that a package did. **Secret-bearing paths are excluded by an explicit
  deny-list** (e.g. `/etc/ubuntu-zombie/*.env`, `/etc/shadow`, SSH host
  keys); for those, only a change *fingerprint* (hash + mtime) is
  recorded, never the contents. Off in `minimum`, on in `maximum`.
- **Change journal digest** — `ZOMBIE_INVENTORY_DIGEST`. After each
  snapshot, compute the diff against the previous one and append a compact
  human-readable entry ("3 packages upgraded, 1 service added, 1 port
  opened") to a journal the agent can summarise. On in `maximum`.
- **Retention + pruning** — a bounded number of dated snapshots
  (`ZOMBIE_INVENTORY_RETENTION`, conservative default) so the store never
  grows without limit; old snapshots prune oldest-first, the journal
  digest is kept longer because it is tiny.
- **Audit-log correlation** — `ZOMBIE_INVENTORY_CORRELATE`. When a drift
  digest is produced, annotate it with whether a matching
  agent-driven action exists in the audit log for the same window, so the
  operator can tell agent-caused change from external change. On in
  `maximum`.

The maximum profile is therefore the minimum **plus** config-file
tracking, the change-journal digest, and audit correlation, reusing the
same collector-and-store shape. Nothing in either profile opens a port or
runs a persistent daemon.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_INVENTORY=0|1` — master switch (default `0`). When `1`,
  install the collector, timer, store and query helper.
- `ZOMBIE_INVENTORY_PROFILE=minimum|maximum` — switches the config/
  digest/correlate sub-flags on together (default `minimum`); each remains
  independently overridable.
- `ZOMBIE_INVENTORY_CONFIG=0|1` — enable config-file hashing/tracking
  (default follows the profile).
- `ZOMBIE_INVENTORY_DIGEST=0|1` — enable the change-journal digest
  (default follows the profile).
- `ZOMBIE_INVENTORY_CORRELATE=0|1` — annotate digests with audit-log
  correlation (default follows the profile).
- `ZOMBIE_INVENTORY_SCHEDULE` — the collection cadence as a systemd
  `OnCalendar` expression (conservative default, e.g. `daily`), validated
  as a plausible calendar string.
- `ZOMBIE_INVENTORY_RETENTION` — how many dated snapshots to keep
  (conservative integer default, e.g. `30`), validated as a positive
  integer, so the store stays bounded.

There are **no generated secrets** in this component (it stands up no
service and no credential), which is itself a feature of its low-risk
profile. The only secret-adjacent concern is *not capturing* secrets: the
config-tracking deny-list above must keep secret files out of the
snapshot body, recording only a change fingerprint. Confirm the CI
secret-scan patterns (`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not tripped
by any sample data, and do not add example secrets to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: the collector
   binary/script presence, the data dir and its ownership/mode, the
   systemd unit + timer, and the logrotate rule. Re-running converges with
   no errors, no duplicate timer, and no duplicate units. Collection
   itself is naturally idempotent (each run writes a new dated snapshot
   and prunes to the retention bound).
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone; the component needs no interactive
   input. Invalid `ZOMBIE_INVENTORY_*` values (a bad schedule string, a
   non-integer retention) are rejected by `validate_config()` before any
   host change. When inventory is off, requirements are unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the gate.
   The collector runs as a system timer without the agent; anything the
   chat agent may later be asked to drive — running an on-demand snapshot,
   querying the store, showing a diff, or pruning old snapshots — must be
   classified in `payload/etc/policy.yaml` and described in
   `docs/ARCHITECTURE.md`. Reads (list snapshots, show a diff, read the
   journal) are a low-risk read-only class; triggering a collection or
   pruning is at most a low-risk `system_change` class. The collector must
   never call `sudo` outside a matching policy class.
4. **No new runtime deps beyond what the installer installs.** The
   collector is Bash + the standard tools already present (`dpkg`,
   `systemctl`, `ss`, `apt`, `sha256sum`, `journalctl`) plus `python3`
   from the standard library for any diffing/JSON work; no third-party
   packages. Reuse the existing `collect-diagnostics` guarding pattern and
   `scripts/lib.sh` helpers rather than adding tooling.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation", "minimise",
   "summarise", "unrecognised").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_INVENTORY`, the `ZOMBIE_INVENTORY_*` sub-flags, and
  `ZOMBIE_INVENTORY_SCHEDULE` / `ZOMBIE_INVENTORY_RETENTION` to the
  defaults/derivation block alongside the other `ZOMBIE_*` settings, with
  conservative defaults (`0`, profile `minimum`, `daily`, `30`).
- Add validators (profile enum check, `OnCalendar` schedule sanity check,
  retention positive-integer check) and wire them into `validate_config()`
  so an invalid value is rejected before any host change.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in inventory example (interactive and `ZOMBIE_NONINTERACTIVE=1`).

### 2. Interactive parameter review

- Add a "Host inventory + change journal" row to
  `print_parameter_table()` showing enabled/disabled and, when enabled,
  the profile, the schedule, the retention count, and whether config
  tracking and the digest are on. Mirror how Tailscale, Forgejo, backup
  and observability render.
- Add a `_toggle_inventory()` editor (with nested profile/schedule/
  retention/config editors) and a new menu entry in `review_parameters()`.
  Append as the next index to minimise churn, and update the range hint
  and the "Unrecognised choice" message accordingly.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when inventory is enabled, the plan lists the collector/timer/store/
  logrotate steps (and the config-tracking + digest steps for `maximum`),
  and when disabled it says nothing — keeping the default output
  unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_INVENTORY != 1`. Place them after the workspace/data
section so the data dir root already exists:

- `section "Install host inventory collector"` — install the
  `collect-inventory` helper (and the `inventory-query` helper) to the
  payload bin location with mode `0755`, guarded by a presence check.
- `section "Prepare inventory store"` — create the snapshot/journal data
  dir (e.g. `/var/lib/ubuntu-zombie/inventory`, mode `0750`,
  `root:root`), idempotently; never wipe an existing store on re-run.
- `section "Enable inventory timer"` — install and `enable --now` the
  `ubuntu-zombie-inventory.service` (oneshot) and
  `ubuntu-zombie-inventory.timer` via the existing `render_unit()`
  pattern, mirroring the health service/timer pair already in
  `payload/systemd/`; `daemon-reload` once. Run an initial collection so a
  first snapshot exists immediately.
- `section "Rotate inventory store"` — add a logrotate (or built-in
  prune) rule consistent with `payload/logrotate/ubuntu-zombie` so the
  journal and any text logs stay bounded; snapshot pruning to
  `ZOMBIE_INVENTORY_RETENTION` happens inside the collector.

### 5. The collector and query helpers (`payload/bin/`)

- `payload/bin/collect-inventory` — Bash, `#!/usr/bin/env bash`, the
  best-effort guarding convention (each probe `|| true`, no `set -e`
  abort mid-collection, following the `collect-diagnostics` /
  `health-check` precedent). It writes a timestamped structured snapshot
  (packages, services, listening sockets, kernel/OS release, mounts; plus,
  for `maximum`, the config-file hashes honouring the secret deny-list),
  then — for `maximum` — diffs against the previous snapshot, appends a
  digest, optionally annotates audit correlation, and prunes to the
  retention bound.
- `payload/bin/inventory-query` — read-only helper the operator/agent uses
  to `list` snapshots, `show` one, `diff` two (default: latest vs
  previous), and `journal` (the digest history). No mutation.
- Keep both ShellCheck-clean at `--severity=warning` and bash-`-n` clean;
  reuse `scripts/lib.sh` for status glyphs and JSON escaping where useful.

### 6. systemd units

- Add `payload/systemd/ubuntu-zombie-inventory.service` (oneshot, runs the
  collector) and `ubuntu-zombie-inventory.timer` (`OnCalendar` from
  `ZOMBIE_INVENTORY_SCHEDULE`, `Persistent=true`), header style matching
  `ubuntu-zombie-health.{service,timer}`. The collector needs read access
  to package/service/socket state and the config allow-list; keep
  hardening as tight as that read access permits, consistent with the
  documented rationale for the existing units.

### 7. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add inventory checks (only
  when enabled): the collector + query helpers present and executable; the
  data dir exists with correct ownership/mode; the timer `enabled`/active
  and its last run recent; at least one snapshot present and parseable;
  and, for `maximum`, the journal digest present. Use `[ok]/[!]/[x]/[~]`
  glyphs and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for common failure modes
  (timer inactive, no recent snapshot, a probe tool missing, the data dir
  mis-permissioned, and a **store-size** check since unbounded snapshot
  growth — though retention-bounded — is the only real growth risk).
- Extend `cmd_repair()` to re-assert the data-dir ownership/mode, re-enable
  a disabled timer, and re-run a collection — **never** to delete existing
  snapshots or the journal.

### 8. Receipt

- Record the inventory selection, profile, schedule, retention count,
  config-tracking/digest/correlate on/off, and the data-dir path in
  `write_receipt_start`/`write_receipt_finish`. There is no secret to
  fingerprint; note explicitly that no credential is generated.

### 9. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: stop/disable and remove the inventory `service`+`timer`,
  remove the collector/query helpers and the logrotate rule, and
  `daemon-reload`. The snapshot/journal **store** is operator-facing
  history: delete it only behind the destructive confirmation phrase,
  never as the default path, and warn that the change history is then
  irreversibly lost.

### 10. Policy and docs

- `payload/etc/policy.yaml`: add the read-only query verbs (run
  `inventory-query list/show/diff/journal`) at a low-risk class and the
  collect/prune verbs at the low-risk `system_change` class; describe both
  in `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  schedule/retention model, the secret-exclusion deny-list for config
  tracking, and the query helper's subcommands.
- `docs/ARCHITECTURE.md`: describe the optional inventory component, how
  it complements the audit log (host drift regardless of cause vs.
  agent-driven actions), its trust boundary (local store, no service), and
  the new policy entries.
- `README.md`: note the optional component and any new flag/subcommand.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 11. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_INVENTORY=1` (and `=1` with the
  `maximum` profile) without touching the host (extend the existing
  `noninteractive`/`subcommands` cases).
- Assert the collector/query helpers pass `bash -n` and ShellCheck, and
  that `collect-inventory` guards its probes best-effort (no unguarded
  external command under the collection loop).
- Add a "standards" assertion that the new section names, units, helpers,
  and logrotate/policy entries exist, that the config deny-list keeps the
  known secret paths (`*.env`, `/etc/shadow`, host keys) out of the
  snapshot body, and that British spelling / status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including the new `payload/bin` helpers and units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  do-not-wipe-existing-store guard and the retention-prune bound.
- Confirm no secrets, screenshots, or local state are staged, that the
  config deny-list excludes secret files, and that the CI secret-scan
  patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host. All verification here is static (`lint`/`test`/`package`) plus
  dry-run reasoning. End-to-end collection, the timer cadence, and the
  diff output must be validated by a human on a disposable Ubuntu Desktop
  LTS VM.
- **It is a journal, not an enforcer.** Inventory records drift; it never
  remediates it, never enforces a desired state, and never rolls anything
  back. Desired-state/config-management (a CMDB or Ansible-style apply) is
  explicitly out of scope — that is a different, higher-risk product.
- **Capturing secrets is the one sharp edge.** The config-tracking
  deny-list is load-bearing: secret-bearing files must contribute only a
  change fingerprint, never their contents, or the store becomes a secret
  sink. Treat the deny-list as a security control, test it, and default
  config tracking off in `minimum`.
- **No remote or multi-host collection.** This snapshots *this* machine
  only. Pulling inventory from *other* hosts is fleet management and
  breaks the one-machine boundary in [`brainstorm.md`](brainstorm.md).
- **No network service.** The component stands up no listening daemon and
  no web UI; querying is a local CLI through the policy gate. Adding a
  dashboard or API is out of scope (and, if ever wanted, would defer to the
  observability stack's web front door rather than running its own).
