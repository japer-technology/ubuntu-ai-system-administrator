# Plan: optional Forgejo Server with Local Runner (Forgejo + PostgreSQL) install

> **Status: IMPLEMENTED** (first shipped optional component). The
> as-built behaviour is documented in
> [`docs/CONFIGURATION.md`](../docs/CONFIGURATION.md#optional-components-ubuntu-zombie--options)
> and [`docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md#optional-components).
> Key deltas from the original draft below, which was written against an
> older baseline:
>
> - There is no UFW/Docker/Tailscale baseline any more, so the
>   implementation introduced the shared optional-component mechanism
>   itself (flags, validators, the `9) Options` review sub-menu,
>   dry-run/banner/receipt stanzas, and a skip-aware phase counter) with
>   Forgejo as its first consumer.
> - **Exposure is normal network access**: Forgejo listens on all
>   interfaces (`HTTP_ADDR = 0.0.0.0`, default port `3000`) so people on
>   the LAN can use the forge — unlike the loopback-only chat UI. There
>   is no firewall step because the baseline manages no firewall.
> - The runner is the **standard Docker executor**: the runner opt-in
>   installs `docker.io` itself and registers with labels defaulting to
>   `ubuntu-latest:docker://node:20-bookworm`. The runner runs as the
>   `forgejo-runner` system user (not `runner`).
> - Binaries are downloaded from `codeberg.org` and verified against the
>   published SHA-256 sums; `FORGEJO_VERSION`/`FORGEJO_RUNNER_VERSION`
>   pin releases, and the resolved version is recorded in the receipt.
> - The Forgejo units ship in `payload/systemd/` and are hardened
>   (`NoNewPrivileges`, `ProtectSystem=full`, scoped `ReadWritePaths`) —
>   the opposite of the deliberately unsandboxed chat unit.
> - The "maximum" profile (Caddy, fail2ban, Restic, metrics, SMTP)
>   remains deferred to the dedicated proxy/remote/backup component
>   plans, as argued below. Git LFS is included in the minimum build.

## Goal

Add an **opt-in** capability to `scripts/install.sh` that, in addition to
the standard Ubuntu Zombie baseline, installs a self-hosted **Forgejo**
server backed by **PostgreSQL** and — against upstream's recommendation,
but explicitly requested here — a **Forgejo Actions runner on the same
host**.

The capability follows the same shape as the existing optional
component (Tailscale): off by default, toggled by an environment
variable, surfaced in the interactive parameter review, honoured in the
dry-run plan, recorded in the receipt, idempotent on re-run, gated
through the policy/audit model, verifiable, and reversible by
`uninstall.sh`. It mirrors the behaviour of the Forgejo-Society
`easy-install/` scripts
(`FORGEJO-SOCIETY-INSTALLATION/easy-install/install.sh` and
`install-runner.sh`), which use **PostgreSQL 16** rather than SQLite.

## Design principle: a general "optional software" mechanism

The problem statement asks for the ability to "define other software to
install" with Forgejo as the first such component. So the plan
introduces a small, reusable opt-in pattern rather than hard-wiring
Forgejo alone:

- A new family of `ZOMBIE_INSTALL_<COMPONENT>=0|1` opt-in flags
  (defaulting to `0`), following the precedent set by
  `ZOMBIE_SKIP_TAILSCALE`. Forgejo is the first consumer
  (`ZOMBIE_INSTALL_FORGEJO`, plus `ZOMBIE_INSTALL_FORGEJO_RUNNER`).
- Each optional component is implemented as one or more guarded
  `section "..."` blocks that early-return when their flag is off, so
  the default install is byte-for-byte unchanged when nothing is opted
  in.
- Each component registers itself in the parameter table, dry-run plan,
  receipt, verify checks, and uninstall — the touch-points enumerated
  below. Future components reuse the same checklist.

Keep the first cut focused on Forgejo; only generalise the helper
plumbing as far as Forgejo actually needs it, to avoid speculative
abstraction.

## What "maximum" means: the full forge-server software stack

The first cut above mirrors `easy-install/` — the *minimum* viable
forge (Forgejo + PostgreSQL, plus an optional co-located runner). A
**maximum** Forgejo server is the forge-server role described by the
Forgejo-Society `scripts/` installer and `install/` library, hardened
and observable rather than merely functional. The
`install/00-index.md` "Forge server" install order enumerates the
target stack, and the [Forgejo admin docs](https://forgejo.org/docs/latest/admin)
list the supporting services a production instance is expected to
integrate. The additional software, beyond the Forgejo binary and its
PostgreSQL database, is:

### Already provided by the Ubuntu Zombie baseline (reuse, do not re-add)

- **UFW firewall** — the baseline already manages UFW; the Forgejo
  sections add rules to the existing instance rather than installing
  it. (`install/02-ufw-firewall.md`.)
- **Docker Engine** — the baseline installs it; the optional runner
  reuses it instead of pulling a second container runtime.
  (`install/04-docker-engine.md`.)

### New components for a maximum forge server

Each is its own opt-in `ZOMBIE_INSTALL_*` flag (defaulting to `0`),
following the same per-component checklist (parameter table, dry-run
plan, receipt, verify/doctor/repair, uninstall, policy, docs) the
Forgejo flag uses. Order them by the forge-server install sequence so
prerequisites land first.

- **Caddy web server** (reverse proxy + automatic HTTPS) —
  `ZOMBIE_INSTALL_FORGEJO_CADDY`. Terminates TLS for a public
  `FORGE_DOMAIN`, fronts Forgejo on loopback, and obtains/renews
  Let's Encrypt certificates automatically. When enabled, Forgejo's
  `ROOT_URL`/`HTTP_ADDR` bind to `127.0.0.1` and only Caddy's
  `80`/`443` are exposed; mutually exclusive with the plain
  `FORGEJO_HTTP_PORT` exposure. (`install/08-caddy-web-server.md`;
  admin docs "Reverse proxies".) This is the single biggest gap
  between the minimum and maximum builds.
- **fail2ban** (brute-force protection) —
  `ZOMBIE_INSTALL_FORGEJO_FAIL2BAN`. Ship a Forgejo jail/filter that
  reads the Forgejo log and bans IPs after repeated failed logins.
  (`install/03-fail2ban.md`; admin docs "Fail2ban setup".)
- **Restic backup** (off-host backups) —
  `ZOMBIE_INSTALL_FORGEJO_BACKUP`. Scheduled `restic` snapshots of
  `/var/lib/forgejo`, `/etc/forgejo/app.ini`, and a `pg_dump` of the
  database to an operator-supplied repository, via a systemd timer.
  Restic's repository/credentials are generated/required env, never
  committed. (`install/05-restic-backup.md`.)
- **Prometheus Node Exporter** (host metrics) —
  `ZOMBIE_INSTALL_FORGEJO_METRICS`. Exposes host metrics for
  monitoring; bind to loopback or `tailscale0` only, consistent with
  the project's Tailscale-only posture. Optionally enable Forgejo's
  own built-in `/metrics` endpoint guarded by a bearer token in
  `app.ini`. (`install/06-prometheus-node-exporter.md`.)
- **Git LFS** (large-file storage) — install `git-lfs` and set
  `[server] LFS_START_SERVER = true` in `app.ini` so the forge serves
  large binaries. This is light enough to fold into the core Forgejo
  prerequisites rather than a separate flag. (Admin docs "Git LFS
  setup".)

### Optional integrations the admin docs recommend at scale

These are worth listing in the plan as deliberately deferred, with a
documented rationale, so "maximum" is understood as the hardened
single-host forge rather than a multi-node cluster:

- **Outbound mailer (SMTP)** — required for notifications, password
  resets, and email-based sign-up. A maximum build should at least
  expose `FORGEJO_SMTP_*` env to configure `app.ini`'s `[mailer]`
  block against an operator-supplied relay; running a local Postfix
  is out of scope. (Admin docs "Mail templates"/"Incoming email".)
- **Search indexer** — Forgejo's default in-process Bleve indexer is
  adequate for a single host; Elasticsearch/Meilisearch are only
  needed for very large code search and stay out of scope. Document
  enabling repository/issue indexing in `app.ini` as the maximum
  single-host setting. (Admin docs "Repository indexer".)
- **Redis for cache/session/queue** — Forgejo defaults (in-memory
  cache, file session, level queue) are fine on one host. Redis only
  pays off across nodes, so it is deferred; note it as the scale-out
  upgrade path. (Admin docs "Config cheat sheet": `[cache]`,
  `[session]`, `[queue]`.)

The maximum profile is therefore the minimum profile **plus** Caddy +
HTTPS, fail2ban, Restic backups, Node Exporter metrics, Git LFS, and a
configurable SMTP mailer — reusing the baseline's UFW and Docker. A
convenience meta-flag (e.g. `ZOMBIE_INSTALL_FORGEJO_PROFILE=minimum|
maximum`) can switch the component flags on together while leaving
each independently overridable.

## Behaviour and options

New environment variables (document them all in
`docs/CONFIGURATION.md` and the `usage()` env block in
`scripts/install.sh`):

- `ZOMBIE_INSTALL_FORGEJO=0|1` — master switch (default `0`). When `1`,
  install Forgejo + PostgreSQL.
- `ZOMBIE_INSTALL_FORGEJO_RUNNER=0|1` — also install and register a
  local Actions runner (default `0`; only meaningful when Forgejo is
  enabled). Document the co-location caveat that upstream advises
  against running the runner on the forge host.
- `FORGEJO_HTTP_PORT` — Forgejo HTTP port (default `3000`).
- `FORGEJO_ADMIN_USER` / `FORGEJO_ADMIN_EMAIL` — initial admin account
  (sensible defaults; password auto-generated).
- `FORGEJO_DB_NAME` / `FORGEJO_DB_USER` — PostgreSQL database/role
  (default `forgejo`/`forgejo`; password auto-generated).
- `FORGEJO_VERSION` — optional pin; default resolves the latest release
  tag from `codeberg.org` (record the resolved value, mirroring how the
  Node bridge pins are handled).
- `FORGEJO_RUNNER_LABELS` — runner labels (default maps `ubuntu-latest`
  to the host, as `easy-install/install-runner.sh` does).

Generated secrets (DB password, admin password, `SECRET_KEY`,
`INTERNAL_TOKEN`, `JWT_SECRET`, runner registration token) are created
at install time and **never** committed or printed into the repo. They
are written only to root-owned files on the target host
(`/etc/forgejo/app.ini`, mode `640`, owner `root:git`) and surfaced to
the operator via the existing receipt mechanism as set/unset flags or
fingerprints — not plaintext. Confirm the CI secret-scan patterns
(`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not tripped; do not add example
secrets to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: package
   presence, `git` system user, `/usr/local/bin/forgejo`,
   `/etc/forgejo`, `/var/lib/forgejo`, the PostgreSQL role/database
   (the upstream script's `pg_roles`/`pg_database` guards), the systemd
   units, and the runner registration. Re-running converges with no
   errors and no duplicate firewall rules.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone (no prompts). Decide and document
   whether any new required input exists in non-interactive mode; if so,
   exit `64` when missing, consistent with `validate_noninteractive()`.
   Forgejo should need no new required input (all values default or are
   generated), so the existing SSH-key/VNC requirements are unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. Extend `payload/etc/policy.yaml` `sudo_allow_list` with the new
   privileged programs the agent may later be asked to drive
   (`postgres`/`psql`, `forgejo`, `forgejo-runner`, and `adduser`/
   `useradd` if not already covered) at `system_change`, and document
   them in `docs/ARCHITECTURE.md`. The installer itself runs as root, but
   anything the chat agent might invoke post-install must be classified.
4. **No new runtime deps beyond what the installer installs.** New apt
   packages (`postgresql`, `postgresql-contrib`, `git-lfs`, `xz-utils`,
   etc.) are installed by the installer when the option is on, which is
   permitted; do not add language-level dependencies. The runner reuses
   the Docker Engine the baseline already installs rather than pulling a
   second container runtime.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`;
   checklist rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add the new `ZOMBIE_INSTALL_FORGEJO*` and `FORGEJO_*` variables to the
  defaults/derivation block alongside the other `ZOMBIE_*` settings, with
  conservative defaults (`0`, port `3000`, etc.).
- Add validators (reuse `is_valid_tcp_port`, add a small Forgejo
  username/db-name check) and wire them into `validate_config()` so an
  invalid port or name is rejected before any host change.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in Forgejo example (interactive and `ZOMBIE_NONINTERACTIVE=1`).

### 2. Interactive parameter review

- Add a "Forgejo server" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, port + admin user + runner
  on/off (mirroring how Tailscale renders at item 6).
- Add a `_toggle_forgejo()` (and nested runner toggle) editor and a new
  menu entry in `review_parameters()`. Renumber the menu and update the
  "[1-11]" hint and the "Unrecognised choice" message accordingly, or
  append as the next index to minimise churn.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary `cat`
  block so that when Forgejo is enabled the plan lists the Forgejo and
  (optionally) runner steps, and when disabled it says nothing — keeping
  the default output unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, placed after Docker Engine (the runner
depends on it) and before/around the chat-service deployment. Each block
returns early when `ZOMBIE_INSTALL_FORGEJO != 1`. Model the logic on
`easy-install/install.sh`:

- `section "Install Forgejo prerequisites"` — `apt_install git git-lfs
  postgresql postgresql-contrib openssl xz-utils` (only the packages not
  already present from the baseline).
- `section "Create git system user"` — idempotent `adduser --system`
  guarded by `id git`.
- `section "Install Forgejo binary"` — resolve `FORGEJO_VERSION`
  (latest from codeberg API unless pinned), download the arch-matched
  release, `install -m 0755` to `/usr/local/bin/forgejo`, skip download
  if the target version is already installed. Reuse `curl_get`/retry
  helpers and architecture mapping like the Node bridge install.
- `section "Create Forgejo directories"` — `/var/lib/forgejo`
  (`git:git`, `750`) and `/etc/forgejo` (`root:git`, `750`), idempotent.
  Only `app.ini` is temporarily group-writable while the stopped service's
  one-shot migration command may persist generated settings.
- `section "Configure PostgreSQL for Forgejo"` — `systemctl enable
  --now postgresql`; create role + database only if absent (the
  upstream `DO $$ ... pg_roles`/`pg_database` guards); generate the DB
  password once and reuse it if `app.ini` already exists so re-runs do
  not desync the credential.
- `section "Write Forgejo configuration"` — generate the three secrets
  via `forgejo generate secret`, render `/etc/forgejo/app.ini`
  (`DB_TYPE = postgres`, `INSTALL_LOCK = true`, root URL, port), owner
  `root:git`, mode `640`. Make rendering idempotent (only (re)write when
  content/inputs change), echoing the `render_unit()` pattern.
- `section "Enable Forgejo service"` — install a `forgejo.service`
  systemd unit (prefer shipping our own unit under `payload/systemd/`
  rather than downloading upstream's, so it is reviewable and version
  controlled), `daemon-reload`, `enable --now`, then `forgejo migrate`
  and admin-user creation guarded so they run once.
- `section "Firewall for Forgejo"` — add a UFW rule for the HTTP port.
  Decide the exposure policy deliberately: to match the project's
  Tailscale-only posture, restrict the Forgejo port to `tailscale0`
  when Tailscale is enabled, otherwise loopback or all-interface per an
  explicit, documented choice. Make rule add/remove idempotent like the
  existing SSH rule handling.

### 5. Local runner (opt-in within the opt-in)

Guard on `ZOMBIE_INSTALL_FORGEJO_RUNNER == 1`. Model on
`easy-install/install-runner.sh` but reuse the baseline Docker Engine:

- `section "Install Forgejo runner"` — create a `runner` system user in
  the `docker` group (idempotent); download the arch-matched
  `forgejo-runner` release to `/usr/local/bin`.
- `section "Register Forgejo runner"` — generate a registration token
  from the just-installed forge (`forgejo forgejo-cli actions
  register` / the runner secret path the upstream scripts use), write
  `config.yml`, register against `127.0.0.1:${FORGEJO_HTTP_PORT}`, patch
  `.runner` labels so `ubuntu-latest` jobs match, install a systemd
  unit, `enable --now`. All steps guarded so re-runs do not
  double-register.
- Add a visible warning (`warn`) that co-locating the runner with the
  forge is contrary to upstream guidance and is enabled deliberately.

### 6. systemd units

- Add `payload/systemd/forgejo.service` and
  `payload/systemd/forgejo-runner.service` (bash shebang/header style
  matching existing units). Keep hardening consistent with the
  documented rationale for the chat unit; do not over-restrict in a way
  that breaks Forgejo's need to write `/var/lib/forgejo`.

### 7. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add Forgejo checks (only
  when enabled): binary present and reports a version, `forgejo.service`
  active, PostgreSQL reachable and the `forgejo` DB present, HTTP port
  answering on loopback, and (if applicable) `forgejo-runner.service`
  active and registered. Use the `[ok]/[!]/[x]` glyphs and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for the common Forgejo
  failure modes (port in use, DB auth, migration not run).
- Extend `cmd_repair()` to re-assert Forgejo file ownership/permissions
  and restart the units, mirroring the existing repair actions.

### 8. Receipt

- Record the Forgejo selection, port, admin user, resolved version, and
  runner on/off in `write_receipt_start`/`write_receipt_finish`. Record
  secrets only as "set"/fingerprint, never plaintext.

### 9. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only
  install is untouched: stop/disable `forgejo.service` and
  `forgejo-runner.service`, remove the units, remove
  `/usr/local/bin/forgejo` and `/usr/local/bin/forgejo-runner`,
  `/etc/forgejo`, `/var/lib/forgejo`, drop the PostgreSQL database and
  role, remove the `git` and `runner` system users, remove the UFW
  rule, and `daemon-reload`. Treat database/role drop as `destructive`
  and require the confirmation phrase consistent with the policy model.
  Mirror the upstream `install.sh purge` path.

### 10. Policy and docs

- `payload/etc/policy.yaml`: add the new privileged programs to
  `sudo_allow_list` at `system_change` (see non-negotiable #3).
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  exposure/firewall choice, and the runner co-location caveat.
- `docs/ARCHITECTURE.md`: describe the optional Forgejo component, its
  trust boundary (a network-listening service), and the new policy
  entries.
- `README.md`: note the optional component and, if any new subcommand
  or flag is added, list it in the Subcommands/Flags block.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 11. Tests (`tests/smoke.sh`)

These are non-root, no-network checks, so keep them static:

- Assert the new env vars appear in `usage()`/help and that the
  installer parses `--dry-run` with `ZOMBIE_INSTALL_FORGEJO=1` without
  touching the host (extend the existing `noninteractive`/`subcommands`
  cases).
- Add a "standards" assertion that the new sections and units exist and
  that British spelling / status glyphs are respected.
- If any new subcommand/flag is added, extend the `subcommands` case so
  CI checks parsing.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the
  new option by reasoning through each guarded section.
- Confirm no secrets, screenshots, or local state are staged, and the
  CI secret scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a
  real host. All verification here is static (`lint`/`test`/`package`)
  plus dry-run reasoning. End-to-end Forgejo bring-up must be validated
  by a human on a disposable Ubuntu Desktop LTS VM.
- The **first cut** (the `easy-install/`-shaped minimum) keeps
  HTTPS/reverse-proxy, off-host backups, and metrics out of scope. The
  **maximum** profile described above adds them back as further opt-in
  components (Caddy + HTTPS, Restic, Node Exporter, fail2ban, Git LFS,
  SMTP mailer); deliver the minimum first, then layer the maximum
  components on once the base flow is proven.
- The multi-host production topology, Elasticsearch/Meilisearch search,
  and Redis-backed cache/session/queue remain out of scope even for the
  maximum profile; those belong to the `transition-plan/` rollout, not
  this single-host installer.
- Downloading release binaries from `codeberg.org` adds a network
  dependency at install time; pin `FORGEJO_VERSION` for reproducibility
  where determinism matters and record the resolved value in the
  receipt.
