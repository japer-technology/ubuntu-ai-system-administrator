# AI agent definition template

Copy this file to `docs/ai-agent/<agent-name>.md` while a proposal is being
developed. Replace every bracketed instruction, remove sections that are
genuinely not applicable, and link evidence for every completed acceptance
gate.

This template defines an independent product implemented below a dedicated
`products/<product-id>/` root in this repository. It is not a persona file, a
plugin manifest, or a way to add authority to an installed agent. Read the
[family catalogue](README.md), [implementation contract](implementation.md),
and [Ubuntu Zombie reference](ubuntu-zombie.md) first.

---

# [Product name]

> [One sentence stating the human need, intended user, and useful result.]

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | [Idea, product definition, prototype, release candidate, or implemented] |
| Product ID | `[unique-kebab-case-id]` |
| Human need | [One specific need] |
| Intended users | [People who interact with it] |
| Operator | [Person responsible for installation, policy, and removal] |
| Maximum authority | [The strongest action the installed product can perform] |
| Default Linux identity | `[unique non-login account]` |
| Default loopback port | `[unique port]` |
| Install root | `/opt/[unique-product-name]` |
| Configuration root | `/etc/[unique-product-name]` |
| State root | `/var/lib/[unique-product-name]` |
| Log root | `/var/log/[unique-product-name]` |
| Environment prefix | `[UNIQUE_PREFIX]_*` |
| Ubuntu Zombie management | [Supported interface and restrictions] |
| Source root | `products/[unique-product-name]` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

[Describe the problem, the result this agent provides, and why an installed
local AI is appropriate. Keep this narrow enough to test.]

### It must

- [Required user-visible outcome.]
- [Required safety or privacy outcome.]
- [Required operator-control outcome.]

### It must not

- [A tempting but explicitly unsupported use.]
- [A claim the product cannot honestly prove.]
- [An authority or data use outside its purpose.]

## Status and evidence

[State what exists today. Separate implemented behaviour, accepted design,
prototype work, and later ideas. Never describe a planned safeguard as
already enforced.]

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | [Open/passed] | [Link or owner] |
| First implementation slice fixed | [Open/passed] | [Link or owner] |
| Configuration and data contracts fixed | [Open/passed] | [Link or owner] |
| Threat model reviewed | [Open/passed] | [Link or owner] |
| Installer lifecycle complete | [Open/passed] | [Link or owner] |
| Security boundary tested | [Open/passed] | [Link or owner] |
| Update and rollback tested | [Open/passed] | [Link or owner] |
| Standalone VM validation | [Open/passed] | [Link or owner] |
| Co-installation validation | [Open/passed] | [Link or owner] |
| Release verification complete | [Open/passed] | [Link or owner] |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Operator | [Install, configure, approve, suspend, remove] | [Product-specific limits] |
| Ubuntu Zombie manager | [Root-level product lifecycle operations] | [Human, consent, legal, and secret-use limits] |
| Primary user | [Normal interactions] | [Administrative or unsafe actions] |
| Service identity | [Exact runtime access] | [Everything outside the capability set] |
| Additional role | [Optional role] | [Role boundary] |

### Authority ceiling

[State the maximum filesystem, process, network, tool, and privileged-helper
access. Explain why each permission is necessary. A prompt, persona,
password, or approval must not raise this ceiling.]

### Authority inherited, retained, and removed

- [General passwordless `sudo` retained or removed, with the reason.]
- [General shell or command runner retained or removed, with the reason.]
- [Host-wide file reads retained or removed, with the reason.]
- [Package, service, device, or network control retained or removed.]
- [Other inherited privileged mechanism and its disposition.]

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| [Feature] | [Outcome] | [Minimum access] | [MVP/later] |
| [Feature] | [Outcome] | [Minimum access] | [MVP/later] |

### Primary workflow

1. [How the user starts an authenticated interaction.]
2. [How the request is checked and processed.]
3. [How tools or data are mediated.]
4. [How the result is validated and presented.]
5. [What is recorded for the operator.]

### Failure behaviour

[List unavailable services, invalid state, policy failures, ambiguous users,
failed validators, or other conditions that must fail closed. State what the
user sees and what is audited.]

## Architecture and trust boundaries

[List the independently trusted services and data flows. Identify where an
LLM, untrusted input, privileged helper, external provider, browser, or
human approval crosses a boundary.]

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| [Component] | `[service account]` | [Inputs] | [Outputs] | [Exact access] |

### Compromise boundaries

- If the conversation service is compromised, [state the maximum impact].
- If the model/provider is compromised, [state what remains protected].
- If a user session is stolen, [state scope, expiry, and revocation].
- If an update fails, [state what keeps the last valid version recoverable].

## Product-owned namespace

All values must be checked against the host before mutation. The installer
must refuse to adopt an existing resource without a valid ownership marker.
Use the marker and receipt formats in
[`implementation.md`](implementation.md#ownership-marker-and-receipt); do
not invent a product-specific discovery format.

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `[names]` |
| Install root | `/opt/[name]` |
| Configuration | `/etc/[name]` |
| State | `/var/lib/[name]` |
| Logs | `/var/log/[name]` |
| Units | `[name]-*.service` |
| Commands | `[prefix]-*` |
| Environment | `[PREFIX]_*` |
| Loopback ports | `[ports]` |
| Cookie names | `[unique names]` |
| Package names | `[unique names]` |
| Ownership marker | `/var/lib/[name]/installation.json` |
| Receipt | `/var/log/[name]/management-receipt.json` |
| Firewall rules | `[names or none]` |

## Authentication and secrets

For every credential, record its owner, creation path, storage mode,
rotation, recovery, session invalidation, and redaction rules.

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner or administrator password | [Role] | [Salted hash path/mode] | [Flow] |
| Session-signing key | [Service] | [Path/mode] | [Flow] |
| Provider credential | [Service] | [Path/mode] | [Flow] |
| Encryption or guardian key | [Role] | [Custody] | [Flow] |

Requirements:

- generate or accept fresh product-specific credentials;
- never read a sibling product's secret as a default;
- use a unique cookie name and session-signing key;
- preserve valid hashes and keys on reinstall unless rotation is requested;
- redact secret values from logs, receipts, diagnostics, and errors; and
- reject every sibling product's password, cookie, token, and reset flow.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| [Exact capability] | [Allow/deny/restrict] | [Who, if anyone] | [Event] | [Paths, arguments, rate] |

### Denied capabilities

- [A negative capability that is absent from the runtime.]
- [A request the policy must refuse.]
- [A path, destination, or data class that remains unreachable.]

Sensitive actions must pass through product-owned policy and audit code.
Prompt instructions are guidance, not enforcement. A product without a
host-administration purpose must use a closed root-owned helper with enumerated
operations for any narrowly privileged work. A product that requires general
root authority must justify it, use a dedicated identity and closed tool
surface, preserve explicit approval and audit, provide revocation, and disclose
that compromise is root-equivalent.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| [Data] | [Why needed] | [Role] | [Path/encryption] | [Duration] | [Flow] |

Document:

- data minimisation and whether raw transcripts are retained;
- third-party data and consent;
- encryption at rest and key custody;
- backup contents and recovery testing;
- provenance and integrity requirements;
- export formats and portability; and
- suspension, expiry, deletion, and legal-retention behaviour.

## Network and model providers

[List every listener, destination, protocol, and reason. State whether local
models are mandatory, whether cloud providers are optional, what each
provider receives, and how egress is restricted.]

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:[port]` | [Traffic] | [Open/closed] | [Authentication] |
| Outbound | [Destination or none] | [Data] | [Allowed/blocked] | [Policy] |

## Ubuntu Zombie management contract

Ubuntu Zombie is the root-level family manager. Define the product-owned,
root-only interface it may invoke without turning this product into a
Zombie component. The entry point, flags, request and response envelopes,
exit codes, ownership marker, receipt, health checks, plan digest, locks, and
audit correlation are fixed by
[`implementation.md`](implementation.md#lifecycle-entry-point). This section
defines product-specific inputs, approvals, checks, and retained inventory;
it must not fork the common protocol.

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | [Machine-readable interface] | [None/read-only] | [Event] |
| Install/dry-run | [Product installer] | [Approval] | [Event] |
| Verify/doctor/repair | [Lifecycle interface] | [Approval rules] | [Events] |
| Update/rollback | [Product updater] | [Approval rules] | [Events] |
| Suspend/uninstall | [Lifecycle interface] | [Approval/confirmation] | [Events] |

Specify:

- product-specific release-verification additions, if any;
- every accepted `inputs` key and whether it is a secret-file reference;
- which non-secret inventory fields Zombie may retain;
- how sensitive inputs reach the target without entering Zombie history,
  logs, receipts, or long-term state;
- matching correlation identifiers in manager and target audits;
- failure, cancellation, timeout, rollback, and partial-batch behaviour;
- proof that only the selected product changes; and
- why managing software does not grant Zombie a target-specific human,
  guardian, consent, evidence, or legal role.

Family membership and this interface do not themselves grant management
authority or increase installed authority. If this product is also a family
manager, define and test that role explicitly; otherwise its normal service
interface cannot request management of a sibling.

## Installation

The product owns its installer. Ubuntu Zombie may verify and invoke that
installer as the family manager, but must not reimplement it or register the
product as a Zombie component.

### Preflight

- [Supported operating systems, architectures, and resources.]
- [Collision checks for identities, paths, ports, units, and commands.]
- [Release, checksum, signature, provenance, and SBOM verification.]
- [Existing-install ownership and compatibility checks.]
- [Backup or rollback readiness.]

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| [Input] | [Prompt/default] | `[PRODUCT_INPUT]` | [Rules] |

`[PREFIX]_NONINTERACTIVE=1` and `--non-interactive` are equivalent.
Unattended mode must never prompt and must exit `64` before mutation when a
required input is missing. Secret inputs use `[PREFIX]_*_FILE`; raw secrets
must not enter arguments or environment values.

### Dry-run and mutation order

1. [Render the complete common response envelope and plan digest without
   filesystem writes, locks, downloads, or network access.]
2. [Create identities and protected directories.]
3. [Write credentials and configuration atomically.]
4. [Install root-owned executable code and confined services.]
5. [Create state, logs, rotation, receipt, and ownership markers.]
6. [Start services only after integrity checks pass.]
7. [Run health and boundary checks before marking success.]

### Idempotence

[For every created resource, state how a re-run recognises valid state,
repairs drift, preserves credentials/data, and refuses an unowned
collision.]

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | [Converge declared state] | Yes | [Health/receipt] |
| `verify` | [Read-only checks] | No | [Human/JSON result] |
| `doctor` | [Explain drift and recovery] | No | [Diagnosis] |
| `repair` | [Known-safe corrections] | Yes | [Reverification] |
| `update` | [Verify, back up, migrate, switch] | Yes | [Health/audit] |
| `rollback` or recovery | [Restore known-good state] | Yes | [Health/audit] |
| `suspend` or kill | [Stop useful operation] | Yes | [Lifecycle state] |
| `uninstall` | [Remove only owned resources] | Yes | [Removal report] |

Every row must define product-specific health checks and stable error codes.
The common operation names, JSON response fields, and exit statuses are not
open design choices.

## Update and migration design

Define:

1. supported source versions and compatibility checks;
2. state, credential, policy, and lifecycle preservation;
3. pre-migration backup or snapshot;
4. staged schema and policy validation;
5. atomic service switch and health gate;
6. failed-migration rollback or documented recovery;
7. release and migration audit records; and
8. proof that no non-target sibling file or process changes; and
9. conformance with the stable management plan/result contract Ubuntu Zombie
   invokes.

There is no shared release number, schedule, updater, or migration format.
Ubuntu Zombie may coordinate “update all agents” by invoking each verified
product updater serially, with per-product approval, health, audit, and
recovery. The batch is not one atomic migration.

## Co-installation

[List every supported sibling combination and any recommendation for a
dedicated machine.]

Prove:

- unique users, groups, paths, units, ports, commands, cookies, credentials,
  logs, receipts, and manifests;
- cross-password and cross-session rejection;
- service-account denial when reading sibling protected resources;
- independent reinstall, repair, update, suspension, and uninstall;
- stable sibling file hashes and service start times; and
- honest treatment of Ubuntu Zombie's root authority;
- successful Zombie-managed lifecycle operations against only this target;
  and
- denial of every unauthorised attempt by this service identity to invoke
  Zombie's management plane.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | [Path] | [Events] | [Rules] |
| Service journal | [Unit identifier] | [Events] | [Rules] |
| Health check | [Command/API] | [Checks] | [Rules] |
| Diagnostics | [Command] | [Bundle] | [Rules] |
| Receipt/manifest | [Path] | [Ownership/version] | [Rules] |
| Suspension/kill switch | [Command/UI] | [Effect] | [Authorisation] |

## Validation plan

### Product tests

- [ ] Interactive install on every supported platform.
- [ ] Unattended install and required-input exit `64`.
- [ ] Accurate dry-run and idempotent reinstall.
- [ ] Ownership, permissions, confinement, and secret redaction.
- [ ] Every allowed capability succeeds within bounds.
- [ ] A larger negative capability set fails and is audited.
- [ ] Malformed, missing, stale, and unowned state fails closed.
- [ ] Credential rotation and session invalidation.
- [ ] Update from every supported version.
- [ ] Failed migration, rollback, and recovery.
- [ ] Verify, doctor, repair, suspension, and uninstall.
- [ ] Direct and Ubuntu Zombie-managed lifecycle paths produce equivalent
      target results and matching audit evidence.
- [ ] Artifact, checksum, signature, provenance, and SBOM verification.

### Product-specific red team

- [Attack or bypass case and expected denial.]
- [Compromised model/provider case and protected boundary.]
- [Compromised service account case and protected boundary.]
- [Data/provenance manipulation case and expected detection.]
- [Update, rollback, and uninstaller ownership attack.]

### Co-installation matrix

- [ ] Product alone.
- [ ] Every supported two-product combination.
- [ ] Every supported three-product combination.
- [ ] All current family products together.
- [ ] Operate and remove each product while all siblings remain unchanged.
- [ ] Use Ubuntu Zombie to manage each selected target while every
      non-target sibling remains unchanged.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| [Threat] | [Impact] | [Control] | [Recovery] | [Evidence] |

Record residual risk honestly. If the product's purpose cannot tolerate a
same-host root administrator, require a dedicated machine rather than
claiming impossible isolation.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | [Decision] | [Reason] | [Test/link] |
| Policy and audit gate | [Decision] | [Reason] | [Test/link] |
| Root-capable account | [Keep or remove for the declared purpose] | [Reason] | [Boundary test] |
| Chat authentication | [Decision] | [Reason] | [Test/link] |
| Lifecycle/kill switch | [Decision] | [Reason] | [Test/link] |
| Update and recovery | [Decision] | [Reason] | [Test/link] |

**Measurable improvement:** [Name at least one improvement and the test or
metric that proves it.]

**Pinned source lesson set:** [Exact Ubuntu Zombie tag. A product is not
implementation-ready while this remains unselected.]

## Honest claims and out of scope

### Approved description

> [The exact short product description.]

### Prohibited claims

- [A safety, identity, legal, privacy, or capability claim not established
  by evidence.]

### Out of scope

- [Excluded feature or use.]
- [Excluded authority.]
- [Excluded integration or deployment.]

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| [Item] | [Authority, data, lifecycle, or user impact] | [Owner] | [Milestone] |

An item may remain open only when it is explicitly outside the fixed first
implementation slice. Any open decision about first-slice authority, data,
credentials, interfaces, defaults, dependencies, installation, or removal
keeps the definition in proposal status.

## Product-owned documentation

These documents live below the product's reserved source root in this
repository; no external repository is required.

- [ ] README and product vision.
- [ ] Architecture and data-flow diagrams.
- [ ] Threat model, security policy, and disclosure process.
- [ ] Privacy, consent, retention, export, and deletion model.
- [ ] Configuration and credential rotation.
- [ ] Installation, verification, diagnostics, repair, and removal.
- [ ] Updating, migration, rollback, backup, and recovery.
- [ ] Test strategy and red-team evidence.
- [ ] Release process, changelog, version, checksums, signatures,
      provenance, and SBOM.
- [ ] Platform support and troubleshooting.

## Release gate

A release is not complete until the product's lint, tests, package,
artifact verification, standalone VM lifecycle, negative security suite,
co-installation matrix, changelog, and version all pass. Any unproven
security or safety claim remains visibly labelled as planned.
