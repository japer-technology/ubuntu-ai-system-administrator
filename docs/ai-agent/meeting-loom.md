# Meeting Loom

> A private local assistant that turns deliberately imported meeting
> transcripts into cited summaries, decisions, and proposed action items
> without recording people or contacting them.

Meeting Loom complements the family with a consent-aware, time-bounded meeting
record. It is not a recorder, surveillance service, calendar client, task
executor, general document library, or source of organisational authority.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `meeting-loom` |
| Human need | Review what was said and agreed in a meeting without uploading the transcript or inventing commitments |
| Intended users | One adult owner processing meetings they are authorised to record or receive |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read supported transcripts in one fixed inbox and write Loom-owned summaries, corrections, action proposals, exports, and logs |
| Default Linux identity | Non-login `loom` account and group |
| Default loopback port | `2525` |
| Install root | `/opt/meeting-loom` |
| Configuration root | `/etc/meeting-loom` |
| State root | `/var/lib/meeting-loom` |
| Log root | `/var/log/meeting-loom` |
| Environment prefix | `LOOM_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; transcripts and participant data stay out of manager inventory |
| Source root | `products/meeting-loom/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Meeting Loom imports owner-provided UTF-8 transcripts, preserves immutable
source provenance, and proposes summaries, decisions, questions, and action
items linked to exact speaker-labelled lines or timestamps. Local installation
keeps sensitive discussions on the machine and permits enforceable source,
retention, and network boundaries.

The first release supports one owner, `.txt` and canonical JSON transcripts,
manual participant labels and consent attestations, a loopback UI, and one
credential-free loopback model. It neither captures audio nor updates another
system.

### It must

- keep source statements separate from model summaries and owner-confirmed
  decisions or actions;
- cite every proposed decision and action item to a current transcript range
  and identify uncertain speakers; and
- expose consent, correction, retention, export, suspension, and deletion
  controls before storing a meeting record.

### It must not

- record microphones, infer covert participants, identify voices, send mail,
  assign work, or update calendars and task systems;
- claim that a transcript is complete, lawful, accurate, or an authoritative
  minute merely because it was imported; or
- invent attendance, agreement, ownership, deadlines, quotations, or consent.

## Status and evidence

This document fixes a first product slice. No Loom implementation, installer,
catalogue admission, security evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Transcript, consent, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/meeting-loom/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Loom release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Attest authority, import, review, correct, confirm, export, suspend, and delete | Use Loom to bypass recording, employment, legal, or confidentiality duties |
| Participant | Receive an owner-controlled export or correction route outside Loom | Gain access merely because their name appears |
| Machine operator | Install, update, back up, recover, and uninstall | Treat root access as participant consent |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain transcripts, participants, summaries, actions, or secrets |
| `loom` service | Read fixed transcripts and write Loom-owned state | Record, message, schedule, inspect the host, or invoke lifecycle commands |
| Model endpoint | Propose structured output from selected transcript ranges | Confirm decisions, identify people, or assign authority |

### Authority ceiling

The service accepts authenticated loopback requests, reads supported regular
files below `/srv/meeting-loom/inbox`, writes protected Loom state and exports,
and calls one loopback model. It has no microphone, camera, audio, device,
shell, subprocess, `sudo`, email, calendar, task-system, browser, internet, or
host-wide filesystem access.

Each transcript is at most 32 MiB and must declare a format, meeting label,
time, owner authority attestation, and participant labels or explicit unknowns.
Links, devices, mounts, and path escape are rejected. No prompt or password can
create consent or organisational authority.

### Authority inherited, retained, and removed

- Independent lifecycle, authentication, policy, audit, diagnostics, backup,
  and release verification are retained.
- Root, shell, host inspection, package, service, network, account, and device
  controls are removed.
- Workspace mutation is replaced by read-only transcript import and Loom-owned
  outputs.
- Automatic recording, speaker identification, communication, scheduling, and
  task execution are removed.
- Model output cannot become a confirmed record without owner review.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Transcript import | Creates an attributable meeting source | Read fixed inbox and store digest | MVP |
| Cited summary | Makes long discussions reviewable | Selected lines and local model | MVP |
| Decision and question proposals | Separates possible outcomes from source | Structured untrusted model output | MVP |
| Action proposal review | Lets owner confirm or reject owner, due date, and wording | Loom state only | MVP |
| Corrected minute export | Produces a portable labelled record | Confirmed Loom state | MVP |
| Recording and integrations | Captures or distributes meetings | Device and external authority | Out of scope |

### Primary workflow

1. The owner authenticates, attests their authority to process the meeting, and
   imports a supported transcript.
2. Loom validates format, source digest, participant labels, and line or time
   ranges without changing the file.
3. The model proposes structured summaries, decisions, questions, and actions,
   each with source references and confidence.
4. Loom reopens the source, verifies every reference and quotation, and
   requires owner confirmation or correction.
5. It exports a labelled minute and writes a content-minimised audit event.

### Failure behaviour

Loom rejects missing authority attestations, invalid formats, ambiguous
speakers, stale sources, unverifiable quotations, impossible timestamps,
malformed model output, or audit failure. Unknown speakers remain unknown.
Model outage leaves import, deterministic search, confirmed-record review, and
export available but creates no new summary.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `loom` | Credentials, attestations, corrections | Authenticated views and controls | No recording or external authority |
| Transcript validator | `loom` | Supported imported files | Canonical lines, labels, digests | Read-only fixed root |
| Retrieval and citation verifier | `loom` | Query, source, proposed references | Verified or rejected references | Deterministic |
| Model bridge | `loom` | Selected transcript ranges and schema | Untrusted proposals | Exact loopback endpoint only |
| Record and export service | `loom` | Owner-confirmed proposals | Labelled JSON and Markdown | Loom-owned state only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Loom-owned resources only |

Root owns executable code, configuration, credentials, policy, units, and
markers. The service has strict filesystem protection, private devices, no
capabilities, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose transcripts and corrupt Loom-owned
  records, but cannot record or contact a participant.
- A compromised model sees selected transcript text and can mislead, but cannot
  forge a valid source range or owner confirmation.
- A stolen owner session permits review and export until expiry or revocation,
  but not root or external actions.
- A failed update retains the previous verified code and protected compatible
  backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `loom`, `loom-share` |
| Install root | `/opt/meeting-loom` |
| Configuration | `/etc/meeting-loom` |
| State | `/var/lib/meeting-loom` |
| Transcript inbox | `/srv/meeting-loom/inbox` |
| Logs | `/var/log/meeting-loom` |
| Units | `meeting-loom-*.service` |
| Commands | `loom-*` |
| Environment | `LOOM_*` |
| Loopback ports | `2525` |
| Cookie names | `meeting_loom_session` |
| Package names | `meeting-loom` |
| Ownership marker | `/var/lib/meeting-loom/installation.json` |
| Receipt | `/var/log/meeting-loom/management-receipt.json` |
| Firewall rules | None |

All resources are collision-checked and require the common marker and receipt
before an existing installation is recognised.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Loom-specific scrypt hash in protected state | Owner rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Loom-only key in `/etc/meeting-loom/secrets`, mode `0600` | Rotation revokes sessions |
| Participant credential | None | Participants have no first-release account | A future role requires separate review |
| Model or integration credential | None | Never accepted in the first release | Unsupported |

Consent attestations are records, not credentials. Raw secrets and transcript
content never enter operational logs, receipts, diagnostics, ordinary
environment values, or manager inventory. Sibling credentials are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Import transcript | Restricted | Owner attestation | `transcript.imported` | Fixed root, formats, size, digest |
| Generate proposals | Restricted | Authenticated owner | `record.proposed` | Selected source ranges and loopback model |
| Confirm/correct item | Restricted | Owner | `record.confirmed` | Existing proposal and source version |
| Export minute | Restricted | Owner confirmation | `minute.exported` | Loom-owned export root |
| Delete meeting state | Restricted | Owner confirmation | `meeting.deleted` | Loom-owned data only |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Recording, transcription capture, voice identification, messaging,
  scheduling, task assignment, document signing, and external publication.
- Writes to imported transcripts or reads outside the fixed inbox.
- Model authority over participants, consent, decisions, commitments,
  deadlines, or confirmed records.

Audit records contain event IDs, actor/session IDs, source digest, counts,
decision state, result, and correlation ID. They exclude names, transcript
text, summaries, action text, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Source transcripts | Meeting evidence | Owner and applicable participants | Read-only inbox; excluded from backup | Owner-controlled | Managed outside Loom |
| Consent and authority attestations | Record processing basis | Owner | Protected append-only state | Same as meeting record | Included in labelled export |
| Proposals and corrections | Produce reviewable minutes | Owner | Mode `0600` SQLite with provenance | 30 days | JSON/Markdown or deletion |
| Confirmed minute | Portable meeting record | Owner | Protected export root | 90 days | Export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

The owner is responsible for applicable recording, employment, confidentiality,
and data-protection duties. Loom performs no telemetry or training and sends
only selected text to the local model. Backups exclude source and active
sessions. Complete uninstall never deletes inbox files.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2525` | Authenticated UI traffic | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Selected transcript ranges and schema | Allowed | Exact URL and bounded payload |
| Outbound | Email, calendars, task systems, internet, or LAN | None | Blocked | Network policy and absent clients |

The first release requires a credential-free loopback model. Dry-run performs
no network access. Cloud models, remote access, live transcription, and
webhooks are unsupported.

## Ubuntu Zombie management contract

The source entry point is `products/meeting-loom/scripts/manage.sh`; the
installed command is `/usr/local/sbin/loom-manage`. It implements
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `owner_user`, `owner_password_file`, `model_base_url`,
`model`, `meeting_retention_days`, `audit_retention_days`,
`backup_destination`, and `retain_state`. Unknown keys fail closed.

Zombie inventory may retain identifiers, version, marker and receipt digests,
coarse health, result, and correlation ID. It must not retain participant or
meeting labels, transcript metadata or content, attestations, summaries,
actions, credentials, or model payloads. The `loom` service cannot invoke
management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject namespace and ownership collisions before mutation.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor, and
  pinned source lesson set.
- Validate owner, storage, inbox boundary, loopback model, backup, and rollback
  readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select existing local user | `LOOM_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `LOOM_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `LOOM_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `LOOM_MODEL` | Non-empty; required unattended |
| Meeting retention | Review default `30` | `LOOM_MEETING_RETENTION_DAYS` | Integer `1..365` |
| Audit retention | Review default `90` | `LOOM_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`LOOM_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and stable digest.
2. Revalidate release, plan, ownership, and collisions under the lock.
3. Create identities and protected directories.
4. Write credentials, schemas, retention, and configuration atomically.
5. Install root-owned code and confined services.
6. Create the read-only inbox, state, logs, marker, and receipt.
7. Start after citation, consent-record, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, attestations, corrections, confirmed minutes,
retention, and instance ID. It never changes source transcripts or silently
regenerates confirmed records and refuses unmarked resources.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, citation fixtures, marker, receipt |
| `verify` | Check ownership, confinement, schemas, inbox identity, and model | No | Human and JSON results |
| `doctor` | Explain source, model, consent, retention, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe resources and derived indexes | Yes | Reverification without transcript changes |
| `backup` | Archive Loom state, excluding transcripts and sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code and compatible state | Yes | Prior health checks |
| `suspend` | Stop processing and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate privacy and integrity before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report; transcripts unchanged |

## Update and migration design

Updates preserve credentials, source provenance, attestations, corrections,
confirmed records, retention, and instance ID; verify a backup; migrate staged
state; switch atomically; and rerun citation and label fixtures. Failure
restores the previous verified version. Tests prove transcripts and sibling
resources remain unchanged.

## Co-installation

Loom supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, transcript immutability, independent lifecycle operations, stable
non-target hashes and service times, and exact Zombie target selection. A
dedicated machine is recommended when meetings must be hidden from root.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/meeting-loom/audit.jsonl` | Policy and lifecycle events | No names, transcript or action text, or secrets |
| Service journal | `meeting-loom-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `loom-health` | Service, model, schemas, retention | Coarse public result |
| Diagnostics | `loom-diagnostics` | Versions, permissions, units, checks | Excludes meeting data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `loom-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, session revocation, consent records, and redaction.
- [ ] Transcript schemas, speaker uncertainty, citations, corrections,
      confirmations, retention, and exports.
- [ ] Prompt injection, invented participants, path escape, transcript writes,
      recording, integrations, sibling access, and egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Put instructions in transcript text that demand messaging, assignment,
  disclosure, or policy changes; they must remain inert.
- Make the model invent a speaker, quotation, decision, deadline, action owner,
  or consent; validation and labels must reject it.
- Race and replace transcripts during generation; mixed snapshots must fail.
- Compromise `loom` and prove microphone, email, calendar, source-write,
  sibling, and management access remain unavailable.
- Attack migrations and removal with unowned state; mutation must remain
  target-scoped and recoverable.

### Co-installation matrix

- [ ] Loom alone and with each current family product.
- [ ] Every supported three-product combination containing Loom.
- [ ] All current family products together.
- [ ] Operate and remove Loom while transcripts and siblings remain unchanged.
- [ ] Manage Loom through Ubuntu Zombie without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Transcript prompt injection | Unauthorised disclosure or invented record | Delimited data, absent tools, verified references | Reject proposal | Adversarial corpus |
| Fabricated agreement | False organisational commitment | Source citations, uncertainty labels, owner confirmation | Correct or delete record | Malicious-model fixtures |
| Unlawful processing | Participant privacy or legal harm | Owner attestation, minimisation, retention controls, warnings | Suspend and delete authorised state | Consent-flow tests |
| Service compromise | Transcript disclosure or record corruption | Least privilege, read-only inbox, root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |
| Malicious release | Root-level compromise | Verified signed artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes inaccurate source transcripts, disputed consent, and
human over-reliance on summaries. Loom does not resolve those disputes.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Meeting records need safe convergence | Reinstall tests |
| Policy and audit gate | Keep with participant-data minimisation | Confirmation and deletion need accountability | Redaction tests |
| Root-capable account | Remove | Summarisation needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Loom requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Owner needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with source provenance | Confirmed records must survive migrations | Migration tests |

**Measurable improvement:** every quotation, proposed decision, and proposed
action must resolve to a current source range, while every confirmed record
must preserve both the original proposal and authenticated owner correction.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Meeting Loom is a private local assistant for creating cited, owner-reviewed
> meeting summaries and action proposals from deliberately imported
> transcripts.

### Prohibited claims

- That Loom records consent, proves attendance, or creates legally authoritative
  minutes merely through import.
- That summaries establish what a person intended or agreed.
- That local operation hides meetings from same-host root.
- That this definition represents implemented or released software.

### Out of scope

- Audio/video capture, transcription, voice identification, surveillance,
  email, calendar, task-system, signature, and publication integrations.
- Cloud models, remote users, multi-tenant organisations, employment
  monitoring, and legal discovery.
- Automatic action assignment or deadline enforcement.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Loom | Repository maintainers | First implementation change |
| Canonical transcript profile | Speaker and timestamp ambiguity affects evidence | Product maintainers | First runtime change |
| Consent and privacy review | Meetings contain third-party sensitive data | Privacy reviewers | Implementation approval |
| Export labelling | A generated minute must not masquerade as raw source | Security reviewers | Release candidate |
| Disposable-VM boundary | Permissions and egress controls need host proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, transcript flow, and threat model.
- [ ] Consent, privacy, retention, export, correction, and deletion model.
- [ ] Transcript, citation, proposal, confirmation, and minute schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Adversarial transcript fixtures and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, citation and
label fixtures, standalone VM lifecycle, negative security and privacy suites,
co-installation evidence, changelog, and version. Family admission also
requires manager and contract evidence. Unproven consent, accuracy, privacy, or
security claims remain visibly planned.
