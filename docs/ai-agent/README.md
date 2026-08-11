# AI agent catalogue

This directory specifies the independent AI-agent product family that began
with Ubuntu Zombie. It turns the agent definitions in
[`ghosts-in-the-machine-plan.md`](../options/ghosts-in-the-machine-plan.md)
into one implementation-ready document per named product, provides a
normative [`implementation contract`](implementation.md), and provides a
[`template.md`](template.md) for defining the next product by hand.

Ubuntu Zombie comes first because it is the implemented reference product
and the root-level manager of the family: the **God role**. The later agents
are variations on its proven product lessons, not modes, personas,
components, or subclasses of its runtime. Each remains a separate
installation with its own authority, security boundary, lifecycle,
documentation, and release, while Ubuntu Zombie can install and manage it
on the operator's behalf. Their source and release automation live in this
repository under separate product roots; source co-location does not combine
their installed trust boundaries. The manager role does not reserve root
authority: a separately defined systems-administrator product may also be
fully root-capable.

## Catalogue

| Product | Status in this repository | Purpose | Maximum authority | Default identity | Default port |
| ------- | ------------------------- | ------- | ----------------- | ---------------- | ------------ |
| [Ubuntu Zombie](ubuntu-zombie.md) | Core implemented; family manager implementation-ready | AI Systems Administrator and family manager | Root through its policy and approval boundary | `zombie` | `7878` |
| [Imaginary Friend](imaginary-friend.md) | Standalone source and release implemented; production family admission gated | Private conversational companion and workspace | Its own files and nominated workspace only | `friend` | `6767` |
| [Beep](beep.md) | Standalone source, tests, package, and release workflow implemented; production family admission gated | Independent Ubuntu Zombie functional duplicate | Root through Beep policy and approval | `beep` | `58989` |
| [Curriculum Flame](curriculum-flame.md) | Implementation-ready first-release specification | Curriculum-gated local AI for children | Its own state; learner workspaces are later | `flame-*` services | `5656`, `5657` |
| [ERIC](eric.md) | Living-apprenticeship implementation-ready; later stages gated | Evolving record of identity and cognition | Its own evidence and model; Executor absent in first release | `eric-*` services | `4545`, `4546` |

“Implemented” means this repository currently ships and tests the named
scope. “Implementation-ready” means the source root, first scope, interfaces,
defaults, and acceptance gates are fixed; it does not claim that software
exists or is safe to deploy. Imaginary Friend and Beep now have standalone
source, tests, lifecycle, documentation, packaging, and independent release
machinery, but remain absent from the production family catalogue while their
recorded disposable-VM, co-installation, security-review, and final
release-verification gates remain open. Curriculum Flame and ERIC are to be
implemented at the roots reserved by
[`implementation.md`](implementation.md). No external repository needs to be
created or consulted.

### Product-definition proposals

The following template-complete documents explore complementary products.
They are discoverable design inputs, not entries in the implementation-ready
catalogue above. A link here does not admit a product to the family contract,
reserve an implemented manager target, or claim that source, tests, security
evidence, or a release exists.

| Proposal | Purpose | Maximum authority | Default identity | Default port |
| -------- | ------- | ----------------- | ---------------- | ------------ |
| [Archive Lantern](archive-lantern.md) | Cited answers from a private text library | Read one fixed library; write derived state | `lantern` | `3434` |
| [Code Orchard](code-orchard.md) | Evidence-bound local code review and patch proposals | Read one source root; write unapplied reports and patches | `orchard` | `3567` |
| [Household Ledger](household-ledger.md) | Offline household transaction analysis | Read one CSV import root; write Ledger state | `ledger` | `3890` |
| [Maintenance Atlas](maintenance-atlas.md) | Cited household asset maintenance planning | Read one manual library; write Atlas records | `atlas` | `2828` |
| [Meeting Loom](meeting-loom.md) | Cited summaries and action proposals from imported transcripts | Read one transcript inbox; write Loom records | `loom` | `2525` |
| [Language Harbor](language-harbor.md) | Private adult language practice | Read signed lessons; write Harbor learner state | `harbor` | `2424` |
| [Photo Grove](photo-grove.md) | Local search over a read-only photo library | Read one image library; write derived metadata | `grove` | `2727` |
| [Mail Pilot](mail-pilot.md) | Triage imported messages and prepare unsent drafts | Read one `.eml` inbox; write Pilot drafts | `pilot` | `2626` |
| [Project Compass](project-compass.md) | Structured personal project planning | Compass-owned state only | `compass` | `2323` |
| [Access Bridge](access-bridge.md) | Reviewable cognitive-accessibility text alternatives | Bridge-owned state only | `bridge` | `2121` |
| [Quiet Watch](quiet-watch.md) | Sanitised host-health telemetry and local alerts | Fixed read-only collector; Watch-owned state | `watch` | `2222` |

## Reading order

1. Read the [implementation contract](implementation.md) for the authoritative
   source layout, lifecycle protocol, release model, and work order.
2. Read [Ubuntu Zombie](ubuntu-zombie.md) for the working reference:
   installation, policy, audit, lifecycle, updates, and removal.
3. Read the later product documents to see which lessons and privileged
   mechanisms are retained, changed, or removed.
4. Use the [AI agent definition template](template.md) for a new proposal.
5. Use the original
   [family plan](../options/ghosts-in-the-machine-plan.md) for rationale and
   historical context. If it conflicts with this directory, this directory
   controls implementation.

## The family rule: copy, separate, improve

Every new family member follows the same progression:

1. **Copy the lessons.** Begin in the reserved product source root from the
   pinned, audited Ubuntu Zombie lesson set named in
   [`implementation.md`](implementation.md), retaining only useful installer,
   lifecycle, audit, test, packaging, and documentation disciplines.
2. **Separate the product.** Rename every account, group, path, unit,
   command, environment variable, cookie, port, log, manifest, receipt, and
   package before the first install.
3. **Set authority deliberately.** Retain only capabilities the purpose
   requires. A systems-administrator variant may retain general root access
   when its definition justifies that boundary and preserves explicit policy,
   approval, audit, revocation, and root-equivalent compromise disclosure.
   Products without that purpose delete root access, general shell execution,
   host-wide reads, package and service control, and other unneeded power.
4. **Write a new boundary.** Define a product-specific threat model, policy,
   approval model, data model, and refusal behaviour. It is not a lower
   Ubuntu Zombie capability setting.
5. **Own the lifecycle.** Build a dedicated installer, updater, verifier,
   doctor, repair path, rollback or recovery path, and uninstaller.
6. **Improve the mechanism.** Record at least one measurable improvement
   over the inherited design and prove it in tests.

After the copy there is no runtime import, shared payload, common virtual
environment, source submodule, service template, policy package, or
automatic code synchronisation. The data-only family schemas and black-box
conformance tests are the sole shared source contract. A useful fix can be
ported manually, but it is reviewed, tested, versioned, and released
independently by every product that adopts it.

## Lessons every product must preserve

These are acceptance outcomes, not a shared implementation:

1. **Idempotent convergence:** a re-run reaches the declared state without
   destroying valid credentials or state.
2. **Interactive and unattended operation:** required values are
   reviewable; non-interactive mode never prompts and exits `64` when a
   required input is missing.
3. **Inspection before mutation:** preflight, parameter review, and dry-run
   expose intended host changes before root applies them.
4. **Least authority by construction:** Linux identities, filesystem
   ownership, service confinement, tools, and policy agree on the maximum
   authority.
5. **Policy and audit together:** every sensitive action passes through the
   product's policy and reaches its audit trail.
6. **Independent authentication:** raw passwords and session secrets never
   enter logs, diagnostics, or ordinary receipts.
7. **Operator control:** every product provides credential rotation, health
   checks, diagnostics, a kill switch or suspension control, and removal.
8. **Reversibility:** uninstall removes only product-owned resources and
   protects state destruction with explicit confirmation.
9. **Safe updates:** updates preserve or migrate state, validate before
   committing, and document rollback or recovery.
10. **Release trust:** artifacts are checksum-pinned, signed,
    provenance-verifiable, and accompanied by an SBOM where practical.
11. **Honest boundaries:** documentation says what the product cannot do;
    prompts are never described as a security boundary.
12. **Evidence before release:** lint, tests, packaging, disposable-VM
    lifecycle tests, and negative security tests pass.

## Independence contract

| Concern | Each product owns |
| ------- | ----------------- |
| Source and release | Product root in this repository, version, changelog, artifact, SBOM, checksums, signatures, and provenance |
| Installation | Installer, prompts, preflight, dry-run, receipt, ownership markers, and rollback |
| Update | Compatibility checks, backup, migration, health gate, rollback, schedule, and release channel |
| Removal | An uninstaller that removes only its product; Ubuntu Zombie may invoke it for the operator |
| Runtime | Code tree, dependencies, environment, templates, tools, and processes |
| Identity | Linux users, groups, optional sharing groups, and service accounts |
| Authentication | Passwords, hashes, signing keys, cookies, rotation, and recovery |
| Provider access | Credential file and model selection; never a sibling's secrets |
| Policy | Threat model, allowed actions, refusal rules, approvals, and fail-closed behaviour |
| State | Configuration, history, lifecycle, cache, database, and backup format |
| Observability | Audit and event logs, journal identifiers, diagnostics, and rotation |
| Host resources | Ports, units, commands, firewall rules, paths, manifests, and package ownership |
| Quality | Tests, VM matrix, red-team cases, release gates, and documentation |

Products may independently select the same language or upstream dependency.
They do not share a live installed copy merely because they have a common
ancestor or Git repository.

## Ubuntu Zombie is the designated family manager (“God” role)

Ubuntu Zombie is generally root-capable and is the family's designated
machine-level administrator. “God” describes that implemented management role:
it can discover, install, verify, start, stop, diagnose, repair, update,
suspend, back up, and uninstall another local agent when the human operator
approves the action. It is not an exclusivity rule. A separately defined
product may retain equivalent root authority, in which case the products are
operating-system peers and cannot claim same-host isolation from one another.

The current Ubuntu Zombie runtime already has the underlying root tools to
operate product-owned commands. A dedicated family inventory and management
experience is a required extension with a fixed implementation contract, not
an implemented UI or installer target yet. Documentation must keep that
distinction visible.

Management does not turn the products into components or one runtime:

- each target still owns and validates its release, installer, updater,
  migration, rollback, policy, and uninstaller;
- Ubuntu Zombie verifies and invokes that product-owned entry point instead
  of reimplementing it;
- management is serial and target-scoped, with an explicit plan and
  approval before mutation;
- both Ubuntu Zombie and the target product audit the request and outcome;
- raw target passwords, provider keys, guardian keys, and vault keys are
  not copied into Zombie state or reused as Zombie credentials;
- manager integration does not grant a target access to the management plane
  or any authority absent from its own product definition; and
- managing a service does not grant Zombie the human, guardian, legal, or
  consent authority represented inside that service.

Each product defines its own authority ceiling. A product that does not need
general host administration uses a non-login identity and, if essential, a
closed root-owned helper for enumerated operations. A product whose purpose
does require full host administration may instead use a dedicated root-capable
identity and general command runner, but those capabilities must pass through
product-owned policy, approval, and audit controls and be covered by explicit
revocation and root-equivalent compromise guidance.

Less-privileged agents must not read or write Ubuntu Zombie's or one
another's secrets, code, policy, state, logs, or ports. Any root-capable
product can inspect and administer the entire host; same-machine isolation
cannot hide one root-capable product from another. A dedicated machine remains
the stronger deployment for child data, ERIC evidence, or any boundary that
must exclude every Systems Administrator.

No prompt, persona, password, approval, or template can increase installed
authority.

## Initial host namespace reservations

These reservations prevent accidental overlap; each product must validate
the real host and refuse to adopt an unmarked resource.

| Resource | Ubuntu Zombie | Imaginary Friend | Curriculum Flame | ERIC |
| -------- | ------------- | ---------------- | ---------------- | ---- |
| Install root | `/opt/ai-zombie` | `/opt/imaginary-friend` | `/opt/curriculum-flame` | `/opt/eric` |
| Configuration | `/etc/ubuntu-zombie` | `/etc/imaginary-friend` | `/etc/curriculum-flame` | `/etc/eric` |
| State | `/var/lib/ubuntu-zombie` and `/opt/ai-zombie/state` | `/var/lib/imaginary-friend` | `/var/lib/curriculum-flame` | `/var/lib/eric` |
| Logs | `/var/log/ubuntu-zombie` | `/var/log/imaginary-friend` | `/var/log/curriculum-flame` | `/var/log/eric` |
| Service identities | `zombie` | `friend` | `flame-child`, `flame-policy`, `flame-guardian`, `flame-model`, `flame-validator` | `eric-twin`, `eric-vault`, `eric-governance`; later `eric-executor` |
| Service prefix | `ubuntu-zombie-*` | `imaginary-friend-*` | `curriculum-flame-*` | `eric-*` |
| Command prefix | `zombie-*` | `friend-*` | `flame-*` | `eric-*` |
| Environment prefix | `ZOMBIE_*` | `FRIEND_*` | `FLAME_*` | `ERIC_*` |
| Loopback ports | `7878` | `6767` | `5656` child, `5657` guardian | `4545` Twin, `4546` governance |

Every web product also owns a unique session-signing key and cookie name.
Passwords, provider keys, local-model tokens, guardian credentials, and
encryption keys are generated or supplied independently and are never
copied, linked, inherited, or accepted across products.

## Installation and lifecycle contract

There is no generic family payload and another agent is not an Ubuntu Zombie
component target. Product source is co-located under `products/`, but every
package and installation remains independent. Ubuntu Zombie can nevertheless
manage installation as the root controller. Each installation remains one
product-owned transaction:

1. obtain that product's release and verify its artifact, checksum,
   signature, provenance, and SBOM;
2. inspect identities, names, paths, ports, units, and ownership markers
   for collisions before mutation;
3. review the exact product purpose, requested authority, settings, and
   planned host changes;
4. install only the product's identities, files, credentials, state,
   services, logs, receipts, and ownership markers;
5. run the product's health and security-boundary checks before recording
   success; and
6. let Ubuntu Zombie record a secret-free inventory result and the target's
   receipt reference when it initiated the transaction.

Direct installation runs the target entry point. Managed installation uses
the catalogue-pinned lifecycle and JSON contracts in
[`implementation.md`](implementation.md): Ubuntu Zombie fetches and verifies
the target release, displays the target's plan, references product-specific
secret files without retaining their values, invokes the same entry point,
and preserves both audit trails. It must not add `friend`, `flame`, `eric`,
or arbitrary persona targets to Ubuntu Zombie's component registry.

Every product defines these lifecycle operations:

| Operation | Required outcome |
| --------- | ---------------- |
| Install | Converges from a clean or valid existing state |
| Verify | Reads state and reports whether the declared installation is present |
| Doctor | Explains drift and product-specific recovery without mutation |
| Repair | Reasserts only known-safe product-owned state |
| Update | Verifies, backs up, migrates, validates, and health-checks one product |
| Rollback or recovery | Restores a known-good product state without weakening policy |
| Suspend or kill | Stops useful operation while following retention rules |
| Uninstall | Removes only owned resources and explicitly handles retained state |

## Update management

Ubuntu Zombie may offer one-agent and “update all agents” orchestration, but
it does not become a shared updater. A batch operation reads every
product's changelog, presents each plan, invokes product-owned updaters
serially, records per-product results, and stops or continues according to
an operator-approved failure policy. Each updater must:

- identify only installations carrying its ownership markers;
- verify its own release before privileged work;
- explain compatibility and state risks;
- preserve its passwords, keys, history, policy, and lifecycle unless a
  documented migration changes them;
- back up or snapshot state that a migration can damage;
- validate migrations before switching the running version;
- restart and health-check only its own services;
- audit the old version, new version, migration, and outcome;
- provide a product-appropriate rollback or recovery path; and
- leave every sibling's files and processes untouched.

Versions, release schedules, migration formats, and update acknowledgements
are never inherited from another product. A batch is not an atomic
transaction: a successful target remains successfully updated if a later
target fails, and every result remains independently recoverable.

## Co-installation contract

When products share a host:

- installers fail before mutation on identity, path, port, unit, command,
  cookie, or ownership collisions;
- no product requires a sibling to be installed;
- each listens on its own loopback port and owns only its firewall rules;
- each accepts only its own passwords, cookies, sessions, and reset flow;
- non-root service identities cannot enumerate or read sibling protected
  directories;
- direct or Zombie-managed update, repair, suspension, and uninstall affect
  only the selected target;
- every target implements the root-only, machine-readable request, response,
  ownership-marker, receipt, health, and audit contracts in
  [`implementation.md`](implementation.md);
- family membership does not imply management authority; a product may manage
  siblings only when its reviewed definition explicitly assigns that role and
  its implementation satisfies the same target-selection and audit contract;
  and
- peer-to-peer messaging, shared memory, shared credentials, shared
  approval queues, and shared audit logs remain absent.

## Defining the next agent

A future member is a deliberately designed and released product, not an
operator-authored persona file. Reserve a unique `products/<product-id>/`
root, copy [`template.md`](template.md), and answer at least:

1. What single human need does it serve?
2. Who uses it and who operates it?
3. What maximum authority does it require, why is each privileged capability
   necessary, and does that authority differ from Ubuntu Zombie?
4. Which tools, paths, destinations, and data does it need?
5. Which unique host and credential namespaces does it own?
6. What can never be shared with a sibling?
7. How does every lifecycle operation work?
8. Which Ubuntu Zombie lessons and privileged mechanisms are retained,
   changed, or removed?
9. What does this product measurably improve?
10. How will standalone and co-installation security be proved?
11. Which product-owned lifecycle interface may Ubuntu Zombie invoke, and
    what data must never enter its family inventory?

The proposal is incomplete until every open decision that affects
authority, data, credentials, installation, updates, or removal has an
owner and an acceptance test.

## Validation before hand-off

Each product root must test clean interactive and unattended installation,
required-input exit `64`, dry-run accuracy, idempotent
reinstall, permissions, unique authentication, malformed state, capability
allow and deny lists, updates from supported versions, migration failure,
rollback, diagnostics redaction, suspension, and uninstall.

Disposable Ubuntu VMs must also test every supported co-installation
combination. Record resource names, sibling file hashes, service start
times, cross-login rejection, service-account access failures, independent
updates, and selective uninstall results.

The product-specific negative suites begin with:

- **Ubuntu Zombie:** policy, approval, audit, TTL, reinstall, update, and
  root-capable behaviour remain unchanged; family management selects only
  the named target, invokes verified product-owned entry points, and
  produces matching manager and target audit evidence.
- **Imaginary Friend:** shell, host inspection, network access, workspace
  escape, self-modification, sibling reads, and cross-product login fail.
- **Curriculum Flame:** Friend denials also hold; child access cannot reach
  guardian data, unvalidated output never streams, curriculum bypass is
  blocked, and missing validators stop service.
- **ERIC:** generated output never becomes source evidence; citations and
  provenance cannot be fabricated; a compromised Twin cannot reach vault
  keys, alter the Constitution, transition lifecycle, or invoke the
  Executor.

## Documentation ownership

This catalogue records family definitions and links. Ubuntu Zombie's live
operating instructions remain at the repository root. Every later product
owns its README, vision, architecture, security and privacy models,
configuration, installation, upgrading, troubleshooting, release, and
disclosure documents below its reserved `products/<product-id>/` root.

ERIC must additionally own evidence and provenance schemas, its consent
model, Constitution and guardian formats, Executor authority mapping,
succession guide, data-protection assessment, and legal-review record.
