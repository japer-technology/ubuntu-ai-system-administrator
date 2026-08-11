# Maintenance Atlas

> A private local household-maintenance assistant that turns owner-entered
> asset records and deliberately shared manuals into cited schedules and
> reminders without controlling equipment.

Maintenance Atlas complements the family by organising physical asset care. It
is not a host administrator, smart-home controller, repair professional,
warranty authority, or general research library.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `maintenance-atlas` |
| Human need | Keep household equipment maintained using attributable records and manufacturer guidance |
| Intended users | One adult owner and household members they authorise |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read supported manuals in one fixed library and write Atlas-owned asset, maintenance, reminder, report, and audit state |
| Default Linux identity | Non-login `atlas` account and group |
| Default loopback port | `2828` |
| Install root | `/opt/maintenance-atlas` |
| Configuration root | `/etc/maintenance-atlas` |
| State root | `/var/lib/maintenance-atlas` |
| Log root | `/var/log/maintenance-atlas` |
| Environment prefix | `ATLAS_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; asset and household data stay out of manager inventory |
| Source root | `products/maintenance-atlas/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Maintenance Atlas records owner-declared appliances, tools, vehicles, and
other household assets, indexes deliberately shared text manuals, and proposes
maintenance schedules with citations to exact source passages. Deterministic
calendar code owns dates and recurrence; a local model helps match plain
language and explain cited guidance.

The first release supports one owner, manual asset entry, UTF-8 text and
Markdown manuals, local reminders in the authenticated UI, and one
credential-free loopback model. It has no device, vehicle, vendor, messaging,
or purchasing connection.

### It must

- preserve the source, date, actor, and correction history for asset and
  maintenance records;
- distinguish owner-entered intervals, cited manufacturer guidance, model
  suggestions, and completed work; and
- let the owner review, correct, export, postpone, suspend, and delete all
  Atlas-owned records.

### It must not

- operate equipment, order parts, book services, submit warranty claims, or
  send reminders outside the local UI;
- claim that a schedule makes equipment safe, compliant, warranted, or fit for
  use; or
- invent specifications, bypass warnings, or turn manual text into executable
  instructions.

## Status and evidence

This document fixes a first product slice. Atlas has no source, installer,
catalogue admission, test evidence, or release. Planned controls below are not
implemented safeguards.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Asset, manual, reminder, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/maintenance-atlas/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Atlas release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Add assets, share manuals, confirm schedules and work, export, suspend, and delete | Treat an Atlas suggestion as proof of safety or professional inspection |
| Household member | View or update only owner-granted assets | Gain machine or unrelated household authority |
| Machine operator | Install, configure, update, recover, and uninstall | Infer consent to process third-party records |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain asset names, locations, serials, manuals, schedules, or secrets |
| `atlas` service | Read fixed manuals and write Atlas state | Control devices, contact vendors, inspect the host, or invoke lifecycle commands |
| Model endpoint | Suggest matches and explanations from selected records | Set authoritative intervals, mark work complete, or bypass warnings |

### Authority ceiling

The service accepts authenticated loopback requests, reads supported regular
files below `/srv/maintenance-atlas/library`, writes Atlas state and reports,
and calls one loopback model. It has no `sudo`, shell, subprocess, hardware
device, Bluetooth, serial, vehicle, smart-home, browser, package, service,
internet, email, or purchasing capability.

Manual traversal is descriptor-relative and rejects links, devices, mount
changes, unsupported encodings, and files over 16 MiB. A prompt, password,
manual instruction, or confirmation cannot grant physical control.

### Authority inherited, retained, and removed

- Independent installation, authentication, policy, audit, lifecycle,
  diagnostics, backup, and release verification are retained.
- General root, shell, host reads, package, service, account, network, and
  device controls are removed.
- Workspace writes are replaced by a read-only manual library and Atlas-owned
  records.
- Model authority over dates, completion, and safety status is removed.
- Family management and proactive external communication are removed.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Asset register | Keeps attributable equipment details | Owner-entered Atlas state | MVP |
| Manual catalogue | Finds current guidance | Read fixed manual library; store digests | MVP |
| Cited maintenance proposal | Connects an asset to source guidance | Asset fields, selected manual passages, local model | MVP |
| Deterministic schedule | Calculates due dates reproducibly | Owner-confirmed interval and completion dates | MVP |
| Local dashboard and export | Shows due work and portable history | Atlas state and export root | MVP |
| Device integration or external reminders | Automates action | Hardware or network authority | Later, separately reviewed |

### Primary workflow

1. The owner signs in with Atlas-only credentials and records an asset.
2. Atlas catalogues deliberately shared manuals and stores path, range, and
   digest metadata without altering them.
3. Retrieval selects likely passages; the model proposes a maintenance item
   with source references and uncertainty.
4. Atlas verifies citations and requires the owner to confirm the interval and
   first due date before scheduling.
5. The owner records completion or correction; Atlas recalculates
   deterministically and writes a content-minimised audit event.

### Failure behaviour

Atlas rejects ambiguous asset identity, unsupported manuals, missing units,
invalid dates, impossible recurrence, stale citations, model failure, and
failed audit. It never silently guesses a serial, specification, interval, or
completion. If the model is unavailable, asset records, confirmed schedules,
manual search, and local reminders remain available.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `atlas` | Credentials, asset records, confirmations | Authenticated views and controls | No device or host authority |
| Manual cataloguer | `atlas` | Supported manual files | Metadata, passages, digests | Read-only fixed root |
| Retrieval and citation verifier | `atlas` | Asset query, index, current files | Verified source passages | Deterministic |
| Model bridge | `atlas` | Minimised asset fields and selected passages | Untrusted proposed guidance | Exact loopback endpoint only |
| Schedule engine | `atlas` | Confirmed interval and event dates | Due dates and reminders | Deterministic; model cannot write |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Atlas-owned resources only |

Code, configuration, policy, credentials, units, and markers are root-owned.
The service has no capabilities or privilege escalation and receives explicit
read-only and read-write paths with loopback-only networking.

### Compromise boundaries

- A compromised service can disclose manuals and Atlas records or corrupt
  Atlas state, but cannot control equipment or write manuals.
- A compromised model can mislead and observe selected context, but cannot
  create a confirmed schedule or completion record.
- A stolen session permits scoped record access until expiry or revocation,
  but no root or physical action.
- A failed update retains the previous verified version and protected state
  backup until recovery.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `atlas`, `atlas-share` |
| Install root | `/opt/maintenance-atlas` |
| Configuration | `/etc/maintenance-atlas` |
| State | `/var/lib/maintenance-atlas` |
| Manual library | `/srv/maintenance-atlas/library` |
| Logs | `/var/log/maintenance-atlas` |
| Units | `maintenance-atlas-*.service` |
| Commands | `atlas-*` |
| Environment | `ATLAS_*` |
| Loopback ports | `2828` |
| Cookie names | `maintenance_atlas_session` |
| Package names | `maintenance-atlas` |
| Ownership marker | `/var/lib/maintenance-atlas/installation.json` |
| Receipt | `/var/log/maintenance-atlas/management-receipt.json` |
| Firewall rules | None |

Every value is collision-checked and existing resources require the common
ownership marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Atlas-specific scrypt hash in protected state | Owner rotation or root reset revokes all sessions |
| Member password | Optional scoped login | Independent salted hash and role record | Owner revocation removes access |
| Session-signing key | UI service | Random Atlas-only key in `/etc/maintenance-atlas/secrets`, mode `0600` | Rotation revokes every session |
| Vendor or model credential | None | Never accepted in the first release | Unsupported |

Asset serials and locations are sensitive data, not credentials. Neither they
nor raw secrets enter operational logs, receipts, diagnostics, manager
inventory, or ordinary environment values. Sibling credentials are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Manage asset record | Restricted | Owner or scoped member | `asset.changed` | Atlas state only |
| Catalogue/search manual | Restricted | Authenticated user | `manual.searched` | Fixed read-only library |
| Propose maintenance | Restricted | Owner confirms schedule | `schedule.proposed` | Verified passages and local model |
| Record completion | Restricted | Authorised user | `maintenance.recorded` | Existing asset and valid date |
| Export history | Restricted | Owner | `history.exported` | Atlas export root |
| Delete state | Restricted | Owner confirmation | `state.deleted` | Atlas-owned records only |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Device, vehicle, building-control, vendor, booking, payment, shopping,
  messaging, and warranty operations.
- Manual writes, host inspection, sibling access, or arbitrary filesystem
  paths.
- Model confirmation of schedules, completion, safety, compliance, or owner
  authority.

Audit records include event IDs, actors, asset pseudonyms, source digests,
decisions, dates, results, and correlation IDs. They exclude serials,
locations, manual text, notes, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Manual files | Maintenance evidence | Owner | Read-only library; excluded from backup | Owner-controlled | Managed outside Atlas |
| Asset records | Identify and organise equipment | Owner | Mode `0600` SQLite | Until owner deletion | Versioned JSON/CSV |
| Schedules and completion history | Plan and record care | Owner | Protected SQLite with provenance | Until owner deletion | JSON/CSV export |
| Reports | Portable owner review | Owner | Protected export root | 90 days | Export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Atlas minimises third-party names and sends only selected asset fields and
manual passages to the loopback model. It performs no telemetry or training.
Backups exclude manuals and active sessions. Complete uninstall never deletes
the manual library.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2828` | Authenticated UI traffic | Open after healthy install | Password, scoped session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Minimised asset fields and selected passages | Allowed | Exact URL and bounded payload |
| Outbound | Vendors, devices, internet, LAN, email, or messaging | None | Blocked | Network policy and absent clients |

Dry-run makes no network request. The first release neither discovers devices
nor checks manufacturer sites, recalls, regulations, or warranty systems.

## Ubuntu Zombie management contract

The source entry point is `products/maintenance-atlas/scripts/manage.sh`; the
installed command is `/usr/local/sbin/atlas-manage`. It implements the fixed
contract in [`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `owner_user`, `owner_password_file`, `model_base_url`,
`model`, `audit_retention_days`, `backup_destination`, and `retain_state`.
Unknown keys fail closed; only the password file is secret.

Zombie may retain identifiers, version, marker and receipt digests, coarse
health, result, and correlation ID. It must not retain household identities,
asset data, manual metadata, schedules, reports, credentials, or model
payloads. The `atlas` service cannot invoke management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject identity, path, port, command, unit, cookie, package, and ownership
  collisions.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor, and
  pinned source lesson set.
- Validate owner, storage, manual boundary, loopback model, backup, and
  rollback readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select existing local user | `ATLAS_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `ATLAS_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `ATLAS_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `ATLAS_MODEL` | Non-empty; required unattended |
| Audit retention | Review default `90` | `ATLAS_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`ATLAS_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
file references only.

### Dry-run and mutation order

1. Render the complete no-write, no-network plan and digest.
2. Revalidate release, plan, ownership, and collisions under the lock.
3. Create identities and protected directories.
4. Write credentials, configuration, and schedule rules atomically.
5. Install root-owned code and confined services.
6. Create the read-only manual root, state, logs, marker, and receipt.
7. Start after schedule, citation, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, assets, schedules, history, retention, and
instance ID. It repairs only Atlas-owned resources, never alters manuals, and
refuses every unmarked collision.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, schedule fixtures, marker, receipt |
| `verify` | Check ownership, confinement, schemas, library identity, and model | No | Human and JSON results |
| `doctor` | Explain manual, schedule, model, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe resources and derived indexes | Yes | Reverification without manual changes |
| `backup` | Archive Atlas state, excluding manuals and sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code and compatible state | Yes | Prior health checks |
| `suspend` | Stop reminders and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate boundaries and schedules before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report; manuals unchanged |

## Update and migration design

Updates preserve credentials, provenance, asset records, confirmed schedules,
history, and instance ID; verify a protected backup; migrate staged state;
rerun date fixtures; and switch atomically. Failure restores the previous
verified version or returns recovery guidance. Tests prove manuals and sibling
resources remain unchanged.

## Co-installation

Atlas supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, manual immutability, independent lifecycle operations, stable
non-target hashes and service times, and exact Zombie target selection.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/maintenance-atlas/audit.jsonl` | Policy and lifecycle events | No serials, locations, manual text, or secrets |
| Service journal | `maintenance-atlas-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `atlas-health` | Service, model, schemas, schedule fixtures | Coarse public result |
| Diagnostics | `atlas-diagnostics` | Versions, permissions, units, checks | Excludes household data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `atlas-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, scoped roles, session revocation, and redaction.
- [ ] Manual catalogue, citation checks, asset provenance, recurrence, dates,
      reminders, corrections, and exports.
- [ ] Prompt injection, invalid units, impossible dates, path escape, manual
      writes, device access, sibling access, and egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Put unsafe instructions and fake specifications in manuals; citations must
  not become verified safety claims or executable actions.
- Make the model invent an interval, manual passage, completion, recall, or
  warranty status; deterministic checks and labels must reject it.
- Race and replace manual files during retrieval; mixed snapshots must fail.
- Compromise `atlas` and prove device, vendor, source-write, sibling, and
  management access remain unavailable.
- Attack migration and removal with unowned resources; mutation must remain
  target-scoped.

### Co-installation matrix

- [ ] Atlas alone and with each current family product.
- [ ] Every supported three-product combination containing Atlas.
- [ ] All current family products together.
- [ ] Operate and remove Atlas while manuals and siblings remain unchanged.
- [ ] Manage Atlas through Ubuntu Zombie without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Unsafe or injected manual text | Harmful maintenance guidance | Source labelling, citations, absent tools, prominent warnings | Reject item and retain source for review | Adversarial manual corpus |
| Invented schedule or completion | Missed work or false confidence | Human confirmation and append-only provenance | Correct record and recalculate | Malicious-model fixtures |
| Asset-data disclosure | Household privacy harm | Local model, minimised context, protected paths | Suspend, rotate, delete data | Egress and redaction suite |
| Service compromise | Record disclosure or corruption | Least privilege, read-only manuals, root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |
| Malicious release | Root-level compromise | Verified signed artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes incomplete manuals, owner data-entry errors, outdated
guidance, and physical hazards that software cannot inspect.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Long-lived records need safe convergence | Reinstall tests |
| Policy and audit gate | Keep with household-data minimisation | Changes and deletion need accountability | Redaction tests |
| Root-capable account | Remove | Planning needs no host or device control | Capability-negative tests |
| Chat authentication | Replace | Atlas requires independent scoped roles | Cross-login tests |
| Lifecycle/kill switch | Keep | Owner needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with date fixtures | Schedules must survive migrations exactly | Migration tests |

**Measurable improvement:** every due date must be reproducible from a
confirmed interval and attributable completion record, and every
manufacturer-derived interval must retain a current verified citation.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Maintenance Atlas is a private local assistant for cited household
> maintenance schedules built from owner-entered asset records and shared
> manuals.

### Prohibited claims

- That Atlas certifies safety, compliance, warranty, recall status, or
  professional workmanship.
- That a reminder proves work was performed or an asset is safe.
- That local operation hides records from same-host root.
- That this definition represents implemented or released software.

### Out of scope

- Device control, telemetry, smart-home automation, vendor accounts, booking,
  purchasing, messaging, warranty claims, and emergency response.
- Cloud models, remote access, business fleet management, regulated
  inspections, and autonomous repairs.
- PDF/OCR/image manual extraction in the first release.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Atlas | Repository maintainers | First implementation change |
| Canonical asset and recurrence schema | Ambiguous units and dates can create bad reminders | Product maintainers | First runtime change |
| Safety-language review | Users may over-trust cited guidance | Safety reviewers | Implementation approval |
| Manual boundary VM proof | Permissions and source immutability need host evidence | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, data flow, and threat model.
- [ ] Privacy, household roles, retention, export, and deletion model.
- [ ] Asset, manual citation, schedule, completion, and report schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Date fixtures, adversarial manuals, and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, schedule
fixtures, standalone VM lifecycle, negative security and safety suites,
co-installation evidence, changelog, and version. Family admission also
requires manager and contract evidence. Unproven claims remain visibly planned.
