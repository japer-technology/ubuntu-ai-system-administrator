# Deep Lessons from SysKnife (`lacs-foundation/sysknife`)

This document is a deep companion to [`ALTERNATIVES.md`](ALTERNATIVES.md)
and [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md), in the same
shape as [`ALTERNATIVE-MISSY.md`](ALTERNATIVE-MISSY.md) and
[`ALTERNATIVE-LINUX-AGENT.md`](ALTERNATIVE-LINUX-AGENT.md). Of every
project in the catalogue, **SysKnife** is the closest *architectural*
analog to Ubuntu Zombie: not because it shares the same form factor —
it does not — but because it has already made, in code, the
single biggest design choice Ubuntu Zombie needs to make: **the LLM
never holds a shell; it emits typed, risk-classified actions that a
small privileged executor renders, approves, runs, and chains into a
tamper-evident audit log.**

Missy teaches Ubuntu Zombie what to *defend against*. SysKnife teaches
Ubuntu Zombie what to *build*. Both projects ship more surface area
than the MVP needs, and the discipline of this document — like its
siblings — is to separate the load-bearing primitives from the
research-grade additions and to translate them into terms that make
sense for a single Ubuntu Desktop LTS box with a real local `zombie`
Unix account on the other end of a private Tailscale tailnet.

This file reads SysKnife through the Ubuntu Zombie filter defined in
[`VISION.md`](VISION.md) — *Ubuntu LTS + a real local Unix account +
a private Tailscale interface + an LLM under human approval* — and
decides, capability by capability, what to **borrow**, what to
**translate**, what to **defer**, and what to **explicitly refuse**.

## What SysKnife actually is, in one paragraph

SysKnife is a three-process Linux control plane written in Rust (with
a TypeScript setup wizard and React/Tauri GUI shell). The `brain` is
an unprivileged LLM planner that talks to a provider (OpenAI,
Anthropic, Gemini, Ollama, Groq, DeepSeek, Mistral, xAI) and emits a
typed plan; the `shell` (CLI, GUI, or MCP server) is an approval gate
that presents the plan with risk badges, previews, side-effect notes,
and rollback metadata; the `daemon` is the only privileged component
and is the only thing that ever touches the system. The daemon owns
~60 typed actions (package management, systemd units, firewall, users,
containers, flatpak, toolbox, SSH, kernel args, …), role-based
authorization (`Observer` → `Dev` → `Admin` → `Boot`), preview
generation (risk level, side effects, reboot flag, rollback
availability, content hash), live stdout streaming, automatic
rollback for supported high-risk failures, and an HMAC-SHA256
hash-chained audit log in SQLite or Postgres that an operator can
verify with `sysknife audit verify`. Per-distro prompt dispatch means
a Fedora prompt physically cannot contain Debian action names and
vice versa. The MCP integration exposes exactly two tools —
`sysknife_plan` and `sysknife_execute` — and refuses high-risk
actions outright at the MCP boundary, forcing them through the
CLI/GUI confirmation flow. The whole thing is the reference
implementation of the **LACS (Linux Agent Control Standard)** spec,
which is published separately under CC0.

Ubuntu Zombie is much smaller than that and intentionally so. The
interesting question is which SysKnife primitives are load-bearing
for the safety posture Ubuntu Zombie has already promised in
[`VISION.md`](VISION.md), and which are platform features that would
blow up the MVP if imported.

## The axis-by-axis comparison

| Axis                          | SysKnife                                                                                                       | Ubuntu Zombie                                                                              | Implication                                                                                                                            |
| ----------------------------- | -------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- |
| Host target                   | Fedora 41+/Silverblue first, Ubuntu 22.04/24.04/26.04 LTS validated                                            | Supported Ubuntu Desktop **LTS** only                                                       | SysKnife pays a real multi-distro tax (per-distro prompt dispatch, separate action catalogues). Zombie should keep cashing the LTS-only simplification. |
| Install shape                 | `npx sysknife-setup` wizard installs the daemon as a systemd unit and writes integration config for the IDE    | Transparent bash installer that creates a real Unix account                                | SysKnife is a *daemon* the operator's IDE talks to; Zombie is a *system change* with its own identity. Zombie's audit/approval has to survive that escalation.   |
| Privilege model               | Polkit-mediated; daemon is the only privileged process; brain and shell are unprivileged                       | Dedicated `zombie` account with passwordless `sudo`                                        | The "small, boring, privileged executor is the only thing that touches the system" rule is the most important thing to copy.                                     |
| Caller identity               | Explicit `CallerRole` enum: `Observer` / `Dev` / `Admin` / `Boot`                                              | One operator, one machine, one trust boundary                                              | The *idea* of typed caller roles is right; Zombie does not need four of them in the MVP, but it should at least separate read-only ("ask") from mutating ("act"). |
| Action surface                | 60+ typed actions with formal risk levels (`Low` / `Medium` / `High`)                                          | Privileged actions classified, gated, surfaced before they run                             | Zombie should ship a small typed action catalogue from day one and grow it; *raw shell strings must never cross the trust boundary*.                              |
| Interface                     | CLI, Tauri GUI, MCP server inside Claude Code / Cursor / Codex CLI                                             | Private chat surface, Tailscale-only inbound, no public listener                           | The CLI is fine, the GUI is post-MVP, and the MCP server is interesting but optional. Zombie's chat surface replaces the IDE-host model.                          |
| Inference                     | Multi-provider; Ollama recommended for privacy/homelab                                                         | Cloud LLM in MVP, local models on roadmap                                                  | A provider abstraction is the right seam; Ollama-first as a recommendation is consistent with Zombie's eventual local-model story.                               |
| Human-in-the-loop             | Per-step approval; `--yes` allowed only up to a configurable risk ceiling; High requires typing the action name | Mandatory approval gate per [`VISION.md`](VISION.md)                                       | The *risk-ceiling* idea and the *type-to-confirm* idea are both worth importing verbatim. Auto-approve must never silently cross a class.                         |
| Audit                         | HMAC-SHA256 hash-chained SQLite or Postgres log; `sysknife audit verify`; RFC 5424 syslog forwarding           | "An auditable trail of every command the AI proposes or runs" ([`VISION.md`](VISION.md))   | A hash chain (or Missy's Ed25519 JSONL) is what turns a log into evidence. Pick one cryptographic property and commit to it.                                      |
| Rollback                      | Automatic rollback on failure for supported high-risk actions                                                  | Reversibility is a stated value but not yet a mechanism                                    | Per-action rollback metadata is one of SysKnife's most distinctive primitives and is the single biggest "operator confidence" win.                                |
| Reboot signalling             | `JobState::NeedsReboot` is a first-class terminal state                                                        | Not yet modelled                                                                           | Zombie should adopt this verbatim. "It worked but the box needs a reboot" is information the audit log and the chat surface both need to surface.                 |
| Distribution                  | npm-distributed setup wizard + Rust binaries; daemon under `systemd`                                           | Curl-bash installer that creates a system account, configures `sudo`, joins Tailscale       | Same install ergonomics for the operator (one command), very different blast radius. Zombie owes a louder install transcript than SysKnife does.                  |
| Spec posture                  | Reference implementation of an external CC0 spec (LACS)                                                        | One project, one repository, one installer                                                 | Zombie does not need to be a spec, but it should write its action types and risk classes down in a *human-readable schema file* that a third party could read.    |
| Scope                         | "Sysadmin co-pilot. Plan. Approve. Audit."                                                                     | "Computer that can administer itself" — diagnose, explain, configure, repair, operate      | Same elevator pitch, different framing of *who* the agent is. SysKnife is a tool *you* drive; Zombie is a *role on the machine* you ask.                          |

## Capabilities to borrow now (load-bearing for the MVP)

These are the SysKnife primitives that map directly onto promises
Ubuntu Zombie has already made in [`VISION.md`](VISION.md). Without
them the promises are aspirational; with them they are testable.

### 1. Typed actions, never raw shell strings, across the trust boundary

The most architecturally important sentence in SysKnife's README is:

> SysKnife never runs a shell command. Every action is a typed
> operation with a formal risk level. The AI cannot touch your system
> directly.

That sentence is the whole game. Once the LLM is allowed to emit a
free-form shell string, every other safety primitive in the system —
approval, audit, classification, rollback — is reduced to *pattern
matching on strings the model wrote*. Once the LLM is forced to emit
a typed action (`AptInstall { package: "nginx" }`,
`SystemdRestart { unit: "ssh.service" }`,
`WriteFile { path: "/etc/Y", diff: "..." }`), the safety primitives
become *checks on a structured value* and the security review of the
agent collapses to the security review of one small executor.

Ubuntu Zombie should adopt the same rule: **the LLM proposes a typed
action; the executor renders, classifies, gates, logs, and runs it; no
raw shell escapes are allowed, ever.** This is the single biggest
safety win in the space and it is non-negotiable, even before the
MVP ships.

### 2. A formal risk level on every action

SysKnife tags every action with one of `Low` · `Medium` · `High`. The
approval UX, the auto-approve ceiling, the typed-confirmation
requirement, and the rollback policy all *follow from* that tag. Risk
is not metadata for humans; it is the input to policy.

Ubuntu Zombie's [`VISION.md`](VISION.md) already talks about
*"destructive, networked, or system-altering commands"* being
classified before they run. SysKnife is the worked example of what
that classification has to *do* once it exists:

- `Low` (read-only diagnostics: `journalctl`, `systemctl status`,
  `df`, `apt list --installed`) can run without an approval prompt
  and should be cheap and fast.
- `Medium` (mutating-local: install a package, restart a unit, edit
  a config file) requires an explicit approval — a checkbox, a
  click, or a `y` keystroke.
- `High` (destructive, irreversible, or wide-blast-radius: user/group
  changes, partition operations, kernel parameter changes,
  network-topology changes) requires the operator to *type the action
  name* to confirm.

The vocabulary is small enough to fit in a single enum and rich
enough to drive every other policy decision in the system. Ship it in
the MVP.

### 3. A three-role process split: planner / approval gate / executor

SysKnife runs three processes — `sysknife-brain`, `sysknife-shell`,
`sysknife-daemon` — and only the daemon is privileged. The brain
never talks to the OS; the shell never talks to the OS; the daemon
never talks to the LLM. The trust boundary is *mechanical*, enforced
by the process model and the IPC contract, not by convention.

Ubuntu Zombie's MVP can collapse these three roles into a single
binary if necessary — Cline's SDK does the same — but the *seam*
between them has to be real:

- The **planner** (whichever process talks to the cloud LLM) holds
  the prompt, the provider client, and the conversation history, and
  is the only thing with network egress to the provider endpoint.
- The **approval gate** (the chat surface bound to localhost,
  reached over Tailscale) renders the typed action and captures the
  human decision; it does not execute and it does not talk to the
  LLM.
- The **executor** (the small process that holds passwordless
  `sudo`) accepts only approved typed actions, classifies, logs,
  runs, and reports.

Even if these three live in one process today, the *interfaces*
between them should be the interfaces between three processes
tomorrow. That is the seam the local-model roadmap and the future
"swap out the chat surface" story both depend on.

### 4. Content-hashed approvals (stale-approval detection)

SysKnife's daemon generates a *content hash* of every previewed
action and verifies that hash is fresh before executing. The
operator does not approve "install nginx"; the operator approves
*this specific typed action with these specific parameters with this
specific hash*, and the daemon will refuse to run anything else under
that approval.

This is the primitive that closes the time-of-check / time-of-use
gap. Without it, "the operator already approved an install five
minutes ago" can be replayed against a *different* install. With it,
every approval is bound to exactly one execution.

Ubuntu Zombie should adopt this verbatim. The approval log entry,
the chat-surface prompt, and the executor's pre-run check all
reference the same content hash; the executor refuses anything else.

### 5. Per-action rollback metadata and automatic rollback on failure

SysKnife's daemon ships *rollback metadata* alongside the preview for
supported actions and **automatically rolls back high-risk steps that
fail**. Rollback is not an afterthought reachable from the audit log;
it is part of the action contract.

Ubuntu Zombie has reversibility as a stated value but no mechanism
yet. SysKnife's mechanism is the right shape:

- Actions that have a clean inverse (install / remove a package,
  enable / disable a unit, add / remove a UFW rule, write / restore
  a file from a snapshot) declare it in their type.
- The preview surfaces "rollback available" as a first-class flag the
  operator can see *before approving*.
- On failure of a `High` step that has rollback metadata, the
  executor runs the inverse automatically and records both events in
  the audit chain.

Not every action will be reversible. The discipline is to be honest
about which ones are not, surface that fact in the preview, and let
the operator decide whether to accept the irreversibility.

### 6. A first-class `NeedsReboot` terminal state

SysKnife's `JobState` enum has `NeedsReboot` as one of its terminal
values, alongside `Succeeded`, `Failed`, `Canceled`, and
`RolledBack`. That is the right modelling: "the action worked but
the kernel, the initramfs, or a service needs to come back for the
change to take effect" is *not* `Succeeded` and is *not* `Failed`,
and pretending it is either is how operators end up surprised.

Ubuntu Zombie should adopt this verbatim. The chat surface should be
able to say "this worked, but your machine needs a reboot to pick it
up", the audit log should record that fact, and a follow-up
`zombie status` should be able to remind the operator that there is
an outstanding reboot.

### 7. A hash-chained audit log with `audit verify`

SysKnife writes a hash-chained HMAC-SHA256 audit trail (SQLite by
default, Postgres optional for fleets) and ships
`sysknife audit verify` to validate the chain end-to-end.

This is a slightly different cryptographic choice from Missy's
Ed25519-signed JSONL — chain integrity vs. per-event signatures —
and Ubuntu Zombie has to pick one. The criteria are the same either
way:

- Tamper-evidence: any modification of a past event must be
  detectable from outside the box.
- Exportability: the operator (or a third party they hand the log
  to) must be able to verify the log *without* root on the machine.
- A single, well-documented verifier command (`zombie audit verify`)
  is what turns the cryptographic property into an operator-facing
  feature.

A reasonable Ubuntu Zombie posture is to take the Missy primitive
(Ed25519-signed JSONL, per-event signatures, exportable JWK) as the
*format* and the SysKnife primitive (one-command verifier, optional
external sink) as the *operator UX*. Either way: signed and
verifiable from day one.

### 8. Type-to-confirm for irreversible actions

SysKnife's GUI requires the operator to *type the action name* to
approve a `High` step (not just click, not just press `y`). It is a
deliberate friction primitive: irreversible decisions should be
harder to make than reversible ones.

Ubuntu Zombie's chat surface should do the same. For a Low
diagnostic, no prompt. For a Medium mutation, a single keystroke. For
a High destructive action, the operator types the action name (or a
canonical confirmation phrase) into chat. This is cheap to implement,
expensive to bypass by accident, and reads as obvious safety culture
to anyone auditing the surface.

### 9. Risk-bounded auto-approve

SysKnife's `--yes` flag does not mean "auto-approve everything"; it
means "auto-approve up to a configured risk ceiling". The ceiling is
the policy axis, not the existence of the flag.

Ubuntu Zombie should adopt the same model. An "auto-approve Low" mode
is a reasonable default for the operator who wants the agent to be
able to read logs and check service status without prompting. An
"auto-approve Medium" mode is a deliberate choice the operator opts
into with eyes open. An "auto-approve High" mode does not exist; the
flag is *bounded by the enum*, not by the operator's patience.

### 10. Per-distro prompt dispatch as structural isolation

SysKnife builds its system prompt by dispatching on
`distro_hint.family` to one of three render functions; the Fedora
prompt physically cannot contain Debian action names and vice versa.
The isolation is *structural*, not "we ask the model nicely".

Ubuntu Zombie's situation is simpler — there is one supported
substrate, Ubuntu LTS — and the lesson is to embrace that. The
prompt should *name the substrate* (kernel cadence, `apt`,
`systemd`, `netplan`, `ufw`), enumerate only the action types that
apply to it, and refuse outright if the underlying system does not
match. The prompt is part of the safety contract, not part of the
LLM's general knowledge.

### 11. An open, written schema for actions and risk

SysKnife is the reference implementation of the **LACS** spec
([`lacs-foundation/specification`](https://github.com/lacs-foundation/specification)),
published separately under CC0. Other implementations are explicitly
encouraged.

Ubuntu Zombie does not need to become a spec organisation. It does
need to write its action catalogue, its risk classes, its caller
roles, its `JobState` enum, and its audit-event schema down *in a
human-readable file in the repository* — JSON Schema, TOML, or
Markdown tables, anything that a third party can read without
running the code. This is the legibility property that
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) flags as a
trust signal from Goose and Butterfish, and SysKnife has the cleanest
worked example of it in the catalogue.

## Capabilities to translate, not copy

These are good ideas in SysKnife that need to be re-expressed because
Ubuntu Zombie's threat model or form factor is different.

### Polkit-mediated daemon → systemd-unit-hardened `zombie` account

SysKnife's daemon runs as a polkit-mediated privileged process the
unprivileged brain and shell talk to over a Unix socket. Ubuntu
Zombie's privilege model is different: there is a real local Unix
account with passwordless `sudo`, not a polkit-mediated daemon. The
translation is:

- The `zombie` account is the privilege boundary; it is the only
  identity that can run `sudo`.
- The executor process inside `zombie` is the only thing that calls
  `sudo`, and it does so only for typed, approved, hashed actions.
- The runtime is hardened with systemd unit options
  (`ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`,
  `NoNewPrivileges`, `RestrictAddressFamilies`, `SystemCallFilter`,
  `CapabilityBoundingSet`, a tight `ReadWritePaths`).

Polkit is the right primitive for SysKnife's "daemon plus desktop
app" architecture. Systemd unit hardening plus a dedicated Unix
account is the right Ubuntu-native translation for Ubuntu Zombie's
"the agent is a user on the box" architecture.

### MCP server inside an IDE → private chat surface over Tailscale

SysKnife ships an MCP server that plugs into Claude Code, Cursor, and
Codex CLI; the agent inside the IDE calls `sysknife_plan` and
`sysknife_execute` as MCP tools, and high-risk actions are refused
outright at the MCP boundary (they require the CLI/GUI confirmation
flow).

Ubuntu Zombie's interface is the opposite shape: the LLM is not
running inside an IDE on the operator's laptop; the LLM is being
called by an executor *on the machine being administered*, reached
through a private chat surface over Tailscale. The two lessons that
translate are:

- **Expose a tiny, fixed tool surface to the model.** SysKnife's MCP
  server exposes two tools; everything else lives behind them. Ubuntu
  Zombie's prompt/tool surface should be similarly narrow: propose,
  preview, approve, execute, audit. Adding tools is a deliberate
  product decision, not an implementation detail.
- **Some classes of action are refused at the boundary, not gated.**
  SysKnife refuses high-risk actions at the MCP layer entirely.
  Ubuntu Zombie's executor should have an equivalent: certain
  command classes (mass deletion, partition operations, full-disk
  encryption changes) are *not* approvable through the normal chat
  surface and require an out-of-band confirmation (a TTY on the
  machine, a signed file in `/etc/zombie/consent.d/`, or a future
  Telegram-style second channel).

### Tauri GUI → text chat surface

SysKnife's `sysknife-shell` is a Tauri (Rust + React) GUI with an
intent pane, plan review, approval gate, and live job timeline. It is
a beautiful product, and it is the wrong product for Ubuntu Zombie:
Ubuntu Zombie's interface is a *private chat over Tailscale*, not a
desktop GUI on the operator's screen, because the operator may not be
in front of the machine.

The lesson is the *information density* the SysKnife GUI lands on,
not the rendering technology:

- Plan as a numbered list of typed actions with risk badges.
- Per-step preview: command, side effects, reboot flag, rollback
  availability, content hash.
- Live streaming output as the job runs.
- Final state (`Succeeded` / `Failed` / `Canceled` / `RolledBack` /
  `NeedsReboot`) on its own line.

All of that fits in a chat surface. The GUI is a way to present it;
the *vocabulary* is what matters.

### `CallerRole` enum → "ask" vs "act" mode in the MVP

SysKnife's `CallerRole` enum (`Observer` / `Dev` / `Admin` / `Boot`)
is the right shape for a fleet tool with multiple human operators
and a boot-time path. Ubuntu Zombie's MVP has one operator. The
translation is to keep the *idea* of typed caller roles but to ship
only two of them at first:

- **Ask** mode: read-only diagnostics, no approval, fast and cheap.
- **Act** mode: mutating actions, approval mandatory, audited.

Adding a `Boot` role (for first-install hardening) or an `Operator`
role (for a delegated second human) is a post-MVP decision, but the
enum should exist from day one so adding entries is a typed change,
not a refactor.

### Postgres audit backend → optional external sink, SQLite default

SysKnife supports Postgres (RDS / Cloud SQL / Neon / Supabase) as a
production backend for the audit chain. Ubuntu Zombie's MVP is a
single Ubuntu LTS box, not a fleet, and the default audit store
should be local — a signed JSONL file or a local SQLite database
under `~/.zombie/audit/`.

The translation is to leave the seam open. SysKnife also forwards
RFC 5424 syslog to Splunk / Sentinel / QRadar; Ubuntu Zombie should
similarly support *optional* external forwarding (syslog, journald
upload, or a webhook) without making it the default. The local log
is the source of truth; the external sink is a copy.

### Live `JobProgress` streaming → chat-surface streaming with the same frames

SysKnife streams live stdout as `JobProgress` frames over the Unix
socket. Ubuntu Zombie's chat surface should stream output in the same
shape — line-by-line, attributed to the running action, with a final
terminal state — because "the agent has been running this for two
minutes, here is what it has printed so far" is the difference
between a usable UX and a black box.

The transport is different (chat tokens vs. socket frames) but the
*frame shape* (action id, stream, line, timestamp, terminal state)
is the same and should be the same in the audit log.

## Capabilities to defer until after the MVP

These are interesting and well-built in SysKnife, but they are
platform features that would multiply Ubuntu Zombie's surface area
before its core promises are tested. They belong in
[`ROADMAP.md`](ROADMAP.md), not in `main`.

- **Tauri GUI.** Wayland desktop GUI is on SysKnife's own roadmap and
  is genuinely useful. For Ubuntu Zombie it duplicates the chat
  surface and pulls in a large dependency stack (Rust toolchain,
  WebKit, GTK) the bash installer should not need.
- **MCP server.** MCP is the right long-term plug-in shape (see
  [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) on Goose and
  RHEL Lightspeed), but the MVP should ship a fixed, internal tool
  catalogue and earn the right to add a plug-in surface later. If and
  when an MCP server is added, it should *only* expose `plan` and
  `execute` and it should refuse high-risk actions outright, exactly
  as SysKnife does.
- **Multi-provider with hot-swap.** SysKnife supports 8+ providers.
  Ubuntu Zombie's MVP should pick one cloud provider, hide it behind
  a provider abstraction (per the Missy lessons), and ship a clean
  upgrade path to Ollama as part of the local-model roadmap.
  Shipping 8 providers in the MVP is 7 sets of egress policy and 7
  failure modes nobody asked for.
- **Postgres audit backend.** SQLite or signed JSONL on disk is more
  than enough for one box. Pulling a Postgres URL into a bash
  installer is the kind of operational complexity that breaks the
  "I ran one command and it works" property.
- **RFC 5424 syslog forwarding to enterprise SIEMs.** A small webhook
  or `journald` sink is a fine v2; full SIEM integration is a
  different product (and pulls in compliance conversations the MVP
  does not need to have).
- **Fleet plan/execute (one plan, N targets).** Ubuntu Zombie is
  *one machine, one administrator* by definition
  ([`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) §"Ubuntu LTS
  + root user + Pi + LLM"). Multi-target dispatch is on SysKnife's
  roadmap; for Ubuntu Zombie it is explicitly out of scope.
- **Telegram approval interface.** On SysKnife's roadmap, attractive
  for "approve from the bus stop", and probably a v2 feature for
  Ubuntu Zombie too — but the MVP's approval surface is the chat
  over Tailscale, and adding a second channel before the first one
  is solid is a distraction.
- **Per-distro prompt *dispatch*.** The pattern is good; the *plural*
  is the deferral. Ubuntu Zombie writes one render function — for
  Ubuntu LTS — and defends the structural-isolation property
  ("prompts only ever name actions that exist on this distro") even
  though there is only one branch today.

## Capabilities to explicitly refuse

These are not "defer", they are "no". They are listed so future
contributors do not import them by accident.

- **Multi-distro support in the MVP.** SysKnife's per-distro prompt
  dispatch, separate action catalogues, and three-LTS test matrix are
  the right answer for a project whose goal is to be a sysadmin
  co-pilot anywhere. Ubuntu Zombie's value is in being *the* opinion
  for Ubuntu LTS; chasing distro-portability before the single-distro
  story is solid is how the project's identity gets diluted.
- **A `Dev` or `Boot` caller role on a single-operator desktop.**
  SysKnife's four-role enum makes sense for its fleet ambitions.
  Ubuntu Zombie has one operator; adding roles that do not map to a
  real human or a real boot path is invented complexity.
- **Embedding inside an IDE as the primary interface.** SysKnife's
  MCP-into-Claude-Code shape is a great fit for "the developer is at
  the keyboard". Ubuntu Zombie's premise is the opposite: the
  operator is *not* expected to be a developer, the machine is *not*
  expected to be a workstation, and the interface is a private chat
  over Tailscale precisely so the operator can be anywhere.
- **An npm-distributed installer.** SysKnife's `npx sysknife-setup`
  is the right call for an IDE-integrated tool whose users already
  have Node.js. Ubuntu Zombie's installer must not depend on Node.js;
  the substrate is Ubuntu LTS and the installer is bash plus the
  packages already in `main`.
- **Raw shell anywhere in the trust path.** This is not a "we will
  add it later" — it is a permanent refusal. If a future action
  cannot be expressed as a typed operation, the answer is to add a
  typed operation for it, not to fall back to a string.
- **Auto-approve at `High`.** The risk ceiling exists *because*
  high-risk actions are not auto-approvable. Any future flag that
  would allow it is a regression of the safety contract, regardless
  of how it is named.

## Operational details worth copying outright

A handful of small, concrete SysKnife choices are good enough that
Ubuntu Zombie should adopt them verbatim or close to it. They are
boring in isolation and load-bearing in aggregate.

- **A documented file layout for the daemon.** SysKnife uses
  `/run/sysknife/daemon.sock` for the socket and
  `/var/lib/sysknife/daemon.sqlite` for state, with
  `~/.config/sysknife/config.toml` for user config and
  `~/.config/sysknife/prefs.md` for user preferences injected into
  the prompt. Ubuntu Zombie's `zombie` account should have a similarly
  legible layout: socket under `/run/zombie/`, state under
  `/var/lib/zombie/`, config and prefs under `~/.zombie/` (mode
  `0600` where they contain secrets).
- **`chmod 0600` on every config file that may carry a secret.**
  SysKnife's setup wizard does this for every integration file it
  writes. Ubuntu Zombie's installer should do the same for
  `config.yaml`, the vault, the audit-signing key, and any provider
  key file — and the installer should *say so* in its transcript.
- **A user preferences file injected into the system prompt.**
  SysKnife reads `~/.config/sysknife/prefs.md` on every plan call so
  the prompt is always current. Ubuntu Zombie's equivalent
  (`~/.zombie/prefs.md` or `/etc/zombie/prefs.d/`) is a cheap,
  transparent way to let the operator say "I run UFW, not iptables"
  or "I use `netplan`, not NetworkManager" without re-prompting per
  conversation.
- **A `--dry-run --json` mode that emits plans without executing.**
  SysKnife uses this mode for every E2E story script. Ubuntu Zombie
  should expose the same: `zombie plan "..." --dry-run --json` emits
  the typed plan and the previews on stdout without contacting the
  executor. This is what makes the agent *testable in CI*.
- **A documented IPC contract with a small max-message size and a
  semaphore-limited connection count.** SysKnife's daemon uses a
  4 MiB cap and 16 concurrent connections, with excess connections
  dropped rather than queued. Ubuntu Zombie's executor IPC should
  ship similar limits from day one; "the chat surface is bound to
  localhost" is not a substitute for a hard cap on what the executor
  will accept.
- **A human-readable wire protocol.** SysKnife uses length-prefixed
  JSON over a Unix socket explicitly so an operator can debug live
  traffic with `socat - UNIX-CONNECT:/run/sysknife/daemon.sock`.
  Ubuntu Zombie's executor IPC should be similarly inspectable.
  Opaque binary protocols are the wrong choice for a system whose
  value proposition is *transparency*.
- **An ADR series in `docs/adr/`.** SysKnife publishes its
  architecturally significant decisions (system boundaries, brain
  provider layer, IPC wire protocol, per-distro prompt dispatch) as
  numbered ADRs. Ubuntu Zombie should adopt the same practice: the
  decisions to ship typed actions, signed audit logs, a chat surface
  over Tailscale, and a real Unix account are all ADR-worthy and the
  document trail is part of how a third party comes up to speed.

## Where SysKnife is honest about being a platform

A useful exercise: read SysKnife's status table as a *map* of how
much a single-host sysadmin agent has to grow to feel
production-ready. Sixty typed actions; live IPC and streaming and
rollback; a Tauri shell; an MCP server; a tamper-evident audit chain;
RFC 5424 syslog forwarding; a Postgres backend; per-distro prompt
dispatch; an open spec; 860+ tests across two languages. None of
those are wrong. All of them, together, are a project Ubuntu Zombie
cannot ship and does not want to.

The discipline Ubuntu Zombie has to maintain is to look at SysKnife's
status table and say "we borrowed these eleven primitives, we
translated those six, the rest is post-MVP or out of scope" — and
then *not drift*. The most useful single sentence from SysKnife's
README, for Ubuntu Zombie's purposes, is:

> The brain *proposes*; only the daemon is privileged. The daemon
> *enforces* policy, executes typed actions, writes the chain, and
> triggers rollback. The trust boundary is mechanical — no shell
> strings cross the wire.

That paragraph is the architecture Ubuntu Zombie wants, expressed in
fewer words than the rest of this document. Everything above is the
expanded form of "do that, in terms that make sense for an Ubuntu
LTS box with a `zombie` account on the other end of a Tailscale
tailnet".

## Top ten SysKnife lessons, ranked

If only ten lessons survive from this whole document, in order:

1. **Typed actions, never raw shell strings, across the trust
   boundary.** The LLM emits a structured value; the executor renders,
   classifies, gates, logs, and runs it. No exceptions.
2. **A formal risk level (`Low` / `Medium` / `High`) on every
   action**, and let policy, approval UX, auto-approve ceiling, and
   rollback policy all *follow from* the tag.
3. **A three-role process split (planner / approval gate /
   executor)** with the privilege boundary on the executor only,
   even if the MVP collapses the three roles into one binary.
4. **Content-hashed approvals.** The operator approves *this exact
   action with these exact parameters with this exact hash*; the
   executor refuses anything else.
5. **Per-action rollback metadata and automatic rollback for
   high-risk failures**, with `rollback_available` surfaced in the
   preview *before* approval.
6. **A first-class `NeedsReboot` terminal state** alongside
   `Succeeded` / `Failed` / `Canceled` / `RolledBack`, surfaced in
   chat and in the audit log.
7. **A hash-chained, externally verifiable audit log** with a single
   one-command verifier (`zombie audit verify`).
8. **Type-to-confirm for irreversible actions**; cheap to implement,
   expensive to bypass by accident, obvious safety culture.
9. **Risk-bounded auto-approve.** `--yes` means "auto-approve up to
   a configured risk ceiling"; the ceiling is the policy axis.
10. **An open, written schema for actions, risk classes, caller
    roles, and audit events** in the repository, in human-readable
    form, so a third party can read the contract without running the
    code.

Everything else — Tauri GUI, MCP server, 8+ providers, Postgres
backend, RFC 5424 syslog, multi-distro dispatch, fleet plan/execute,
Telegram approvals — is post-MVP at best and out of scope at worst.
The promises in [`VISION.md`](VISION.md) come first; SysKnife's
catalogue of architectural moves comes after, and only the ones that
make those promises more testable get to come at all.
