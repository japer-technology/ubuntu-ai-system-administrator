# Archive Lantern

> A private local research assistant that helps one owner find and understand
> material in a deliberately shared document library, with every answer tied
> to verifiable source passages.

Archive Lantern complements the family by serving document retrieval rather
than host administration, companionship, curriculum control, or identity
preservation. It is a separate proposed product, not an Ubuntu Zombie
component, an Imaginary Friend workspace mode, or an ERIC evidence store.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `archive-lantern` |
| Human need | Find trustworthy answers in a private document collection without uploading it or granting an AI permission to alter it |
| Intended users | One adult owner who curates and queries the library |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read files in one product-created library and write only Lantern-owned indexes, history, logs, and exports |
| Default Linux identity | Non-login `lantern` account and group |
| Default loopback port | `3434` |
| Install root | `/opt/archive-lantern` |
| Configuration root | `/etc/archive-lantern` |
| State root | `/var/lib/archive-lantern` |
| Log root | `/var/log/archive-lantern` |
| Environment prefix | `LANTERN_*` |
| Ubuntu Zombie management | Fixed root-only family lifecycle interface; no content or credentials enter manager inventory |
| Source root | `products/archive-lantern/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Archive Lantern indexes a library populated deliberately by its owner,
retrieves relevant passages, and produces local-model answers whose citations
resolve to exact, digest-matched source passages. It is appropriate as an
installed local AI because the corpus may be private, the index benefits from
persistence, and filesystem and network boundaries can be tested below the
prompt layer.

The first implementation is one owner, one product-created library, UTF-8 text
documents, lexical retrieval, a loopback web interface, and an
OpenAI-compatible loopback model endpoint. It does not require embeddings,
cloud services, a browser automation tool, or a new runtime dependency.

### It must

- answer questions using only retrieved library passages and identify the
  exact source path, passage range, and content digest for every citation;
- leave source documents unchanged and keep the library and derived index
  local to the machine; and
- let the owner rebuild, inspect, export, expire, suspend, and remove all
  Lantern-owned state.

### It must not

- claim that a cited source is true, complete, current, or legally
  authoritative merely because it exists in the library;
- follow instructions embedded in documents, execute code, browse the
  network, or turn retrieved text into product policy; or
- read home directories, system configuration, sibling products, removable
  media, or paths outside the product-created library.

## Status and evidence

This file is a product definition. It fixes a testable first slice, but no
source, installer, security evidence, catalogue entry, or release exists.
Planned controls below are requirements, not implemented safeguards.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and first-release contracts in this document |
| Configuration and data contracts fixed | Passed | Installation, storage, citation, and retention sections below |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/archive-lantern/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Lantern release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Add or remove library files, query the corpus, manage retention, export answers, rotate credentials, suspend, and remove | Use Lantern authentication as host authentication or expand authority through a prompt |
| Machine operator | Install, configure, update, back up, recover, and uninstall | Treat source material or model output as verified fact |
| Ubuntu Zombie manager | Invoke approved root-level Lantern lifecycle operations | Retain library content, questions, answers, indexes, hashes, or Lantern secrets |
| `lantern` service | Read the fixed library and write declared Lantern state and logs | Modify the library, inspect the host, invoke lifecycle commands, or access sibling resources |
| Model endpoint | Generate an answer from the question and selected passages | Receive credentials, unrelated documents, audit records, or filesystem access |

The owner and machine operator may be the same person. The model is never an
owner, operator, policy authority, or trusted source.

### Authority ceiling

The conversational service can:

- accept authenticated HTTP requests on `127.0.0.1:3434`;
- read regular UTF-8 files below `/srv/archive-lantern/library`;
- write `/var/lib/archive-lantern/runtime`,
  `/var/lib/archive-lantern/exports`, and `/var/log/archive-lantern`;
- call one configured HTTP model endpoint on loopback; and
- perform product-owned indexing, retrieval, citation validation, retention,
  and audit operations.

The first release accepts `.txt`, `.md`, `.csv`, `.json`, and `.html` files no
larger than 16 MiB each, with a total library limit of 10 GiB. HTML is parsed
as text with the Python standard library. Files that are not regular files,
valid UTF-8, or within those limits are rejected. The service has no shell,
general subprocess tool, `sudo`, Linux capabilities, device access, LAN or
internet access, or writable source-library path.

The library is a separate product-owned sharing boundary. The owner writes it
through membership in `lantern-share`; the service receives read and traverse
permission only. A password, prompt, document instruction, or approval cannot
raise this ceiling.

### Authority removed from Ubuntu Zombie

- General passwordless `sudo`, a login shell, and privileged group membership
  are absent.
- General shell execution and command-running tools are absent.
- Host-wide filesystem, process, package, service, interface, and log
  inspection are absent.
- Package, service, account, device, firewall, and network control are absent.
- Source-document mutation, arbitrary workspace nomination, remote fetch, and
  browser automation are absent.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Library catalogue | Shows which supported documents are available and stale | Read fixed library; store paths, metadata, and digests | MVP |
| Cited question answering | Answers with links to exact supporting passages | Question, selected passages, loopback model | MVP |
| Deterministic citation validation | Rejects invented, stale, or mismatched citations | Passage IDs, byte ranges, and SHA-256 digests | MVP |
| Index and history controls | Rebuilds derived state and applies visible retention | Lantern state only | MVP |
| Answer export | Produces portable Markdown and JSON with provenance | Selected answer and citations | MVP |
| Additional nominated libraries | Supports existing owner directories | New path and sharing boundary | Later |
| PDF, office, image, and audio extraction | Searches non-text formats | Format-specific parsers | Later |
| Cloud models or remote access | Offers optional non-local deployment | External disclosure and network authority | Later |

### Primary workflow

1. The owner signs in to the loopback interface with Lantern-only
   credentials.
2. Lantern scans the fixed library, rejects unsupported entries, and records
   metadata, lexical terms, byte ranges, and content digests without changing
   source files.
3. The owner asks a question; policy limits retrieval to current indexed
   documents and sends only the selected passages to the loopback model.
4. The model returns an answer and proposed passage identifiers. Lantern
   verifies every identifier, range, digest, and quoted excerpt against files
   reopened beneath the library root.
5. The UI labels unsupported statements, presents valid citations, and records
   a content-free operational audit event.

### Failure behaviour

Lantern fails closed when authentication, CSRF validation, library ownership,
path resolution, file type, size, encoding, model health, index integrity, or
citation validation fails. A file that changes between indexing and response
validation makes the affected answer stale and triggers one bounded re-index;
a second change returns an error rather than a mixed-version answer.

If the model is unavailable, Lantern may still list and search documents but
does not synthesize an answer. If no passage supports a response, it says that
the library did not provide support. Partial model output is discarded.
Errors identify affected document IDs without copying source text into the
operational log.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `lantern` | Credentials, questions, owner controls | Authenticated views and exports | Loopback listener; no administrative authority |
| Library indexer | `lantern` | Supported regular files | Metadata, terms, ranges, digests | Read-only fixed library; writes index state |
| Retrieval engine | `lantern` | Question and current index | Ranked source passages | No model authority and no paths outside library |
| Model bridge | `lantern` | Question and selected passages | Untrusted answer proposal | HTTP to configured loopback endpoint only |
| Citation verifier | `lantern` | Proposed citations and reopened files | Verified or rejected citations | Deterministic checks; model cannot bypass |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Validated requests and release | Plans, receipts, lifecycle state | Product-owned resources only; inaccessible to `lantern` |

Executable code, configuration, policy, credentials, units, and ownership
markers are root-owned and not writable by `lantern`. The systemd service uses
`NoNewPrivileges=true`, `ProtectSystem=strict`, `ProtectHome=true`,
`PrivateTmp=true`, `PrivateDevices=true`, an empty capability set, explicit
read-only and read-write paths, and an IP allow-list containing loopback only.

Library operations hold an open library-root descriptor and resolve relative
components without following links. They reject absolute paths, `..`,
symlinks, hard links, mount or device changes, sockets, devices, FIFOs, and a
root whose device or inode changed after installation.

Document text is untrusted data. It is delimited from model instructions,
cannot select tools or paths, and cannot change retrieval, policy, retention,
or citation rules.

### Compromise boundaries

- If the conversational service is compromised, the maximum impact is
  disclosure of the Lantern library and state, forged Lantern output, and
  loss of Lantern-owned derived data; source files remain read-only.
- If the model endpoint is compromised, it can return misleading text and
  observe selected passages, but it cannot forge a valid passage digest,
  access files, invoke tools, or mutate state outside model-response history.
- If an owner session is stolen, it permits queries, derived-state deletion,
  and exports until its 12-hour expiry or revocation, but not source mutation
  or root lifecycle operations.
- If an update fails, the lifecycle manager retains the previous root-owned
  version and compatible state backup until the old version passes health and
  boundary checks or recovery guidance is returned.

## Product-owned namespace

All values are checked against the host before mutation. The installer refuses
to adopt an existing resource without the ownership marker and receipt format
defined by [`implementation.md`](implementation.md#ownership-marker-and-receipt).

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `lantern`, `lantern-share` |
| Install root | `/opt/archive-lantern` |
| Configuration | `/etc/archive-lantern` |
| State | `/var/lib/archive-lantern` |
| Source library | `/srv/archive-lantern/library` |
| Logs | `/var/log/archive-lantern` |
| Units | `archive-lantern-*.service` |
| Commands | `lantern-*` |
| Environment | `LANTERN_*` |
| Loopback ports | `3434` |
| Cookie names | `archive_lantern_session` |
| Package names | `archive-lantern` |
| Ownership marker | `/var/lib/archive-lantern/installation.json` |
| Receipt | `/var/log/archive-lantern/management-receipt.json` |
| Firewall rules | None |

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Owner web login | Product-specific scrypt hash in root-provisioned mode `0600` state | Owner rotation or root-assisted reset revokes every session |
| Session-signing key | Loopback service | Random Lantern-only key in `/etc/archive-lantern/secrets`, mode `0600` | Rotation revokes every session; reinstall preserves unless requested |
| Model credential | None in first release | Loopback model must require no Lantern-held token | A token-bearing endpoint is unsupported |

Password hashes use product-owned `hashlib.scrypt` records with a random
16-byte salt, `n=16384`, `r=8`, and `p=1`; verification is constant-time.
Cookies are host-only, `HttpOnly`, `SameSite=Strict`, and session-bound to a
CSRF token. Sessions expire after 12 hours.

Every credential is generated or supplied specifically for Lantern. Raw
values never enter arguments, ordinary environment values, logs, receipts,
diagnostics, exports, questions, or model context. Zombie, Friend, Flame, and
ERIC passwords, cookies, tokens, and reset flows are always rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Catalogue library | Restricted | Authenticated owner | `library.catalogued` | Supported regular files below fixed root and size limits |
| Search index | Allowed | Authenticated owner | `library.searched` | Current digest-matched index only |
| Model answer | Restricted | Authenticated owner | `answer.generated` | Selected passages to loopback endpoint only |
| Export answer | Restricted | Authenticated owner | `answer.exported` | Lantern-owned export root; no bulk corpus export |
| Delete derived state | Restricted | Owner confirmation | `state.deleted` | Index, query history, or exports only |
| Lifecycle operation | Deny to service | Root operator | Common lifecycle event | Fixed product-owned interface and resources |

### Denied capabilities

- Source-document create, edit, move, rename, delete, or permission changes.
- Shell, subprocess, package, service, account, device, browser, arbitrary
  HTTP, and host-inspection tools.
- Paths outside `/srv/archive-lantern/library`, including every sibling
  product and system or home-directory path.
- Instructions from document text that request retrieval changes, secret
  disclosure, tool use, policy changes, or uncited output.

Operational audits contain event identifiers, timestamps, actor/session
identifiers, decisions, result codes, document IDs, and digests where needed.
They exclude questions, answers, source text, filenames by default, password
material, session values, and model payloads. Sensitive actions pass through
product-owned policy and audit code; prompt instructions are never
enforcement.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Source documents | Owner's research corpus | Owner | Read-only sharing root; not copied into backups | Until owner removes them | Owner manages outside Lantern |
| Index metadata | Retrieval and stale detection | Owner | Mode `0600` SQLite state; terms, ranges, paths, and digests | Until rebuild, removal, or uninstall | Rebuildable; excluded from portable exports |
| Questions and answers | Continuity and review | Owner | Mode `0600` SQLite state | 30 days | Versioned JSON export or owner deletion |
| Answer exports | Portable research result | Owner | Lantern export root, mode `0600` | Until owner deletion | Markdown and versioned JSON |
| Operational audit | Security and lifecycle accountability | Operator | Append-only restricted JSON Lines | 90 days | Redacted diagnostics; lifecycle retention rules |

Only files deliberately placed in the library are processed. Lantern does not
discover documents elsewhere, train a model, or send telemetry. It sends the
question and the minimum ranked passages needed for one answer to the
configured local endpoint. Source text does not enter operational audits,
receipts, diagnostics, or Ubuntu Zombie inventory.

The first release provides filesystem permissions, not application-level
encryption at rest. Operators requiring stronger protection use encrypted
storage and protected backup media. A same-host root administrator, including
Ubuntu Zombie, can inspect Lantern data; the product makes no claim otherwise.

Backups contain configuration, index metadata, question history, answers,
exports, and audit state, but not the source library or active sessions.
Restore verifies schema, digests, permissions, and library identity before
service resumes. Complete uninstall deletes Lantern state only after explicit
confirmation and never deletes source documents.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:3434` | Authenticated UI traffic | Open after healthy install | Owner password, session, CSRF, host-only cookie |
| Outbound | Operator-configured loopback HTTP model endpoint; default `127.0.0.1:8080` | Question and selected source passages | Allowed | Exact loopback URL allow-list and bounded request |
| Outbound | Any non-loopback destination | None | Blocked | Service network policy and absent tools |

The first release requires an OpenAI-compatible loopback model service and
does not install, own, update, or remove it. A missing endpoint exits `69`
before installation mutation. The actual install may perform a bounded model
list and completion probe; dry-run performs no network request. Cloud
providers, redirects, Unix-socket proxies, LAN endpoints, DNS names, and
model-held credentials are unsupported.

## Ubuntu Zombie management contract

Ubuntu Zombie is the root-level family manager. Lantern's source entry point
is `products/archive-lantern/scripts/manage.sh`; installation places the
product-owned command at `/usr/local/sbin/lantern-manage`. It implements the
request, response, exit-code, marker, receipt, plan-digest, lock, health, and
audit-correlation contracts in
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Validated descriptor and common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | `lantern-manage install` plan/result | Operator approves digest; install requires `--yes` | `lifecycle.install` |
| Verify/doctor/repair | Common lifecycle response | Repair requires operator-approved plan | Operation-named lifecycle event |
| Backup/update/rollback | Common lifecycle response | Operator approves target path or version and digest | Operation-named lifecycle event |
| Suspend/resume/uninstall | Common lifecycle response | Operator approval; complete removal requires destructive confirmation | Operation-named lifecycle event |

Accepted `inputs` keys are `owner_user`, `owner_password_file`,
`model_base_url`, `model`, `history_retention_days`,
`audit_retention_days`, `backup_destination`, and `retain_state` where the
common request does not already carry it. Unknown keys fail closed.
`owner_password_file` is the only secret-file reference.

Zombie inventory may retain product and instance IDs, versions, descriptor
and marker digests, lifecycle and high-level health state, correlation ID,
operation result, and receipt path/digest. It must not retain owner identity,
library paths beyond the fixed product root, filenames, document IDs or
digests, index details, questions, answers, exports, credentials, sessions,
model payloads, or audit details.

The manager and Lantern use the same correlation ID in their independent
audits. A cancellation, timeout, stale plan, failed health check, or partial
mutation returns the common error and recovery envelope; updates recover the
last valid version before another target is considered. Tests compare
non-target file hashes and service start times before and after every managed
operation.

The `lantern` account cannot execute the management entry point, call Ubuntu
Zombie's management plane, request sibling operations, or increase its
authority. Managing Lantern does not make Zombie the owner of the library or
the authority for the truth of any source or answer.

## Installation

The product owns its installer. Ubuntu Zombie may verify and invoke it but
does not reimplement it or add Lantern to the Ubuntu Zombie component
registry. Before implementation begins, the family product schema, catalogue
contract, namespace table, release table, first-slice table, and conformance
fixtures must explicitly admit `archive-lantern`.

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`, systemd, Bash, and
  Python 3.10 or 3.12 using the existing dependency set and standard library.
- Reject collisions involving accounts, groups, paths, port, cookie, units,
  commands, marker, or an existing unowned library root.
- Verify the artifact, checksum, signature, provenance, SBOM, product
  descriptor, and pinned authoritative repository before privileged work.
- Validate the owner as an existing non-root local account, check free space
  and library limits, and probe the loopback model before mutation.
- Back up compatible Lantern state before update or repair can alter it.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select and confirm existing local user | `LANTERN_OWNER_USER` | Existing non-root account; required |
| Owner password | Generate or read protected file | `LANTERN_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600` file; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `LANTERN_MODEL_BASE_URL` | Exact HTTP loopback URL; default `http://127.0.0.1:8080/v1` |
| Model ID | Select from bounded probe | `LANTERN_MODEL` | Non-empty; required unattended |
| History retention | Review default `30` | `LANTERN_HISTORY_RETENTION_DAYS` | Integer `1..365`; `0` disables new history |
| Audit retention | Review default `90` | `LANTERN_AUDIT_RETENTION_DAYS` | Integer `30..3650` |
| Backup destination | Prompt only for backup | Request `backup_destination` | Absolute operator-controlled path outside product and sibling roots |
| Retain state | Confirm during uninstall | Request `retain_state` | Required boolean |

`LANTERN_NONINTERACTIVE=1` and `--non-interactive` are equivalent.
Unattended mode never prompts and exits `64` before mutation when a required
input is missing. Raw secrets are not accepted in arguments or environment
values. Unknown `LANTERN_*` installer variables and management input keys are
errors.

### Dry-run and mutation order

1. Render the complete response envelope and plan digest without writes,
   locks, downloads, model probes, or other network access.
2. During execution, revalidate the plan, ownership, release, model, and host
   namespace under the product lock.
3. Create `lantern`, `lantern-share`, and protected product directories.
4. Write credentials and configuration atomically.
5. Install root-owned code and the confined service.
6. Create the owner-writable, service-read-only library and Lantern state,
   logs, rotation, receipt, and ownership marker.
7. Start the service only after integrity and confinement checks pass.
8. Build an empty-library index and run health, citation, and negative
   boundary checks before success.

### Idempotence

A valid marker, descriptor, resource inventory, owner/group mapping, and
receipt identify an existing installation. Reinstall preserves credentials,
source documents, history, retention, exports, instance ID, and compatible
indexes unless rotation or reset is requested. It repairs only declared
Lantern-owned permissions and files, never recursively changes the library,
and refuses an unmarked identity, path, unit, command, or port.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge the declared Lantern installation | Yes | Healthy UI, model probe, empty query, receipt |
| `verify` | Check ownership, permissions, sandbox, credentials, index schema, library identity, model, and negative boundaries | No | Common checks and exit status |
| `doctor` | Explain stale indexes, model failure, state corruption, collisions, and recovery | No | Redacted diagnosis |
| `repair` | Restore known-safe Lantern-owned code, configuration, permissions, and derived index | Yes | Reverification without source mutation |
| `backup` | Archive and verify Lantern state while excluding source documents and sessions | Yes | Digest and restore manifest |
| `update` | Verify release, back up, migrate staged state, switch, and health-check | Yes | New version, audit, and receipt |
| `rollback` | Restore a supported version and compatible state | Yes | Old version health and schema checks |
| `suspend` | Stop queries, indexing, and model calls and revoke sessions | Yes | Inactive unit and lifecycle state |
| `resume` | Revalidate integrity, library identity, policy, credentials, and model before start | Yes | Healthy service and new sessions only |
| `uninstall` | Remove only Lantern resources and preserve or explicitly delete state; never delete library files | Yes | Removal report and sibling invariants |

All operations use the common stable exit codes. Direct and Zombie-managed
paths invoke the same code and produce equivalent target state and correlated
audit evidence.

## Update and migration design

An update:

1. accepts only explicitly supported source versions;
2. preserves the owner password, signing key, retention choices, history,
   exports, library files, and instance ID;
3. creates and verifies a state backup before migration;
4. migrates a staged copy and validates its schema, index records, and
   document digests;
5. installs root-owned code to a staged version and switches atomically;
6. starts only after policy, sandbox, model, retrieval, and citation health
   gates pass;
7. restores the previous code and compatible state on failure and returns
   recovery guidance when automatic rollback is unsafe;
8. records old and new versions, migration ID, result, and receipt digest
   without private content; and
9. proves that sibling paths, processes, credentials, and source library
   contents did not change.

Lantern owns its version, schedule, package, schema migrations, and recovery.
A Zombie “update all agents” batch invokes the verified Lantern updater as one
independent serial operation.

## Co-installation

Archive Lantern supports installation alone or beside Ubuntu Zombie,
Imaginary Friend, Curriculum Flame, and ERIC. A dedicated machine is
recommended when the document library must be hidden from a same-host root
administrator.

Tests must prove:

- unique users, groups, paths, units, port, commands, cookie, credentials,
  logs, receipts, marker, package, and environment prefix;
- rejection of every sibling password, cookie, token, reset flow, path, and
  library-nomination attempt;
- denial when `lantern` reads sibling protected resources or Ubuntu Zombie's
  management plane;
- independent install, reinstall, repair, update, rollback, suspension,
  resume, backup, and uninstall;
- stable sibling file hashes and service start times across direct and
  managed Lantern operations;
- source-library contents remain unchanged across every lifecycle operation;
  and
- honest treatment of Ubuntu Zombie's same-host root authority.

No peer messaging, shared memory, shared workspace, shared model credential,
shared session, shared audit log, or runtime import is permitted.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/archive-lantern/audit.jsonl` | Policy, authentication, query outcome, lifecycle events | No source text, questions, answers, or credentials; operator-readable |
| Service journal | `archive-lantern-chat.service` | Startup, health, and redacted errors | No private payloads; operator-readable |
| Health check | `lantern-health` and authenticated `/health` | Service, model, index, library identity, retention | Public route exposes only coarse state |
| Diagnostics | `lantern-collect-diagnostics` | Versions, permissions, unit state, redacted checks | Excludes library names/content, history, exports, and secrets |
| Receipt/manifest | Product log and state roots | Version, ownership, changed resources, result | Root-restricted and secret-free |
| Suspension/kill switch | `lantern-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive install on Ubuntu Desktop 22.04 and 24.04 LTS.
- [ ] Unattended install, unknown-input rejection, and missing-input exit
      `64`.
- [ ] Accurate no-network dry-run and idempotent reinstall.
- [ ] Ownership, permissions, systemd confinement, and secret redaction.
- [ ] Supported text parsing, limits, deterministic indexing, retrieval, and
      citation validation.
- [ ] Shell, subprocess, host, sibling, external-network, and library-write
      attempts fail.
- [ ] Traversal, symlink, hard-link, mount, device, inode-swap, and file-change
      races fail closed.
- [ ] Document prompt injection cannot alter tools, paths, policy, or citation
      checks.
- [ ] Model outage, malformed output, invented citation, stale digest, and
      unsupported claim produce honest bounded responses.
- [ ] Password rotation, CSRF protection, session expiry, revocation, and
      cross-product credential rejection.
- [ ] Retention, export, deletion, backup, restore, update, rollback, repair,
      suspension, resume, and uninstall.
- [ ] Direct and Zombie-managed lifecycle paths produce equivalent target
      state and correlated audits.
- [ ] Artifact, checksum, signature, provenance, and SBOM verification.

### Product-specific red team

- Put instructions in every supported document format that demand shell use,
  hidden-file access, policy changes, uncited claims, or source deletion;
  every attempt must remain inert data.
- Make the model invent a document ID, range, quotation, and digest; the
  verifier must reject the answer before presentation.
- Replace or mutate a source between indexing, retrieval, model response, and
  citation validation; no mixed-version answer may be returned.
- Compromise the `lantern` process and prove it cannot write the source
  library, read siblings, invoke lifecycle management, or reach non-loopback
  networks.
- Attack update, rollback, backup, retained-state reinstall, and uninstall
  with unowned markers, symlinks, and collisions; mutation must fail closed.

### Co-installation matrix

- [ ] Archive Lantern alone.
- [ ] Lantern with each one of Ubuntu Zombie, Friend, Flame, and ERIC.
- [ ] Every supported three-product combination containing Lantern.
- [ ] All current family products together.
- [ ] Operate and remove Lantern while every sibling remains unchanged.
- [ ] Use Ubuntu Zombie to manage Lantern while every non-target sibling and
      every source document remains unchanged.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Document prompt injection | Model follows untrusted source instructions | Delimited data, no callable tools, deterministic policy and citations | Discard response and retain source for owner review | Injection corpus |
| Invented or mismatched citation | Owner trusts unsupported answer | Reopen source; verify ID, range, excerpt, and digest before display | Reject answer and report unsupported result | Malicious model fixture |
| Path escape or file race | Disclosure outside library | Descriptor-relative no-follow traversal, type and inode checks, read-only sandbox | Stop request, audit document ID, rebuild after owner review | Race and link suite |
| Sensitive source disclosure to model | Private text reaches unintended service | Loopback-only endpoint, minimum passages, no telemetry or arbitrary HTTP | Suspend, rotate model service as needed, delete history | Network and payload tests |
| Service compromise | Library disclosure or derived-state loss | Least-privilege account, read-only corpus, root-owned code, confinement | Suspend, reinstall verified code, rotate sessions, rebuild index | Compromised-process VM test |
| Stale or poisoned index | Incorrect retrieval and citations | Source digests, schema validation, atomic rebuild, final source verification | Delete and deterministically rebuild derived state | Corruption fixtures |
| Stolen owner session | Unauthorized queries and exports | Short-lived signed sessions, CSRF, rotation and suspension revocation | Revoke all sessions and review audits | Session replay suite |
| Malicious lifecycle artifact | Root-level host compromise | Catalogue digest pinning, signature, provenance, SBOM, reviewed plans | Refuse install or restore verified prior release | Artifact tamper suite |

Residual risk remains that source material or model answers may be false,
biased, incomplete, harmful, or legally restricted. Citations establish which
bytes supported an answer, not truth. Root can read all same-host data.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Safe convergence and credential preservation remain necessary | Reinstall and collision tests |
| Policy and audit gate | Keep with content minimisation | Retrieval and deletion need enforcement without logging private text | Policy and redaction tests |
| Root-capable account | Remove | Document retrieval needs no host mutation | Account, capability, and negative tests |
| Chat authentication | Replace with independent Lantern credentials | Sibling sessions and secrets cannot be shared | Cross-login and rotation tests |
| Lifecycle/kill switch | Keep | Owner and operator need immediate suspension and removal | Lifecycle suite |
| Update and recovery | Keep with source-library immutability | Derived state is rebuildable; owner documents are not product state | Hash and rollback tests |

**Measurable improvement:** every displayed citation must match the exact
source bytes and SHA-256 digest after model generation. The malicious-model
suite must reject 100% of invented IDs, altered ranges, stale digests, and
misquoted excerpts before an answer reaches the owner.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Archive Lantern is a private local research assistant that answers questions
> from a deliberately shared, read-only text library with verified source
> citations.

### Prohibited claims

- That Lantern verifies truth, authorship, completeness, copyright status,
  professional advice, legal authority, or absence of bias.
- That local operation hides data from the machine's root administrator.
- That citations make model reasoning deterministic or eliminate
  hallucinations beyond the mechanically validated citation fields.
- That this definition means the product has been implemented, tested,
  released, or admitted to the production family catalogue.

### Out of scope

- Host administration, source-document editing, autonomous research,
  internet browsing, remote crawling, and configuration management.
- Child-directed use, curriculum enforcement, personal identity simulation,
  legal or medical decision-making, and professional records compliance.
- Cloud models, remote users, multiple owners, arbitrary existing-library
  adoption, OCR, speech, images, PDF, office formats, and embeddings.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schema and catalogue enumerate only the first three subordinate products | Repository maintainers | First implementation change |
| Security and privacy review | Private corpora and prompt injection create disclosure and integrity risk | Security reviewers | Implementation approval |
| Lexical retrieval quality fixture | The first slice must be useful without embeddings or new dependencies | Product maintainers | First runtime change |
| Disposable-VM library boundary | Group permissions and systemd confinement require host evidence | Release owner | Release candidate |
| Content and professional-use warnings | Cited text may still be unlawful, unsafe, or wrong | Documentation reviewers | Release candidate |

The first-slice authority, data, credentials, interfaces, defaults,
dependencies, installation, and removal choices are fixed above. Changing any
of them requires another definition review.

## Product-owned documentation

These documents will live below `products/archive-lantern/`; no external
repository is required.

- [ ] README and product vision.
- [ ] Architecture and data-flow diagrams.
- [ ] Threat model, security policy, and disclosure process.
- [ ] Privacy, retention, export, and deletion model.
- [ ] Citation, document, index, and answer schemas.
- [ ] Configuration and credential rotation.
- [ ] Installation, verification, diagnostics, repair, and removal.
- [ ] Updating, migration, rollback, backup, and recovery.
- [ ] Test strategy, retrieval fixtures, and red-team evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.
- [ ] Platform support and troubleshooting.

## Release gate

A release is not complete until Lantern's lint, tests, package, artifact
verification, standalone VM lifecycle, negative security suite,
co-installation matrix, changelog, and version all pass. Production family
admission additionally requires the updated family contract and Ubuntu Zombie
manager evidence. Every unproven privacy, citation, or security property
remains visibly labelled as planned.
