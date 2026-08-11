# Plan: optional self-hosted DNS / ad-blocking resolver (`Unbound` + blocklists)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that installs a
curated, single-host **DNS resolver** with **ad/tracker blocklists** —
a local recursive (or forwarding) resolver that the operator's machine
uses for every lookup, with a small, declarative set of blocklists and
an upstream over **DNS-over-TLS** by default. This is the worked-out
promotion of candidate **D** ("Self-hosted DNS / ad-block resolver",
`ZOMBIE_INSTALL_DNS`, ★) from [`brainstorm.md`](brainstorm.md).

The capability follows the same shape as the existing optional
components (Tailscale, the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md),
and the already-specified backup/observability/inventory/snapshots
plans): off by default, toggled by an environment variable, surfaced in
the interactive parameter review, honoured in the dry-run plan, recorded
in the receipt, idempotent on re-run, gated through the policy/audit
model, verifiable by `verify`/`doctor`/`repair`, and reversible by
`uninstall.sh`. Its sharpest constraint is the one the brainstorm names
outright: *breaking DNS breaks everything*, so this plan is built around
**never letting name resolution go dark**.

## Why AI assistance is the unlock

Installing a resolver is a package; *running* it without locking
yourself out of the network is the day-2 burden the brainstorm's thesis
names directly. The hard parts are operational, not conceptual:
sequencing the cut-over so `systemd-resolved` and the new resolver do
not fight over port `53`, picking and refreshing blocklists without
breaking a site the operator actually needs, diagnosing *why* a single
domain fails to resolve, and reverting safely when a list is too
aggressive. A resident administrator that can read the resolver's query
log and the audit log, run a controlled `dig`/`resolvectl` probe, and
explain a resolution failure in plain language — "this domain is on the
`steven-black` blocklist; allow it?" — collapses exactly that cost. The
agent can also tune lists conversationally and roll a bad change back
through the policy gate, turning a famously brittle piece of
infrastructure into something an owner can actually keep.

## Design principle: never let DNS go dark

The brainstorm's risk note is explicit: *breaking DNS breaks
everything; `verify` must include a resolver health check and `doctor`
an obvious revert.* This plan honours that with three load-bearing
guarantees, each reused from the existing optional-component shape:

- **Atomic, reversible cut-over.** The installer captures the current
  resolver configuration (the `systemd-resolved` stub state and
  `/etc/resolv.conf` target) **before** changing anything, and writes it
  into the receipt and a root-owned saved-state file. The switch to the
  local resolver is one guarded step that is undone verbatim by
  `uninstall.sh` and by `repair`/`doctor`'s revert path.
- **Health-gated activation.** After the resolver is enabled, the
  install section runs a self-test (resolve a known-good name through the
  new resolver) **before** the system is pointed at it. If the self-test
  fails, the section leaves the previous resolver in place, records the
  failure, and exits non-zero rather than half-applying a broken
  cut-over.
- **An always-present escape hatch.** A small `payload/bin` helper
  (e.g. `dns-revert`) restores the captured pre-install resolver state in
  one command, documented in the receipt and `docs/CONFIGURATION.md`, so
  an operator (or the agent, via the policy gate) can recover name
  resolution even if the chat service itself is unreachable.

## Coexisting with `systemd-resolved`

Ubuntu Desktop LTS ships `systemd-resolved` listening on
`127.0.0.53:53` as the stub resolver. A second resolver on `53` is the
classic foot-gun, so the cut-over is explicit and idempotent:

- The resolver binds to a **distinct loopback address/port** by default
  (e.g. `127.0.0.1:53`, with `systemd-resolved`'s stub on `127.0.0.53`),
  and `systemd-resolved` is reconfigured to **forward** to it via a
  drop-in (`/etc/systemd/resolved.conf.d/`), keeping `resolv.conf`
  pointed at the stub. This is the safer default because the desktop's
  per-link DNS, MagicDNS for Tailscale, and VPN split-DNS all keep
  working through `resolved`.
- A `DNS_MODE=resolved-forward|replace` flag selects between forwarding
  through `systemd-resolved` (default) and fully replacing the stub
  (advanced; the resolver owns `53` and `resolv.conf` points at it).
  `replace` is documented as higher-risk and is never the default.
- **Tailscale MagicDNS is preserved.** When the Tailscale option is on,
  the plan keeps MagicDNS working by leaving `resolved`'s tailnet split
  DNS intact in `resolved-forward` mode; this seam is documented so the
  two networking options compose instead of clobbering each other.

## What "maximum" means

The **minimum** viable resolver is: a local recursive/forwarding
resolver bound to loopback, one curated blocklist, an encrypted upstream
(DNS-over-TLS) as the forwarder, the `systemd-resolved` forward cut-over
with the captured-state revert, and a `verify` check that resolution
works through it and the previous state was saved. A **maximum** role
rounds that out, each piece an independently overridable sub-flag under a
`ZOMBIE_DNS_PROFILE=minimum|maximum` meta-flag (mirroring the Forgejo,
backup and observability plans' profile flag):

- **Blocklist refresh timer** — `ZOMBIE_DNS_BLOCKLISTS`. A systemd timer
  that refreshes the enumerated blocklists on a schedule and reloads the
  resolver, instead of a one-shot list baked in at install. Off in
  `minimum`, on in `maximum`.
- **Recursive vs forwarding** — `ZOMBIE_DNS_RECURSIVE`. In `maximum` the
  resolver does full recursion from the root hints (no third-party
  upstream sees queries); in `minimum` it forwards to a configured
  encrypted upstream. Recursion is the stronger privacy story but more
  to operate, so it is opt-in.
- **Local DNS records** — `ZOMBIE_DNS_LOCAL_RECORDS`. Converge a small
  manifest of local A/CNAME records (e.g. names for the other opt-in web
  components fronted by the proxy candidate) so tailnet services get
  stable names. On in `maximum`.
- **Query logging for diagnosis** — `ZOMBIE_DNS_QUERY_LOG`. A privacy-
  conscious, short-retention query log the agent can read to explain "why
  did this fail?", off by default even in `maximum` because query logs
  are sensitive; when on, retention is conservative and the log is
  root-owned.

The maximum profile is therefore the minimum **plus** the refresh timer,
full recursion, local records, reusing the same unit-and-config shape.
DHCP/PXE serving, a second authoritative zone, and split-horizon views
are deliberately deferred — see "Out of scope" — because they turn a
personal resolver into network infrastructure for *other* machines.

## A curated minimum, not a network appliance

The component is **one resolver and an enumerated, small set of
blocklists**, not a general DNS platform:

- **Resolver:** a single, well-understood daemon (e.g. **Unbound**) that
  does both forwarding (with DNS-over-TLS upstreams) and full recursion,
  so one binary covers both profiles. The binary is operator-installed
  by the installer from apt when the option is on; no external control
  plane is contacted at runtime beyond the configured DNS upstream/root
  servers.
- **Blocklists:** a short, **explicitly enumerated** default set (e.g. a
  single widely-trusted hosts-style list) converted into resolver config
  by a small helper, with the operator able to add or remove lists by
  flag/manifest. The set is curated and bounded; this is an ad-blocker
  for one machine, not a managed threat-feed appliance.
- **Allowlist first.** An operator allowlist always overrides the
  blocklists, so a needed domain is one entry away and the agent can add
  it on request through the policy gate.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_DNS=0|1` — master switch (default `0`). When `1`,
  install and configure the local resolver + blocklists.
- `ZOMBIE_DNS_PROFILE=minimum|maximum` — switches the refresh-timer/
  recursive/local-records sub-flags on together (default `minimum`);
  each remains independently overridable.
- `DNS_MODE=resolved-forward|replace` — how the resolver integrates with
  `systemd-resolved` (default `resolved-forward`, the safer path).
- `ZOMBIE_DNS_RECURSIVE=0|1` — full recursion from root hints vs
  forwarding to an encrypted upstream (default follows the profile).
- `DNS_UPSTREAM` — the DNS-over-TLS upstream(s) used when not recursive
  (e.g. a provider's DoT endpoint), validated as `host[@port]#hostname`
  for TLS name verification. Required only when forwarding; ignored when
  `ZOMBIE_DNS_RECURSIVE=1`.
- `ZOMBIE_DNS_BLOCKLISTS` — comma-separated list URLs or a manifest path
  for the enumerated blocklist set (sensible curated default); validated
  as `https://` URLs.
- `ZOMBIE_DNS_ALLOWLIST` — comma-separated domains (or a manifest path)
  that always override the blocklists.
- `ZOMBIE_DNS_BIND` / `DNS_PORT` — loopback bind address/port (defaults
  e.g. `127.0.0.1` / `53`), validated as a loopback address and a free,
  integer port distinct from the `systemd-resolved` stub.
- `ZOMBIE_DNS_QUERY_LOG=0|1` — enable the short-retention query log
  (default `0`, even in `maximum`).
- `ZOMBIE_DNS_LOCAL_RECORDS` — manifest path for local A/CNAME records
  (default empty; on in `maximum` when provided).
- `UNBOUND_VERSION` — optional pin; the default resolves the
  distribution package and records the resolved value in the receipt
  (mirroring how `FORGEJO_VERSION` and the observability plan's pins are
  handled).

This component generates no long-lived application secrets. Any sensitive
artefacts it does write (the captured pre-install resolver state, and the
optional query log) are written **only** to root-owned files on the
target host (e.g. `/etc/ubuntu-zombie/dns.env` and
`/var/lib/ubuntu-zombie/dns/`, mode `600`/`700`, owner `root:root`) and
surfaced via the receipt as set/unset fingerprints — never plaintext
into the repo. Confirm the CI secret-scan patterns (`sk-…`, `sk-ant-…`,
`tskey-auth-…`) are not tripped; do not add example secrets to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: package/binary
   presence (`unbound -V`), the resolver config and `resolved` drop-in,
   the captured pre-install state file, the blocklist artefacts, the
   timer, and the systemd unit. Re-running converges with no errors, no
   duplicate drop-ins or blocklist entries, and never re-captures over an
   already-saved pre-install state (so the revert target stays the true
   original).
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone. When forwarding is selected
   (`ZOMBIE_DNS_RECURSIVE=0`) and `DNS_UPSTREAM` is missing in
   non-interactive mode, exit `64`, consistent with
   `validate_noninteractive()`. When DNS is off, requirements are
   unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. The resolver runs as a system service without the agent, but
   anything the chat agent may later be asked to drive — adding an
   allowlist/blocklist entry, refreshing lists, reloading/restarting the
   resolver, or running the `dns-revert` escape hatch — must be
   classified in `payload/etc/policy.yaml` `sudo_allow_list` and
   described in `docs/ARCHITECTURE.md`. Reads (query the resolver, read
   the query log) are a low-risk class; list edits, reloads, and the
   revert are a `system_change` class.
4. **No new runtime deps beyond what the installer installs.** Unbound
   (and any small fetch/convert tooling) is an apt package installed by
   the installer **only when the option is on**, which is permitted; do
   not add language-level dependencies. Reuse the existing
   `curl_get`/retry helper for blocklist fetches.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation", "minimise",
   "unrecognised").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_DNS`, the `ZOMBIE_DNS_*`, `DNS_MODE`,
  `DNS_UPSTREAM`, `ZOMBIE_DNS_BIND`/`DNS_PORT`, and `UNBOUND_VERSION`
  variables to the defaults/derivation block alongside the other
  `ZOMBIE_*` settings, with conservative defaults (`0`, profile
  `minimum`, `resolved-forward`, the documented bind/port and curated
  blocklist).
- Add validators (a profile enum check, a `DNS_MODE` enum check, the
  loopback-bind and free/distinct/integer port checks, the
  `DNS_UPSTREAM` format check, blocklist/allowlist URL/domain sanity
  checks, and the "`DNS_UPSTREAM` required when forwarding" rule) and
  wire them into `validate_config()` so an invalid value is rejected
  before any host change.
- Extend `validate_noninteractive()` to exit `64` when forwarding is
  selected but `DNS_UPSTREAM` is missing.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in DNS example (interactive and `ZOMBIE_NONINTERACTIVE=1`).

### 2. Interactive parameter review

- Add a "DNS resolver / ad-block" row to `print_parameter_table()`
  showing enabled/disabled and, when enabled, the profile, the mode
  (`resolved-forward`/`replace`), recursive vs upstream (host only),
  and the number of blocklists. Mirror how Tailscale and Forgejo render.
- Add a `_toggle_dns()` editor (and nested profile/mode/upstream/
  blocklist editors) and a new menu entry in `review_parameters()`.
  Append as the next index to minimise churn, and update the range hint
  and the "Unrecognised choice" message accordingly.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when DNS is enabled, the plan lists the install/config/cut-over/
  self-test steps (and the refresh-timer/recursion/local-records steps
  for `maximum`) and explicitly names the captured-state revert path,
  and when disabled it says nothing — keeping the default output
  unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_DNS != 1`. Place them after the Tailscale section so
MagicDNS/split-DNS state already exists and can be preserved:

- `section "Install DNS resolver"` — `apt_install` Unbound (version-
  probed), and any small fetch/convert helper, only when the option is
  on.
- `section "Capture resolver state"` — **before** any change, record the
  current `systemd-resolved` drop-in state and `/etc/resolv.conf` target
  into a root-owned saved-state file (mode `600`), idempotently (never
  overwrite an already-captured original). This is the revert anchor.
- `section "Write DNS config"` — render the Unbound config (loopback
  bind, blocklist include, allowlist override, DoT upstream **or** root
  hints for recursion) and the blocklist artefacts from templates;
  create `/etc/ubuntu-zombie/dns.env` (mode `600`, `root:root`). Bind to
  `${ZOMBIE_DNS_BIND}:${DNS_PORT}` only.
- `section "Enable DNS service"` — `enable --now` the resolver unit via
  the existing `render_unit()` pattern; `daemon-reload` once.
- `section "Cut over resolver"` — run the **health-gated** self-test
  (resolve a known-good name through the new resolver); only on success
  apply the `systemd-resolved` forward drop-in (or, in `replace` mode,
  repoint `resolv.conf`), then re-test end-to-end. On failure, leave the
  previous resolver active, record the failure, and exit non-zero.
- `section "DNS blocklist timer"` *(refresh timer only)* — install a
  systemd timer + oneshot service that refreshes the enumerated
  blocklists and reloads the resolver; idempotent, no duplicate units.
- `section "DNS local records"` *(local records only)* — converge the
  manifest of local A/CNAME records into resolver config; re-running
  never duplicates a record.

### 5. systemd units and helper

- Add `payload/systemd/ubuntu-zombie-unbound.service` (and, for
  `maximum`, `ubuntu-zombie-dns-blocklist.{service,timer}`), header style
  matching existing units, running as the resolver's own unprivileged
  system user with a private data dir and hardening consistent with the
  documented rationale for the existing units (the resolver needs to bind
  a privileged port, so grant `CAP_NET_BIND_SERVICE` rather than running
  as root).
- Add `payload/bin/dns-revert` (bash, `set -Eeuo pipefail`,
  ShellCheck-clean, British spelling, status glyphs) that restores the
  captured pre-install resolver state in one command. Keep it
  best-effort-guarded per the diagnostics convention and document it in
  the receipt and `docs/CONFIGURATION.md`.

### 6. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add DNS checks (only when
  enabled): the binary present and reporting a version; the config and
  `dns.env` exist with correct ownership/modes; the **captured
  pre-install state file exists** (the revert anchor); the service
  `enabled`/`active`; a live resolution of a known-good name **succeeds**
  through the resolver; a known blocked domain is blocked; and, for
  `maximum`, the refresh timer is active and the last refresh recent.
  Use `[ok]/[!]/[x]/[~]` glyphs and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for common failure
  modes (a port clash with the `systemd-resolved` stub, an upstream DoT
  failure, an over-aggressive blocklist breaking a needed domain, and —
  prominently — the **one-command revert** to the captured state when
  resolution is broken).
- Extend `cmd_repair()` to re-assert config/`dns.env` ownership and
  modes, re-apply the forward drop-in, re-enable a disabled unit, and
  refresh the blocklists — never to discard the captured pre-install
  state.

### 7. Receipt

- Record the DNS selection, profile, mode, recursive/upstream (host
  only), bind/port, blocklist count, query-log on/off, the path to the
  captured pre-install state and the `dns-revert` helper, and the
  resolved `UNBOUND_VERSION` in `write_receipt_start`/
  `write_receipt_finish`. Record no plaintext upstream credentials (none
  are expected); the query log, if enabled, is referenced only as a
  set/fingerprint.

### 8. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: **first restore the captured pre-install resolver state**
  (the `resolved` drop-in and `resolv.conf`) so the host can still
  resolve names, then stop/disable the resolver + timer units, remove the
  units, the `/etc/ubuntu-zombie/dns.env`, the rendered config and
  blocklist artefacts, the resolver user, and `daemon-reload`. Removal of
  the optional **query log** (operator data) is gated behind the
  destructive confirmation phrase and warned as irreversible; restoring
  DNS is never gated, because leaving the host unable to resolve names is
  itself the failure mode.

### 9. Policy and docs

- `payload/etc/policy.yaml`: add the read-only verbs (resolver queries,
  reading the query log/`resolvectl status`) at a low-risk class and the
  list edits, blocklist refresh, resolver reload/restart, and
  `dns-revert` verbs at the `system_change` class; describe both in
  `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, defaults, the two
  `DNS_MODE` integration models, the `systemd-resolved`/MagicDNS
  coexistence, and the `dns-revert` escape hatch.
- `docs/ARCHITECTURE.md`: describe the optional DNS component, its trust
  boundary (loopback-bound resolver, encrypted upstream or full
  recursion, no listener on a routable interface), the cut-over/revert
  model, and the new policy entries.
- `README.md`: note the optional component and any new flag/subcommand
  (and list the `dns-revert` helper in the Subcommands/helpers block).
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 10. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_DNS=1` (and, for the forwarding
  path, a dummy `DNS_UPSTREAM`) without touching the host (extend the
  existing `noninteractive`/`subcommands` cases).
- Assert that `ZOMBIE_DNS_RECURSIVE=0` with no `DNS_UPSTREAM` under
  `ZOMBIE_NONINTERACTIVE=1` exits `64`.
- Add a "standards" assertion that the new section names, the
  `ubuntu-zombie-unbound` unit, and the `payload/bin/dns-revert` helper
  exist, that the rendered config binds to loopback only (never
  `0.0.0.0`), and that British spelling / status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including the new `payload/bin/dns-revert` helper and
  the units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  capture-once guard (the revert anchor must stay the true original) and
  the health-gated cut-over (a failed self-test must not half-apply).
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host and reconfigure name resolution. All verification here is static
  (`lint`/`test`/`package`) plus dry-run reasoning. The cut-over,
  blocklist behaviour, and `dns-revert` escape hatch must be validated by
  a human on a disposable Ubuntu Desktop LTS VM.
- **Breaking DNS is the sharp edge.** The captured-state revert, the
  health-gated cut-over, the `verify` resolution check, and the
  `dns-revert` helper are load-bearing; they exist precisely because a
  bad resolver leaves the whole machine unable to resolve names. Never
  apply the cut-over before the self-test passes.
- **No DHCP/PXE, no authoritative zones for a LAN, no split-horizon
  views.** Serving DNS (or DHCP) to *other* machines turns a personal
  resolver into network infrastructure and breaks the one-machine,
  beside-not-over boundary in [`brainstorm.md`](brainstorm.md).
- **The resolver stays loopback-bound.** It must never listen on
  `0.0.0.0` or a routable interface; opening DNS to the network is a
  reflection/amplification risk and is out of scope, consistent with the
  project's Tailscale-only posture.
- **Blocklists are curated and bounded.** An open-ended threat-feed
  subscription model is out of scope; the default set is small and
  explicitly enumerated, and the operator allowlist always wins so a
  needed domain is one entry away.
- **Query logs are sensitive.** They are off by default even in
  `maximum`, short-retention, and root-owned; this is a personal
  diagnostic aid, not a surveillance log.
