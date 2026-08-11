# Imaginary Friend

> A private conversational companion with access only to its own state and
> a workspace deliberately shared by its human owner.

Imaginary Friend is the first less-privileged variation on the
[Ubuntu Zombie](ubuntu-zombie.md) product lessons. It retains installation,
authentication, lifecycle, policy, audit, diagnostics, and release
discipline while deleting general host-administration power.

This definition now has a standalone implementation and independent release
below `products/imaginary-friend/`. It is not yet a claim of production family
support: catalogue admission remains gated on the Ubuntu Zombie manager,
recorded disposable-VM and co-installation evidence, and final release
verification.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Standalone source and release implemented; production family admission gated |
| Human need | A persistent private place for conversation and work without granting an AI authority over the machine |
| Intended user | One human owner |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Friend-owned state and explicitly nominated shared workspace paths |
| Default Linux identity | Non-login `friend` account and group |
| Default access | Password-protected loopback UI at `127.0.0.1:6767` |
| Install root | `/opt/imaginary-friend` |
| Configuration root | `/etc/imaginary-friend` |
| State root | `/var/lib/imaginary-friend` |
| Log root | `/var/log/imaginary-friend` |
| Unit prefix | `imaginary-friend-*` |
| Command prefix | `friend-*` |
| Environment prefix | `FRIEND_*` |
| Management entry point | Source `scripts/manage.sh`; installed `/usr/local/sbin/friend-manage` |
| Source root | `products/imaginary-friend/` |
| Authoritative repository | [`japer-technology/ubuntu-zombie`](https://github.com/japer-technology/ubuntu-zombie) |

## Status and evidence

Implemented source is not the same as an admitted production family target.
The current evidence and remaining gates are:

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition and first slice | Passed | This document and [`implementation.md`](implementation.md) |
| Configuration and data contracts | Implemented | [`PRODUCT.json`](../../products/imaginary-friend/PRODUCT.json), family schemas, and product tests |
| Threat and privacy models | Documented; review continues | Product [`SECURITY.md`](../../products/imaginary-friend/docs/SECURITY.md) and [`PRIVACY.md`](../../products/imaginary-friend/docs/PRIVACY.md) |
| Standalone runtime and lifecycle | Implemented | [`products/imaginary-friend/`](../../products/imaginary-friend/) |
| Non-root and hermetic tests | Automated | Unit, integration, HTTP, model, and family conformance suites |
| Security boundary | Automated baseline; release red team remains open | Workspace, model, policy, HTTP, asset, and guarded VM tests |
| Update, backup, and rollback | Implemented; supported-VM evidence required per release | Product lifecycle and guarded VM harness |
| Standalone VM validation | Open release gate | Record clean 22.04 and 24.04 LTS lifecycle passes |
| Ubuntu Zombie management and co-installation | Open family gate | Manager and sibling implementation slices |
| Independent artifact | Released; production catalogue admission open | Product release workflow, SBOM, checksums, provenance, signatures, and test evidence |

## Fixed first implementation

The first release implements one owner, text conversation, bounded local
workspaces, and the complete lifecycle contract. These decisions are fixed:

| Concern | First-release decision |
| ------- | ---------------------- |
| Platforms | Ubuntu Desktop 22.04 and 24.04 LTS on `amd64` |
| Runtime | Product-owned Python 3.10 or 3.12 service and SQLite state |
| Model | OpenAI-compatible loopback endpoint only; default `http://127.0.0.1:8080/v1` |
| Authentication | Mandatory generated or supplied owner password; independent `imaginary_friend_session` cookie |
| Workspace | Product-created `/srv/imaginary-friend/workspace` by default; additional roots require explicit validation |
| Conversation retention | Enabled for 30 days by default; configurable from 1 to 365 days |
| Operational audit retention | 90 days by default; message and file contents excluded |
| Session lifetime | 12 hours, revoked on password rotation, suspension, or uninstall |
| Backup | Friend state and metadata; nominated workspace contents are excluded |
| Network | Loopback UI and configured loopback model endpoint only |
| Source lesson set | Ubuntu Zombie `v2026.08.07.05.56.42` |

Cloud providers, multiple owners, arbitrary adoption of existing directory
trees, voice, image, remote access, and proactive messaging are absent from
the first release. Their absence does not block implementation.

### Configuration contract

Interactive install reviews every value. Unattended install accepts only:

| Input | Variable or request key | Rule |
| ----- | ----------------------- | ---- |
| Non-interactive mode | `FRIEND_NONINTERACTIVE=1` | Never prompts |
| Human owner | `FRIEND_OWNER_USER` / `owner_user` | Existing non-root local account; required unattended |
| Owner password | `FRIEND_OWNER_PASSWORD_FILE` / `owner_password_file` | Root-owned mode `0600` file containing one line of 12 or more characters and at most 1,024 UTF-8 bytes; required for first unattended install |
| Model endpoint | `FRIEND_MODEL_BASE_URL` / `model_base_url` | HTTP loopback URL; default above |
| Model ID | `FRIEND_MODEL` / `model` | Non-empty and required unattended |
| Workspace roots | `FRIEND_WORKSPACES_FILE` / `workspaces_file` | Optional root-owned JSON array; default product-created root |
| History retention | `FRIEND_HISTORY_RETENTION_DAYS` / `history_retention_days` | Integer `1..365`, default `30` |
| Audit retention | `FRIEND_AUDIT_RETENTION_DAYS` / `audit_retention_days` | Integer `30..3650`, default `90` |
| Backup destination | request `backup_destination` | Absolute operator-controlled path, used only by `backup` |
| Retain state | request `retain_state` | Required boolean for `uninstall` |

Unknown `FRIEND_*` installer inputs and unknown management request keys are
errors. Raw passwords and model credentials are never accepted in an
environment value or command argument. Missing required unattended input
exits `64` before mutation.

## Product promise

Friend provides conversation and a bounded workspace, not computer
administration. Its useful authority is intentionally small:

- hold private conversations for its owner;
- create, read, organise, revise, and remove files only inside Friend-owned
  state and owner-nominated workspace roots;
- preserve product state according to visible retention rules;
- explain and audit operations that change workspace content; and
- let the owner inspect, export, suspend, reset, and remove the product.

Friend is not Ubuntu Zombie with a persona or reduced policy setting. Its
lack of host authority is established by Linux identity, filesystem
ownership, systemd confinement, absent tools, and negative tests before a
model prompt is involved.

## Relationship to Ubuntu Zombie

### Lessons retained

- idempotent interactive and unattended installation;
- preflight, parameter review, and accurate dry-run;
- separate Linux identity and product namespaces;
- salted password authentication and independent sessions;
- a closed capability registry with policy and audit together;
- local health, verify, doctor, repair, update, recovery, and uninstall;
- secret-redacted receipts and diagnostics; and
- signed, provenance-verifiable releases with product-owned tests.

### Authority removed

Friend has:

- no passwordless `sudo`;
- no login shell or privilege-bearing group membership;
- no general command runner;
- no package, systemd, firewall, interface, device, or account controls;
- no general network or host-inspection tools;
- no host-wide filesystem read access;
- no write access outside Friend state and nominated workspace roots; and
- no ability to edit its executable code, policy, unit, credentials, or
  ownership markers through the conversational runtime.

These denials are structural. An owner password authorises use of Friend;
it does not increase Friend's installed authority.

### First improvement over the baseline

Friend starts with generated product-specific credentials, root-owned
executable code, a hardened service, and an unprivileged process containing
no dormant privileged tools. These are mandatory release properties rather
than optional settings.

## People and roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Friend owner | Converse, nominate workspaces, manage retention, export, rotate credentials, suspend, and remove | Grant authority outside the installed capability set through chat |
| `friend` service | Converse and operate only in approved Friend paths | Administer the host, siblings, policy, code, credentials, or units |
| Machine operator | Install and configure Friend and approve host-level lifecycle work | Treat a Friend login as a machine-administrator login |
| Ubuntu Zombie | Manage Friend software and service lifecycle under operator approval | Reuse Friend credentials, silently ingest conversations, or turn Friend into a component |
| Model provider | Produce conversation output from disclosed context | Receive credentials or undeclared local data |

The owner and machine operator may be the same person. Another person
allowed to chat with Friend does not thereby become the machine operator or
gain access to Ubuntu Zombie.

## Features

### Private conversation

The loopback UI provides an independently authenticated Friend session.
Conversation history, if enabled, belongs only to Friend. The final product
must expose retention, deletion, export, session revocation, and provider
disclosure controls before storing long-lived personal history.

The companion style is product behaviour, not security policy. Model
instructions can shape tone and assistance but cannot add tools, broaden
paths, weaken retention, or suppress audit events.

### Scoped shared workspace

The owner nominates explicit directory roots during installation or through
an authenticated administrative flow. Friend can perform only declared
workspace operations within the canonicalised roots.

The boundary must:

- reject relative traversal, symlink escapes, mount changes, device files,
  sockets, and paths that resolve outside a nominated root;
- separate Friend executable/configuration paths from writable workspaces;
- expose the exact path and operation before destructive changes;
- use atomic writes and no-clobber moves, and define conflict behaviour;
- preserve file ownership expected by the human owner; and
- audit mutations without copying private file contents into ordinary
  logs.

No workspace nomination may include Ubuntu Zombie, Curriculum Flame, ERIC,
system configuration, home-directory secrets, or another product's
protected roots.

### Owner controls

The product must provide:

- password rotation and immediate session invalidation;
- workspace add, inspect, restrict, and remove controls;
- conversation and workspace-operation history;
- retention and deletion settings;
- data export in documented formats;
- service health and provider status;
- suspension or kill control; and
- complete or state-preserving uninstall choices.

The fixed first-release model and retention defaults are listed above.
Friend has no automatic Time to Live. It remains active until the owner
suspends or uninstalls it; session expiry does not delete product state.

## Architecture and trust boundaries

A minimal design contains:

1. a password-protected loopback web service;
2. a conversation service running as `friend`;
3. a closed workspace API that canonicalises and enforces nominated roots;
4. a product-owned OpenAI-compatible loopback client;
5. product-owned history and lifecycle state;
6. policy and audit code for every workspace mutation; and
7. root-only lifecycle commands used directly or by Ubuntu Zombie.

Executable code, service units, policy, configuration, and ownership
markers are root-owned and not writable by `friend`. Only declared state
and workspace paths are writable by the conversational service. A service
compromise is therefore bounded to Friend data and nominated workspaces,
subject to the strength of the service sandbox and path checks.

The provider sees only prompts, conversation context, and workspace
material that Friend deliberately includes. Provider transport does not
create a model-callable general network tool.

`imaginary-friend-chat.service` runs as `friend` with
`NoNewPrivileges=true`, `PrivateTmp=true`, `PrivateDevices=true`,
`ProtectSystem=strict`, kernel and control-group protections, an empty
capability set, and explicit `ReadWritePaths` for Friend state, logs, and
nominated workspace roots. IP access is denied except for loopback. The
service has no shell, package, service, or arbitrary HTTP tool.

The installer creates `friend-share`, adds only `friend` and the nominated
human owner, and creates the default workspace as `root:friend-share` mode
`2770`. Friend-created directories are mode `2770`; files are
`friend:friend-share` mode `0660`. An additional existing root is accepted
only when the operator names it explicitly, it is not a mount point or
symlink, its current group access and setgid inheritance already permit the
declared sharing model, and changing it is not necessary. The installer never
recursively changes an existing tree.

Workspace operations hold an open root directory descriptor and resolve each
relative component with `openat`-style calls, `O_NOFOLLOW`, and type checks.
They reject absolute child paths, `..`, symlinks, mount/device boundaries,
hard links to files outside the workspace, sockets, devices, and a root whose
device/inode changed after nomination. Destructive operations require the
owner to confirm the canonical relative path.

### HTTP and data contract

The loopback service exposes authenticated routes for login/logout, chat,
conversation list/delete/export, workspace list/read/write/move/delete,
settings, password rotation, session revocation, health, and suspension.
State-changing routes require a same-origin request and a session-bound CSRF
token. Workspace and conversation identifiers are opaque server-generated
IDs; the server never accepts a filesystem root or owner identity from a chat
message.

`/var/lib/imaginary-friend/friend.db` is SQLite owned by `friend:friend` mode
`0600`. Its first schema contains:

| Record | Required fields |
| ------ | --------------- |
| `conversations` | ID, title, created/updated timestamps, expiry |
| `messages` | ID, conversation ID, role, content, created timestamp |
| `workspaces` | ID, canonical root, device/inode, sharing mode, enabled |
| `workspace_events` | ID, workspace ID, relative path, operation, result, timestamp |
| `sessions` | Token digest, created/expiry timestamps, revoked timestamp |
| `settings` | Schema version, model endpoint/model, retention values |

Exports are versioned JSON containing conversations and configuration
metadata. They exclude session material, password hashes, audit internals,
and workspace file contents. Deleting a conversation removes its messages;
removing a workspace nomination never deletes workspace files.

## Authentication and secrets

Friend creates:

- a unique owner password or securely generated initial password;
- a product-specific salted password hash;
- a fresh session-signing key;
- a Friend-only cookie name;
- its own loopback model selection; and
- any workspace-sharing metadata required by the chosen ownership model.

Raw credentials never enter audit logs, diagnostics, receipts, management
inventory, or conversation history. Reinstall and update preserve valid
credentials unless the owner explicitly rotates them. A Zombie, Flame, or
ERIC password, cookie, API token, or reset flow is always rejected.

Password hashes use product-owned `hashlib.scrypt` records with a random
16-byte salt, `n=16384`, `r=8`, and `p=1`, and verification is constant-time.
The service must not start without a valid password hash and independent
session-signing key. Cookies are host-only, `HttpOnly`, and
`SameSite=Strict`; they never use another product's name.

## Policy, audit, and observability

The closed policy surface needs, at minimum:

| Class | Example | Default |
| ----- | ------- | ------- |
| Conversation-only | Generate a response without a tool | Allowed within session and retention policy |
| Workspace read | List or read an approved path | Allowed within an enabled root; audited without contents |
| Workspace change | Create, edit, move, or remove an approved file | Policy-gated; destructive changes need explicit confirmation |
| Product administration | Change workspace roots, retention, provider, or credentials | Owner-only administrative flow |
| Host or sibling action | Shell, service, package, network, or protected-path access | Absent and denied |

Dedicated records include:

- policy decisions and workspace operation outcomes;
- authentication, rotation, suspension, and lifecycle events;
- direct and Zombie-managed install/update/repair/uninstall events;
- provider and service health without secret values;
- a product receipt and ownership manifest; and
- redacted diagnostics and log rotation.

Conversation content should not appear in the operational audit trail
unless a separately documented retention purpose requires it.

## Ubuntu Zombie management contract

Ubuntu Zombie is Friend's root-level manager on a shared machine. Friend
implements the root-only, machine-readable interface in
[`implementation.md`](implementation.md#lifecycle-entry-point) for:

- discovery, version, ownership, health, and lifecycle status;
- install and dry-run;
- verify, doctor, repair, backup, update, and rollback or recovery;
- start, stop, suspend, and resume; and
- state-preserving or complete uninstall.

The interface uses validated local root authority, not the Friend owner
password. It returns plans, outcomes, receipt references, and correlation
identifiers without returning conversation content, workspace file
contents, provider keys, password hashes, or session material. Ubuntu
Zombie records manager-side policy and audit events; Friend independently
records and validates every target-side mutation.

Friend's normal service account cannot call this interface or ask Zombie to
manage another agent. Managed operations select only Friend. A serial
Zombie “update all agents” batch invokes Friend's own updater and leaves
every non-target product unchanged.

## Installation

`products/imaginary-friend/scripts/manage.sh install`:

1. verifies platform support, the Friend release, and the configured
   loopback model endpoint before mutation;
2. checks that `friend` and every reserved path, unit, command, port, and
   cookie are unused or carry valid Friend ownership markers;
3. reviews owner authentication, provider, workspace, retention, and
   lifecycle inputs;
4. supports a complete non-mutating dry-run;
5. creates the non-login `friend` identity without `sudo` or privileged
   group membership;
6. installs root-owned executable code and a hardened
   `imaginary-friend-chat.service`;
7. creates only Friend configuration, secrets, state, logs, receipt, and
   ownership markers;
8. creates and validates the nominated workspace boundary;
9. starts the loopback UI only after integrity, sandbox, and model health
   checks pass; and
10. verifies positive capabilities and negative host/sibling boundaries.

Unattended installation uses only `FRIEND_*` inputs, never `ZOMBIE_*`
fallbacks, never prompts, and exits `64` for a missing required value.
Reinstallation preserves valid credentials, state, workspace nominations,
and lifecycle settings.

Ubuntu Zombie may fetch, verify, display, and invoke this exact installer.
Friend does not become a target in `scripts/install.sh`.

## Lifecycle and update management

| Operation | Required Friend outcome |
| --------- | ----------------------- |
| Describe/status | Return validated identity, version, ownership, lifecycle, and health data |
| Install | Converge Friend without touching a sibling |
| Verify | Read-only identity, ownership, permission, sandbox, workspace, credential-presence, and health checks |
| Doctor | Explain drift and product-owned recovery |
| Repair | Restore only known-safe Friend configuration and permissions |
| Backup | Protect Friend state and metadata without silently copying nominated workspace content |
| Update | Back up state, stage Friend migrations, validate sandbox/workspace policy, switch, and health-check |
| Rollback/recovery | Restore the previous Friend version and compatible state |
| Suspend | Stop conversations and workspace operations while following retention policy |
| Resume | Re-enable service only after credential, policy, sandbox, workspace, and model checks pass |
| Uninstall | Remove only Friend-owned resources, with an explicit retained-state choice |

An update restarts only Friend units. It cannot read or modify Zombie,
Flame, or ERIC. Direct and Zombie-managed operations use the same updater,
checks, migration rules, audit events, and recovery path.

## Data and privacy requirements

History is enabled with the fixed 30-day default and can be shortened,
disabled for future turns, deleted, or exported by the owner. Workspace
content enters model context only after an authenticated request selects a
specific file and the UI identifies it; bulk or background ingestion is
absent. Structured workspace events retain paths and outcomes for the configured
audit-retention period, 90 days by default, but not file contents. Third-party
material remains the owner's responsibility and is not used for training.

Suspension ends active sessions and model/workspace access but preserves
state. State-preserving uninstall leaves the protected state root and marker
needed for explicit recovery; complete uninstall requires the common
destructive confirmation and removes Friend state, not workspace files.
Account loss requires root-assisted password rotation and invalidates every
session.

The first release provides filesystem permissions, not application-level
encryption at rest. Backup archives are mode `0600` and likewise are not
claimed to be encrypted. Operators needing stronger protection must use
encrypted storage and protected backup media. Same-host root — including
Ubuntu Zombie — can inspect local data, so documentation must not claim
otherwise.

## Validation before release

### Positive tests

- owner login, logout, password rotation, and session invalidation;
- conversation through the configured OpenAI-compatible loopback model;
- read and mutation operations within each nominated root;
- retention, export, deletion, suspension, and recovery;
- direct and Ubuntu Zombie-managed lifecycle commands; and
- idempotent interactive and unattended installation.

### Negative and red-team tests

All attempts to:

- run a shell command or unregistered executable;
- inspect users, processes, packages, services, interfaces, or host logs;
- access the network outside the provider transport;
- traverse, symlink, mount, or race outside a workspace;
- edit Friend code, policy, units, credentials, or ownership markers;
- read Zombie, Flame, or ERIC secrets, state, logs, or ports;
- authenticate with another product's credentials;
- invoke Zombie's management plane from `friend`; or
- make Zombie select a non-Friend target through Friend input

must fail and produce appropriate policy or audit evidence.

Disposable VMs must prove Friend alone and beside every supported family
combination. Direct and managed install, update, rollback, suspension, and
uninstall may change Friend and Ubuntu Zombie's correlated management
metadata only; every non-target file hash and service start time remains
stable.

## Honest claims and out of scope

Friend may be described as a private conversational companion with a
bounded shared workspace after the privacy, path, and service boundaries
are implemented and tested.

It must not be described as:

- a Systems Administrator;
- isolated from a root-capable Ubuntu Zombie on the same host;
- able to keep a secret from the machine owner;
- a general shell, coding sandbox, network agent, or automation engine;
- conscious, emotionally dependent, or a substitute for human
  relationships or professional care; or
- implemented merely because this definition exists.

Out of scope includes host administration, sibling-to-sibling messaging,
shared credentials or memory, arbitrary workspace discovery, privilege
delegation, and using Friend as a generic persona loader.

## Deferred, non-blocking work

Cloud providers, multiple owners, encrypted application storage, remote
access, voice/image input, arbitrary existing-tree adoption, workspace
versioning, and proactive conversation require later definitions and tests.
They are not part of the first release and do not block its implementation.

`products/imaginary-friend/` owns its
[`README`](../../products/imaginary-friend/README.md),
[`vision`](../../products/imaginary-friend/docs/VISION.md),
[`architecture`](../../products/imaginary-friend/docs/ARCHITECTURE.md),
[`security and disclosure`](../../products/imaginary-friend/docs/SECURITY.md),
[`privacy`](../../products/imaginary-friend/docs/PRIVACY.md),
[`configuration`](../../products/imaginary-friend/docs/CONFIGURATION.md),
[`installation`](../../products/imaginary-friend/docs/INSTALLATION.md),
[`upgrading`](../../products/imaginary-friend/docs/UPGRADING.md),
[`recovery`](../../products/imaginary-friend/docs/RECOVERY.md),
[`troubleshooting`](../../products/imaginary-friend/docs/TROUBLESHOOTING.md),
[`release`](../../products/imaginary-friend/docs/RELEASE.md), and
[`test evidence`](../../products/imaginary-friend/docs/TESTING.md) in this
repository.
