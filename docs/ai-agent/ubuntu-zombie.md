# Ubuntu Zombie

> A private, root-capable AI Systems Administrator that lets the owner of a
> supported Ubuntu Desktop LTS machine ask it to diagnose, explain,
> configure, repair, and operate itself under explicit policy, approval,
> lifecycle, and audit controls.

Ubuntu Zombie is the first and currently implemented member of the
[AI-agent family](README.md). It also has the **God role**: the root-level
manager that can install and manage the other agents for the human
operator. Those products copy its proven disciplines, select the authority
their own purposes require, and retain independent runtimes, credentials,
policies, data, and releases. Another systems-administrator variant may be
equally root-capable.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Core Systems Administrator implemented; dedicated family management is required but not yet implemented |
| Human need | Operate and repair a complex personal Ubuntu machine without requiring the owner to translate every problem into administration commands |
| Intended user | The owner/operator and authorised local users of one machine |
| Operator | The human who owns the machine, provider account, chat credential, and lifecycle controls |
| Maximum authority | Root through the installed account, including approved management of other local agents |
| Default Linux identity | `zombie` (renameable with `ZOMBIE_USER`) |
| Default access | Password-protected loopback chat at `127.0.0.1:7878` |
| Install root | `/opt/ai-zombie` |
| Configuration root | `/etc/ubuntu-zombie` |
| State root | `/opt/ai-zombie/state` |
| Log root | `/var/log/ubuntu-zombie` |
| Environment prefix | `ZOMBIE_*` |
| Family contract | Repository `family/`; installed `/opt/ai-zombie/family/` |
| Family CLI | `/opt/ai-zombie/bin/zombie-agents` |
| Authoritative repository | [`japer-technology/ubuntu-zombie`](https://github.com/japer-technology/ubuntu-zombie) |

## Product promise

The product installs an administrator *beside* the existing desktop user,
not over them. A human asks for work in plain language, the agent inspects
the machine, explains its proposal, requests approval when required, runs
the selected action, and leaves an audit record.

The operator remains the principal. Provider access can be revoked, the
service can be stopped, the Time to Live can expire or be killed, and the
installation can be removed. Ubuntu Zombie is transparent local software,
not a hosted service, locked appliance, autonomous tenant, or fleet control
plane.

## Why it is the reference product

Ubuntu Zombie demonstrates that a local AI product can combine:

- a dedicated Linux operating identity;
- an idempotent interactive and unattended installer;
- visible preflight and dry-run behaviour;
- a closed tool registry;
- classification and explicit approval before elevated work;
- secret-redacted audit and diagnostics;
- health, verification, diagnosis, repair, and removal commands;
- a bounded lifecycle and operator kill switch; and
- independently verifiable release artifacts.

Later products inherit these outcomes, not this live runtime. Ubuntu Zombie
remains the root-capable reference product and designated machine
administrator; that designation does not prevent another product from defining
and testing equivalent root authority.

## Implemented features

### Local chat and conversation

- The browser UI binds to loopback only and is protected by a chat
  password. Only its salted PBKDF2 hash is stored.
- Authenticated server-sent events show live model, tool, and approval
  progress. Clients fall back to the synchronous JSON path and transcript
  reload when streaming is unavailable.
- One normal message can remain visibly queued while a turn is active.
  Immediate slash commands, including stop and approval controls, still
  work during the turn.
- Conversations, tool events, and lifecycle metadata persist locally in
  SQLite and JSON state.
- `/help` exposes the command catalogue; `/status` performs a
  proof-of-life provider check and host summary; `/version` reports local
  and available versions.
- Model discovery and selection are available through `/locals` and
  `/models`; browser-local branding, prompt text, and transcript width can
  be changed without rewriting product files.

The complete command and chat behaviour reference is in
[`../CONFIGURATION.md`](../CONFIGURATION.md#chat-access).

### Model providers

Ubuntu Zombie supports OpenAI, Anthropic, Google Gemini, xAI, Mistral,
Groq, OpenRouter, and OpenAI-compatible local servers through the
`@earendil-works/pi-ai` bridge. Provider and model selection come from the
product-owned secrets environment rather than a second native `pi`
configuration.

Interactive installation can discover LM Studio, Ollama, and `llama.cpp`
servers on a bounded set of LAN ports. Runtime discovery is explicit. A
separately installable CPU `llama.cpp` component provides a loopback-only
OpenAI-compatible endpoint and does not require the Zombie agent.

See [`../CONFIGURATION.md`](../CONFIGURATION.md#provider-keys) for the
current provider variables and model defaults.

### Closed tools and skills

The runtime presents a closed, schema-validated tool set:

| Tool area | Purpose |
| --------- | ------- |
| `shell.run` | Run a command through policy classification and the command runner |
| `fs.read`, `fs.list`, `fs.write` | Bounded filesystem inspection and writes |
| `pkg.query`, `pkg.install` | Query or install Debian packages |
| `svc.status`, `svc.control` | Inspect or control systemd units |
| `net.status` | Inspect interfaces and listening ports |
| `web.fetch` | Read a bounded public HTTP or HTTPS resource |
| `skill.list`, `skill.load` | Find and load product-owned operating briefs |
| `timer.reactivation` | Schedule one bounded future continuation |

Built-in Markdown skills guide the model towards these tools and their
policy classes. Skills do not add executable tools or increase authority.
Operators can add local guidance under `/etc/ubuntu-zombie/skills.d/`
without changing the registry.

The read-only web tool rejects embedded credentials and hosts resolving to
loopback, link-local, or private addresses on the initial request and every
redirect. It has no request body, truncates responses, and records the URL
in the audit trail.

### Policy and approval

Every proposed tool call is schema-validated and classified. The shipped
policy uses these classes:

| Class | Meaning |
| ----- | ------- |
| `read_only` | Inspection that can run automatically |
| `chat_schedule` | One bounded, visible future conversation turn |
| `user_change` | Mutation within product-approved user state |
| `system_change` | Package, service, or privileged filesystem mutation |
| `network_change` | Firewall or interface mutation |
| `destructive` | Irreversible work requiring the confirmation phrase |

Unknown commands fail closed into the highest-gated class. Elevated calls
require operator approval; destructive calls require the explicit
confirmation phrase. Per-turn tool, elevated-call, and inactivity budgets
bound model operation without silently changing the approval rules.

The policy is reloaded on every request from
`/etc/ubuntu-zombie/policy.yaml`. The account's underlying root capability
is broader than the policy: this gate and its audit trail are the intended
runtime safety boundary, not an operating-system sandbox.

### Audit and observability

- `/var/log/ubuntu-zombie/audit.log` contains secret-redacted JSON Lines for
  prompts, policy decisions, approvals, tool actions, outcomes, lifecycle
  events, and verification.
- `audit-recent` presents recent audit records.
- `health-check` provides a one-shot service, provider, disk, permission,
  and runtime summary.
- `collect-diagnostics` creates a redacted support bundle.
- Installer transcripts and a component-aware receipt record host changes
  and outcomes.
- Service events remain available through the product-named systemd
  journal.

Audit evidence is local and logrotated. It is not sent to the model
provider as a matter of normal operation.

### Time to Live and reactivation

The first install creates a seven-day Time to Live by default. The operator
can inspect or extend it, reset it from the current time, or run
`/ttl --die`. Expiry and explicit death create a durable tombstone and stop
future answers. A normal reinstall preserves valid lifecycle state,
including extensions and death; a full uninstall followed by a new install
creates a new lifecycle.

The agent can request one future continuation through
`timer.reactivation`. The request:

- is visible and cancellable in the authenticated UI;
- is constrained by configured delay bounds and remaining TTL;
- starts a normal turn with fresh policy and approval decisions;
- carries no authority or approval from the previous turn; and
- is recorded in history and audit with its chain outcome.

The operator can enable, disable, reset, or cancel reactivation. Only one
timer exists across conversations, so a later accepted request must
explicitly replace the current one.

### Optional system installations

The component-aware installer currently knows:

| Component | Purpose | Relationship to the agent |
| --------- | ------- | ------------------------- |
| `zombie` | Account, runtime, chat, policy, state, and services | The Ubuntu Zombie product baseline |
| `forgejo` | PostgreSQL-backed local git forge behind Caddy | Optional software managed by the same installer; not another AI agent |
| `forgejo-runner` | Restricted co-located Forgejo Actions runner | Depends on `forgejo`; does not select `zombie` |
| `llama` | Standalone CPU `llama.cpp` server and verified model | Independent local model endpoint; does not select `zombie` |

Other plans under [`../options/`](../options/) are designs, not implemented
features. Imaginary Friend, Curriculum Flame, and ERIC must never become
component targets.

### Family management (“God” role)

Ubuntu Zombie's root authority lets it serve as the designated administrator
for managed agents installed on the same machine. A separately defined
root-capable product is an operating-system peer, not an isolated subordinate.
Ubuntu Zombie must be able to:

- discover independently installed agents from verified ownership markers;
- show product, version, authority, health, lifecycle, and update status;
- fetch and verify a target's release artifacts;
- display and invoke its product-owned install or dry-run entry point;
- run its verify, doctor, repair, backup, update, rollback, suspend, and
  uninstall operations;
- coordinate a serial “update all agents” operation with per-product plans,
  approvals, health gates, results, and recovery; and
- keep a secret-free inventory and cross-reference the manager and target
  audit records.

This dedicated management plane is the next implementation work package in
[`implementation.md`](implementation.md#implementation-order-and-hand-off-gates).
The current runtime can already execute product-owned lifecycle commands
with root authority through `shell.run`, `svc.control`, and filesystem tools,
subject to normal classification and operator approval, but it does not yet
ship the dedicated catalogue, family inventory, CLI, tools, or UI described
below.

The first manager implementation adds:

| Repository source | Installed purpose |
| ----------------- | ----------------- |
| `family/catalog.json` and `family/schemas/` | Digest-pinned product allowlist and lifecycle schemas under `/opt/ai-zombie/family/` |
| `payload/agent/family.py` | Strict catalogue, descriptor, marker, request, response, and inventory validation |
| `payload/bin/zombie-agents` | Root CLI for list, status, plan, install, verify, doctor, repair, backup, update, rollback, suspend, resume, and uninstall |
| `/var/lib/ubuntu-zombie/agents/inventory.json` | Atomic, secret-free cache of validated installed products and last outcomes |

`zombie-agents` accepts only product IDs from the installed catalogue and
invokes only the relative release entry point or absolute installed entry
point recorded by the matching validated descriptor and ownership marker.
It uses an argument array without a shell, applies bounded timeouts, captures
only the common JSON response, and verifies target, operation, correlation
ID, plan digest, and receipt before updating inventory.

The chat runtime gains four closed tools:

| Tool | Class | Boundary |
| ---- | ----- | -------- |
| `agent.list` | `read_only` | Validated catalogue and inventory summaries |
| `agent.status` | `read_only` | One exact product ID |
| `agent.plan` | `read_only` | Target dry-run with no secret collection |
| `agent.manage` | `system_change` or `destructive` | Execute one approved plan for one exact product |

The tool schemas use a catalogue product-ID enum and never accept a command,
path, URL, environment map, or sibling-supplied target. Destructive uninstall
still requires the existing confirmation phrase plus the target's
product-specific confirmation. An operation needing a new target password,
key, consent, or guardian decision is refused in chat and directs the
operator to the local root CLI or target interface; model-visible text is not
a secret-entry channel.

The management contract is deliberately narrow:

1. the target product owns its installer, updater, migrations, rollback,
   policy, receipt, and uninstaller;
2. Ubuntu Zombie verifies and invokes those interfaces rather than
   rewriting them;
3. the operator sees the exact target and plan before mutation;
4. manager actions are `system_change` or `destructive` as appropriate and
   are audited by Ubuntu Zombie;
5. the target independently validates ownership, authority, and inputs and
   writes its own audit result;
6. Zombie inventory stores identifiers, versions, health, receipt
   references, and outcomes, never raw target credentials or private
   content; and
7. family membership and manager integration grant no target access to the
   management plane or authority beyond the target's own product definition.

The request, response, marker, receipt, health, lock, exit-status, and audit
formats are not product-specific design work. They are fixed by
[`implementation.md`](implementation.md#lifecycle-entry-point).

“God” is a host-administration role, not an identity, consent, guardian, or
legal role. Ubuntu Zombie may manage ERIC's software and service lifecycle,
for example, but it cannot turn an inference into consent, weaken a frozen
Constitution, or manufacture Executor authority.

## People and trust boundaries

### Operator

The operator owns:

- the physical machine;
- the provider account and API key;
- the chat password;
- the TTL and reactivation controls;
- policy configuration and approvals; and
- service suspension, credential revocation, uninstall, and approved
  management of managed agents.

### Agent identity

The dedicated `zombie` account is the operating identity of the Systems
Administrator and holds passwordless `sudo`. Compromise of that account or
of provider authority that can successfully drive it is root-equivalent.
The account name is configurable, but later lifecycle commands must use the
same name.

### Model provider

A cloud provider receives typed and scheduled prompts, conversation history,
and local context or command output that the assistant includes in a turn.
It does not receive the provider API key, chat password, product secrets
directory, or local audit log through the normal provider interface.

Local model servers reduce cloud disclosure but do not change Ubuntu
Zombie's host authority. The operator must still evaluate the local model,
server, and network boundary.

### Browser and local users

Every local user can reach a loopback listener, so the password gate
protects the chat. This is a single product-owner authentication boundary,
not multi-user authorisation. A person with a root or Zombie shell remains
root-equivalent regardless of browser authentication.

## Runtime shape

The principal turn path is:

1. an authenticated browser submits a prompt;
2. lifecycle and turn-state checks run;
3. the product sends the prompt and conversation context to the configured
   model through the `pi` bridge;
4. proposed calls enter the closed tool registry;
5. schema and policy classification determine whether work can run or needs
   approval;
6. the runner executes accepted calls and returns bounded results;
7. decisions and outcomes enter history and audit; and
8. the final answer is persisted and returned to the browser.

Core runtime modules and their responsibilities are documented in
[`../ARCHITECTURE.md`](../ARCHITECTURE.md#runtime-components).

## Product-owned resources

| Resource | Current Ubuntu Zombie ownership |
| -------- | ------------------------------- |
| Account and group | `zombie` by default; configurable as one consistent identity |
| Payload and helpers | `/opt/ai-zombie/agent`, `/opt/ai-zombie/bin`, `/opt/ai-zombie/pi` |
| Secrets | `/opt/ai-zombie/secrets/env`, mode `0600` |
| Conversation and lifecycle state | `/opt/ai-zombie/state/` |
| Component and future family metadata | `/var/lib/ubuntu-zombie/components/`; planned `/var/lib/ubuntu-zombie/agents/` |
| Operator policy and skill overlays | `/etc/ubuntu-zombie/` |
| Audit and receipt | `/var/log/ubuntu-zombie/` |
| Chat service | `ubuntu-zombie-chat.service` |
| Sudo boundary | Product-named drop-in under `/etc/sudoers.d/` |
| Default cookie and listener | Product-specific session cookie; `127.0.0.1:7878` |
| Environment | `ZOMBIE_*` |

The installer also owns explicit manifests and receipts for selected
components. It must not infer ownership of an unmarked sibling product.
`/opt/ai-zombie/state/` is the authoritative chat/lifecycle state root;
`/var/lib/ubuntu-zombie/` contains root-owned component and family-management
metadata, not a second conversation state root.

## Installation

Ubuntu Zombie supports:

- an interactive parameter review before mutation;
- `--dry-run` to display the selected plan;
- `ZOMBIE_NONINTERACTIVE=1` and `--yes` for unattended operation;
- explicit component targets and dependency ordering;
- validated settings and preflight checks;
- retry and verification around downloaded dependencies;
- receipts that distinguish selected components and outcomes; and
- idempotent convergence on re-run.

The canonical command grammar is:

```text
sudo ./scripts/install.sh <install|verify|doctor|repair|uninstall> \
  [zombie|forgejo|forgejo-runner|llama ...] [flags]
```

A default `install` selects only the Zombie baseline. Operators should
preview with `install --dry-run`, then follow
[`../QUICKSTART.md`](../QUICKSTART.md) on a supported disposable Ubuntu
Desktop LTS machine before using a real workstation.

## Lifecycle management

| Operation | Ubuntu Zombie behaviour |
| --------- | ----------------------- |
| `install` | Installs or converges selected components and preserves valid secrets and state |
| `verify` | Performs read-only component checks, with human or JSON output |
| `doctor` | Explains detected drift and likely recovery |
| `repair` | Reasserts known-safe permissions/configuration and restarts the selected service where needed |
| `update` | Pull or unpack a release and re-run idempotent `install` |
| manage agent | Invoke the fixed family lifecycle interface under policy, approval, strict target selection, and dual audit; implementation is specified but not shipped |
| revoke | Remove provider keys or stop and disable the chat service |
| kill | Use `/ttl --die` to create the durable lifecycle tombstone |
| `uninstall` | Removes all or selected owned components, with state/archive choices for Zombie |

Component-selective operations do not intentionally install, restart, or
remove an unselected component.

## Update, recovery, and removal

Ubuntu Zombie does not yet have an in-place package-manager upgrade command.
The supported update procedure is:

1. read [`../../CHANGELOG.md`](../../CHANGELOG.md);
2. back up the secrets environment, product state, and audit records that
   must be retained;
3. verify and unpack or pull the new release;
4. re-run `scripts/install.sh install`; and
5. run `verify` and `health-check`.

Reinstallation rerenders runtime configuration and built-in skills while
preserving provider secrets and valid lifecycle/conversation state.
Downgrades are unsupported; recovery requires the operator's backup or a
fresh installation of the desired release.

Uninstall removes product services, sudoers material, payload, policy,
logrotate configuration, and selected product-owned state. Shared system
packages are not treated as exclusively owned. See
[`../UPGRADING.md`](../UPGRADING.md) and
[`../QUICKSTART.md`](../QUICKSTART.md#uninstall) for live instructions.

## Security properties and known limits

### Properties

- The baseline exposes no inbound LAN listener; chat remains loopback-only.
- Only password hashes are stored for chat authentication.
- Unknown commands receive the most restrictive default classification.
- Sensitive actions are policy-gated and audited.
- Filesystem tools resolve and check approved paths and explicitly exclude
  the secrets directory and process environments from automatic reads.
- Diagnostic and audit writes redact recognised secrets.
- TTL, service revocation, key rotation, and uninstall remain under operator
  control.

### Limits

- Passwordless `sudo` is intentional. Ubuntu Zombie is not sandboxed from
  the host and cannot be made safe solely by a prompt.
- Cloud providers can receive prompts, conversation history, and selected
  machine data.
- The chat password is one local owner boundary, not a multi-tenant identity
  system.
- Conversation history is local SQLite state and is not advertised as
  encrypted at rest.
- No SSH, Tailscale, VNC, graphical automation, remote-access service,
  multi-machine fleet management, high availability, or provider failover
  is installed by the baseline.
- Only one future reactivation can be pending.
- Supported platforms and architectures are limited to those listed in
  [`../PLATFORMS.md`](../PLATFORMS.md).
- Updates are forward-moving; downgrades are not supported.

The known default chat password exists for compatibility and should be
changed. Later family members improve on this baseline with generated
credentials, root-owned executable code, hardened units, and smaller
purpose-specific tool registries from their first release.

## Validation and release evidence

Repository checks include ShellCheck, Bash syntax validation, Python
compilation, non-root smoke tests, installer parser and unattended-mode
tests, packaging checks, secret scanning, and release workflows. The
installer also exposes `verify`, `doctor`, `repair`, `health-check`, and
redacted diagnostics for the installed product.

Disposable-VM validation must continue to prove:

- clean and repeated installation;
- interactive, unattended, and dry-run behaviour;
- policy and approval decisions;
- audit completeness and redaction;
- TTL death and state preservation;
- credential rotation and revocation;
- update and repair convergence;
- selective and complete removal; and
- unchanged root-capable behaviour when later family products are
  co-installed;
- strict target selection and product-owned lifecycle invocation; and
- matched, secret-redacted audit evidence for every managed operation.

Hermetic manager tests must additionally reject unknown catalogue fields,
duplicate JSON keys, unpinned versions and URLs, path traversal, symlinked or
mis-owned markers/request files, mismatched product or operation responses,
stale plan digests, secret-bearing inventory fields, unauthorised callers,
timeouts, and non-target receipt updates.

Run the repository's existing `make lint` and `make test` checks for every
source change. Do not run the live installer outside a disposable Ubuntu
Desktop LTS VM.

## Canonical operating documentation

| Document | Authority |
| -------- | --------- |
| [`../../README.md`](../../README.md) | Product entry point, current features, and command grammar |
| [`../VISION.md`](../VISION.md) | Narrow product promise and non-promises |
| [`../QUICKSTART.md`](../QUICKSTART.md) | Installation and first use |
| [`../CONFIGURATION.md`](../CONFIGURATION.md) | Providers, policy, chat, lifecycle, components, and settings |
| [`../ARCHITECTURE.md`](../ARCHITECTURE.md) | Runtime, tools, trust boundaries, and installed components |
| [`../../SECURITY.md`](../../SECURITY.md) | Threat model, provider disclosure, risks, revocation, and disclosure process |
| [`../UPGRADING.md`](../UPGRADING.md) | Supported update and recovery process |
| [`../TROUBLESHOOTING.md`](../TROUBLESHOOTING.md) | Diagnosis and support bundles |
| [`../PLATFORMS.md`](../PLATFORMS.md) | Supported host matrix |
| [`../../CHANGELOG.md`](../../CHANGELOG.md) | Versioned changes |

This document is the family-facing definition. The linked operator
documents remain authoritative for live commands, defaults, and current
implementation details.
