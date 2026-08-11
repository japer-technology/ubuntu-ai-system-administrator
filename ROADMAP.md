# Ubuntu Zombie Roadmap

## Direction

Ubuntu Zombie will remain focused on installing and maintaining the
root-capable AI Systems Administrator. Every other installable will move out
of the Ubuntu Zombie component implementation and own an independent
lifecycle, following the separation already established by Imaginary Friend.

The intended independently managed installables are:

- `imaginary-friend`;
- `llama`;
- `forgejo`; and
- `forgejo-runner`, with an explicit dependency on `forgejo`.

Imaginary Friend remains an AI-agent family product. Llama, Forgejo, and
Forgejo Runner are infrastructure products, not AI agents, even though a
common manager may present them through the same operator interface.

This change is intended to reduce risk to Ubuntu Zombie: changes to model or
development infrastructure should no longer enlarge its installer, alter its
release, or threaten installation of the root-capable agent.

## Architectural outcome

Each non-Zombie installable will own:

- a dedicated source root under `products/<product-id>/`;
- its installer and complete lifecycle entry point;
- configuration, validation, dry-run plans, and non-interactive operation;
- Linux identities, paths, services, ports, ownership markers, and receipts;
- install, status, verify, doctor, repair, backup, update, rollback, suspend,
  resume, and uninstall behavior where applicable;
- its version, changelog, package, release, checksums, SBOM, provenance, and
  signatures;
- standalone, upgrade, rollback, and removal tests; and
- documentation for its authority and security boundary.

Products may conform to shared, data-only lifecycle schemas and black-box
tests. They must not share a runtime, virtual environment, credentials,
mutable state, audit log, release version, or lifecycle implementation.

Ubuntu Zombie and any future top-level manager will invoke a product-owned
lifecycle entry point rather than reimplementing the product's installation.
The manager may retain only a secret-free catalogue, inventory, plan, result,
and receipt reference.

## Operator experience

The eventual operator interface may offer one selectable command surface:

```text
ubuntu-zombie install zombie
ubuntu-zombie install llama
ubuntu-zombie install forgejo
ubuntu-zombie install forgejo-runner
ubuntu-zombie install imaginary-friend
ubuntu-zombie update --all
```

This is one management experience, not one installer implementation. The
manager resolves declared dependencies, verifies pinned releases, displays
the target's own plan, invokes targets serially, and reports each result
independently.

Existing commands such as `scripts/install.sh install llama` and
`scripts/install.sh install forgejo` will remain compatibility shims during
migration. A shim must delegate to the product-owned lifecycle and must not
preserve a second implementation of the same operation.

## Implementation plan

### 1. Fix the common lifecycle boundary

- Generalize the existing family lifecycle request, response, receipt,
  ownership-marker, audit-correlation, and inventory contracts for
  independently managed installables.
- Preserve each AI-agent product's reviewed authority and security rules;
  infrastructure products must not be presented as agents.
- Define dependency metadata, including the
  `forgejo-runner` → `forgejo` relationship.
- Add schema and black-box conformance tests before moving implementation.
- Define how direct source installs differ from verified release installs.

### 2. Complete the management plane

- Implement catalogue-pinned discovery and release verification.
- Add target-scoped planning, locking, invocation, inventory, and audit
  correlation.
- Reject unknown products, unlisted versions, ownership conflicts, unsafe
  request files, and raw secrets.
- Keep mutation serial and preserve independent results when an update-all
  operation partially fails.
- Exercise the manager against Imaginary Friend before infrastructure
  extraction begins.

### 3. Extract Llama

**Source status: implemented.** `products/llama/` now owns the complete
lifecycle, compatibility delegation, release workflow, fixture-backed
supported-VM harness, and product documentation. Root Llama payload and
mutation implementations have been removed. Catalogue admission remains
separate and waits for a published artifact plus recorded supported-VM and
co-installation evidence under the release gates below.

- Create `products/llama` with an independent descriptor, version, lifecycle,
  package, release, tests, and documentation.
- Move all Llama-owned installation and removal behavior out of the Zombie
  installer while preserving current paths, service identity, loopback
  listener, model verification, and ownership safeguards.
- Make the existing `llama` component target a delegating compatibility shim.
- Prove clean install, idempotent reinstall, update, rollback, selective
  uninstall, and continued Ubuntu Zombie operation.

Llama is the first extraction because it is already standalone, has no
dependency on Zombie, and provides a smaller migration surface than Forgejo.

### 4. Extract Forgejo

**Source status: implemented.** `products/forgejo/` now owns the complete
server lifecycle, compatibility delegation, release workflow, guarded
supported-VM harness, and product documentation. PostgreSQL, Caddy, Avahi,
certificate trust, recovery secrets, service hardening, ownership, and the
loopback boundary remain intact. Root runner management remains deliberately
in place for phase 5, with health-gated server coordination and explicit
same-host name-resolution and CA injection.

- Create `products/forgejo` with an independent lifecycle and release.
- Preserve its PostgreSQL, Caddy, Avahi, certificate, secrets, service
  hardening, ownership, and network-boundary behavior.
- Replace the existing component implementation with a delegating shim.
- Prove that direct and managed operations neither install nor modify Ubuntu
  Zombie.

### 5. Extract Forgejo Runner

- Create `products/forgejo-runner` as an independently versioned product.
- Declare Forgejo as an explicit manager-resolved dependency rather than
  duplicating Forgejo installation logic.
- Preserve the runner's restricted executor and trusted-repository warnings.
- Test install ordering, independent updates, failure handling, selective
  removal, and behavior when Forgejo is absent or unhealthy.

### 6. Retire the component implementations

- Remove Llama, Forgejo, and Forgejo Runner mutation hooks from the Ubuntu
  Zombie installer after their shims and product lifecycles have passed the
  migration gates.
- Reduce the Ubuntu Zombie component registry to the Zombie installation
  path and any genuinely Zombie-owned internal features.
- Keep compatibility inputs for a documented deprecation period, with clear
  diagnostics when they delegate.
- Remove shims only in a separately announced breaking release.

### 7. Introduce the neutral command and naming

- Introduce a neutral manager command only after direct and managed
  lifecycles are proven.
- Keep product names, security boundaries, releases, and documentation
  independent beneath that command.
- Retain Ubuntu Zombie as the name of the root-capable agent.
- Evaluate repository rebranding separately; command unification does not
  require an immediate repository rename.

## Migration invariants

Throughout the work:

1. Ubuntu Zombie installation remains idempotent and supports
   `ZOMBIE_NONINTERACTIVE=1`.
2. Existing supported installations can be adopted only when their ownership
   markers and resources validate exactly; unsafe or ambiguous state fails
   before mutation.
3. Product extraction does not silently move, reset, copy, or expose
   credentials or mutable state.
4. Selective update, repair, suspension, and uninstall affect only the named
   product and its declared dependencies.
5. A manager never becomes a shared updater: each target validates, backs up,
   migrates, health-checks, audits, and rolls back its own release.
6. Ubuntu Zombie's policy gate and audit behavior remain unchanged, and
   managed privileged operations produce correlated manager and target audit
   records.
7. Every product's authority matches its reviewed purpose. A root-capable
   product must preserve policy, approval, audit, revocation, and explicit
   root-equivalent compromise guidance.
8. Existing ports, paths, commands, and service names remain stable unless a
   product-specific migration explicitly documents and tests a change.

## Release gates

An extracted product replaces its component implementation only after:

- lint, unit, integration, schema, and secret-redaction tests pass;
- direct and managed dry-runs describe the same product-owned mutations;
- a disposable supported Ubuntu VM proves clean install and idempotent
  reinstall;
- update, migration failure, rollback, repair, suspend, resume, and uninstall
  are exercised;
- co-installation tests prove sibling credentials, files, services, ports,
  updates, and removal remain isolated;
- existing component installations are safely adopted or rejected before
  mutation;
- release artifacts, checksums, SBOM, provenance, and signatures verify; and
- the compatibility shim delegates without retaining duplicate lifecycle
  logic.

## Not in scope

- Moving Ubuntu Zombie itself under `products/` during these extractions.
- Combining product runtimes, credentials, databases, policies, or audits.
- Giving Imaginary Friend or infrastructure products general root authority.
- Treating Forgejo, Forgejo Runner, or Llama as AI-agent family members.
- Rewriting all lifecycle code into a generic framework.
- Removing compatibility commands before the replacement paths have shipped
  and been validated.
