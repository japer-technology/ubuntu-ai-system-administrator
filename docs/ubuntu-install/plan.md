# Package installation and update implementation plan

## Purpose

Implement a polished package-based installation and update mechanism while
retaining the Git clone workflow as a fully supported peer. The governing
architecture is:

> There must be one installation engine with multiple thin entry points.

The repository checkout, release tarball, and Debian package must therefore
invoke the same lifecycle hooks in `scripts/install.sh`,
`scripts/uninstall.sh`, and `scripts/component-registry.sh`. Package
maintainer scripts, the command wrapper, and the bootstrap script must not
duplicate host-convergence logic.

This document is an implementation plan, not an implementation.

## Current baseline

The repository already provides much of the required foundation:

- `scripts/install.sh` owns install, verify, doctor, repair, and uninstall
  dispatch, including component-aware operation for `zombie`, `forgejo`, and
  `llama`.
- `scripts/component-registry.sh` supplies ordered lifecycle dispatch, and
  `scripts/uninstall.sh` removes selected components in reverse registry
  order.
- The installer is idempotent, supports `--dry-run`, preserves exit code `64`
  for missing unattended configuration, and writes a human-readable receipt.
- `make package` creates the canonical release tarball.
- `make deb` and `scripts/build-deb.sh` create a Stage 1 package under
  `/usr/share/ubuntu-zombie/` with `/usr/sbin/ubuntu-zombie`.
- `debian/postinst` currently limits itself to file modes and next-step
  guidance; it does not activate the product.
- `debian/prerm` currently blocks ordinary package removal while an activated
  installation remains, rather than silently deleting runtime state.
- `.github/workflows/release.yml` publishes the tarball and Debian package
  with checksums, SBOM, provenance, and signatures.

The primary gaps are a stable wrapper contract, origin-aware updates,
structured installation metadata, versioned migrations, capability consent,
APT repository/bootstrap delivery, package lifecycle semantics, and
package-level integration coverage.

## Decisions to settle before implementation

Record these decisions in the architecture note before changing runtime
behaviour:

1. **Canonical engine boundary.** Keep component convergence in
   `scripts/install.sh` and component reversal in `scripts/uninstall.sh`.
   Shared update, receipt, migration, and consent helpers may move into
   focused files under `scripts/`, but entry points must only dispatch to
   them.
2. **Stable installed source path.** Keep the package-owned canonical tree at
   `/usr/share/ubuntu-zombie/`. Package upgrades replace this tree while
   preserving mutable state elsewhere.
3. **Mutable state location.** Use a root-owned directory under
   `/var/lib/ubuntu-zombie/` for installation metadata, migration state,
   update transactions, and approved capabilities. Continue to keep runtime
   configuration in `/etc/ubuntu-zombie/`, product state beneath
   `/opt/ai-zombie/state/`, and audit material beneath
   `/var/log/ubuntu-zombie/`.
4. **Package removal semantics.** Ordinary `apt remove` must be permitted to
   remove package-owned files without invoking product uninstall and without
   deleting mutable user data. `apt purge` may remove package-owned
   configuration and package metadata only; destructive runtime-data removal
   remains an explicit `ubuntu-zombie uninstall` choice.
5. **Git update source.** Track the repository URL and branch at activation.
   A detached HEAD, missing upstream, unsafe ownership, or dirty working tree
   must fail closed with recovery guidance.
6. **Override policy.** Any dirty-tree override must be explicitly named,
   separately documented, and must never discard work implicitly. Prefer
   allowing the operator to acknowledge and continue only when the update can
   preserve the changes; otherwise require the operator to clean or stash the
   checkout.
7. **Capability identity.** Compare stable capability identifiers and
   security-relevant attributes, not descriptions or release versions.
   Routine code revisions must not create new consent prompts.
8. **Service restart policy.** Snapshot enabled and active state before an
   update. Restart only services belonging to already-enabled components;
   never enable a new unit or component as an upgrade side effect.
9. **Repository channels.** Define supported Ubuntu suites, architectures,
   signing-key rotation, and stable/candidate/edge publication policy before
   advertising the bootstrap URL.

## Target architecture

### Thin entry points

Provide these entry points, all resolving the same repository root and then
delegating:

| Entry point | Responsibility |
| --- | --- |
| `scripts/install.sh` | Canonical lifecycle engine for clone and tarball use |
| `/usr/sbin/ubuntu-zombie` | Stable command parser and thin dispatcher |
| Debian maintainer scripts | Package file lifecycle only |
| Bootstrap script | OS check, APT trust setup, package install, optional setup |
| Update command | Origin selection, transaction orchestration, then canonical convergence |

The wrapper should translate `setup` and its `install` alias to the existing
install verb. It should delegate verify/status, doctor, repair, and uninstall
without reimplementing their checks or component dispatch. `version` should
read the canonical packaged or checkout `VERSION`. Update orchestration may
call delivery-specific source acquisition, but convergence and verification
must return to the canonical lifecycle engine.

### Shared command contract

The supported public interface will be:

| Public command | Canonical action |
| --- | --- |
| `setup [component]` | `scripts/install.sh install [component]` |
| `install [component]` | Alias for `setup` |
| `update` | Origin-aware update transaction |
| `status [component]` | Read-only canonical verification summary |
| `verify [component]` | `scripts/install.sh verify [component]` |
| `doctor [component]` | `scripts/install.sh doctor [component]` |
| `repair [component]` | `scripts/install.sh repair [component]` |
| `uninstall [component]` | Canonical uninstall dispatch |
| `version` | Delivery and activated-version information |

Preserve existing flag placement, environment variables, component names,
JSON output, dry-run behaviour, and exit codes. Decide whether `status` is a
strict alias for `verify` or a concise formatter over verification results;
in either case it must consume canonical verification output rather than
introducing a second health implementation.

### Installation metadata

Introduce one versioned, root-owned, non-secret metadata document. Write it
atomically with mode `0600` or `0640`, validate its schema before use, and
preserve the previous valid copy during updates.

The schema should include:

- schema version;
- installed Ubuntu Zombie version;
- origin: `git`, `tarball`, or `deb`;
- canonical source root;
- repository URL and branch for Git origins;
- enabled components and component sub-options;
- activation timestamp;
- approved capability-manifest version and capability digest;
- last successful update timestamp and version;
- last successful verification timestamp and result;
- last completed migration version;
- interrupted-update transaction identifier, if any.

Derive enabled components from the existing component manifests rather than
maintaining two independently editable lists. Never include passwords,
tokens, generated credentials, repository credentials, environment dumps, or
audit content.

Origin detection should prefer an existing valid metadata document. For
legacy installations, use conservative evidence from the invocation tree,
package database, and Git metadata, then write the origin only after operator
confirmation where evidence is ambiguous.

### Capability and consent manifest

Add a versioned, data-only manifest to the canonical source tree. Each
capability should have a stable identifier and the minimum attributes needed
to identify material privilege or exposure:

- passwordless sudo rules and command scope;
- privileged system services;
- listener address, port, protocol, and exposure class;
- component activation;
- service account privilege;
- agent filesystem, process, package, and network permissions.

The update transaction must compare the newly required capabilities for
already-enabled components with the approved snapshot. Added capabilities or
materially broadened attributes require explicit approval before migration or
convergence. Removed or narrowed capabilities do not require approval.
Text-only changes, implementation revisions, and version bumps must not
prompt.

Interactive approval must display a concise semantic diff. Non-interactive
updates that need new approval must stop before mutation with a distinct,
documented exit code and instructions for pre-approving the exact manifest
digest. Approval must be bound to the manifest content, recorded atomically,
and auditable without containing secrets.

The installer must apply the same consent check during first activation and
component expansion. Selecting a component explicitly is consent to its
declared current capabilities, but later expansion still requires a new
approval.

### Versioned migrations

Create an ordered migration registry with stable version identifiers,
preconditions, apply hooks, verification hooks, and recovery guidance.
Migrations must be:

- idempotent and safe to retry;
- applied only after capability approval;
- recorded only after their verification succeeds;
- scoped to enabled components;
- prohibited from enabling a previously disabled component;
- capable of reporting whether a rollback is safe or manual recovery is
  required.

Keep application data migrations separate from source acquisition. Snapshot
mutable databases or files where the current application supports safe
snapshotting, as the installer already does for chat history. Do not promise
automatic downgrade support.

### Update transaction

Implement updates as an explicit transaction with durable phases:

1. acquire an exclusive update lock;
2. load and validate installation metadata;
3. detect and validate origin;
4. capture enabled components and enabled/active service state;
5. perform preflight checks and create appropriate backups;
6. acquire the candidate source without activating it;
7. validate version, package/source integrity, migrations, and capability
   manifest;
8. request approval only for material capability expansion;
9. mark the transaction as applying;
10. update the delivery source;
11. run pending migrations;
12. invoke canonical idempotent convergence for enabled components only;
13. restore the prior service enablement policy and restart only applicable
   services;
14. invoke canonical component verification;
15. atomically record success and clear the transaction marker;
16. print a concise health and recovery summary.

On failure, retain the transaction record, identify the last completed phase,
avoid claiming success, and direct the operator to `doctor` or `repair`.
`repair` should recognise interrupted transactions and safely resume or
complete recovery.

### Package-origin update

For `deb` origin:

- confirm that the installed package owns the selected source root;
- refresh APT metadata and upgrade only the Ubuntu Zombie package set;
- rely on package unpacking to replace immutable files;
- ensure maintainer scripts never call setup or enable product services;
- run migrations and convergence explicitly from update orchestration;
- preserve `/etc`, `/var/lib`, `/var/log`, `/opt` state, credentials,
  receipts, history, models, databases, and repositories;
- verify that package upgrades do not activate newly shipped components.

Avoid recursive invocation when the running wrapper upgrades its own package.
The update flow should stage transaction intent before APT, then re-exec the
new packaged updater for post-upgrade phases.

### Git-origin update

For `git` origin:

- require a valid Git work tree with the recorded remote and branch;
- reject unsafe ownership, detached or unexpected branches, unresolved
  operations, and uncommitted tracked or untracked changes by default;
- fetch the configured remote without changing the work tree;
- reject downgrades and unexpected history according to the documented
  fast-forward policy;
- validate the candidate revision before switching;
- update by fast-forward only;
- preserve operator configuration and all state outside the checkout;
- rerun convergence for enabled components and canonical verification;
- provide exact recovery instructions if source update or convergence fails.

Do not use reset, clean, forced checkout, or implicit stash operations. If an
override is retained, specify exactly what it permits and prove through tests
that it cannot erase local changes.

### Tarball-origin update

Although the primary objective names package and Git updates, the metadata
schema includes tarball origin. Define supported behaviour rather than
letting it fall through to Git:

- either support a verified release-artifact update using the existing
  `verify-release` mechanism and an atomic versioned source directory; or
- report that automatic tarball updates are unsupported and provide a safe,
  documented manual replacement flow before convergence.

Do not silently treat an unpacked tarball as a Git checkout.

## Implementation phases

### Phase 1: freeze contracts and add characterisation tests

Before refactoring:

- capture current installer grammar, flag ordering, component selection,
  exit-code behaviour, dry-run output invariants, and uninstall delegation;
- add package-content tests for the current Stage 1 boundary;
- test that maintainer scripts contain no activation path;
- add test fixtures for root-owned state without using the real host;
- document the metadata, migration, capability, and update transaction
  schemas.

This phase protects the existing Git clone path while later work moves shared
logic.

### Phase 2: install a maintained wrapper

- Move wrapper source out of the heredoc in `scripts/build-deb.sh` into a
  tracked, linted script.
- Make packaging copy that script to `/usr/sbin/ubuntu-zombie`.
- Add setup/install alias translation, status, update, and version dispatch.
- Resolve package, Git, and tarball roots safely without relying on the
  caller's working directory.
- Keep lifecycle arguments opaque after validation so the canonical scripts
  retain control.
- Add shell completion updates only after the command contract stabilises.

### Phase 3: structured metadata and legacy adoption

- Add atomic schema read/write helpers.
- Record activation origin, source, version, components, and timestamps from
  successful canonical lifecycle operations.
- Update verification timestamps only after successful verification.
- Reconcile metadata with component manifests and fail safely on corruption.
- Add an explicit migration/adoption path for installations created before
  metadata existed.

### Phase 4: capability consent and migrations

- Add the current baseline capability manifest for every component.
- Add semantic comparison and interactive/non-interactive approval flows.
- Integrate approval before first activation, component expansion, migration,
  and update mutation.
- Add the migration registry and no-op baseline migration.
- Make doctor and repair report invalid approval state and interrupted
  migrations.

### Phase 5: origin-aware update engine

- Implement common transaction, lock, backup, service snapshot, verification,
  summary, and recovery handling.
- Add the package source adapter.
- Add the Git source adapter with dirty-tree protection and fast-forward
  validation.
- Define and implement the chosen tarball policy.
- Ensure update convergence receives only currently enabled components.
- Add dry-run support that reports source, candidate version, migrations,
  capability changes, services, and verification without mutation.

### Phase 6: Debian lifecycle refinement

- Keep `postinst` non-activating on install and upgrade.
- Replace package-removal blocking with documented preservation semantics.
- Add any required `postrm` handling for package-owned metadata only, with
  careful distinction between remove, purge, upgrade, and failed upgrade.
- Keep mutable product state outside package-owned paths.
- Verify conffile behaviour and package upgrade handling.
- Ensure direct `.deb` installation and APT installation behave identically
  after package unpack.

### Phase 7: APT repository and bootstrap

- Define repository layout, supported suites/architectures, release channels,
  signing, key rotation, retention, and publication rollback.
- Extend release automation to publish immutable package artifacts into
  signed APT metadata only after existing release verification succeeds.
- Add a tracked bootstrap script that validates supported Ubuntu releases,
  installs a dearmoured keyring in `/usr/share/keyrings`, writes a
  `signed-by` source definition, updates APT, and installs the package.
- Support package-only, non-interactive, and repeatable component-selection
  flags.
- Stop after Stage 1 for package-only operation.
- Otherwise invoke the installed wrapper exactly once for setup.
- Make rerunning the bootstrap idempotent and avoid deprecated global
  `apt-key` trust.

The production bootstrap URL must not appear in `README.md`,
`docs/QUICKSTART.md`, or the eventual package-installation guide until DNS,
TLS, repository signing, and publication ownership are operational.

### Phase 8: documentation and migration guidance

Update:

- `README.md` and `docs/QUICKSTART.md` with the simple install, status, and
  update journey;
- `docs/UPGRADING.md` with package, Git, tarball, consent, interruption, and
  recovery flows;
- `docs/ARCHITECTURE.md` with the shared engine, Stage 1/Stage 2 trust
  boundary, state locations, and update transaction;
- `docs/CONFIGURATION.md` with update and consent environment controls;
- `debian/README.md` with package install, upgrade, remove, purge, and full
  uninstall semantics;
- `docs/TROUBLESHOOTING.md` with interrupted update and corrupted metadata
  recovery;
- release documentation with direct `.deb`, APT, offline, and signature
  verification paths;
- `CHANGELOG.md` and `VERSION` when user-visible implementation begins.

Add a short architecture note in this directory and a migration note for
existing Git installations. Include component-specific setup, direct `.deb`,
APT, bootstrap, offline installation, privilege-expanding updates, and the
advanced clone workflow.

## Test strategy

### Fast non-root tests

Extend `tests/smoke.sh` or focused shell tests with temporary roots and mocked
system commands to cover:

- wrapper command and flag mapping;
- setup/install equivalence;
- status/verify equivalence;
- component argument preservation;
- metadata schema validation and atomic writes;
- origin detection precedence;
- capability comparisons for unchanged, narrowed, and expanded manifests;
- non-interactive approval refusal;
- migration ordering, retries, and completion recording;
- update phase transitions and interrupted transaction detection;
- Git dirty-tree, detached-HEAD, wrong-branch, and fast-forward checks;
- package maintainer scripts remaining activation-free;
- package contents, ownership, modes, and dependencies;
- absence of secrets in metadata and package fixtures.

### Disposable Ubuntu integration tests

Use isolated Ubuntu 22.04 and 24.04 environments or disposable VMs for tests
that require root, dpkg, APT, users, sudoers, and systemd. Never run these
against a development workstation.

Cover at least:

1. installing the Debian package changes only package-owned Stage 1 paths;
2. setup activates the selected component through the canonical engine;
3. Git clone activation remains supported;
4. repeated setup converges without destructive changes;
5. package upgrade preserves configuration and mutable state;
6. Git update preserves configuration and mutable state;
7. unchanged capabilities update unattended without renewed approval;
8. expanded capabilities stop before mutation until explicitly approved;
9. missing required non-interactive input returns `64`;
10. setup, verification, repair, and uninstall work per component;
11. interrupted updates are diagnosed and repairable;
12. package remove and purge preserve user data according to the documented
    contract;
13. explicit full uninstall follows existing reversal and confirmation
    guarantees;
14. upgrades restart only services enabled before the update;
15. upgrades never activate a newly introduced component;
16. bootstrap package-only mode performs no activation;
17. bootstrap component and non-interactive flags map exactly to setup;
18. direct `.deb`, APT, tarball, and Git payloads have canonical file parity.

Package integration tests should build artifacts with `make package` and
`make deb`, inspect both manifests, then exercise installs and upgrades from
a local signed APT repository fixture. Fault injection should interrupt each
durable update phase and verify the resulting doctor/repair behaviour.

### Required validation

For every implementation slice:

- run `make lint`;
- run `make test`;
- run `make package`;
- run `make deb`;
- inspect the Debian package with `dpkg-deb`;
- run the relevant disposable-environment integration suite;
- scan changed files and built package contents for secrets;
- confirm no maintainer script invokes setup, install, user creation,
  sudoers changes, or service enablement.

## Expected file impacts

The implementation will likely affect:

- `scripts/install.sh` for lifecycle aliases, metadata hooks, consent,
  migrations, and update dispatch;
- `scripts/uninstall.sh` for explicit data-removal choices and metadata
  reconciliation;
- `scripts/component-registry.sh` for capability/migration metadata or
  additional trusted hooks;
- new focused shared files under `scripts/` for wrapper, state, update,
  migration, and consent responsibilities;
- `scripts/build-deb.sh`, `debian/control.in`, and Debian maintainer scripts;
- `Makefile` for package and integration entry points;
- `tests/smoke.sh` plus package integration fixtures;
- `.github/workflows/ci.yml`, `.github/workflows/integration.yml`, and
  `.github/workflows/release.yml`;
- user, architecture, configuration, upgrade, troubleshooting, release, and
  Debian documentation.

Avoid moving component convergence into Debian files or bootstrap code.
Avoid copying lifecycle shell functions into the wrapper. Prefer data
manifests and narrow shared libraries over another large dispatcher.

## Incremental commit sequence

Keep each commit independently reviewable and green:

1. Add characterisation tests and architecture contracts.
2. Track and package the thin wrapper with setup/status/version aliases.
3. Add structured installation metadata and legacy adoption.
4. Add capability manifests and consent comparison.
5. Add versioned migration registry and recovery state.
6. Add common update transactions and package-origin updates.
7. Add safe Git-origin updates and define tarball behaviour.
8. Refine Debian remove, purge, and upgrade semantics.
9. Add package-level disposable Ubuntu integration tests.
10. Add signed APT publication and bootstrap orchestration.
11. Complete user documentation, migration notes, changelog, and version.

Use imperative commit subjects under 72 characters. Run the required
validation before each commit rather than deferring all failures to the end.

## Acceptance criteria

The work is complete when:

- both documented install paths activate through the same lifecycle engine;
- package installation alone creates no product account, sudo rule, product
  service activation, component activation, or credential prompt;
- every public wrapper command delegates to canonical lifecycle behaviour;
- package and Git updates preserve all mutable configuration and user data;
- routine updates are unattended, while material privilege expansion
  requires exact, durable consent;
- enabled components and service state do not expand during an update;
- interrupted updates are detectable and recoverable;
- package removal cannot silently perform full product uninstall or destroy
  user data;
- the legacy clone commands and exit-code conventions remain compatible;
- release tarball and Debian package contain the same canonical scripts and
  payload;
- all fast and disposable-environment tests pass on supported Ubuntu LTS
  versions;
- documentation clearly distinguishes setup, update, package removal, purge,
  and explicit full uninstall.

## Principal risks and mitigations

- **Self-updating wrapper:** persist the transaction before APT and re-exec
  the newly installed updater for completion.
- **Package scripts activating the host:** enforce both static tests and
  integration assertions around maintainer scripts.
- **State schema corruption:** validate, lock, atomically replace, and retain
  the last valid copy.
- **False consent prompts:** compare stable semantic capability identifiers
  and attributes, not prose or release versions.
- **Missed privilege expansion:** require every component to declare its
  capabilities and fail closed when declarations are absent.
- **Git data loss:** permit fast-forward updates only and reject dirty or
  ambiguous work trees without destructive overrides.
- **Service-state drift:** snapshot enabled/active state and assert no new
  service or component is enabled after update.
- **Uninstall ambiguity:** separate package-file removal from explicit
  component/data destruction in commands, prompts, tests, and documentation.
- **APT trust mistakes:** use repository-scoped keyrings and `signed-by`,
  publish signed metadata, document rotation, and never use global
  `apt-key`.
- **Testing privileged behaviour:** confine end-to-end tests to disposable
  supported Ubuntu environments and keep default CI tests non-mutating.
