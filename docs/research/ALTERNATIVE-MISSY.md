# Deep Lessons from Missy (`MissyLabs/missy`)

This document is a deep companion to [`ALTERNATIVES.md`](ALTERNATIVES.md)
and [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md). Of every
project in that catalogue, **Missy** is the closest single-host analog
to Ubuntu Zombie — same threat model (one machine, one operator, hostile
network assumed), same instinct (default-deny everything the agent can
touch), same shape (signed audit log + interactive approval + policy
engine in front of every privileged call).

That closeness makes it the most useful project to learn from in
detail. It is also the most dangerous to copy from naively: Missy ships
a *very* large surface area (multi-channel runtime, voice nodes, vision
subsystem, scheduler, code evolution, FAISS memory, sub-agents,
attention/sleep subsystems, REST "agent-as-a-service" API), and Ubuntu
Zombie is deliberately the opposite — a small bash installer that adds
one Unix account and an audited approval loop on top of stock Ubuntu
LTS.

The job of this file is to read Missy through the Ubuntu Zombie filter
defined in [`VISION.md`](VISION.md) — *Ubuntu LTS + a real local Unix
account + a private Tailscale interface + an LLM under human approval*
— and decide, capability by capability, what to **borrow**, what to
**translate**, what to **defer**, and what to **explicitly refuse**.

## What Missy actually is, in one paragraph

Missy is a self-hosted, Python-based agentic platform for Linux that
treats the agent's own capabilities as untrusted by default. Network,
filesystem, and shell access are all closed at boot; the operator opens
them with named policies (CIDRs, domains, paths, command whitelists,
even HTTP method + path per host). Every outbound request from the
runtime, the providers, the tools, the plugins, and the MCP servers
flows through a single `PolicyHTTPClient` enforcement point. Every
policy decision, provider call, and tool execution is written as a
JSONL event signed by the agent's own Ed25519 identity at
`~/.missy/identity.pem`. An interactive Rich-based TUI surfaces
policy-denied operations as *allow once / deny / allow always*
prompts. On top of that core sit a multi-provider runtime (Anthropic,
OpenAI, Ollama with fallback and hot-swap), an encrypted ChaCha20-
Poly1305 vault for secrets, a prompt-injection sanitiser, a secrets
detector that censors responses, optional Landlock LSM enforcement,
optional Docker sandboxing, MCP digest pinning, and a long tail of
agent-research features (attention/sleep/condensers/playbook/graph
memory/sub-agents/code evolution).

Ubuntu Zombie is much smaller. The interesting question is which
*primitives* from Missy are load-bearing for the security posture
Ubuntu Zombie promises in [`VISION.md`](VISION.md), and which are
research-grade additions that would blow up the MVP if imported.

## The axis-by-axis comparison

| Axis                          | Missy                                                                                            | Ubuntu Zombie                                                                              | Implication                                                                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Host target                   | Any Linux with Python 3.11+                                                                      | Supported Ubuntu Desktop **LTS** only                                                       | Missy pays portability tax; Zombie should keep cashing the LTS-only simplification.                                                                  |
| Install shape                 | `pip install -e .` + `missy setup` wizard, lives in `~/.local/share/missy`                       | Transparent bash installer that creates a real Unix account                                | Missy is a *user-space app*; Zombie is a *system change*. Zombie's audit/approval story has to survive that escalation.                              |
| Privilege model               | Runs as the invoking user; shell access is opt-in and command-whitelisted                        | Dedicated `zombie` account with passwordless `sudo`                                        | Zombie is strictly more privileged. Every Missy safety primitive needs to be *stronger* in Zombie, not weaker.                                       |
| Interface                     | CLI REPL + Discord + Webhooks + Voice nodes + Screencast + REST API                              | Private chat surface, Tailscale-only inbound, no public listener                           | Missy's surface is wide; Zombie's is one-channel and private. Borrow Missy's per-channel policy idea, not its channel count.                         |
| Inference                     | Multi-provider with hot-swap and fallback (Anthropic / OpenAI / Ollama)                          | Cloud LLM in MVP, local models on roadmap                                                  | The "swap the model without touching policy" property is worth importing now even though Zombie has one provider today.                              |
| Human-in-the-loop             | Interactive Rich TUI: allow once / deny / allow always                                           | Mandatory approval gate per [`VISION.md`](VISION.md)                                       | Missy's tri-state UX is the right floor. "Allow always" must be explicit, scoped, and auditable, never the default.                                  |
| Audit                         | Signed JSONL audit log (Ed25519, `~/.missy/audit.jsonl`)                                         | "An auditable trail of every command the AI proposes or runs" ([`VISION.md`](VISION.md))   | Adopt the format almost verbatim. Signing is what turns logging into evidence.                                                                       |
| Policy enforcement            | `PolicyHTTPClient` as the *single* enforcement point for every outbound HTTP call                | Approval pipeline in front of privileged actions                                           | The "single chokepoint" architectural rule is the most important thing to copy from Missy.                                                           |
| Distribution                  | Curl-bash installer that clones to a user-space directory                                        | Curl-bash installer that creates a system account, configures `sudo`, and joins Tailscale  | Same install ergonomics, very different blast radius. Zombie owes the operator a louder install transcript.                                          |
| Scope                         | "Production-grade agentic platform"                                                              | "Computer that can administer itself" — diagnose, explain, configure, repair, operate      | Zombie is a *role* (sysadmin) on a *machine*. Missy is a *platform*. Reading Missy's feature list as a menu, not a spec, is essential.               |

## Capabilities to borrow now (load-bearing for the MVP)

These are the Missy primitives that map directly onto promises Ubuntu
Zombie has already made in [`VISION.md`](VISION.md). Without them the
promises are aspirational; with them they are testable.

### 1. Default-deny on network, filesystem, and shell

Missy ships with `network.default_deny: true`, no allowed filesystem
paths, and `shell.enabled: false`. Anything the agent wants to do
beyond reading its own config requires the operator to write a policy
line.

Ubuntu Zombie already has the equivalent of `network.default_deny` for
*inbound* traffic (Tailscale-only). The lesson is to extend the same
posture in three other directions:

- **Outbound network from the agent.** Even though the operator's
  desktop has unrestricted internet, the *agent identity* (`zombie`)
  should not. Egress for the agent should be an allow-list (provider
  endpoint, package mirrors, Tailscale coordination), not "whatever
  the network allows".
- **Filesystem write scopes.** The agent will eventually want to edit
  files outside its own home. Those write paths should be enumerated
  in config, not implicit in "has sudo".
- **Command classes.** Even with passwordless `sudo`, the executor
  should refuse command classes (mass deletion, partition operations,
  user/group changes, kernel parameter changes) unless they are
  explicitly enabled and approved per-invocation.

The point is not to reproduce Missy's YAML schema; the point is the
posture. "Closed unless opened" is the only sane default for a
component with `NOPASSWD: ALL`.

### 2. A single enforcement chokepoint

The most architecturally important sentence in Missy's README is:

> Every outbound request — from providers, tools, plugins, MCP
> servers, Discord — passes through `PolicyHTTPClient`. **No
> exceptions.**

That "no exceptions" is the whole game. If the agent has *one* place
where every privileged action is rendered, classified, gated, logged,
and either executed or refused, then the security review of the agent
collapses to the security review of that one component. If it has
*two*, the security review is the union plus the integration plus
whatever falls between them.

Ubuntu Zombie should adopt the same rule, with the chokepoint sitting
in front of `sudo`-bearing execution rather than HTTP: **every
privileged action proposed by the LLM passes through one executor that
classifies, gates, logs, and runs it. No exceptions.** Direct shell
escapes, "just this once" bypasses, and parallel code paths are how
this property dies; resisting them is most of the work.

### 3. Signed, append-only JSONL audit

Missy writes structured JSONL to `~/.missy/audit.jsonl`, signed by an
Ed25519 keypair generated at first run and stored at
`~/.missy/identity.pem`, with a JWK export available so an external
verifier can validate events without trusting the host.

Ubuntu Zombie should match this almost verbatim:

- One event per line, JSON object, schema-versioned.
- Fields cover *who asked*, *what was proposed*, *what class it was
  in*, *who approved (or that auto-approve fired and which scope)*,
  *what command actually ran*, *its exit status*, and a content hash
  of stdout/stderr.
- Each event is signed by a key owned by the `zombie` account.
- The public key (JWK) is exportable, so the operator — or a third
  party they hand the log to — can verify events without root on the
  machine.

Plain logging answers "what happened on this box?" only as long as
nobody tampers with the file. Signed JSONL answers "what did the
agent commit to?" even if the machine is later compromised.

### 4. Interactive tri-state approval UX

Missy's Rich TUI presents policy-denied operations as **allow once /
deny / allow always**. That three-button vocabulary is the right floor
for any local agent that touches the OS:

- *Deny* is the safe default and must require zero typing.
- *Allow once* is the common path and must scope precisely to the
  action being shown.
- *Allow always* is the dangerous one and must be *narrowly scoped*
  (this exact verb, this exact path / package / unit, possibly with a
  time bound), *audited as its own event*, and *revocable from a
  single command* (`zombie revoke` or equivalent).

Ubuntu Zombie's chat surface should render the same three choices, in
the same vocabulary, with the same defaults. The diff or command
preview that accompanies the prompt is part of the UX, not a "nice to
have"; an approval the operator cannot meaningfully read is not an
approval.

### 5. Multi-provider abstraction even with one provider

Missy's `ProviderRegistry` carries Anthropic, OpenAI, and Ollama
behind one interface with fallback and runtime hot-swap (`missy
providers switch`). Ubuntu Zombie ships with one provider today, but
the *seam* — "the runtime talks to a Provider interface, not to a
vendor SDK directly" — is worth establishing now, because:

- It is the seam the local-model roadmap depends on.
- It is the seam that lets the operator rotate to a different vendor
  without re-auditing the rest of the agent.
- It is the seam where the egress policy lives ("this provider may
  reach this host, and only this host").

The cost of introducing the seam later, after the executor and audit
log are wired in, is much higher than introducing it now.

### 6. Secrets out of config, into a vault

Missy's rule is simple: API keys go in environment variables or the
encrypted vault, **never in the config file**. The vault uses
ChaCha20-Poly1305 and addresses values via `vault://` references in
config.

Ubuntu Zombie has the same need (provider API key, possibly Tailscale
auth key, possibly SMTP creds for alerts). The MVP does not need the
full vault implementation, but it needs the *rule*: there is exactly
one place secrets live, it is not the YAML or the install script, and
the audit log references secrets by name rather than value.

### 7. Operator-facing health and audit CLIs

Missy ships `missy doctor`, `missy audit recent`, `missy audit
security`, and `missy security scan`. The pattern is: the agent is
the thing that knows whether the agent is healthy, and the operator
should be able to ask it from a normal shell.

Ubuntu Zombie should expose the same shape — a small CLI surface,
runnable by the operator's *own* account (not the `zombie` account),
that answers "is the agent reachable?", "what did it do in the last
hour?", "what was denied?", and "what does its install look like
relative to a known-good baseline?". These are read-only, do not need
approval, and are how the operator stays in charge between
incidents.

## Capabilities to translate, not copy

These are good ideas in Missy that need to be re-expressed because
Ubuntu Zombie's threat model or form factor is different.

### Per-channel policy → single private channel with per-action policy

Missy supports CLI, Discord, Webhooks, Voice, Screencast, and a REST
API, and applies different policies per channel (Discord DM
allowlists, guild/role policies, webhook HMAC). Ubuntu Zombie has
**one** channel by design: a chat surface bound to localhost, reached
over a private Tailscale tailnet. The translation is to move the
"different policies for different sources" idea from channel-level to
action-level: read-only diagnostics need no approval, mutating-local
needs approval, network-touching needs approval, destructive needs
approval *plus* a typed confirmation. The channel stays singular; the
policy axis is the action class.

### Container sandbox → systemd unit hardening

Missy offers an optional Docker sandbox with `--network=none` and
memory/CPU limits for tool execution. Ubuntu Zombie should not adopt
Docker as an installer dependency, but the *underlying property*
("the agent's runtime is isolated from the rest of the OS even though
it can ask `sudo` to do things") is right. The Ubuntu-native
translation is systemd unit hardening: `ProtectSystem=strict`,
`ProtectHome`, `PrivateTmp`, `NoNewPrivileges`, `RestrictAddressFamilies`,
`SystemCallFilter`, `CapabilityBoundingSet`, and a tight set of
`ReadWritePaths`. The runtime stays unprivileged; only the executor
path that hands a vetted command to `sudo` crosses the line.

### Landlock LSM → keep as an option, not a requirement

Missy uses Landlock for kernel-level filesystem enforcement on top of
its userspace policy. Ubuntu LTS kernels ship Landlock, so Ubuntu
Zombie can do the same — but it should be additive. The userspace
policy is the contract; Landlock is belt-and-braces. The MVP can ship
without it and add it later without changing the contract.

### Prompt-injection sanitiser → small allow-list, not 250+ patterns

Missy claims "250+ prompt injection patterns across 10+ languages
with Unicode normalization, base64 decode, multi-layer detection". A
large pattern set is brittle and produces a maintenance burden Ubuntu
Zombie should not take on. The translation is the
defence-in-depth principle, not the pattern count: Unicode-normalise
inputs, strip control characters, refuse content that claims to be
system instructions in known formats, and — most importantly — keep
the *executor*'s contract narrow enough that a successful injection
still has to clear the typed-action and approval gates. The audit log
then catches anything that does.

### Secrets detector → policy at the boundary, not pattern matching

Missy ships 37+ credential patterns and censors responses. Ubuntu
Zombie should instead avoid putting secrets in the agent's reach in
the first place (vault, environment, scoped reads), and *log* rather
than scrub on the way out. Scrubbing is a hint, not a control;
treating it as one is how secrets leak through near-misses.

### Trust scoring → boring failure counters first

Missy maintains 0–1000 reliability scores per tool/provider/MCP
server. Ubuntu Zombie's MVP has one provider and one executor; trust
scoring is over-engineered for that. Translate it to a small counter:
consecutive failures per tool, with a circuit breaker (Missy
threshold=5, exponential backoff to 300s is a sensible default) and
an operator-visible "this is degraded" state.

## Capabilities to defer until after the MVP

These are interesting and well-built in Missy, but they are
research-grade features that would multiply Ubuntu Zombie's surface
area before its core promises are tested. They belong in
[`ROADMAP.md`](ROADMAP.md), not in `main`.

- **Code evolution with git-backed rollback.** A self-modifying agent
  inside a passwordless-`sudo` account is exactly the failure mode
  Ubuntu Zombie's audit and approval design exists to prevent. If it
  ever ships, it ships as a separate, opt-in mode behind a louder
  consent surface than anything else in the system.
- **Attention/sleep/condenser subsystems, AI Playbook, graph memory,
  vector memory.** All useful for long-running agentic workloads; all
  orthogonal to "diagnose and fix this Ubuntu box". Defer until there
  is concrete evidence that the operator's tasks span the kind of
  context windows these subsystems exist to manage.
- **Sub-agents.** Multi-agent dispatch on a single host is a great
  way to lose track of who proposed what; not worth importing until
  the single-agent audit story is airtight.
- **Voice nodes, screencast channel, vision subsystem, desktop
  automation (Playwright/X11/AT-SPI), camera discovery.** Each of
  these is a major attack surface and a major UX commitment. Ubuntu
  Zombie's MVP interface is text in a private chat; expanding the
  channel set is a post-MVP product decision, not an MVP feature.
- **Scheduler / proactive triggers / heartbeats.** A sysadmin that
  acts *on its own* without an operator prompt is a different product
  with a different trust story. The MVP is reactive; proactive is a
  v2 conversation.
- **REST "Agent-as-a-Service" API.** A loopback-bound, API-keyed REST
  endpoint is reasonable for Missy's "platform" framing. For Ubuntu
  Zombie it duplicates the chat surface, widens the attack surface,
  and tempts users to expose it. Out of scope.
- **MCP server hosting and digest pinning.** MCP is the right
  long-term plug-in shape (see [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md)
  on Goose and RHEL Lightspeed), but the MVP should ship a fixed,
  internal tool catalogue and earn the right to add a plug-in surface
  later.
- **Persona system, behaviour layer, hatching wizard.** Ubuntu Zombie
  has one persona — *systems administrator of this machine* — and
  needs no tone configuration to do its job.

## Capabilities to explicitly refuse

These are not "defer", they are "no". They are listed so future
contributors do not import them by accident.

- **A public listener of any kind.** Missy supports webhooks with
  HMAC auth, a REST API with rate limiting, a Discord gateway, and a
  voice WebSocket server. Ubuntu Zombie's interface is private by
  construction. None of these belong on the same box without
  re-opening the [`VISION.md`](VISION.md) trust model.
- **Auto-promotion of patterns to skills.** Missy's playbook
  auto-promotes patterns with 3+ successes into skill proposals. In
  a passwordless-`sudo` context, "the agent learned to do this on its
  own" is the failure mode the audit log exists to make visible.
  Skills, runbooks, and tool definitions belong on disk in
  human-readable files, added by humans, reviewed by humans.
- **Hidden or embedded system prompts.** Missy's culture is
  transparent; Ubuntu Zombie's must be more so. Prompts, action
  classes, policies, and approval thresholds live in readable files
  under `/etc/zombie` (or equivalent), not in source-baked strings.
- **A second provider channel on by default.** Multi-provider as an
  *abstraction* (see "Capabilities to borrow now") is good. Multiple
  providers actively reachable in the egress policy by default is
  bad. The operator picks one and opens egress to one.

## Operational details worth copying outright

A handful of small, concrete Missy choices are good enough that
Ubuntu Zombie should adopt them verbatim or close to it. They are
boring in isolation and load-bearing in aggregate.

- **`~/.<agent>/` as the agent home.** Missy uses `~/.missy/` for
  config, identity, vault, audit log, and MCP definitions. Ubuntu
  Zombie's `zombie` account should have the same layout under its own
  `$HOME`: `~/.zombie/config.yaml`, `~/.zombie/identity.pem`,
  `~/.zombie/audit.jsonl`, `~/.zombie/vault`. One directory, owned by
  the agent account, mode-restricted, easy to back up, easy to wipe.
- **Config versioning and auto-migration with backups.** Missy
  stamps a `config_version` and keeps up to 5 backups, with
  `config diff` and `config rollback`. Ubuntu Zombie should do the
  same from day one; configs drift, and a one-command rollback is the
  difference between "I broke it" and "I broke it and the machine
  fixed itself".
- **`doctor` / `audit recent` / `security scan` as a CLI triad.**
  These are the three questions the operator will ask: *is it
  healthy?*, *what did it do?*, *is anything obviously wrong with my
  install?*. Shipping all three from the MVP, even with trivial
  implementations, sets the expectation that the agent is
  inspectable.
- **A non-interactive setup path.** Missy's `missy setup --provider
  ... --api-key-env ... --no-prompt` is exactly the shape Ubuntu
  Zombie already uses for its installer (`ZOMBIE_NONINTERACTIVE=1`).
  Worth keeping aligned: non-interactive install is what makes the
  whole thing reproducible and CI-testable.
- **Symlink, ownership, and permission checks before reload.** Missy
  re-validates these before hot-reloading config. Ubuntu Zombie
  should do the same: a `zombie reload` that silently accepts an
  attacker-writable config is worse than no reload at all.

## Where Missy is honest about being too big

A useful exercise: read Missy's feature list as a *warning* about how
much an "AI assistant for Linux" can grow if it is allowed to. Voice
nodes, vision, sub-agents, attention systems, sleeptime memory
processing, code evolution, graph memory, FAISS — each one is
defensible in isolation, and the combination is a project Ubuntu
Zombie can never ship and never wants to. The discipline Ubuntu
Zombie has to maintain is to look at Missy's surface area and say "we
borrowed these five primitives, we translated those three, the rest
is post-MVP" — and then *not drift*.

The most important thing Missy teaches Ubuntu Zombie, in other words,
is what *both* projects could become if scope were unbounded, and how
much of that scope Ubuntu Zombie should refuse on purpose.

## Top ten Missy lessons, ranked

If only ten lessons survive from this whole document, in order:

1. **One enforcement chokepoint, no exceptions.** Every privileged
   action goes through the same executor — classified, gated, logged,
   executed.
2. **Default-deny on network egress, filesystem writes, and command
   classes**, not just on inbound network.
3. **Signed JSONL audit log with an exportable public key**, so the
   log is evidence rather than a story.
4. **Tri-state approval UX (`allow once / deny / allow always`)**
   with narrowly scoped, audited, revocable "always" entries.
5. **Secrets in a vault or environment, never in config**, with the
   audit log naming secrets rather than carrying them.
6. **A Provider abstraction from day one**, even with one provider,
   so the local-model roadmap and the egress policy have a stable
   seam.
7. **`~/.<agent>/` as the single, mode-restricted agent home** for
   config, identity, vault, and audit.
8. **`doctor` / `audit recent` / `security scan` CLI triad**, runnable
   by the operator's own account, read-only, no approval.
9. **Config versioning with backups and one-command rollback** from
   the MVP onward.
10. **Read Missy's feature list as a menu, not a spec.** The biggest
    risk is importing the surface area along with the primitives.

Everything else — voice, vision, sub-agents, code evolution,
attention/sleep/condensers, MCP plug-ins, REST API, scheduler — is
post-MVP at best and out of scope at worst. The promises in
[`VISION.md`](VISION.md) come first; Missy's catalogue of clever
ideas comes after, and only the ones that make those promises more
testable get to come at all.
