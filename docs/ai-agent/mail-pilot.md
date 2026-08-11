# Mail Pilot

> A private local mail-review assistant that triages deliberately imported
> messages and prepares unsent drafts without connecting to an account or
> changing a mailbox.

Mail Pilot complements the family with a narrow communication-review workflow.
It is not an email client, spam gateway, account agent, autonomous sender,
Archive Lantern collection, or Imaginary Friend messaging feature.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `mail-pilot` |
| Human need | Review a private set of messages and prepare replies without giving an AI access to an email account |
| Intended users | One adult owner authorised to process the imported messages |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read supported `.eml` files in one fixed inbox and write only Pilot-owned labels, notes, unsent drafts, exports, and logs |
| Default Linux identity | Non-login `pilot` account and group |
| Default loopback port | `2626` |
| Install root | `/opt/mail-pilot` |
| Configuration root | `/etc/mail-pilot` |
| State root | `/var/lib/mail-pilot` |
| Log root | `/var/log/mail-pilot` |
| Environment prefix | `PILOT_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; message content, correspondents, drafts, and credentials stay out of manager inventory |
| Source root | `products/mail-pilot/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Mail Pilot parses owner-exported RFC 5322 messages, displays safe plain text,
suggests triage labels, and prepares clearly marked unsent reply drafts with
source references. Local installation is appropriate because correspondence
is sensitive and account, network, source-write, and active-content boundaries
can be enforced below the prompt.

The first release supports one owner, `.eml` files up to 16 MiB, plain-text
bodies, header review, a loopback UI, and one credential-free loopback model.
HTML is rendered as inert text, attachments are listed but never opened, and
there is no IMAP, SMTP, webmail, contacts, or calendar connection.

### It must

- preserve source digest, message identifier, parsed-header provenance, and
  owner corrections for every label and draft;
- keep generated text visibly separate from received content and require owner
  review before any draft export; and
- provide retention, redaction, export, suspension, and deletion controls for
  all Pilot-owned state.

### It must not

- send, receive, delete, move, mark, forward, or otherwise mutate email or an
  account;
- fetch links, images, receipts, attachments, remote content, keys, or contact
  data; or
- claim sender identity, message authenticity, legal effect, urgency, safety,
  or absence of phishing.

## Status and evidence

This document fixes a first product slice. No Pilot source, installer,
catalogue admission, security evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Message, draft, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/mail-pilot/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Pilot release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Import authorised mail, review labels, edit/export drafts, expire, suspend, and delete | Treat a generated draft as sent or an authenticity determination |
| Correspondent | Be represented only as stated in imported headers | Gain access or consent status merely by appearing in a message |
| Machine operator | Install, update, back up, recover, and uninstall | Treat host access as authority to use another person's mailbox |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain messages, addresses, subjects, labels, drafts, or secrets |
| `pilot` service | Read fixed messages and write Pilot state | Connect to mail systems, open attachments, inspect the host, or invoke lifecycle commands |
| Model endpoint | Suggest labels and reply text from selected inert content | Send, authenticate, fetch, set policy, or establish sender identity |

### Authority ceiling

The service accepts authenticated loopback requests, reads supported regular
`.eml` files below `/srv/mail-pilot/inbox`, writes protected Pilot state and
draft exports, and calls one loopback model. It has no `sudo`, shell,
subprocess, browser, DNS, IMAP, SMTP, webmail, contacts, calendar, keyring,
attachment opener, external network, or host-wide filesystem access.

Parsing applies nesting, header, line, character-set, and body limits. Links,
remote images, HTML forms and scripts, delivery-status actions, MIME
executables, devices, symlinks, and path escapes remain inert or are rejected.
No message instruction or owner password can broaden authority.

### Authority inherited, retained, and removed

- Independent installation, authentication, policy, audit, lifecycle,
  diagnostics, backup, and release verification are retained.
- Root, shell, host inspection, package, service, account, device, and general
  network controls are removed.
- Workspace writes are replaced by a read-only import inbox and Pilot-owned
  drafts.
- Account credentials, mail protocols, link fetching, attachment handling,
  autonomous sending, and family management are removed.
- Model output cannot alter a source message or become a sent-message claim.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Safe message import | Makes exported mail reviewable | Read fixed inbox; parse bounded MIME | MVP |
| Suggested triage | Helps prioritise owner review | Selected inert fields and local model | MVP |
| Unsent draft | Provides an editable reply starting point | Current message and Pilot state | MVP |
| Source-linked note | Preserves why a draft or label exists | Message digest and owner note | MVP |
| Portable draft export | Moves reviewed text to an owner-controlled workflow | Pilot export root | MVP |
| Mail-account integration | Sends or mutates mail | Account credentials and network | Out of scope |

### Primary workflow

1. The owner signs in with Pilot-only credentials and deliberately places an
   exported message in the fixed inbox.
2. Pilot parses bounded headers and inert text, records the file and canonical
   message digest, and lists but does not open attachments.
3. The model proposes labels, a summary, and optional reply text using selected
   content.
4. Pilot binds every proposal to the current message digest, removes active
   content, labels it generated, and requires owner review and editing.
5. The owner exports an unsent `.eml` or Markdown draft; Pilot records a
   content-minimised event and makes no delivery claim.

### Failure behaviour

Pilot rejects malformed MIME, excessive nesting, unsupported encodings,
changed files, ambiguous source identity, active-content escape, malformed
model output, and audit failure. It never fetches missing content or guesses an
attachment. During model outage, deterministic parsing, search, owner labels,
draft editing, export, and deletion remain available.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `pilot` | Credentials, review controls | Authenticated safe views and drafts | No account or sending authority |
| MIME parser and sanitiser | `pilot` | Supported `.eml` files | Canonical inert fields and digest | Read-only fixed inbox |
| Model bridge | `pilot` | Selected inert content and schema | Untrusted labels and draft text | Exact loopback endpoint only |
| Proposal verifier | `pilot` | Model output and current source | Labelled source-bound proposal | Rejects active or unsupported fields |
| Draft/export service | `pilot` | Owner-reviewed text | Unsent `.eml` and Markdown | Pilot-owned export root only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Pilot-owned resources only |

Root owns code, policy, configuration, credentials, units, and markers. The
service has no capabilities, strict filesystem protection, private devices,
explicit paths, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose imported correspondence and corrupt
  Pilot-owned state, but cannot connect to or mutate a mailbox.
- A compromised model sees selected message content and can produce phishing
  or harmful text, but cannot fetch, send, or authenticate.
- A stolen owner session permits message review and draft export until
  revocation, but not account or lifecycle action.
- A failed update retains the previous verified version and protected
  compatible state backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `pilot`, `pilot-share` |
| Install root | `/opt/mail-pilot` |
| Configuration | `/etc/mail-pilot` |
| State | `/var/lib/mail-pilot` |
| Message inbox | `/srv/mail-pilot/inbox` |
| Logs | `/var/log/mail-pilot` |
| Units | `mail-pilot-*.service` |
| Commands | `pilot-*` |
| Environment | `PILOT_*` |
| Loopback ports | `2626` |
| Cookie names | `mail_pilot_session` |
| Package names | `mail-pilot` |
| Ownership marker | `/var/lib/mail-pilot/installation.json` |
| Receipt | `/var/log/mail-pilot/management-receipt.json` |
| Firewall rules | None |

Every resource is collision-checked and recognised only through the common
ownership marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Pilot-specific scrypt hash in protected state | Owner rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Pilot-only key in `/etc/mail-pilot/secrets`, mode `0600` | Rotation revokes sessions |
| Mail account, signing, or model credential | None | Never accepted in the first release | Unsupported |

Messages may contain quoted secrets and are always treated as sensitive data.
Raw credentials and message bodies never enter arguments, ordinary environment
values, operational logs, receipts, diagnostics, or manager inventory. Sibling
credentials are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Import/parse message | Restricted | Authenticated owner | `message.imported` | Fixed root and bounded MIME profile |
| Generate triage/draft | Restricted | Owner request | `draft.generated` | Selected inert content and local model |
| Edit owner labels/draft | Restricted | Owner | `draft.changed` | Pilot state only |
| Export unsent draft | Restricted | Owner confirmation | `draft.exported` | Pilot export root and unsent marker |
| Delete derived state | Restricted | Owner confirmation | `state.deleted` | Pilot-owned records only |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- IMAP, POP, SMTP, webmail, contacts, calendar, account credentials, sending,
  receipt requests, forwarding, mailbox mutation, and remote fetch.
- Attachment opening, code execution, active HTML, external images, and links.
- Model authority over sender identity, authenticity, urgency, policy,
  retention, or delivery status.

Audit records include event IDs, actor/session IDs, opaque message IDs,
digests, decisions, counts, results, and correlation IDs. They exclude
addresses, subjects, bodies, attachments, labels, draft text, credentials, and
model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Source messages | Correspondence evidence | Owner and applicable correspondents | Read-only inbox; excluded from backup | Owner-controlled | Managed outside Pilot |
| Parsed metadata and labels | Triage and source binding | Owner | Mode `0600` SQLite | 30 days | JSON export or deletion |
| Summaries and drafts | Owner review and reply preparation | Owner | Protected SQLite/export root | 30 days | Markdown/`.eml` or deletion |
| Owner corrections | Preserve review history | Owner | Protected append-only records | 30 days | Included in export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

The owner is responsible for authority to process correspondence and disclose
it to the selected local model. Pilot performs no telemetry or training.
Backups exclude source messages and active sessions. Complete uninstall never
deletes inbox files.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2626` | Authenticated UI traffic | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Selected inert message content and schema | Allowed | Exact URL and payload limits |
| Outbound | Mail servers, links, images, internet, or LAN | None | Blocked | Network policy and absent clients |

The first release requires a credential-free loopback model and permits no
redirect. Dry-run performs no network access. Export writes a local file; it
never invokes a mail handler.

## Ubuntu Zombie management contract

The source entry point is `products/mail-pilot/scripts/manage.sh`; the
installed command is `/usr/local/sbin/pilot-manage`. It implements
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `owner_user`, `owner_password_file`, `model_base_url`,
`model`, `message_retention_days`, `audit_retention_days`,
`backup_destination`, and `retain_state`. Unknown keys fail closed.

Zombie inventory may retain identifiers, version, marker and receipt digests,
coarse health, result, and correlation ID. It must not retain message counts,
identifiers, correspondents, source metadata, labels, drafts, credentials, or
model payloads. The `pilot` service cannot invoke management.

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
| Owner | Select existing local user | `PILOT_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `PILOT_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `PILOT_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `PILOT_MODEL` | Non-empty; required unattended |
| Message retention | Review default `30` | `PILOT_MESSAGE_RETENTION_DAYS` | Integer `0..365` |
| Audit retention | Review default `90` | `PILOT_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`PILOT_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and stable digest.
2. Revalidate release, plan, ownership, collisions, and endpoint under lock.
3. Create identities and protected directories.
4. Write credentials, MIME policy, retention, and configuration atomically.
5. Install root-owned code and confined services.
6. Create the read-only inbox, state, logs, marker, and receipt.
7. Start after MIME, active-content, privacy, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, owner labels, reviewed drafts, retention, and
instance ID. Derived state remains bound to source digests; source messages are
never changed and unmarked resources are refused.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, MIME fixtures, marker, receipt |
| `verify` | Check ownership, confinement, schemas, inbox identity, and model | No | Human and JSON results |
| `doctor` | Explain message, model, parser, privacy, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe resources and rebuild derived indexes | Yes | Reverification without message changes |
| `backup` | Archive Pilot state, excluding messages and sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code and compatible state | Yes | Prior health checks |
| `suspend` | Stop processing and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate privacy and integrity before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report; messages unchanged |

## Update and migration design

Updates preserve credentials, source provenance, owner labels, reviewed
drafts, retention, and instance ID; verify a backup; migrate staged state;
rerun MIME and sanitisation fixtures; and switch atomically. Failure restores
the previous version. Source messages and sibling resources remain unchanged.

## Co-installation

Pilot supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, message immutability, independent lifecycle operations, stable
non-target hashes and service times, and exact Zombie target selection.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/mail-pilot/audit.jsonl` | Policy and lifecycle events | No addresses, message or draft text, or secrets |
| Service journal | `mail-pilot-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `pilot-health` | Service, model, MIME and schema integrity | Coarse public result |
| Diagnostics | `pilot-diagnostics` | Versions, permissions, units, checks | Excludes correspondence |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `pilot-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, session revocation, retention, export labels, and
      redaction.
- [ ] MIME limits, encodings, inert HTML, attachment listing, digest binding,
      triage, draft editing, and export.
- [ ] MIME bombs, prompt injection, active content, link fetch, account access,
      send attempts, sibling access, and egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Put instructions, tracking pixels, forms, scripts, phishing, and
  tool-request text in every MIME field; all must remain inert.
- Make the model invent a sender, authenticity result, attachment, commitment,
  or delivery claim; policy and labels must reject it.
- Race and replace messages during parsing and generation; mixed sources must
  fail.
- Compromise `pilot` and prove mail, internet, attachment, source-write,
  sibling, and management access remain unavailable.
- Attack migrations and uninstall with unowned resources; mutation must remain
  scoped and recoverable.

### Co-installation matrix

- [ ] Pilot alone and with each current family product.
- [ ] Every supported three-product combination containing Pilot.
- [ ] All current family products together.
- [ ] Operate and remove Pilot while messages and siblings remain unchanged.
- [ ] Manage Pilot through Ubuntu Zombie without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| MIME or HTML attack | Parser exploit, resource exhaustion, or active content | Strict profile, limits, inert rendering, no attachment handler | Reject source and suspend if needed | Adversarial mail corpus |
| Message prompt injection | Disclosure, sending claim, or unsafe draft | Delimited data, absent tools, source and generated labels | Discard proposal | Injection fixtures |
| Correspondence disclosure | Severe privacy harm | Local endpoint, protected paths, content-free logs | Suspend, rotate, delete state | Egress and redaction suite |
| Service compromise | Message disclosure or state corruption | Least privilege, read-only inbox, root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |
| Malicious release | Root-level compromise | Verified signed artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes phishing, spoofed source mail, harmful draft text, and
human export or sending through another application.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Reviewed drafts need safe convergence | Reinstall tests |
| Policy and audit gate | Keep with correspondence minimisation | Export and deletion need accountability | Redaction tests |
| Root-capable account | Remove | Mail review needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Pilot requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Owner needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with source immutability | Imported mail is not product state | Hash and rollback tests |

**Measurable improvement:** automated network and syscall tests must show zero
mail-protocol or external-network attempts while every exported draft carries
an explicit unsent/generated marker and current source digest.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Mail Pilot is a private local assistant for triaging deliberately imported
> `.eml` files and exporting clearly labelled, unsent reply drafts.

### Prohibited claims

- That Pilot sends mail, manages an account, authenticates a sender, detects
  all phishing, or proves legal effect.
- That a generated draft represents the owner until they independently review
  and send it.
- That local operation hides messages from same-host root or the local model.
- That this definition represents implemented or released software.

### Out of scope

- IMAP, POP, SMTP, webmail, contacts, calendars, sending, mailbox mutation,
  remote images, links, attachment opening, and cryptographic signing.
- Cloud models, remote users, organisational mailboxes, spam filtering, and
  compliance archiving.
- Legal advice, emergency response, and autonomous communication.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Pilot | Repository maintainers | First implementation change |
| Safe MIME profile | Parser ambiguity and active content are security-critical | Product maintainers | First runtime change |
| Privacy and phishing review | Correspondence is sensitive and adversarial | Security reviewers | Implementation approval |
| Unsent export marker | Another client must not mistake output for received or sent mail | Product reviewers | Release candidate |
| Disposable-VM boundary | Read-only inbox and egress controls need host proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, message flow, and threat model.
- [ ] Correspondence privacy, retention, export, and deletion model.
- [ ] MIME profile, source provenance, proposal, and unsent-draft schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Adversarial mail fixtures and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, adversarial
MIME and no-egress fixtures, standalone VM lifecycle, negative security and
privacy suites, co-installation evidence, changelog, and version. Family
admission also requires manager and contract evidence. Unproven authenticity,
privacy, or security claims remain visibly planned.
