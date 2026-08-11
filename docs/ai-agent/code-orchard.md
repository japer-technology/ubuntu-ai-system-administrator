# Code Orchard

> A private local code-review assistant that explains a deliberately shared
> source tree and produces review reports and patch proposals without executing
> or changing the project.

Code Orchard complements the family with a developer-specific, read-only
analysis boundary. It is not Ubuntu Zombie development mode, an Imaginary
Friend workspace, or an Archive Lantern document collection.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `code-orchard` |
| Human need | Understand and review a local codebase without granting a model execution or repository-write authority |
| Intended users | One developer who owns or is authorised to review the shared source |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read regular files in one product-created repository root and write only Orchard-owned reports and patch bundles |
| Default Linux identity | Non-login `orchard` account and group |
| Default loopback port | `3567` |
| Install root | `/opt/code-orchard` |
| Configuration root | `/etc/code-orchard` |
| State root | `/var/lib/code-orchard` |
| Log root | `/var/log/code-orchard` |
| Environment prefix | `ORCHARD_*` |
| Ubuntu Zombie management | Fixed root-only family lifecycle interface; source, reports, and credentials stay out of manager inventory |
| Source root | `products/code-orchard/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Code Orchard inventories a deliberately shared source tree, answers questions
with path-, line-, and digest-bound evidence, and writes review findings or
unapplied unified-diff proposals into its own export area. Local installation
is appropriate because source may be private and operating-system permissions
can make the no-execution and no-write boundaries testable.

The first release supports one owner, one product-created repository root,
UTF-8 text files, lexical retrieval, a loopback UI, and one OpenAI-compatible
loopback model. It does not run builds, inspect Git credentials, or modify the
source tree.

### It must

- tie every code claim to a current path, line range, and SHA-256 digest;
- keep source read-only and validate every proposed patch against the exact
  source snapshot it references; and
- let the owner inspect, export, expire, rebuild, suspend, and remove all
  Orchard-owned state.

### It must not

- execute code, shells, hooks, tests, build tools, language servers, or package
  managers;
- write to the repository, Git metadata, developer home, credentials, or a
  sibling product; or
- claim that a review proves correctness, security, licence compliance, or
  fitness for deployment.

## Status and evidence

This document fixes a first product slice. No Orchard source, installer,
catalogue admission, disposable-VM evidence, or release exists. Every control
below is a requirement rather than an implemented safeguard.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Namespace, installation, and retention sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/code-orchard/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Orchard release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Share source, ask questions, request reviews, export patches, set retention, and remove state | Treat Orchard output as an executed or verified change |
| Machine operator | Install, configure, update, recover, suspend, and uninstall | Adopt an unowned repository or expose it without authorisation |
| Ubuntu Zombie manager | Invoke approved Orchard lifecycle operations | Retain source, findings, patch content, prompts, or Orchard secrets |
| `orchard` service | Read the fixed source root and write Orchard state, reports, and logs | Execute or modify source, inspect the host, or invoke lifecycle commands |
| Model endpoint | Propose explanations, findings, and diff text from selected snippets | Select paths, execute tools, or bypass deterministic evidence checks |

### Authority ceiling

The service accepts authenticated loopback requests, reads supported regular
files below `/srv/code-orchard/repositories`, writes below its state and log
roots, and calls one configured loopback model endpoint. It has no shell,
subprocess, compiler, Git command, repository write, `sudo`, Linux capability,
device access, internet access, or host-wide read.

Repository traversal is descriptor-relative and rejects links, devices,
sockets, mount changes, hard links, `..`, and files over 8 MiB. A prompt,
password, source comment, or approval cannot raise this ceiling.

### Authority inherited, retained, and removed

- Idempotent lifecycle, independent authentication, policy, audit, diagnostics,
  and release verification are retained.
- General passwordless `sudo`, login access, and privileged groups are removed.
- General shell, subprocess, package, service, device, and network tools are
  removed.
- Host-wide reads and workspace writes are replaced by one read-only sharing
  root and product-owned exports.
- Family management authority and source self-modification are removed.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Source catalogue | Shows supported files and stale snapshots | Read fixed source root; store metadata and digests | MVP |
| Evidence-bound explanation | Answers code questions with exact references | Selected current snippets and loopback model | MVP |
| Review report | Records prioritised, attributable findings | Orchard report state only | MVP |
| Patch proposal | Exports an unapplied unified diff | Current source snapshot and export root | MVP |
| Build and test integration | Validates proposed changes | Execution authority | Later, separately reviewed |

### Primary workflow

1. The owner signs in with Orchard-only credentials.
2. Orchard catalogues supported source files without executing or changing
   them.
3. A question or review selects bounded snippets by deterministic retrieval.
4. The model proposes an answer, findings, or patch; Orchard verifies every
   path, range, digest, and patch preimage.
5. The UI labels unverified statements and exports only validated, unapplied
   artefacts while recording a content-minimised audit event.

### Failure behaviour

Authentication, path, type, size, encoding, snapshot, model, patch, or audit
failure stops the affected operation. Source changes during analysis mark the
result stale; Orchard never combines different snapshots. If the model is
unavailable, catalogue and deterministic search remain available, but no AI
review is claimed. Errors omit source content and credentials.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `orchard` | Credentials, questions, controls | Authenticated views and exports | No administrative authority |
| Source cataloguer | `orchard` | Supported repository files | Paths, ranges, metadata, digests | Read-only fixed root |
| Retrieval and evidence verifier | `orchard` | Query, index, current files | Verified snippets and references | Deterministic; no model authority |
| Model bridge | `orchard` | Query and selected snippets | Untrusted proposed analysis | Exact loopback endpoint only |
| Patch validator | `orchard` | Proposed diff and source snapshot | Accepted or rejected bundle | Writes Orchard exports only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Orchard-owned resources only |

Executable code, configuration, credentials, units, and markers are root-owned.
The service uses an empty capability set, `NoNewPrivileges=true`,
`ProtectSystem=strict`, `ProtectHome=true`, `PrivateDevices=true`, explicit
read-only and read-write paths, and loopback-only network access.

### Compromise boundaries

- A compromised service can disclose shared source and corrupt Orchard-owned
  reports, but cannot write or execute the repository.
- A compromised model sees selected snippets and can mislead, but cannot forge
  a valid current digest or invoke tools.
- A stolen owner session permits queries and exports until expiry or revocation,
  but not source mutation or root lifecycle work.
- A failed update retains the previous verified code and compatible state until
  rollback or documented recovery.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `orchard`, `orchard-share` |
| Install root | `/opt/code-orchard` |
| Configuration | `/etc/code-orchard` |
| State | `/var/lib/code-orchard` |
| Shared source | `/srv/code-orchard/repositories` |
| Logs | `/var/log/code-orchard` |
| Units | `code-orchard-*.service` |
| Commands | `orchard-*` |
| Environment | `ORCHARD_*` |
| Loopback ports | `3567` |
| Cookie names | `code_orchard_session` |
| Package names | `code-orchard` |
| Ownership marker | `/var/lib/code-orchard/installation.json` |
| Receipt | `/var/log/code-orchard/management-receipt.json` |
| Firewall rules | None |

Every value is collision-checked. Existing resources are accepted only with
the marker and receipt formats in
[`implementation.md`](implementation.md#ownership-marker-and-receipt).

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Product-specific scrypt hash in protected state | Owner rotation or root reset revokes all sessions |
| Session-signing key | UI service | Random Orchard-only key in `/etc/code-orchard/secrets`, mode `0600` | Rotation revokes all sessions; reinstall preserves it |
| Model credential | None in the first release | Loopback endpoint must require no Orchard-held token | Token-bearing endpoints are unsupported |

Raw credentials never enter arguments, ordinary environment values, source
indexes, model context, logs, reports, receipts, diagnostics, or manager
inventory. Every sibling password, cookie, token, and reset flow is rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Catalogue source | Restricted | Authenticated owner | `source.catalogued` | Supported regular files below fixed root |
| Explain/review | Restricted | Authenticated owner | `review.generated` | Current selected snippets only |
| Export report | Restricted | Authenticated owner | `report.exported` | Orchard-owned export root |
| Export patch | Restricted | Owner confirms snapshot | `patch.exported` | Validated unapplied diff only |
| Delete derived state | Restricted | Owner confirmation | `state.deleted` | Indexes, reports, and exports only |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Source writes, Git mutation, command execution, builds, tests, hooks, and
  dependency installation.
- Paths outside the fixed sharing root and Orchard-owned state.
- Instructions embedded in source that request tools, secrets, policy changes,
  or broader retrieval.

Audits record identifiers, decisions, digests, counts, result codes, and
lifecycle correlation, not prompts, source text, patches, credentials, or model
payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Source files | Review corpus | Owner | Read-only sharing root; excluded from backup | Owner-controlled | Managed outside Orchard |
| Index metadata | Retrieval and staleness | Owner | Mode `0600` SQLite state | Until rebuild or uninstall | Rebuildable and deletable |
| Questions and reports | Review continuity | Owner | Protected SQLite state | 30 days | JSON/Markdown export or deletion |
| Patch bundles | Proposed changes | Owner | Protected export root | 30 days | Unified diff export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Orchard sends only the current question and minimum selected snippets to the
loopback model. It performs no telemetry or training. Backups exclude source
and active sessions. Complete uninstall never removes shared source.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:3567` | Authenticated UI traffic | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Question and selected snippets | Allowed | Exact URL, bounded payload |
| Outbound | Any non-loopback destination | None | Blocked | Service policy and absent tools |

The first release requires a credential-free loopback model and does not own
it. Dry-run performs no network access. Cloud, LAN, redirects, remote source
fetching, and browser automation are unsupported.

## Ubuntu Zombie management contract

The source entry point is `products/code-orchard/scripts/manage.sh`; the
installed root-only command is `/usr/local/sbin/orchard-manage`. It implements
the fixed protocol in
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves plan digest | `lifecycle.install` |
| Verify/doctor/repair | Common lifecycle response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common lifecycle response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common lifecycle response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted product inputs are `owner_user`, `owner_password_file`,
`model_base_url`, `model`, `history_retention_days`,
`audit_retention_days`, `backup_destination`, and `retain_state`. Unknown keys
fail closed; only `owner_password_file` is secret.

Zombie may retain product and instance IDs, version, marker and receipt
digests, coarse health, operation result, and correlation ID. It must not
retain source paths below the fixed root, filenames, digests, questions,
reports, patches, credentials, sessions, or model payloads. The `orchard`
service cannot invoke either management plane.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject identity, path, port, command, unit, cookie, package, and ownership
  collisions before mutation.
- Verify artefact, checksum, signature, provenance, SBOM, descriptor, and
  pinned source lesson set.
- Validate owner, storage, sharing-root ownership, model configuration, and
  rollback readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select existing local user | `ORCHARD_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `ORCHARD_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `ORCHARD_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `ORCHARD_MODEL` | Non-empty; required unattended |
| History retention | Review default `30` | `ORCHARD_HISTORY_RETENTION_DAYS` | Integer `0..365` |
| Audit retention | Review default `90` | `ORCHARD_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`ORCHARD_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Unattended
mode never prompts and exits `64` before mutation when required input is
missing. Raw secrets are accepted only through protected files.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and stable digest.
2. Revalidate release, plan, ownership, collisions, and model under the lock.
3. Create identities and protected directories.
4. Write credentials and configuration atomically.
5. Install root-owned code and the confined service.
6. Create the read-only source sharing root, state, logs, marker, and receipt.
7. Start only after integrity and boundary checks pass.

### Idempotence

A valid marker, descriptor, inventory, and receipt identify an installation.
Reinstall preserves credentials, source, reports, retention, and instance ID
unless rotation or reset is requested. It repairs only Orchard-owned resources
and refuses every unmarked collision.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, boundary, marker, receipt |
| `verify` | Check ownership, confinement, schemas, source identity, and model | No | Human and JSON results |
| `doctor` | Explain drift and recovery | No | Redacted diagnosis |
| `repair` | Restore known-safe Orchard resources and derived indexes | Yes | Reverification without source change |
| `backup` | Archive protected Orchard state, excluding source and sessions | Yes | Verified manifest and digest |
| `update` | Verify, back up, stage, migrate, switch, and health-check | Yes | New version and audit |
| `rollback` | Restore a supported version and compatible state | Yes | Prior health checks |
| `suspend` | Stop analysis and revoke sessions | Yes | Inactive service and state |
| `resume` | Revalidate boundaries before start | Yes | Healthy service |
| `uninstall` | Remove only owned resources; preserve or confirm state deletion | Yes | Removal report and source hash stability |

## Update and migration design

Updates accept supported source versions, preserve credentials and owner data,
verify a backup, migrate a staged copy, switch code atomically, and run source
immutability and confinement gates. Failure restores the previous verified
version or returns bounded recovery. Audit records omit private content and
tests prove no source or sibling resource changed.

## Co-installation

Orchard supports standalone installation and co-installation with every current
family product. Tests prove unique namespaces, cross-login rejection,
service-account denial against sibling roots, source immutability, independent
lifecycle operations, stable non-target hashes and start times, and exact
Zombie target selection. A dedicated machine is required if source must be
hidden from a same-host root administrator.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/code-orchard/audit.jsonl` | Policy and lifecycle events | No source, prompts, patches, or secrets |
| Service journal | `code-orchard-chat.service` | Startup, health, bounded errors | Operator-readable; payload-free |
| Health check | `orchard-health` | Service, model, index, source identity | Coarse public result |
| Diagnostics | `orchard-diagnostics` | Versions, permissions, units, checks | Excludes private content |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `orchard-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, required-input exit `64`, dry-run,
      and idempotent reinstall.
- [ ] Ownership, confinement, authentication, rotation, and redaction.
- [ ] Supported parsing, retrieval, references, patch validation, and stale
      snapshot handling.
- [ ] Shell, execution, repository-write, traversal, link, race, host-read,
      sibling-read, and non-loopback attempts fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and Zombie-managed paths produce equivalent target state and
      correlated audits.

### Product-specific red team

- Place prompt injection in source comments and filenames; it must remain data.
- Make the model invent paths, lines, digests, and patch preimages; validation
  must reject them.
- Change files throughout retrieval and generation; mixed snapshots must never
  be presented.
- Compromise `orchard` and prove repository writes, execution, sibling reads,
  and management calls remain unavailable.
- Attack lifecycle operations with unowned paths, links, and malicious
  artefacts; mutation must fail closed.

### Co-installation matrix

- [ ] Orchard alone and with each current product.
- [ ] Every supported three-product combination containing Orchard.
- [ ] All current family products together.
- [ ] Operate and remove Orchard while source and siblings remain unchanged.
- [ ] Manage Orchard through Ubuntu Zombie without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Source prompt injection | Unsafe or misleading review | Delimited data, absent tools, deterministic references | Discard result and review source | Injection corpus |
| Repository escape | Private host disclosure | Descriptor-relative no-follow traversal and confinement | Suspend, repair, review audit | Path and race suite |
| Fabricated finding or patch | Owner applies an invalid change | Digest, range, preimage, and diff validation | Reject or mark stale | Malicious-model fixtures |
| Service compromise | Source disclosure or report corruption | Least privilege, read-only root, root-owned code | Suspend, reinstall, rotate sessions | Compromised-process VM |
| Malicious release | Root-level lifecycle compromise | Signed verified artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes misleading analysis and owner application of an unsafe
patch. Orchard validates provenance, not semantic correctness.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Safe convergence remains necessary | Reinstall tests |
| Policy and audit gate | Keep with content minimisation | Exports and deletion need accountability | Policy and redaction tests |
| Root-capable account | Remove | Code review needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Orchard requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Owner needs immediate revocation | Lifecycle tests |
| Update and recovery | Keep with source immutability | Source is not product state | Hash and rollback tests |

**Measurable improvement:** 100% of displayed code references and exported
patch preimages must validate against one current source snapshot in the
malicious-model and concurrent-change suites.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Code Orchard is a private local code-review assistant that reads one shared
> source tree and exports evidence-bound reports and unapplied patch proposals.

### Prohibited claims

- That Orchard proves code correct, secure, licensed, tested, or deployable.
- That local operation hides source from a same-host root administrator.
- That a generated patch was applied, compiled, or tested.
- That this definition represents implemented or released software.

### Out of scope

- Command execution, builds, tests, Git mutation, package management, CI, and
  deployment.
- Remote repositories, cloud models, multiple owners, IDE plugins, and
  autonomous changes.
- Host administration, professional security certification, and legal advice.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Orchard | Repository maintainers | First implementation change |
| Source parser fixture | Binary and generated-file behaviour must be exact | Product maintainers | First runtime change |
| Patch validator review | Diff ambiguity can misrepresent proposed changes | Security reviewers | Implementation approval |
| Disposable-VM boundary | Permissions and confinement need host proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, source-flow, and trust-boundary diagrams.
- [ ] Threat model, security policy, and disclosure process.
- [ ] Privacy, retention, export, and deletion model.
- [ ] Source catalogue, evidence, finding, and patch schemas.
- [ ] Configuration, credential rotation, lifecycle, and recovery.
- [ ] Test strategy, adversarial corpus, and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires product lint, tests, package and artefact verification,
standalone VM lifecycle, negative security and source-immutability suites,
co-installation evidence, changelog, and version. Family admission additionally
requires manager and contract evidence. Unproven claims remain labelled as
planned.
