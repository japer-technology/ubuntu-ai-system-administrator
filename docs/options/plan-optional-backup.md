# Plan: optional whole-machine backup and restore (`restic`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that configures
scheduled, encrypted, off-host **backups** of operator-nominated paths —
and a guarded, operator-driven **restore** — using
[`restic`](https://restic.net) on a systemd timer. This is the
worked-out promotion of candidate **A** ("Whole-machine backup and
restore", `ZOMBIE_INSTALL_BACKUP`) from
[`brainstorm.md`](brainstorm.md): the highest value-to-risk first mover,
and the safety net the stateful application tiers (Forgejo, Nextcloud,
local LLM stores) depend on before they are worth enabling.

The capability follows the same shape as the existing optional
components (Tailscale, and the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md)):
off by default, toggled by an environment variable, surfaced in the
interactive parameter review, honoured in the dry-run plan, recorded in
the receipt, idempotent on re-run, gated through the policy/audit model,
verifiable by `verify`/`doctor`/`repair`, and reversible by
`uninstall.sh`. It generalises the per-service `restic` sketch in the
Forgejo server plan (`install/05-restic-backup.md`) to the whole host.

## Why AI assistance is the unlock

Installing a backup tool is a one-line `apt install`. The reason most
machines have no working backups is the *day-2* burden the brainstorm's
thesis names directly: nobody verifies that snapshots still run, nobody
test-restores, and nobody can read a failed snapshot at 11pm. A resident
administrator that can answer "is my backup healthy?", run a **test
restore into a scratch directory** on request, prune to policy, and
explain a failed run in plain language — all through the policy gate and
audit log — is exactly the "diagnose, explain, operate" loop the MVP
promises. Backup is therefore the cleanest demonstration of the project's
core value, with the smallest new attack surface (an outbound-only
client, no listening service).

## Design principle: a reusable "scheduled maintenance job" pattern

The Forgejo plan introduced the `ZOMBIE_INSTALL_<COMPONENT>=0|1` opt-in
family. This plan adds a complementary, reusable shape: a
**timer-driven maintenance job** that owns a systemd `service`+`timer`
pair, a generated credential, and a small wrapper script under
`payload/bin/`, with no network-listening surface. Keep the first cut
focused on `restic`; only generalise the helper plumbing (timer
rendering, credential file handling) as far as backup actually needs it,
to avoid speculative abstraction. Later timer-driven candidates from the
brainstorm (inventory snapshots, registry GC) can reuse the same shape.

`restic` is chosen over `borg` because it has first-class support for the
widest set of operator-supplied repository backends (local path, SFTP,
S3-compatible object stores, `rest-server`, `rclone`) behind one
`RESTIC_REPOSITORY` string, ships as a single static binary, and encrypts
and deduplicates by default. The repository backend is **operator-
supplied** — this plan never stands up a storage server.

## What "maximum" means

The **minimum** viable backup is: `restic` installed, a repository
initialised from operator-supplied credentials, a daily timer that runs
`backup` over a default path set, and a `verify` check that the last run
succeeded. A **maximum** backup role hardens and rounds that out, each
piece an independently overridable sub-flag under a
`ZOMBIE_BACKUP_PROFILE=minimum|maximum` meta-flag (mirroring the Forgejo
plan's profile flag):

- **Retention/prune policy** — `ZOMBIE_BACKUP_PRUNE`. A second timer runs
  `restic forget --prune` on a `--keep-daily/--keep-weekly/--keep-monthly`
  schedule so the repository does not grow without bound. Off in
  `minimum` (backups accumulate), on in `maximum`.
- **Integrity check** — `ZOMBIE_BACKUP_CHECK`. A periodic
  `restic check [--read-data-subset]` timer that detects repository
  corruption early; the agent can read its result. On in `maximum`.
- **Pre-snapshot database dumps** — `ZOMBIE_BACKUP_DB_DUMP`. When a
  stateful component is present (e.g. the Forgejo PostgreSQL DB), run a
  consistent `pg_dump` into a backup staging dir *before* the snapshot so
  the backup is restorable, not just a copy of live data files. This is
  the explicit seam between this plan and the Forgejo server plan's
  per-service `restic` sketch: the per-service plan can defer its backup
  to this host-wide job when both are enabled.
- **Off-host transport hardening** — bind any backend the agent reaches
  conversationally to the project's Tailscale-only posture where the
  backend is on the tailnet; document that public S3/SFTP endpoints are
  the operator's responsibility.

The maximum profile is therefore the minimum **plus** prune, integrity
check, and pre-snapshot DB dumps, reusing the same single timer-job
shape. Notifications (email on failure) are deliberately deferred — see
"Out of scope" — because they need an outbound mailer the baseline does
not install.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_BACKUP=0|1` — master switch (default `0`). When `1`,
  install and configure `restic` with a daily backup timer.
- `ZOMBIE_BACKUP_PROFILE=minimum|maximum` — switches the prune/check/
  DB-dump sub-flags on together (default `minimum`); each remains
  independently overridable.
- `RESTIC_REPOSITORY` — the backend location string (e.g.
  `sftp:user@host:/srv/restic`, `s3:https://…`, or a local/USB path).
  **Required** when `ZOMBIE_INSTALL_BACKUP=1`: there is no safe default
  for *where* backups go.
- `RESTIC_PASSWORD` — repository encryption passphrase. If unset, the
  installer **generates** a strong one and stores it root-only; if set,
  it is used and stored the same way. Either way it is never printed or
  committed.
- Backend-credential env passthrough (e.g. `AWS_ACCESS_KEY_ID`/
  `AWS_SECRET_ACCESS_KEY` for S3, or an SFTP key path) — accepted from
  env, written only to the root-owned environment file, surfaced in the
  receipt as set/unset fingerprints only.
- `ZOMBIE_BACKUP_PATHS` — colon- or newline-separated include paths
  (default a conservative set: `/etc`, `/home`, `/var/lib/ubuntu-zombie`
  and other operator data, **excluding** caches, `/proc`, `/sys`, `/tmp`,
  and the restic repository itself). Document the default list explicitly.
- `ZOMBIE_BACKUP_EXCLUDE` — additional exclude patterns/globs.
- `ZOMBIE_BACKUP_SCHEDULE` — systemd `OnCalendar` expression for the
  backup timer (default `daily`, with a randomised delay).
- `ZOMBIE_BACKUP_KEEP_DAILY` / `_KEEP_WEEKLY` / `_KEEP_MONTHLY` —
  retention counts used by the prune job (sensible defaults, only applied
  when `ZOMBIE_BACKUP_PRUNE=1`).
- `RESTIC_VERSION` — optional pin; default resolves the latest release
  from the distribution package or the upstream release, recording the
  resolved value in the receipt (mirroring how `FORGEJO_VERSION` and the
  Node bridge pins are handled).

Generated secrets (`RESTIC_PASSWORD` when auto-generated, backend
credentials) are created at install time and **never** committed or
printed into the repo. They are written only to root-owned files on the
target host (e.g. `/etc/ubuntu-zombie/backup.env`, mode `600`, owner
`root:root`, and a separate `restic` password file) and surfaced to the
operator via the receipt as set/unset flags or fingerprints — not
plaintext. Confirm the CI secret-scan patterns (`sk-…`, `sk-ant-…`,
`tskey-auth-…`) are not tripped; do not add example secrets to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: package/binary
   presence (`restic version`), the env/password files, `restic
   snapshots` to detect an already-initialised repository (init only when
   the repo is empty/absent — never re-init over existing snapshots), and
   the systemd `service`/`timer` units. Re-running converges with no
   errors and no duplicate timers.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone. Because there is no safe default
   for `RESTIC_REPOSITORY`, when `ZOMBIE_INSTALL_BACKUP=1` and the
   repository (or a required backend credential) is missing in
   non-interactive mode, exit `64`, consistent with
   `validate_noninteractive()`. When backup is off, requirements are
   unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. The backup *timer* runs as root without the agent, but anything
   the chat agent may later be asked to drive — `restic` (snapshot/check/
   prune and especially **restore**) and `pg_dump`/`psql` for DB dumps —
   must be classified in `payload/etc/policy.yaml` `sudo_allow_list` and
   described in `docs/ARCHITECTURE.md`. **Restore is destructive and must
   be its own, higher-risk policy class** (see implementation step 5); a
   read-only test-restore into a scratch dir is the safe default the
   agent should prefer.
4. **No new runtime deps beyond what the installer installs.** `restic`
   is an apt package (or a pinned single-binary release) installed by the
   installer only when the option is on, which is permitted; do not add
   language-level dependencies. Reuse existing `curl_get`/retry and
   architecture-mapping helpers if fetching a binary release.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation", "minimise").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add the new `ZOMBIE_INSTALL_BACKUP`, `ZOMBIE_BACKUP_*`, and the
  `RESTIC_*` variables to the defaults/derivation block alongside the
  other `ZOMBIE_*` settings, with conservative defaults (`0`, profile
  `minimum`, schedule `daily`, the documented default path set).
- Add validators (a repository-string presence check, an `OnCalendar`
  sanity check, integer checks for the keep-counts, a profile enum check)
  and wire them into `validate_config()` so an invalid value is rejected
  before any host change. Enforce the "repository required when enabled"
  rule here.
- Extend `validate_noninteractive()` to exit `64` when backup is enabled
  but `RESTIC_REPOSITORY` (or a required backend credential) is missing.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in backup example (interactive and `ZOMBIE_NONINTERACTIVE=1`).

### 2. Interactive parameter review

- Add a "Backup (restic)" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, the repository (host/path only —
  never the password), schedule, profile, and prune on/off. Mirror how
  Tailscale renders.
- Add a `_toggle_backup()` editor (and nested profile/schedule/path
  editors) and a new menu entry in `review_parameters()`. Append as the
  next index to minimise churn, and update the range hint and the
  "Unrecognised choice" message accordingly.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when backup is enabled, the plan lists the install/init/timer steps
  (and the prune/check/DB-dump steps for `maximum`), and when disabled it
  says nothing — keeping the default output unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_BACKUP != 1`. Place them after the workspace/data
sections so the paths they back up already exist:

- `section "Install backup tools"` — `apt_install restic` (or fetch and
  `install -m 0755` a pinned arch-matched release if a newer version is
  required), guarded by `restic version`.
- `section "Write backup credentials"` — create
  `/etc/ubuntu-zombie/backup.env` (mode `600`, `root:root`) with
  `RESTIC_REPOSITORY`, the password-file path, and any backend
  credentials; generate `RESTIC_PASSWORD` once and reuse it if the file
  already exists so re-runs never desync the key (losing the passphrase
  loses the backups — make this guard explicit and loud).
- `section "Initialise backup repository"` — run `restic snapshots` to
  detect an existing repo; `restic init` **only** when absent/empty.
  Never re-init. Record the repository id/fingerprint for the receipt.
- `section "Install backup wrapper"` — ship a `payload/bin/backup-run`
  helper (bash shebang/header, ShellCheck-clean, best-effort guards per
  the diagnostics convention) that sources the env file, applies the
  include/exclude lists, and runs `restic backup`; the timer calls this
  rather than embedding a long `ExecStart`.
- `section "Enable backup timer"` — install
  `payload/systemd/ubuntu-zombie-backup.service` (oneshot) and
  `ubuntu-zombie-backup.timer` (`OnCalendar=${ZOMBIE_BACKUP_SCHEDULE}`,
  `Persistent=true`, randomised delay), `daemon-reload`, `enable --now`
  the timer. Render via the existing `render_unit()` pattern.
- `section "Enable backup maintenance"` *(maximum only)* — when
  `ZOMBIE_BACKUP_PRUNE=1`/`ZOMBIE_BACKUP_CHECK=1`, install the prune and
  check service/timer pairs; when `ZOMBIE_BACKUP_DB_DUMP=1` and a known
  stateful component is present, wire a pre-backup `pg_dump` into the
  staging dir consumed by `backup-run`.

### 5. Restore (operator-driven, never scheduled)

Restore is **never** on a timer and **never** automatic. Provide it as an
explicit operator/agent action:

- Ship a `payload/bin/backup-restore` helper that, by default, performs a
  **read-only test restore** of the latest snapshot into a scratch
  directory and reports success — the safe verb the agent should prefer.
- A real, in-place restore must require the destructive **confirmation
  phrase** (consistent with `uninstall.sh`'s destructive steps) and be
  classified as its own high-risk policy class distinct from routine
  backup operations. Document loudly that an in-place restore overwrites
  live data.

### 6. systemd units

- Add `payload/systemd/ubuntu-zombie-backup.{service,timer}` (and the
  prune/check pairs for `maximum`), header style matching existing units.
  The backup service needs broad read access to back up `/etc`, `/home`,
  etc.; keep hardening consistent with the documented rationale for the
  chat unit and do not over-restrict in a way that blocks reading the
  nominated paths.

### 7. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add backup checks (only
  when enabled): `restic` present and reports a version; the env/password
  files exist with correct ownership/modes; the repository is reachable
  (`restic snapshots --last` succeeds); the most recent backup run
  succeeded and is recent enough; the timer is `enabled`/`active`; and,
  for `maximum`, the last `check` passed. Use `[ok]/[!]/[x]/[~]` glyphs
  and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for common failure modes
  (repository unreachable/credential wrong, locked repository needing
  `restic unlock`, disk/quota full at the backend, timer disabled).
- Extend `cmd_repair()` to re-assert env/password file ownership and
  modes, `restic unlock` a stale lock, and re-enable the timer — never to
  re-init or restore.

### 8. Receipt

- Record the backup selection, repository host/path (never the
  password), schedule, profile, resolved `RESTIC_VERSION`, and prune/
  check on/off in `write_receipt_start`/`write_receipt_finish`. Record
  the passphrase and backend credentials only as "set"/fingerprint.

### 9. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: stop/disable the backup, prune, and check timers and
  services, remove the units, remove `payload/bin` helpers from
  `/opt/ai-zombie/`, and `daemon-reload`. **Do not delete the restic
  repository or its snapshots** by default — that is the operator's data
  and lives off-host; only remove the local config. Offer repository
  destruction (`restic forget`/backend wipe) strictly behind the
  destructive confirmation phrase, never as the default path, and warn
  that it is irreversible.

### 10. Policy and docs

- `payload/etc/policy.yaml`: add `restic`, `pg_dump`/`psql` to
  `sudo_allow_list` at the appropriate class for routine ops, and add the
  in-place **restore** action as its own higher-risk/destructive class
  (see non-negotiable #3 and step 5).
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  default include/exclude path set, the repository-required rule, and the
  restore safety model.
- `docs/ARCHITECTURE.md`: describe the optional backup component, its
  trust boundary (an outbound-only client holding an encryption key and
  backend credentials; no listening service), and the new policy entries,
  emphasising the restore class.
- `README.md`: note the optional component and any new flag/subcommand.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 11. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_BACKUP=1` and a dummy
  `RESTIC_REPOSITORY` without touching the host (extend the existing
  `noninteractive`/`subcommands` cases).
- Assert that `ZOMBIE_INSTALL_BACKUP=1` with no `RESTIC_REPOSITORY` under
  `ZOMBIE_NONINTERACTIVE=1` exits `64`.
- Add a "standards" assertion that the new section names, units, and
  `payload/bin` helpers exist and that British spelling / status glyphs
  are respected, and that `backup-run`/`backup-restore` pass `bash -n`.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including the new `payload/bin` helpers and units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  init-only-when-absent and reuse-existing-passphrase guards.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host and would write to a real backend. All verification here is static
  (`lint`/`test`/`package`) plus dry-run reasoning. End-to-end backup and
  a real test-restore must be validated by a human on a disposable Ubuntu
  Desktop LTS VM against a throwaway repository.
- **Passphrase loss = data loss.** A `restic` repository cannot be read
  without its passphrase. The reuse-existing-key guard and the receipt's
  set/fingerprint surfacing are load-bearing; never regenerate the key on
  re-run and never print it.
- **Restore is the sharp edge.** In-place restore overwrites live data;
  it stays operator-driven, confirmation-gated, and in its own policy
  class. The agent's default offering is a read-only test restore.
- **No mailer/alerting** (email on failure) in this plan — it needs an
  outbound SMTP relay the baseline does not install; alerting is layered
  on later, consistent with the brainstorm deferring a host mailer.
- **The backend is operator-supplied.** This plan does not stand up
  object storage, an SFTP host, or a `rest-server`; multi-host backup
  servers and cross-machine deduplication remain out of scope, consistent
  with the one-machine boundary in `brainstorm.md`.
