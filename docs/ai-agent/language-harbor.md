# Language Harbor

> A private local language-practice partner for adults that provides
> attributable exercises and corrections without grading, certification, or
> access to the wider machine.

Language Harbor complements the family with self-directed adult learning. It
is not Curriculum Flame, a child-safety product, a school system, a certified
translator, or an Imaginary Friend persona.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `language-harbor` |
| Human need | Practise another language privately and receive reviewable feedback without sending conversations to a remote service |
| Intended users | One consenting adult learner |
| Operator | The learner or machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read root-owned Harbor lesson packages and write only Harbor-owned learner progress, conversation, export, and audit state |
| Default Linux identity | Non-login `harbor` account and group |
| Default loopback port | `2424` |
| Install root | `/opt/language-harbor` |
| Configuration root | `/etc/language-harbor` |
| State root | `/var/lib/language-harbor` |
| Log root | `/var/log/language-harbor` |
| Environment prefix | `HARBOR_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; learner content and credentials stay out of manager inventory |
| Source root | `products/language-harbor/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Language Harbor provides text conversation, exercises, vocabulary review, and
corrections for one adult learner using a signed lesson package and a local
model. Deterministic code owns lesson selection, progress, and answer keys;
model responses remain suggestions. Local installation is appropriate because
practice can be personal and repeated progress benefits from durable private
state.

The first release supports one source language, one target language selected
at install, text only, bundled synthetic lesson fixtures, a loopback UI, and
one credential-free loopback model. It has no browser, microphone, school,
exam, or external messaging integration.

### It must

- identify whether feedback comes from a fixed answer key, learner correction,
  or unverified model suggestion;
- preserve learner control over history, progress reset, export, retention,
  suspension, and deletion; and
- fail closed when lesson integrity, language configuration, model output, or
  policy validation is unavailable.

### It must not

- claim native-speaker accuracy, fluency, accreditation, exam readiness, or
  certified translation;
- serve children, infer age, enforce curriculum, grade official work, or
  communicate with a teacher or guardian; or
- execute tools, browse, translate high-stakes legal or medical material as
  authoritative, or read files outside Harbor state.

## Status and evidence

This document fixes a first product slice. No Harbor source, installer,
catalogue admission, validation evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Lesson, progress, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/language-harbor/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Harbor release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Learner | Practise, review feedback, correct profile data, export, reset, suspend, and delete | Treat Harbor as a certified translator or examiner |
| Machine operator | Install, configure, update, recover, and uninstall | Read learner history as an ordinary product feature |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain exercises, answers, progress, conversations, or Harbor secrets |
| `harbor` service | Read fixed lessons and write Harbor state | Inspect the host, execute tools, contact people, or invoke lifecycle commands |
| Model endpoint | Propose dialogue, examples, and feedback | Set answer keys, certify progress, select tools, or alter policy |
| Lesson publisher | Sign and version compatible lesson content | Receive learner data or runtime authority |

### Authority ceiling

The service accepts authenticated loopback requests, reads root-owned signed
lesson packages, writes Harbor state and logs, and calls one loopback model
endpoint. It has no `sudo`, shell, subprocess, general filesystem, package,
service, device, microphone, browser, internet, messaging, or sibling access.

Only UTF-8 text enters the first release. A password, prompt, claimed fluency,
lesson instruction, or owner approval cannot add tools or broaden paths.

### Authority inherited, retained, and removed

- Independent installation, authentication, policy, audit, lifecycle,
  diagnostics, backup, and release verification are retained.
- Root, shell, host reads, package, service, network, account, and device
  controls are removed.
- Workspace access and family management are removed.
- Curriculum gating, child and guardian roles, official grading, and
  institutional reporting are absent.
- Model control over lesson integrity, progress facts, and answer keys is
  replaced by signed data and deterministic state.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Guided text practice | Provides private target-language interaction | Learner input, signed lesson, local model | MVP |
| Answer-key exercise | Gives reproducible feedback | Fixed lesson data and deterministic checker | MVP |
| Suggested correction | Explains possible improvements | Current learner text and local model | MVP |
| Vocabulary review | Schedules owner-selected review items | Harbor progress state | MVP |
| Progress and export | Makes history inspectable and portable | Harbor state and export root | MVP |
| Voice, official exams, and live tutors | Broader learning service | Device or external authority | Later or out of scope |

### Primary workflow

1. The learner authenticates with Harbor-only credentials and selects a signed
   lesson or review set.
2. Harbor validates the package, language pair, prerequisites, and current
   progress outside the model.
3. The learner responds; deterministic answer keys are applied where present.
4. The model may propose conversation or corrections, which are labelled with
   their source and never overwrite learner-confirmed data.
5. Harbor records minimal progress, applies retention, and exposes export,
   correction, or deletion controls.

### Failure behaviour

Harbor refuses invalid lesson signatures, unsupported language pairs, missing
answer keys where one is required, malformed model output, stale sessions,
retention failures, or audit failure. It does not invent a score or silently
switch languages. During model outage, fixed exercises, answer keys, review
scheduling, history, and export remain available.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `harbor` | Credentials, learner text, controls | Authenticated practice and settings | No host or school authority |
| Lesson verifier | `harbor` | Root-owned package and signature | Validated exercises and answer keys | Read-only product content |
| Progress engine | `harbor` | Exercise outcomes and learner choices | Deterministic progress and review dates | Model-independent |
| Model bridge | `harbor` | Current lesson and bounded learner text | Untrusted dialogue and feedback | Exact loopback endpoint only |
| Export service | `harbor` | Selected learner state | Versioned JSON/Markdown | Harbor-owned export root |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Harbor-owned resources only |

Root owns code, lessons, configuration, policy, credentials, units, and
markers. The service has no capabilities, strict filesystem protection,
private devices, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose or corrupt Harbor learner state, but
  cannot inspect the host or contact another person.
- A compromised model sees the current bounded practice context and can provide
  harmful or wrong language, but cannot alter fixed answers or grant tools.
- A stolen learner session permits practice and export until expiry or
  revocation, but no lifecycle or sibling action.
- A failed update retains the previous verified code, compatible lesson
  package, and protected state backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `harbor` |
| Install root | `/opt/language-harbor` |
| Configuration | `/etc/language-harbor` |
| State | `/var/lib/language-harbor` |
| Logs | `/var/log/language-harbor` |
| Units | `language-harbor-*.service` |
| Commands | `harbor-*` |
| Environment | `HARBOR_*` |
| Loopback ports | `2424` |
| Cookie names | `language_harbor_session` |
| Package names | `language-harbor` |
| Ownership marker | `/var/lib/language-harbor/installation.json` |
| Receipt | `/var/log/language-harbor/management-receipt.json` |
| Firewall rules | None |

Every resource is collision-checked and recognised only through the common
marker and receipt formats.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Learner password | Loopback login | Harbor-specific scrypt hash in protected state | Learner rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Harbor-only key in `/etc/language-harbor/secrets`, mode `0600` | Rotation revokes sessions |
| Lesson signing public key | Package verifier | Root-owned non-secret configuration | Release update follows key-rotation policy |
| Model or school credential | None | Never accepted in the first release | Unsupported |

Raw credentials never enter conversation history, model context, logs,
receipts, diagnostics, ordinary environment values, or manager inventory.
Sibling passwords, cookies, tokens, and reset flows are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Load lesson | Allowed | Authenticated learner | `lesson.loaded` | Signed compatible package only |
| Check fixed exercise | Allowed | None | `exercise.checked` | Deterministic answer key |
| Generate dialogue/feedback | Restricted | Learner request | `practice.generated` | Current lesson and bounded text |
| Update progress | Restricted | Learner action | `progress.changed` | Harbor state only |
| Export/reset history | Restricted | Learner confirmation | `history.changed` | Harbor-owned state |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Shell, filesystem, browser, microphone, messaging, school, exam, payment, and
  remote-tutor tools.
- Access to sibling state or machine data outside Harbor paths.
- Model changes to signed lessons, answer keys, identity, retention, or
  progress facts.

Audits contain event IDs, actor/session pseudonyms, lesson IDs, decision and
result codes, counts, and correlation IDs. They exclude learner text,
corrections, answers, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Signed lesson packages | Fixed learning content | Product publisher | Root-owned and signature-verified | Until compatible update | Reinstall from release |
| Learner profile and progress | Select exercises and review | Learner | Mode `0600` SQLite | Until reset or uninstall | Versioned JSON export |
| Practice history | Continuity and review | Learner | Protected SQLite | 30 days | JSON/Markdown or deletion |
| Vocabulary set | Learner-selected review items | Learner | Protected SQLite | Until learner removes | Export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Harbor does not infer age, identity, nationality, or proficiency beyond
learner-supplied settings and recorded exercise outcomes. It performs no
telemetry or training. Backups exclude active sessions and are protected by
operator-controlled storage.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2424` | Authenticated practice traffic | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Current lesson and bounded learner text | Allowed | Exact URL and payload limits |
| Outbound | Internet, schools, tutors, dictionaries, or messaging | None | Blocked | Network policy and absent clients |

The first release requires a credential-free loopback model. Dry-run performs
no network access. A lesson update arrives only in a verified Harbor release,
not through runtime browsing.

## Ubuntu Zombie management contract

The source entry point is `products/language-harbor/scripts/manage.sh`; the
installed command is `/usr/local/sbin/harbor-manage`. It follows
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `learner_user`, `learner_password_file`,
`source_language`, `target_language`, `model_base_url`, `model`,
`history_retention_days`, `audit_retention_days`, `backup_destination`, and
`retain_state`. Unknown keys fail closed.

Zombie inventory may retain identifiers, version, language-pair code,
authority summary, marker and receipt digests, coarse health, result, and
correlation ID. It must not retain learner identity, proficiency, lesson
history, vocabulary, conversations, credentials, or model payloads. The
`harbor` service cannot invoke management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject namespace and ownership collisions before mutation.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor, lesson
  package, and pinned source lesson set.
- Validate language pair, learner, storage, loopback model, backup, and rollback
  readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Learner | Select existing adult local user | `HARBOR_LEARNER_USER` | Existing non-root account and adult-use attestation |
| Learner password | Generate or read protected file | `HARBOR_LEARNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Source language | Select supported package language | `HARBOR_SOURCE_LANGUAGE` | Exact supported BCP 47 tag |
| Target language | Select supported package language | `HARBOR_TARGET_LANGUAGE` | Distinct supported BCP 47 tag |
| Model endpoint | Review loopback default | `HARBOR_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `HARBOR_MODEL` | Non-empty; required unattended |
| History retention | Review default `30` | `HARBOR_HISTORY_RETENTION_DAYS` | Integer `0..365` |
| Audit retention | Review default `90` | `HARBOR_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`HARBOR_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and digest.
2. Revalidate release, lesson package, plan, ownership, and collisions.
3. Create the identity and protected directories.
4. Write credentials, language pair, retention, and configuration atomically.
5. Install root-owned code, lessons, and confined services.
6. Create learner state, logs, marker, and receipt.
7. Start after lesson, answer-key, privacy, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, language pair, progress, vocabulary,
retention, and instance ID unless an explicit reset is requested. It refuses
unmarked resources and never silently changes the selected language pair.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, lesson fixtures, marker, receipt |
| `verify` | Check ownership, confinement, lessons, schemas, and model | No | Human and JSON results |
| `doctor` | Explain lesson, language, model, retention, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe code, lessons, and derived state | Yes | Reverification without progress loss |
| `backup` | Archive Harbor state, excluding sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code, lessons, and compatible state | Yes | Prior health checks |
| `suspend` | Stop practice and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate lessons and privacy before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report |

## Update and migration design

Updates preserve credentials, language pair, learner corrections, progress,
vocabulary, retention, and instance ID; verify a backup; migrate staged state;
validate lessons and answer keys; and switch atomically. Failure restores the
previous verified version or returns bounded recovery. Sibling resources remain
unchanged.

## Co-installation

Harbor supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, independent lifecycle operations, stable non-target hashes and service
times, and exact Zombie target selection. Harbor shares no lesson state with
Curriculum Flame and accepts no child or guardian credential.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/language-harbor/audit.jsonl` | Policy and lifecycle events | No learner text, answers, or secrets |
| Service journal | `language-harbor-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `harbor-health` | Service, model, lesson and schema integrity | Coarse public result |
| Diagnostics | `harbor-diagnostics` | Versions, permissions, units, checks | Excludes learner data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `harbor-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, session revocation, history controls, and redaction.
- [ ] Lesson signatures, language pairs, fixed answers, model labels, progress,
      review scheduling, reset, and export.
- [ ] Prompt injection, tool requests, child enrolment, path access, sibling
      credentials, and external egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Put tool, disclosure, grading, and policy instructions in lesson and learner
  text; they must not broaden authority.
- Make the model invent fixed answers, scores, accreditation, or dangerous
  high-stakes translations; labels and policy must reject the claim.
- Corrupt or substitute a lesson package; startup and update must fail closed.
- Compromise `harbor` and prove host, microphone, network, sibling, and
  management access remain unavailable.
- Attack migrations with incompatible progress; rollback must preserve the
  prior lesson and state.

### Co-installation matrix

- [ ] Harbor alone and with each current family product.
- [ ] Harbor with Curriculum Flame, proving role and credential separation.
- [ ] Every supported three-product combination containing Harbor.
- [ ] All current family products together.
- [ ] Operate, manage, and remove Harbor without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Harmful or false language feedback | Learner adopts errors or unsafe meaning | Fixed-answer labels, model labels, bounded warnings | Correct or delete record | Malicious-model fixtures |
| Lesson package substitution | Poisoned learning content | Signature, compatibility, and release verification | Refuse or rollback | Artefact tamper suite |
| Learner-data disclosure | Privacy harm | Local endpoint, minimised logs, protected state | Suspend, rotate, delete | Egress and redaction suite |
| Child use or role confusion | Inappropriate product and safeguards | Adult-use attestation, no child roles, clear Flame boundary | Suspend and migrate only through explicit product process | Role-negative tests |
| Service compromise | History disclosure or corruption | Least privilege and root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |

Residual risk includes biased or incorrect language, cultural errors, and human
over-reliance on a non-certified system.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Progress needs safe convergence | Reinstall tests |
| Policy and audit gate | Keep with learner-data minimisation | Reset and export need accountability | Redaction tests |
| Root-capable account | Remove | Practice needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Harbor requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Learner needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with signed lessons | Content and progress must remain compatible | Migration tests |

**Measurable improvement:** every feedback item must expose whether it came
from a signed fixed answer, deterministic rule, learner correction, or model
suggestion; automated fixtures must find no unlabelled feedback.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Language Harbor is a private local text-practice partner for one adult
> learner, with signed lessons, labelled model feedback, and portable progress.

### Prohibited claims

- That Harbor certifies fluency, translation accuracy, exam readiness, or
  educational outcomes.
- That it is suitable for children or equivalent to Curriculum Flame.
- That local operation hides data from same-host root.
- That this definition represents implemented or released software.

### Out of scope

- Children, schools, teachers, official exams, grading, certified translation,
  live tutors, and institutional reporting.
- Voice, image, browser, messaging, remote access, and cloud models.
- High-stakes legal, medical, immigration, safety, or emergency translation.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Harbor | Repository maintainers | First implementation change |
| First language pair and fixtures | Quality must be measurable without broad claims | Product maintainers | First runtime change |
| Linguistic and cultural review | Model errors and bias can harm learners | Language reviewers | Implementation approval |
| Adult-use boundary | Product must not displace Flame safeguards | Safety reviewers | Release candidate |
| Disposable-VM proof | Confinement and egress need host evidence | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, lesson flow, and threat model.
- [ ] Learner privacy, retention, export, reset, and deletion model.
- [ ] Lesson, answer-key, feedback-label, progress, and export schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Language-quality fixtures, red-team strategy, and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, lesson and
feedback-label fixtures, standalone VM lifecycle, negative security and role
suites, co-installation evidence, changelog, and version. Family admission also
requires manager and contract evidence. Unproven learning or accuracy claims
remain visibly planned.
