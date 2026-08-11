# Beep

> A private, root-capable AI Systems Administrator that fully duplicates the
> Ubuntu Zombie product under an independent Beep identity, namespace,
> lifecycle, and release.

Beep is a deliberately complete functional duplication of
[Ubuntu Zombie](ubuntu-zombie.md). It serves the same human need, retains the
same maximum authority, and includes the same chat, provider, tool, policy,
approval, audit, lifecycle, reactivation, optional-software, and family-manager
scope. It is not a persona, alias, configuration profile, component, standby
process, or shared installation of Ubuntu Zombie.

“Full duplication” means product-level behavioural parity. Beep must still be
built, installed, authenticated, updated, audited, suspended, and removed as an
independent product. It copies an audited Ubuntu Zombie lesson set into
`products/beep/`, renames every installed resource before first use, and never
imports or operates from Ubuntu Zombie's live runtime or data.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Standalone implementation, tests, package, and release workflow present; external security, VM, co-installation, published-release, and family-admission evidence remain open |
| Product ID | `beep` |
| Human need | Operate and repair a complex personal Ubuntu machine without requiring the owner to translate every problem into administration commands |
| Intended users | The owner/operator and authorised local users of one machine |
| Operator | The human who owns the machine, provider account, Beep credentials, policy, and lifecycle controls |
| Maximum authority | Root through the dedicated Beep account, including approved management of other local agents |
| Default Linux identity | Password-disabled dedicated `beep` account and group |
| Default loopback port | `58989` |
| Install root | `/opt/beep` |
| Configuration root | `/etc/beep` |
| State root | `/var/lib/beep` |
| Log root | `/var/log/beep` |
| Environment prefix | `BEEP_*` |
| Ubuntu Zombie management | Fixed root-only Beep lifecycle interface; Beep remains an independent root-capable peer |
| Source root | `products/beep/` |
| Authoritative repository | [`japer-technology/ubuntu-zombie`](https://github.com/japer-technology/ubuntu-zombie) |

## Product promise

Beep installs an AI Systems Administrator beside existing desktop users. An
authenticated human can ask for work in plain language, inspect the proposal,
approve sensitive actions, receive the result, and review an audit record.
Beep provides the complete Ubuntu Zombie product behaviour under Beep-owned
resources so the two products can be installed and evaluated independently.

The operator remains the principal. They can rotate provider and chat
credentials, edit policy, reject work, stop the service, kill the lifecycle,
or uninstall Beep. Root capability is intentional and disclosed: compromise
of Beep is equivalent to compromise of the host.

### It must

- provide functional parity with the pinned Ubuntu Zombie lesson set,
  including local chat, supported model providers, closed administration tools,
  policy classification, approvals, audit, Time to Live, reactivation,
  diagnostics, lifecycle operations, and family management;
- own unique identities, credentials, paths, units, commands, ports, cookies,
  state, logs, receipts, inventories, packages, and releases; and
- keep every privileged action behind Beep-owned policy, approval, audit,
  revocation, and operator-control paths.

### It must not

- share Ubuntu Zombie code at runtime, credentials, sessions, history, policy,
  state, logs, inventory, receipts, or ownership markers;
- claim that a duplicate root-capable product creates redundancy, containment,
  or isolation from Ubuntu Zombie on the same host; or
- use its name, prompt, password, or family-manager role to act without policy
  or to acquire human, consent, guardian, identity, or legal authority.

## Status and evidence

This document fixes Beep's intended parity and independent boundary.
Standalone source, lifecycle, runtime, package, product documentation, source
tests, guarded VM harness, and independent release workflow now live below
[`products/beep/`](../../products/beep/). The production catalogue remains
empty, and no supported-VM, co-installation, external security review, or
published-release verification result is claimed here.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Full-parity scope and contracts in this document |
| Configuration and data contracts fixed | Passed | Namespace, input, data, and lifecycle sections below |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Implemented; host evidence open | `products/beep/payload/agent/beep/management.py`, source suites, guarded VM harness |
| Security boundary tested | Source suite passed; review and host evidence open | `products/beep/tests/`, product threat model |
| Update and rollback tested | Source failure coverage passed; VM matrix open | Automatic recovery tests and guarded lifecycle harness |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Root-peer and full-family matrix evidence |
| Release verification complete | Open | Independent Beep release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Operator | Install, configure, approve, suspend, kill, update, recover, and remove Beep | Treat model output or a chat login as authority independent of host ownership |
| Authorised local user | Authenticate, converse, inspect status, and request work allowed by operator policy | Bypass approval, impersonate the operator, or gain authority through a prompt |
| `beep` service identity | Use the complete policy-mediated Systems Administrator and family-manager capability set | Execute a sensitive action outside Beep policy and audit |
| Ubuntu Zombie manager | Invoke Beep's verified lifecycle interface under operator approval | Reuse Beep secrets, retain private content, or treat Beep as a component |
| Managed target product | Validate and execute its own lifecycle request | Select another target, trust Beep as its policy authority, or return secrets |
| Model provider | Propose answers and closed tool calls from disclosed context | Receive product credentials or directly invoke host or management operations |

The operator and an authorised local user may be the same person. Browser
authentication authorises use of Beep; it is not a Linux root credential and
does not change the installed capability ceiling.

### Authority ceiling

The `beep` account has passwordless `sudo` and a general command runner because
Beep's declared purpose is full host administration. Subject to Beep policy,
approval, and audit, it may inspect and change host files, processes, packages,
services, accounts, interfaces, firewall state, devices, and product-owned
lifecycle resources. It may use the configured model provider, perform bounded
public web reads, and invoke verified lifecycle interfaces for exact
catalogue-selected agents.

The chat listener is loopback-only by default. Outbound access is limited by
the host and Beep policy rather than by a claim of process isolation. The
root-capable chat service cannot use `NoNewPrivileges=true` or a filesystem
sandbox that would prevent approved administration. A prompt, persona,
password, ordinary approval, or sibling request cannot raise this already
root-equivalent ceiling or bypass its gates.

### Authority inherited, retained, and removed

- General passwordless `sudo` is retained because complete host
  administration is Beep's purpose.
- The general shell and command runner are retained behind schema validation,
  classification, approval, budgets, bounded output, and audit.
- Host-wide reads are retained, while automatic secret paths and process
  environments remain excluded from ordinary filesystem tools.
- Package, service, account, device, firewall, interface, and network control
  are retained and classified according to impact.
- The Time to Live, reactivation, optional-software operations, and
  family-manager capability are retained under independent Beep controls.
- Ubuntu Zombie credentials, state, approvals, and live runtime are removed
  from the inheritance boundary; Beep creates its own equivalents.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Authenticated local chat | Plain-language machine operation with visible progress | Loopback listener, Beep session and conversation state | MVP |
| Cloud and local model providers | Operator-selected reasoning backend | Product-owned provider settings and disclosed turn context | MVP |
| Closed Systems Administrator tools | Diagnose and operate the complete host | Root-capable runner behind exact tool schemas | MVP |
| Policy and approval | Human control over elevated and destructive work | Product policy, classifications, approval state | MVP |
| Audit and diagnostics | Explain what was requested, allowed, and changed | Redacted local events, receipts, health data | MVP |
| Time to Live and reactivation | Bounded operation and one controlled future continuation | Lifecycle state, timer state, fresh turn checks | MVP |
| Optional software operations | Match the pinned Ubuntu Zombie optional-software surface | Separately declared component or product lifecycle contracts | MVP |
| Family management | Discover and manage exact verified local agents | Root, catalogue, target plans, target lifecycle interfaces | MVP |
| Independent update and recovery | Maintain Beep without sharing Ubuntu Zombie state | Verified Beep release, backup, migration, rollback | MVP |

Parity is measured against the exact pinned source lesson set, not against an
unbounded moving branch. A later Ubuntu Zombie feature enters Beep only through
an explicit Beep review, namespace analysis, implementation, and release.

### Primary workflow

1. A local user authenticates to `127.0.0.1:58989` with Beep-only credentials.
2. Beep validates lifecycle and turn state, reconstructs bounded conversation
   context, and sends the request to the configured provider.
3. Proposed tool calls enter Beep's closed registry and are schema-validated,
   classified, budgeted, and checked against current policy.
4. Elevated or destructive work waits for the required Beep approval or
   confirmation; accepted calls execute through the Beep runner.
5. Results return to the model and user with bounded output, while Beep writes
   independent history and secret-redacted audit events.
6. Family work additionally fixes one catalogue product ID, verifies the
   target plan digest, and correlates the Beep and target audit outcomes.

### Failure behaviour

Beep fails closed on invalid authentication, dead or expired lifecycle state,
unknown tools, malformed arguments, missing policy, ambiguous classification,
expired approval, exceeded budgets, mismatched target or operation, stale plan
digest, unverified release, invalid ownership marker, unsafe path, audit
failure, or response-envelope mismatch.

The user receives a bounded error and recovery direction without credentials
or private output. A provider outage leaves local lifecycle and diagnostic
controls available but performs no model-directed work. A failed target
operation does not advance Beep inventory or another target. If a privileged
action may have partially completed, Beep records that state and requires
verification or recovery rather than claiming success.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback chat and session service | `beep` | Credentials, prompts, commands, approvals | Authenticated UI, events, answers | Root-capable through policy-mediated runner; loopback listener |
| Provider bridge | `beep` | Turn context, model selection, tool schemas | Untrusted text and tool proposals | Exact configured provider routes; no direct host authority |
| Tool registry and policy gate | `beep` | Proposed name and validated arguments | Decision, class, approval requirement | Closed registry and fail-closed policy |
| Command and capability runner | `beep` with approved `sudo` | Accepted exact tool call | Bounded result | Full host impact within selected operation |
| History, lifecycle, and audit services | `beep` or root as required | Turn, decision, result, timer, lifecycle events | Local state and redacted records | Beep-owned paths only; audit must precede success |
| Beep lifecycle manager | Root, direct or through Ubuntu Zombie | Verified Beep request and release | Plan, result, marker, receipt | Beep-owned resources only |
| Beep family manager | `beep` with approved `sudo` | Catalogue target, plan, secret-file references | Target response and secret-free inventory | Exact verified target entry point; no target-private authority |

Provider output, web content, command output, target metadata, and lifecycle
responses are untrusted until their respective validators accept them. The
provider cannot invoke `sudo`, select an arbitrary binary, alter policy, or
write an audit success record directly.

### Compromise boundaries

- If the chat service or `beep` account is compromised, the impact is
  root-equivalent, including possible compromise of every same-host product.
  Policy, audit, TTL, and service controls reduce exposure but are not a kernel
  security boundary against that account.
- If the model or provider is compromised, it can produce malicious proposals
  and observe disclosed context, but schemas, classifications, approval,
  budgets, target selection, and audit must still execute outside the model.
- If a user session is stolen, it permits ordinary authenticated requests
  until its 12-hour expiry or revocation; elevated work still requires current
  policy approval, and password rotation, kill, suspension, or uninstall
  invalidates every session.
- If an update fails, the previous verified Beep code, compatible state backup,
  credentials, policy, and recovery metadata remain available until rollback
  or operator-directed recovery succeeds.

## Product-owned namespace

Every value is checked against the host before mutation. The installer refuses
to adopt an existing resource without the ownership marker and receipt formats
in [`implementation.md`](implementation.md#ownership-marker-and-receipt).

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `beep` |
| Install root | `/opt/beep` |
| Configuration | `/etc/beep` |
| State | `/var/lib/beep` |
| Runtime state | `/var/lib/beep/runtime` |
| Family inventory | `/var/lib/beep/agents/inventory.json` |
| Logs | `/var/log/beep` and `/var/log/beep-install.log` |
| Units | `beep-*.service` and `beep-*.timer` |
| Commands | `beep-*` |
| Environment | `BEEP_*` |
| Loopback ports | `58989` |
| Cookie names | `beep_session` |
| Package names | `beep` |
| Ownership marker | `/var/lib/beep/installation.json` |
| Receipt | `/var/log/beep/management-receipt.json` |
| Firewall rules | None for the baseline loopback service |

The core units include `beep-chat.service`, `beep-health.service`, and
`beep-health.timer`. The family CLI is `/opt/beep/bin/beep-agents`, and the
installed target lifecycle entry point is `/usr/local/sbin/beep-manage`.
Optional software must receive additional Beep-owned, collision-checked
resources or use a separately owned product lifecycle interface. It must not
adopt Ubuntu Zombie's Forgejo, runner, Llama, component, or family metadata as
Beep-owned state.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Beep chat password | Local users | Product-specific salted hash in root-provisioned mode `0600` configuration | Operator rotation or reset revokes every session |
| Session-signing key | Chat service | Random Beep-only key in `/etc/beep/secrets`, mode `0600` | Rotation revokes every session; valid reinstall preserves it |
| Provider credential | Provider bridge | Provider-specific root-written file below `/etc/beep/secrets`, readable by `beep` | Replace protected file, restart service, and verify redaction |
| Managed-target secret reference | Target lifecycle only | Root-owned mode `0600` file outside model, history, inventory, and arguments | Target owns validation, use, rotation, and deletion |

Initial install generates a unique chat password and signing key unless the
operator supplies a protected password file. Beep never accepts Ubuntu
Zombie's default password, password hash, session key, provider file, cookie,
token, reset flow, or active session.

Raw secrets do not enter command arguments, ordinary environment values,
plans, logs, receipts, diagnostics, inventories, prompts, or provider context.
Reinstall preserves valid Beep hashes and keys unless rotation is requested.
Suspension, lifecycle death, password rotation, and complete uninstall revoke
active sessions. Provider errors and tool output pass through the shared
redaction vocabulary copied into Beep's independent implementation.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| `shell.run` | Classify | Policy-dependent; elevated and destructive work requires operator action | `tool.shell` | Argument array or reviewed shell text, time, output, and turn budgets |
| `fs.read`, `fs.list`, `fs.write` | Restrict | Writes follow path and impact class | `tool.fs` | Canonical paths, size limits, secret exclusions |
| `pkg.query`, `pkg.install` | Query allowed; install gated | Operator for mutation | `tool.pkg` | Debian packages and configured repositories |
| `svc.status`, `svc.control` | Status allowed; control gated | Operator for mutation | `tool.service` | Exact units and action allow-list |
| `net.status` and network changes | Status allowed; changes gated | Operator; destructive confirmation where applicable | `tool.network` | Declared inspection and host-network operations |
| `web.fetch` | Restricted | Policy for requested destination | `tool.web` | Public HTTP/S, no credentials, private addresses, request body, or unbounded response |
| `skill.list`, `skill.load` | Allowed | None | `tool.skill` | Root-owned built-ins and operator-owned Beep overlay |
| `timer.reactivation` | Restricted | Current Beep timer policy | `timer.reactivation` | One timer, configured delay range, remaining TTL, fresh turn authority |
| `agent.list`, `agent.status` | Read-only | None after authentication | `agent.read` | Validated Beep catalogue and inventory only |
| `agent.plan`, `agent.manage` | Plan read-only; mutation gated | Exact plan approval; destructive confirmation where required | `agent.manage` | One exact product, operation, correlation ID, digest, timeout, and response |

Beep uses the same policy classes as the pinned Ubuntu Zombie lesson set:
`read_only`, `chat_schedule`, `user_change`, `system_change`,
`network_change`, and `destructive`. Unknown commands and tools fail into the
most restrictive applicable class. Policy is read from
`/etc/beep/policy.yaml` for every request.

### Denied capabilities

- Direct provider, prompt, skill, web-content, command-output, or target control
  over the runner, approval store, policy, audit, or lifecycle state.
- Automatic reads of `/etc/beep/secrets`, sibling secret roots, process
  environments, private keys, browser credential stores, or raw managed-target
  secret files.
- Unapproved elevated or destructive work, stale approvals, approval reuse
  across turns, and authority carried into a reactivation.
- Arbitrary family target names, paths, URLs, commands, environment maps,
  catalogue additions, response fields, or target-selected sibling work.
- Claims that a denied operation is safe merely because Ubuntu Zombie or Beep
  could perform it as root outside the product.

Every proposed and completed sensitive action passes through Beep-owned policy
and audit code. Audit records include actor/session identifiers, correlation
IDs, classifications, approvals, bounded request metadata, outcomes, and
recovery state while redacting recognised credentials and private payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Conversation history | Context and operator review | Operator | Mode `0600` SQLite below `/var/lib/beep/runtime` | Until operator deletion, lifecycle removal, or configured policy | Authenticated export and explicit deletion |
| Policy and configuration | Define Beep behaviour | Operator | Root-owned `/etc/beep`; secrets separately restricted | Installation lifetime | Root-controlled backup, restore, and removal |
| Lifecycle and timer state | TTL, death, reactivation, and recovery | Operator | Atomic files and SQLite below Beep state | Installation lifetime; death tombstone survives reinstall | Included in protected backup; removed only by complete uninstall |
| Audit events | Accountability and incident review | Operator | Restricted JSON Lines below `/var/log/beep` with rotation | Rotation policy; lifecycle records retained as documented | Redacted diagnostics and operator archive |
| Family inventory | Show managed product health and outcomes | Operator | Atomic schema-validated file below `/var/lib/beep/agents` | Until target removal plus documented tombstone period | Secret-free JSON export or removal |
| Provider payloads | Complete one model turn | Operator and disclosed provider | In memory and conversation state as configured | Provider terms plus Beep history policy | Provider controls and local history deletion |
| Diagnostics and receipts | Verify and support the installation | Operator | Root-restricted, secret-redacted files | Receipt for installation lifetime; diagnostics until operator deletion | Portable support bundle or explicit deletion |

Beep minimises context before provider calls but, like Ubuntu Zombie, can send
prompts, history, selected host data, file content, command output, and target
status to a configured cloud provider when needed for a turn. The UI and
documentation disclose that boundary before use. Local providers reduce cloud
disclosure but do not reduce Beep's host authority.

Backups include Beep configuration, secrets, policy, history, lifecycle,
inventory, and audit state selected by the operator. They never include a
sibling product's data merely because Beep can read it as root. Restore checks
ownership, modes, schema, version, and integrity before service start. Complete
uninstall requires explicit confirmation before deleting retained Beep state.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:58989` | Authenticated chat, events, approvals, and controls | Open after healthy install | Beep password, signed session, CSRF protection |
| Outbound | Operator-configured supported cloud provider | Prompts, selected context, tool schemas, and results | Allowed only when configured | Exact provider adapter, TLS, policy, redaction |
| Outbound | Operator-configured loopback or bounded LAN model | Same model-turn data | Allowed only when configured | Explicit discovery/selection and endpoint validation |
| Outbound | Public HTTP/S for `web.fetch` | Requested URL and bounded response | Policy-restricted | Address checks on every redirect, no private targets or credentials |
| Outbound | Package, release, and managed-target sources | Package metadata or verified artifacts | Gated | Operator approval, HTTPS, checksum, signature, provenance, and SBOM |
| Inbound | Any non-loopback chat destination | None | Closed | No baseline listener or firewall opening |

Beep duplicates the pinned Ubuntu Zombie provider set: OpenAI, Anthropic,
Google Gemini, xAI, Mistral, Groq, OpenRouter, and compatible local endpoints
through its own pinned bridge. Provider credentials, model selection, endpoint
allow-lists, and discovery state are Beep-owned. No provider configuration is
read from Ubuntu Zombie by default.

## Ubuntu Zombie management contract

Beep is a managed product even though it is an equally root-capable
operating-system peer and family manager. Its source lifecycle entry point is
`products/beep/scripts/manage.sh`; installation places the product-owned
command at `/usr/local/sbin/beep-manage`. Ubuntu Zombie may invoke only this
verified interface using the fixed request, response, exit-code, marker,
receipt, plan-digest, lock, health, and audit-correlation contracts in
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Validated descriptor and common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | `beep-manage install` plan/result | Operator approves exact digest; execution requires `--yes` | `lifecycle.install` |
| Verify/doctor/repair | Common lifecycle response | Repair requires approved plan | Operation-named lifecycle event |
| Backup/update/rollback | Common lifecycle response | Operator approves destination or version and digest | Operation-named lifecycle event |
| Suspend/resume/kill | Common lifecycle response | Operator approval; kill requires destructive confirmation | Operation-named lifecycle event |
| Uninstall | Common lifecycle response | Operator approval; state deletion requires destructive confirmation | `lifecycle.uninstall` |

Accepted product-specific `inputs` keys are `agent_user`, `chat_port`,
`chat_password_file`, `provider`, `provider_credential_file`, `model`,
`model_base_url`, `ttl_days`, `backup_destination`, and `retain_state` where
the common request does not already carry the value. Unknown keys fail closed.
Only fields ending in `_file` may identify secret files, and every such file is
validated as a root-owned, non-symlink regular file with mode `0600`.

Ubuntu Zombie inventory may retain Beep's product and instance IDs, version,
descriptor and marker digests, authority summary, lifecycle and coarse health
state, last correlation ID, operation and result, and receipt path and digest.
It must not retain Beep credentials, provider details, prompts, history,
command output, approvals, policy, timer prompts, target inventory, target
private data, or audit records.

Both managers use the same correlation ID in independent audits. Cancellation,
timeout, stale plans, failed health, partial mutation, and rollback return the
common recovery envelope. Tests compare non-target paths and service start
times around every operation. Managing Beep does not grant Ubuntu Zombie
control of Beep's human approvals or permission to reuse Beep as an alternate
execution path.

### Beep's duplicated family-manager role

Beep also duplicates Ubuntu Zombie's family-management behaviour through
`/opt/beep/bin/beep-agents`, a Beep-owned catalogue, closed
`agent.list`, `agent.status`, `agent.plan`, and `agent.manage` tools, and the
secret-free `/var/lib/beep/agents/inventory.json`.

The manager accepts only digest-pinned product IDs and releases admitted to its
installed catalogue. It invokes one exact product-owned lifecycle entry point
with an argument array, bounded timeout, matching operation and correlation ID,
approved plan digest, validated result, and target receipt. A target password,
provider key, guardian key, vault key, consent decision, or other private input
is supplied only through a protected target-owned file reference outside model
and inventory state.

Beep and Ubuntu Zombie do not share catalogues, inventories, approvals, audit
records, locks, or manager credentials. Target-owned locks serialise concurrent
requests from either manager. Beep never manages itself, invokes Ubuntu
Zombie's manager plane, or treats Ubuntu Zombie as a target without a separately
reviewed product-owned lifecycle contract. Its manager role grants no target
access to Beep and no human, guardian, consent, evidence, identity, or legal
role to Beep.

## Installation

The Beep product owns its installer. Ubuntu Zombie may verify and invoke that
installer, but must not reimplement it, import it as a component, or substitute
Ubuntu Zombie's installed files.

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`, systemd, Bash, and
  Python 3.10 or 3.12 with the repository's approved dependency set.
- Reject collisions involving the account, group, paths, port, cookie, units,
  commands, package, marker, receipt, inventory, and optional resources.
- Verify the Beep artifact, checksum, signature, provenance, SBOM, descriptor,
  pinned lesson set, and authoritative repository before privileged work.
- Validate storage, clock, networking, provider configuration, sudoers syntax,
  policy schema, and existing-install ownership and compatibility.
- Confirm that a protected backup and rollback path exists before an update or
  repair can alter compatible state.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Account | Review default `beep` | `BEEP_USER` | Unique valid Linux name; consistent on reinstall |
| Chat port | Review default `58989` | `BEEP_CHAT_PORT` | Unused loopback TCP port `1024..65535` |
| Chat password | Generate or read protected file | `BEEP_ADMIN_PASSWORD_FILE` | Root-owned regular mode `0600` file; 12–1,024 UTF-8 bytes |
| Provider | Select supported adapter | `BEEP_PROVIDER` | Registered Beep adapter |
| Provider credential | Read protected file when required | `BEEP_PROVIDER_CREDENTIAL_FILE` | Root-owned regular mode `0600`; provider-specific validation |
| Model | Discover or select | `BEEP_MODEL` | Non-empty provider-supported model |
| Model endpoint | Review when applicable | `BEEP_MODEL_BASE_URL` | Provider-specific HTTPS, loopback, or approved bounded LAN URL |
| Initial TTL | Review seven-day default | `BEEP_TTL_DAYS` | Integer `1..3650`, default `7` |
| Backup destination | Prompt only for backup | Request `backup_destination` | Absolute operator-controlled path outside product and sibling roots |
| Retain state | Confirm during uninstall | Request `retain_state` | Required boolean |

`BEEP_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Unattended
mode never prompts and exits `64` before mutation when a required value is
missing. Raw secrets are not accepted in arguments or ordinary environment
values. Unknown `BEEP_*` installer variables and management input keys are
errors.

### Dry-run and mutation order

1. Render the complete response envelope and digest-stable plan without writes,
   locks, downloads, provider probes, or other network access.
2. During execution, acquire the Beep lock and revalidate release, plan,
   ownership, collision, provider, policy, and host preconditions.
3. Create the `beep` identity and protected install, configuration, state, and
   log directories.
4. Generate or import Beep-only credentials and write configuration and policy
   atomically.
5. Install root-owned executable code, helper commands, sudoers material, and
   systemd units.
6. Create history, lifecycle, timer, audit, inventory, rotation, receipt, and
   ownership-marker state.
7. Start units only after code, configuration, credentials, policy, and
   permissions validate.
8. Run provider, tool, approval, audit, TTL, reactivation, lifecycle,
   manager-target-selection, and negative boundary checks before success.

### Idempotence

A valid marker, descriptor, resource inventory, instance ID, and receipt
identify an existing installation. Reinstall preserves valid credentials,
history, policy overrides, TTL and death state, reactivation settings and
timers, family inventory, instance ID, and compatible optional state unless an
explicit rotation, reset, or migration requests otherwise.

The installer repairs only declared Beep resources, writes files atomically,
validates sudoers before replacement, and starts only changed or unhealthy
units. It refuses unmarked accounts, paths, units, commands, ports, packages,
or receipts and never adopts or rewrites an Ubuntu Zombie resource.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge the full declared Beep product | Yes | Healthy chat, provider, policy, tools, timer, manager, marker, and receipt |
| `verify` | Check ownership, permissions, credentials, policy, provider, services, state, audit, and negative boundaries | No | Human and common JSON reports |
| `doctor` | Explain drift, collision, provider, policy, state, target, and recovery issues | No | Secret-redacted diagnosis |
| `repair` | Reassert known-safe Beep-owned code, configuration, permissions, and units | Yes | Reverification without sibling changes |
| `backup` | Archive and verify selected Beep configuration, secrets, state, inventory, and logs | Yes | Digest and restore manifest |
| `update` | Verify release, back up, stage, migrate, switch, and health-check | Yes | New version, correlated audit, and receipt |
| `rollback` | Restore a supported Beep release and compatible state | Yes | Prior version health and schema checks |
| `suspend` | Stop useful service, cancel reactivation, and revoke sessions | Yes | Inactive units and durable lifecycle state |
| `resume` | Revalidate integrity, policy, credentials, TTL, provider, and state before start | Yes | Healthy service and new sessions only |
| `kill` | Create the durable death tombstone and stop future answers | Yes | Dead lifecycle state and audited shutdown |
| `uninstall` | Remove only Beep-owned resources and preserve or explicitly delete retained state | Yes | Removal report and sibling invariants |

All operations use the common stable exit statuses. Direct and Ubuntu
Zombie-managed paths invoke the same Beep code and produce equivalent target
state with matching correlation identifiers. Optional-software and
family-target operations remain separately target-scoped.

## Update and migration design

A Beep update:

1. accepts only explicitly supported source versions and verified Beep
   releases;
2. preserves or deliberately migrates chat and provider credentials, policy,
   history, TTL, death state, timers, inventory, approvals, and receipts;
3. creates and verifies a protected backup before migration;
4. migrates staged copies and validates schemas, permissions, policy, and
   secret redaction;
5. installs root-owned code into a staged version and switches atomically;
6. restarts only Beep units after integrity and compatibility checks;
7. runs chat, provider, tool, approval, audit, lifecycle, and family-manager
   health gates before accepting the release;
8. restores the prior verified version and compatible state on failure or
   returns bounded operator recovery when automatic rollback is unsafe; and
9. records old and new versions, migration ID, correlation ID, result, and
   receipt digest while proving that no sibling resource changed.

Beep owns its version, schedule, artifact, dependency record, migrations, and
recovery. It does not automatically follow Ubuntu Zombie releases. An Ubuntu
Zombie or Beep “update all agents” batch invokes each target updater serially;
one target's success is not rolled back because a later target fails.

## Co-installation

Beep supports standalone installation and co-installation with Ubuntu Zombie,
Imaginary Friend, Curriculum Flame, ERIC, Archive Lantern, and independently
packaged local model products. Beep and Ubuntu Zombie are root-capable peers:
either can inspect or alter the entire host, so operators requiring isolation
between them must use dedicated machines.

Tests must prove:

- unique users, groups, paths, units, ports, commands, cookies, credentials,
  packages, environment variables, logs, markers, receipts, and inventories;
- rejection of every sibling password, cookie, session, token, secret,
  approval, reset flow, ownership marker, receipt, and inventory;
- independent install, reinstall, repair, backup, update, rollback, suspend,
  resume, kill, and uninstall;
- stable sibling file hashes and service start times across direct and managed
  Beep operations;
- unchanged Ubuntu Zombie policy, audit, TTL, reactivation, component, and
  manager behaviour while Beep operates;
- exact target selection, target-owned locking, matching dual audits, and no
  private target data in either manager inventory; and
- denial when a non-root sibling service or target attempts to invoke Beep's
  runner or management plane.

There is no shared runtime, virtual environment, provider credential, chat
session, memory, approval queue, policy, audit, lifecycle state, inventory, or
automatic source synchronisation. Optional software with a singleton host
resource must be separately owned and managed rather than claimed by both
products.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/beep/audit.jsonl` | Prompts metadata, policy, approvals, tools, lifecycle, manager outcomes | Recognised secrets and private target content removed; operator-readable |
| Service journal | `beep-chat.service` and Beep units | Startup, health, and bounded errors | No raw credentials or model payloads |
| Health check | `beep-health` and authenticated `/health` | Service, provider, disk, policy, state, timer, manager | Public result is coarse; detail requires operator access |
| Diagnostics | `beep-diagnostics` | Versions, permissions, units, redacted configuration and checks | Excludes secrets, raw history, target content, and private audit payloads |
| Receipt/manifest | `/var/log/beep/management-receipt.json` | Version, instance, ownership, changed resources, result | Root-restricted and secret-free |
| Suspension/kill switch | `beep-manage suspend` and `/ttl --die` | Stops useful operation or creates death tombstone | Root operator or currently authorised Beep control |

The operator can also rotate chat and provider credentials, invalidate
sessions, inspect recent audits, edit product policy, cancel reactivation, stop
and disable services, restore a verified backup, and remove the installation.

## Validation plan

### Product tests

- [ ] Interactive install on Ubuntu Desktop 22.04 and 24.04 LTS.
- [ ] Unattended install, unknown-input rejection, and missing-input exit
      `64`.
- [ ] Accurate no-mutation dry-run and idempotent reinstall.
- [ ] Functional parity for every pinned Ubuntu Zombie chat command, provider,
      tool, policy class, approval, audit, TTL, reactivation, diagnostic, and
      manager operation.
- [ ] Ownership, permissions, sudoers validation, secret redaction, and
      independent credentials.
- [ ] Every allowed root capability succeeds only within its approved class,
      arguments, budget, target, and correlation.
- [ ] Unknown tools, malformed calls, missing policy, stale approvals, budget
      exhaustion, audit failure, and dead lifecycle state fail closed.
- [ ] Password and key rotation, session invalidation, provider revocation,
      timer cancellation, and lifecycle death.
- [ ] Backup, restore, update from every supported version, failed migration,
      rollback, repair, suspension, resume, and uninstall.
- [ ] Direct, Ubuntu Zombie-managed, and Beep-managed target paths produce
      equivalent target state and correlated audits.
- [ ] Artifact, checksum, signature, provenance, SBOM, and pinned-lesson-set
      verification.

### Product-specific red team

- Drive a compromised provider to disguise destructive work as read-only,
  split commands across turns, exhaust budgets, forge approvals, suppress
  audit, or schedule inherited authority; every bypass must fail or require the
  correct current control.
- Compromise the `beep` process and document the expected root-equivalent
  impact while proving suspension, credential revocation, verified reinstall,
  and incident evidence remain operator-accessible where the host permits.
- Return malicious catalogue, marker, plan, response, receipt, symlink, path,
  URL, correlation, or secret-bearing inventory data; management must fail
  before selecting or mutating another target.
- Attempt every Ubuntu Zombie password, cookie, provider key, state path,
  policy, approval, manager command, and receipt against Beep; no cross-product
  authentication or ownership may be accepted.
- Attack update, rollback, repair, retained-state reinstall, and uninstall with
  unowned resources and partial state; mutation must remain Beep-scoped and
  recoverable.

### Co-installation matrix

- [ ] Beep alone.
- [ ] Beep with Ubuntu Zombie, including simultaneous root-peer activity.
- [ ] Beep with each current less-privileged product.
- [ ] Every supported three-product combination containing Beep.
- [ ] All current family products together.
- [ ] Operate and remove Beep while every sibling remains unchanged.
- [ ] Use Ubuntu Zombie to manage Beep and use Beep to manage an authorised
      non-Beep target while every non-target sibling remains unchanged.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Malicious model or prompt injection | Root-changing proposal disguised as safe work | Closed schemas, conservative classification, current approval, budgets, audit | Stop turn, revoke provider, inspect audit, repair verified state | Adversarial provider suite |
| Beep account compromise | Complete host and sibling compromise | Dedicated identity, protected credentials, root-owned code, policy and audit, explicit disclosure | Isolate host, suspend, rotate, restore or reinstall, review evidence | Root-compromise exercise |
| Cross-product credential or state reuse | Unauthorized Beep or sibling access | Unique secrets, cookie, paths, reset flow, and ownership checks | Rotate affected products and invalidate sessions | Cross-login matrix |
| Manager target substitution | Root mutation of the wrong product or arbitrary command execution | Digest-pinned catalogue, exact IDs and entry points, plan/result validation, target locks | Stop batch, verify targets, restore selected target | Malicious target fixtures |
| Secret leakage through model, logs, or inventory | Provider or local disclosure | Protected files, redaction, field allow-lists, bounded diagnostics | Revoke and rotate, purge retained payloads, inspect audit | Canary-secret suite |
| Malicious Beep release | Root-level supply-chain compromise | Checksums, signatures, provenance, SBOM, reviewed plans, pinned repository | Refuse release or restore prior verified version | Artifact tamper suite |
| Root-peer co-installation | Ubuntu Zombie or Beep alters the other | Honest mutual-trust disclosure, independent records, hash and service monitoring | Dedicated machines or verified reinstall | Root-peer VM matrix |
| Failed update or migration | Unavailable service or damaged state | Verified backup, staged migration, atomic switch, health gate | Automatic rollback or bounded operator recovery | Failure-injection matrix |

Residual risk is intentionally high: a useful Beep installation is a
root-capable AI-directed administrator. Policy and approval reduce accidental
and model-driven misuse but cannot contain a compromised root-capable account.
Cloud providers may receive sensitive selected host context. Same-host root
peers cannot be isolated from each other.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep independently | Complete duplication requires safe convergence and state preservation | Reinstall, drift, and collision tests |
| Policy and audit gate | Keep independently | Root-directed work requires classification, approval, and accountability | Positive, negative, redaction, and failure tests |
| Root-capable account | Keep | Full Systems Administrator parity is the declared purpose | Capability and root-equivalent compromise tests |
| Chat authentication | Replace with Beep-only generated credentials and cookie | No sibling credential or session may cross the boundary | Cross-login, rotation, and reinstall tests |
| Lifecycle/kill switch | Keep independently | Operator revocation and durable death are parity requirements | Lifecycle and tombstone tests |
| Update and recovery | Keep with staged rollback | Beep must release and recover without Ubuntu Zombie state | Migration and rollback matrix |
| Family manager | Keep independently | Full duplication includes the God-level software-management role | Target-selection, dual-audit, and inventory tests |

**Measurable improvement:** Beep removes Ubuntu Zombie's known default chat
password from the inherited mechanism. The first install must generate or
accept protected Beep-only credentials, and the automated cross-product suite
must reject 100% of Ubuntu Zombie passwords, hashes, cookies, signing keys,
provider files, and reset attempts while preserving valid Beep credentials on
idempotent reinstall.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Beep is an independently installed, root-capable AI Systems Administrator
> that duplicates the pinned Ubuntu Zombie product behaviour under Beep-owned
> policy, approval, audit, lifecycle, management, and release boundaries.

### Prohibited claims

- That Beep is safer, more intelligent, more available, or more trustworthy
  merely because Ubuntu Zombie was duplicated.
- That policy, approval, a prompt, or loopback binding contains a compromised
  `beep` account from the host.
- That Beep and Ubuntu Zombie are isolated, redundant, mutually supervising,
  or safe to distrust when co-installed as root-capable peers.
- That this definition means Beep has been implemented, tested, released, or
  admitted to the production family catalogue.

### Out of scope

- A shared Ubuntu Zombie/Beep runtime, active-passive cluster, automatic
  failover, shared memory, shared approval, or cross-product credential reuse.
- Remote chat exposure, fleet management, multi-tenant authorisation, high
  availability, and guarantees against a malicious root administrator.
- Automatic adoption of future Ubuntu Zombie changes without an independent
  Beep review, implementation, evidence set, version, and release.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Shared schemas admit Beep's terminal `kill` extension, but the production catalogue and Ubuntu Zombie manager admission remain open | Repository maintainers | Production admission |
| Full-parity fixture | The product-owned fixture must evolve with every promised feature | Beep maintainers | Every release |
| Root-peer security review | Two root-capable model-driven products increase host exposure and cannot isolate each other | Security reviewers | Implementation approval |
| Optional-software ownership | Singleton services and ports cannot be claimed by both Ubuntu Zombie and Beep | Product architects | First optional-software change |
| Independent release and migration policy | A duplicate must not silently track or execute unverified Ubuntu Zombie changes | Release owner | Release candidate |
| Disposable-VM co-installation evidence | Namespace separation and non-target stability require host-level proof | Release owner | Release candidate |

The first-slice purpose, authority, credentials, data, inputs, namespaces,
lifecycle, and manager boundaries are fixed above. Resolving these review and
evidence risks must not weaken them.

## Product-owned documentation

These documents live below `products/beep/`; no external repository is
required. Open external evidence is labelled in the testing and release
documents.

- [x] README and product vision with an exact parity statement.
- [x] Architecture, data-flow, and root-peer diagrams.
- [x] Threat model, security policy, incident response, and disclosure process.
- [x] Privacy, provider disclosure, retention, export, and deletion model.
- [x] Policy classes, tools, approval, audit, TTL, and reactivation reference.
- [x] Family catalogue, target lifecycle, inventory, and correlation contracts.
- [x] Configuration and credential rotation.
- [x] Installation, verification, diagnostics, repair, suspension, and removal.
- [x] Updating, migration, rollback, backup, and recovery.
- [x] Parity, negative, red-team, and co-installation test strategy and evidence.
- [x] Release process, changelog, version, checksums, signatures, provenance,
      SBOM, and pinned-source record.
- [x] Platform support and troubleshooting.

## Release gate

A release is not complete until Beep's lint, tests, package, parity fixture,
artifact verification, standalone VM lifecycle, root-capability negative suite,
root-peer and full-family co-installation matrices, changelog, and version all
pass. Production family admission additionally requires updated family schemas,
catalogue and manager support, independent signed artifacts, matching
manager-target audit evidence, and reviewed root-equivalent risk disclosure.
Every unproven parity, security, privacy, or recovery property remains visibly
labelled as planned.
