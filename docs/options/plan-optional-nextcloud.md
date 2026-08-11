# Plan: optional files, sync and docs — Nextcloud (`ZOMBIE_INSTALL_NEXTCLOUD`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that stands up a
single-operator **Nextcloud** instance — files, sync and (optionally)
collaborative docs — on the host, deployed as a curated container stack
on the Docker Engine the baseline already installs, bound to
loopback/tailnet, with PostgreSQL for storage and an agent that owns the
*day-2* upkeep Nextcloud is infamous for. This is the worked-out
promotion of candidate **E** ("Files + sync + docs",
`ZOMBIE_INSTALL_NEXTCLOUD`, ★) from [`brainstorm.md`](brainstorm.md).

Nextcloud is the canonical "I'd love to self-host this but the upkeep
scared me off" application: easy enough to *start*, punishing to *run*
across PHP tuning, database migrations, `occ` maintenance, background
cron, preview generation, and the upgrade treadmill. That gap — install
is easy, operate is hard — is exactly where a resident administrator that
can `verify`/`doctor`/`repair`, read the audit log, and explain the next
step earns its keep.

The capability follows the same shape as the existing optional components
(Tailscale, the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md),
backup, observability and inventory): off by default, toggled by an
environment variable, surfaced in the interactive parameter review,
honoured in the dry-run plan, recorded in the receipt, idempotent on
re-run, gated through the policy/audit model, verifiable by
`verify`/`doctor`/`repair`, and reversible by `uninstall.sh`. Because it
holds irreplaceable operator data it carries a **hard recommendation** to
enable whole-machine backup
([`plan-optional-backup.md`](plan-optional-backup.md)) first.

## Why AI assistance is the unlock

Nextcloud's difficulty was never conceptual — it was the long tail of
operational toil that only shows up *after* the first login. The PHP
memory limit is too low and large uploads fail; APCu/Redis caching is
unconfigured and the admin overview nags; transactional file locking is
off and a sync client corrupts a file; background jobs silently stop and
notifications dry up; a point release needs `occ maintenance:mode` and
`occ upgrade` in the right order; previews eat the disk; the trusted
domains list rejects the tailnet name. Each is a documented, well-trodden
fix — and each is precisely the kind of "diagnose, explain, configure,
repair, operate" loop the MVP already promises.

A resident administrator that can read the container logs, run `occ`
through the policy gate, and explain *why* the admin overview is
complaining turns Nextcloud's notorious upkeep into a conversation:
"large uploads are failing because the PHP upload limit is 2 MB —
shall I raise it to 10 GB and restart?"; "the background job hasn't
run in two days, the cron timer is wedged — here's the fix"; "a point
release is available; I'll snapshot, enable maintenance mode, upgrade,
verify, and report". The agent doing the upgrade *under approval and
audit* is the whole point: the part people dread becomes the part the
machine shepherds.

## Design principle: a curated container stack, not a kitchen sink

The brainstorm's risk note for this candidate is explicit: *data gravity
— back it up (tier A) before enabling.* This plan honours that and the
project boundaries by being a **curated, declared, single-operator**
deployment, never a general hosting platform:

- **Declared as data, converged by code.** The stack is a small,
  enumerated `docker compose` manifest (Nextcloud + PostgreSQL, plus
  Redis and Collabora when enabled) — echoing the
  `ZOMBIE_INSTALL_APPS` manifest idea — so a complex multi-service app is
  a reviewable file, converged idempotently and reversed by
  `uninstall.sh`. No Nextcloud App Store auto-install, no open-ended
  add-ons.
- **One operator, beside not over.** A single admin account for the
  operator; this is **not** multi-user/multi-tenant hosting and must not
  touch the desktop session or existing logins. Group/federation/external
  user back-ends are out of scope.
- **Reuse the baseline, add no new runtime deps.** Build on the Docker
  Engine the installer already provides; the official upstream
  `nextcloud`, `postgres`, `redis` and (optional) `collabora/code`
  images carry PHP and their own runtimes inside the container, so the
  host gains no PHP stack and no third-party host packages.
- **Loopback/tailnet only.** Consistent with the Tailscale-only posture,
  every container port binds to `127.0.0.1`; reachability is via the
  tailnet web front door (below), never a routable `0.0.0.0` bind. This
  is not a public file-sharing server.
- **Avoid the all-in-one foot-gun.** Deliberately **not** Nextcloud AIO:
  its master container wants to own ports `80`/`443` and manage Docker
  itself, which collides with the project's front-door and trust model.
  A plain compose stack we converge keeps the seams visible and the
  policy gate in charge.

## A great web server (the front door)

Nextcloud is only usable if it is *served well* — TLS, HTTP/2, large
request bodies, and the correct `Host`/trusted-domain handling:

- **Tailnet-bound by default.** The Nextcloud container's HTTP port binds
  to `127.0.0.1`; a front door listens only on `tailscale0` (or loopback
  when Tailscale is off). The instance is **never** served plaintext on a
  routable interface.
- **HTTPS by design.** When a `NEXTCLOUD_DOMAIN` on the tailnet is
  supplied, the front door obtains/renews a certificate (`tailscale cert`
  or an operator-supplied internal CA); otherwise it serves the
  built-in internal CA, and the operator trusts the local root once
  (document this trust step). The supplied domain is added to Nextcloud's
  `trusted_domains` and `overwrite.cli.url`/`overwriteprotocol` are set
  so generated links and `occ` URLs are correct behind the proxy.
- **Defer to the host proxy when it exists.** `ZOMBIE_NEXTCLOUD_WEB=1`
  (on in `maximum`) selects a Caddy front door consistent with the
  Forgejo and observability plans' Caddy component; with it off,
  Nextcloud stays strictly on loopback for `ssh -L` access only. When the
  host-wide reverse-proxy candidate (`ZOMBIE_INSTALL_PROXY`) is promoted,
  this stack defers its front door to it rather than running a second
  Caddy — document that seam, exactly as observability does.
- **Right-sized request limits.** The front door and the container agree
  on a generous client-body limit and timeouts so large uploads and sync
  work, with the matching PHP `upload_max_filesize`/`post_max_size` and
  `memory_limit` applied inside the container.

## What "maximum" means

The **minimum** viable Nextcloud is: the `nextcloud` + `postgres`
containers from a converged compose manifest, a generated admin account
and DB credentials in root-owned files, a systemd-driven background cron
(`cron.php` every 5 minutes, the upstream-recommended mode), the PHP
tuning that silences the common admin-overview warnings, loopback
binding, and a `verify` check that the containers are healthy and
`occ status` reports installed and not in maintenance mode. A **maximum**
role rounds that out, each piece an independently overridable sub-flag
under a `ZOMBIE_NEXTCLOUD_PROFILE=minimum|maximum` meta-flag (mirroring
the Forgejo, backup, observability and inventory plans' profile flag):

- **Redis caching + file locking** — `ZOMBIE_NEXTCLOUD_REDIS`. A Redis
  container wired as the memory cache (`memcache.local`/`memcache.locking`
  and `memcache.distributed`) so transactional file locking is on and
  the multi-client corruption foot-gun is closed. Off in `minimum`, on in
  `maximum`.
- **Great web server** — `ZOMBIE_NEXTCLOUD_WEB`. The Caddy + HTTPS front
  door described above. Off in `minimum` (loopback-only), on in
  `maximum`.
- **Collaborative docs** — `ZOMBIE_NEXTCLOUD_OFFICE`. A Collabora Online
  (`collabora/code`) container plus the Nextcloud Office integration, so
  the "docs" half of the candidate is real. Heavier, so it is **opt-in
  within maximum**: off in `minimum`, defaults on under `maximum` only
  when explicitly chosen, and independently overridable.
- **Backup integration** — `ZOMBIE_NEXTCLOUD_BACKUP_HOOK`. When tier-A
  backup is installed, register the Nextcloud data dir and a consistent
  database dump in the backup set, and wrap snapshots with
  `occ maintenance:mode` so the backup is crash-consistent. On in
  `maximum`; a no-op (with a warning) when backup is not installed.
- **Retention/disk hygiene** — sensible preview and trash/version
  retention defaults plus the `doctor` disk-pressure check (below) so the
  data dir does not grow without bound surprises.

The maximum profile is therefore the minimum **plus** Redis-backed
locking, the HTTPS front door, optional Collabora docs, and backup
integration, reusing the same compose-and-store shape. Email
notifications, the App Store, and external storage back-ends are
deliberately deferred — see "Out of scope".

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_NEXTCLOUD=0|1` — master switch (default `0`). When `1`,
  converge the compose stack, secrets, cron timer and (per profile) the
  front door.
- `ZOMBIE_NEXTCLOUD_PROFILE=minimum|maximum` — switches the
  Redis/web/office/backup-hook sub-flags on together (default `minimum`);
  each remains independently overridable.
- `ZOMBIE_NEXTCLOUD_REDIS=0|1` — Redis cache + transactional locking
  (default follows the profile).
- `ZOMBIE_NEXTCLOUD_WEB=0|1` — the Caddy/HTTPS front door (default
  follows the profile).
- `ZOMBIE_NEXTCLOUD_OFFICE=0|1` — Collabora Online docs integration
  (default `0`; opt-in within `maximum`).
- `ZOMBIE_NEXTCLOUD_BACKUP_HOOK=0|1` — register with tier-A backup
  (default follows the profile; no-op with a warning if backup absent).
- `NEXTCLOUD_DOMAIN` — the tailnet hostname for the front door and
  `trusted_domains`; validated as a plausible hostname. Empty means
  loopback-only.
- `NEXTCLOUD_ADMIN_USER` — the single admin account name (sane default,
  e.g. `admin`), validated as a permitted Nextcloud username.
- `NEXTCLOUD_DATA_DIR` — where operator data lives (default under
  `/var/lib/ubuntu-zombie/nextcloud`), validated as an absolute path.

**Generated secrets** land in root-owned files (mode `0600`) and are
surfaced only as set/unset fingerprints in the receipt, never echoed:
the Nextcloud admin password, the PostgreSQL password, the Redis password
(when Redis is on), and the Collabora admin secret (when Office is on).
Reuse the existing secret-generation and `secrets-edit` plumbing; never
write a password to the compose file in plaintext — pass them via an
`--env-file`/Docker secret the compose stack reads. Confirm the CI
secret-scan patterns (`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not tripped
by sample data, and use placeholders like `sk-...` in docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: the data dirs
   and their ownership/mode, the compose manifest and `--env-file`, the
   running containers (`docker compose up -d` converges, it does not
   duplicate), the systemd cron timer, the front-door config, and the
   logrotate rule. The first-run `occ maintenance:install` runs **only**
   when `occ status` shows the instance is not yet installed; re-running
   the installer must never re-install over existing data.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone; the component needs no interactive
   input. Invalid `ZOMBIE_NEXTCLOUD_*`/`NEXTCLOUD_*` values (bad profile,
   bad hostname, non-absolute data dir) are rejected by
   `validate_config()` before any host change. When Nextcloud is off,
   requirements are unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. Anything the chat agent may later be asked to drive —
   running `occ` maintenance/upgrade/repair, putting the instance into or
   out of maintenance mode, restarting a container, reading logs, or
   tuning a config value — must be classified in
   `payload/etc/policy.yaml` and described in `docs/ARCHITECTURE.md`.
   Read-only verbs (`occ status`, log read, `occ` config *get*) are a
   low-risk read-only class; container restart and `occ` config *set* are
   a `system_change` class; **`occ upgrade`, `occ maintenance:repair`,
   `occ db:*`, and any data-touching command are a high-risk
   `system_change`** that snapshots first (tier A) and is never run
   unattended. The agent must never call `docker`/`occ` outside a
   matching policy class.
4. **No new runtime deps beyond what the installer installs.** The host
   gains no PHP/Apache/MySQL packages — everything PHP-side lives inside
   the upstream container images on the existing Docker Engine. The
   installer glue is Bash + `scripts/lib.sh` helpers plus `python3`
   standard library where JSON is needed; pin image tags to specific
   versions (not `latest`) so upgrades are deliberate.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation", "minimise",
   "synchronise", "unrecognised").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_NEXTCLOUD`, the `ZOMBIE_NEXTCLOUD_*` sub-flags, and
  `NEXTCLOUD_DOMAIN`/`NEXTCLOUD_ADMIN_USER`/`NEXTCLOUD_DATA_DIR` to the
  defaults/derivation block alongside the other `ZOMBIE_*` settings, with
  conservative defaults (`0`, profile `minimum`, office `0`, empty
  domain, `admin`, data dir under `/var/lib/ubuntu-zombie/nextcloud`).
- Add validators (profile enum, hostname sanity for the domain, Nextcloud
  username charset, absolute-path check for the data dir) and wire them
  into `validate_config()` so an invalid value is rejected before any
  host change. Validate that Docker is available when the flag is on.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in Nextcloud example (interactive and `ZOMBIE_NONINTERACTIVE=1`),
  including the backup recommendation.

### 2. Interactive parameter review

- Add a "Files + sync + docs (Nextcloud)" row to
  `print_parameter_table()` showing enabled/disabled and, when enabled,
  the profile, the domain (or "loopback only"), and whether Redis, the
  web front door, Office and the backup hook are on. Mirror how
  Tailscale, Forgejo, backup, observability and inventory render.
- Add a `_toggle_nextcloud()` editor (with nested profile/domain/admin/
  data-dir/Redis/web/office/backup-hook editors) and a new menu entry in
  `review_parameters()`. Append as the next index to minimise churn, and
  update the range hint and the "Unrecognised choice" message
  accordingly.
- When the operator enables Nextcloud while backup is **off**, surface a
  prominent `[!]` recommendation to enable tier-A backup first (data
  gravity), without blocking.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when Nextcloud is enabled, the plan lists the data-dir, compose-stack,
  secrets, first-run install, cron-timer and (for the relevant sub-flags)
  Redis/front-door/Office/backup-hook steps; when disabled it says
  nothing — keeping the default output unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_NEXTCLOUD != 1`. Place them after the Docker baseline and
the workspace/data section so the engine and data-dir root already exist:

- `section "Prepare Nextcloud data dirs"` — create the data/db/config
  directories under `NEXTCLOUD_DATA_DIR` (`root:root`, tight modes),
  idempotently; **never** wipe an existing data dir on re-run.
- `section "Write Nextcloud secrets"` — generate the admin/DB/Redis/
  Collabora secrets to root-owned `0600` files (and the compose
  `--env-file`), only when absent, reusing the existing secret plumbing.
- `section "Render Nextcloud stack"` — render the `docker compose`
  manifest (pinned image tags; ports bound to `127.0.0.1`) and supporting
  config from templates via the existing `render_*` pattern.
- `section "Start Nextcloud stack"` — `docker compose up -d` to converge
  the containers; wait for health; then run first-run
  `occ maintenance:install` **only if** `occ status` shows not-installed,
  set `trusted_domains`/`overwrite*`, apply the PHP tuning and (per
  sub-flags) the Redis cache config.
- `section "Enable Nextcloud cron"` — install and `enable --now` the
  `ubuntu-zombie-nextcloud-cron.timer` (every 5 minutes) running
  `cron.php` in the container; set Nextcloud's background-jobs mode to
  `cron`; `daemon-reload` once.
- `section "Enable Nextcloud front door"` (when `ZOMBIE_NEXTCLOUD_WEB=1`)
  — render the Caddy site (or defer to `ZOMBIE_INSTALL_PROXY`),
  tailnet-bound, with the generous client-body limit.
- `section "Enable Nextcloud Office"` (when `ZOMBIE_NEXTCLOUD_OFFICE=1`)
  — add the Collabora container and wire the Office app's WOPI/allow-list
  to the front door host.
- `section "Register Nextcloud backup"` (when
  `ZOMBIE_NEXTCLOUD_BACKUP_HOOK=1`) — add the data dir and a pre-snapshot
  DB-dump + `maintenance:mode` hook to the tier-A backup set; warn and
  skip if backup is not installed.

### 5. Operator/agent helpers (`payload/bin/`)

- `payload/bin/nextcloud-occ` — a thin, ShellCheck-clean wrapper that runs
  `occ` inside the container as the web user, so the agent has one audited
  entry point for status/config/maintenance/upgrade verbs (each mapped to
  a policy class). Best-effort guarding is **not** appropriate here
  (these are deliberate mutating actions); instead fail loudly and
  surface the `occ` exit code.
- `payload/bin/nextcloud-upgrade` — an operator/agent helper that
  encodes the safe upgrade order: snapshot (if tier-A snapshots/backup
  present) → `maintenance:mode --on` → pull pinned image → `occ upgrade`
  → `maintenance:mode --off` → `verify`, narrating each step and aborting
  on the first failure. Keep both bash-`-n` and ShellCheck-clean and
  reuse `scripts/lib.sh` glyphs.

### 6. systemd units

- Add `payload/systemd/ubuntu-zombie-nextcloud-cron.service` (oneshot,
  runs `cron.php` in the container) and
  `ubuntu-zombie-nextcloud-cron.timer` (every 5 minutes,
  `Persistent=true`), header style matching the existing
  `ubuntu-zombie-*.{service,timer}` pairs. The container lifecycle itself
  is managed by `docker compose` (a `restart: unless-stopped` policy);
  document why a compose stack is used rather than per-container units,
  consistent with the documented rationale for the existing units.

### 7. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add Nextcloud checks (only
  when enabled): the data dirs exist with correct ownership/mode; the
  compose stack's containers are running and healthy; `occ status`
  reports installed and **not** in maintenance mode; the cron timer is
  active and last ran recently; the configured caching back-end matches
  the profile; the front door (when on) serves HTTPS on the tailnet; and
  the trusted-domains list contains `NEXTCLOUD_DOMAIN`. Use
  `[ok]/[!]/[x]/[~]` glyphs and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for the well-known
  failure modes: PHP upload/memory limits too low, background job not run
  recently (wedged cron), missing/incorrect trusted domain, Redis not
  reachable so locking is degraded, a **disk-pressure** check on the data
  dir (previews/versions/trash growth), and "an upgrade is pending — run
  `nextcloud-upgrade`".
- Extend `cmd_repair()` to re-assert data-dir ownership/mode, re-render
  the compose/env files, `docker compose up -d` to reconverge, re-enable
  a disabled cron timer, and re-apply the PHP/caching config — **never**
  to delete operator data, drop the database, or re-run the first-run
  install over an existing instance.

### 8. Receipt

- Record the Nextcloud selection, profile, domain (or "loopback only"),
  Redis/web/office/backup-hook on/off, the data-dir path, and the
  set/unset fingerprints of the admin/DB/Redis/Collabora secrets in
  `write_receipt_start`/`write_receipt_finish`. Never write a secret
  value to the receipt.

### 9. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: `docker compose down` (stop/remove containers and the
  app network), remove the compose/env/front-door/logrotate files and the
  cron `service`+`timer`, remove the `payload/bin` helpers, and
  `daemon-reload`. The **data dir, database volume and secrets** are
  irreplaceable operator state: delete them only behind the destructive
  confirmation phrase, never as the default path, and warn that all files
  and the instance are then irreversibly lost. By default, leave the data
  in place and print where it is.

### 10. Policy and docs

- `payload/etc/policy.yaml`: add the read-only verbs (`occ status`, log
  read, config *get*) at a low-risk class; container restart and config
  *set* at a `system_change` class; and `occ upgrade`/`maintenance`/`db`/
  data-touching verbs at a high-risk `system_change` class that requires
  approval. Describe all three tiers in `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  profile model, the front-door/Tailscale binding, the secret files, the
  upgrade helper, and the strong backup recommendation.
- `docs/ARCHITECTURE.md`: describe the optional Nextcloud component, its
  compose-stack shape, trust boundary (loopback/tailnet, single
  operator), how it leans on Docker + the front door + tier-A backup, and
  the new policy entries.
- `README.md`: note the optional component and any new flag/subcommand
  (`nextcloud-occ`, `nextcloud-upgrade`).
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 11. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_NEXTCLOUD=1` (and `=1` with the
  `maximum` profile) without touching the host or contacting Docker
  (extend the existing `noninteractive`/`subcommands` cases).
- Assert the `nextcloud-occ`/`nextcloud-upgrade` helpers pass `bash -n`
  and ShellCheck, and that the upgrade helper performs maintenance-mode
  on/off around `occ upgrade` and aborts on first failure.
- Add a "standards" assertion that the new section names, the compose
  template, the cron unit, the helpers and the policy entries exist; that
  container ports in the template bind to `127.0.0.1` (no `0.0.0.0`);
  that image tags are pinned (no `:latest`); that no secret value is
  written into the compose file; and that British spelling / status
  glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including the new `payload/bin` helpers and units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  install-only-if-not-installed guard, the do-not-wipe-data guard, and
  the compose `up -d` convergence.
- Confirm no secrets, screenshots, or local state are staged; that
  secrets live only in root-owned `0600` files (never the compose file);
  and that the CI secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, `docker compose`,
  or any `/opt/ai-zombie/` helper in the agent environment — these mutate
  a real host and pull images. All verification here is static
  (`lint`/`test`/`package`) plus dry-run reasoning. End-to-end stand-up,
  the first-run install, the upgrade path, and the front door must be
  validated by a human on a disposable Ubuntu Desktop LTS VM.
- **Data gravity is the sharpest edge.** Nextcloud holds irreplaceable
  operator files; enabling it without tier-A backup is a foot-gun. The
  installer recommends backup, uninstall never deletes data by default,
  and `occ upgrade`/data-touching verbs are high-risk and snapshot-first.
- **Single operator, not multi-tenant.** One admin account for the owner;
  user provisioning, group/federation, SSO back-ends and sharing with
  third parties are out of scope — that breaks the one-operator boundary
  in [`brainstorm.md`](brainstorm.md). (Local SSO would defer to the
  `ZOMBIE_INSTALL_SSO` candidate, not be reinvented here.)
- **Curated, not an App Store.** No automatic Nextcloud app installation
  and no open-ended add-ons; the stack is the enumerated compose manifest
  only. Email notifications and external storage back-ends are deferred
  because they need outbound credentials/services the baseline does not
  install.
- **Upgrades are deliberate.** Image tags are pinned and upgrades run
  through `nextcloud-upgrade` (snapshot → maintenance → `occ upgrade` →
  verify); the stack never auto-pulls `latest`, so a breaking release can
  never land unattended.
- **No public exposure.** The instance is loopback/tailnet-bound and never
  bound to a routable interface; turning it into a public file-sharing
  server is out of scope and inconsistent with the Tailscale-only
  posture.
