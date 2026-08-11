# Deep Lessons from LinuxOS-AI (`ANVEAI/linuxos-ai`)

This document is a deep companion to [`ALTERNATIVES.md`](ALTERNATIVES.md)
and [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md), in the same
shape as [`ALTERNATIVE-MISSY.md`](ALTERNATIVE-MISSY.md),
[`ALTERNATIVE-LINUXAGENT.md`](ALTERNATIVE-LINUXAGENT.md),
[`ALTERNATIVE-SYSKNIFE.md`](ALTERNATIVE-SYSKNIFE.md), and
[`ALTERNATIVE-SYSADMINAGENTS.md`](ALTERNATIVE-SYSADMINAGENTS.md).

It reads [`ANVEAI/linuxos-ai`](https://github.com/ANVEAI/linuxos-ai)
through the Ubuntu Zombie filter defined in [`VISION.md`](VISION.md):
*Ubuntu LTS + a real local Unix account + a private Tailscale interface
+ an LLM under human approval, on a single operator-owned machine.*

LinuxOS-AI matters for Ubuntu Zombie for an unusual reason. Of every
project in the catalogue, it is the only one whose **framing** is the
mirror image of Ubuntu Zombie's — *"the first step towards an AI-native
Linux OS"*, with a four-phase roadmap that ends at "complete AI-native
OS" and "autonomous system management". It is also, on inspection, the
project with the **smallest gap** between its marketing surface and its
actual implementation: a ~430-line bash script (`aios`) that prints a
banner, dumps a few `top` / `df` / `vm_stat` lines, injects a system
prompt into `npx @google/gemini-cli`, and hands the user a chat.

That gap — *the distance between the elevator pitch and the executor* —
is the single most useful thing Ubuntu Zombie can learn from this
project. SysKnife teaches Zombie what to *build*. Missy teaches Zombie
what to *defend against*. LinuxOS-AI teaches Zombie what to *not say
out loud*, what to *not paper over*, and where the line between a
named in-OS administrator identity and a marketing wrapper actually
lives.

## What LinuxOS-AI actually is, in one paragraph

LinuxOS-AI is a TypeScript/Node.js workspace forked from Google's
Gemini CLI (`packages/cli`, `packages/core`, `packages/ui`, plus an
empty `packages/mcp-servers/`) with a single bash entry point, `aios`,
that the project bills as an *"Interactive AI System Administrator"*
and the *"first step towards an AI-native Linux OS"*. The `aios`
script runs on Linux or macOS, requires Node ≥ 18 and a
`GEMINI_API_KEY` exported in the operator's shell, and behaves as
follows: it prints an ASCII banner, runs a handful of local diagnostic
commands (`top`, `vm_stat` / `free`, `df`, `ifconfig` / `ip addr`,
`who`, `journalctl`, `systemctl`) under a small `case` dispatcher, and
then `execve`s `npx @google/gemini-cli` with a hand-written
sysadmin-flavoured system prompt. When the API is unavailable
(`check_api_availability` runs a 10-second probe), it falls back to a
purely local read-only command alias mode that can no longer install,
configure, or change anything. The installer (`install.sh`) checks
Node ≥ 18, prompts for a Gemini key, and offers to **append the key
in clear text** to `~/.bashrc` or `~/.zshrc`; the project's
`QUICKSTART.md` documents the same flow and ships with a real-looking
partial key string visible in the file (`AIzaSyCR1FJ7KN26986a...`).
The Gemini CLI underneath supports a sandbox option
(`GEMINI_SANDBOX=docker|podman`), an MCP server surface, and a
`--yolo` flag that **auto-accepts every action** the model proposes;
all three are inherited verbatim and surfaced in the `aios` help text
as supported options. The project's README declares a four-phase
roadmap (AI sysadmin → AI desktop environment → AI kernel integration
→ "full AI operating system"), and the only privilege model the
project owns is "whatever the invoking user can do, plus `sudo` when
the LLM is told to use it".

Ubuntu Zombie is the opposite shape on most of those axes. The
interesting question is which *ideas* survive translation, which
*claims* must not be repeated, and which *operational details* are
warning signs Ubuntu Zombie should design against from day one.

## The axis-by-axis comparison

| Axis                          | LinuxOS-AI                                                                                                | Ubuntu Zombie                                                                                                  | Implication                                                                                                                                                |
| ----------------------------- | --------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Framing                       | "First step towards an AI-native Linux OS"; AI owns the machine                                           | Ubuntu LTS with a private, root-capable administrator account; the *operator* owns the machine                 | Same neighbourhood, opposite trust direction. Zombie must keep saying "the operator owns the box; the AI is a tool with hands."                            |
| Host target                   | Linux *or* macOS, any distro; no LTS commitment                                                            | Supported Ubuntu Desktop **LTS** only                                                                          | LinuxOS-AI pays for cross-platform reach with the impossibility of any concrete safety primitive. Zombie should keep cashing the LTS-only simplification.  |
| Identity model                | None — `aios` runs as whoever invoked it; no dedicated account, no UID, no `getent passwd` answer         | Dedicated local `zombie` Unix account with passwordless `sudo`                                                 | "The administrator is a user you can name" is the load-bearing idea here, and LinuxOS-AI quietly skips it. Zombie's single biggest mental-model win.       |
| Privilege model               | Implicit: the LLM is given a shell and may call `sudo` if the operator's session has it                   | Explicit: a named account whose only purpose is to mediate privilege via typed actions                         | Privilege without an identity is privilege without an audit subject. Zombie's audit log gets to say *which user* did a thing; LinuxOS-AI's cannot.         |
| Distribution shape            | `git clone` + `npm install` + `npm run build`; a bash wrapper plus a bundled Gemini CLI                    | A transparent bash installer that creates a system account, configures `sudo`, joins Tailscale                  | LinuxOS-AI is an *application* the operator runs; Zombie is a *system change*. Different blast radius, different installer transcript bar.                  |
| Interface                     | Terminal session on the local box, started by the operator                                                | Private chat surface bound to `127.0.0.1`, reachable only over the operator's Tailscale tailnet                | LinuxOS-AI has no remote story at all. Zombie's tailnet posture is a feature, not an accident, and not something LinuxOS-AI argues against — it just lacks. |
| Inference                     | Google Gemini only; `GEMINI_API_KEY` hard-required; no provider abstraction in the wrapper                | Cloud LLM in MVP, local models on roadmap, provider-swappable                                                  | Single-vendor lock is the trade-off LinuxOS-AI accepts in exchange for Gemini CLI's tool surface. Zombie should not import that lock.                       |
| Agent topology                | One LLM, one chat, one prompt; tools come from Gemini CLI's built-in surface                              | One agent, one operator, one machine                                                                           | The single-agent shape is right; the rest of the architecture is what makes that shape safe. LinuxOS-AI ships the shape and skips the rest.                 |
| Action surface                | Free-form: whatever Gemini CLI's bundled tools (shell, file edit, web) can do, plus shell-out             | Typed actions executed by a small local executor                                                                | No typed action layer at all. Every safety primitive collapses to *the system prompt asking nicely*; Zombie should treat this as a non-starter.             |
| Human-in-the-loop             | Inherited from Gemini CLI; `--yolo` auto-accepts everything; `--sandbox` is optional                       | Mandatory per [`VISION.md`](VISION.md): classify → propose → approve → run → log                               | The existence of an opt-in "approve nothing" flag is the central anti-pattern. Zombie's risk ceiling must be *bounded by the enum*, not by the operator's patience. |
| Risk classification           | None. The system prompt mentions "ask for confirmation for potentially dangerous operations"               | Risk class is a first-class enum that drives policy                                                              | "Safety as a string in the system prompt" is the failure mode Zombie's typed-action layer exists to prevent. Useful as a negative example.                  |
| Audit                         | Whatever Gemini CLI prints to the terminal; no signed log, no chain, no exporter                          | Tamper-evident, externally verifiable audit log (Ed25519 / hash-chained)                                        | Without an audit primitive, "the operator can review what the AI did" is *terminal scrollback* and dies with the session. Zombie's bar is higher.           |
| Sandbox                       | `GEMINI_SANDBOX=docker|podman` available *and off by default*                                              | The machine *is* the operator's machine; safety comes from typed actions + approval, not container isolation    | Sandbox-as-opt-in is a sign of confused trust. Zombie shouldn't ship "you can turn safety on" — it should ship "safety is the only mode."                   |
| Secret handling               | Installer appends `GEMINI_API_KEY` in clear text to `~/.bashrc` / `~/.zshrc`; `QUICKSTART.md` shows a real-looking partial key | Secrets live in mode-`0600` files owned by the `zombie` account; never in shell rc files; never in docs         | The contrast is stark and instructive. LinuxOS-AI's pattern is one of the few that Zombie should *explicitly forbid in its installer*.                       |
| Telemetry                     | Inherited Gemini CLI telemetry (`telemetry.js`, `telemetry_gcp.js`); GCP target available                  | Local-by-default; no third-party telemetry without an explicit operator opt-in                                  | LinuxOS-AI's telemetry posture follows from being a wrapped vendor CLI. Zombie's posture should follow from operator ownership.                              |
| Marketing register            | "🚀 Revolutionising system administration"; "🤖 The future of computing"; "340% performance improvement"   | Sober, transparent, falsifiable                                                                                 | The register of the README *is* part of the trust contract. Zombie's docs should sound like the audit log they describe.                                    |
| Scope                         | "Phase 1: AI sysadmin" → "Phase 4: full AI operating system, autonomous system management"                | One machine, one administrator, no autonomy claim                                                                | The maximalist roadmap is the thing Zombie most needs *not* to import. The MVP delivers a tool, not a movement.                                              |

## The one capability genuinely worth borrowing

The whole point of reading every project in the catalogue is to find
the primitive that is sharper, smaller, or more honest than what
Ubuntu Zombie has today and to copy it. LinuxOS-AI has exactly one
such primitive, and it is one Ubuntu Zombie already half-implements.

### A single named, in-OS administrator identity

LinuxOS-AI's README and `aios` script are organised around one
rhetorical move: *the LLM is your system administrator*. The branding
is `aios`, the prompt is "You are LinuxOS-AI", the elevator pitch is
"talk to your sysadmin instead of typing commands at your shell". The
mental model is **a named role on the machine** rather than "an AI
feature in your terminal".

That mental model is exactly right. It is also the move that
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) already credits
to LinuxOS-AI under "lessons to borrow", and the move Ubuntu Zombie
makes literal: the administrator is a **real Unix account** named
`zombie`, that `getent passwd zombie` answers, that owns its config,
its socket, its audit log, and its `sudoers.d/` snippet, and that an
operator can point at and say *"that user did the thing"*.

LinuxOS-AI gets the *naming* right and stops there: the role exists in
the prompt and the docs but not in `/etc/passwd`. Ubuntu Zombie gets
to take the framing one architectural layer deeper and make the role
a kernel-recognised identity. The lesson is:

- A named in-OS administrator identity is a stronger mental model than
  "an AI feature in your terminal", because it is something the
  operator can talk *about* rather than just *to*.
- The naming is not enough. The identity has to be **mechanical** —
  a UID, a home directory, a `sudoers.d/` rule, an account the
  operator could disable with `usermod -L zombie` if it ever
  misbehaves.
- The audit log is the *receipt* of that identity. Every entry should
  be of the form *"zombie@host at time T proposed action A, classified
  R, approved by operator O, executed with outcome X"*. The identity
  is what makes the subject of that sentence non-trivial.

Everything else useful about LinuxOS-AI either belongs to Gemini CLI
(and is therefore a lesson about Gemini CLI rather than about
LinuxOS-AI), or is a negative example. The rest of this document is
about those negative examples — what they teach, and how Ubuntu Zombie
should refuse them.

## Anti-patterns to refuse explicitly

These are the LinuxOS-AI choices Ubuntu Zombie should not just decline
to copy but should design *against*. Each one is a specific failure
mode the Zombie architecture has to prevent by construction.

### 1. "Safety as a string in the system prompt"

LinuxOS-AI's only safety layer is a paragraph in its system prompt:

> 🔒 SAFETY PROTOCOLS:
> - Always explain what commands will do before executing
> - Ask for confirmation for potentially dangerous operations
> - Provide rollback options when possible
> - Use dry-run mode when available

There is no enforcement. The "safety protocols" are advice to the
model, which is free to follow them, paraphrase them, ignore them
under prompt injection, or skip them entirely when `--yolo` is set.

This is the failure mode the typed-action layer described in
[`ALTERNATIVE-SYSKNIFE.md`](ALTERNATIVE-SYSKNIFE.md) exists to
prevent. Ubuntu Zombie's rule must be the inverse: **safety is not
something the model is asked to do; it is something the executor
enforces on the model's output, before the model's output reaches
anything that can change the system.** Risk classification is a
function of the typed action, not a sentence in a prompt; approval is
a state machine, not a courtesy; the audit log is a cryptographic
artefact, not a transcript.

### 2. `--yolo` exists and is documented

LinuxOS-AI's help text lists `--yolo` ("auto-accept all actions") as a
first-class option. Even with the "(use carefully!)" warning in
`QUICKSTART.md`, the existence of a flag that disables the approval
gate is the central anti-pattern of the entire space. It collapses
*every* other safety primitive — risk class, content hash, type-to-
confirm, audit log integrity — into something that can be bypassed by
adding one flag to a shell invocation.

Ubuntu Zombie's rule, already foreshadowed by SysKnife: **auto-approve
is bounded by the risk enum, not by a single flag.** A reasonable
operator can opt into auto-approve for `Low` (read-only diagnostics);
they can deliberately opt into auto-approve for `Medium` (mutating-
local); they cannot opt into auto-approve for `High` (destructive,
irreversible, wide-blast-radius). The ceiling is a property of the
system, not a property of the invocation.

### 3. Sandbox is opt-in

LinuxOS-AI inherits Gemini CLI's `GEMINI_SANDBOX=docker|podman`
option. It is off by default, and the README never makes it a
condition of safe use. The implicit posture is "run me without a
sandbox; the prompt will keep things sensible".

Ubuntu Zombie should not import that posture even by accident. Zombie
does not, in the MVP, sandbox individual actions inside a container —
it does something stronger: it executes only typed actions through a
small privileged executor that the operator has explicitly approved.
The point is that **there is no off-mode**. There is no flag the
operator can flip to make the typed-action layer optional and let the
model run shell.

### 4. Secrets in shell rc files (and in the documentation)

LinuxOS-AI's `install.sh` offers to append the operator's Gemini API
key in clear text to `~/.bashrc` or `~/.zshrc`. `QUICKSTART.md` then
echoes a real-looking partial key (`AIzaSyCR1FJ7KN26986a...`) into the
documentation as part of the "you're ready to go!" copy.

Both are concrete failure modes Ubuntu Zombie should design against:

- **Secrets never live in shell rc files.** They live in mode-`0600`
  files owned by the `zombie` account, in a documented location under
  `/etc/zombie/` or `~/.zombie/`. The installer should *say* where it
  put each secret in its install transcript, and it should never write
  a secret into a file that other processes — editors, history files,
  shell completion — will read.
- **Secrets never appear in documentation, even partially.** A
  documented partial key teaches the wrong habit and trains operators
  to share screenshots with key fragments visible. Ubuntu Zombie's
  docs should use a fully synthetic, obviously fake placeholder
  (`TS_AUTHKEY_REPLACE_ME`, `OPENAI_API_KEY_REPLACE_ME`).
- **The installer's transcript is the operator's contract.** "Wrote
  key to `~/.bashrc`" must never be a line in that transcript.
  "Wrote key to `/etc/zombie/secrets.env` (mode `0600`, owner
  `zombie`)" should be.

### 5. No identity, no audit subject

LinuxOS-AI runs `aios` as whoever invoked it. If the operator runs it
as themselves, the audit subject of every action is the operator. If
they sudo into root and run it there, the audit subject is root. In
neither case is the AI a distinct subject; there is no way for the
audit log on the underlying system (`/var/log/auth.log`, `journalctl
_UID=…`) to say "the AI did this and the human did that".

Ubuntu Zombie's `zombie` account is exactly the fix. Every action the
AI proposes runs as `zombie` (under `sudo` via the executor when
elevation is required), and the underlying system's audit primitives
— `auth.log`, `journalctl`, `last`, `who`, `getent passwd zombie` —
naturally separate AI-originated activity from human-originated
activity. The Zombie audit log layers on top; the system's own audit
primitives already do the right thing because the identity is real.

### 6. The maximalist roadmap

LinuxOS-AI's README publishes a four-phase plan:

> Phase 1: AI System Administrator (✅ CURRENT)
> Phase 2: AI Desktop Environment (🔄 NEXT)
> Phase 3: AI Kernel Integration (⏳ FUTURE)
> Phase 4: Full AI Operating System (⏳ VISION)

Phases 2–4 commit, in writing, to *AI-powered window management*, *AI-
optimised resource allocation*, *predictive system maintenance*,
*self-healing capabilities*, *autonomous system management*, and
"voice-controlled everything". None of these are wrong to dream
about; all of them are dangerous to promise.

The lesson for Ubuntu Zombie is not "have a smaller roadmap". It is:
**ship a roadmap whose phases are operationally distinguishable from
each other and whose later phases are conditional on the earlier ones
working in the field.** [`VISION.md`](VISION.md) already does this:
the MVP is "private root-capable account on Ubuntu LTS over
Tailscale, with approval and audit", and later phases (local models,
fleet-of-one expanded to fleet-of-few, richer action catalogues) are
*concrete features* rather than *paradigm shifts*. The discipline is
to keep it that way.

### 7. Hype as user interface

LinuxOS-AI's README contains, verbatim:

> ⚡ System performance improved by 340%!
> 🔒 SSL Score: A+ (ssllabs.com)
> Database ready! Connection: localhost:1521/ORCLPDB1

These are demo-grade aspirational claims rendered as if they were
output. An operator reading the README cannot tell which lines are
*things the agent will actually print*, which are *things the author
hopes it would print*, and which are *transcribed from a single
lucky run*. The README is a marketing document wearing a screenshot's
clothing.

Ubuntu Zombie's documents — including this one — should be readable
as falsifiable claims. When [`VISION.md`](VISION.md) says "Tailscale-
only inbound", the install transcript and the firewall state on a
freshly installed box should make that statement true and checkable.
When the docs claim signed audit logs, `zombie audit verify` should
run and exit zero on a real installation. The rule is: *the docs
should sound like the audit log they describe*. Numbers in the docs
should be numbers an operator can reproduce.

### 8. A bash wrapper as the "architecture"

The honest description of LinuxOS-AI's architecture is: a 430-line
bash script that runs Gemini CLI with a long system prompt and a
fallback `case` statement. The README's *"Modular Agent System"*
diagram (InstallationAgent / SecurityAgent / PerformanceAgent /
FileAgent / DiagnosticAgent) does not correspond to any code in the
repository — there are no `*.ts` files under those names. The
"agents" exist only in the prompt the bash wrapper injects.

This is a useful negative example for Ubuntu Zombie's own
documentation. Architecture diagrams in the Zombie docs should
correspond to actual processes, sockets, files, and systemd units; if
a box on the diagram is "the LLM treats this as a role internally",
the diagram should say so. The reader should be able to take any box
on the diagram and find it on disk.

## Operational details worth designing against

A handful of small, concrete LinuxOS-AI choices are good enough as
*warnings* that Ubuntu Zombie should write its own rule for each one
into its installer and its docs.

- **The install transcript should never end with "AI features will be
  limited."** LinuxOS-AI's installer cheerfully proceeds without a
  Gemini key and tells the operator they can set it later. The
  resulting system is half-installed: the bash wrapper runs, the
  fallback `case` statement runs, but the headline feature does not.
  Ubuntu Zombie's installer should be all-or-nothing for its safety
  primitives: if `tailscale` is not present, if the `zombie` account
  cannot be created, if the audit-signing key cannot be written, the
  installer aborts and rolls back rather than producing a half-state.
- **An API-availability probe is not a safety primitive.**
  LinuxOS-AI's `check_api_availability` runs a 10-second test prompt
  against Gemini and uses the result to decide whether to enter
  "enhanced mode" or "local mode". This is fine as ergonomics and
  useless as safety: it tests reachability, not policy. Ubuntu
  Zombie's analogous check should test policy state — *the executor
  is reachable, the audit log opens for append, the signing key
  verifies* — not just *the provider answered*.
- **The chat surface should not be both the planner and the executor.**
  In LinuxOS-AI the chat surface (Gemini CLI's REPL) is also the
  thing that runs shell. There is no executor. Ubuntu Zombie's MVP
  may collapse the three roles (planner, approval gate, executor) into
  one binary, but the *interfaces* between them must be real, and the
  chat surface must never call `execve` directly — it must hand a
  typed action to the executor and wait for an audited result.
- **A fallback mode that loses safety is a worse state, not a better
  one.** When LinuxOS-AI's API is down, the fallback mode is *also*
  the mode without approval, without audit, and without the LLM that
  was supposed to mediate the action. Ubuntu Zombie's degraded modes
  should preserve the safety primitives even when they cost
  functionality: if the LLM is unreachable, the executor still
  refuses raw shell, the audit log still appends, the approval gate
  still gates.
- **Multi-OS support is not free.** LinuxOS-AI claims Linux *and*
  macOS support, then ships code that branches on `vm_stat` vs
  `free`, `ifconfig` vs `ip addr`, `launchctl` vs `systemctl` inside
  the same `case` statement. The branches are shallow and the
  resulting system administrator has roughly half the capabilities on
  either platform. Ubuntu Zombie's "Ubuntu LTS only" stance is the
  honest version of this: pick one substrate, rely on it, and let the
  cross-platform story start when the single-platform story is
  load-bearing.
- **A workspace whose `packages/mcp-servers/` is empty is documenting
  an aspiration, not a feature.** LinuxOS-AI's `packages/`
  directory contains `cli`, `core`, `ui`, and `mcp-servers` — and
  `mcp-servers` is an empty directory. Ubuntu Zombie should keep the
  rule that an artifact in the tree (a directory, a service file, a
  CLI subcommand) is something that *does* something. Empty
  scaffolding is a category of lie even when it is well-intentioned.

## Where LinuxOS-AI is accidentally honest

It is worth giving LinuxOS-AI credit where the accidents work in its
favour. Two things the project does are useful inputs for Ubuntu
Zombie, even though neither is presented as a design contribution.

- **The bash wrapper is short and readable.** A 430-line bash script
  is easy to audit end-to-end. Whatever else is true of the project,
  the operator can read `aios` in twenty minutes and know exactly what
  it does. Ubuntu Zombie's executor and installer should hit the same
  bar: small enough that a third party can read them in one sitting
  and predict their behaviour without running them.
- **The chat-first ergonomics are right.** The thing the operator
  actually does — "open a chat with the administrator and describe
  the problem in English" — is the same thing Ubuntu Zombie's chat
  surface is designed to enable. The disagreement is not about
  ergonomics; it is about everything else.

## Top ten LinuxOS-AI lessons, ranked

If only ten lessons survive from this whole document, in order:

1. **A named, in-OS administrator identity is the right mental model
   — and it has to be mechanical (a real Unix account), not just
   rhetorical (a name in a system prompt).**
2. **Safety must be enforced by the executor on the model's output,
   not asked of the model in its prompt.** Risk class, approval, and
   audit are checks on a typed value, not paragraphs in a string.
3. **Auto-approve is bounded by the risk enum, not by a flag.** A
   `--yolo`-style "approve everything" mode is a permanent refusal,
   regardless of how it is named or warned about.
4. **There is no off-mode for safety.** Sandboxes and approval gates
   that the operator can toggle off are confused trust; the typed-
   action layer is the system's only mode.
5. **Secrets live in mode-`0600` files owned by the agent account,
   never in shell rc files, never in screenshots, never in
   documentation — not even partially.**
6. **The installer's transcript is part of the trust contract.** If
   it ever ends with "AI features will be limited" or "you can fix
   this later", the installer has produced a half-state and should
   instead have aborted.
7. **Fallback modes preserve the safety primitives, not the headline
   functionality.** A degraded Zombie still refuses raw shell, still
   appends to the audit log, still gates approvals; a degraded
   LinuxOS-AI is a Gemini-less terminal with no AI.
8. **Architecture diagrams correspond to artefacts on disk.** Any
   "agent" in a diagram should be a process, a service, a typed-
   action namespace, or a file; not a line in a prompt and not an
   empty directory.
9. **Documents should be falsifiable.** Numbers in the README should
   reproduce on a freshly installed box; safety claims should be
   verifiable by a single command; transcripts should look like the
   real audit log.
10. **Phase roadmaps should be operational, not paradigmatic.** Later
    phases are concrete features conditional on earlier phases
    working in the field; they are not stages of a revolution.

Everything LinuxOS-AI does *well* — the chat-first ergonomics, the
named-administrator framing, the readability of the wrapper — Ubuntu
Zombie already does, or already plans to do, in a load-bearing form.
Everything LinuxOS-AI does *badly* is a worked example of a specific
failure mode the Zombie architecture has to prevent by construction.
Read in that spirit, the project's most useful contribution to Ubuntu
Zombie is the precision with which it shows where the line lives
between a marketing surface and an executor — and which side of that
line Ubuntu Zombie has to stay on.
