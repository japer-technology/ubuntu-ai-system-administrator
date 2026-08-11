# Plan: optional local observability — metrics, logs and dashboards (`Prometheus` + `Grafana` + `Loki`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that installs a
curated, single-host **observability** stack — host and service
**metrics**, structured **logs**, and pre-built **dashboards** — all
bound to loopback/the tailnet and fronted by a **great web server**
(Caddy reverse proxy with automatic HTTPS). This is the worked-out
promotion of candidate **C** ("Local metrics + logs + dashboards",
`ZOMBIE_INSTALL_OBSERVABILITY`, ★★★) from
[`brainstorm.md`](brainstorm.md): with backup
([`plan-optional-backup.md`](plan-optional-backup.md)) already specified,
observability is the natural next first mover because it strengthens the
core "diagnose, explain, operate" promise with little new surface and no
data-loss risk.

The capability follows the same shape as the existing optional
components (Tailscale, and the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md)):
off by default, toggled by an environment variable, surfaced in the
interactive parameter review, honoured in the dry-run plan, recorded in
the receipt, idempotent on re-run, gated through the policy/audit model,
verifiable by `verify`/`doctor`/`repair`, and reversible by
`uninstall.sh`. It generalises the per-service Node Exporter sketch in
the Forgejo server plan (`install/06-node-exporter.md`) to the whole
host and adds the logs and dashboard tiers around it.

## Why AI assistance is the unlock

Installing Prometheus is a package; *running* an observability stack is
the classic day-2 burden the brainstorm's thesis names directly. Nobody
hand-writes scrape configs, nobody curates dashboards, nobody correlates
a CPU spike with the log line that caused it, and a half-configured
Grafana with a public port is a footgun, not a feature. A resident
administrator that can **read its own metrics and logs** answers "why is
the machine slow?" with *evidence* — a real series, a real log
excerpt — instead of guesses, pre-builds the dashboards a human would
never assemble, and explains a scrape failure in plain language, all
through the policy gate and audit log. Observability is therefore the
sharpest demonstration of the project's self-knowledge value, and unlike
the application tiers it adds *no* persistent operator data to lose.

## Design principle: a curated minimum, not a TSDB appliance

The brainstorm's risk note for this candidate is explicit: *monitoring
stacks sprawl; ship a curated minimum and resist becoming a general
TSDB appliance.* This plan honours that by enumerating a small, fixed
set of components with conservative retention, all reusing the existing
optional-component shape:

- **Metrics:** Node Exporter (host metrics) scraped by a small,
  short-retention **Prometheus**.
- **Logs:** **Promtail** tailing the journal/files into a small
  **Loki**.
- **Dashboards + web front door:** **Grafana**, provisioned from code
  with a curated dashboard set, served behind **Caddy** (see "A great
  web server" below).

No alertmanager, no remote-write, no clustering, no exporter zoo: those
are out of scope (see the final section) and would turn a personal
diagnostic aid into fleet infrastructure, breaking the one-machine
boundary in [`brainstorm.md`](brainstorm.md). Generalise the shared
plumbing (unit rendering, the Caddy seam) only as far as this stack
actually needs it, to avoid speculative abstraction.

The component binaries are **operator-installed by the installer** from
apt or pinned upstream single-binary releases when the option is on; no
external control plane is contacted at runtime.

## A great web server (the dashboard front door)

The dashboards are only useful if they are *served well*. The web tier
is a first-class part of this plan, not an afterthought:

- **Caddy** is the front door, terminating TLS and reverse-proxying
  Grafana. This reuses and is consistent with the Forgejo plan's Caddy
  web-server component (`install/08-caddy-web-server.md`): one battle-
  tested server, automatic HTTPS, HTTP/2 and HTTP/3, sane security
  headers, and a tiny, declarative `Caddyfile`.
- **Tailnet-bound by default.** Consistent with the project's
  Tailscale-only posture, Grafana, Prometheus and Loki bind to
  `127.0.0.1`; Caddy listens only on `tailscale0` (or loopback when
  Tailscale is off). Prometheus and Loki are **never** exposed through
  Caddy — only Grafana is reachable, and only over the tailnet.
- **HTTPS by design.** When an `OBSERVABILITY_DOMAIN` on the tailnet is
  supplied, Caddy obtains/renews a certificate (Tailscale/`tailscale
  cert` or an operator-supplied internal CA); otherwise it serves a
  certificate from Caddy's built-in internal CA (`tls internal`). In the
  internal-CA case the dashboard is reachable over HTTPS on the tailnet,
  but the operator must trust Caddy's local root once (or accept the
  one-time browser warning) — document this trust step. The dashboard is
  never served plaintext on a routable interface.
- **One toggle.** `ZOMBIE_OBSERVABILITY_WEB=1` (on in `maximum`) selects
  the Caddy front door; with it off, Grafana stays strictly on loopback
  for `ssh -L` access only. When the host-wide reverse-proxy candidate
  (`ZOMBIE_INSTALL_PROXY`) is promoted, this stack defers its front door
  to it rather than running a second Caddy — document that seam.

## What "maximum" means

The **minimum** viable observability is: Node Exporter + a short-
retention Prometheus scraping it, Grafana with the curated dashboards on
loopback, and a `verify` check that the targets are up and the last
scrape succeeded. A **maximum** role rounds that out, each piece an
independently overridable sub-flag under a
`ZOMBIE_OBSERVABILITY_PROFILE=minimum|maximum` meta-flag (mirroring the
Forgejo and backup plans' profile flag):

- **Logs tier** — `ZOMBIE_OBSERVABILITY_LOGS`. Loki + Promtail tailing
  the systemd journal (and `ubuntu-zombie` logs), so the agent can
  correlate a metric spike with the log line behind it. Off in
  `minimum`, on in `maximum`.
- **Great web server** — `ZOMBIE_OBSERVABILITY_WEB`. The Caddy + HTTPS
  front door described above. Off in `minimum` (loopback-only Grafana),
  on in `maximum`.
- **Service discovery for opt-in components** —
  `ZOMBIE_OBSERVABILITY_SCRAPE_SERVICES`. When another optional
  component exposes an exporter (e.g. the Forgejo plan's Node Exporter
  or Forgejo's own metrics), converge a scrape job for it from a small
  manifest rather than hand-editing Prometheus config. On in `maximum`.
- **Retention hardening** — sensible `prometheus --storage.tsdb.retention.time`
  and Loki retention defaults so neither store grows without bound; the
  `doctor` disk-pressure check (below) backs this up.

The maximum profile is therefore the minimum **plus** the logs tier, the
Caddy/HTTPS web front door, and component scrape discovery, reusing the
same unit-and-config shape. Alerting is deliberately deferred — see "Out
of scope" — because it needs an outbound notifier the baseline does not
install.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_OBSERVABILITY=0|1` — master switch (default `0`). When
  `1`, install and configure the metrics + dashboards stack.
- `ZOMBIE_OBSERVABILITY_PROFILE=minimum|maximum` — switches the logs/
  web/scrape sub-flags on together (default `minimum`); each remains
  independently overridable.
- `ZOMBIE_OBSERVABILITY_LOGS=0|1` — enable the Loki + Promtail logs tier
  (default follows the profile).
- `ZOMBIE_OBSERVABILITY_WEB=0|1` — enable the Caddy reverse-proxy +
  HTTPS front door for Grafana (default follows the profile).
- `OBSERVABILITY_DOMAIN` — the tailnet hostname Caddy serves Grafana on
  when the web front door is enabled (e.g. a MagicDNS name). Required
  only when `ZOMBIE_OBSERVABILITY_WEB=1`; when absent, Caddy serves a
  Caddy-internal cert on the tailnet address.
- `GRAFANA_HTTP_PORT` / `PROMETHEUS_HTTP_PORT` / `LOKI_HTTP_PORT` —
  loopback bind ports (sensible defaults, e.g. `3001`/`9090`/`3100`),
  validated as free, distinct ports.
- `GRAFANA_ADMIN_PASSWORD` — Grafana admin passphrase. If unset, the
  installer **generates** a strong one and stores it root-only; if set,
  it is used and stored the same way. Never printed or committed;
  surfaced in the receipt as a set/unset fingerprint only.
- `ZOMBIE_OBSERVABILITY_RETENTION` — Prometheus/Loki retention window
  (default conservative, e.g. `15d`), to keep the curated minimum from
  sprawling.
- `ZOMBIE_OBSERVABILITY_SCRAPE_SERVICES=0|1` — converge scrape jobs for
  other enabled optional components from a manifest (default follows the
  profile).
- `PROMETHEUS_VERSION` / `GRAFANA_VERSION` / `LOKI_VERSION` /
  `NODE_EXPORTER_VERSION` — optional pins; defaults resolve the
  distribution package or the upstream release, recording the resolved
  value in the receipt (mirroring how `FORGEJO_VERSION` and the Node
  bridge pins are handled).

Generated secrets (`GRAFANA_ADMIN_PASSWORD` when auto-generated, any
data-source tokens) are created at install time and **never** committed
or printed into the repo. They are written only to root-owned files on
the target host (e.g. `/etc/ubuntu-zombie/observability.env`, mode
`600`, owner `root:root`) and surfaced via the receipt as set/unset
fingerprints — not plaintext. Confirm the CI secret-scan patterns
(`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not tripped; do not add example
secrets to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: package/binary
   presence (`prometheus --version`, `grafana-server -v`, `loki
   -version`, `caddy version`), the env/config files, provisioned
   dashboards, and the systemd units. Re-running converges with no
   errors, no duplicate scrape jobs, and no duplicate units.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone. When `ZOMBIE_OBSERVABILITY_WEB=1`
   and `OBSERVABILITY_DOMAIN` is missing in non-interactive mode, exit
   `64`, consistent with `validate_noninteractive()`. When observability
   is off, requirements are unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. The stack runs as system services without the agent, but
   anything the chat agent may later be asked to drive — querying
   Prometheus/Loki, restarting a collector, reloading Caddy, rotating the
   Grafana admin password — must be classified in
   `payload/etc/policy.yaml` `sudo_allow_list` and described in
   `docs/ARCHITECTURE.md`. Reads (query metrics/logs) are a low-risk
   class; service restarts/config reloads are a `system_change` class.
4. **No new runtime deps beyond what the installer installs.**
   Prometheus, Grafana, Loki, Promtail, Node Exporter and Caddy are apt
   packages (or pinned single-binary releases) installed by the
   installer **only when the option is on**, which is permitted; do not
   add language-level dependencies. Reuse existing `curl_get`/retry and
   architecture-mapping helpers if fetching a binary release.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation", "minimise",
   "visualise").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_OBSERVABILITY`, the `ZOMBIE_OBSERVABILITY_*`, the
  `*_HTTP_PORT`, `OBSERVABILITY_DOMAIN`, `GRAFANA_ADMIN_PASSWORD`, and
  the `*_VERSION` variables to the defaults/derivation block alongside
  the other `ZOMBIE_*` settings, with conservative defaults (`0`,
  profile `minimum`, the documented ports and retention).
- Add validators (port free/distinct/integer checks, a profile enum
  check, a retention-string sanity check, and the
  "`OBSERVABILITY_DOMAIN` required when web front door enabled" rule)
  and wire them into `validate_config()` so an invalid value is rejected
  before any host change.
- Extend `validate_noninteractive()` to exit `64` when the web front
  door is enabled but `OBSERVABILITY_DOMAIN` is missing.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in observability example (interactive and `ZOMBIE_NONINTERACTIVE=1`).

### 2. Interactive parameter review

- Add an "Observability (Prometheus/Grafana)" row to
  `print_parameter_table()` showing enabled/disabled and, when enabled,
  the profile, the Grafana URL/domain (host only — never the password),
  whether the logs tier and web front door are on. Mirror how Tailscale
  and Forgejo render.
- Add a `_toggle_observability()` editor (and nested profile/logs/web/
  domain editors) and a new menu entry in `review_parameters()`. Append
  as the next index to minimise churn, and update the range hint and the
  "Unrecognised choice" message accordingly.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when observability is enabled, the plan lists the install/scrape/
  dashboard/timer/web steps (and the logs + Caddy steps for `maximum`),
  and when disabled it says nothing — keeping the default output
  unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_OBSERVABILITY != 1`. Place them after the
workspace/data and (if present) Tailscale sections so the bind interface
and data dirs already exist:

- `section "Install observability tools"` — `apt_install` (or fetch and
  `install -m 0755` pinned arch-matched releases) for Node Exporter,
  Prometheus, Grafana, and — for `maximum` — Loki/Promtail and Caddy,
  each guarded by a version probe.
- `section "Write observability config"` — render Prometheus scrape
  config, Loki/Promtail config, and Grafana provisioning files
  (data sources + the curated dashboard set) from templates; create
  `/etc/ubuntu-zombie/observability.env` (mode `600`, `root:root`) and
  generate `GRAFANA_ADMIN_PASSWORD` once, reusing it if the file already
  exists so re-runs never desync the credential. Bind every component to
  `127.0.0.1:${*_HTTP_PORT}`.
- `section "Provision dashboards"` — install the curated dashboards
  (host overview, the agent/service health, and — when logs are on — a
  logs panel) via Grafana file-based provisioning so they are declared
  as code, not clicked in by hand. Idempotent: re-provision overwrites
  the managed dashboards, never duplicates them.
- `section "Enable observability services"` — install and `enable --now`
  the `node_exporter`, `prometheus`, `grafana-server` (and, for
  `maximum`, `loki`/`promtail`) units via the existing `render_unit()`
  pattern; `daemon-reload` once.
- `section "Observability web server"` *(web front door only)* — render a
  minimal `Caddyfile` that reverse-proxies `OBSERVABILITY_DOMAIN` →
  `127.0.0.1:${GRAFANA_HTTP_PORT}` with automatic HTTPS and security
  headers, bind Caddy to `tailscale0` (loopback when Tailscale is off),
  enable the Caddy service, and add a UFW rule restricting `443` (and
  `80` for the ACME/redirect) to `tailscale0` consistent with the
  Tailscale-only posture. **Never** proxy Prometheus or Loki.
- `section "Scrape opt-in components"` *(scrape discovery only)* — when
  `ZOMBIE_OBSERVABILITY_SCRAPE_SERVICES=1`, converge a scrape job for
  each enabled optional component that exposes an exporter, from a small
  manifest; re-running never duplicates a job.

### 5. systemd units

- Add `payload/systemd/ubuntu-zombie-{prometheus,grafana,loki,promtail,
  node-exporter}.service` (only those a profile uses), header style
  matching existing units. Run each as its own unprivileged system user
  with a private data dir; keep hardening consistent with the documented
  rationale for the chat unit — restrict where it does not block the
  component (Promtail needs journal read access; Grafana needs its
  provisioning and data dirs). Caddy reuses/extends the Forgejo plan's
  Caddy unit pattern.

### 6. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add observability checks
  (only when enabled): each binary present and reporting a version; the
  env/config files exist with correct ownership/modes; each service
  `enabled`/`active`; Prometheus targets `up` and the last scrape
  recent; Grafana answering on loopback; and, for `maximum`, Loki ready,
  the dashboards provisioned, and — for the web front door — Caddy
  active and Grafana reachable through it on the tailnet. Use
  `[ok]/[!]/[x]/[~]` glyphs and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for common failure
  modes (a target down, a port clash, Grafana provisioning error, Caddy
  cert/ACME failure on the tailnet, and a **disk-pressure** check for the
  Prometheus/Loki data dirs since unbounded growth is this stack's
  sharpest operational risk).
- Extend `cmd_repair()` to re-assert env/config file ownership and modes,
  re-provision the managed dashboards, reload Caddy, and re-enable any
  disabled unit — never to wipe metric/log data.

### 7. Receipt

- Record the observability selection, profile, Grafana domain/host
  (never the password), the ports, retention window, logs/web on/off,
  and the resolved `*_VERSION` values in `write_receipt_start`/
  `write_receipt_finish`. Record `GRAFANA_ADMIN_PASSWORD` only as
  "set"/fingerprint.

### 8. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: stop/disable every observability + Caddy unit, remove
  the units, the `/etc/ubuntu-zombie/observability.env`, the rendered
  configs/dashboards and the Caddyfile, drop the UFW rules, remove the
  component users created, and `daemon-reload`. Removal of the
  Prometheus/Loki **data dirs** (the time series and logs) is the
  operator's data: delete it only behind the destructive confirmation
  phrase, never as the default path, and warn it is irreversible.

### 9. Policy and docs

- `payload/etc/policy.yaml`: add the read-only query verbs (Prometheus/
  Loki HTTP queries, `journalctl` reads) at a low-risk class and the
  service restart/`caddy reload`/password-rotation verbs at the
  `system_change` class; describe both in `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  default ports/retention, the tailnet-bound web model, and the
  loopback-vs-Caddy access modes.
- `docs/ARCHITECTURE.md`: describe the optional observability component,
  its trust boundary (loopback collectors + a single tailnet-bound web
  front door; Prometheus/Loki never exposed), and the new policy entries.
- `README.md`: note the optional component and any new flag/subcommand.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 10. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_OBSERVABILITY=1` (and, for the
  web path, a dummy `OBSERVABILITY_DOMAIN`) without touching the host
  (extend the existing `noninteractive`/`subcommands` cases).
- Assert that `ZOMBIE_OBSERVABILITY_WEB=1` with no `OBSERVABILITY_DOMAIN`
  under `ZOMBIE_NONINTERACTIVE=1` exits `64`.
- Add a "standards" assertion that the new section names, units, and any
  `payload/bin` helpers exist, that the rendered configs bind to
  loopback (and only Caddy/Grafana is exposed), and that British
  spelling / status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including any new `payload/bin` helpers and units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  reuse-existing-password guard and the no-duplicate-scrape-job guard.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host and start listening services. All verification here is static
  (`lint`/`test`/`package`) plus dry-run reasoning. End-to-end scraping,
  dashboards, and the Caddy front door must be validated by a human on a
  disposable Ubuntu Desktop LTS VM.
- **Sprawl is the sharp edge.** Unbounded TSDB/log growth and an
  exporter zoo are how monitoring stacks rot. The curated component list,
  conservative retention defaults, and the `doctor` disk-pressure check
  are load-bearing; resist becoming a general TSDB appliance.
- **The web tier must stay tailnet-only.** Grafana is the only thing
  Caddy exposes, only over `tailscale0`, only with HTTPS; Prometheus and
  Loki never leave loopback. Widening this to public `0.0.0.0` breaks the
  project's Tailscale-only posture and is out of scope.
- **No alerting/notifications** (Alertmanager, email/Slack on a firing
  rule) in this plan — it needs an outbound notifier the baseline does
  not install; alerting is layered on later, consistent with the
  brainstorm deferring a host mailer.
- **No remote-write, federation, or multi-host aggregation.** This is a
  single-host diagnostic aid; collecting from *other* machines is fleet
  monitoring and breaks the one-machine boundary in
  [`brainstorm.md`](brainstorm.md).
