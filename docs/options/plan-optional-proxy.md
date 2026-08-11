# Plan: optional reverse proxy with automatic HTTPS — a host-wide web front door (`Caddy`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that installs a
single, host-wide **reverse proxy** — **Caddy** — that terminates TLS
and routes to the loopback-bound web services on the machine, with
**automatic HTTPS** for every opt-in component on one shared domain.
This is the worked-out promotion of candidate **D** ("Reverse proxy +
automatic HTTPS", `ZOMBIE_INSTALL_PROXY`, ★★) from
[`brainstorm.md`](brainstorm.md): with the data-safety tier
([`plan-optional-backup.md`](plan-optional-backup.md),
[`plan-optional-snapshots.md`](plan-optional-snapshots.md)) and the
self-knowledge tier
([`plan-optional-observability.md`](plan-optional-observability.md),
[`plan-optional-inventory.md`](plan-optional-inventory.md)) already
specified, the reverse proxy is the natural next first mover because it
**unlocks the whole web-app tier** (E) and is the front door many other
candidates — observability's Grafana, a wiki, Nextcloud — would
otherwise each have to build for themselves.

The capability follows the same shape as the existing optional
components (Tailscale, and the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md)):
off by default, toggled by an environment variable, surfaced in the
interactive parameter review, honoured in the dry-run plan, recorded in
the receipt, idempotent on re-run, gated through the policy/audit model,
verifiable by `verify`/`doctor`/`repair`, and reversible by
`uninstall.sh`. It **generalises** the per-service Caddy idea the
Forgejo server plan sketches (`install/08-caddy-web-server.md`) and the
per-stack front door the observability plan describes
(`ZOMBIE_OBSERVABILITY_WEB`) into **one shared proxy** so opt-in web
components stop each shipping their own.

## Why AI assistance is the unlock

Installing Caddy is a single package; *operating* a reverse proxy across
a growing set of services is the classic day-2 burden the brainstorm's
thesis names directly. The hard parts are never the install — they are
the certificate lifecycle (issue, renew, recover when ACME fails),
per-service routing without clobbering an existing route, opening
*exactly* the right firewall holes, and diagnosing a 502 at 11pm when a
backend moved port. A resident administrator that can read the audit
log, run `verify`/`doctor`/`repair`, and explain the next step collapses
exactly this toil: it converges each service's route from one manifest,
answers "is my certificate healthy and when does it renew?" with
evidence from `caddy` and the cert store, and explains a bad-gateway in
plain language instead of leaving the operator to grep logs. The
difficulty here is **genuinely operational**, which is the sharpest
AI-assistance argument in the brainstorm.

## Design principle: one front door, declared as data

The brainstorm's risk note for this candidate is explicit: *exposing
`80`/`443` widens the surface; keep it deliberate and consistent with
the project's Tailscale-only posture.* This plan honours that by
shipping **one** proxy whose entire routing table is **declared as
data**, never hand-edited live, and whose listening posture defaults to
the tailnet:

- **One Caddy, one `Caddyfile`.** A single battle-tested server with
  automatic HTTPS, HTTP/2 and HTTP/3, sane security headers, and a tiny,
  declarative config. No second proxy per stack: components that
  previously fronted themselves (observability's `ZOMBIE_OBSERVABILITY_WEB`)
  **defer to this proxy** when it is installed, per the seam that plan
  already documents.
- **Routes are a manifest, not clicks.** Each opt-in web component
  contributes a route (`subpath` or `subdomain` → a loopback
  `127.0.0.1:PORT` backend) from a small, idempotently converged
  manifest. Re-running never duplicates or reorders a route.
- **Tailnet-bound by default.** Consistent with the project's
  Tailscale-only posture, Caddy listens on `tailscale0` (loopback when
  Tailscale is off). Binding to a routable `0.0.0.0`/public interface is
  an explicit, separately gated opt-in (`ZOMBIE_PROXY_PUBLIC`), never the
  default, and is loudly flagged in the parameter review and receipt.
- **Backends stay on loopback.** The proxy is the *only* component that
  binds a network-facing port; every backend it fronts stays on
  `127.0.0.1`. The proxy never widens a backend's own exposure.

Caddy is **operator-installed by the installer** from apt or a pinned
upstream single-binary release when the option is on; no external
control plane is contacted at runtime beyond the ACME endpoint used to
issue certificates (and even that is skipped in the internal-CA case).

## What "maximum" means

The **minimum** viable proxy is: Caddy installed, bound to the tailnet,
fronting the services already declared on the host over HTTPS using
Caddy's built-in **internal CA** (`tls internal`), with a `verify` check
that Caddy is active and each declared route answers. A **maximum** role
rounds that out, each piece an independently overridable sub-flag under a
`ZOMBIE_PROXY_PROFILE=minimum|maximum` meta-flag (mirroring the Forgejo,
backup and observability plans' profile flag):

- **Public ACME certificates** — `ZOMBIE_PROXY_ACME`. When a routable
  `PROXY_DOMAIN` is supplied, obtain/renew real Let's Encrypt (or
  operator-configured ACME) certificates instead of the internal CA. Off
  in `minimum` (internal CA on the tailnet), on in `maximum`.
- **Security headers + hardening** — `ZOMBIE_PROXY_HARDEN`. A curated
  security-header set (HSTS where a public cert is used, sane referrer/
  content-type/frame defaults), request-size limits, and basic per-route
  rate limiting. On in `maximum`.
- **Route discovery for opt-in components** —
  `ZOMBIE_PROXY_ROUTE_SERVICES`. When another optional component exposes
  a loopback web port (e.g. observability's Grafana), converge a route
  for it from a small manifest rather than hand-editing the `Caddyfile`.
  On in `maximum`.
- **Access logging** — structured Caddy access logs to the journal (or a
  rotated file under the project's logrotate rules) so the agent can
  triage a 502 or an unexpected client. On in `maximum`, with a
  retention default so the log cannot grow without bound.

The maximum profile is therefore the minimum **plus** public ACME, the
hardened header/rate-limit set, route discovery, and access logging,
reusing the same single-Caddy-and-`Caddyfile` shape. Public exposure
(`ZOMBIE_PROXY_PUBLIC`) is **not** part of `maximum`: it is an orthogonal,
explicitly dangerous opt-in that stays off in both profiles.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_PROXY=0|1` — master switch (default `0`). When `1`,
  install and configure the host-wide reverse proxy.
- `ZOMBIE_PROXY_PROFILE=minimum|maximum` — switches the ACME/harden/
  route-discovery/logging sub-flags on together (default `minimum`); each
  remains independently overridable.
- `PROXY_DOMAIN` — the base hostname Caddy serves on (a tailnet MagicDNS
  name in the default tailnet-bound mode, or a routable FQDN when public
  ACME is enabled). Required only when `ZOMBIE_PROXY_ACME=1`; when absent,
  Caddy serves its internal CA on the tailnet address.
- `ZOMBIE_PROXY_ACME=0|1` — issue public ACME certificates for
  `PROXY_DOMAIN` instead of the internal CA (default follows the
  profile). Implies the host can reach the ACME endpoint.
- `PROXY_ACME_EMAIL` — contact address for the ACME account when
  `ZOMBIE_PROXY_ACME=1`; validated as an email when present.
- `ZOMBIE_PROXY_PUBLIC=0|1` — **dangerous, default `0`.** Bind Caddy to a
  routable interface (`0.0.0.0`) and open `80`/`443` to the world instead
  of restricting them to `tailscale0`. Off in both profiles; enabling it
  is loudly surfaced in the review and receipt.
- `ZOMBIE_PROXY_HARDEN=0|1` — enable the curated security-header,
  request-size and rate-limit set (default follows the profile).
- `ZOMBIE_PROXY_ROUTE_SERVICES=0|1` — converge routes for other enabled
  optional components from a manifest (default follows the profile).
- `ZOMBIE_PROXY_ACCESS_LOG=0|1` and `ZOMBIE_PROXY_LOG_RETENTION` —
  enable structured access logging and bound its retention (default
  conservative, e.g. `14d`) so logs cannot sprawl.
- `CADDY_VERSION` — optional pin; the default resolves the distribution
  package or the upstream release, recording the resolved value in the
  receipt (mirroring how `FORGEJO_VERSION` and the observability plan's
  `*_VERSION` pins are handled).

The proxy holds **no operator secrets** of its own beyond the ACME
account key and the issued certificates/private keys, which Caddy
manages in its own root-owned data dir (e.g. `/var/lib/caddy`, mode
`700`). Those are generated at issue time, never committed or printed,
and surfaced in the receipt only as a set/unset fingerprint (cert
present for domain, renews on date). Confirm the CI secret-scan patterns
(`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not tripped; do not add example
secrets or private keys to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: package/binary
   presence (`caddy version`), the rendered `Caddyfile` and any route
   fragments, the systemd unit, the UFW rules, and the data dir. Re-
   running converges with no errors, no duplicate routes, and no
   duplicate firewall rules. Use `caddy validate` (or `caddy fmt
   --diff`) before reloading so a bad config never replaces a good one.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone. When `ZOMBIE_PROXY_ACME=1` and
   `PROXY_DOMAIN` (or `PROXY_ACME_EMAIL` where the ACME provider needs
   it) is missing in non-interactive mode, exit `64`, consistent with
   `validate_noninteractive()`. When the proxy is off, requirements are
   unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. Caddy runs as a system service without the agent, but anything
   the chat agent may later be asked to drive — reloading Caddy, adding/
   removing a route, inspecting a certificate's expiry, triggering a
   renewal — must be classified in `payload/etc/policy.yaml`
   `sudo_allow_list` and described in `docs/ARCHITECTURE.md`. Reads
   (config/cert/route inspection, `caddy validate`) are a low-risk class;
   `caddy reload`/route changes/UFW edits are a `system_change` class.
4. **No new runtime deps beyond what the installer installs.** Caddy is
   an apt package (or a pinned single-binary release) installed by the
   installer **only when the option is on**, which is permitted; do not
   add language-level dependencies. Reuse existing `curl_get`/retry and
   architecture-mapping helpers if fetching a binary release.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation", "minimise",
   "recognised").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_PROXY`, the `ZOMBIE_PROXY_*` flags, `PROXY_DOMAIN`,
  `PROXY_ACME_EMAIL`, `ZOMBIE_PROXY_LOG_RETENTION`, and `CADDY_VERSION`
  to the defaults/derivation block alongside the other `ZOMBIE_*`
  settings, with conservative defaults (`0`, profile `minimum`, internal
  CA, tailnet-bound, public off).
- Add validators (a profile enum check, a domain-syntax check, an email
  check for `PROXY_ACME_EMAIL`, a retention-string sanity check, the
  "`PROXY_DOMAIN` required when `ZOMBIE_PROXY_ACME=1`" rule, and a loud
  guard so `ZOMBIE_PROXY_PUBLIC=1` is only honoured when the operator has
  explicitly set it) and wire them into `validate_config()` so an invalid
  value is rejected before any host change.
- Extend `validate_noninteractive()` to exit `64` when ACME is enabled
  but `PROXY_DOMAIN`/`PROXY_ACME_EMAIL` are missing.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in proxy example (interactive and `ZOMBIE_NONINTERACTIVE=1`),
  including the internal-CA tailnet default and the public-ACME variant.

### 2. Interactive parameter review

- Add a "Reverse proxy (Caddy)" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, the profile, the base domain (host
  only), the cert mode (internal CA vs public ACME), and — prominently —
  whether `ZOMBIE_PROXY_PUBLIC` is on. Mirror how Tailscale and Forgejo
  render. Never print any key material.
- Add a `_toggle_proxy()` editor (and nested profile/domain/ACME/public
  editors) and a new menu entry in `review_parameters()`. Append as the
  next index to minimise churn, and update the range hint and the
  "Unrecognised choice" message accordingly. The public-exposure editor
  must require an explicit confirmation step.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when the proxy is enabled, the plan lists the install/config/route/
  firewall/unit steps (and the ACME/harden/logging steps for `maximum`),
  calls out the listening interface, and when disabled it says nothing —
  keeping the default output unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_PROXY != 1`. Place them after the workspace/data and (if
present) Tailscale sections so the bind interface already exists, and
after any optional web components so their loopback ports are known:

- `section "Install reverse proxy"` — `apt_install` (or fetch and
  `install -m 0755` a pinned arch-matched release of) Caddy, guarded by a
  `caddy version` probe. Create the `caddy` system user and data dir
  (`/var/lib/caddy`, `700`) if absent.
- `section "Write proxy config"` — render a base `Caddyfile` (and a
  `conf.d`-style fragment dir for per-service routes) from templates:
  the global options block (admin endpoint on loopback only, ACME vs
  `tls internal`, optional access log with retention), and a route for
  each declared loopback backend. Run `caddy validate` before writing the
  active config so a re-render never installs a broken `Caddyfile`. Bind
  the listener to `tailscale0` (loopback when Tailscale is off) unless
  `ZOMBIE_PROXY_PUBLIC=1`.
- `section "Route opt-in components"` *(route discovery only)* — when
  `ZOMBIE_PROXY_ROUTE_SERVICES=1`, converge a route fragment for each
  enabled optional component that exposes a loopback web port, from a
  small manifest; re-running never duplicates a route.
- `section "Enable reverse proxy"` — install and `enable --now` the Caddy
  unit via the existing `render_unit()` pattern; `daemon-reload` once;
  `caddy reload` (not restart) on config change so in-flight connections
  drain.
- `section "Proxy firewall"` — add UFW rules restricting `443` (and `80`
  for the ACME challenge/redirect) to `tailscale0`, consistent with the
  Tailscale-only posture. Only when `ZOMBIE_PROXY_PUBLIC=1` open them to
  any interface, and emit a `[!]` warning when doing so. Idempotent: never
  add a duplicate rule.

### 5. systemd unit

- Add `payload/systemd/ubuntu-zombie-caddy.service` (or reuse/extend the
  Forgejo plan's Caddy unit pattern so there is a single shared unit),
  header style matching existing units. Run Caddy as its own
  unprivileged system user with `AmbientCapabilities=CAP_NET_BIND_SERVICE`
  so it can bind `80`/`443` without full root, a private data dir, and
  hardening consistent with the documented rationale for the existing
  units. Reload (not restart) on config change.

### 6. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add proxy checks (only
  when enabled): Caddy present and reporting a version; the `Caddyfile`
  valid (`caddy validate`) with correct ownership/modes; the service
  `enabled`/`active`; the listener on the expected interface (and **not**
  on a routable interface unless `ZOMBIE_PROXY_PUBLIC=1`); each declared
  route answering through the proxy; and, for `maximum`/ACME, the
  certificate present and not near expiry. Use `[ok]/[!]/[x]/[~]` glyphs
  and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for common failure
  modes: a backend down (502), a port clash on `80`/`443`, an ACME/cert
  issuance or renewal failure (rate-limit, DNS, reachability), a route
  pointing at a moved backend port, and an accidental public bind. Each
  with the obvious revert.
- Extend `cmd_repair()` to re-validate and re-render the `Caddyfile`,
  re-assert config/data ownership and modes, reload Caddy, re-add a
  missing UFW rule, and re-enable the unit if disabled — never to delete
  certificates or force a re-issue that could trip ACME rate limits.

### 7. Receipt

- Record the proxy selection, profile, base domain/host (never key
  material), cert mode (internal CA vs ACME), listening interface, the
  **public-exposure flag prominently**, access-log on/off + retention,
  and the resolved `CADDY_VERSION` in `write_receipt_start`/
  `write_receipt_finish`. Record the certificate only as a
  present/renews-on fingerprint.

### 8. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: stop/disable the Caddy unit, remove the unit, the
  rendered `Caddyfile` and route fragments, drop the UFW rules, remove
  the `caddy` system user, and `daemon-reload`. Removal of Caddy's
  **data dir** (the issued certificates and ACME account key) is the
  operator's data: delete it only behind the destructive confirmation
  phrase, never as the default path, and warn that re-issuing later may
  hit ACME rate limits.

### 9. Policy and docs

- `payload/etc/policy.yaml`: add the read-only verbs (`caddy validate`,
  config/cert/route inspection) at a low-risk class and the
  `caddy reload`/route-change/UFW-edit verbs at the `system_change`
  class; describe both in `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  tailnet-bound-by-default model, the internal-CA-vs-public-ACME modes,
  and the dangerous `ZOMBIE_PROXY_PUBLIC` opt-in.
- `docs/ARCHITECTURE.md`: describe the optional reverse-proxy component,
  its trust boundary (one tailnet-bound front door; backends stay on
  loopback), the seam by which other components defer their own front
  door to it, and the new policy entries.
- `README.md`: note the optional component and any new flag/subcommand.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 10. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_PROXY=1` (and, for the ACME
  path, a dummy `PROXY_DOMAIN`/`PROXY_ACME_EMAIL`) without touching the
  host (extend the existing `noninteractive`/`subcommands` cases).
- Assert that `ZOMBIE_PROXY_ACME=1` with no `PROXY_DOMAIN` under
  `ZOMBIE_NONINTERACTIVE=1` exits `64`.
- Add a "standards" assertion that the new section names and the Caddy
  unit exist, that the rendered config binds to the tailnet/loopback (and
  not a routable interface) unless the public flag is set, and that
  British spelling / status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including the new unit and any `payload/bin` helpers.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  `caddy validate`-before-reload guard and the no-duplicate-route /
  no-duplicate-UFW-rule guards.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host, start a listening service, and may contact a live ACME endpoint.
  All verification here is static (`lint`/`test`/`package`) plus dry-run
  reasoning. End-to-end routing, certificate issuance, and the firewall
  posture must be validated by a human on a disposable Ubuntu Desktop LTS
  VM.
- **Public exposure is the sharp edge.** The default is tailnet-only with
  an internal CA. `ZOMBIE_PROXY_PUBLIC` is an explicit, loudly flagged
  opt-in; binding `0.0.0.0` and opening `80`/`443` to the world is the
  single riskiest thing this component can do and must never be the
  default, must never be implied by `maximum`, and must be obvious in the
  review and receipt.
- **One proxy, not many.** This component exists so opt-in web stacks
  stop each shipping their own front door; running a second proxy beside
  it (e.g. leaving `ZOMBIE_OBSERVABILITY_WEB` independent when the host
  proxy is present) is a misconfiguration the plans should steer away
  from via the documented deferral seam.
- **No layer-4/load-balancing or multi-host routing.** This is a single-
  host front door for *this* machine's loopback services; proxying to or
  balancing across *other* machines is fleet networking and breaks the
  one-machine boundary in [`brainstorm.md`](brainstorm.md).
- **No authentication gateway / SSO here.** Per-route auth and a shared
  login belong to the separate `ZOMBIE_INSTALL_SSO` candidate; this plan
  terminates TLS and routes, it does not become an identity provider.
