# Project Compass

> A private local planning assistant that turns one owner's goals into
> reviewable projects, tasks, dependencies, and decisions without reading a
> workspace or performing the work.

Project Compass complements the family with structured planning rather than
conversation, document retrieval, code review, or host administration. It is
not an Imaginary Friend mode, team tracker, calendar, or autonomous worker.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `project-compass` |
| Human need | Break personal goals into a coherent, inspectable plan without granting an AI access to files, accounts, or execution tools |
| Intended users | One adult owner |
| Operator | The owner or machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read and write only Compass-owned project, task, decision, export, and audit state |
| Default Linux identity | Non-login `compass` account and group |
| Default loopback port | `2323` |
| Install root | `/opt/project-compass` |
| Configuration root | `/etc/project-compass` |
| State root | `/var/lib/project-compass` |
| Log root | `/var/log/project-compass` |
| Environment prefix | `COMPASS_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; goals, projects, tasks, and credentials stay out of manager inventory |
| Source root | `products/project-compass/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Project Compass records owner-entered goals and constraints, asks a local model
for candidate milestones and tasks, and stores only owner-confirmed structured
plans. Deterministic code owns identifiers, dependencies, dates, status, and
change history. Local installation supports private long-lived planning with a
small, testable authority boundary.

The first release supports one owner, multiple personal projects, text input,
dependency-aware task lists, local exports, a loopback UI, and one
credential-free loopback model. It reads no workspace and performs no task.

### It must

- distinguish owner-entered facts, model proposals, owner confirmations, and
  later corrections;
- reject dependency cycles, impossible date constraints, silent status
  changes, and ambiguous destructive edits; and
- let the owner inspect, export, archive, reset, suspend, and delete every
  Compass-owned record.

### It must not

- execute tasks, read project files, run commands, contact people, spend money,
  schedule calendars, or update another service;
- claim that estimated effort, dates, priorities, or outcomes are guaranteed;
  or
- infer employer, team, legal, medical, financial, or safety authority from a
  goal description.

## Status and evidence

This document fixes a first product slice. No Compass source, installer,
catalogue admission, validation evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Project, task, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/project-compass/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Compass release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Create goals, review proposals, edit plans, record status, export, archive, suspend, and delete | Treat a plan as completed work or delegated authority |
| Machine operator | Install, update, back up, recover, and uninstall | Read private projects as an ordinary lifecycle action |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain goal, task, decision, schedule, or credential data |
| `compass` service | Operate only on Compass-owned state | Inspect the host, execute tasks, contact people, or invoke lifecycle commands |
| Model endpoint | Propose plan structures from current owner input | Confirm facts, mutate authoritative state, or invoke tools |

### Authority ceiling

The service accepts authenticated loopback requests, reads and writes only
Compass-owned state and exports, and calls one loopback model endpoint. It has
no `sudo`, shell, subprocess, general filesystem, browser, internet, email,
calendar, contacts, package, service, device, payment, or sibling access.

Owner authentication permits planning, not machine or external authority. A
prompt, project label, model proposal, or confirmation cannot add a tool or
path.

### Authority inherited, retained, and removed

- Independent installation, authentication, policy, audit, lifecycle,
  diagnostics, backup, and release verification are retained.
- Root, shell, host reads, workspace access, package, service, network, account,
  and device controls are removed.
- General conversational memory is replaced by explicit project records.
- Family management, external integrations, and proactive communication are
  removed.
- Model authority over status, dates, dependencies, and owner facts is removed.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Goal and constraint record | Makes project intent explicit | Owner-entered Compass state | MVP |
| Plan proposal | Offers milestones and tasks for review | Current project context and local model | MVP |
| Dependency validation | Prevents cyclic or dangling plans | Structured task graph | MVP |
| Decision and status history | Shows how and why a plan changed | Append-only Compass records | MVP |
| Portable export | Produces JSON and Markdown plan snapshots | Compass export root | MVP |
| Workspace and account integrations | Observes or performs work | External authority | Out of scope |

### Primary workflow

1. The owner authenticates and records a goal, constraints, known facts, and
   desired review horizon.
2. Compass asks the model for a schema-constrained proposal containing
   milestones, tasks, dependencies, assumptions, and questions.
3. Deterministic validation rejects cycles, missing identifiers, invalid dates,
   and undeclared status changes.
4. The owner confirms, edits, or rejects each proposal before it enters the
   authoritative plan.
5. Later status and decisions are owner-entered, versioned, exportable, and
   recorded in a content-minimised audit.

### Failure behaviour

Compass rejects malformed model output, dependency cycles, impossible dates,
unknown identifiers, stale versions, unauthorised bulk deletion, retention
failure, and audit failure. It never infers completion from time passing. If
the model is unavailable, existing plan review, manual editing, graph
validation, status updates, export, and deletion remain available.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `compass` | Credentials, goals, edits, controls | Authenticated planning views | No external or host authority |
| Project store | `compass` | Owner-confirmed records | Versioned projects, tasks, decisions | Compass state only |
| Model bridge | `compass` | Bounded current project context and schema | Untrusted plan proposal | Exact loopback endpoint only |
| Graph and date validator | `compass` | Proposed or edited plan | Accepted structure or errors | Deterministic |
| Export service | `compass` | Selected confirmed project version | JSON and Markdown | Compass export root only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Compass-owned resources only |

Root owns code, configuration, policy, credentials, units, and markers. The
service has no capabilities, strict filesystem protection, private devices,
explicit state paths, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose or corrupt Compass plans, but cannot read
  work products or perform tasks.
- A compromised model sees bounded project context and can manipulate
  proposals, but cannot confirm them or access tools.
- A stolen owner session permits planning and export until expiry or
  revocation, but no host or external action.
- A failed update retains the previous verified version and protected,
  compatible project backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `compass` |
| Install root | `/opt/project-compass` |
| Configuration | `/etc/project-compass` |
| State | `/var/lib/project-compass` |
| Logs | `/var/log/project-compass` |
| Units | `project-compass-*.service` |
| Commands | `compass-*` |
| Environment | `COMPASS_*` |
| Loopback ports | `2323` |
| Cookie names | `project_compass_session` |
| Package names | `project-compass` |
| Ownership marker | `/var/lib/project-compass/installation.json` |
| Receipt | `/var/log/project-compass/management-receipt.json` |
| Firewall rules | None |

Every resource is collision-checked and existing state is recognised only with
the common ownership marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Compass-specific scrypt hash in protected state | Owner rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Compass-only key in `/etc/project-compass/secrets`, mode `0600` | Rotation revokes sessions |
| Model or integration credential | None | Never accepted in the first release | Unsupported |

Raw credentials never enter project records, model context, arguments,
ordinary environment values, logs, receipts, diagnostics, or manager
inventory. Every sibling credential and reset flow is rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Create/edit owner fact | Restricted | Owner | `project.changed` | Compass state only |
| Generate plan proposal | Restricted | Owner request | `plan.proposed` | Current project version and local model |
| Confirm proposal | Restricted | Owner | `plan.confirmed` | Validated item and current version |
| Update status/decision | Restricted | Owner | `status.changed` | Existing project records only |
| Export/archive/delete | Restricted | Owner; deletion requires confirmation | `project.lifecycle` | Compass-owned state |
| Product lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Workspace reads or writes, shell, browser, email, calendar, contacts, task
  execution, payments, purchases, notifications, and third-party APIs.
- Model confirmation of facts, commitments, status, deletion, or authority.
- Paths outside Compass state and every sibling product.

Audits contain event IDs, actor/session IDs, project pseudonyms, version and
item counts, decisions, results, and correlation IDs. They exclude goals, task
text, decisions, schedules, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Goals and constraints | Define project intent | Owner | Mode `0600` SQLite | Until owner archives or deletes | JSON/Markdown |
| Plan versions and tasks | Track accepted structure | Owner | Protected versioned SQLite | Until owner deletion | JSON/Markdown |
| Decisions and status | Preserve changes and provenance | Owner | Append-only protected records | Until owner deletion | Included in export |
| Model proposals | Review and trace suggestions | Owner | Protected SQLite, source-labelled | 30 days if rejected; accepted provenance retained | Export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Compass processes only owner-entered project data and performs no file
discovery, telemetry, or training. The loopback model receives only the current
bounded project context. Backups exclude active sessions and use
operator-controlled protection.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2323` | Authenticated planning traffic | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Current bounded project context and schema | Allowed | Exact URL and payload limits |
| Outbound | Internet, calendars, mail, task systems, or other agents | None | Blocked | Network policy and absent clients |

The first release requires a credential-free loopback model. Dry-run performs
no network access. Import from and export to third-party planning systems are
unsupported.

## Ubuntu Zombie management contract

The source entry point is `products/project-compass/scripts/manage.sh`; the
installed command is `/usr/local/sbin/compass-manage`. It follows
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `owner_user`, `owner_password_file`, `model_base_url`,
`model`, `proposal_retention_days`, `audit_retention_days`,
`backup_destination`, and `retain_state`. Unknown keys fail closed.

Zombie inventory may retain identifiers, version, marker and receipt digests,
coarse health, result, and correlation ID. It must not retain project counts,
goals, tasks, status, dates, decisions, credentials, or model payloads. The
`compass` service cannot invoke management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject namespace and ownership collisions before mutation.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor, and
  pinned source lesson set.
- Validate owner, storage, loopback model, backup, and rollback readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select existing local user | `COMPASS_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `COMPASS_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `COMPASS_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `COMPASS_MODEL` | Non-empty; required unattended |
| Proposal retention | Review default `30` | `COMPASS_PROPOSAL_RETENTION_DAYS` | Integer `0..365` |
| Audit retention | Review default `90` | `COMPASS_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`COMPASS_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and stable digest.
2. Revalidate release, plan, ownership, collisions, and endpoint under lock.
3. Create the identity and protected directories.
4. Write credentials, schemas, retention, and configuration atomically.
5. Install root-owned code and confined services.
6. Create project state, logs, marker, and receipt.
7. Start after graph, date, privacy, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, confirmed plan versions, decisions, status,
retention, and instance ID. It never regenerates or changes confirmed plans
silently and refuses every unmarked collision.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, graph fixtures, marker, receipt |
| `verify` | Check ownership, confinement, schemas, graph integrity, and model | No | Human and JSON results |
| `doctor` | Explain graph, date, model, retention, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe resources and derived indexes | Yes | Reverification without plan changes |
| `backup` | Archive Compass state, excluding sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code and compatible state | Yes | Prior health checks |
| `suspend` | Stop planning and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate graph and privacy before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report |

## Update and migration design

Updates preserve credentials, owner facts, confirmed plan versions,
dependencies, decisions, status, retention, and instance ID; verify a backup;
migrate staged state; rerun graph and date fixtures; and switch atomically.
Failure restores the previous verified version. Sibling resources remain
unchanged.

## Co-installation

Compass supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, independent lifecycle operations, stable non-target hashes and service
times, and exact Zombie target selection. Compass cannot read an Imaginary
Friend workspace or Code Orchard source.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/project-compass/audit.jsonl` | Policy and lifecycle events | No goal, task, decision text, or secrets |
| Service journal | `project-compass-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `compass-health` | Service, model, schema, graph integrity | Coarse public result |
| Diagnostics | `compass-diagnostics` | Versions, permissions, units, checks | Excludes project data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `compass-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, session revocation, proposal labels, and redaction.
- [ ] Project versions, graph validation, date constraints, owner confirmation,
      decisions, status, retention, archive, and export.
- [ ] Prompt injection, cyclic plans, silent status changes, workspace access,
      external integrations, sibling access, and egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Put instructions in goals that demand shell, messaging, payment, workspace,
  or policy access; they must remain text.
- Make the model claim a task is complete, invent owner commitments, hide a
  dependency, or create a cycle; validation and confirmation must stop it.
- Replay stale edits against a newer plan version; optimistic concurrency must
  reject them.
- Compromise `compass` and prove filesystem, network, sibling, and management
  access remain unavailable.
- Attack migrations with invalid graphs; rollback must preserve the last valid
  version.

### Co-installation matrix

- [ ] Compass alone and with each current family product.
- [ ] Compass with Friend and Orchard, proving workspace/source separation.
- [ ] Every supported three-product combination containing Compass.
- [ ] All current family products together.
- [ ] Operate, manage, and remove Compass without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Manipulative plan proposal | Owner accepts unsafe or irrelevant work | Proposal labels, explicit confirmation, absent tools | Reject or restore plan version | Malicious-model fixtures |
| Graph or date corruption | Incoherent project state | Deterministic validation and versioned transactions | Restore last valid version | Property and corruption tests |
| Project-data disclosure | Personal or commercial privacy harm | Local endpoint, protected state, content-free logs | Suspend, rotate, delete | Egress and redaction suite |
| Service compromise | Plan disclosure or corruption | Least privilege and root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |
| Malicious release | Root-level compromise | Verified signed artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes unrealistic estimates, missed constraints, and human
over-reliance on a plan that has not performed or observed any work.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Long-lived plans need safe convergence | Reinstall tests |
| Policy and audit gate | Keep with project-data minimisation | Confirmation and deletion need accountability | Redaction tests |
| Root-capable account | Remove | Planning needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Compass requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Owner needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with graph validation | Plans must remain coherent across migrations | Migration tests |

**Measurable improvement:** no model proposal may enter authoritative project
state without schema, acyclic-graph, date, current-version, and explicit owner
confirmation checks, each covered by a failing adversarial fixture.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Project Compass is a private local planning assistant that stores only
> owner-confirmed goals, tasks, dependencies, decisions, and status.

### Prohibited claims

- That Compass performs, observes, delegates, guarantees, or certifies project
  work.
- That model estimates or dates are commitments or professional advice.
- That local operation hides plans from same-host root.
- That this definition represents implemented or released software.

### Out of scope

- Workspace and repository access, commands, task execution, calendars, email,
  contacts, payments, purchasing, notifications, and third-party APIs.
- Teams, employers, remote users, shared projects, performance monitoring, and
  autonomous management.
- Legal, medical, financial, construction, and other professional planning
  claims.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Compass | Repository maintainers | First implementation change |
| Canonical project schema | Versioning and dependency semantics must be stable | Product maintainers | First runtime change |
| Manipulation review | Planning recommendations can shape owner behaviour | Safety reviewers | Implementation approval |
| Graph and migration fixtures | Corruption must fail closed and recover | Security reviewers | Release candidate |
| Disposable-VM boundary | Confinement and egress need host evidence | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, project flow, and threat model.
- [ ] Privacy, retention, archive, export, and deletion model.
- [ ] Project, task, dependency, decision, proposal, and export schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Graph fixtures, red-team strategy, and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, graph and
version fixtures, standalone VM lifecycle, negative security and manipulation
suites, co-installation evidence, changelog, and version. Family admission also
requires manager and contract evidence. Unproven planning, privacy, or security
claims remain visibly planned.
