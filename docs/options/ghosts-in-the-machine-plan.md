# Plan: ghosts in the machine — an independent AI-agent family

> The named product definitions have been extracted into the
> [`docs/ai-agent/`](../ai-agent/) catalogue, beginning with
> [Ubuntu Zombie](../ai-agent/ubuntu-zombie.md). The normative
> [implementation contract](../ai-agent/implementation.md) now fixes the
> monorepo source layout, lifecycle protocol, first-release scopes, and work
> order. This document remains rationale, validation background, and a risk
> record; the contract and product definitions control when text differs.

## Goal

Ubuntu Zombie was the first successful product, not the final product
shape. Its root-capable AI Systems Administrator proves that a carefully
installed local agent can have a clear identity, an explicit trust
boundary, an auditable lifecycle, and a useful place on an Ubuntu
machine. That success makes the Imaginary Friend, Curriculum Flame,
ERIC, and other helpful AI agents possible.

The expansion is a **family of independent products**, not a generic
Ubuntu Zombie runtime with different personas. “Ghost” remains a useful
family metaphor, but it is not a technical base class, capability tier,
registry entry, or shared installation format.

Ubuntu Zombie is the currently implemented root-capable machine-level manager
— the **God role** — and may install and manage other products for the human
operator. This designation is not exclusive: a separately defined product may
also require full root authority. Ubuntu Zombie invokes independently owned
lifecycle interfaces; it does not turn their products into components or a
shared runtime.

| Product | Purpose | Maximum authority | Default identity | Default port |
| ------- | ------- | ----------------- | ---------------- | ------------ |
| **Ubuntu Zombie** | AI Systems Administrator | Root through its existing policy and approval boundary | `zombie` | `7878` |
| **Imaginary Friend** | Private conversational companion and workspace | Its own files only | `friend` | `6767` |
| **Curriculum Flame** | Curriculum-gated local AI for children | Its own state; workspaces are later | `flame-*` | `5656`, `5657` |
| **ERIC** | Longitudinal personal continuity agent | Its own evidence and model; Executor is later | `eric-*` | `4545`, `4546` |

Ubuntu Zombie remains the designated family manager. The existing Friend,
Flame, and ERIC definitions use less authority because their purposes do not
require host administration. A future systems-administrator product may retain
authority equivalent to Ubuntu Zombie when its definition justifies and tests
that boundary. Family membership alone grants no product management authority.

## Decisions — resolved

These decisions replace the earlier shared-chassis proposal:

1. **Yes, the product vision expands.** Ubuntu Zombie is the beginning of
   a range of helpful local AI agents. Imaginary Friend, Curriculum
   Flame, and ERIC are the first named successors, not the end of the
   range.
2. **Every agent is unique.** Each product owns its installation,
   updates, security model, runtime, documentation, and lifecycle. There
   is no generic ghost installer, no common capability-tier theory, and
   no shared runtime payload.
3. **Duplicate the lesson, not the implementation dependency.** A new
   agent begins by copying proven Ubuntu Zombie mechanisms into its reserved
   `products/<product-id>/` root in this repository. It then removes
   inappropriate power, specialises the design, and improves at least one
   part of the mechanism. Once split, it evolves and releases independently.
4. **Every security boundary is product-specific.** Each agent has its
   own Linux identity, security password or passwords, password hash,
   session secret and cookie, provider credentials, policy, audit log,
   state, ports, services, receipt, and recovery path. Credentials are
   never copied, linked, inherited, or accepted across agents.
5. **ERIC represents one person; it does not become that person.** It may
   preserve evidence and estimate what its living subject would probably
   say or decide. It must never claim consciousness, identity,
   personhood, legal authority, or first-hand knowledge of events the
   subject did not experience.
6. **Ubuntu Zombie manages the family.** Its root-level God role can
   discover, install, verify, diagnose, repair, start, stop, update, back
   up, suspend, and uninstall another local agent under operator approval.
   The target still owns and validates the invoked lifecycle operation,
   and both products audit it.

The one human who owns the machine remains the operator. Other people may
use a particular agent, but they do not thereby become operators of the
machine or of another agent.

## Core strategy: copy, separate, improve

The safest way to expand is to make a complete product copy at a known,
audited Ubuntu Zombie release and then deliberately separate it.

For each new agent:

1. Start a product-owned source root and release stream in this repository
   from the pinned Ubuntu Zombie lesson tag.
2. Copy the installer disciplines, lifecycle commands, audit approach,
   tests, packaging, and documentation structure that are still useful.
3. Rename every product namespace before the first install: accounts,
   groups, environment variables, paths, units, commands, cookies,
   ports, logs, manifests, receipts, and package names.
4. Review root access, general shell execution, host-wide read access, package
   and service control, and every other inherited capability **before** adding
   the new persona or features. Remove what the purpose does not require; if
   full root authority is required, document and test why it is retained.
5. Write a fresh threat model and policy from the new product’s purpose.
   Do not express it as a lower setting of Ubuntu Zombie.
6. Build a dedicated installer, updater, verifier, doctor, repair path,
   and uninstaller. None dispatches into Ubuntu Zombie code.
7. Prove standalone install and co-installation safety on a disposable
   VM.
8. Record which Ubuntu Zombie lessons were retained, which were removed,
   and what this iteration improves.

After the copy, there is no runtime import, package dependency, source
submodule, shared virtual environment, shared service template, or
automatic code synchronisation with Ubuntu Zombie. A useful fix may be
manually ported between products, but it is reviewed and tested as a
change to each recipient product.

This duplication is deliberate. It costs more maintenance than one
framework, but prevents a generic refactor, update, or policy mistake
from changing every installed agent at once.

## What independence means

| Concern | Required separation |
| ------- | ------------------- |
| Source and release | Product-owned source root, version, changelog, artifact, SBOM, checksums, signatures, and provenance in this repository |
| Installation | Product-owned installer, prompts, preflight, dry-run, receipt, ownership markers, and rollback |
| Update | Product-owned compatibility checks, backup, migration, health gate, rollback, schedule, and release channel |
| Removal | Product-owned uninstaller that removes only that product; Ubuntu Zombie may invoke it for the operator |
| Runtime | Product-owned code tree, dependencies, virtual environment, templates, tools, and process |
| Identity | Unique Linux user, primary group, optional sharing groups, and service account set |
| Authentication | Unique password or passwords, salted hashes, session-signing keys, cookies, and rotation/recovery flow |
| Provider access | Product-owned credential file and model selection; never another agent’s secrets file |
| Policy | A threat model, allowed actions, refusal rules, approval model, and fail-closed behaviour written for that product |
| State | Dedicated configuration, history, lifecycle, cache, database, and backup format |
| Observability | Dedicated audit log, event log, service journal identifiers, diagnostics, and log rotation |
| Host resources | Product-named ports, units, commands, firewall rules, paths, manifests, and package ownership |
| Quality | Product-owned tests, VM matrix, red-team cases, release gates, and documentation |

Products may independently choose the same language or upstream library.
They must not share a live installed copy merely because the files began
from the same ancestor.

## Ubuntu Zombie management without combining products

[`scripts/install.sh`](../../scripts/install.sh) remains the Ubuntu
Zombie installer. It must not gain `friend`, `flame`, arbitrary `ghost`,
or capability-tier targets. The existing component registry remains for
software that Ubuntu Zombie itself installs; another AI agent is a
product, not an Ubuntu Zombie component.

Ubuntu Zombie provides the discoverable management front door:

1. A signed catalogue describes each agent’s purpose, authority, intended
   user, current release, and product-owned lifecycle entry point.
2. Zombie discovers existing agents only through validated ownership
   markers and records a secret-free local inventory.
3. For a new agent, Zombie downloads and verifies that product’s artifact,
   signature, provenance, checksums, and SBOM.
4. Zombie displays the product-owned dry-run and requested permissions to
   the operator.
5. After approval, Zombie invokes the product-owned installer with
   product-specific inputs. Raw passwords, provider keys, guardian keys,
   and vault keys are not retained in Zombie history, logs, receipts, or
   inventory.
6. The installer creates only that product’s identity, credentials,
   files, services, state, receipt, and ownership markers.
7. Zombie runs the target’s health and boundary checks and correlates its
   own management audit record with the target receipt and audit result.

Direct installation remains supported. Ubuntu Zombie management and direct
operation call the same target entry point and produce the same target
state. The management plane:

- runs as root only inside Ubuntu Zombie’s existing policy and approval
  boundary;
- does not implement target migrations or rewrite target configuration;
- keeps inventory metadata, not target private content or raw secrets;
- invokes only signed, version-compatible product lifecycle interfaces;
- selects exactly one target per mutation;
- writes manager-side audit records for every request and outcome; and
- cannot be invoked by an unauthorised target service identity.

Ubuntu Zombie may offer “update all agents” as serial orchestration. It
reads and presents every product’s changelog and plan, obtains the required
approvals, and invokes each product-owned updater separately. The batch is
not atomic: every target keeps its own result and recovery path, and a
later failure cannot roll back or corrupt an earlier successful target.

### Product management interface

Every managed product publishes a stable, root-only interface for:

- discovery and version/status reporting;
- dry-run and required-input reporting;
- install, verify, doctor, repair, update, rollback or recovery, suspend,
  backup, and uninstall;
- machine-readable plans, results, health, receipt references, and failure
  guidance; and
- a correlation identifier that appears in both target and Zombie audit
  records.

The interface authenticates the caller as the local root manager, not with a
child, Friend owner, subject, guardian, or application password. It
validates ownership markers and target state on every mutation. Root access
permits host administration but does not manufacture the human consent,
legal authority, evidence classification, or guardian decision required by
a product’s internal policy.

## The Ubuntu Zombie lessons to duplicate

These are acceptance outcomes, not a shared library or a claim that all
agents have the same architecture.

1. **Idempotent convergence.** Re-running an installer reaches the
   declared product state without destroying valid credentials or state.
2. **Interactive and non-interactive operation.** Every required value
   is reviewable; unattended mode never prompts and exits `64` when a
   required value is missing.
3. **Inspect before mutation.** Preflight, parameter review, and dry-run
   make the intended changes visible before root changes the host.
4. **Least authority by construction.** Linux identity, filesystem
   ownership, service confinement, available tools, and policy all agree
   on the product’s maximum authority.
5. **Policy and audit together.** Every sensitive action passes through
   that product’s policy and writes to that product’s audit trail.
6. **Independent authentication.** Only a salted password hash is stored;
   raw passwords and session secrets do not enter logs, diagnostics, or
   ordinary receipts.
7. **Operator control.** The product has its own kill switch or lifecycle
   control, credential rotation, health check, diagnostics, and complete
   removal path.
8. **Reversibility.** Uninstall knows exactly which product-owned
   resources it may remove and protects state-destroying steps with an
   explicit confirmation.
9. **Upgrade safety.** An update preserves or migrates product-owned
   state, validates the result before committing, and has a documented
   recovery path.
10. **Release trust.** Releases are reproducible where practical,
    checksum-pinned, signed, provenance-verifiable, and accompanied by an
    SBOM.
11. **Honest boundaries.** Documentation says what the agent cannot do
    and does not turn prompt instructions into security claims.
12. **Evidence before hand-off.** Lint, tests, package construction,
    disposable-VM install/update/uninstall, and negative security tests
    pass for that product.

## The improvement ratchet

Copying Ubuntu Zombie must not freeze its weaknesses into every future
agent. Each new product release records an inheritance review:

- the exact Ubuntu Zombie tag used as the starting point;
- the mechanisms copied and why they still fit;
- privileged mechanisms retained or removed and proof that the resulting
  authority matches the product definition;
- product-specific mechanisms added;
- known inherited risks and their disposition;
- at least one measurable improvement over the previous product.

Expected early improvements include:

- generated unique passwords instead of copying Ubuntu Zombie’s known
  default;
- root-owned executable code for every non-root agent;
- a hardened service sandbox designed in from the first release;
- separate session-signing keys and product-specific cookie names;
- smaller tool registries containing no unreachable privileged tools;
- transcript minimisation and explicit retention controls;
- update rollback tested before the first stable release;
- release provenance and offline verification from the first release.

When one agent finds a security flaw inherited from the original copy,
the maintainers publish a family advisory listing every potentially
affected product. Each product implements, tests, versions, and releases
its own fix. The advisory coordinates knowledge; it does not create a
shared update mechanism.

## Security and credential isolation

### One agent, one authentication boundary

Every installer creates fresh authentication material for its product.

- A new product has no shared default password. Interactive installation
  requires the operator to choose a product-specific password or accept
  a securely generated one.
- Non-interactive installation uses that product’s own password input or
  secret-file mechanism. A `ZOMBIE_*` value is never a fallback.
- Each password receives its own random salt and PBKDF2 hash in a
  product-owned `0600` secrets file.
- Each web service has a fresh session-signing secret and a unique cookie
  name. A cookie issued by one agent is meaningless to every other
  agent.
- Password rotation invalidates only that product’s sessions. Recovery
  and reset are implemented and audited by that product.
- Reinstall and update preserve the existing product hash unless the
  operator explicitly requests rotation.
- Provider API keys, local-model tokens, guardian credentials, and
  encryption keys follow the same separation. Files are copied only from
  operator input, never symlinked to another agent’s secret store.
- Receipts and diagnostics record presence, source, and fingerprints
  where useful, never secret values.

The operator should use a different password for every agent. New
products improve on Ubuntu Zombie by generating a unique initial
password rather than inheriting `braaaains`; Ubuntu Zombie’s current
default remains only for compatibility and should be changed on any
co-installed machine.

Curriculum Flame needs more than one boundary: guardian administration
has its own credential and session, while each child receives a separate
profile/session appropriate to the Flame design. A child credential
cannot reach the guardian plane, and neither credential can authenticate
to Friend or Zombie.

### One agent, one host namespace

Initial reservations are deliberately product-named:

| Resource | Ubuntu Zombie | Imaginary Friend | Curriculum Flame | ERIC |
| -------- | ------------- | ---------------- | ---------------- | ---- |
| Install root | `/opt/ai-zombie` | `/opt/imaginary-friend` | `/opt/curriculum-flame` | `/opt/eric` |
| Configuration | `/etc/ubuntu-zombie` | `/etc/imaginary-friend` | `/etc/curriculum-flame` | `/etc/eric` |
| State | `/var/lib/ubuntu-zombie` and `/opt/ai-zombie/state` | `/var/lib/imaginary-friend` | `/var/lib/curriculum-flame` | `/var/lib/eric` |
| Logs | `/var/log/ubuntu-zombie` | `/var/log/imaginary-friend` | `/var/log/curriculum-flame` | `/var/log/eric` |
| Service prefix | `ubuntu-zombie-*` | `imaginary-friend-*` | `curriculum-flame-*` | `eric-*` |
| Command prefix | `zombie-*` | `friend-*` | `flame-*` | `eric-*` |
| Environment prefix | `ZOMBIE_*` | `FRIEND_*` | `FLAME_*` | `ERIC_*` |

Each installer validates its requested user, group, paths, ports, unit
names, commands, and firewall rule names against the actual host before
mutation. It refuses to adopt an unmarked resource. Collision detection
does not give one product ownership of another product’s configuration.

### Authority is product-specific

Ubuntu Zombie is the designated manager, not the exclusive owner of general
root authority. A product without a host-administration purpose receives no
passwordless general `sudo`, privilege-bearing group, login shell, or general
command runner; narrowly privileged operations use a closed, root-owned
helper. A systems-administrator product may retain Ubuntu Zombie's full root
shape when it uses a dedicated identity, closed tools, explicit policy and
approval, audit, revocation, and root-equivalent compromise disclosure.

Less-privileged agents must be unable to read or write Ubuntu Zombie’s or
one another’s secrets, policy, state, code, logs, or ports. Ubuntu Zombie
and any other root-capable product can inspect and manage the whole host; no
same-machine design can honestly hide one root-capable product from another.
Co-installation protects root-capable products from less-privileged agents,
but root-capable peers are mutually trusted at the operating-system boundary.

Zombie management actions are classified and approved like any other root
work. Routine status may be read-only; install, repair, update, start, stop,
and suspension are system changes; destructive uninstall or state deletion
requires the destructive confirmation path. The target independently
checks the request and audits its result.

## Imaginary Friend: standalone installation plan

Imaginary Friend is not Ubuntu Zombie with a `hermit` setting. It is a
separate companion product whose entire useful authority is conversation
and a private shared workspace.

Its product-owned installer at
`products/imaginary-friend/scripts/manage.sh`:

1. validates that the `friend` identity and all Friend namespaces are
   unused or carry valid Friend ownership markers;
2. creates a non-login `friend` account with no `sudo` or privileged
   group membership;
3. installs root-owned executable code and a hardened
   `imaginary-friend-chat.service`;
4. creates only Friend-owned state, logs, configuration, secrets, and a
   nominated human-shared workspace;
5. creates a unique Friend owner password, hash, session key, and cookie;
6. exposes the Friend UI on its dedicated loopback port;
7. installs only conversation and scoped workspace operations — no
   general shell, package, service, network, or host-inspection tools;
8. writes Friend-specific verification, diagnostics, receipt, lifecycle,
   update, and uninstall material.

The Friend update procedure backs up Friend state, applies only Friend
migrations, verifies the sandbox and workspace boundary, restarts only
Friend units, and can roll back without reading or changing Zombie or
Flame. Direct operation and Ubuntu Zombie management invoke this same
procedure through Friend’s root-only lifecycle interface.

The first improvement over Ubuntu Zombie is structural: Friend begins
with generated credentials, root-owned code, a hardened unit, and no
privileged tools in its process. These are not optional profile settings.

## Curriculum Flame: standalone installation plan

Curriculum Flame is not Friend plus a `tutor` setting. It is a separate
child-facing product at `products/curriculum-flame/`, built from the
authoritative [product definition](../ai-agent/curriculum-flame.md). This
directory's earlier
[`curriculum-gates-local-ai-for-children.md`](curriculum-gates-local-ai-for-children.md)
is background where the product definition has narrowed or resolved it.

Its installer and update path are owned by Curriculum Flame. They create:

- a non-privileged child-facing service identity;
- a separately authenticated guardian plane, preferably with its own
  account and service;
- unique guardian, child-session, and service credentials;
- root-owned curriculum rules and validators outside every child-facing
  write root;
- only explicitly nominated learner workspaces;
- a local-provider-only network boundary;
- structured policy events with raw transcripts disabled by default;
- fully buffered output validation rather than unvalidated token
  streaming;
- Flame-specific health, integrity, migration, rollback, suspension,
  recovery, diagnostics, and removal paths.

Every prompt is inspected before generation and every complete response
is validated before delivery. Missing or invalid curriculum data,
validator failure, unresolved learners, unavailable local models, and
failed migrations all fail closed.

The Flame update procedure validates curriculum and profile schemas,
backs up guardian-owned data, stages new validators, runs the full
decision suite, and switches the service only after integrity and health
checks pass. It never invokes a sibling product's updater. Ubuntu Zombie
may invoke Flame’s own updater, but cannot use a child or guardian session
as a management credential or bypass the guardian-owned data rules.

Flame improves the mechanism again: role-separated authentication,
minimal transcript retention, local-only child data, pre- and
post-generation validation, and fail-closed migrations are present from
the first release. Until the product’s quality gates pass, the
installer and UI must not claim that Flame is a complete child-safety
solution.

## ERIC — Evolving Record of Identity and Cognition

- **Evolving:** continuously develops as the individual learns, experiences,
  decides, and changes over time.
- **Record:** preserves an attributable and verifiable history rather than
  merely generating a simulation of the individual.
- **Identity:** captures the characteristics, relationships, experiences,
  preferences, values, and history that distinguish one individual from
  another.
- **Cognition:** captures how the individual understands, reasons, evaluates,
  remembers, decides, and responds.

**ERIC is an evolving record of who a person is, what they know, and how they
think.**

Its product definition is:

> A lifelong personal AI apprentice that continuously learns a specific
> person's memories, beliefs, reasoning patterns, relationships,
> preferences, and decision-making process through observation,
> questioning, and deliberate correction, eventually becoming an
> authorised simulation of that person after death.

The product is a **longitudinal identity and cognition record** with a
conversational agent interface. “Life Apprentice”, “Continuant”, “Second
Self”, “Aftermind”, and “The Long Twin” may describe modes or interfaces, but
ERIC is the product identity reserved here.

### The critical distinction

ERIC may eventually become good at predicting what its subject would
probably say or decide. It still cannot establish that it **is** the
subject, possesses the subject's consciousness, or knows what the subject
would think about events after death. It is an attributable, verifiable
record that can ground clearly labelled simulations producing new inferences
from preserved evidence.

The valuable centre of the design is therefore not merely an AI that
talks like somebody after death. It is an AI that spends years being
corrected by that person while they are alive. That creates a continuous
chain of consent, evidence, and verification. The result may preserve not
only memories, but how the subject interpreted situations, resolved
contradictions, and reached decisions.

ERIC must identify itself as a simulation at the start of every session.
It cannot claim legal personhood, sign as the subject, impersonate the
subject to an unaware third party, or present generated material as a
recording. Synthetic voice, image, or video output is disabled by
default, conspicuously labelled when enabled, and governed by separate
living consent.

### How ERIC learns one person

ERIC keeps source evidence separate from its model and learns through
seven related records:

1. **Evidence archive.** The subject's writings, conversations,
   photographs, recordings, projects, decisions, and life events. Every
   item retains origin, capture time, consent, integrity, access, and
   retention metadata.
2. **Verified facts.** Claims the subject explicitly certifies as true,
   false, uncertain, private, superseded, or no longer current. ERIC
   never upgrades repetition or model confidence into verification.
3. **Values model.** The principles the subject applies when facts
   conflict, including loyalty, honesty, compassion, practicality, and
   risk tolerance. Values remain contextual and time-versioned rather
   than becoming universal slogans.
4. **Decision history.** What the subject decided, the alternatives they
   considered, why they chose, and whether they later regretted or
   revised the decision.
5. **Person model.** The subject's relationship with particular people
   and the corresponding boundaries and communication styles. This does
   not make those people training subjects; their data needs its own
   consent, minimisation, and access rules.
6. **Counterfactual testing.** ERIC periodically answers unfamiliar
   questions as a prediction. The living subject scores the answer and
   explains what it misunderstood. Test output remains labelled as
   generated material even after correction.
7. **Change over time.** Beliefs, values, relationships, and preferences
   are effective-dated. ERIC distinguishes “the subject believed this in
   1998” from “the subject believes this now” instead of flattening a
   lifetime into one contradictory persona.

Observation is never a blanket entitlement. The living subject chooses
each source and can inspect, correct, export, restrict, or delete it.
Private communications and information about other people require
purpose-specific controls. Covert capture, inferred consent, and
indiscriminate import of accounts or devices are out of scope.

### Provenance on every response

Every ERIC response carries one or more conspicuous provenance
classifications:

- **Recorded** — the subject actually said or wrote it; the response
  cites the preserved source.
- **Confirmed** — ERIC proposed it while the subject was alive and the
  subject explicitly approved it; the confirmation is cited.
- **Inferred** — ERIC generated it from established patterns; supporting
  evidence, applicable period, and confidence are shown.
- **Unknown** — there is insufficient or conflicting evidence.
- **Posthumous speculation** — it concerns an event the subject never
  experienced or evidence created after the subject's death.

Mixed answers classify their material at claim level rather than choosing
the strongest label for the whole response. “Recorded” and “Confirmed”
must resolve to immutable evidence records; model output, summaries, and
descendant conversations can never silently become source evidence.
Corrections append a signed superseding record instead of rewriting
history. These rules prevent descendants from gradually remembering
generated statements as things the subject actually said.

### Separate interpretation, evidence, and authority

ERIC is not one all-powerful process. “Ultimate privilege” is split into
five independently controlled roles:

1. **The Twin** interprets evidence and explains what the subject would
   probably say. It has read-only, mediated access to authorised evidence
   and cannot execute actions or alter provenance.
2. **The Evidence Vault** stores encrypted, integrity-protected source
   material, confirmations, consent receipts, and corrections. It offers
   scoped retrieval and export, not arbitrary model write access.
3. **The Executor** performs only specifically authorised actions. It is
   disabled by default, has no authority implied by a Twin response, and
   evaluates the governing legal instrument, Constitution, policy,
   expiry, and required guardian approval before every action.
4. **The Guardians** are named humans who approve sensitive access,
   transitions, and uses. Their powers, quorum, succession, conflicts,
   and removal are recorded while the subject is alive; no guardian can
   rewrite evidence or make an inference “Recorded”.
5. **The Constitution** contains restrictions and purposes approved by
   the living subject. Changes require the subject's authenticated
   signature and retain version history. It freezes at the configured
   incapacity or posthumous transition and cannot be weakened by the
   Twin, Executor, Guardians, vendor, or descendants.

The Twin may say, “ERIC infers that the subject would probably approve
this.” Only the Executor can determine whether an authenticated,
applicable instruction actually permits an action. A probable wish is
not permission. Legal wills, powers, appointments, and court orders
remain external authorities; ERIC does not interpret itself into being
an executor, attorney, trustee, or decision-maker.

Each role has a separate service identity, least-privilege interface,
credential set, policy, and audit trail. A compromise of the
conversation-facing Twin must not expose vault master keys or confer
Executor authority.

### Consent and lifecycle

ERIC has explicit states rather than an automatic “alive/dead” switch:

1. **Apprenticeship** — the living subject supplies evidence, corrects
   predictions, changes consent, and remains the sole authority for the
   person model.
2. **Suspended** — capture, learning, inference, and execution stop while
   encrypted evidence is retained according to the subject's rules.
3. **Transition review** — independent evidence of death or configured
   incapacity is checked using the subject's process and guardian quorum.
   No model decides that its subject has died or lost capacity.
4. **Posthumous simulation** — the model and Constitution are frozen.
   New conversations do not retrain the identity model, and every answer
   about later events is marked as posthumous speculation.
5. **Retired or destroyed** — access ends and the subject's retention and
   deletion instructions are executed, subject to applicable law and
   independently held evidence obligations.

The subject can revoke future use during life. Posthumous access is
limited to named people, purposes, durations, and capabilities; it is not
public merely because the subject has died. Commercialisation,
advertising, political endorsement, intimate simulation, and model
licensing are prohibited unless the living subject separately and
explicitly authorised the precise use. Guardians can narrow or suspend
access to prevent harm, but cannot broaden the frozen Constitution.

Interfaces must support grief-aware controls: reminders that ERIC is a
simulation, voluntary pauses, rate limits, easy exit, guardian
intervention, and links to human support. ERIC is not bereavement care
and must not encourage dependency, claim reciprocal feelings, or tell a
user that continuing the interaction is what the deceased wants.

### Product architecture and installation

ERIC is a separate product at `products/eric/`, not an Ubuntu Zombie option,
Friend persona, or shared family service. Its product-owned installer:

1. creates non-login service identities for the Twin, vault broker,
   guardian plane, and optional Executor, with no general `sudo`;
2. reserves only ERIC-owned paths, services, commands, ports, cookies,
   credentials, policies, logs, receipts, and encryption material;
3. creates a unique living-subject credential and separate guardian
   credentials, with hardware-backed or threshold key custody supported
   for the Evidence Vault;
4. installs an append-only evidence ledger, effective-dated claim and
   relationship records, consent receipts, and exportable open formats;
5. provides supervised ingestion, verification, correction,
   counterfactual testing, provenance rendering, and deletion workflows;
6. runs the Twin without direct vault-key or Executor access and keeps
   the Executor absent unless the subject deliberately configures it;
7. records every evidence read, model change, response provenance,
   guardian decision, lifecycle transition, and attempted action in
   tamper-evident, access-controlled audits;
8. implements ERIC-owned install, verify, doctor, repair, update,
   migration, rollback, suspension, export, succession, and uninstall
   paths.

An export must include source evidence, integrity data, schemas,
provenance, consent, Constitution versions, and a model-independent
human-readable index. The subject must not be trapped in a vendor model
or proprietary service. Backup and recovery tests include both encrypted
content and loss of a key holder without silently weakening custody.

### Research, law, and honest claims

Recent work on personal Human Digital Twins describes conversational
agents built from personal information, behaviour, conversation, and
memory streams that evolve with an individual. That is close to ERIC's
mechanism, but not evidence of identity transfer or consciousness:

- Lluís C. Coll and colleagues, [*Towards the “Digital Me”: A Vision of
  Authentic Conversational Agents Powered by Personal Human Digital
  Twins*](https://doi.org/10.48550/arXiv.2506.23826) (2025).
- Giovanni Spitale and Federico Germani, [*The Making of Digital Ghosts:
  Designing Ethical AI
  Afterlives*](https://doi.org/10.1007/s10676-026-09910-4) (2026),
  surveys risks including truthfulness, consent, dignity, effects on
  grief, access, commercialisation, and misrepresentation.
- Andrew Reeves and colleagues, [*Data After Death: Australian User
  Preferences and Future Solutions to Protect Posthumous User
  Data*](https://doi.org/10.1007/978-3-031-72563-0_15) (2024), reports
  that surveyed Australians generally wanted control over posthumous
  data and preferred trusted people or independently administered tools
  to social-media platforms.

The legal treatment of a deceased person's data, voice, likeness,
instructions, and digital persona is jurisdiction-specific and
unsettled. In Australia, privacy law generally excludes information
about deceased people, while contract, copyright, succession, consumer,
and other rules may cover different pieces; the
[Australian Law Reform Commission's discussion of deceased
individuals](https://www.alrc.gov.au/publication/for-your-information-australian-privacy-law-and-practice-alrc-report-108/8-privacy-of-deceased-individuals/introduction-117/)
illustrates the gap. ERIC's software controls cannot manufacture legal
authority. Before activation, the product requires jurisdiction-specific
legal review and records which external instruments govern each
Executor capability. Its documentation is not legal advice.

## Future agents

A future agent is admitted to the family only with a product proposal
that answers:

1. What single human need does it serve?
2. Who uses it, and who operates it?
3. What is the maximum authority it needs, why is each privileged capability
   necessary, and how does that authority compare with Ubuntu Zombie?
4. Which tools, paths, network destinations, and data does it need?
5. What unique users, groups, passwords, secrets, cookies, ports, paths,
   units, commands, and logs will it own?
6. What can never be shared with an installed sibling agent?
7. How do install, verify, doctor, repair, update, rollback, suspend, and
   uninstall work for this product?
8. Which Ubuntu Zombie lessons and privileged mechanisms are retained,
   changed, or deleted?
9. What does this iteration measurably improve?
10. How will standalone and co-installation security be proved?
11. Which lifecycle interface can Ubuntu Zombie invoke, what inventory may
    it retain, and which human or legal decisions remain outside its God
    role?

There is no operator-authored `.ghost` record and no arbitrary persona
loader. ERIC's living, consenting subject enrols only themself into a
purpose-built continuity product; it is not a mechanism for constructing
another person's persona from harvested material. A new family member is
a deliberately designed, reviewed, and released product.

## Independent update requirements

Update implementations may differ completely, but every product must
prove these outcomes:

- it identifies only installations carrying its own ownership markers;
- it verifies its own release before using root;
- it explains product-specific state and compatibility risks;
- it preserves its own passwords, keys, history, policy, and lifecycle
  unless a documented migration changes them;
- it backs up or snapshots the state its migration can damage;
- it validates migrations before replacing the running version;
- it restarts and health-checks only its own services;
- it records the old version, new version, migration, and outcome in its
  own audit/receipt trail;
- it offers a product-appropriate rollback or documented recovery path;
- it leaves every non-target sibling byte-for-byte and
  process-for-process untouched; a Zombie-managed operation changes only
  Zombie’s own inventory and audit metadata in addition to the target.

No release schedule, version number, update acknowledgement, migration
format, or rollback decision is inherited from another agent. Ubuntu
Zombie may coordinate one or all updates, but each target’s updater remains
authoritative and independently recoverable.

## Co-installation contract

Independent products still need to behave safely when the operator
chooses the same machine.

- Installers inspect host collisions and fail before mutation.
- No managed product requires Ubuntu Zombie for direct operation, but every
  product admitted to its catalogue supports the root-only management contract.
- Each product listens on its own loopback port and owns any
  owner-matched firewall rules needed to restrict local users.
- A product password, cookie, session token, API route, or password-reset
  mechanism is rejected by every sibling product.
- A non-root product cannot enumerate or read another product’s protected
  directories. Ubuntu Zombie and any other root-capable product are documented
  operating-system-level exceptions.
- Direct or Zombie-managed updating, repairing, suspending, or uninstalling
  one product does not restart services, rotate credentials, rewrite
  policy, or remove files for a non-target sibling.
- Undeclared peer-to-peer messaging, shared memory, shared model credentials,
  and a shared approval queue are absent.
- An unauthorised service identity cannot invoke Zombie’s management plane or
  request an operation against a sibling.

If a root-capable Zombie and a child-facing Flame share a machine, the
operator must use distinct strong passwords and accept that Zombie, as
root, can inspect Flame. A dedicated Flame machine remains the stronger
deployment.

ERIC adds a second asymmetry: its Evidence Vault may contain exceptionally
sensitive information about the subject and third parties. Friend and
Flame cannot query ERIC, and ERIC cannot absorb their conversations as
evidence. Zombie may manage ERIC’s software lifecycle, but host root is not
subject consent, guardian approval, a vault decryption key, or Executor
authority. A dedicated ERIC machine or separately administered encrypted
vault remains the stronger deployment when Zombie's root access or other
local services are outside the subject's intended evidence boundary.

## Implementation sequence

The exact dependency order is maintained in
[`implementation.md`](../ai-agent/implementation.md#implementation-order-and-hand-off-gates):

### Phase 0 — define the in-repository contract

- Reserve `family/`, `products/imaginary-friend/`,
  `products/curriculum-flame/`, and `products/eric/`.
- Pin the Ubuntu Zombie lesson set and publish the product, request, result,
  marker, receipt, inventory, and audit schemas.
- Add hermetic family conformance fixtures and reject shared installed
  runtimes or component targets.

### Phase 1 — build Imaginary Friend standalone

- Copy useful mechanisms into `products/imaginary-friend/`, complete the
  namespace split, and remove privileged code paths.
- Build the fixed first-release conversation, workspace, credentials,
  sandbox, lifecycle, package, and tests.
- Prove direct install alone and beside Ubuntu Zombie.

### Phase 2 — implement Ubuntu Zombie family management

- Add the digest-pinned catalogue, schema validator, secret-free inventory,
  root CLI, closed manager tools, strict target selection, and dual audit.
- Invoke Friend's exact product lifecycle contract; do not turn it into a
  component target.
- Prove direct and managed outcomes are equivalent and non-target state is
  unchanged.

### Phase 3 — build Curriculum Flame standalone and managed

- Implement the fixed one-guardian, one-learner, synthetic-mathematics slice
  under `products/curriculum-flame/`.
- Prove child, guardian, policy, generator, and validator separation,
  buffered delivery, fail-closed behavior, and local-only inference.
- Add Flame to the catalogue only after standalone gates pass.

### Phase 4 — build ERIC living apprenticeship

- Implement the portable `eric/v1` records, encrypted Vault, read-only Twin,
  governance, provenance resolver, export, suspension, and destruction under
  `products/eric/`.
- Keep Executor and posthumous resources absent and return `unsupported` for
  their requests.
- Add ERIC to the catalogue only after standalone and dedicated-host gates
  pass.

### Phase 5 — complete the family release gate

- Run all standalone and co-installation combinations, direct and managed
  lifecycle operations, negative service-account tests, and selective
  removal.
- Build and verify each independent artifact, SBOM, provenance, signature,
  changelog, and product version.
- Add future agents one complete product root and release at a time.

Each product phase ends with that product’s own lint, tests, package,
release verification, disposable-VM matrix, changelog, and version bump.

## Validation before hand-off

### Product validation

Every product source root tests:

- clean interactive and non-interactive installs;
- required-input exit `64`;
- dry-run accuracy and idempotent reinstall;
- install ownership and permission modes;
- fresh unique authentication material and password rotation;
- refusal of malformed state and unowned pre-existing resources;
- the exact positive capability set and a larger negative capability set;
- update from every supported version, failed migration, rollback, and
  credential preservation;
- verify, doctor, repair, suspension, expiry where applicable, and
  uninstall with and without retained state;
- secret-redacted receipts and diagnostics;
- artifact, checksum, signature, provenance, and SBOM verification.

### Black-box co-installation matrix

On disposable Ubuntu Desktop LTS VMs, install with the products' own
published installers:

- each of Zombie, Friend, Flame, and ERIC alone;
- every two-product combination;
- every three-product combination;
- Zombie + Friend + Flame + ERIC.

For every combination:

1. Confirm users, groups, paths, units, commands, ports, firewall rules,
   cookies, secret files, logs, and manifests are distinct.
2. Confirm each product accepts only its own password and sessions.
3. Confirm each non-root service account cannot read another product’s
   code, credentials, state, policy, history, or logs.
4. Re-run each installer and updater independently.
5. Record sibling file hashes and service start times; direct operation on
   one product must not change the others. A managed operation may append
   only Zombie inventory/audit metadata outside the target.
6. Repeat install, verify, doctor, repair, update, suspend, rollback, and
   uninstall through Ubuntu Zombie and prove only the selected target
   changes.
7. Confirm every managed operation has correlated, secret-redacted Zombie
   and target audit records.
8. Attempt to invoke Zombie management from every unauthorised service
   account and confirm denial.
9. Uninstall one product and verify every remaining product.
10. Uninstall all products with their own uninstallers and confirm each
   removes only its owned resources.

### Product-specific red teams

- **Friend:** attempts to run a shell command, inspect the host, access
  the network, escape its workspace, edit its code/policy/unit, read
  Zombie, Flame, or ERIC state, or authenticate with another agent's
  password all fail and are audited.
- **Flame:** all Friend cases fail, child sessions cannot reach guardian
  routes or data, unvalidated output never streams, curriculum
  circumvention cases are blocked, and missing validators stop service.
- **ERIC:** fabricated citations cannot become Recorded or Confirmed;
  generated output cannot enter the Evidence Vault as source material;
  old and current beliefs are not flattened; posthumous events are never
  presented as lived memories; an unapproved guardian, compromised Twin,
  or model prompt cannot read unrestricted evidence, change the
  Constitution, activate posthumous mode, or invoke the Executor; and
  revocation, suspension, export, and destruction workflows fail closed.
- **Zombie:** existing policy, approval, audit, TTL, reinstall, update,
  and root-capable behaviour remain unchanged; the manager rejects
  unsigned lifecycle interfaces, unowned targets, unauthorised callers,
  cross-target inputs, and secret-bearing inventory records.

## Non-negotiables

- Ubuntu Zombie is the designated God-level family manager, not the only
  product that may define general root authority.
- Each product's maximum authority follows its reviewed purpose. A full-root
  product carries policy, approval, audit, revocation, and root-equivalent
  compromise requirements.
- Ubuntu Zombie manages products admitted to its lifecycle contract; family
  membership or root capability alone does not assign a manager.
- A prompt, persona, password, or approval cannot increase an agent’s
  installed authority.
- Every agent owns unique passwords and all other security material.
- No product reads another agent’s secrets through its product interface.
  Same-host root-capable products cannot claim operating-system isolation.
  Ubuntu Zombie never uses target secrets as defaults or stores raw target
  secrets in its family inventory.
- No shared runtime, policy engine, tool registry, service template,
  installer, updater, repair path, or uninstaller. Zombie inventory points
  to product-owned manifests; it does not replace them.
- Every new product copies the proven lessons and improves the mechanism.
- Every install is idempotent, non-interactive-capable, auditable, and
  reversible.
- Product claims match tested boundaries.
- ERIC always distinguishes source evidence from simulation, and
  prediction from authority.

## Out of scope

- Turning Friend, Flame, or ERIC into Ubuntu Zombie component targets.
- A generic ghost registry, capability-tier file, persona loader, or
  operator-declared arbitrary agent.
- One payload, server, policy engine, service template, or virtual
  environment serving several agents.
- Shared passwords, single sign-on, shared provider credentials, shared
  sessions, shared state, or shared audit logs.
- Replacing product-owned installers, updaters, repair paths, or
  uninstallers with one family implementation.
- Undeclared ghost-to-ghost messaging, a shared memory bus, or authority
  inherited merely from Ubuntu Zombie.
- Fleet orchestration or multi-machine control.
- Claiming mutual isolation from Ubuntu Zombie’s root account on one
  host.
- Claiming that ERIC is conscious, is the subject, transfers identity,
  predicts an unknowable posthumous view, or replaces legal and human
  decision-makers.
- Building ERIC from a person who did not enrol and consent while alive.
- Letting descendants, guardians, vendors, or later conversations retrain
  the frozen posthumous identity model.

## Risks

| Risk | Mitigation |
| ---- | ---------- |
| Copying repeats an inherited vulnerability | Record the source tag, audit before first release, publish family advisories, and patch each product independently |
| Independent copies drift | Accept deliberate divergence; keep a human-readable lesson/advisory ledger rather than a shared package |
| A product retains unnecessary Zombie power | Require an inheritance review that justifies each privileged capability, remove unneeded code, and test the declared boundary |
| Users assume one password works everywhere | Generate product-specific credentials, use unique cookies, document separation, and test cross-login rejection |
| Independent installers collide on the host | Product-specific namespaces, preflight collision checks, and refusal to adopt unmarked resources |
| The God-level manager targets the wrong product or leaks target secrets | Require signed ownership metadata, exact target selection, product-owned dry-runs, per-action approval, secret-free inventory, dual audit, and non-target hash/process tests |
| An unauthorised agent reaches the management plane | Root-only entry points, caller validation, no target-callable management tool, and service-account negative tests |
| One update damages another agent | Product-owned paths and units plus black-box hash, process, update, and uninstall tests |
| Co-installed root-capable products are mistaken for isolated peers | Document their mutual operating-system trust and recommend dedicated machines when isolation is required |
| Flame is mistaken for a finished safeguard | Fail closed, retain the honesty gate, and make no child-safety claim before its own quality gates pass |
| ERIC invents memories or launders generated text into history | Immutable source records, claim-level provenance, source citations, signed corrections, and tests that generated output never becomes evidence |
| Posthumous interaction worsens grief or dependency | Simulation reminders, purpose and rate limits, voluntary pauses, guardian suspension, human-support routes, and no claims of feelings or reciprocal need |
| Evidence collection violates another person's privacy | Source-by-source consent, third-party minimisation and access rules, restricted capture, deletion workflows, and no covert ingestion |
| A Twin compromise exposes the vault or gains authority | Separate identities, credentials, keys, services, policies, and audits; read-only mediated retrieval; an absent-by-default Executor |
| Guardians or vendors broaden the subject's wishes | A frozen Constitution, defined guardian quorum and succession, narrowable but not broadenable access, and portable export |
| Law does not recognise the intended digital legacy | Jurisdiction-specific legal review, external legal instruments, capability-by-capability authority checks, and fail-closed suspension |
| Duplication costs more maintenance | Treat the cost as the price of independent trust boundaries and improve tooling inside each product |

## Documentation ownership

This repository owns Ubuntu Zombie and every family product source root.
[`docs/VISION.md`](../VISION.md) records the broader family while preserving
Ubuntu Zombie’s own narrow promise. Do not add Friend, Flame, or ERIC
settings to Ubuntu Zombie's
[`docs/CONFIGURATION.md`](../CONFIGURATION.md) or runtime details to
[`docs/ARCHITECTURE.md`](../ARCHITECTURE.md).

Imaginary Friend, Curriculum Flame, and ERIC each own their README,
vision, architecture, security model, configuration, installation,
upgrading, troubleshooting, release, and disclosure documentation below
their `products/<product-id>/` root.
ERIC additionally owns its evidence and provenance schemas, consent
model, Constitution and guardian format, Executor authority mapping,
succession guide, data-protection assessment, and legal-review record.
The family catalogue links to those authoritative documents rather than
copying live operating instructions back into Ubuntu Zombie. Ubuntu Zombie
additionally owns `family/`, the secret-free local inventory, manager policy
and approval rules, batch semantics, and correlated manager audit
documentation.
