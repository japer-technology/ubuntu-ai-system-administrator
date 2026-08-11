# Household Ledger

> A private offline assistant that helps one household understand deliberately
> imported transaction records while keeping arithmetic deterministic and
> financial decisions with people.

Household Ledger complements the family with bounded personal-finance analysis.
It is not a bank client, accountant, tax adviser, investment service, payment
agent, or general document assistant.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `household-ledger` |
| Human need | Understand household spending and plan a budget without disclosing financial records to a remote service |
| Intended users | One adult owner and household members whose records they are authorised to process |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read supported CSV files in one import root and write only Ledger-owned classifications, plans, reports, and logs |
| Default Linux identity | Non-login `ledger` account and group |
| Default loopback port | `3890` |
| Install root | `/opt/household-ledger` |
| Configuration root | `/etc/household-ledger` |
| State root | `/var/lib/household-ledger` |
| Log root | `/var/log/household-ledger` |
| Environment prefix | `LEDGER_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; financial records and credentials stay out of manager inventory |
| Source root | `products/household-ledger/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Household Ledger imports owner-provided UTF-8 CSV transaction exports,
normalises them into an auditable local ledger, computes totals
deterministically, and uses a local model only to suggest classifications and
explain trends. An installed local product is appropriate because the records
are sensitive and filesystem, network, and calculation boundaries can be
tested independently of model instructions.

The first release supports one owner, one household, one currency per import,
manual CSV import, monthly budgets, and a credential-free loopback model. It
has no bank connection and cannot move money.

### It must

- preserve every imported amount, date, currency, source row, and correction
  with provenance;
- calculate balances and totals outside the model using fixed decimal rules;
  and
- provide review, correction, export, retention, suspension, and deletion
  controls before keeping financial history.

### It must not

- connect to banks, store banking credentials, initiate payments, trade,
  borrow, file taxes, or submit forms;
- present model classifications or forecasts as facts, guarantees, regulated
  advice, or professional accounting; or
- read home directories, browser profiles, email, sibling data, or files
  outside the fixed import root.

## Status and evidence

This is a product definition. No source, installer, catalogue admission,
security evidence, or release exists. Planned controls remain requirements.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Import, calculation, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/household-ledger/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Ledger release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Import authorised records, correct categories, set budgets, export, delete, and suspend | Treat a forecast or category as professional advice |
| Household contributor | View only the scopes the owner explicitly grants | Infer access from a relationship or shared machine account |
| Machine operator | Install, update, back up, recover, and uninstall | Treat root access as consent from every person in a transaction |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain transactions, budgets, reports, household identities, or secrets |
| `ledger` service | Read fixed imports and write Ledger state and reports | Contact banks, move money, inspect the host, or invoke lifecycle commands |
| Model endpoint | Suggest categories and explanations from minimised rows | Perform arithmetic, set policy, or create authoritative records |

### Authority ceiling

The service accepts authenticated loopback requests, reads supported regular
CSV files below `/srv/household-ledger/imports`, writes its protected state and
reports, and calls one loopback model endpoint. It has no `sudo`, shell,
subprocess, browser, bank protocol, payment API, package tool, device access,
internet route, or source-import write permission.

CSV files are at most 16 MiB and must contain declared date, description,
amount, and currency columns. Descriptor-relative traversal rejects links,
devices, mount changes, and paths outside the import root. Authentication,
prompts, or owner confirmation cannot add a financial capability.

### Authority inherited, retained, and removed

- Product-owned installation, authentication, policy, audit, lifecycle,
  diagnostics, and verified release practices are retained.
- General root, shell, host inspection, package, service, account, device, and
  network control are removed.
- Arbitrary workspace mutation is replaced by a read-only import root and
  Ledger-owned reports.
- Arithmetic is removed from model authority and implemented deterministically.
- Family management, autonomous action, and provider credentials are removed.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| CSV import | Creates an attributable local transaction record | Read fixed import root | MVP |
| Deterministic totals | Shows accurate sums by period and category | Decimal transaction fields | MVP |
| Suggested categories | Reduces manual classification work | Minimised descriptions and local model | MVP |
| Budget comparison | Compares owner-set plans with recorded spending | Ledger state only | MVP |
| Portable report | Supports owner review outside the product | Ledger-owned export root | MVP |
| Bank synchronisation | Automatic record collection | External credentials and network | Out of scope |

### Primary workflow

1. The owner authenticates with Ledger-only credentials.
2. Ledger validates a CSV, records its digest and immutable source-row
   provenance, and detects exact duplicate imports.
3. Deterministic code parses decimal amounts and computes totals.
4. The model proposes categories or explanations; the UI labels them as
   suggestions and requires owner confirmation before they affect reports.
5. Ledger exports a versioned report and records a content-minimised audit
   event.

### Failure behaviour

Ledger rejects malformed columns, ambiguous dates or decimal separators,
mixed undeclared currencies, duplicate source rows, invalid encodings, changed
imports, impossible arithmetic, stale sessions, and failed audits. It never
guesses a missing amount or exchange rate. A model outage leaves import,
totals, corrections, and export available without AI suggestions.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `ledger` | Credentials, budgets, corrections | Authenticated views and controls | No financial execution authority |
| Import validator | `ledger` | Supported CSV files | Canonical rows and provenance | Read-only fixed root |
| Calculation engine | `ledger` | Decimal canonical rows | Reproducible totals | Deterministic; model-independent |
| Model bridge | `ledger` | Minimised descriptions and summaries | Untrusted category suggestions | Exact loopback endpoint only |
| Report exporter | `ledger` | Confirmed ledger state | JSON and CSV reports | Ledger export root only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Ledger-owned resources only |

Root owns code, policy, credentials, units, and markers. The service runs with
an empty capability set, strict filesystem protection, private devices and
temporary storage, explicit paths, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose imported financial data and corrupt
  Ledger-owned state, but cannot alter source exports or contact a bank.
- A compromised model sees selected descriptions and summaries and can
  misclassify them, but cannot change canonical amounts or totals.
- A stolen session permits authorised views and exports until expiry or
  revocation, but no host or payment action.
- A failed update retains the previous verified version and a protected,
  schema-compatible backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `ledger`, `ledger-share` |
| Install root | `/opt/household-ledger` |
| Configuration | `/etc/household-ledger` |
| State | `/var/lib/household-ledger` |
| Import root | `/srv/household-ledger/imports` |
| Logs | `/var/log/household-ledger` |
| Units | `household-ledger-*.service` |
| Commands | `ledger-*` |
| Environment | `LEDGER_*` |
| Loopback ports | `3890` |
| Cookie names | `household_ledger_session` |
| Package names | `household-ledger` |
| Ownership marker | `/var/lib/household-ledger/installation.json` |
| Receipt | `/var/log/household-ledger/management-receipt.json` |
| Firewall rules | None |

Resources are collision-checked and never adopted without the common ownership
marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Ledger-specific scrypt hash in protected state | Owner rotation or root reset revokes all sessions |
| Contributor password | Optional scoped login | Independent salted hash and role record | Owner revocation invalidates contributor sessions |
| Session-signing key | UI service | Random Ledger-only key in `/etc/household-ledger/secrets`, mode `0600` | Rotation revokes all sessions |
| Bank or provider credential | None | Never accepted or stored | Unsupported |

Reinstall preserves valid Ledger credentials unless rotation is requested.
Raw secrets and complete transaction rows never enter arguments, environment
values, operational logs, receipts, diagnostics, or Zombie inventory. Sibling
credentials and reset flows are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Import CSV | Restricted | Authenticated owner | `import.accepted` | Fixed root, schema, size, and digest |
| Compute totals | Allowed | None after valid import | `calculation.completed` | Deterministic decimal operations |
| Suggest category | Restricted | Owner confirms use | `category.suggested` | Minimised row fields, loopback model |
| Edit budget/category | Restricted | Owner | `ledger.changed` | Ledger state only |
| Export report | Restricted | Owner | `report.exported` | Protected export root |
| Delete state | Restricted | Owner confirmation | `state.deleted` | Ledger-owned data only |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Banking, payment, trading, lending, tax filing, form submission, or external
  notification.
- Writes to source imports or paths outside Ledger state.
- Model control over amounts, arithmetic, confirmed categories, access, or
  retention.

Operational audit includes actor, event, source digest, row counts, decision,
result, and correlation ID. It excludes transaction descriptions, amounts,
budgets, identities, reports, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Source CSV files | Owner-provided evidence | Owner | Read-only import root; excluded from backup | Owner-controlled | Managed outside Ledger |
| Canonical transactions | Totals and history | Owner | Mode `0600` SQLite with row provenance | 365 days | Versioned CSV/JSON or deletion |
| Categories and budgets | Household analysis | Owner | Protected SQLite state | 365 days | Export, correction, deletion |
| Reports | Portable review | Owner | Protected export root | 90 days | CSV/JSON export or deletion |
| Operational audit | Security accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Third-party transaction data is processed only when the owner has authority to
do so. Ledger does not train models or send telemetry. Backups are encrypted by
operator-controlled storage and exclude source imports and active sessions.
Complete uninstall never deletes the import root contents.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:3890` | Authenticated UI traffic | Open after healthy install | Password, scoped session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | Minimised descriptions and aggregate context | Allowed | Exact loopback URL and payload bounds |
| Outbound | Banks, payment services, internet, or LAN | None | Blocked | Service network policy and absent clients |

The first release requires a credential-free loopback model. It performs no
exchange-rate lookup; each currency is reported separately unless the owner
imports explicit rates in a later reviewed design.

## Ubuntu Zombie management contract

The source entry point is `products/household-ledger/scripts/manage.sh`; the
installed command is `/usr/local/sbin/ledger-manage`. It follows
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common lifecycle response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common lifecycle response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common lifecycle response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `owner_user`, `owner_password_file`, `model_base_url`,
`model`, `transaction_retention_days`, `audit_retention_days`,
`backup_destination`, and `retain_state`. Unknown keys fail closed.

Zombie inventory may retain product and instance IDs, version, authority
summary, marker and receipt digests, coarse health, result, and correlation ID.
It must not retain household identities, import names, transaction data,
budgets, reports, credentials, sessions, or model payloads. The service cannot
call either management plane.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject all namespace and ownership collisions before mutation.
- Verify release artefact, checksums, signature, provenance, SBOM, descriptor,
  and pinned lesson set.
- Validate owner, storage, import-root boundary, loopback model, backup, and
  rollback readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select existing local user | `LEDGER_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `LEDGER_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `LEDGER_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `LEDGER_MODEL` | Non-empty; required unattended |
| Transaction retention | Review default `365` | `LEDGER_TRANSACTION_RETENTION_DAYS` | Integer `30..3650` |
| Audit retention | Review default `90` | `LEDGER_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`LEDGER_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Raw secrets use only
protected file references.

### Dry-run and mutation order

1. Render a complete no-write, no-network plan and digest.
2. Revalidate release, plan, ownership, and collisions under the product lock.
3. Create identities and protected directories.
4. Write credentials, calculation rules, and configuration atomically.
5. Install root-owned code and confined services.
6. Create the read-only import root, state, logs, marker, and receipt.
7. Start only after arithmetic, privacy, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, canonical rows, corrections, budgets,
retention, and instance ID unless explicitly reset. It never recategorises
confirmed rows silently and refuses unmarked resources.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, calculation fixtures, marker, receipt |
| `verify` | Check ownership, confinement, schemas, arithmetic, and boundaries | No | Human and JSON results |
| `doctor` | Explain import, model, schema, or retention issues | No | Redacted diagnosis |
| `repair` | Restore known-safe code, configuration, and derived indexes | Yes | Reverification without source change |
| `backup` | Archive and verify Ledger state, excluding source and sessions | Yes | Manifest and digest |
| `update` | Verify, back up, stage, migrate, switch, and health-check | Yes | New version and audit |
| `rollback` | Restore a supported version and compatible state | Yes | Prior health checks |
| `suspend` | Stop access and revoke sessions | Yes | Inactive service and state |
| `resume` | Revalidate privacy and integrity before start | Yes | Healthy service |
| `uninstall` | Remove only owned resources; preserve or confirm state deletion | Yes | Removal report; imports unchanged |

## Update and migration design

An update preserves credentials, provenance, confirmed corrections, budgets,
retention, and instance ID; verifies a backup; migrates a staged copy; reruns
decimal fixtures; switches atomically; and restores the prior version on
failure. Audit omits financial content. Tests prove source imports and sibling
resources remain unchanged.

## Co-installation

Ledger supports installation alone or with every current family product.
Tests cover unique resources, cross-login rejection, service denial against
sibling roots, import immutability, independent lifecycle operations, stable
non-target hashes and start times, and exact Zombie targeting. A dedicated
machine is recommended when records must be hidden from same-host root.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/household-ledger/audit.jsonl` | Import, policy, export, lifecycle events | No transaction content or secrets |
| Service journal | `household-ledger-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `ledger-health` | Service, model, schema, arithmetic fixtures | Coarse public result |
| Diagnostics | `ledger-diagnostics` | Versions, permissions, units, redacted checks | Excludes financial data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `ledger-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, scoped roles, session revocation, and redaction.
- [ ] CSV schemas, exact decimal arithmetic, duplicate detection, provenance,
      corrections, categories, budgets, and exports.
- [ ] Malformed input, mixed currencies, prompt injection, path escape,
      source write, bank access, sibling access, and external egress fail.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Put instructions and formula-injection payloads in every CSV field; they must
  remain inert and exports must neutralise spreadsheet execution.
- Make the model alter amounts, invent transactions, or claim guaranteed
  savings; deterministic state and labels must reject it.
- Race, replace, link, or mutate imports during parsing; no mixed source may be
  committed.
- Compromise `ledger` and prove bank, internet, source-write, sibling, and
  management access remain unavailable.
- Attack migrations and uninstall with unowned resources and corrupted state;
  mutation must remain target-scoped and recoverable.

### Co-installation matrix

- [ ] Ledger alone and with each current family product.
- [ ] Every supported three-product combination containing Ledger.
- [ ] All current family products together.
- [ ] Operate and remove Ledger while imports and siblings remain unchanged.
- [ ] Manage Ledger through Ubuntu Zombie without changing a non-target.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| CSV formula or prompt injection | Code execution after export or model manipulation | Treat fields as data, escape exports, absent tools | Reject or regenerate safe export | Adversarial CSV corpus |
| Arithmetic/model confusion | Incorrect household decisions | Decimal engine owns amounts and totals; model output labelled | Recompute and correct | Deterministic fixtures |
| Financial-data disclosure | Privacy harm | Local endpoint, minimised context, protected paths and logs | Suspend, rotate, delete retained data | Egress and redaction suite |
| Service compromise | Record disclosure or state corruption | Least privilege, read-only imports, root-owned code | Suspend, restore backup, rotate sessions | Compromised-process VM |
| Malicious release | Root-level compromise | Verified signed artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes incomplete imports, misleading classifications, and
poor human decisions. The product does not replace professional advice.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Financial state needs safe convergence | Reinstall tests |
| Policy and audit gate | Keep with data minimisation | Import, export, and deletion need accountability | Redaction tests |
| Root-capable account | Remove | Analysis needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Ledger requires independent roles and credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Immediate privacy control is necessary | Lifecycle tests |
| Update and recovery | Keep with calculation fixtures | Migrations must preserve exact values | Migration tests |

**Measurable improvement:** canonical transaction totals must match fixed
decimal reference fixtures exactly across import, export, backup, update, and
rollback, regardless of any model response.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Household Ledger is a private offline assistant for reviewing deliberately
> imported transaction CSVs with deterministic totals and human-confirmed
> classifications.

### Prohibited claims

- That Ledger is a bank, accountant, tax adviser, fiduciary, credit service, or
  regulated financial product.
- That a category, budget, or forecast is complete, correct, or guaranteed.
- That local operation hides data from the machine's root administrator.
- That this definition represents implemented or released software.

### Out of scope

- Bank connectivity, credentials, payments, trading, tax filing, lending,
  credit scoring, and external notifications.
- Cloud models, remote users, multi-tenant accounting, payroll, and business
  books.
- Automatic exchange rates, document OCR, email scraping, and legal advice.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Ledger | Repository maintainers | First implementation change |
| Canonical CSV profile | Bank exports vary and ambiguity can change values | Product maintainers | First runtime change |
| Financial and privacy review | Sensitive data and advice boundaries require scrutiny | Reviewers | Implementation approval |
| Spreadsheet-safe export | Formula injection can survive into another application | Security reviewers | Release candidate |
| Disposable-VM boundary | Permissions and egress controls need host proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, data flow, and threat model.
- [ ] Privacy, household authority, retention, export, and deletion model.
- [ ] Canonical import, provenance, calculation, budget, and report schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Deterministic fixtures, red-team strategy, and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, exact
calculation fixtures, standalone VM lifecycle, negative security and privacy
suites, co-installation evidence, changelog, and version. Family admission also
requires manager and contract evidence. Unproven financial, privacy, or
security claims remain visibly planned.
