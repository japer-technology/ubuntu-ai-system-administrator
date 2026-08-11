# Deep Lessons from RHEL Lightspeed Sysadmin Agents (`rhel-lightspeed/sysadmin-agents`)

This document is a deep companion to [`ALTERNATIVES.md`](ALTERNATIVES.md)
and [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md). It reads the
[`rhel-lightspeed/sysadmin-agents`](https://github.com/rhel-lightspeed/sysadmin-agents)
project — and its underlying tool surface,
[`rhel-lightspeed/linux-mcp-server`](https://github.com/rhel-lightspeed/linux-mcp-server)
— through the Ubuntu Zombie filter defined in [`VISION.md`](VISION.md):
*Ubuntu LTS + a real local Unix account + a private Tailscale interface
+ an LLM under human approval, on a single operator-owned machine*.

Sysadmin Agents matters because it is the closest thing in the
alternatives catalogue to "the OS vendor itself shipping an LLM agent
for Linux administration." That makes it the most interesting reference
for *framing* (what does a vendor-grade Linux agent look like?) and the
most dangerous one to copy from naively, because its shape — fleet, SSH,
read-only, multi-agent, Gemini-locked, container-first — is almost the
mirror image of Ubuntu Zombie's shape.

The job of this file is to decide, capability by capability, what to
**borrow**, what to **translate**, what to **defer**, and what to
**explicitly refuse**.

## What Sysadmin Agents actually is, in one paragraph

Sysadmin Agents is a Red Hat / RHEL Lightspeed project that packages a
collection of AI agents for Linux administration. A single
**orchestrator** agent (`sysadmin`) accepts a natural-language problem
description and routes it via `transfer_to_agent` to one of five
**specialist** sub-agents — RCA, performance, capacity, upgrade, and
security. The specialists reason with Google ADK's `PlanReActPlanner`
(structured `/*PLANNING*/`, `/*ACTION*/`, `/*REASONING*/`,
`/*FINAL_ANSWER*/` blocks) and execute against a sidecar **MCP server**
(`linux-mcp-server`) that exposes 19 **strictly read-only** Linux
diagnostic tools — system info, journal logs, service status,
processes, disk usage, network state, audit logs, and so on. The MCP
server reaches target hosts over **SSH with key-based authentication**;
the agents and MCP process live together inside a container, behind an
ADK web UI on `localhost:8000`. The default model is **Google Gemini**.
The system is positioned for *system administrators, DevOps, and SREs*
operating *fleets* of RHEL/Fedora servers, not for individual desktop
ownership.

Ubuntu Zombie is the opposite shape on most of those axes. The
interesting question is which *ideas* from Sysadmin Agents survive the
translation to a single Ubuntu LTS desktop with a real `zombie` Unix
account, a Tailscale-only interface, and a mandatory approval gate in
front of every mutation.

## The axis-by-axis comparison

| Axis                          | Sysadmin Agents                                                                                  | Ubuntu Zombie                                                                              | Implication                                                                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Host target                   | One or many RHEL / Fedora servers, reached over SSH from a separate runner                       | A single Ubuntu Desktop **LTS** machine the operator already owns                          | Sysadmin Agents is a fleet tool; Zombie is a per-machine resident. Don't import fleet abstractions into the MVP.                                     |
| Distro posture                | RHEL/systemd-focused; "optimised for Red Hat Enterprise Linux systems"                           | Ubuntu LTS-only, by design                                                                 | Both projects honestly encode a distro choice. Zombie should keep doing this and resist generic-Linux drift.                                         |
| Privilege model               | SSH user on remote hosts; `sudo` recommended but optional; tools are **read-only**               | Dedicated local `zombie` account with passwordless `sudo` on this machine                  | Zombie is strictly more privileged and strictly more local. Read-only is not a substitute for an approval gate when you can also *write*.            |
| Interface                     | Browser UI at `http://localhost:8000` served by ADK Web / FastAPI inside a container             | Private chat surface, bound to `127.0.0.1`, exposed only over the operator's Tailscale net | Both are localhost-first. Zombie's tailnet posture is stronger; do not regress to "just trust the container network".                                |
| Inference                     | Google Gemini via `GOOGLE_API_KEY` (single provider, single vendor)                              | Cloud LLM in MVP, local models on roadmap, provider-swappable                              | Sysadmin Agents' vendor lock is the trade-off it accepts for ADK's reasoning quality. Zombie should not import the lock-in.                          |
| Agent topology                | Orchestrator + five specialists, dispatched via `transfer_to_agent`                              | One agent, one operator, one machine                                                       | Multi-agent dispatch is interesting and **out of scope for the MVP**, as already called out in `ALTERNATIVES-LESSONS.md`.                            |
| Tool surface                  | 19 typed, read-only MCP tools served by `linux-mcp-server` over stdio                            | Typed actions executed by a small local executor (planned)                                 | The *shape* (typed tools, MCP-compatible) is exactly what Zombie wants. The *content* (read-only verb set) is the right *starting* tier.             |
| Reasoning UX                  | `PlanReActPlanner` with explicit `/*PLANNING*/`, `/*ACTION*/`, `/*REASONING*/`, `/*FINAL_ANSWER*/` | Free-form chat, today                                                                      | Borrow the structured-blocks idea; visible reasoning is itself an audit and approval primitive.                                                      |
| Human-in-the-loop             | Effectively *not present* — safe because the tools cannot mutate. Recommendations are text.       | Mandatory approval gate per [`VISION.md`](VISION.md)                                       | Sysadmin Agents avoids the HITL problem by never mutating. Zombie *does* mutate, so HITL is non-negotiable; do not copy the "no approval" posture.   |
| Audit                         | Per-command SSH execution against remote hosts; agent traces visible in ADK UI                   | "An auditable trail of every command the AI proposes or runs" ([`VISION.md`](VISION.md))   | Zombie must add a signed, append-only audit log on top of anything it learns about tool-call traces from ADK-style UIs.                              |
| Distribution shape            | `pip install -e .`, container image, OpenShift/Kubernetes manifests                              | Transparent bash installer that creates a real Unix account                                | Zombie's blast radius is bigger per-host; install transcript and reversibility matter more.                                                          |
| Scope                         | "Enterprise-grade AI agents for Linux/RHEL system administration" across a fleet                 | "Computer that can administer itself" — one machine, one operator                          | Two legitimate but very different products. Read Sysadmin Agents' menu as inspiration, not as a target spec.                                         |

## Capabilities to borrow now (load-bearing for the MVP)

These are Sysadmin Agents primitives that map directly onto promises
Ubuntu Zombie has already made in [`VISION.md`](VISION.md) or are
implied by the existing top-five takeaways in
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md).

### 1. A first-class read-only diagnostic tier

The entire `linux-mcp-server` surface is **strictly read-only by
construction**: `get_system_information`, `get_cpu_information`,
`get_memory_information`, `get_disk_usage`, `list_processes`,
`get_journal_logs`, `get_service_status`, `get_service_logs`,
`get_audit_logs`, `list_directories`, `list_block_devices`, and so on.
Nothing in that set can change the machine. That makes the *entire
diagnostic conversation* approval-free without losing safety, because
the worst case is "the agent reads a log you could already read."

This is the strongest single architectural idea to import. It validates
the line in `ALTERNATIVES-LESSONS.md` that "diagnostic-first is a
legitimate scope" and gives it teeth: Ubuntu Zombie should ship a
clearly delineated **read-only diagnostic tier** where the executor
*physically cannot* mutate the system — separate code path, separate
typed-action enum, separate audit category — and a **mutating tier**
behind the approval gate. The split is not a UX nicety; it is what lets
"what is using my disk?" feel instant while "remove these files" still
goes through the proposer → policy → approve → execute → log loop.

Concretely, the verbs to lift from `linux-mcp-server` as the opening
read-only catalogue are well-chosen: system identity, CPU, memory,
disk, processes, services, journal, service-specific logs, audit logs,
block devices, network interfaces, and directory listings. They are a
good checklist for Ubuntu Zombie's first read-only tool set.

### 2. Typed tools served over MCP, not free-form shell

`linux-mcp-server` is a separate process, communicates with the agent
over stdio MCP, and exposes each diagnostic as a typed tool. The agent
never composes shell strings; it calls `get_journal_logs(priority=err,
unit=rhcd, lines=100, host=...)` and the MCP server is the *only* thing
that knows how to render that into a real command.

This is the same conclusion `ALTERNATIVES-LESSONS.md` already reaches
from SysKnife and Cline — "typed actions, not free-form shell" — and
seeing a vendor-grade project commit to it via MCP raises the
confidence that Ubuntu Zombie's executor should ship as a typed tool
catalogue from day one, with MCP-compatible signatures even if the MVP
does not yet speak the protocol on the wire. The payoff is the same
one Sysadmin Agents enjoys: the renderer / approver / auditor can be
written once against a structured action object instead of being
re-derived from a shell string at every layer.

### 3. Structured, visible reasoning (`PlanReActPlanner` shape)

ADK's `PlanReActPlanner` forces every specialist's output into four
labelled blocks: `/*PLANNING*/`, `/*ACTION*/`, `/*REASONING*/`,
`/*FINAL_ANSWER*/`. The result is that the user — and any reviewer of
the audit log — can see *why* the agent did what it did, not just
*what* it did.

Ubuntu Zombie's audit story benefits from the same shape. Every
proposed action should be accompanied by a short structured rationale
written by the agent (what it intends to do, which tool calls it
intends to make, why those calls and not others, and what the expected
outcome is). That rationale becomes part of the approval surface (the
operator approves "the plan", not "the command") and part of the
signed audit record (the *reason* is captured alongside the *action*,
which makes after-the-fact review meaningful instead of forensic).

This is the cheapest important UX upgrade to borrow: it costs a prompt
template and a renderer.

### 4. Risk-class vocabulary on every recommendation

The capacity agent's example output rates each cleanup suggestion as
**SAFE / MODERATE / CAUTION / DANGEROUS** before listing the command
that would achieve it. The agent never *runs* the command; the rating
exists so the human reading the recommendation can prioritise.

`ALTERNATIVES-LESSONS.md` already names "named runbooks and a risk-
class vocabulary" as one of the top five takeaways (from LinuxAgent and
RHEL sysadmin-agents). Sysadmin Agents shows the most concrete
spelling of that vocabulary in the catalogue: a four-level ordinal,
attached *per recommendation*, not per command type. Ubuntu Zombie
should adopt the same four-level scale (or something very close) as the
mandatory annotation on every proposed mutating action. It maps
naturally onto the approval gate: SAFE actions can be eligible for
scoped auto-approve; CAUTION and DANGEROUS actions never are.

### 5. A named specialist vocabulary as the runbook starter set

Sysadmin Agents' five specialists — **RCA**, **performance**,
**capacity**, **upgrade**, **security** — are an excellent first-pass
taxonomy of what an operator actually wants help with on a personal
Linux machine. Ubuntu Zombie does *not* need to implement them as
separate agents (see below), but it should treat them as a starter set
of **named runbooks**: "diagnose a performance problem", "explain disk
usage and propose cleanup", "investigate the last crash / hang",
"check upgrade readiness before `do-release-upgrade`", "run a basic
security posture review". Each is bounded, each is something the
operator will recognise, and each is easier to audit than an open-ended
prompt.

This is the same idea `ALTERNATIVES-LESSONS.md` borrows from LinuxAgent
("runbooks as first-class objects"), but Sysadmin Agents has done the
useful work of *naming the runbooks a Linux operator actually needs*.
Borrow the names.

## Capabilities to translate (right idea, wrong shape)

### 1. The ADK Web UI → Zombie's private chat surface

Sysadmin Agents serves an ADK browser UI on `http://localhost:8000`
from inside a container, exposing routing decisions, tool calls, and
agent traces in a live panel. The *information* in that panel — which
specialist was chosen, which typed tools were called with which
arguments, what the reasoning was, what the final answer is — is
exactly the information Ubuntu Zombie's operator should see in chat.

The translation: Ubuntu Zombie keeps its single private chat surface
(bound to `127.0.0.1`, reached over Tailscale), and the chat
*messages themselves* render the same content the ADK UI shows —
collapsible reasoning blocks, a list of tool calls with their typed
arguments, and the final answer or proposed action. The UX win comes
from the structure, not from the browser-vs-chat substrate.

### 2. SSH transport on a remote target → in-process executor on the local machine

`linux-mcp-server` reaches its targets over SSH because the agents and
the machines are on different hosts; SSH is the natural trust boundary.
Ubuntu Zombie is in the opposite situation: the agent and the machine
*are the same machine*, and there is a real local Unix account
(`zombie`) to act as. SSH would be a worse trust boundary here, not a
better one — every Zombie command would round-trip through `sshd` only
to land on the same kernel.

The lesson to translate is *not* "use SSH" but "make the executor a
separate process from the agent with a small, well-typed protocol
between them". That protocol can be a Unix-domain socket, an MCP stdio
pipe, or a local `polkit`-mediated D-Bus service — the point is the
same separation Sysadmin Agents enforces between the FastAPI/ADK
process and the `linux-mcp-server` subprocess, scaled down to one
machine. The separation is what lets the proposer be replaced (or
ported, or sandboxed) without rewriting the executor, and it is what
keeps the audit log honest because the audit lives in the boring
executor, not in the chatty LLM client.

### 3. Multi-agent orchestration → single agent with named runbooks

`ALTERNATIVES-LESSONS.md` already says, plainly, that "multi-agent
orchestration in the MVP" is **not** a lesson to copy. Sysadmin
Agents' five-specialist split makes sense at fleet scale where a
performance investigation and a security audit may need genuinely
different prompts, tools, and even quotas. Ubuntu Zombie is one
machine and one operator; the *content* of the specialists is useful,
but the *dispatch machinery* (`transfer_to_agent`, sub-agent
lifecycles, per-specialist memory) is pure overhead at this scale.

Translation: one agent, one chat session, one runbook vocabulary. The
agent picks which runbook to run; there is no separate process to
"transfer" to.

### 4. Container/Kubernetes deployment → bash installer + real local user

Sysadmin Agents ships a `Containerfile`, `podman/docker run` recipes,
and an OpenShift/Kubernetes deployment path. That makes sense for an
enterprise tool that may run anywhere from a dev laptop to a managed
cluster. Ubuntu Zombie's distribution is explicitly the opposite — a
transparent bash installer that creates a real Unix account on the
operator's own Ubuntu LTS machine. A container would *hide* the trust
boundary the installer is trying to make legible.

Translation: keep the bash installer, but borrow the *legibility* of
the container approach — every dependency declared up front, every
file path predictable, every secret read from a named environment
variable, every component startable and stoppable as a `systemd` unit
the operator can `systemctl status`.

## Capabilities to defer

These are real Sysadmin Agents features that Ubuntu Zombie should
probably grow into eventually, but not in the MVP.

- **Multi-host conversations.** Sysadmin Agents' value proposition
  includes "query multiple hosts in one conversation". Ubuntu Zombie's
  vision is one machine. If Zombie ever grows a fleet story, it
  should look like *several independent Zombies that happen to share
  an operator*, not like one agent SSH-ing into many hosts.
- **A web UI in addition to chat.** ADK's tool-call inspector is
  genuinely useful for debugging. Zombie can defer it; the same
  information rendered well in chat covers the operator case, and the
  audit log covers the forensic case.
- **PlanReActPlanner as a hard contract.** Borrow the *shape*; defer
  enforcing it as the only output mode until there is evidence that a
  free-form reply ever beats it. Soft templates first, hard schemas
  later.
- **Specialist sub-agents as separate processes.** Defer the process
  split until two runbooks have genuinely incompatible prompts or
  tools. Until then, sub-agents are configuration, not architecture.
- **A pre-flight "upgrade readiness" runbook.** Useful but specific.
  Zombie's MVP should cover diagnose / explain / configure / repair /
  operate first; "check before `do-release-upgrade`" is a great
  second-wave runbook.

## Capabilities to explicitly refuse

These are choices Sysadmin Agents has made that Ubuntu Zombie should
*not* import, even later, because they conflict with promises in
[`VISION.md`](VISION.md).

### 1. "Read-only is the whole product"

Sysadmin Agents is safe in part because it cannot mutate anything; it
recommends commands for a human to run. Ubuntu Zombie's whole point is
the opposite — a computer that can *operate* itself. Refusing to
mutate would be refusing the product. The lesson is to *separate* the
read-only and mutating tiers, not to collapse the latter into "we'll
just print the command and let the human paste it".

### 2. Single-vendor LLM lock-in

Hardcoding Google Gemini via `GOOGLE_API_KEY` is a defensible enterprise
choice; the ADK reasoning quality is the trade. Ubuntu Zombie's
roadmap commits to local inference, and its operator owns the machine,
so the provider must be swappable. The Missy lesson ("swap the model
without touching policy") applies here too: every promise Ubuntu Zombie
makes — typed actions, approval gates, audit signatures — has to hold
across provider swaps.

### 3. Implicit trust in the container's localhost

Serving ADK Web on `localhost:8000` inside a container is fine when the
container *is* the trust boundary. On a personal Ubuntu LTS machine
sitting on a hostile LAN, "bind to localhost" is a much weaker
statement than "bind to localhost and only reach me over my tailnet,
and never publish a port." Zombie's Tailscale-by-construction posture
is stricter and should stay stricter.

### 4. Fleet-shaped assumptions

"Query multiple hosts", "session state preserved across conversations",
"OpenShift/Kubernetes deployment" — these are all reasonable for a
fleet tool. Importing any of them into the MVP would force Zombie to
grow concepts (host registries, cross-host audit aggregation, multi-
tenant approvals) that the one-operator-one-machine vision explicitly
excludes.

### 5. "Approval is unnecessary because the tools cannot break things"

This is true in Sysadmin Agents' threat model and false in Zombie's.
The moment an executor can `apt install`, edit `/etc/netplan/*.yaml`,
or `systemctl restart`, the read-only-tools justification disappears
and the proposer → approve → execute → log loop becomes mandatory
again. The approval gate is the price of being allowed to mutate.

## How Sysadmin Agents changes the top five takeaways

Rereading the top-five takeaways in
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) through what
Sysadmin Agents demonstrates concretely:

1. **Typed actions over raw shell strings.** Sysadmin Agents adds
   *credible evidence at vendor scale* that this is the right shape —
   19 typed MCP tools instead of a `bash` corner. Strengthens the
   takeaway.
2. **Signed, append-only audit logs.** Sysadmin Agents does *not*
   really do this (its safety story leans on read-only tools and an
   ADK tool-call trace rather than a signed audit log). The lesson is
   that Zombie cannot inherit Sysadmin Agents' implicit "the trace in
   the UI is the audit" stance; the audit log has to be its own
   primitive, signed and on disk, as Missy already showed.
3. **Per-action approval as the default UX.** Sysadmin Agents avoids
   the question by not having actions to approve. Zombie cannot.
   Takeaway unchanged but reinforced by negative evidence: without
   approval, you must give up mutation.
4. **Named runbooks and a risk-class vocabulary.** Sysadmin Agents
   contributes both the runbook names (RCA / performance / capacity /
   upgrade / security) and the risk vocabulary (SAFE / MODERATE /
   CAUTION / DANGEROUS). Adopt both, almost verbatim, as Zombie's
   starting taxonomy.
5. **Separate proposer, policy/guard, and executor.** Sysadmin Agents
   demonstrates the proposer/executor split cleanly (ADK agent vs
   `linux-mcp-server` subprocess). Zombie should mirror that split
   locally and *add* the policy/guard layer Sysadmin Agents does not
   need because its executor is read-only.

## Net summary

Sysadmin Agents is the closest thing in the alternatives catalogue to
"a major Linux vendor's idea of what an LLM-driven system
administrator should look like." Read as a *blueprint*, almost
everything about it is wrong for Ubuntu Zombie — fleet over single
host, SSH over local user, container over installer, Gemini over
provider-swappable, multi-agent over single-agent, read-only-only over
mutating-with-approval. Read as a *menu of primitives*, almost
everything about it is right: typed tools over MCP, a clearly bounded
read-only diagnostic tier, structured visible reasoning, a four-level
risk vocabulary, and a starter set of named runbooks that map onto
problems real operators actually have.

The job for Ubuntu Zombie is to take the primitives, refuse the
shape, and add the one thing Sysadmin Agents structurally does not
need: a signed audit log and a mandatory approval gate in front of
every action that can change the machine.
