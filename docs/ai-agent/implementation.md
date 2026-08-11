# AI-agent implementation contract

This document is the normative implementation contract for adding Imaginary
Friend, Curriculum Flame, ERIC, and Ubuntu Zombie family management to this
repository. It resolves the source-layout, lifecycle, release, and sequencing
questions that previously prevented implementation from starting.

The products remain independent at runtime. Their source is deliberately
co-located in this repository so one GitHub change can be reviewed and tested
against every host namespace and trust boundary.

## Authority and precedence

Implementers must use this order when documents disagree:

1. [`AGENTS.md`](../../AGENTS.md), [`SECURITY.md`](../../SECURITY.md), and
   repository contribution rules;
2. this implementation contract;
3. the applicable product definition in this directory; and
4. documents under [`docs/options/`](../options/) as design history and
   background requirements.

The product definitions remain authoritative for purpose, authority, data,
and safety. This document is authoritative for where and how the products are
built in this repository. No external repository, generic agent framework, or
future Ubuntu Zombie management UI is a prerequisite.

An open release, legal, safety-review, or deployment gate does not prevent
code, schemas, fail-closed controls, fixtures, or tests from being written.
It prevents the affected feature from being enabled or advertised until the
gate passes.

## Fixed repository layout

Ubuntu Zombie remains at the repository root. New product source must use
these exact roots:

```text
family/
  catalog.json
  schemas/
    audit-event-v1.schema.json
    catalog-v1.schema.json
    installation-v1.schema.json
    inventory-v1.schema.json
    product-v1.schema.json
    receipt-v1.schema.json
    request-v1.schema.json
    response-v1.schema.json
products/
  imaginary-friend/
  curriculum-flame/
  eric/
tests/
  family/
```

Every `products/<product-id>/` root owns:

```text
CHANGELOG.md
Makefile
PRODUCT.json
UPSTREAM.md
VERSION
docs/
payload/
  agent/
  bin/
  etc/
  logrotate/
  systemd/
scripts/
  manage.sh
tests/
  fixtures/
  integration/
  unit/
```

`PRODUCT.json`, `VERSION`, and `scripts/manage.sh` are required from the
first implementation change. A product may omit an otherwise empty
subdirectory until the change that needs it.

There are no nested Git repositories, submodules, or generated copies from
another repository. A product can copy an audited Ubuntu Zombie mechanism,
but the copied code must live below that product root, use only that
product's namespace, and record the source tag and copied files in
`UPSTREAM.md`. The initial lesson set is
`v2026.08.07.05.56.42`.

The only source shared across products is the data-only contract under
`family/` and black-box conformance code under `tests/family/`. Installed
products must not import a sibling or the root `payload/`, share a virtual
environment, use a sibling executable as a library, or write sibling state.

## Supported implementation baseline

The first implementation supports Ubuntu Desktop 22.04 and 24.04 LTS on
`amd64`, systemd, Bash, and Python 3.10 or 3.12. `arm64`, Ubuntu flavours,
Ubuntu Server, Windows, macOS, containers as a deployment target, and school
or fleet deployment are later work unless a product definition explicitly
requires a stricter boundary.

Use the repository's existing runtime dependency set and the Python standard
library. A product owns its own virtual environment and pinned dependency
record even when it selects the same dependency version as Ubuntu Zombie.
Docker, a JavaScript application framework, a new database server, or a
shared agent framework is not required for any first implementation.

Each product Makefile must expose:

```text
make -C products/<product-id> lint
make -C products/<product-id> test
make -C products/<product-id> package
```

When the first product source lands, root `make lint` and `make test` must
delegate to every present product. Root `make package` keeps producing the
Ubuntu Zombie artifact; product packages are built by their own Makefiles.
CI must run the product commands on Python 3.10 and 3.12 and build every
product artifact. Root-required lifecycle tests stay in the disposable-VM
integration workflow, never in normal developer tests.

## Product identity document

`PRODUCT.json` is UTF-8 JSON with no duplicate keys. It is data, never
sourced or evaluated. `family/schemas/product-v1.schema.json` must require
the following fields:

| Field | Type and rule |
| ----- | ------------- |
| `schema_version` | Integer `1` |
| `product_id` | One of `imaginary-friend`, `curriculum-flame`, or `eric` |
| `display_name` | Non-empty human-readable name |
| `authority_summary` | Non-empty description that does not overstate the product |
| `source_root` | Exact repository-relative `products/<product-id>` path |
| `version_file` | Literal `VERSION` |
| `lifecycle_script` | Literal `scripts/manage.sh` |
| `installed_entrypoint` | Absolute product-owned management command |
| `install_root` | Reserved absolute `/opt` path |
| `configuration_root` | Reserved absolute `/etc` path |
| `state_root` | Reserved absolute `/var/lib` path |
| `log_root` | Reserved absolute `/var/log` path |
| `ownership_marker` | Absolute marker path below `state_root` |
| `environment_prefix` | Exact uppercase product prefix |
| `accounts` | Complete, non-empty array of product-owned identities |
| `units` | Complete array of product-owned systemd units |
| `ports` | Complete array of product-owned listening ports |
| `cookie_names` | Complete array of unique cookie names |
| `operations` | Operations implemented by the lifecycle entry point |

Unknown top-level fields are rejected for schema version `1`. Paths must be
canonical absolute paths without `..`. An installed descriptor is copied
unchanged to `<configuration_root>/PRODUCT.json`, owned by `root:root` and
mode `0644`.

`ports` never includes a provider or model endpoint that the product calls
but does not own. The shared default `127.0.0.1:8080` model endpoint is an
external local prerequisite, not a product resource, so co-installed
products do not claim or collide on that port.

## Family catalogue

`family/catalog.json` is the only list of products Ubuntu Zombie may manage.
Its top-level object contains `schema_version` (`1`), `repository`
(`japer-technology/ubuntu-zombie`), `generated_at` (UTC RFC 3339), and a
`products` array. Each product entry contains:

| Field | Rule |
| ----- | ---- |
| `product_id` | Exact descriptor product ID |
| `descriptor` | Repository-relative `products/<product-id>/PRODUCT.json` |
| `version` | Exact product date-time version |
| `tag` | Exact product tag defined below |
| `artifact` | Name, HTTPS release URL, and lowercase SHA-256 |
| `sbom` | Name, HTTPS release URL, and lowercase SHA-256 |
| `provenance` | Name, HTTPS release URL, and lowercase SHA-256 |
| `signature_bundle` | Name, HTTPS release URL, and lowercase SHA-256 |
| `certificate_identity` | Expected GitHub Actions signing identity |

Unknown or duplicate fields are rejected. Every URL must use HTTPS, the
catalogue repository, exact tag, and exact listed asset name. Redirects are
accepted only when every hop uses HTTPS and a GitHub-owned release-asset
host; the final bytes still must match the pinned digest.

The initial manager is deliberately digest-pinned. CI verifies the product's
checksum, signature, provenance, and SBOM before a catalogue digest update
can pass. The installed manager then verifies downloaded bytes against those
catalogue digests using existing system tools. It never installs an
unlisted version, follows an unlisted URL, or treats target-provided metadata
as a trust root.

Development from a checkout may invoke a product's source lifecycle script
on a disposable VM. It must identify the result as an un-released source
install and may not add it to a production catalogue.

`family/schemas/catalog-v1.schema.json` validates the catalogue.
`inventory-v1.schema.json` validates manager state. The installation,
receipt, and audit schemas encode the structures below; product schemas may
add namespaced detail fields but cannot weaken required common fields.

The inventory top-level object contains schema version, generated timestamp,
and a `products` object keyed by exact product ID. Each value contains only
instance ID, installed and available versions, descriptor and marker digests,
high-level lifecycle and health status, last correlation ID, last operation
and result, receipt path/digest, and last checked timestamp. Schema
validation rejects any credential, request input, private-content,
conversation, learner, evidence, consent, or key field.

## Ownership marker and receipt

Every managed product uses
`/var/lib/<product-id>/installation.json` as its ownership marker. It is
written atomically only after install and health checks succeed, is a regular
non-symlink file owned by `root:root` with mode `0644`, and contains:

| Field | Required value |
| ----- | -------------- |
| `schema_version` | Integer `1` |
| `product_id` | Exact product ID |
| `instance_id` | UUID generated on first successful install and preserved |
| `version` | Exact product `VERSION` |
| `source_revision` | Git commit or verified artifact digest |
| `installed_at` | UTC RFC 3339 timestamp |
| `install_root` | Exact descriptor value |
| `lifecycle_entrypoint` | Exact descriptor value |
| `artifact_sha256` | Lowercase digest, or `null` for a source install |

Discovery trusts a marker only after validating its type, owner, mode,
schema, product ID, paths, entry point, and descriptor. A marker never grants
ownership of an unexpected account, path, unit, command, or port. Any
conflict outside the declared and valid marker fails before mutation.

Each operation also writes a secret-free JSON receipt below the product log
root. The current receipt is `management-receipt.json`; historical receipts
use `receipts/<correlation-id>.json`. Receipt files are regular files,
`root:root`, mode `0640`, and contain the common response envelope, product
and instance versions, changed resource names, recovery guidance, and the
preallocated target `audit_event_id`. They never contain request values
marked secret, password hashes, keys, private content, prompts, or model
output.

## Lifecycle entry point

The source entry point is `scripts/manage.sh`. Installation copies a
product-named command to `/usr/local/sbin`:

| Product | Installed command |
| ------- | ----------------- |
| Imaginary Friend | `/usr/local/sbin/friend-manage` |
| Curriculum Flame | `/usr/local/sbin/flame-manage` |
| ERIC | `/usr/local/sbin/eric-manage` |
| Beep | `/usr/local/sbin/beep-manage` |

The source and installed commands implement the same interface:

```text
manage.sh <operation> [--dry-run] [--json] [--non-interactive]
  [--request-file <absolute-path>] [--correlation-id <uuid>]
  [--plan-digest <sha256:hex>] [--yes]
```

The required operations are:

| Operation | Contract |
| --------- | -------- |
| `describe` | Read and return the validated product descriptor |
| `status` | Read ownership, lifecycle, version, integrity, and health |
| `install` | Converge a clean or valid existing installation |
| `verify` | Perform read-only declared-state and boundary checks |
| `doctor` | Explain drift and recovery without mutation |
| `repair` | Reassert only documented, product-owned state |
| `backup` | Create and verify a product-scoped backup |
| `update` | Verify, back up, migrate, switch, and health-check |
| `rollback` | Restore a supported product version and compatible state |
| `suspend` | Stop useful operation while preserving declared state |
| `resume` | Resume only after integrity and policy checks pass |
| `uninstall` | Remove only owned resources with explicit retention choice |

Products may add a schema-declared operation that does not weaken or overload
the common meanings. Beep adds `kill`: an approved, audited terminal
tombstone and useful-service shutdown. The v1 request, response, and product
schemas conditionally admit `kill` only when `product_id` is `beep`; other
descriptors retain the common operation list.

Mutating operations support `--dry-run`. A plan lists the exact resources
and checks in execution order and does not create lock files, directories,
credentials, logs, downloads, or network requests. Execution recomputes the
plan under the product lock and rejects a supplied `--plan-digest` if host
state or inputs changed.

Only one mutating operation may hold
`/run/lock/<product-id>.lock`. A busy target exits `75`; Ubuntu Zombie
manages targets serially and does not bypass the lock.

### Request file

`--request-file` accepts one UTF-8 JSON object matching
`family/schemas/request-v1.schema.json`. The command rejects a symlink,
non-regular file, non-root owner, group/other permission, wrong product ID,
wrong operation, duplicate key, or unknown schema version.

Required request fields are:

| Field | Type |
| ----- | ---- |
| `schema_version` | Integer `1` |
| `product_id` | Exact product ID |
| `operation` | Exact requested operation |
| `correlation_id` | UUID |
| `requested_by` | `operator` or `ubuntu-zombie` |
| `inputs` | Product-defined object |
| `retain_state` | Boolean, required for uninstall |
| `confirmation` | String or `null` |

Product definitions list every accepted `inputs` key. Unknown keys fail
closed. Secret inputs are file references, not raw values. The referenced
file must pass the same regular-file, root-owner, and mode checks and is read
only by the target operation that needs it.

Ubuntu Zombie creates transient requests below
`/run/ubuntu-zombie/agents/requests/<correlation-id>/`, with every directory
mode `0700` and file mode `0600`, and removes them after success or failure.
The chat runtime never asks a user to type a target password or key into a
model-visible conversation. Operations requiring a new secret are completed
through the local root CLI or the target's own authenticated interface.

### Response envelope

With `--json`, stdout contains exactly one JSON object matching
`family/schemas/response-v1.schema.json`; progress goes to stderr and is
secret-redacted. Required fields are:

| Field | Type and rule |
| ----- | ------------- |
| `schema_version` | Integer `1` |
| `product_id` | Exact product ID |
| `product_version` | Date-time version string |
| `instance_id` | UUID or `null` before first install |
| `operation` | Requested operation |
| `phase` | `read`, `plan`, or `execute` |
| `correlation_id` | Request UUID |
| `status` | `ok`, `degraded`, `blocked`, `unsupported`, or `failed` |
| `changed` | Boolean; always false for read and plan |
| `plan_digest` | `sha256:<lowercase-hex>` or `null` |
| `requires_confirmation` | Boolean |
| `required_inputs` | Array of names and `secret` booleans |
| `steps` | Ordered resource/action summaries with a `mutates` boolean |
| `checks` | Ordered health or integrity results |
| `receipt` | Receipt path and digest, or `null` |
| `errors` | Stable code, redacted message, and retryable boolean |
| `recovery` | Ordered, non-secret operator guidance |

The plan digest covers canonical UTF-8 JSON for `product_id`, version,
operation, instance, non-secret input fingerprints, and ordered steps.
Objects use sorted keys and compact separators; arrays preserve order.
Secret files contribute a SHA-256 digest, never their value.

Each check has `id`, `status` (`pass`, `warn`, or `fail`), `summary`, and a
non-secret `remediation` string. `verify` exits non-zero if any required
check fails. `doctor` exits zero when it successfully produces a diagnosis,
even when the diagnosed product is degraded.

### Exit status

| Code | Meaning |
| ---- | ------- |
| `0` | Requested operation or report completed successfully |
| `1` | Operation failed or `verify` found failed required checks |
| `2` | Invalid command-line usage |
| `64` | Required interactive or unattended input is missing |
| `65` | Request or stored data does not match its schema |
| `66` | Required installation, marker, or input file does not exist |
| `69` | Required local dependency or safeguard is unavailable |
| `73` | Unsafe collision, ownership mismatch, or unwritable destination |
| `75` | Target is busy or a retryable operation timed out |
| `78` | Configuration, policy, signature, or integrity validation failed |

Unexpected failures use `1`; they do not invent product-specific meanings
for common codes.

## Non-interactive and secret inputs

Every product accepts `<PREFIX>_NONINTERACTIVE=1` as equivalent to
`--non-interactive`. It never prompts in that mode and exits `64` before
mutation when a required input is absent. `--yes` accepts an already rendered
non-destructive plan; it never supplies destructive confirmation or
subject/guardian consent.

Passwords, provider tokens, encryption material, and recovery keys use
`<PREFIX>_*_FILE` inputs. Raw secrets are prohibited in command arguments,
plain environment variables, plans, output, receipts, diagnostics, audit
details, and Ubuntu Zombie inventory.

## Audit correlation

Every direct or managed lifecycle call creates a target JSON Lines audit
event containing:

```text
timestamp, event_id, correlation_id, product_id, instance_id, operation,
phase, actor, decision, result, changed, receipt_digest
```

Ubuntu Zombie uses the same correlation ID in its manager-side audit event.
The target creates its audit event even when validation denies the request.
For a completed mutation, the target preallocates `event_id`, writes that ID
into the receipt, atomically writes the receipt, computes its digest, and
then appends the audit event with `receipt_digest`. Denied or pre-receipt
events use `receipt_digest: null`; there is no circular digest.
Product-specific audit details may add fields but must not replace or change
the common field meanings. Audit writes are append-only, mode-restricted,
redacted before serialization, and tested with representative secret values.

## Release ownership inside one repository

Each product has an independent date-time `VERSION` and `CHANGELOG.md`.
Ubuntu Zombie's root `VERSION`, `CHANGELOG.md`, `v<VERSION>` tags, package,
and release process remain unchanged.

Product releases use:

| Product | Tag | Artifact |
| ------- | --- | -------- |
| Imaginary Friend | `imaginary-friend-v<VERSION>` | `imaginary-friend-<VERSION>.tar.gz` |
| Curriculum Flame | `curriculum-flame-v<VERSION>` | `curriculum-flame-<VERSION>.tar.gz` |
| ERIC | `eric-v<VERSION>` | `eric-<VERSION>.tar.gz` |

Every artifact contains only its product root plus the repository license and
the applicable family schemas. Each release independently produces
checksums, an SPDX SBOM, provenance, signatures, and test evidence. A change
to one product does not bump another product's version.

## Fixed first implementation slices

| Product | Required first slice | Explicitly later |
| ------- | -------------------- | ---------------- |
| Imaginary Friend | One owner, text conversation, one or more bounded workspaces, local model endpoint, retention/export, complete lifecycle | Cloud providers, arbitrary existing-workspace adoption, multiple owners |
| Curriculum Flame | One guardian, one learner, synthetic Years 5–8 mathematics outcomes, text-only local model, deterministic policy, buffered validation, local event dashboard | Schools, teachers, images, voice, external alerts, real curriculum distribution |
| ERIC | Living apprenticeship, consented evidence ingestion, append-only correction, retrieval, claim-level provenance, export, suspend/destroy | Executor, incapacity transition, posthumous mode, synthetic media |

Later features must be absent or return `unsupported`; they must not be
partially enabled. The product definitions specify concrete defaults and
data contracts for these slices.

The model endpoint is operator-provided infrastructure. It may be the
standalone Ubuntu Zombie `llama` component or another OpenAI-compatible
server, but none of the three initial managed products installs, owns, updates,
or removes it.
Install health gates require the configured endpoint to answer a bounded
model-list and completion probe. Hermetic tests start a product-owned
loopback fixture implementing those two calls; tests never need a real model
or network. The actual install performs this probe during preflight; a
missing endpoint exits `69` before mutation.

## Implementation order and hand-off gates

Work may be split into the following dependency-ordered GitHub changes:

1. **Family contract:** add `family/` schemas, catalogue validation, fixture
   descriptors, and hermetic conformance tests.
2. **Friend standalone:** implement the complete first Friend slice and pass
   its non-root tests and disposable-VM lifecycle.
3. **Ubuntu Zombie manager:** implement catalogue-pinned discovery, the
   `zombie-agents` root CLI, closed manager tools, target selection, request
   handling, inventory, and dual audit against Friend.
4. **Flame standalone and managed:** implement the complete first Flame
   slice, fail-closed validator fixtures, role isolation, then add it to the
   catalogue and manager matrix.
5. **ERIC living apprenticeship:** implement the living-only ERIC slice,
   vault/Twin separation, provenance and export, then add it to the catalogue
   and manager matrix.
6. **Family release gate:** run every standalone and co-installation VM
   combination, independent update/removal tests, artifact verification, and
   red-team suites.

Work on a later product may begin after the family schemas exist, but it
cannot claim managed support until the preceding manager contract passes.
No implementation change must wait for a separate product repository,
generic framework extraction, cloud service, legal recognition, school
partnership, real child data, deceased-person data, or production signing
credential. Fixtures use synthetic people, conversations, curriculum, and
evidence.

## Definition of done

A product is implemented only when:

- its source exists at the reserved root and has no runtime import from a
  sibling or root Ubuntu Zombie payload;
- its descriptor, lifecycle operations, marker, receipts, audit, and
  non-interactive behavior pass family conformance tests;
- install, reinstall, update, rollback, repair, suspend, resume, and
  uninstall preserve the documented boundaries;
- positive, negative, secret-redaction, and malformed-state tests pass
  without root or network where those capabilities are unnecessary;
- a disposable VM proves the declared systemd, account, filesystem, port,
  credential, and removal boundaries;
- its own package, version, changelog, SBOM, checksum, signature, and
  provenance gates pass; and
- documentation labels every deferred or unreviewed capability unavailable.
