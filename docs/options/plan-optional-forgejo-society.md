# Plan: optional Forgejo Society seeding (repos + configuration injection)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that, **on top of an
already-installed Forgejo server** (the
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md)
option), *injects* the **Forgejo-Society** content and configuration into
the running forge: its organisations, its many role-bearing repositories,
the conformance suite, the Actions workflows, runner labels, themes, and
the matching rows in the **PostgreSQL** database that backs Forgejo.

Where the first option stands a *server* up (Forgejo binary + PostgreSQL +
optional runner), this option *populates* that server so it becomes a
working **Forgejo-Society** — the "society of repos" described by
[`japer-technology/forgejo-society`](https://github.com/japer-technology/forgejo-society),
whose `THE-SOCIETY-OF-REPO/` specification assigns each repository a single
role (agency, critic, censor, memory, workspace, service) and whose
`FORGEJO-SOCIETY/` subtree ships the three runnable implementation targets
(`forgejo-intelligence`, `forgejo-society`, `forgejo-labour`), each a
folder/workflow pair installed in that order.

This is deliberately the heavier, more opinionated option: it writes a lot
of state into Forgejo and therefore into PostgreSQL, runs Actions
workflows on the co-located runner, and is the bridge from "a forge
exists" to "a society runs on it".

## Relationship to the server option (hard dependency)

This option is a **second layer** that requires the first:

- It does **not** install Forgejo, PostgreSQL, or a runner. It refuses to
  run (clear `[x]` message, exit non-zero) unless a Forgejo server is
  present and healthy — either installed in the same run with
  `ZOMBIE_INSTALL_FORGEJO=1`, or already on the host and reachable on
  `127.0.0.1:${FORGEJO_HTTP_PORT}`.
- It strongly recommends the co-located Actions runner
  (`ZOMBIE_INSTALL_FORGEJO_RUNNER=1`): the Society's cognition *is* its
  workflows, so the conformance suite and the `forgejo-society.yaml`
  heart-beat need a `docker`-labelled runner to execute. If no runner is
  present, seed the content but warn that nothing will *run* until one is
  registered.
- It is sequenced strictly **after** every server section in
  `scripts/install.sh`, since it talks to a live forge.

## Design principle: seeding is a distinct, reusable phase

The first option introduced a family of `ZOMBIE_INSTALL_<COMPONENT>`
software flags. This option introduces a complementary idea: a
**post-install seeding phase** that drives a service through its own
API/CLI rather than installing packages. Keep it as one guarded
`section "Seed Forgejo Society"` block (plus a few sub-sections) that
early-returns when its flag is off, so the default install — and a
server-only install — are byte-for-byte unchanged.

A "society manifest" (a small, version-controlled description of the
organisations, repositories, roles, and settings to create) is the single
source of truth for what gets injected. The installer reads the manifest
and converges the forge to it. This keeps *what to seed* as reviewable
data and *how to seed it* as code, mirroring the repo's own ethos
("capability is granted by files and audited by Git").

## What "inject complex repos and configuration" means

The Forgejo-Society is not a single repo; it is a structured set of orgs,
repos, and forge settings. Seeding it means converging the live forge to
the following, in dependency order:

### 1. Forge-level configuration (Forgejo + PostgreSQL)

- **Society organisation(s).** Create the owning org(s) (e.g. a
  `forgejo-society` org) that the role repositories live under.
- **Actions enablement.** Ensure repository Actions are enabled and that
  the runner's labels (`docker`, `ubuntu-latest`) match what the
  workflows request, consistent with how the server option registered the
  runner.
- **Repository defaults / branch protection / settings** appropriate to a
  society of automated agencies (e.g. protected default branches, required
  workflows), expressed in the manifest, not hard-coded.
- **Theme.** Apply the Society theme assets
  (`FORGEJO-SOCIETY-INSTALLATION/theme/`) to the forge so the instance is
  recognisably a Society deployment, if a theme hook is in scope.
- All of the above land as rows in the **Forgejo PostgreSQL database** via
  Forgejo's own API/CLI — we never write the DB directly.

### 2. The role-bearing repositories (THE-SOCIETY-OF-REPO)

Create and populate the repositories that play the SOR roles — agencies,
critics, censors, memory, workspace, services — and the three runnable
implementation targets `forgejo-intelligence`, `forgejo-society`, and
`forgejo-labour` (each a `.forgejo-society/` folder plus a
`.forgejo/workflows/forgejo-society.yaml` heart-beat), installed in that
order.

### 3. The conformance suite

Install the conformance repo
(`FORGEJO-SOCIETY-INSTALLATION/CONFORMANCE/forgejo-conformance-repo/`) and
its two-step workflow pattern (`forgejo-conformance-INSTALL` then
`forgejo-conformance-TESTS`) so the deployment can *prove* it is ready for
SOR work. "If the conformance suite cannot run, SOR cannot run", so this
is the natural acceptance gate for the seeding phase.

### Sourcing the content (compliance-aware)

Per the Society repo's `WARNING.md`, **shared forges are mirrors only and
runtime lives on owned hardware**. The seeded repository *content* is
sourced from the project's published material (the
`FORGEJO-SOCIETY/` subtree and the installation `repo/` and `CONFORMANCE/`
folders), vendored or fetched at a pinned ref, then pushed into the local
owned forge. Decide and document one sourcing strategy:

- **Pinned archive fetch** of `japer-technology/forgejo-society` at a
  recorded `FORGEJO_SOCIETY_REF` (mirrors how the server option pins
  `FORGEJO_VERSION` and how the bridge pins are handled), or
- **Local checkout** path (`FORGEJO_SOCIETY_SUITE`) for air-gapped/dev use.

Record the resolved ref in the receipt for reproducibility. Do not seed
*from* GitHub/Codeberg as a runtime; treat them strictly as source
mirrors.

## Behaviour and options

New environment variables (document all in `docs/CONFIGURATION.md` and the
`usage()` env block):

- `ZOMBIE_INSTALL_FORGEJO_SOCIETY=0|1` — master switch (default `0`). When
  `1`, seed the Society into the Forgejo server. Implies a Forgejo server
  must be present (see the dependency rule above).
- `ZOMBIE_FORGEJO_SOCIETY_PROFILE=minimum|standard|full` — how much to
  seed (default `minimum`): `minimum` = org + conformance repo only;
  `standard` = the three implementation targets + conformance; `full` =
  the complete role catalogue. Each profile is just a manifest selection.
- `FORGEJO_SOCIETY_ORG` — owning organisation name (default
  `forgejo-society`).
- `FORGEJO_SOCIETY_REF` — pinned ref of the source content (default
  resolves the latest tag/`main`, recording the resolved value).
- `FORGEJO_SOCIETY_SUITE` — optional path to a local content checkout,
  skipping any fetch.
- `FORGEJO_SOCIETY_RUN_CONFORMANCE=0|1` — after seeding, dispatch the
  conformance workflow and treat failure as a verify failure (default
  `1` when a runner is present, otherwise `0` with a warning).

Reuse the server option's `FORGEJO_HTTP_PORT`, `FORGEJO_ADMIN_USER`, and
the generated admin credentials/token to authenticate API/CLI calls.

### Secrets

Seeding needs an **admin API token**. Generate it at seed time from the
existing admin account (via `forgejo admin user generate-access-token` or
the equivalent CLI), use it in-process, and store it only in a root-owned
file on the target (mode `640`, owner `root:git`) — never echo it, never
commit it, surface it in the receipt as set/fingerprint only. Confirm the
CI secret-scan patterns (`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not
tripped and add no example tokens to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every create is guarded by an existence check via the
   Forgejo API/CLI: skip orgs/repos that already exist, push only when the
   content differs, and make workflow dispatch safe to repeat. Re-running
   converges with no errors and no duplicate orgs, repos, hooks, or
   labels.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the whole
   seeding path from env alone. The defaults/generated token mean no new
   *required* input is introduced; if a profile ever needs operator input,
   exit `64` when missing in non-interactive mode, consistent with
   `validate_noninteractive()`.
3. **Policy gate + audit.** Anything the chat agent might later invoke to
   manage the Society (the `forgejo` admin CLI, `psql` against the forgejo
   DB, the runner controls) must be classified in
   `payload/etc/policy.yaml` `sudo_allow_list` at `system_change` and
   described in `docs/ARCHITECTURE.md`. The installer runs as root; the
   agent's post-install reach is what must be gated.
4. **No new runtime deps.** Seed using tools the server option already
   installs — the `forgejo` binary's admin CLI, `git`, `curl`, and
   `psql`/`postgresql-client`. Do not add language-level dependencies or a
   second HTTP toolchain.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "organisation").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_FORGEJO_SOCIETY`, `ZOMBIE_FORGEJO_SOCIETY_PROFILE`,
  and the `FORGEJO_SOCIETY_*` variables to the defaults/derivation block.
- Add validators (org-name check, profile enum check, ref/path checks) and
  wire them into `validate_config()`.
- Enforce the dependency: if the Society flag is on but no Forgejo server
  will exist (`ZOMBIE_INSTALL_FORGEJO != 1` and no live forge detected),
  fail validation early with a clear `[x]` message before any host change.
- Extend `usage()` env section and examples with opt-in Society examples
  (interactive and `ZOMBIE_NONINTERACTIVE=1`).

### 2. Interactive parameter review

- Add a "Forgejo Society" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, the profile, org, and whether
  conformance will run.
- Add a `_toggle_forgejo_society()` editor and a menu entry in
  `review_parameters()`; renumber the menu and update the range hint and
  "Unrecognised choice" message, or append as the next index to minimise
  churn.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary so that, when
  enabled, the plan lists the seeding steps (org, repos for the chosen
  profile, conformance, optional dispatch) and says nothing when disabled —
  keeping default output unchanged.

### 4. Source the Society content

- `section "Fetch Forgejo Society content"` — resolve
  `FORGEJO_SOCIETY_REF` (or use `FORGEJO_SOCIETY_SUITE`), download the
  pinned archive with the existing `curl_get`/retry helpers, verify it,
  unpack to a work dir, and record the resolved ref. Idempotent: re-use an
  already-fetched ref.

### 5. Authenticate to the live forge

- `section "Authorise Society seeding"` — wait for `forgejo.service` to be
  healthy on loopback, then mint/reuse the admin API token (guarded so a
  second run reuses the stored token rather than minting duplicates).

### 6. Seed forge-level configuration

- `section "Configure Forgejo Society organisation"` — create the owning
  org if absent; apply Actions enablement and repo-default settings from
  the manifest; ensure runner labels match. Idempotent via API existence
  checks.

### 7. Seed the role repositories

- `section "Seed Forgejo Society repositories"` — for each repository in
  the selected profile's manifest: create it if absent, push the
  vendored content (the `.forgejo-society/` folder and
  `.forgejo/workflows/forgejo-society.yaml` for the implementation
  targets), in the documented order
  (`forgejo-intelligence` → `forgejo-society` → `forgejo-labour`, then the
  wider catalogue for `full`). Push only when content differs.

### 8. Seed and (optionally) run the conformance suite

- `section "Seed Forgejo conformance suite"` — create/populate
  `forgejo-conformance-repo`, copy its `.forgejo/workflows/` in.
- When `FORGEJO_SOCIETY_RUN_CONFORMANCE=1` and a runner is present:
  dispatch `forgejo-conformance-INSTALL` then `forgejo-conformance-TESTS`,
  poll for completion, and treat a failed run as a seeding failure. When
  no runner is present, `warn` and skip the dispatch (`[~]`).

### 9. Verification, doctor, repair

- Extend `cmd_verify()` (only when the Society flag is on): the org
  exists; the expected repos for the profile exist and are non-empty; the
  conformance repo's last `TESTS` run passed (if dispatched); the runner
  has the required labels. Use `[ok]/[!]/[x]` glyphs and JSON records.
- Extend `cmd_doctor()` with guidance for the common seeding failures
  (token expired/invalid, runner missing or mislabeled, Actions disabled,
  workflow run failed, forge not reachable).
- Extend `cmd_repair()` to re-assert org/repo settings and labels and to
  re-dispatch conformance, idempotently.

### 10. Receipt

- Record in `write_receipt_start`/`write_receipt_finish`: Society enabled,
  profile, org, resolved `FORGEJO_SOCIETY_REF`, number of repos seeded,
  and the conformance result. Record the admin token only as
  "set"/fingerprint, never plaintext.

### 11. Uninstall (`scripts/uninstall.sh`)

- Reverse what seeding created, gated so a server-only or baseline-only
  install is untouched: delete the seeded repositories and the Society
  organisation via the Forgejo API/CLI (which also removes their rows from
  PostgreSQL), and revoke the seeding admin token. Treat org/repo deletion
  as **destructive** and require the confirmation phrase consistent with
  the policy model. Leave the Forgejo server itself to the server option's
  uninstall path.

### 12. Policy and docs

- `payload/etc/policy.yaml`: classify the Society-management programs
  (`forgejo` admin CLI, `psql` against the forgejo DB, runner controls) at
  `system_change` (see non-negotiable #3).
- `docs/CONFIGURATION.md`: document every new env var, the profiles, the
  sourcing/compliance posture, and the runner requirement.
- `docs/ARCHITECTURE.md`: describe the optional seeding phase, its trust
  boundary (it writes content and config into a network-listening service
  and its database, and triggers code execution on the runner), and the
  new policy entries.
- `README.md`: note the optional Society seeding and any new flag.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 13. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that `--dry-run`
  with `ZOMBIE_INSTALL_FORGEJO_SOCIETY=1` (and a Forgejo server enabled)
  parses and prints the seeding plan without touching the host.
- Assert the dependency guard rejects
  `ZOMBIE_INSTALL_FORGEJO_SOCIETY=1` without a Forgejo server.
- Add a "standards" assertion that the new section names exist and that
  British spelling / status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python compile)
  clean.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path by reasoning
  through each guarded section and every API existence check.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer or seed a live forge in the agent
  environment — seeding mutates a running service and its database and
  triggers runner execution. All verification here is static
  (`lint`/`test`/`package`) plus dry-run reasoning; end-to-end seeding must
  be validated by a human on a disposable Ubuntu Desktop LTS VM with the
  server option already applied.
- **Compliance.** Honour the Society repo's `WARNING.md`: the seeded forge
  must be **owned hardware**; shared forges (Codeberg) and GitHub are
  source mirrors only, never runtimes for agent workloads. The seeding
  path must not push agent workloads or secrets to shared infrastructure.
- **Execution surface.** This option enables code execution on the
  co-located runner (the conformance workflow and the
  `forgejo-society.yaml` heart-beat). That is a larger attack/trust
  surface than the server-only option; keep it strictly opt-in, gated by
  policy/audit, and documented.
- **Content drift.** Seeded content is pinned by `FORGEJO_SOCIETY_REF`;
  record the resolved value so a re-run reproduces the same Society. The
  full role catalogue, federation across multiple hosts, and the wider
  `transition-plan/` rollout remain out of scope for this single-host
  seeding option.
