# Implementation plan for improvements 3

Source analysis: [`improvements-3.md`](improvements-3.md).

This plan turns the component-oriented installer recommendation into a
sequence of reviewable changes. It covers the installer grammar, component
state, selective lifecycle operations, standalone Forgejo installation, and
the extension contract for future components. It does not implement those
changes.

## Outcome

The canonical command grammar becomes:

```text
scripts/install.sh <verb> [component ...] [flags]
```

The initial public components are `zombie` and `forgejo`. The existing verbs
remain `install`, `verify`, `doctor`, `repair`, and `uninstall`.

The intended selection rules are:

- The `install` verb with no following component target keeps its current
  meaning: install or upgrade the `zombie` baseline.
- `scripts/install.sh install forgejo` installs Forgejo and PostgreSQL without
  implicitly installing the zombie account or runtime.
- `scripts/install.sh install zombie forgejo` converges both components in one
  run.
- Existing `ZOMBIE_INSTALL_FORGEJO=1 scripts/install.sh install` invocations
  continue to select both the default zombie and Forgejo.
- Explicit component arguments and enabled `ZOMBIE_INSTALL_*` variables are
  combined and deduplicated. Explicit `install forgejo` does not add the
  default zombie merely because the verb is `install`.
- `verify`, `doctor`, and `repair` with explicit targets operate only on those
  targets.
- `verify` and `doctor` with no targets inspect components recorded in the
  on-host manifest. On a pre-manifest installation they retain a compatibility
  fallback based on existing host artefacts.
- `uninstall` with no targets keeps the current all-components behaviour.
  Explicit targets remove only those components.
- Unknown or repeated component targets fail before host mutation with exit
  code `2`.

Do not add the bare-component shorthand (`install.sh forgejo`) in the first
delivery. Reserve it as a later compatibility-free enhancement after the
canonical grammar has shipped and usage has been evaluated.

Keep `ZOMBIE_INSTALL_FORGEJO_RUNNER` as an option owned by the `forgejo`
component. Do not expose `forgejo-runner` as an independent component until it
has a lifecycle that can sensibly exist apart from Forgejo.

## Constraints

- Preserve idempotence for every component combination and installation order.
- Preserve `ZOMBIE_NONINTERACTIVE=1`; missing required non-interactive input
  must continue to exit `64`.
- Preserve current exit-code meanings.
- Preserve the default zombie-only dry-run output unless a deliberate,
  documented compatibility change is approved.
- Keep generated credentials in the root-only receipt and component-owned
  configuration. The component manifest must contain no secrets.
- Do not add runtime dependencies; Bash associative and indexed arrays are
  sufficient.
- Keep the policy gate and audit implementation unchanged unless a component
  introduces new agent-driven privileged behaviour.
- Do not run mutating installer or uninstaller paths outside a disposable
  Ubuntu Desktop LTS VM.

## Target internal model

### Component registry

Create one registry in `scripts/install.sh` with an ordered list of component
names and metadata for each component:

- public name;
- legacy environment selection variable, where applicable;
- dependencies;
- install, verify, doctor, repair, and uninstall hook names;
- whether it requires the resident zombie;
- optional progress-section marker name.

Register `zombie` first and `forgejo` second. PostgreSQL remains an internal
Forgejo dependency rather than a public component.

Keep registration separate from execution. Parsing produces a selected target
set, dependency resolution produces an ordered execution list, and dispatch
calls only the hooks for the active verb. Validate every hook and dependency at
startup so a malformed registry fails before mutation.

Use the same public component-name list in help generation, target validation,
error messages, and tests. Shell completions remain static, but must mirror
that list and be covered by standards checks to prevent drift.

### Core and component boundaries

The core layer owns infrastructure needed by any component:

- argument and flag parsing;
- target resolution and dependency ordering;
- configuration validation relevant to the selected targets;
- root and supported-host checks;
- apt locking, retry, download, checksum, and command helpers;
- transcript and step logging;
- dry-run rendering;
- confirmation and non-interactive behaviour;
- receipt lifecycle;
- component manifest reads and writes;
- phase counting and dispatch.

The `zombie` component owns:

- local LLM discovery and zombie-specific parameter review;
- the agent user, home, and sudoers entry;
- baseline package and Node/Python runtime setup;
- unattended-upgrade and desktop availability configuration;
- `/opt/ai-zombie`, `/etc/ubuntu-zombie`, policy, skills, and secrets;
- chat and health services, logrotate, lifecycle state, and audit log;
- zombie verification, diagnosis, repair, and uninstall steps.

The `forgejo` component owns:

- Forgejo-specific configuration review and validation;
- PostgreSQL, Forgejo, and optional runner packages and users;
- Forgejo configuration, database, binaries, services, data, and health
  checks;
- Forgejo receipt fields;
- Forgejo verification, diagnosis, repair, and uninstall steps.

Forgejo may use core apt, download, receipt, logging, and progress helpers, but
must not reference the zombie user, `/opt/ai-zombie`, chat settings, local LLM
discovery, policy deployment, or zombie services.

### Component manifest

Use one root-owned file per component under:

```text
/var/lib/ubuntu-zombie/components/
```

The directory must be independent of `/opt/ai-zombie` so it survives selective
zombie removal. The `ubuntu-zombie` namespace deliberately matches the existing
`/etc/ubuntu-zombie` and `/var/log/ubuntu-zombie` installer-owned paths; the
`ai-zombie` name remains the deployed agent runtime path. These existing paths
are catalogued in `docs/ARCHITECTURE.md` under “Installed shape” and “Logs and
state”. Each entry records only:

- a fixed manifest format version;
- component name;
- installed Ubuntu Zombie version;
- installation or last-converged UTC timestamp;
- component version where meaningful, such as the resolved Forgejo version;
- enabled sub-options that affect lifecycle, such as the Forgejo runner.

Write entries atomically with a temporary file in the same directory, validate
the component name against the registry before constructing a path, and set
root ownership with non-secret-readable permissions. Write an entry only after
the component install and health checks succeed. Remove it only after the
component uninstall hook completes successfully.

Treat the manifest as authoritative for managed-component discovery, not as
proof of health. Explicit lifecycle targets remain valid when an entry is
missing so operators can repair or remove a partial or legacy installation.
When an existing component is successfully converged by the new installer,
backfill its entry automatically.

## Phase 1 — grammar and selection

### Installer parsing

Refactor the argument parser in `scripts/install.sh` to distinguish:

1. the lifecycle verb;
2. zero or more component targets;
3. global or verb-specific flags.

Retain flags before or after the verb and targets. Continue treating `--` as
the end of flags, but validate all following tokens as component targets rather
than generic positional arguments.

Replace `PARSED_ARGS` and `reject_unexpected_positional_args` with explicit
target collection and validation. A second lifecycle verb must remain an error;
it must never be interpreted as a component. Reject duplicate component names
to surface likely command mistakes rather than silently hiding them.

Resolve selections after parsing:

- no explicit `install` targets selects `zombie`;
- explicit `install` targets select exactly those targets;
- enabled legacy environment options are added to the selected set;
- no-target non-install verbs defer target discovery until manifest loading;
- no-target `uninstall` selects the compatibility “all managed artefacts”
  operation rather than only manifest entries.

Limit configuration validation to the selected components. A forgejo-only run
must not fail because a zombie-only setting is absent or invalid, while unsafe
global paths and Forgejo values must still fail before mutation.

Forward resolved uninstall targets from `install.sh uninstall` to
`scripts/uninstall.sh`, along with the existing behaviour flags.

### Help and completions

Update `usage()` to show the new grammar, valid components, selection rules,
and canonical examples. Retain environment examples so cloud-init and existing
automation remain supported.

Update:

- `scripts/completions/install.bash`;
- `scripts/completions/_install.sh`.

Before a verb, complete verbs and global flags. After a verb, complete valid
components plus flags. Stop suggesting a component after it has already been
used. Only suggest `--archive` and `--keep-agent` for uninstall commands.

### Phase 1 tests

Extend `tests/smoke.sh` with non-root parser tests for:

- every verb with `zombie`, `forgejo`, and both targets;
- flags before, between, and after targets;
- the default `install` selection;
- explicit `install forgejo` excluding zombie;
- legacy environment selection remaining additive;
- unknown and duplicate targets exiting `2`;
- a second verb token exiting `2`;
- component-looking values after `--`;
- uninstall target forwarding;
- `--archive` and `--keep-agent` rejection outside a zombie uninstall;
- completion files containing every registered public name.

Use dry-run output or a parser-only test mode already safe for smoke tests; do
not execute root mutation paths.

### Phase 1 documentation

Update the command grammar and compatibility examples in:

- `README.md`;
- `docs/QUICKSTART.md`;
- `docs/CONFIGURATION.md`;
- `docs/ARCHITECTURE.md`.

Describe the canonical two-word form and explicitly state that environment
flags remain supported. Do not imply that standalone Forgejo works until Phase
3 lands; if Phase 1 ships independently, mark `install forgejo` as accepted
syntax whose standalone execution is gated until the extraction is complete,
or keep that target behind an internal guard until Phase 3.

### Phase 1 acceptance

- Existing no-target commands retain their documented meaning.
- All invalid target combinations fail before root checks or host mutation.
- `install --dry-run` remains unchanged for the default selection.
- Component names are available in Bash and Zsh completion.

## Phase 2 — manifest and selective lifecycle

### Manifest helpers

Add core helpers to:

- create and validate the manifest directory;
- atomically write a component entry;
- read and validate known entries without evaluating shell content;
- list installed known components in registry order;
- ignore and warn about malformed or unknown entries;
- remove one entry after successful uninstall;
- remove empty manifest directories on a best-effort basis after the final
  known component is gone, but leave them in place with a warning if unknown
  entries or other state remain.

Do not `source` manifest files. Parse a fixed key/value format as data and
reject duplicate, unknown, or unsafe component names.

### Verify and doctor

Split the current monolithic lifecycle functions into component hooks:

- zombie verification continues to use the deployed verifier initially, then
  moves behind `verify_component_zombie`;
- Forgejo service, config-permission, PostgreSQL, health endpoint, and runner
  checks move into `verify_component_forgejo` and
  `doctor_component_forgejo`;
- zombie checks in `cmd_doctor` move into `doctor_component_zombie`.

Preserve current human output and JSON fields where possible. Add the component
name to each structured check so multi-component output is unambiguous. Define
one aggregate exit policy: verification fails if any selected component fails;
doctor reports warnings but retains its current exit behaviour.

For no-target runs:

- iterate valid manifest entries;
- on a host with no entries, detect legacy zombie and Forgejo artefacts;
- explain when nothing managed is installed instead of assuming zombie;
- never infer a component solely from an enabled environment flag.

### Repair

Dispatch repair only to selected or discovered components. Zombie repair must
not restart Forgejo; Forgejo repair must not chown `/opt/ai-zombie` or restart
chat. An explicit repair of an absent component should return a clear failure
or warning without creating it; installation remains the operation that creates
missing components.

### Selective uninstall

Refactor `scripts/uninstall.sh` into parsing, shared helpers, and two explicit
component removal functions. Preserve its current best-effort cleanup and final
non-zero status aggregation.

`uninstall forgejo` must:

- stop and remove the runner and Forgejo services and binaries;
- handle repository data, database, role, and system-user confirmations as
  today;
- remove only Forgejo’s manifest entry after successful required cleanup;
- leave zombie services, sudoers, runtime, policy, logs, and account untouched;
- leave shared apt packages installed.

`uninstall zombie` must:

- perform the existing baseline removal without entering Forgejo cleanup;
- preserve the component manifest and Forgejo artefacts;
- warn prominently when other manifest components remain;
- apply `--archive` and `--keep-agent` exactly as today.

No-target uninstall must preserve the current complete-removal behaviour,
including legacy artefact detection when no manifest exists. Execute dependants
before dependencies and Forgejo before zombie so an interrupted full uninstall
does not strand a component whose management dependency has already gone.

Reject `--archive` and `--keep-agent` when `zombie` is not selected. Retain
`--dry-run`, `--yes`, output flags, path validation, and destructive
confirmation boundaries for every selection.

### Phase 2 tests

Add hermetic shell tests around temporary manifest and filesystem roots. Make
state paths overridable only where the existing test conventions permit it;
production defaults must remain fixed and root-owned.

Cover:

- atomic manifest write, parse, list, update, and remove;
- malformed, duplicate, unknown, and path-traversal entries;
- legacy artefact fallback;
- target-scoped verify, doctor, and repair dispatch;
- aggregate JSON identifying components;
- selective uninstall dispatch and target order;
- Forgejo-only uninstall never reaching zombie cleanup;
- zombie-only uninstall never reaching Forgejo cleanup;
- no-target uninstall retaining complete-removal semantics;
- manifest retention while another component remains;
- failed component removal retaining its manifest entry;
- dry-run never changing manifest or component state.

### Phase 2 acceptance

- A newly converged component has one valid manifest entry.
- Explicit lifecycle commands affect only their selected components.
- Legacy installations remain verifiable, diagnosable, repairable, and
  uninstallable.
- Selective zombie removal leaves Forgejo running and discoverable.
- Selective Forgejo removal leaves the zombie running and discoverable.

## Phase 3 — standalone Forgejo

### Extract the core run

Turn the current top-level install body into an orchestrator:

1. parse and resolve targets;
2. bootstrap only tools required by core;
3. gather selected-component parameters;
4. validate selected-component configuration;
5. run target-aware preflight;
6. open core logs and receipt;
7. confirm the selected plan;
8. dispatch component install hooks in dependency order;
9. write each successful manifest entry;
10. finalise the aggregate receipt and summary.

Make disk, memory, network, package, and expected-duration preflight messages
target-aware. Forgejo-only installation must not claim to create an AI
administrator, install chat, or require zombie runtime capacity.

Keep the existing transcript and receipt paths under
`/var/log/ubuntu-zombie/`; treat them as installer-owned core state. Ensure the
core creates them without relying on the zombie user. A forgejo-only receipt
must contain Forgejo credentials when generated, but omit zombie password,
provider, TTL, and chat fields.

### Extract the zombie hook

Move all baseline mutations into the zombie install hook without changing their
order or behaviour. Include top-level sections currently before and after the
Forgejo block, not merely payload deployment. Keep local LLM discovery and the
main parameter review out of forgejo-only runs.

Preserve:

- re-run convergence;
- existing secret preservation;
- lifecycle reset semantics;
- phase numbering;
- default dry-run text;
- current receipt fields and final summary;
- verification after installation.

### Extract the Forgejo hook

Move the existing guarded Forgejo and runner blocks into one Forgejo install
hook. Keep current checksum verification, migration stop/write/permission
restore sequence, generated-password precedence, database setup, systemd
hardening, and `/api/healthz` readiness requirement.

Give Forgejo an explicit package list rather than relying on the baseline
package phase. Include every command used by the Forgejo path, but install only
missing packages through the shared apt helper. Do not create the zombie user,
install Node or the Python agent runtime, alter sleep targets, deploy policy or
skills, or create chat services. Keep the definitive package list beside the
Forgejo hook and summarise its host dependencies in `docs/ARCHITECTURE.md`.

The optional runner remains nested within Forgejo and continues to require
`ZOMBIE_INSTALL_FORGEJO_RUNNER=1`. Its registration must use the selected
Forgejo configuration and remain idempotent.

### Target-aware interaction and dry-run

Render parameter review pages only for selected components. A combined run can
show a core summary followed by zombie and Forgejo sections; a forgejo-only run
must not prompt for the zombie chat password, TTL, provider, or local LLM.

Render dry-run plans by component. Keep the existing zombie-only output stable,
then append Forgejo text for combined legacy-flag runs. Add a distinct
forgejo-only plan that accurately omits zombie resources.

### Phase 3 tests

Add static and hermetic tests proving that the Forgejo hook has no zombie
dependency:

- no references to `AGENT_USER`, `AGENT_HOME`, chat, TTL, local LLM, policy,
  audit, or `/opt/ai-zombie` in the Forgejo hook;
- forgejo-only dry-run omits all zombie resources and includes PostgreSQL,
  Forgejo, receipt, transcript, and optional runner resources;
- forgejo-only non-interactive parsing requires no zombie-only input;
- combined and reversed target order resolves to the same registry order;
- legacy flag invocation remains equivalent to `install zombie forgejo`;
- generated Forgejo passwords appear only in the root-only receipt contract;
- a component manifest is written only after the health check.

On separate disposable Ubuntu 22.04 and 24.04 VMs, the two releases supported
by the current installer, exercise the complete matrix on both releases. Do not
add Ubuntu 20.04 to the matrix without separately expanding the project’s
supported-platform contract.

1. fresh `install forgejo`;
2. re-run `install forgejo`;
3. add `install zombie`;
4. verify and doctor each component separately and together;
5. remove zombie while retaining Forgejo;
6. reinstall zombie;
7. remove Forgejo while retaining zombie;
8. full no-target uninstall;
9. repeat with the runner enabled;
10. repeat representative paths under `ZOMBIE_NONINTERACTIVE=1`.

Record expected state after every step, including users, units, ports, data,
receipt, manifest, and exit code.

### Phase 3 acceptance

- Forgejo installs and passes health checks on a fresh supported host without
  any zombie account or runtime artefact.
- Adding components later is order-independent and convergent.
- Removing the zombie does not stop or damage Forgejo.
- The default zombie-only path remains behaviourally compatible.

## Phase 4 — complete registry generalisation

Replace remaining Forgejo-specific selection branches in shared infrastructure
with registry-driven loops:

- validation dispatch;
- parameter review sections;
- dry-run stanzas;
- phase counts;
- receipt start and finish sections;
- install and lifecycle dispatch;
- manifest discovery;
- final summaries.

Component hooks may remain component-specific; the registry should remove
dispatcher copy-and-paste, not obscure application logic. Avoid storing
executable command strings as registry data. Store trusted function names and
validate them with Bash’s function lookup before dispatch.

Update `CONTRIBUTING.md` and `options/README.md` so the extension recipe is:

1. define the component’s configuration and validators;
2. implement lifecycle hooks;
3. register metadata and dependencies;
4. add manifest version data and receipt fields;
5. add interactive and dry-run rendering;
6. add policy and audit handling only for agent-driven privileged actions;
7. add uninstall reversal and tests;
8. update operator docs, changelog, and version.

Use the next optional component as the proof of the abstraction. Adding it
should not require edits to parser or dispatcher conditionals.

### Phase 4 acceptance

- Shared dispatch contains no Forgejo-name special cases except compatibility
  mapping for `ZOMBIE_INSTALL_FORGEJO`.
- Registry validation catches missing hooks and invalid dependencies.
- A test-only sample component can be registered and dispatched without
  changing parser logic.
- Documentation defines one lifecycle contract for all future `options/`
  components and packaging targets.

## File-by-file change map

### Runtime scripts

- `scripts/install.sh`: parser, target resolver, registry, manifest helpers,
  target-aware validation/preflight/review/dry-run/receipt, lifecycle
  dispatcher, and extracted zombie and Forgejo hooks.
- `scripts/uninstall.sh`: component target parser, selective cleanup hooks,
  manifest updates, compatibility discovery, and all-target orchestration.
- `scripts/lib.sh`: only move helpers here if both entry points genuinely need
  them and doing so does not change existing callers.
- `scripts/completions/install.bash`: verb-aware component completion.
- `scripts/completions/_install.sh`: verb-aware component completion.

### Tests

- `tests/smoke.sh`: grammar, compatibility, manifest, dispatch, dry-run,
  non-interactive, completion, and standards coverage.
- Add fixtures under `tests/fixtures/` only when needed to represent manifest
  or host state; do not add executable test dependencies.

### Documentation and release metadata

- `README.md`: canonical commands, standalone Forgejo, selective lifecycle,
  and compatibility examples.
- `docs/QUICKSTART.md`: zombie, Forgejo-only, combined, and selective removal
  walkthroughs.
- `docs/CONFIGURATION.md`: target/env precedence, component manifest, runner
  option, receipts, and non-interactive examples.
- `docs/ARCHITECTURE.md`: core/registry/component model, manifest trust
  boundary, and standalone-host distinction.
- `CONTRIBUTING.md`: component extension recipe and lifecycle hooks.
- `options/README.md`: replace the flag-and-guard contract with the registry
  contract while retaining environment compatibility.
- `CHANGELOG.md`: user-visible CLI, manifest, and selective lifecycle changes.
- `VERSION`: update whenever the changelog is updated in the required
  `yyyy.mm.dd.hh.nn.ss` UTC format by running
  `date -u +%Y.%m.%d.%H.%M.%S > VERSION`; keep this aligned with the release
  rule in `CONTRIBUTING.md`.

Review packaging wrappers and documentation for assumptions that every command
installs the zombie. In particular, the `/usr/sbin/ubuntu-zombie` wrapper
generated by `scripts/build-deb.sh` must continue forwarding its complete
argument vector to `scripts/install.sh` unchanged.

## Compatibility and migration

- Do not remove or deprecate legacy environment selectors in this work.
- Backfill manifest entries only after a successful converge, never merely
  because artefacts were detected.
- Before backfill, lifecycle discovery may recognise the current zombie
  executable/service and Forgejo unit/config as legacy evidence.
- Explicit uninstall must work against legacy installations with no manifest.
- Unknown manifest entries must be preserved and warned about during targeted
  operations; a no-target uninstall must not delete unknown component state
  blindly. Leave the manifest directory and unknown entries intact, report
  their paths, and require an operator to resolve them explicitly.
- Manifest format changes require an explicit format version and a tolerant
  reader for the previous format.
- Keep current destructive confirmations for repositories, databases, users,
  `/opt/ai-zombie`, and `/etc/ubuntu-zombie`.
- Keep shared packages after selective or complete uninstall, matching current
  policy that base Ubuntu software may be used by other applications.

## Security review checklist

- Component names are registry-validated before use in paths or indirect
  function calls.
- Manifest content is parsed as data and is never sourced or evaluated.
- Temporary manifest and receipt files are created with restrictive modes and
  atomically renamed.
- Generated passwords and tokens never enter manifest data, command output,
  shell traces, or non-root-readable files.
- Target-scoped validation still protects every value interpolated into shell,
  SQL, config, or path contexts.
- Selective uninstall cannot cross component ownership boundaries.
- Legacy artefact detection cannot be redirected through operator-controlled
  symlinks or unsafe paths.
- Forgejo-only operation does not deploy a passwordless-sudo account.
- No new agent-triggered privileged path bypasses policy classification or
  audit logging.

## Validation for every implementation phase

Run from the repository root after each shell change:

```text
make lint
make test
make package
```

Also:

- compare default dry-run output with the pre-change fixture or captured
  baseline;
- inspect shell completion behaviour for Bash and Zsh;
- scan changed files for secrets;
- run code review and CodeQL validation;
- inspect the package contents and wrapper argument forwarding;
- use only a disposable supported VM for live install, repair, and uninstall
  matrices.

Do not mark the work complete until the VM matrix demonstrates idempotence,
non-interactive operation, component-order independence, selective uninstall,
legacy migration, and recovery from an interrupted component install.

## Maintainer decisions before implementation

Confirm these defaults before Phase 1:

1. Ship only the canonical verb-first grammar initially; defer
   bare-component shorthand.
2. Keep the runner environment selector and manifest sub-option owned by
   Forgejo; do not register it as an independent lifecycle component.
3. Warn, but do not require an additional acknowledgement, when selectively
   uninstalling zombie while other components remain; existing destructive
   confirmations still apply.
4. Use per-component entries under
   `/var/lib/ubuntu-zombie/components/`.
5. Reject a component repeated in positional arguments rather than silently
   hiding an operator typo. Treat overlap between an enabled environment
   selector and one positional target as harmless compatibility input and
   deduplicate it during selection.

If any decision changes, update the source analysis and this plan together
before implementation so the public grammar, compatibility tests, and
manifest design remain consistent.
