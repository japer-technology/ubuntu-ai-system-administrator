# Access Bridge

> A private local cognitive-accessibility assistant that rewrites user-supplied
> text into reviewable alternatives without diagnosing the user or sending a
> message.

Access Bridge complements the family with a deliberately small
communication-access boundary. It is not a medical device, diagnostic system,
caregiver account, translator, screen reader, messaging client, or Imaginary
Friend persona.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `access-bridge` |
| Human need | Understand difficult text and prepare clearer text privately without granting an AI access to accounts or the wider machine |
| Intended users | One consenting adult user |
| Operator | The user or machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read and write only Bridge-owned preferences, optional history, exports, and audit state |
| Default Linux identity | Non-login `bridge` account and group |
| Default loopback port | `2121` |
| Install root | `/opt/access-bridge` |
| Configuration root | `/etc/access-bridge` |
| State root | `/var/lib/access-bridge` |
| Log root | `/var/log/access-bridge` |
| Environment prefix | `BRIDGE_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; source text, accessibility preferences, and credentials stay out of manager inventory |
| Source root | `products/access-bridge/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Access Bridge accepts text pasted by its user and produces side-by-side
alternatives such as plain-language explanations, shorter steps, structured
questions, or an editable outgoing draft. The user chooses the transformation
and remains the only authority for meaning and use. A local product keeps
sensitive communication private and needs no file, device, or account access.

The first release supports one adult user, text only, no history by default, a
loopback UI, fixed transformation profiles, and one credential-free loopback
model. It neither listens, speaks, reads the desktop, nor sends output.

### It must

- preserve the original text beside every generated alternative and label all
  additions, omissions, and uncertainty;
- let the user control reading level, layout, optional retention, export,
  correction, suspension, and deletion; and
- keep usable copy, comparison, and deletion controls available without
  requiring an external account.

### It must not

- diagnose disability, capacity, literacy, cognition, emotion, or health;
- make a decision for the user, impersonate them, send a message, sign a form,
  accept terms, or claim informed consent; or
- simplify legal, medical, financial, safety, or emergency text without a
  prominent warning that meaning may change and qualified help may be needed.

## Status and evidence

This document fixes a first product slice. No Bridge source, installer,
catalogue admission, accessibility study, security evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Transformation, privacy, and lifecycle sections |
| Threat model reviewed | Open | Repository security and accessibility reviewers |
| Installer lifecycle complete | Open | Future `products/access-bridge/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Bridge release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| User | Choose a transformation, compare, edit, copy, export, set retention, suspend, and delete | Treat Bridge output as another person's agreement or professional advice |
| Machine operator | Install, update, back up, recover, and uninstall | Access user text through ordinary lifecycle interfaces |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain text, preferences, transformations, exports, or secrets |
| `bridge` service | Transform user-submitted text and manage Bridge state | Read the desktop, use devices, send output, inspect the host, or invoke lifecycle commands |
| Model endpoint | Propose a text alternative under a selected profile | Diagnose, decide, send, sign, or alter user preferences |
| Support person | Help the user outside the product when invited | Gain a product role or access merely through that relationship |

### Authority ceiling

The service accepts authenticated loopback requests, reads and writes only
Bridge-owned state and exports, and calls one loopback model. It has no `sudo`,
shell, subprocess, general filesystem, clipboard API, accessibility bus,
microphone, camera, speech, browser, internet, messaging, form-submission,
device, or sibling access.

The browser's ordinary user-initiated paste and copy actions are not service
authority. A password, prompt, support relationship, or claimed need cannot add
a tool or expand the installed boundary.

### Authority inherited, retained, and removed

- Independent installation, authentication, policy, audit, lifecycle,
  diagnostics, backup, and release verification are retained.
- Root, shell, host reads, workspace access, package, service, network, account,
  and device controls are removed.
- Conversation memory is replaced by per-transformation state with history off
  by default.
- Child, guardian, clinician, employer, school, and family-management roles are
  removed.
- Model authority over diagnosis, consent, sending, and user preference is
  removed.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Plain-language alternative | Makes difficult text easier to review | Current pasted text and local model | MVP |
| Step and question extraction | Turns dense text into a review checklist | Current text and fixed schema | MVP |
| Outgoing draft alternative | Helps the user express intended meaning | User-entered intent and local model | MVP |
| Side-by-side change review | Keeps source and uncertainty visible | In-memory source and generated output | MVP |
| Optional local history/export | Supports later review under user control | Bridge state and export root | MVP |
| Speech, desktop, and messaging integration | Broader accessibility interface | Device and account authority | Later, separately reviewed |

### Primary workflow

1. The user authenticates, selects a fixed transformation profile, and pastes
   text knowingly into the UI.
2. Bridge keeps the source immutable for that request, computes its digest, and
   sends the bounded text and profile to the local model.
3. The model returns a schema-constrained alternative with declared
   uncertainty and change categories.
4. Bridge displays source and alternative side by side, highlights differences
   deterministically, and shows high-stakes warnings when applicable.
5. The user edits or copies text and chooses whether to retain or export it;
   Bridge never sends or submits it.

### Failure behaviour

Bridge rejects oversized or invalid text, unsupported profiles, malformed
model output, hidden active content, stale requests, retention failure, and
audit failure. It never replaces the source view or claims unchanged meaning.
If the model is unavailable, the UI can still display, segment, compare,
copy, delete, and export user text without generating a new alternative.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `bridge` | Credentials, pasted text, preferences | Authenticated review and controls | No desktop, device, or messaging authority |
| Profile and request validator | `bridge` | Selected fixed profile and bounded text | Canonical request and source digest | Deterministic |
| Model bridge | `bridge` | Canonical request and schema | Untrusted alternative and uncertainty | Exact loopback endpoint only |
| Difference and warning engine | `bridge` | Source and proposed alternative | Side-by-side changes and warnings | Deterministic; cannot assert equivalence |
| History/export service | `bridge` | User-approved content | Optional JSON/Markdown | Bridge-owned state only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Bridge-owned resources only |

Root owns code, profiles, configuration, policy, credentials, units, and
markers. The service has no capabilities, strict filesystem protection,
private devices, explicit paths, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose text submitted to Bridge and corrupt its
  state, but cannot read the desktop or send a message.
- A compromised model sees the current bounded text and can manipulate the
  alternative, but cannot hide the source or bypass deterministic comparison.
- A stolen user session permits transformations and optional export until
  revocation, but no account or lifecycle action.
- A failed update retains the previous verified version and protected,
  compatible preferences and optional history.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `bridge` |
| Install root | `/opt/access-bridge` |
| Configuration | `/etc/access-bridge` |
| State | `/var/lib/access-bridge` |
| Logs | `/var/log/access-bridge` |
| Units | `access-bridge-*.service` |
| Commands | `bridge-*` |
| Environment | `BRIDGE_*` |
| Loopback ports | `2121` |
| Cookie names | `access_bridge_session` |
| Package names | `access-bridge` |
| Ownership marker | `/var/lib/access-bridge/installation.json` |
| Receipt | `/var/log/access-bridge/management-receipt.json` |
| Firewall rules | None |

Every resource is collision-checked and existing state is recognised only with
the common ownership marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| User password | Loopback login | Bridge-specific scrypt hash in protected state | User rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Bridge-only key in `/etc/access-bridge/secrets`, mode `0600` | Rotation revokes sessions |
| Model, support, or messaging credential | None | Never accepted in the first release | Unsupported |

Raw credentials and transformation text never enter arguments, ordinary
environment values, operational logs, receipts, diagnostics, or manager
inventory. Sibling credentials and reset flows are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Transform text | Restricted | Authenticated user request | `text.transformed` | Fixed profile, text and output limits |
| Compare changes | Allowed | None after valid response | `text.compared` | Current source and alternative |
| Edit/copy result | Restricted | User action | `result.reviewed` | Current browser session |
| Retain/export/delete | Restricted | User confirmation | `history.changed` | Bridge-owned state only |
| Change preferences | Restricted | User | `preference.changed` | Fixed supported settings |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Clipboard scraping, desktop reading, files, screen capture, speech, devices,
  messaging, form submission, signing, browser automation, and external APIs.
- Diagnosis, capacity assessment, guardianship, consent, identity, or
  professional-advice decisions.
- Model changes to source display, policy, retention, user preferences, or
  high-stakes warnings.

Audits contain event IDs, actor/session pseudonyms, profile IDs, byte counts,
retention decision, result, and correlation ID. They exclude source and output
text, preferences that reveal disability, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Submitted source text | One transformation | User | Memory only by default | End of request/session | Optional explicit export |
| Generated alternative | User review | User | Memory only by default | End of request/session | Optional explicit export |
| Accessibility preferences | Configure presentation | User | Mode `0600` SQLite | Until reset or uninstall | JSON export or deletion |
| Opt-in history | User-requested continuity | User | Protected SQLite | User-selected `1..90` days | JSON/Markdown or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Bridge does not infer or store a diagnosis, disability label, capacity score,
or demographic profile. It performs no telemetry or training. Backups exclude
request text unless the user explicitly enabled history and include no active
sessions.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2121` | Authenticated UI traffic | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Current bounded text and fixed profile | Allowed | Exact URL and payload limits |
| Outbound | Messaging, forms, speech services, internet, or LAN | None | Blocked | Network policy and absent clients |

The first release requires a credential-free loopback model. Dry-run performs
no network access. The UI can offer browser-native visual settings but cannot
request browser extension or operating-system accessibility privileges.

## Ubuntu Zombie management contract

The source entry point is `products/access-bridge/scripts/manage.sh`; the
installed command is `/usr/local/sbin/bridge-manage`. It follows
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `user_account`, `user_password_file`, `model_base_url`,
`model`, `history_retention_days`, `audit_retention_days`,
`backup_destination`, and `retain_state`. Unknown keys fail closed.

Zombie inventory may retain identifiers, version, marker and receipt digests,
coarse health, result, and correlation ID. It must not retain user identity,
accessibility preferences, profile use, source or output text, history,
credentials, or model payloads. The `bridge` service cannot invoke management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject namespace and ownership collisions before mutation.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor, fixed
  transformation profiles, and pinned source lesson set.
- Validate user, storage, loopback model, backup, rollback, keyboard-only
  operation, contrast, and zoom behaviour.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| User | Select existing adult local user | `BRIDGE_USER_ACCOUNT` | Existing non-root account and adult-use attestation |
| User password | Generate or read protected file | `BRIDGE_USER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `BRIDGE_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `BRIDGE_MODEL` | Non-empty; required unattended |
| History retention | Default off | `BRIDGE_HISTORY_RETENTION_DAYS` | Integer `0..90` |
| Audit retention | Review default `90` | `BRIDGE_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`BRIDGE_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and stable digest.
2. Revalidate release, profiles, plan, ownership, and collisions under lock.
3. Create the identity and protected directories.
4. Write credentials, preferences, retention, and configuration atomically.
5. Install root-owned code, profiles, and confined services.
6. Create optional history state, logs, marker, and receipt.
7. Start after accessibility, privacy, comparison, and negative checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, user preferences, explicit history choice,
retention, and instance ID. It never enables history silently and refuses every
unmarked collision.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy accessible UI, model, fixtures, marker, receipt |
| `verify` | Check ownership, confinement, profiles, comparison, and model | No | Human and JSON results |
| `doctor` | Explain model, accessibility, privacy, retention, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe resources and profiles | Yes | Reverification without history enablement |
| `backup` | Archive preferences and opt-in history, excluding sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code and compatible state | Yes | Prior health checks |
| `suspend` | Stop transformations and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate accessibility and privacy before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report |

## Update and migration design

Updates preserve credentials, user preferences, explicit history setting,
retention, and instance ID; verify a backup; migrate staged state; rerun
accessibility and comparison fixtures; and switch atomically. Failure restores
the previous verified version. An update cannot enable new data collection or
device authority without a new definition review.

## Co-installation

Bridge supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, independent lifecycle operations, stable non-target hashes and service
times, and exact Zombie target selection. Bridge receives no shared child,
guardian, Friend, or ERIC role.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/access-bridge/audit.jsonl` | Policy and lifecycle events | No text, disability inference, or secrets |
| Service journal | `access-bridge-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `bridge-health` | Service, model, profile and UI checks | Coarse public result |
| Diagnostics | `bridge-diagnostics` | Versions, permissions, units, checks | Excludes user data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `bridge-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Keyboard-only use, focus order, zoom, contrast, labels, authentication,
      session revocation, history-off default, and redaction.
- [ ] Transformation profiles, source preservation, side-by-side differences,
      uncertainty, high-stakes warnings, export, and deletion.
- [ ] Prompt injection, diagnosis, hidden source, silent retention, desktop or
      clipboard reads, messaging, sibling access, and egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Ask the model to hide, reverse, or materially alter meaning without a change
  marker; deterministic comparison must expose it.
- Provide coercive, legal, medical, financial, safety, and emergency text; the
  product must not claim equivalence, consent, or professional advice.
- Make the model diagnose the user or address a support person as decision
  maker; the response must be rejected.
- Compromise `bridge` and prove desktop, device, network, sibling, and
  management access remain unavailable.
- Attack update to enable history or a new integration silently; migration must
  fail closed.

### Co-installation matrix

- [ ] Bridge alone and with each current family product.
- [ ] Bridge with Flame, Friend, and ERIC, proving role and data separation.
- [ ] Every supported three-product combination containing Bridge.
- [ ] All current family products together.
- [ ] Operate, manage, and remove Bridge without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Meaning-changing rewrite | User acts on materially altered text | Immutable source view, deterministic diff, uncertainty and high-stakes warnings | Reject, edit, or delete result | Semantic-change fixtures |
| Coercive or diagnostic output | Loss of autonomy or stigma | Fixed role boundary, policy filters, no support-person authority | Suspend and remove output | Malicious-model fixtures |
| Sensitive-text disclosure | Privacy harm | Local endpoint, memory-only default, content-free logs | Suspend, rotate, delete history | Egress and redaction suite |
| Inaccessible interface | Intended user cannot control or correct product | Keyboard, focus, zoom, contrast and assistive review gates | Rollback or suspend | Accessibility test matrix |
| Service compromise | Submitted text disclosure or state corruption | Least privilege and root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |

Residual risk includes misleading simplification, model bias, inaccessible edge
cases, and the independently operated local model observing submitted text.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Preferences need safe convergence | Reinstall tests |
| Policy and audit gate | Keep with text minimisation | Retention and export need accountability | Redaction tests |
| Root-capable account | Remove | Text transformation needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Bridge requires independent credentials and accessible UI | Cross-login and UI tests |
| Lifecycle/kill switch | Keep | User needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with history-off invariant | Updates must not expand collection silently | Migration tests |

**Measurable improvement:** every generated alternative must retain an
immutable source view, a deterministic token-level change display, provenance,
and a user-visible uncertainty control; history must remain off in 100% of
fresh and reinstalled default cases.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Access Bridge is a private local cognitive-accessibility assistant that
> presents reviewable text alternatives beside an unchanged user-supplied
> source.

### Prohibited claims

- That Bridge diagnoses, measures capacity, guarantees accessibility, preserves
  meaning, establishes consent, or provides professional advice.
- That a generated outgoing draft represents or binds the user.
- That local operation hides text from same-host root or the local model.
- That this definition represents implemented or released software.

### Out of scope

- Children, guardianship, diagnosis, clinical treatment, capacity assessment,
  certified translation, and emergency communication.
- Speech, microphone, camera, screen reading, clipboard monitoring, messaging,
  forms, signatures, browser automation, and device control.
- Cloud models, remote users, support-person accounts, and institutional
  monitoring.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Bridge | Repository maintainers | First implementation change |
| Participatory accessibility review | Intended users must validate control and usability | Accessibility reviewers | Implementation approval |
| Transformation profile fixtures | Meaning changes and warnings need measurable tests | Product maintainers | First runtime change |
| High-stakes text classifier | False negatives can cause serious harm | Safety reviewers | Release candidate |
| Disposable-VM and UI evidence | Confinement and accessibility need recorded proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Accessible architecture, data flow, and threat model.
- [ ] User autonomy, privacy, retention, export, and deletion model.
- [ ] Transformation profile, difference, warning, and export schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Participatory accessibility, adversarial model, and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification,
participatory accessibility review, transformation and history-off fixtures,
standalone VM lifecycle, negative security and autonomy suites,
co-installation evidence, changelog, and version. Family admission also
requires manager and contract evidence. Unproven accessibility, meaning,
privacy, or security claims remain visibly planned.
