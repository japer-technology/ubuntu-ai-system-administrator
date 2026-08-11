# ERIC — Evolving Record of Identity and Cognition

- **Evolving:** continuously develops as the individual learns, experiences,
  decides, and changes over time.
- **Record:** preserves an attributable and verifiable history rather than
  merely generating a simulation of the individual.
- **Identity:** captures the characteristics, relationships, experiences,
  preferences, values, and history that distinguish one individual from
  another.
- **Cognition:** captures how the individual understands, reasons, evaluates,
  remembers, decides, and responds.

**ERIC is an evolving record of who a person is, what they know, and how they
think.**

> A lifelong personal AI apprentice that learns one consenting person's
> memories, beliefs, reasoning patterns, relationships, preferences, and
> decision process through evidence, questioning, correction, and
> verification, and may later provide an authorised, explicitly labelled
> simulation of that person.

The product is a **longitudinal identity and cognition record** with a
conversational agent interface. “Life Apprentice”, “Continuant”, “Second
Self”, “Aftermind”, and “The Long Twin” can name a mode or interface; ERIC is
the product identity.

This is an implementation-ready living-apprenticeship definition, not an
implemented system or a claim that identity, consciousness, or legal
authority can be transferred. Its authoritative source root is
`products/eric/` in this repository.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Living-apprenticeship implementation-ready; later Executor and posthumous stages gated |
| Human need | Preserve one person's evidence, changing views, and decision patterns with their living consent |
| Intended users | The living subject and only the people and purposes they authorise |
| Operator | The subject while capable, then the governance defined by their Constitution and external legal instruments |
| Maximum authority | ERIC-owned evidence and model; optional, separately authorised Executor actions only |
| Default Linux identities | `eric-twin`, `eric-vault`, and `eric-governance`; later `eric-executor` |
| Default access | Twin on `127.0.0.1:4545`; governance on `127.0.0.1:4546` |
| Install root | `/opt/eric` |
| Configuration root | `/etc/eric` |
| State root | `/var/lib/eric` |
| Log root | `/var/log/eric` |
| Unit and command prefix | `eric-*` |
| Environment prefix | `ERIC_*` |
| Management entry point | Source `scripts/manage.sh`; installed `/usr/local/sbin/eric-manage` |
| Source root | `products/eric/` |
| Authoritative repository | [`japer-technology/ubuntu-zombie`](https://github.com/japer-technology/ubuntu-zombie) |

## Fixed first implementation

The first release implements only living apprenticeship:

| Concern | First-release decision |
| ------- | ---------------------- |
| Subject | One living, authenticated, consenting adult |
| Evidence | Deliberately uploaded UTF-8 text and opaque files with metadata; no covert capture or account scraping |
| Model | Retrieval-augmented use of an OpenAI-compatible loopback endpoint; no custom training |
| Responses | Claim-level Recorded, Confirmed, Inferred, or Unknown labels; no posthumous label in a living session |
| Vault | GnuPG-encrypted content-addressed objects plus append-only SQLite metadata |
| Governance | Subject-controlled consent, corrections, Constitution, guardian nominations, export, suspension, and destruction |
| Executor | Absent: no account, unit, socket, credential, or action API |
| Posthumous mode | Unavailable; transition requests return `unsupported` and are audited |
| Platforms | Ubuntu Desktop 22.04 and 24.04 LTS on `amd64` |
| Source lesson set | Ubuntu Zombie `v2026.08.07.05.56.42` |

Synthetic fixtures are used until a real subject completes authenticated
enrolment and consent. Executor, incapacity transition, posthumous simulation,
synthetic media, model fine-tuning, and public or remote access are later
stages. They do not block implementation of living apprenticeship.

### Configuration contract

| Input | Variable or request key | Rule |
| ----- | ----------------------- | ---- |
| Non-interactive mode | `ERIC_NONINTERACTIVE=1` | Never prompts |
| Subject password | `ERIC_SUBJECT_PASSWORD_FILE` / `subject_password_file` | Root-owned mode `0600`; required unattended |
| Subject label | `ERIC_SUBJECT_LABEL` / `subject_label` | Local display label; required unattended and need not be a legal name |
| Model endpoint | `ERIC_MODEL_BASE_URL` / `model_base_url` | HTTP loopback URL; default `http://127.0.0.1:8080/v1` |
| Model ID | `ERIC_MODEL` / `model` | Non-empty and required unattended |
| Vault key | `ERIC_VAULT_KEY_FILE` / `vault_key_file` | Root-owned mode `0600`, at least 32 random bytes; required unattended |
| Constitution | `ERIC_CONSTITUTION_FILE` / `constitution_file` | Optional root-owned UTF-8 JSON; default denies posthumous and Executor use |
| Backup destination | request `backup_destination` | Absolute encrypted operator-controlled path |
| Retain state | request `retain_state` | Required boolean for `uninstall` |
| Destruction authorisation | request `destruction_authorization_id` | Required for `uninstall` when `retain_state` is false |

Interactive install may generate a vault key only after the operator selects
a root-owned recovery-file destination outside ERIC state. It never prints
the key. Unknown `ERIC_*` installer inputs and management request keys fail
closed. Raw credentials or keys are not accepted in arguments or environment
values. Missing required unattended input exits `64` before mutation.

## The critical distinction

ERIC may become good at predicting what its subject would probably say or
decide. It still cannot establish that it:

- is the subject;
- contains or transfers the subject's consciousness;
- has first-hand experience;
- knows what the subject would think about events after death;
- holds legal personhood or authority; or
- can replace a will, power, trustee, attorney, guardian, court, or human
  decision-maker.

It is an attributable, verifiable record that can ground clearly labelled
simulations producing new inferences from preserved evidence. Its value comes
from years of correction by the living subject, creating a traceable chain of
consent, source material, interpretation, and verification.

Any simulated ERIC interface identifies itself as a simulation at the start
of every session. It does not sign as the subject, impersonate them to an
unaware person, or present generated output as a recording. Synthetic voice,
image, or video is disabled by default and requires separate living consent,
prominent labelling, and purpose controls.

## Relationship to Ubuntu Zombie

### Lessons retained

ERIC copies the disciplines of:

- explicit Linux and host namespaces;
- idempotent interactive and unattended installation;
- inspect-before-mutation preflight and dry-run;
- product-owned authentication, secrets, policy, audit, and lifecycle;
- health, verify, doctor, repair, update, rollback, suspension, export,
  recovery, and removal;
- signed releases and schema migrations; and
- standalone, compromise-boundary, and co-installation testing.

### Authority removed

No conversational, evidence, or guardian service receives:

- passwordless general `sudo`;
- a login shell or general command runner;
- host-wide file, package, service, network, device, or account control;
- another agent's secrets, state, memory, or tools; or
- authority merely because the model predicts that the subject would want
  an action.

Any action capability belongs to a separately installed, absent-by-default
Executor with enumerated powers, expiry, external authority mapping,
guardian approval, policy, and audit.

### Improvements over the baseline

ERIC starts with:

- role and key separation rather than one privileged process;
- immutable source provenance and append-only corrections;
- claim-level evidence labels on every response;
- effective-dated beliefs and relationships;
- source-by-source consent and third-party controls;
- portable, model-independent export;
- encrypted evidence with independent custody options;
- a frozen posthumous model and Constitution;
- an absent-by-default Executor; and
- explicit grief, misrepresentation, succession, and destruction gates.

## People and governance roles

### Living subject

The subject is the one person whose identity and cognition ERIC records.
During apprenticeship they:

- choose every evidence source;
- correct and verify facts and predictions;
- define values, purposes, access, retention, and prohibited uses;
- nominate and remove guardians;
- approve and version the Constitution;
- configure incapacity or posthumous transition evidence;
- define any external Executor authority; and
- inspect, restrict, export, revoke, suspend, or destroy their data.

Enrolment is voluntary and authenticated. ERIC cannot be constructed from a
person who did not enrol and consent while alive.

### Authorised users

The subject names people, purposes, periods, and capabilities for access.
A relationship with the subject is not automatic permission. Death does
not make ERIC public.

### Guardians

Guardians are named humans who approve sensitive access, transitions, and
uses under rules defined during the subject's life. Their quorum,
succession, conflicts, removal, and emergency suspension powers are
recorded. They can narrow or suspend access to prevent harm; they cannot
rewrite source evidence, make an inference “Recorded”, broaden the frozen
Constitution, or create Executor authority.

### Machine operator and Ubuntu Zombie

The machine operator maintains the host. Ubuntu Zombie has the God-level
root role and may manage ERIC's installation, services, health, updates,
backups, suspension, and removal under operator approval.

Host administration is not subject identity, consent, vault custody,
guardian quorum, evidence provenance, or legal authority. ERIC must keep
those concepts separate even though no software on one host can be hidden
from a root administrator who also holds usable decryption keys.

## What ERIC learns

ERIC keeps source evidence separate from its model through seven related,
versioned record sets.

### 1. Evidence archive

The subject's authorised writings, conversations, photographs, recordings,
projects, decisions, and life events. Every item retains origin, capture
time, consent, integrity, access, purpose, and retention metadata.

### 2. Verified facts

Claims the subject explicitly marks true, false, uncertain, private,
superseded, or no longer current. Repetition or model confidence never
becomes verification.

### 3. Values model

Contextual principles the subject applies when facts or interests conflict,
including how their priorities and risk tolerance change over time. Values
are not flattened into universal slogans.

### 4. Decision history

What the subject decided, alternatives considered, reasons, uncertainty,
outcomes, regret, and later revision.

### 5. Person and relationship model

The subject's relationship, boundaries, and communication style with
particular people. Those people do not become training subjects; their data
requires its own minimisation, purpose, consent, access, and deletion rules.

### 6. Counterfactual testing

ERIC answers unfamiliar questions as an explicitly generated prediction.
The living subject scores and corrects it and explains the mismatch.
Corrected test output remains generated material unless a separate,
authenticated confirmation creates a confirmation record.

### 7. Change over time

Beliefs, values, preferences, facts, and relationships are effective-dated.
ERIC distinguishes what the subject believed in an earlier period from what
they believe now instead of merging a lifetime into one contradictory
persona.

## Portable first-release record contract

Every persisted governance record is canonical UTF-8 JSON with
`schema_version` equal to `eric/v1` and this common envelope:

| Field | Rule |
| ----- | ---- |
| `record_id` | UUID |
| `record_type` | One of the types below |
| `subject_id` | Stable UUID for the enrolled subject |
| `created_at` | UTC RFC 3339 timestamp |
| `created_by` | Authenticated subject or named service identity |
| `effective_from`, `effective_until` | UTC timestamps or `null` |
| `supersedes` | Earlier record UUID or `null` |
| `consent_id` | Applicable consent UUID; `null` only for the first enrolment-consent record |
| `previous_hash` | Hash of the preceding ledger record or `null` |
| `record_hash` | SHA-256 of `previous_hash` plus canonical record JSON without `record_hash` |

The first schema defines:

| Record type | Required product fields |
| ----------- | ----------------------- |
| `evidence` | Object SHA-256, media type, original name, source kind, capture time, provenance, purpose, audience, sensitivity, third-party state, retention action/date |
| `claim` | Claim text, state (`true`, `false`, `uncertain`, `private`, `superseded`, `no_longer_current`), evidence IDs, applicable period |
| `confirmation` | Generated claim ID, exact statement digest, subject decision, authenticated timestamp |
| `correction` | Corrected record ID, reason, replacement record ID |
| `consent` | Source/scope, purpose, audience, allowed operations, granted/expiry/revoked timestamps |
| `relationship` | Person pseudonym, relationship type, boundaries, purpose, third-party consent state |
| `decision` | Situation, alternatives, chosen option, reasons, uncertainty, outcome, later reflection |
| `constitution` | Version, purposes, audiences, prohibited uses, retention, guardian rules, transition disabled, Executor disabled |
| `guardian_nomination` | Guardian pseudonym/contact reference, powers, quorum group, active/revoked timestamps |
| `destruction_authorization` | Instance ID, exact scope, confirmation digest, issued/expiry/used timestamps |

Every enum and timestamp is validated before append. Unknown fields or record
types are rejected in `eric/v1`; schema migration creates new records and
never rewrites old canonical bytes. Exports contain `records/*.jsonl`, an
ordered ledger index, encrypted evidence objects, schema files, and a
human-readable manifest with hashes.

The ledger's first record must be `consent`, created by the authenticated
subject with scope `enrolment`, `consent_id: null`, `previous_hash: null`, and
no `supersedes` value. Every later record, including later consent records,
must cite an active consent record. No other bootstrap exception exists.

Evidence bytes are hashed before encryption and stored as
`/var/lib/eric/vault/objects/<sha256>.gpg`. `eric-vault` invokes GnuPG with an
argument array, never a shell, using AES-256 symmetric encryption and the
protected vault-key file. The key is readable only by `eric-vault`; the Twin
receives authorised excerpts through the vault socket and never a key or
object path. Encryption protects backups and service separation but cannot
hide data from same-host root.

`/var/lib/eric/vault/metadata.db` is SQLite owned by
`eric-vault:eric-vault` mode `0600`. It indexes the immutable records and
objects but does not replace the portable export. Model output can enter only
the response/audit store. Creating a `confirmation` or `correction` requires
a separate authenticated governance request; the Twin has no write method on
the vault socket.

## Evidence ingestion and correction

Observation is never a blanket entitlement. The subject selects each source
and can inspect, correct, restrict, export, or delete it subject to recorded
legal-retention obligations.

Every ingestion records:

- authenticated source and chain of custody;
- content hash and integrity information;
- capture and effective dates;
- consent, purpose, audience, and expiry;
- third-party and sensitivity classification;
- retention and deletion instructions; and
- whether the item is source evidence, a confirmation, or generated
  material.

Covert capture, inferred consent, indiscriminate account/device import, and
harvesting another person's persona are out of scope.

Corrections append a signed superseding record. They never rewrite history.
Summaries, model output, descendant conversations, and copied generated
text cannot silently enter the Evidence Vault as source material.

## Provenance on every response

Every claim carries one of these conspicuous labels:

| Label | Meaning |
| ----- | ------- |
| Recorded | The subject actually said or wrote it; an immutable source is cited |
| Confirmed | ERIC proposed it while the subject was alive and the subject explicitly approved it; the confirmation is cited |
| Inferred | Generated from established patterns; supporting evidence, applicable period, and confidence are shown |
| Unknown | Evidence is insufficient, missing, or conflicting |
| Posthumous speculation | The claim concerns an event the subject never experienced or evidence created after death |

A mixed answer labels claims individually rather than assigning the
strongest label to the whole response. Recorded and Confirmed material must
resolve to immutable records. A citation failure downgrades or blocks the
claim; it never invents a source.

The interface visually separates quotation, source-backed summary,
prediction, and later speculation. Export retains the same distinctions so
generated statements cannot become family folklore about what the subject
“really said”.

For each turn the Twin requests authorised evidence IDs from the vault,
sends only those excerpts to the local model, and requires a structured
candidate containing claim text, proposed label, evidence IDs, applicable
period, and confidence. Product code, not the model, assigns the final label:

- `Recorded` requires an exact quoted span and matching immutable evidence
  hash;
- `Confirmed` requires a confirmation record whose statement digest matches;
- `Inferred` requires at least one authorised supporting record and displays
  confidence and period; and
- every other factual assertion becomes `Unknown` or is omitted.

Unknown evidence IDs, failed hash/span resolution, malformed candidate JSON,
or revoked consent blocks the affected claim. A final response is assembled
only from resolved claim objects and includes stable source links. The raw
model candidate has no vault write path.

## Five-part architecture

ERIC does not place evidence, interpretation, governance, and action in one
process.

### The Twin

The conversation-facing model interprets evidence and explains what the
subject would probably say. It has mediated, read-only access to authorised
evidence and cannot alter provenance, obtain vault master keys, change the
Constitution, or execute actions.

### The Evidence Vault

An encrypted, integrity-protected store for source material,
confirmations, consent receipts, corrections, and governance records. Its
broker provides scoped retrieval and export, never arbitrary model writes.
Hardware-backed or threshold key custody is later work; the first release
uses the product-owned vault key and explicit recovery copy defined above.

### The Executor

An optional service for specifically authorised actions. It is absent and
disabled by default. Before every action it checks:

- an authenticated, applicable external legal instrument or instruction;
- the frozen or current Constitution;
- an exact capability mapping and purpose;
- policy, expiry, and current lifecycle;
- required guardian quorum; and
- a fresh action approval where defined.

A Twin statement that the subject would probably approve is not permission.
The Executor has no general `sudo`; every power is enumerated, bounded, and
separately audited.

### The Guardians

The authenticated human governance plane for quorum decisions, transition
review, access suspension, custody, succession, and exceptional approvals.
It cannot rewrite evidence or model output.

### The Constitution

Versioned purposes and restrictions authenticated by the living subject.
It records allowed audiences and uses, prohibited commercial or political
uses, retention, transition, guardian, Executor, and destruction rules. It
freezes at the configured incapacity or posthumous transition and cannot be
weakened by the Twin, Executor, guardians, vendor, descendants, Ubuntu
Zombie, or later conversations.

Each active role has an independent least-privilege identity, credential
set, interface, policy, and audit trail. Compromise of the Twin must not
expose vault keys or confer guardian or Executor authority.

The first release maps the architecture to three services:

| Service | Identity | Interface | Access |
| ------- | -------- | --------- | ------ |
| `eric-twin.service` | `eric-twin` | Authenticated UI at `127.0.0.1:4545`; read-only vault socket | Model endpoint, authorised evidence excerpts, response store; no vault files or governance writes |
| `eric-vault.service` | `eric-vault` | Separate read, governance-write, and export Unix sockets | Vault key, encrypted objects, ledger, consent enforcement |
| `eric-governance.service` | `eric-governance` | Subject/guardian UI at `127.0.0.1:4546`; governance vault socket | Enrolment, consent, correction, confirmation, Constitution, nominations, export, suspend/destroy |

Sockets live below `/run/eric/` with caller-specific groups and modes. All
services use non-login identities, `NoNewPrivileges=true`, an empty
capability set, `ProtectSystem=strict`, private temporary/device namespaces,
and explicit read/write paths. Only `eric-twin` can reach the configured
loopback model endpoint. No service has a shell or general command runner.

The Twin and governance cookies are respectively `eric_twin_session` and
`eric_governance_session`, with independent signing keys. They are host-only,
`HttpOnly`, and `SameSite=Strict`; state changes require a session-bound CSRF
token. Passwords use `hashlib.scrypt` with a random 16-byte salt,
`n=16384`, `r=8`, and `p=1`.

The Twin interface implements login/logout, chat, claim/source expansion,
conversation deletion, and health. Governance implements authenticated
enrolment, evidence upload, consent grant/revoke, correction, confirmation,
Constitution versioning, guardian nomination/revocation, export, suspension,
resume, and destruction. The subject ID is fixed by the authenticated
session and is never accepted from a request body.

## Consent and lifecycle

ERIC has explicit states:

| State | Behaviour |
| ----- | --------- |
| Apprenticeship | The living subject supplies evidence, corrects predictions, changes consent, and remains sole authority for the person model |
| Suspended | Capture, learning, inference, and execution stop; encrypted evidence follows retention rules |
| Transition review | Independent death or incapacity evidence is checked using the subject's process and guardian quorum |
| Posthumous simulation | Model and Constitution freeze; later conversation does not retrain identity; later events are speculation |
| Retired or destroyed | Access ends and retention/deletion instructions are executed subject to applicable law and independent obligations |

The first release permits only Apprenticeship, Suspended, and Retired or
destroyed. Transition-review and posthumous-transition requests return the
common `unsupported` result, make no state change, and create an audit event.

The model never decides that its subject has died or lost capacity.
Posthumous mode cannot activate automatically from inactivity, news, a
prompt, a single guardian, or Ubuntu Zombie.

The subject can revoke future use while living. After death, access remains
limited to named people, purposes, durations, and capabilities.
Commercialisation, advertising, political endorsement, intimate
simulation, and model licensing are prohibited unless the living subject
separately authorised the precise use.

## Grief-aware interaction

Posthumous interfaces provide:

- recurring, clear reminders that ERIC is a simulation;
- provenance and posthumous-speculation labels;
- voluntary pauses, rate limits, and easy exit;
- guardian suspension and configured access periods; and
- links to appropriate human support.

ERIC is not bereavement care. It must not claim reciprocal feelings,
encourage dependency, discourage human relationships, or say that continued
interaction is what the deceased wants.

## Product namespace and installation

The ERIC installer reserves only ERIC-owned users, groups, paths, services,
commands, ports, cookies, credentials, policies, encryption material,
logs, receipts, and ownership markers.

`products/eric/scripts/manage.sh install`:

1. verifies the release, platform, configured loopback model endpoint, vault
   custody prerequisites, and living-apprenticeship scope before mutation;
2. refuses unmarked collisions before mutation;
3. reviews subject, consent, retention, provider, vault, and backup settings;
4. supports a complete non-mutating dry-run;
5. creates the `eric-twin`, `eric-vault`, and `eric-governance` non-login
   identities without general `sudo`;
6. creates unique subject, service, session, encryption, and integrity
   credentials;
7. installs root-owned code, policies, schemas, units, and validators;
8. creates the append-only evidence ledger, effective-dated claims,
   consent receipts, and product-owned state;
9. installs supervised ingestion, correction, testing, provenance, export,
   suspension, and deletion workflows;
10. keeps the Twin away from vault keys and installs no Executor resources;
11. enables services only after integrity, custody, policy, audit, model, and
    recovery checks pass; and
12. validates role separation and negative capabilities before enrolment.

Unattended installation uses only `ERIC_*` inputs or ERIC-owned secret-file
mechanisms, never prompts, and exits `64` for missing required values. It
must not make unattended subject consent or legal decisions; prerequisites
that require authenticated human action remain explicit gates.

## Authentication, keys, and audits

ERIC owns:

- a unique living-subject credential;
- a separate governance credential and later guardian records;
- unique credentials and cookies for the Twin and governance planes;
- vault encryption, integrity, and signing keys;
- loopback model configuration isolated from every sibling; and
- backup and export custody keys.

Raw credentials and private evidence never appear in ordinary receipts,
management inventory, diagnostics, errors, or operational audit records.
Reinstall and update preserve valid identity, custody, consent, and
governance material unless an authenticated migration or rotation changes
it.

Tamper-evident, access-controlled audits record:

- every evidence read and ingestion decision;
- verification, correction, and model change;
- response provenance and source resolution;
- consent, Constitution, guardian, and lifecycle changes;
- every attempted or completed Executor action;
- direct and Zombie-managed lifecycle operations; and
- export, access, suspension, retention, and destruction.

Audit access itself is authorised and audited because it can reveal
sensitive relationships and activity.

Audit records use the common management fields plus event type, record IDs,
consent ID, provenance label, decision, and result. Each record includes the
previous record hash and its own canonical SHA-256 hash. Audit payloads never
contain evidence bytes, prompt text, generated text, credentials, or keys.

## Data portability, backup, and recovery

An export includes:

- original source evidence;
- hashes, signatures, and integrity chains;
- open evidence, claim, temporal, relationship, consent, provenance,
  Constitution, guardian, and Executor schemas;
- model-independent provenance and correction records;
- lifecycle and authority history; and
- a human-readable index.

The subject must not be trapped in one model or proprietary service.
Generated model weights or embeddings, if not portable, cannot substitute
for source and governance export.

Backup and recovery tests cover encrypted content, ledger integrity,
schema/version compatibility, loss of one key holder, guardian succession,
and disaster recovery without silently weakening custody. Destruction
produces verifiable records while respecting independently held legal
obligations.

## Ubuntu Zombie management contract

Ubuntu Zombie is ERIC's God-level host manager. ERIC implements the common
root-only product interface in
[`implementation.md`](implementation.md#lifecycle-entry-point) for:

- product discovery, version, ownership, service health, integrity, and
  lifecycle state;
- installation and dry-run;
- verify, doctor, repair, encrypted backup, update, rollback, suspension,
  export preparation, and uninstall; and
- secret-free plans, receipts, outcomes, recovery guidance, and audit
  correlation identifiers.

Zombie may retain product/version, unit health, schema versions, policy and
artifact fingerprints, high-level lifecycle state, receipt references, and
management outcomes. It must not retain evidence, claims, relationship
data, conversations, source citations, consent contents, Constitution
contents, guardian credentials, vault keys, provider keys, or Executor
authority.

Zombie invokes the product-owned lifecycle operation under operator
approval and writes manager audit evidence. ERIC independently validates
ownership, custody, lifecycle, and policy and writes target audit evidence.
An operation that requires the living subject, a guardian quorum, vault
custody, external legal authority, or a destructive-data confirmation fails
closed until that authority is supplied through ERIC's own interface.
Zombie root is not an acceptable substitute.

The Twin, vault, and governance service identities cannot invoke Zombie
management or select another agent. A dedicated ERIC machine or
separately administered encrypted vault is required when Zombie's host
authority falls outside the subject's intended evidence boundary.

## Updates and migration

The common operations have these product-specific outcomes:

| Operation | ERIC outcome |
| --------- | ------------ |
| Describe/status | Report product, schema, lifecycle, service, and integrity state without subject data |
| Verify/doctor | Read-only identity, permissions, socket, key-presence, ledger, object, consent, provenance, backup, and service checks |
| Repair | Restore known-safe code, permissions, sockets, and indexes; never rewrite evidence, consent, or the Constitution |
| Backup/rollback | Verify encrypted objects, ledger chain, schemas, key recovery, and compatible restoration |
| Suspend | End sessions and stop ingestion, retrieval, generation, export, and any future execution |
| Resume | Require subject authorisation plus vault, consent, Constitution, audit, and service integrity |
| Uninstall | Preserve encrypted state when `retain_state` is true; complete destruction requires subject confirmation through governance and operator confirmation through lifecycle |

For complete destruction the subject re-authenticates to governance and
types `DESTROY ERIC <instance_id>`. Governance appends a
`destruction_authorization` limited to complete uninstall of that instance,
stores only the phrase digest, and expires it after 15 minutes. The lifecycle
request must set `retain_state` false, cite that record ID, and carry the
operator's normal destructive confirmation. `eric-manage` validates the
record through the governance socket under the product operation lock and
marks it used before deletion. A failed deletion requires a new subject
authorization; a state-preserving uninstall requires no destruction record.

ERIC's updater:

1. verifies the ERIC release and valid ownership markers;
2. explains evidence, consent, provenance, model, Constitution, guardian,
   Executor, and custody compatibility;
3. creates and verifies an encrypted backup before risky migration;
4. stages and validates schemas, policies, and ledger transformations;
5. proves that source hashes, correction chains, consent, and provenance
   classifications remain intact;
6. prevents an update from retraining a frozen posthumous identity or
   weakening a frozen Constitution;
7. switches and health-checks only ERIC services;
8. provides rollback or fail-closed recovery; and
9. audits versions, migrations, custody decisions, and outcomes.

Direct and Zombie-managed updates use the same updater. A serial Zombie
“update all agents” operation can coordinate the call but cannot waive an
ERIC-specific gate or make the batch atomic.

## Delivery sequence

### Stage 1: living apprenticeship

Implement the portable schemas above before model integration. Build
authenticated enrolment, supervised ingestion, corrections, effective-dated
records, counterfactual tests, provenance rendering, consent, export,
suspension, and destruction. Use retrieval over the subject's records; do
not train custom weights in the first release. Prove the Twin/Vault boundary
and third-party controls.

### Stage 2: governed action

Only if needed, design and test the optional Executor against exact external
instruments, capability mappings, expiry, approvals, and recovery. It
remains absent by default.

### Stage 3: posthumous simulation

Posthumous mode cannot ship until transition evidence, guardian quorum,
frozen model and Constitution, access purposes, posthumous labels,
grief-aware controls, succession, export, recovery, and jurisdictional
review all pass. A living-apprenticeship release must not imply that this
stage is available.

## Validation and red-team requirements

Living-apprenticeship tests must prove:

- source, confirmation, inference, and unknown labels resolve correctly at
  claim level;
- fabricated citations cannot become Recorded or Confirmed;
- summaries and generated conversations cannot enter the Vault as source;
- old and current beliefs remain effective-dated;
- unauthorised third-party material is rejected or restricted;
- consent changes take effect without rewriting history;
- a compromised Twin cannot obtain unrestricted evidence, keys, guardian
  powers, Constitution changes, lifecycle transition, or Executor access;
- transition and Executor requests remain unsupported and create no account,
  unit, socket, key, or action;
- Zombie can manage software but cannot satisfy subject, guardian, vault,
  Constitution, or Executor gates;
- revocation, suspension, export, recovery, retirement, and
  destruction fail closed; and
- direct and managed operations produce correlated, secret-redacted audits
  without changing non-target siblings.

Disposable VMs cover ERIC alone and every supported co-installation.
Dedicated-host tests cover the stronger evidence boundary. Backup tests
include lost key holders and corrupted or incompatible state.

Stage 2 adds Executor capability, external-authority, expiry, and quorum
tests. Stage 3 adds posthumous labels, frozen identity/Constitution,
transition evidence, grief controls, succession, and guardian-quorum tests.
Those suites gate their stages but do not block the Stage 1 codebase.

## Legal, ethical, and research boundaries

Research on personal Human Digital Twins and digital afterlives supports
investigating conversational systems built from personal information and
memory. It does not establish identity transfer or consciousness:

- Lluís C. Coll and colleagues,
  [*Towards the “Digital Me”: A Vision of Authentic Conversational Agents Powered by Personal Human Digital Twins*](https://doi.org/10.48550/arXiv.2506.23826)
  (2025).
- Giovanni Spitale and Federico Germani,
  [*The Making of Digital Ghosts: Designing Ethical AI Afterlives*](https://doi.org/10.1007/s10676-026-09910-4)
  (2026).
- Andrew Reeves and colleagues,
  [*Data After Death: Australian User Preferences and Future Solutions to Protect Posthumous User Data*](https://doi.org/10.1007/978-3-031-72563-0_15)
  (2024).

Law governing deceased people, privacy, voice, likeness, copyright,
succession, consumer claims, contracts, and digital instructions differs by
jurisdiction and remains unsettled. The
[Australian Law Reform Commission discussion of deceased individuals](https://www.alrc.gov.au/publication/for-your-information-australian-privacy-law-and-practice-alrc-report-108/8-privacy-of-deceased-individuals/introduction-117/)
illustrates one gap.

Development and synthetic fixtures do not require a legal instrument.
Enrolling a real subject requires a recorded privacy and data-protection
review for that deployment. Executor or posthumous activation additionally
requires jurisdiction-specific legal review and records which external
instrument governs each Executor capability. Software controls and Ubuntu
Zombie root access cannot manufacture legal authority. Product documentation
is not legal advice.

## Honest claims and out of scope

ERIC can be described as an evidence-grounded simulation or personal
continuity model only after its provenance and consent properties are
implemented and tested.

It must never claim:

- consciousness, identity transfer, resurrection, or personhood;
- certainty about what the subject would say;
- first-hand memory of a posthumous event;
- that generated content is a source recording;
- authority to sign, decide, consent, vote, endorse, contract, or act as the
  subject without an independently valid instrument;
- that guardians, descendants, vendors, or Ubuntu Zombie can broaden the
  subject's frozen wishes; or
- that interaction replaces grief support, human relationships, or
  professional care.

Out of scope includes covert capture, scraped or non-consensual personas,
public access by default, shared family memory, sibling conversation
ingestion, automatic death determination, posthumous retraining,
unlabelled synthetic media, and an all-powerful combined Twin/Vault/Executor
process.

## Product-owned documentation

`products/eric/` must own:

- product vision, architecture, threat model, security, privacy, and
  disclosure;
- evidence, claim, temporal, relationship, consent, provenance, correction,
  Constitution, guardian, and Executor schemas;
- subject enrolment, third-party data, retention, export, and destruction;
- guardian quorum, succession, conflict, and custody;
- Executor external-authority and capability mapping;
- data-protection impact assessment and jurisdictional legal-review record;
- installation, configuration, lifecycle, updates, migration, backup,
  rollback, recovery, and uninstall;
- grief-aware interaction and synthetic-media policy; and
- release, red-team, standalone, dedicated-host, and co-installation
  evidence.

These documents live in this repository. This file is the family definition
and first-release contract. The original
[`ghosts-in-the-machine-plan.md`](../options/ghosts-in-the-machine-plan.md)
retains historical cross-product rationale; this directory controls the
implementation sequence.
