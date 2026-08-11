# Photo Grove

> A private local photo-catalogue assistant that searches a deliberately shared
> read-only library using locally generated descriptions without identifying
> people or changing originals.

Photo Grove complements the family with bounded visual-media retrieval. It is
not a photo editor, biometric system, surveillance tool, cloud gallery,
general media generator, or ERIC evidence store.

## Definition card

| Field | Definition |
| ----- | ---------- |
| Status | Product definition; implementation and release gates remain open |
| Product ID | `photo-grove` |
| Human need | Find and organise a private photo collection without uploading images or granting an AI permission to alter them |
| Intended users | One adult owner who is authorised to process the shared photographs |
| Operator | The machine owner; Ubuntu Zombie may perform approved host-level lifecycle management |
| Maximum authority | Read supported images in one fixed library and write only Grove-owned metadata, descriptions, albums, exports, and logs |
| Default Linux identity | Non-login `grove` account and group |
| Default loopback port | `2727` |
| Install root | `/opt/photo-grove` |
| Configuration root | `/etc/photo-grove` |
| State root | `/var/lib/photo-grove` |
| Log root | `/var/log/photo-grove` |
| Environment prefix | `GROVE_*` |
| Ubuntu Zombie management | Fixed root-only lifecycle interface; images, tags, people, and credentials stay out of manager inventory |
| Source root | `products/photo-grove/` |
| Authoritative repository | `japer-technology/ubuntu-zombie` |

## Product promise

Photo Grove catalogues JPEG and PNG files deliberately placed in a read-only
library, records deterministic metadata and digests, and asks a local
multimodal model for untrusted descriptions and tags. The owner can search,
correct, group, export, and delete derived state without changing an original.

The first release supports one owner, images no larger than 32 MiB or 100
megapixels, a loopback UI, and one credential-free loopback multimodal model.
It performs no face recognition, identity matching, editing, or remote sync.

### It must

- preserve exact path, size, format, dimensions, and SHA-256 provenance for
  every derived description;
- clearly separate deterministic metadata, owner labels, and model-generated
  descriptions; and
- let the owner rebuild, correct, export, expire, suspend, and delete all
  Grove-owned state while originals remain unchanged.

### It must not

- identify or match people, infer sensitive traits, track individuals, or
  create biometric templates;
- edit, delete, rename, move, upload, publish, or train on source images; or
- claim that a description establishes identity, consent, location, ownership,
  copyright, authenticity, or truth.

## Status and evidence

This document fixes a first product slice. No Grove source, installer,
catalogue admission, security evidence, or release exists.

| Gate | State | Evidence or owner |
| ---- | ----- | ----------------- |
| Product definition reviewed | Open | Repository maintainers |
| First implementation slice fixed | Passed | Product promise and contracts in this document |
| Configuration and data contracts fixed | Passed | Image, description, retention, and lifecycle sections |
| Threat model reviewed | Open | Repository security reviewers |
| Installer lifecycle complete | Open | Future `products/photo-grove/` implementation |
| Security boundary tested | Open | Future negative and disposable-VM suites |
| Update and rollback tested | Open | Future lifecycle evidence |
| Standalone VM validation | Open | Ubuntu 22.04 and 24.04 LTS evidence |
| Co-installation validation | Open | Full family matrix evidence |
| Release verification complete | Open | Independent Grove release evidence |

## People and authority

### Roles

| Role | May do | Must never do |
| ---- | ------ | ------------- |
| Owner | Share authorised images, search, correct tags, create derived albums, export, suspend, and delete | Use Grove for covert identification or surveillance |
| Depicted person | Exercise rights through the owner and applicable law | Gain a Grove account merely by appearing in a photo |
| Machine operator | Install, update, back up, recover, and uninstall | Treat host ownership as consent from depicted people |
| Ubuntu Zombie manager | Invoke approved lifecycle operations | Retain images, paths, descriptions, labels, albums, or secrets |
| `grove` service | Read fixed supported images and write Grove state | Modify originals, identify people, inspect the host, or invoke lifecycle commands |
| Model endpoint | Propose descriptions and tags from one bounded image | Establish identity, consent, truth, or policy |

### Authority ceiling

The service accepts authenticated loopback requests, reads supported regular
images below `/srv/photo-grove/library`, writes protected Grove metadata and
exports, and calls one loopback multimodal model endpoint. It has no `sudo`,
shell, subprocess, camera, microphone, removable-media discovery, browser,
internet, editor, image generator, or host-wide filesystem access.

Header validation rejects polyglots, malformed dimensions, decompression-bomb
limits, animation, SVG, links, devices, mount changes, and unsupported files.
No prompt, owner label, EXIF field, or model output can grant biometric or
source-write capability.

### Authority inherited, retained, and removed

- Independent installation, authentication, policy, audit, lifecycle,
  diagnostics, backup, and release verification are retained.
- Root, shell, host inspection, package, service, account, device, and general
  network controls are removed.
- Workspace writes are replaced by a read-only image library and Grove-owned
  derived metadata.
- Face recognition, identity inference, source editing, browser automation,
  cloud providers, and family management are removed.
- Model metadata is untrusted until labelled and bound to a current digest.

## Features

| Feature | User value | Required authority/data | Release stage |
| ------- | ---------- | ----------------------- | ------------- |
| Image catalogue | Shows supported files and stale entries | Read fixed library; deterministic metadata | MVP |
| Local description and tags | Makes images searchable | One bounded image and local multimodal model | MVP |
| Owner corrections | Replaces model mistakes with attributable labels | Grove state only | MVP |
| Derived album | Groups catalogue entries without moving originals | Grove metadata only | MVP |
| Catalogue export | Provides portable metadata and references | Grove export root | MVP |
| Face recognition and source editing | Higher-risk media operations | Biometric or write authority | Out of scope |

### Primary workflow

1. The owner signs in with Grove-only credentials.
2. Grove opens a supported image descriptor-relative, validates headers and
   limits, and records deterministic metadata and a digest.
3. It sends one bounded image and a fixed schema to the loopback model.
4. Grove labels returned descriptions and tags as model-generated, strips
   unsupported identity and sensitive-trait fields, and binds them to the
   source digest.
5. The owner corrects or accepts derived metadata and may export a catalogue;
   originals remain untouched.

### Failure behaviour

Grove rejects malformed files, excessive dimensions, changed files, ambiguous
formats, model schema violations, identity claims, stale digests, and audit
failure. A file changed during analysis yields no mixed result. If the model is
unavailable, deterministic catalogue, owner labels, search, export, and
deletion remain available.

## Architecture and trust boundaries

| Component | Identity | Inputs | Outputs | Trust and access |
| --------- | -------- | ------ | ------- | ---------------- |
| Loopback UI and session service | `grove` | Credentials, searches, corrections | Authenticated views and controls | No source-write or biometric authority |
| Image validator/cataloguer | `grove` | Supported regular files | Metadata, digest, safe model payload | Read-only fixed root |
| Model bridge | `grove` | One validated image and schema | Untrusted description and tags | Exact loopback endpoint only |
| Metadata policy filter | `grove` | Proposed fields | Accepted or rejected labelled metadata | Deterministic deny-list and schema |
| Album/export service | `grove` | Catalogue and owner labels | JSON/CSV/Markdown | Grove-owned state only |
| Lifecycle manager | Root, direct or through Ubuntu Zombie | Verified request and release | Plan, result, marker, receipt | Grove-owned resources only |

Root owns code, policy, configuration, credentials, units, and markers. The
service has no capabilities, strict filesystem protection, private devices,
explicit paths, and loopback-only networking.

### Compromise boundaries

- A compromised service can disclose the shared library and corrupt derived
  Grove state, but cannot write originals.
- A compromised model sees submitted images and can provide harmful or false
  labels, but cannot read another file, identify through a Grove database, or
  alter sources.
- A stolen owner session permits search and derived exports until revocation,
  but no source or lifecycle mutation.
- A failed update retains the previous verified version and protected
  compatible state backup.

## Product-owned namespace

| Resource | Reserved value |
| -------- | -------------- |
| Linux users and groups | `grove`, `grove-share` |
| Install root | `/opt/photo-grove` |
| Configuration | `/etc/photo-grove` |
| State | `/var/lib/photo-grove` |
| Photo library | `/srv/photo-grove/library` |
| Logs | `/var/log/photo-grove` |
| Units | `photo-grove-*.service` |
| Commands | `grove-*` |
| Environment | `GROVE_*` |
| Loopback ports | `2727` |
| Cookie names | `photo_grove_session` |
| Package names | `photo-grove` |
| Ownership marker | `/var/lib/photo-grove/installation.json` |
| Receipt | `/var/log/photo-grove/management-receipt.json` |
| Firewall rules | None |

All resources are collision-checked and existing state is recognised only with
the common ownership marker and receipt.

## Authentication and secrets

| Credential | Used by | Storage/custody | Rotation and recovery |
| ---------- | ------- | --------------- | --------------------- |
| Owner password | Loopback login | Grove-specific scrypt hash in protected state | Owner rotation or root reset revokes sessions |
| Session-signing key | UI service | Random Grove-only key in `/etc/photo-grove/secrets`, mode `0600` | Rotation revokes sessions |
| Model credential | None | Loopback endpoint must require no Grove-held token | Token-bearing endpoints are unsupported |

Raw credentials and image bytes never enter arguments, ordinary environment
values, operational logs, receipts, diagnostics, catalogue exports by default,
or manager inventory. Sibling credentials and reset flows are rejected.

## Policy, tools, and audit

### Allowed capabilities

| Capability/tool | Default decision | Approval | Audit event | Bounds |
| --------------- | ---------------- | -------- | ----------- | ------ |
| Catalogue image | Restricted | Authenticated owner | `image.catalogued` | Fixed root, supported format and limits |
| Generate description | Restricted | Owner request | `description.generated` | One image, fixed local endpoint |
| Correct metadata | Restricted | Owner | `metadata.corrected` | Grove state only |
| Manage derived album | Restricted | Owner | `album.changed` | Catalogue references only |
| Export/delete derived state | Restricted | Owner confirmation | `state.changed` | Grove-owned data only |
| Lifecycle operation | Denied to service | Root operator | Common lifecycle event | Fixed product interface |

### Denied capabilities

- Source image writes, camera capture, remote fetch, upload, publication, image
  generation, and account integration.
- Face detection used for matching, face recognition, biometric templates,
  sensitive-trait inference, and covert person tracking.
- Paths outside the fixed library or model control over policy, retention, and
  owner-confirmed labels.

Audits contain event IDs, actor/session IDs, opaque image IDs, digests,
decisions, counts, results, and correlation IDs. They exclude paths by default,
image bytes, descriptions, owner labels, credentials, and model payloads.

## Data, privacy, and retention

| Data class | Purpose | Owner | Storage/protection | Default retention | Export/deletion |
| ---------- | ------- | ----- | ------------------ | ----------------- | --------------- |
| Source images | Owner's visual library | Owner and applicable rights holders | Read-only library; excluded from backup | Owner-controlled | Managed outside Grove |
| Deterministic metadata | Catalogue and stale detection | Owner | Mode `0600` SQLite | Until rebuild or deletion | JSON/CSV export |
| Model descriptions and tags | Search and organisation | Owner | Protected SQLite, source-labelled | Until owner deletion | Export, correction, deletion |
| Owner labels and albums | Curated organisation | Owner | Protected SQLite | Until owner deletion | Export or deletion |
| Operational audit | Accountability | Operator | Restricted JSON Lines | 90 days | Redacted diagnostics |

Grove processes only deliberately shared images. It does not train a model,
send telemetry, create embeddings in the first release, or retain model request
bodies in operational logs. Backups exclude source images and sessions.
Complete uninstall never deletes the photo library.

## Network and model providers

| Direction | Endpoint | Data | Default | Control |
| --------- | -------- | ---- | ------- | ------- |
| Inbound | `127.0.0.1:2727` | Authenticated UI and image previews | Open after healthy install | Password, session, CSRF |
| Outbound | Configured loopback multimodal endpoint | One validated image and fixed prompt schema | Allowed | Exact URL, request and response limits |
| Outbound | Cloud, LAN, galleries, social networks, or remote storage | None | Blocked | Network policy and absent clients |

The first release supports no redirects or credential-bearing model endpoint.
Dry-run performs no network access. The model service is independently owned
and must be disclosed to the owner as able to observe submitted images.

## Ubuntu Zombie management contract

The source entry point is `products/photo-grove/scripts/manage.sh`; the
installed command is `/usr/local/sbin/grove-manage`. It implements
[`implementation.md`](implementation.md#lifecycle-entry-point).

| Management operation | Entry point/output | Required approval | Target audit event |
| -------------------- | ------------------ | ----------------- | ------------------ |
| Discover/status | Common JSON response | None; read-only | `lifecycle.status` |
| Install/dry-run | Product plan/result | Operator approves digest | `lifecycle.install` |
| Verify/doctor/repair | Common response | Repair requires approved plan | Operation-named event |
| Backup/update/rollback | Common response | Operator approves destination or version | Operation-named event |
| Suspend/resume/uninstall | Common response | Operator approval; deletion requires confirmation | Operation-named event |

Accepted inputs are `owner_user`, `owner_password_file`, `model_base_url`,
`model`, `audit_retention_days`, `backup_destination`, and `retain_state`.
Unknown keys fail closed.

Zombie inventory may retain identifiers, version, marker and receipt digests,
coarse health, result, and correlation ID. It must not retain image counts,
paths, metadata, digests, labels, albums, depicted-person data, credentials,
or model payloads. The `grove` service cannot invoke management.

## Installation

### Preflight

- Support Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`.
- Reject namespace and ownership collisions before mutation.
- Verify artefact, checksums, signature, provenance, SBOM, descriptor, and
  pinned source lesson set.
- Validate owner, storage, library boundary, multimodal endpoint, backup, and
  rollback readiness.

### Interactive and unattended inputs

| Input | Interactive behaviour | Unattended variable/file | Validation |
| ----- | --------------------- | ------------------------ | ---------- |
| Owner | Select existing local user | `GROVE_OWNER_USER` | Existing non-root account |
| Owner password | Generate or read protected file | `GROVE_OWNER_PASSWORD_FILE` | Root-owned regular mode `0600`; 12–1,024 UTF-8 bytes |
| Model endpoint | Review loopback default | `GROVE_MODEL_BASE_URL` | Exact loopback HTTP URL |
| Multimodal model ID | Select from bounded probe | `GROVE_MODEL` | Non-empty and image-capable; required unattended |
| Audit retention | Review default `90` | `GROVE_AUDIT_RETENTION_DAYS` | Integer `30..3650` |

`GROVE_NONINTERACTIVE=1` and `--non-interactive` are equivalent. Missing
required unattended input exits `64` before mutation. Secrets use protected
files only.

### Dry-run and mutation order

1. Render the full no-write, no-network plan and stable digest.
2. Revalidate release, plan, ownership, collisions, and endpoint under lock.
3. Create identities and protected directories.
4. Write credentials, format policy, retention, and configuration atomically.
5. Install root-owned code and confined services.
6. Create the read-only library, state, logs, marker, and receipt.
7. Start after image, privacy, model-schema, and negative boundary checks pass.

### Idempotence

Valid marker, descriptor, inventory, and receipt identify the installation.
Reinstall preserves credentials, owner labels, albums, retention, and instance
ID. Derived model metadata is retained only while its source digest and schema
remain compatible. Originals are never altered, and unmarked resources are
refused.

## Lifecycle management

| Operation | Behaviour | Mutates state? | Success evidence |
| --------- | --------- | -------------- | ---------------- |
| `install` | Converge declared state | Yes | Healthy UI, model, image fixtures, marker, receipt |
| `verify` | Check ownership, confinement, schemas, library identity, and model | No | Human and JSON results |
| `doctor` | Explain image, model, index, privacy, or state issues | No | Redacted diagnosis |
| `repair` | Restore known-safe resources and rebuild derived indexes | Yes | Reverification without source changes |
| `backup` | Archive Grove state, excluding images and sessions | Yes | Verified manifest |
| `update` | Verify, back up, stage, migrate, switch, and check | Yes | New version and audit |
| `rollback` | Restore supported code and compatible state | Yes | Prior health checks |
| `suspend` | Stop processing and revoke sessions | Yes | Inactive service |
| `resume` | Revalidate privacy and integrity before start | Yes | Healthy service |
| `uninstall` | Remove owned resources; preserve or confirm state deletion | Yes | Removal report; image hashes unchanged |

## Update and migration design

Updates preserve credentials, deterministic metadata, owner labels, albums,
retention, and instance ID; verify a backup; migrate staged state; invalidate
incompatible generated descriptions; and switch atomically. Failure restores
the previous version. Image hashes and sibling resources must remain unchanged.

## Co-installation

Grove supports installation with every current family product. Tests prove
unique namespaces, cross-login rejection, service denial against sibling
roots, image immutability, independent lifecycle operations, stable non-target
hashes and service times, and exact Zombie target selection. Grove shares no
ERIC evidence or Archive Lantern index.

## Observability and operator control

| Record/control | Location or interface | Contains | Redaction/access |
| -------------- | --------------------- | -------- | ---------------- |
| Audit trail | `/var/log/photo-grove/audit.jsonl` | Policy and lifecycle events | No images, descriptions, paths, or secrets |
| Service journal | `photo-grove-chat.service` | Startup, health, bounded errors | Payload-free |
| Health check | `grove-health` | Service, model, schema, library identity | Coarse public result |
| Diagnostics | `grove-diagnostics` | Versions, permissions, units, checks | Excludes image data |
| Receipt | Product log root | Version, ownership, result | Root-only and secret-free |
| Suspension | `grove-manage suspend` | Stops service and revokes sessions | Root operator or approved Zombie action |

## Validation plan

### Product tests

- [ ] Interactive and unattended install, exit `64`, dry-run, and idempotence.
- [ ] Authentication, session revocation, metadata labels, and redaction.
- [ ] JPEG/PNG validation, size and pixel limits, digest binding, model schemas,
      owner corrections, albums, retention, and exports.
- [ ] Polyglots, malformed headers, decompression bombs, links, races, source
      writes, identity inference, sibling access, and egress fail closed.
- [ ] Backup, restore, update, rollback, repair, suspension, and uninstall.
- [ ] Direct and managed paths produce equivalent state and correlated audits.

### Product-specific red team

- Embed prompt instructions and malicious metadata in images; they must not
  change policy, paths, or tools.
- Make the model identify a person, infer a sensitive trait, invent a location,
  or mislabel model output as owner metadata; the filter must reject it.
- Race and replace images during processing; no mixed-version description may
  be committed.
- Compromise `grove` and prove source writes, camera, internet, sibling, and
  management access remain unavailable.
- Attack update and uninstall with unowned paths; mutation must remain scoped.

### Co-installation matrix

- [ ] Grove alone and with each current family product.
- [ ] Grove with ERIC and Archive Lantern, proving data and index separation.
- [ ] Every supported three-product combination containing Grove.
- [ ] All current family products together.
- [ ] Operate, manage, and remove Grove while images and non-targets remain
      unchanged.

## Threats and mitigations

| Threat | Impact | Prevention/detection | Recovery | Test |
| ------ | ------ | -------------------- | -------- | ---- |
| Malformed image | Resource exhaustion or parser exploit | Strict formats, size/pixel limits, bounded parser and model request | Reject file and suspend on repeated failure | Adversarial image corpus |
| Biometric or sensitive inference | Privacy and discrimination harm | Absent identity index, denied fields, policy filter, clear labels | Delete metadata and review audit | Malicious-model fixtures |
| Image disclosure | Severe privacy harm | Loopback model, protected paths, no egress or logs | Suspend, rotate, delete derived state | Egress and redaction suite |
| Service compromise | Library disclosure or metadata corruption | Least privilege, read-only images, root-owned code | Suspend, restore, rotate sessions | Compromised-process VM |
| Malicious release | Root-level compromise | Verified signed artefact and reviewed plan | Refuse or rollback | Artefact tamper suite |

Residual risk includes false descriptions, offensive labels, copyright
questions, and disclosure to the independently operated local model endpoint.

## Inheritance review and improvement

| Ubuntu Zombie mechanism | Keep, replace, or remove | Reason | Evidence |
| ----------------------- | ------------------------ | ------ | -------- |
| Idempotent installer | Keep | Curated metadata needs safe convergence | Reinstall tests |
| Policy and audit gate | Keep with image-data minimisation | Generation and deletion need accountability | Redaction tests |
| Root-capable account | Remove | Catalogue work needs no host mutation | Capability-negative tests |
| Chat authentication | Replace | Grove requires independent credentials | Cross-login tests |
| Lifecycle/kill switch | Keep | Owner needs immediate privacy control | Lifecycle tests |
| Update and recovery | Keep with source immutability | Originals are not product state | Hash and rollback tests |

**Measurable improvement:** every generated field must carry model provenance
and a current image digest, while prohibited identity and sensitive-trait
fields must have a 100% rejection rate in the adversarial model suite.

**Pinned source lesson set:** Ubuntu Zombie `v2026.08.07.05.56.42`.

## Honest claims and out of scope

### Approved description

> Photo Grove is a private local assistant for searching a deliberately shared
> read-only JPEG and PNG library using digest-bound local-model descriptions.

### Prohibited claims

- That Grove identifies people, proves consent, authenticity, ownership,
  copyright, location, or truth.
- That model descriptions are neutral, complete, or accurate.
- That local operation hides images from same-host root or the selected local
  model service.
- That this definition represents implemented or released software.

### Out of scope

- Face recognition, biometrics, surveillance, sensitive-trait inference,
  camera capture, editing, generation, publication, and remote sync.
- Cloud models, remote users, shared albums, social networks, and account
  integrations.
- Video, RAW, HEIF, animated images, OCR, and embeddings in the first release.

## Risks and open decisions

| Decision/risk | Why it matters | Owner | Required before |
| ------------- | -------------- | ----- | --------------- |
| Family contract admission | Current schemas do not admit Grove | Repository maintainers | First implementation change |
| Safe image profile | Header parsing and model payload limits are security-critical | Product maintainers | First runtime change |
| Privacy and biometric review | Photographs contain third-party and sensitive data | Privacy reviewers | Implementation approval |
| Model filter fixture | Prohibited inference must be measurable | Safety reviewers | Release candidate |
| Disposable-VM boundary | Read-only library and egress controls need host proof | Release owner | Release candidate |

## Product-owned documentation

- [ ] README and product vision.
- [ ] Architecture, image flow, and threat model.
- [ ] Privacy, depicted-person data, retention, export, and deletion model.
- [ ] Image profile, provenance, description-label, album, and export schemas.
- [ ] Configuration, credentials, lifecycle, backup, and recovery.
- [ ] Adversarial image/model fixtures and co-installation evidence.
- [ ] Release process, changelog, version, checksums, signatures, provenance,
      and SBOM.

## Release gate

A release requires lint, tests, package and artefact verification, adversarial
image and model-filter fixtures, standalone VM lifecycle, negative security and
privacy suites, co-installation evidence, changelog, and version. Family
admission also requires manager and contract evidence. Unproven privacy,
accuracy, or security claims remain visibly planned.
