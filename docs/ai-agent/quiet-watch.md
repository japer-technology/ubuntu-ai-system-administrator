# Quiet Watch

> A private local host-health observer that explains a fixed, sanitised
> telemetry set and raises local alerts without diagnosing arbitrary logs or
> changing the machine.

Quiet Watch complements Ubuntu Zombie's on-demand administration with
continuous, read-only observation. It is not a second Systems Administrator,
an observability stack, endpoint security product, arbitrary log analyser, or
repair service.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `quiet-watch` |
| Human need | Notice and understand basic local-machine health changes without granting a conversational model host-administration authority |
| Intended users | The owner/operator of one supported Ubuntu machine |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | A closed root-owned collector may read fixed host counters and write sanitised Watch telemetry; the unprivileged service reads that telemetry and writes Watch-owned alerts, history, and logs |
| Default Linux identity | Non-login `watch` account and group |
| Default loopback port | `2222` |
| Install root | `/opt/quiet-watch` |
| Configuration root | `/etc/quiet-watch` |
| State root | `/var/lib/quiet-watch` |
| Log root | `/var/log/quiet-watch` |
| Environment prefix | `WATCH_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; telemetry history, alert details, and credentials stay out of manager inventory |
| Source root | `products/quiet-watch/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Quiet Watch samples a fixed set of CPU, memory, filesystem-capacity, thermal,
uptime, and systemd failure counters through a non-interactive root-owned
collector. Deterministic thresholds create alerts; a local model may explain a
sanitised snapshot. The conversational service cannot request new collection,
run a command, inspect arbitrary logs, or repair the host.

The first release supports one operator, five-minute sampling, a loopback UI,
local alerts, 30-day numeric history, and one credential-free loopback model.
It collects no command lines, environment values, filenames, network payloads,
user activity, journal messages, or arbitrary process data.

### It must

- publish the exact metric schema, source, units, sampling time, freshness, and
  missing-data state for every observation;
- keep threshold decisions deterministic and label model explanations as
  untrusted interpretation; and
- provide retention, threshold, acknowledgement, export, suspension, and
  deletion controls without offering repair.

### It must not

- execute operator or model-supplied commands, accept arbitrary paths, change
  services, kill processes, install packages, alter networking, or repair
  anything;
- claim that no alert means the host is healthy, secure, uncompromised, or
  backed up; or
- collect message content, keystrokes, screenshots, browser history,
  credentials, process environments, or sibling private state.

## Status and evidence

This document fixes a first product slice. No Watch source, collector,
installer, catalogue admission, security evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Collector, telemetry, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/quiet-watch/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Watch release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Operator | Review telemetry, set bounded thresholds, acknowledge alerts, export, suspend, and delete | Treat Watch as a security or availability guarantee |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain telemetry history, thresholds, alert details, or Watch secrets |
| Root collector | Read only enumerated kernel and systemd counters and atomically write the fixed telemetry file | Accept runtime input, execute arbitrary commands, mutate host state, or contact the model |
| `watch` service | Read sanitised telemetry and write Watch state | Invoke the collector, inspect the host, repair, or invoke lifecycle commands |
| Model endpoint | Explain one sanitised snapshot and fixed alert context | Select collection, set thresholds, run tools, or claim diagnosis |

### Authority ceiling

`quiet-watch-collect.service` runs a root-owned, root-only executable with no
arguments, stdin, environment-controlled paths, network, or model input. It
reads an enumerated set of `/proc` and `/sys` counters, configured filesystem
capacity through fixed mount descriptors, and systemd unit active/failed
states through a fixed machine interface. It writes only an atomic,
schema-validated telemetry snapshot below `/var/lib/quiet-watch/collector`.

The non-login `watch` service reads that snapshot, writes Watch history and
alerts, serves loopback HTTP, and calls one loopback model. It has no collector
execute permission, `sudo`, shell, subprocess, D-Bus control, general
filesystem, journal-content, package, service, network-control, or device
authority. Prompts and approvals cannot expand the collector schema.

### Authority inherited, retained, and removed

- Idempotent lifecycle, independent authentication, policy, audit, diagnostics,
  backup, and release verification are retained.
- General root and shell are replaced by one closed read-only collector.
- Host-wide file, log, process, package, service, account, device, and network
  inspection or control are removed.
- Ubuntu Zombie's repair and arbitrary diagnostic capabilities are removed.
- External notifications, security scanning, family management, and model-led
  collection are removed.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Fixed telemetry snapshot | Shows basic host resource state | Closed collector reads enumerated counters | MVP |
| Deterministic threshold alert | Flags configured capacity or health changes | Sanitised current and recent numeric data | MVP |
| Local explanation | Helps interpret a current alert | Sanitised snapshot and loopback model | MVP |
| History and export | Shows trends and preserves portable evidence | Watch state and export root | MVP |
| Alert acknowledgement | Records operator review without changing host | Watch state only | MVP |
| Repair and external notification | Acts on or sends an alert | Host or network authority | Out of scope |

### Primary workflow

1. The root-owned timer invokes the fixed collector with no conversational
   input.
2. The collector reads enumerated counters, validates ranges and freshness, and
   atomically replaces the sanitised snapshot.
3. The unprivileged service validates the schema, appends numeric history, and
   evaluates operator-set bounded thresholds deterministically.
4. On request, the model proposes a plain-language explanation from the
   sanitised snapshot; Watch labels it and offers no action tool.
5. The operator acknowledges, exports, or changes a bounded threshold, and
   Watch records a content-minimised audit event.

### Failure behaviour

Missing, stale, partial, out-of-range, or schema-invalid telemetry is
`unknown`, never healthy. Collector, storage, threshold, model, or audit
failure raises a local product-health alert without attempting repair. Model
outage leaves collection, deterministic alerts, history, export, and
acknowledgement available.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Fixed collector and timer | Root | Enumerated host counters and root-owned configuration | Atomic sanitised snapshot | No runtime arguments, model, or host mutation |
| Telemetry validator/store | `watch` | Collector snapshot | Validated numeric history | Read snapshot; write Watch state |
| Threshold engine | `watch` | Current/history values and bounded operator settings | Deterministic alert state | Model-independent |
| Loopback UI and session service | `watch` | Credentials, thresholds, acknowledgements | Authenticated views and controls | No host-control authority |
| Model bridge | `watch` | Sanitised snapshot and fixed schema | Untrusted explanation | Exact loopback endpoint only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Watch-owned resources only |

Collector code, schema, configuration, service units, credentials, and markers
are root-owned. The chat service has no capabilities, strict filesystem
protection, private devices, explicit paths, and loopback-only networking.

### Compromise boundaries

- A compromised `watch` service can disclose sanitised telemetry and corrupt
  Watch history, alerts, and explanations, but cannot invoke the collector or
  change the host.
- A compromised model sees one sanitised snapshot and can mislead, but cannot
  alter thresholds, collection, or host state.
- Compromise of the root collector executable is root-equivalent; signed
  release verification, root ownership, fixed inputs, and minimal code reduce
  but cannot eliminate that supply-chain risk.
- A stolen operator session permits views, threshold changes within bounds,
  acknowledgements, and exports until revocation, but no repair or lifecycle
  work.
- A failed update retains the previous verified collector, service, and
  compatible state backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `watch` |
| Install root | `/opt/quiet-watch` |
| Configuration | `/etc/quiet-watch` |
| State | `/var/lib/quiet-watch` |
| Collector state | `/var/lib/quiet-watch/collector` |
| Logs | `/var/log/quiet-watch` |
| Units | `quiet-watch-*.service`, `quiet-watch-*.timer` |
| Commands | `watch-*` |
| Environment | `WATCH_*` |
| Loopback ports | `2222` |
| Cookie names | `quiet_watch_session` |
| Package names | `quiet-watch` |
| Ownership marker | `/var/lib/quiet-watch/installation.json` |
| Receipt | `/var/log/quiet-watch/management-receipt.json` |
| Firewall rules | None |

Every resource is collision-checked and existing state is recognised only with
the common ownership marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Operator password | Loopback login | Watch-specific scrypt hash in protected state | Operator rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Watch-only key in `/etc/quiet-watch/secrets`, mode `0600` | Rotation revokes sessions |
| Collector credential | None | Systemd and filesystem identity form the boundary | No bearer secret exists |
| Model or notification credential | None | Never accepted in the first release | Unsupported |

Telemetry excludes credentials by schema. Raw secrets never enter model
context, arguments, ordinary environment values, logs, receipts, diagnostics,
or manager inventory. Sibling credentials are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Collect fixed telemetry | Scheduled | Root-owned timer | `telemetry.collected` | Exact schema and sources; no input |
| Evaluate threshold | Allowed | None | `alert.evaluated` | Deterministic bounded rules |
| Explain snapshot | Restricted | Authenticated operator | `alert.explained` | Sanitised current snapshot only |
| Change threshold | Restricted | Operator | `threshold.changed` | Published metric-specific ranges |
| Acknowledge/export/delete | Restricted | Operator confirmation | `alert.changed` | Watch state only |
| Product lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Arbitrary commands, paths, process details, journal content, service control,
  package operations, networking changes, repairs, and security response.
- Runtime changes to collector code, sources, schema, interval, or privilege
  from the model or `watch` service.
- External alerts, webhooks, telemetry upload, and sibling data collection.

Audits include event IDs, actor/session IDs, metric IDs, threshold versions,
freshness, decisions, result codes, and correlation IDs. They exclude raw host
identifiers, filenames, process names, user activity, credentials, and model
payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Current sanitised snapshot | Host-health view | Operator | Root-written schema-validated JSON | Replaced every sample | JSON export |
| Numeric metric history | Trends and threshold context | Operator | Mode `0600` SQLite | 30 days | CSV/JSON or deletion |
| Thresholds and acknowledgements | Operator control and review | Operator | Protected versioned SQLite | Installation lifetime | JSON export or reset |
| Model explanations | Optional human-readable context | Operator | Not retained by default | Request lifetime | Explicit opt-in export |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

The collector records only published numeric or enumerated fields. It performs
no telemetry upload, model training, or arbitrary log collection. Backups
exclude active sessions and current ephemeral snapshot but include thresholds,
acknowledgements, and selected history.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2222` | Authenticated telemetry UI | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback OpenAI-compatible endpoint | One sanitised snapshot and fixed alert context | Allowed | Exact URL and payload limits |
| Outbound | Telemetry, notifications, internet, or LAN | None | Blocked | Collector has no network; service endpoint allow-list |

The first release requires a credential-free loopback model. Dry-run and the
collector perform no network access. The model is optional for core
deterministic alerting after install.

## Ubuntu Zombie management contract

The source entry point is `products/quiet-watch/scripts/manage.sh`; the
installed command is `/usr/local/sbin/watch-manage`. It follows
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves collector and plan digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `operator_user`, `operator_password_file`,
`model_base_url`, `model`, `sample_interval_seconds`,
`history_retention_days`, `audit_retention_days`, `backup_destination`, and
`retain_state`. The sample interval is limited to `60..3600`; unknown keys fail
closed.

Zombie inventory may retain identifiers, version, authority summary, marker and
receipt digests, coarse product health, result, and correlation ID. It must not
retain metric values, threshold settings, alert details, history, host
identifiers, credentials, or model payloads. The `watch` service cannot invoke
management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64` with systemd.
- Reject namespace and ownership collisions before mutation.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor,
  collector source review, and pinned lesson set.
- Validate metric availability without claiming unsupported values, fixed
  filesystem descriptors, storage, loopback model, backup, and rollback.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Operator | Select existing local user | `WATCH_OPERATOR_USER` | Existing non-root account |
| Operator password | Generate or read protected file | `WATCH_OPERATOR_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `WATCH_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Model ID | Select from bounded probe | `WATCH_MODEL` | Non-empty; required unattended |
| Sample interval | Review default `300` | `WATCH_SAMPLE_INTERVAL_SECONDS` | Integer `60..3600` |
| History retention | Review default `30` | `WATCH_HISTORY_RETENTION_DAYS` | Integer `1..365` |
| Audit retention | Review default `90` | `WATCH_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`WATCH_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-lock, no-collection, no-network plan and digest.
2. Revalidate release, collector digest, plan, ownership, and collisions.
3. Create the `watch` identity and protected directories.
4. Write credentials, fixed collector schema, thresholds, and configuration
   atomically.
5. Install root-owned collector, unprivileged service, and systemd units.
6. Create telemetry state, history, logs, marker, and receipt.
7. Run one collector sample, validate redaction and thresholds, then start the
   timer and UI only after negative boundary checks pass.

### Idempotence

Valid marker, descriptor, collector digest, inventory, and receipt identify the
installation. Reinstall preserves credentials, thresholds, acknowledgements,
history, retention, and instance ID. It revalidates the collector exactly and
refuses unmarked users, paths, units, timers, commands, ports, or state.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared collector and service | Yes | Valid sample, alert fixtures, healthy UI, marker, receipt |
| `verify` | Check ownership, collector digest, schema, confinement, timer, and model | No | Human and JSON results |
| `doctor` | Explain stale data, unsupported metrics, model, timer, or state issues | No | Redacted diagnosis |
| `repair` | Restore exact Watch resources and restart only owned units | Yes | Reverification without host repair |
| `backup` | Archive Watch thresholds, history, and state, excluding sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, sample, and check | Yes | New version and audit |
| `rollback` | Restore supported collector, service, and compatible state | Yes | Prior sample and health checks |
| `suspend` | Stop collector timer and UI; revoke sessions | Yes | Inactive owned units |
| `resume` | Revalidate collector, schema, and policy before start | Yes | Fresh sample and healthy UI |
| `uninstall` | Remove only Watch resources; preserve or confirm state deletion | Yes | Removal report and host invariant checks |

## Update and migration design

Updates preserve credentials, thresholds, acknowledgements, compatible
history, retention, and instance ID; verify a backup; stage collector and
service code; validate schema migration; switch atomically; and require a fresh
sample plus negative privilege tests. Failure restores the prior verified
collector and service. No update may add a metric source or action capability
without a definition and security review.

## Co-installation

Watch supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, denial when `watch` reads sibling
roots or invokes management, independent lifecycle operations, stable
non-target hashes and service times, exact Zombie target selection, and no
collection of sibling ports, logs, content, or health details. Root-capable
products can still inspect Watch; dedicated machines provide stronger
isolation.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/quiet-watch/audit.jsonl` | Collection, threshold, acknowledgement, lifecycle events | No raw private host data or secrets |
| Service journal | `quiet-watch-chat.service` and collector unit | Startup, freshness, bounded errors | Metric IDs and result codes only |
| Health check | `watch-health` | Collector digest, freshness, schema, timer, model | Coarse public result |
| Diagnostics | `watch-diagnostics` | Versions, permissions, units, redacted checks | Excludes metric history and alert details |
| Receipt | Product log root | Version, collector digest, ownership, result | Root-only and secret-free |
| Suspension | `watch-manage suspend` | Stops collector and UI, revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Collector fixed inputs, schema, units, freshness, missing-data state,
      thresholds, acknowledgements, history, and export.
- [ ] Authentication, session revocation, model labels, and redaction.
- [ ] Arbitrary path/command/env/stdin, journal content, process details, host
      mutation, repair, sibling access, and external egress fail closed.
- [ ] Backup, restore, update, rollback, repair-of-product, suspension, and
      uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Attempt to pass paths, commands, environment values, model text, symlinks,
  mounts, and malicious counter values into the collector; all must fail or
  yield `unknown`.
- Make the model claim compromise, safety, a root cause, or required repair;
  output must remain labelled and actionless.
- Compromise `watch` and prove it cannot execute the collector, use D-Bus,
  inspect arbitrary `/proc`, read siblings, or mutate services.
- Replace collector code, schema, unit, or snapshot with an unowned object;
  verify and update must fail closed.
- Inject migration failure between collector and state schemas; rollback must
  restore a coherent pair.

### Co-installation matrix

- [ ] Watch alone and with each current family product.
- [ ] Watch with Ubuntu Zombie and Beep, proving it gains no root-peer access.
- [ ] Every supported three-product combination containing Watch.
- [ ] All current family products together.
- [ ] Operate, manage, and remove Watch without changing or inventorying a
      non-target sibling.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Collector input expansion | Root-level arbitrary read or execution | No inputs, fixed sources/schema, root ownership, digest verification | Suspend and reinstall verified code | Collector adversarial suite |
| Sensitive telemetry leakage | Host privacy disclosure | Field allow-list, no content/process/env collection, local model | Suspend, rotate, delete history | Schema and egress tests |
| False healthy or root-cause claim | Missed incident or unsafe response | Missing is unknown, deterministic alerts, labelled model output | Review raw supported counters with operator tools | Malicious-model fixtures |
| `watch` service compromise | Alert corruption or sanitised-data disclosure | Least privilege and collector separation | Suspend, restore, rotate sessions | Compromised-process VM |
| Malicious release | Root collector supply-chain compromise | Signature, provenance, SBOM, reviewed collector digest and plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes unsupported failures, misleading explanations, sensor
errors, and the inherent root-equivalent impact of malicious collector code.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Collector and history need safe convergence | Reinstall tests |
| Policy and audit gate | Keep with telemetry minimisation | Threshold and lifecycle changes need accountability | Redaction tests |
| Root-capable account | Replace with closed collector | Fixed host counters require narrow privileged reads, not administration | Collector boundary tests |
| Chat authentication | Replace | Watch requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Operator must stop collection immediately | Lifecycle tests |
| Update and recovery | Keep with collector/schema pairing | Privileged code and data must roll back together | Migration tests |

**Measurable improvement:** the unprivileged service must have zero executable
path to the collector and the collector must accept zero variable runtime
inputs; syscall, filesystem, and malicious-fixture tests must prove both
properties while every missing metric reports `unknown`.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Quiet Watch is a private local observer that turns a fixed sanitised host
> telemetry set into deterministic local alerts and labelled explanations.

### Prohibited claims

- That Watch proves a host is healthy, secure, uncompromised, available, or
  backed up.
- That an explanation establishes root cause or a required repair.
- That the root collector is harmless merely because it is read-only.
- That this definition represents implemented or released software.

### Out of scope

- Arbitrary logs, command lines, process environments, file content, user
  activity, network payloads, security scanning, and forensics.
- Host repair, service control, process termination, package operations,
  external notifications, webhooks, and fleet monitoring.
- Cloud models, remote users, shared observability stacks, and guarantees
  against same-host root.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Watch | Repository maintainers | First implementation change |
| Exact telemetry schema | Every extra field changes privacy and privilege risk | Product and security maintainers | First runtime change |
| Collector implementation review | Any flaw executes in a root context | Security reviewers | Implementation approval |
| Threshold defaults | Bad defaults create noise or false reassurance | Product reviewers | Release candidate |
| Disposable-VM compromise boundary | Collector/service separation needs host proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Collector architecture, data flow, and privilege threat model.
- [ ] Telemetry privacy, schema, retention, export, and deletion model.
- [ ] Metric, freshness, threshold, alert, and explanation schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Collector adversarial suite and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, independent
collector security review, syscall and no-input boundary evidence, standalone
VM lifecycle, negative privacy and privilege suites, co-installation evidence,
changelog, and version. Family admission also requires manager and contract
evidence. Unproven health, privacy, or security claims remain visibly planned.
