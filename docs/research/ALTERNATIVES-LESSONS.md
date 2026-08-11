# Lessons from the Alternatives

This document is a companion to [`ALTERNATIVES.md`](ALTERNATIVES.md). That
file catalogues the projects in the same neighbourhood as Ubuntu Zombie.
This file asks two harder questions:

1. **Which of those projects are closest to what Ubuntu Zombie actually
   is** — `Ubuntu LTS + root user + private interface + LLM` — and why?
2. **What concrete lessons should Ubuntu Zombie take from each of
   them**, both as ideas to borrow and as mistakes to avoid?

Ubuntu Zombie is deliberately narrow: it is a transparent installer that
adds a private, root-capable AI Systems Administrator account to a
supported Ubuntu Desktop LTS machine, reachable only over a private
Tailscale tailnet, with human approval and an audit trail in front of
every privileged action. See [`VISION.md`](VISION.md) for the exact
promise. The lessons below are read through that filter.

## The "closeness" axis

The defining shape of Ubuntu Zombie is:

| Axis                          | Ubuntu Zombie's position                                                               |
| ----------------------------- | -------------------------------------------------------------------------------------- |
| Host target                   | A single Ubuntu Desktop **LTS** machine the operator already owns                      |
| Privilege model               | A dedicated local Unix account with passwordless `sudo` (root-capable, not root-by-default) |
| Interface                     | Private local chat surface, tunnelled over Tailscale; never public                     |
| Inference                     | Cloud LLM in the MVP; local models on the roadmap                                      |
| Human-in-the-loop             | Mandatory: classify → propose → approve → run → log                                    |
| Distribution shape            | A transparent bash installer, not an appliance or a hosted service                     |
| Form factor sweet spot        | Desktops, towers, Mini PCs, and SBCs (e.g. Raspberry Pi-class) running Ubuntu LTS      |

A project is "close to Ubuntu Zombie" to the extent that it matches
*several* of those axes at once. Many of the projects in
`ALTERNATIVES.md` match one or two and miss the rest.

## Closest direct analogs

These are the projects that overlap on the most axes — single host, root
or root-capable, audited, approval-gated, intended to actually *operate*
the machine rather than just chat about it.

### Missy (`MissyLabs/missy`)
**Why it's close.** Security-first, self-hosted AI assistant for Linux,
explicitly designed as a single-host agent with default-deny on network,
filesystem, and shell, plus a multi-layer policy engine, signed JSONL
audit log, an interactive approval TUI, and an encrypted secret vault.
It is the only project in the list whose threat model and operational
posture line up with Ubuntu Zombie's almost point-for-point.

**Lessons to borrow.**
- **Signed, append-only audit logs (Ed25519 + JSONL).** Audit value
  comes from tamper-evidence, not just from "we wrote a file". This is
  a stronger bar than plain logging and is worth matching.
- **Default-deny is a feature, not a bug.** Start every capability
  (network, filesystem, shell) closed and require the operator to open
  it. Ubuntu Zombie already does this for inbound network (Tailscale-
  only); the same posture should extend to filesystem write scopes and
  command classes.
- **A dedicated approval TUI is worth building.** Stuffing approval
  into a generic chat surface dilutes it. A purpose-built approve /
  diff / reject view (even a minimal one) makes the human-in-the-loop
  visible instead of incidental.

**Lessons to *not* copy.** Missy bundles many advanced features
(prompt-injection sanitizer, code-evolution with git rollback,
encrypted vault, policy engine layers). Ubuntu Zombie's MVP is
deliberately small; resist the urge to import the entire surface area.
Pick the audit and approval primitives first.

### LinuxAgent (`Eilen6316/LinuxAgent`)
**Why it's close.** LLM-driven Linux operations CLI with mandatory
human-in-the-loop, a policy engine, SSH guards, runbooks, and audit
trails. Same job description, different ergonomics (CLI rather than
chat surface).

**Lessons to borrow.**
- **Runbooks as first-class objects.** A named, reviewable runbook
  ("rotate logs", "renew certificates", "diagnose Wi-Fi") is easier to
  audit than an open-ended prompt. Ubuntu Zombie should have a
  vocabulary of named operations long before it has a free-form
  "do anything" mode.
- **Classify commands by risk class.** Read-only, mutating-local,
  network-touching, destructive — and let policy and approval depend
  on the class, not on per-command rules.

**Lessons to *not* copy.** Pure CLI ergonomics; Ubuntu Zombie's
operator surface is a private chat over Tailscale, not a terminal
session, so the SSH-guard model needs to be re-expressed in a chat
context.

### SysKnife (`lacs-foundation/sysknife`)
**Why it's close.** Plain-language Linux sysadmin agent that proposes
*typed* actions, requires approval, executes through a daemon, and keeps
a tamper-evident audit chain. Fedora-first today but the model is
distro-agnostic and the architecture (proposer + approver + executor +
audit chain) is the architecture Ubuntu Zombie wants.

**Lessons to borrow.**
- **Typed actions, not free-form shell.** The LLM should emit a
  structured action ("install package X", "edit /etc/Y with this
  diff", "restart service Z") that the executor knows how to render,
  approve, and log — not a raw shell string. This is the single
  biggest safety win in the space.
- **Separate the proposer from the executor.** The LLM proposes; a
  small, boring, well-tested daemon executes. The executor is the
  thing you have to trust; keep it small enough to read in one sitting.

**Lessons to *not* copy.** Distro-specific assumptions. Ubuntu Zombie
should encode "Ubuntu LTS only" honestly rather than pretending to be
portable; that constraint is a feature.

### RHEL Lightspeed / sysadmin-agents (`rhel-lightspeed/sysadmin-agents`)
**Why it's close.** Multi-agent Linux troubleshooting system that uses
an MCP server (`linux-mcp-server`) to expose Linux administration as
tools. The closest thing to Ubuntu Zombie's "the OS is the product"
framing inside a major Linux vendor.

**Lessons to borrow.**
- **Treat Linux administration as a set of MCP-style tool surfaces.**
  Even if Ubuntu Zombie does not adopt MCP in the MVP, designing the
  executor as a set of typed tools (read logs, restart unit, edit
  config, install package) leaves the door open to swap providers and
  to compose with other agents later.
- **Diagnostic-first is a legitimate scope.** Many useful interactions
  are read-only: "why did this fail?", "what is using my disk?". These
  do not need approval gates and should be cheap and fast.

**Lessons to *not* copy.** Multi-agent orchestration in the MVP.
Ubuntu Zombie is one machine, one administrator. Multi-agent dispatch
is interesting and out of scope.

### LinuxOS-AI (`ANVEAI/linuxos-ai`)
**Why it's close.** "AI-native Linux OS" direction — natural-language
system administration, package management, security, diagnosis,
optimisation, all on a single host.

**Lessons to borrow.**
- **A single named, in-OS administrator identity** is a clearer mental
  model than "an AI feature in your terminal". Ubuntu Zombie's
  `zombie` account is exactly that, and the naming matters: the
  operator should be able to point at *which user* did a thing.

**Lessons to *not* copy.** "AI-native OS" branding implies the AI
*owns* the machine. Ubuntu Zombie's vision is the opposite — the
operator owns the machine and the AI is a tool with hands. Keep the
framing humble.

## Strong general-purpose comparables

These are not Linux-sysadmin-specific, but they are local, agentic, and
approval-aware, and the ergonomics they have settled on are directly
applicable.

### Open Interpreter (`OpenInterpreter/open-interpreter`)
**Lessons to borrow.**
- **Per-action confirmation as the default UX.** Open Interpreter's
  "here is the code I want to run, approve?" loop is the right floor
  for any local agent that touches the machine. Auto-approve modes
  must be explicit, scoped, and revocable.
- **Local-model support is a roadmap commitment, not a feature flag.**
  Ollama / llama.cpp paths exist from day one even though most users
  will start on a cloud model. Ubuntu Zombie's roadmap should treat
  local inference the same way.

### Goose (`aaif-goose/goose`, formerly `block/goose`)
**Lessons to borrow.**
- **MCP extensions are the right plug-in shape.** Instead of growing a
  custom plug-in API, lean on MCP for shell, files, and dev workflow
  extensions. It composes with the rest of the ecosystem.
- **Foundation governance matters for trust.** Goose's move to the
  Linux Foundation is a credibility signal. Ubuntu Zombie should keep
  its installer and policies legible enough that a third party could
  audit them without privileged access.

### Cline (`cline/cline`)
**Lessons to borrow.**
- **Every edit and command requires approval unless auto-approve is
  explicitly enabled, and the SDK exposes hooks for logging,
  auditing, and policy enforcement.** That is the right separation:
  the agent proposes, the policy layer decides, the audit log
  records. Ubuntu Zombie should mirror that three-layer split even if
  the MVP collapses them into one process.

### Butterfish (`bakks/butterfish`)
**Lessons to borrow.**
- **Transparent, user-editable prompts and verbose logging instead of
  hidden behaviour.** This is a strong cultural cue. Ubuntu Zombie's
  prompts, policies, and runbooks should live on disk in readable
  files, not in opaque embedded strings.

## Useful building blocks (not products)

These are pieces Ubuntu Zombie could *use* or imitate, rather than
projects it competes with.

### linux-administration-mcp (`Cosmicjedi/linux-administration-mcp`)
**Lesson.** SSH-based Linux admin tools (execute, diagnose, services,
logs, network, packages, security audit) with hostname-scoped,
daily-rotated audit logs is a reasonable shape for the executor's tool
catalogue. Even if Ubuntu Zombie does not adopt this server, the *set*
of verbs it exposes is a good checklist.

### HumanLayer (`humanlayer.dev`) and Phantasm (`edwinkys/phantasm`)
**Lesson.** Human-in-the-loop is generic enough to be a library. If
Ubuntu Zombie's approval surface ends up being interesting enough to
extract, it should look like one of these — a small, framework-agnostic
API for "this action needs a human, here is what they need to see".
Conversely, if HumanLayer or Phantasm are good enough off the shelf,
borrowing rather than rebuilding is the right call.

### RoboShellGuard (`robokeys/roboshellguard`) and ShellGuard
**Lesson.** Risk scoring, command approval workflows, and read-only SSH
modes for diagnostics are independently useful primitives. The lesson
is that the *guard* is worth separating from the *agent*: the guard
should be able to say "no" to any agent, including a future one.

## Adjacent but materially different

These projects show up in the same searches but optimise for different
goals; the lessons from them are mostly negative ("don't drift this
way").

- **Aider, ShellGPT, Terminal Agent.** Excellent local CLIs, but
  optimised for the developer-in-a-terminal workflow, not for "the
  computer administers itself for a non-developer owner". Ubuntu
  Zombie should not collapse into a smarter shell.
- **DuckClaw, OpenClaw.** Broader personal-assistant / operator
  platforms. The permission tiers and audit log ideas are good; the
  scope is much wider than Ubuntu Zombie's, and chasing parity would
  blow up the MVP.

## What "Ubuntu LTS + root user + Pi + LLM" specifically implies

Reading the alternatives through the small-machine, Ubuntu-LTS,
operator-owned lens gives a few extra constraints that none of the
alternatives optimise for and that Ubuntu Zombie should not lose:

1. **Ubuntu LTS as the supported substrate.** The installer can rely
   on `systemd`, `apt`, `netplan`, `ufw`, and the LTS kernel cadence.
   That is a real simplification and should be defended; do not chase
   distro-portability before the single-distro story is solid.
2. **A real local Unix account, not a service principal.** "The
   administrator is a user you can `getent passwd` for" is a clearer
   trust boundary than "the administrator is a daemon with a token".
   Most of the alternatives blur this; Ubuntu Zombie should not.
3. **Pi-class hardware is a first-class target.** That bounds memory,
   CPU, and storage budgets. It is also why cloud inference is the MVP
   path and local models are on the roadmap rather than the critical
   path — a 4–8 GB SBC cannot host a competent model today, but it can
   absolutely host the executor, audit log, and approval surface.
4. **Private interface by construction.** Tailscale-only inbound,
   chat surface bound to `127.0.0.1`, no public listener. None of the
   alternatives go this far by default; this is a feature, not an
   accident, and should be preserved as the alternatives evolve.
5. **One operator, one machine, one trust boundary.** Fleet
   management, multi-tenant approvals, and shared audit logs are out
   of scope. The alternatives that try to do all three end up with a
   surface area Ubuntu Zombie should not import.

## Top five takeaways

If only five lessons survive from this whole exercise, they should be:

1. **Typed actions over raw shell strings** (from SysKnife, Cline).
2. **Signed, append-only audit logs** (from Missy, SysKnife).
3. **Per-action approval as the default UX, with explicit, scoped
   auto-approve** (from Open Interpreter, Cline, LinuxAgent).
4. **Named runbooks and a risk-class vocabulary** instead of
   free-form "do anything" prompts (from LinuxAgent, RHEL
   sysadmin-agents).
5. **Separate proposer, policy/guard, and executor** even inside a
   single binary (from Cline's SDK shape and RoboShellGuard's
   guard-as-its-own-thing posture).

Everything else is decoration.
