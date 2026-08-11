# Deep Lessons from LinuxAgent (`Eilen6316/LinuxAgent`)

This document is a deep companion to [`ALTERNATIVES.md`](ALTERNATIVES.md)
and [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md). It sits beside
[`ALTERNATIVE-MISSY.md`](ALTERNATIVE-MISSY.md) and asks the same kind of
question about a different neighbour: of the projects in the catalogue,
**LinuxAgent** is the one whose job description matches Ubuntu Zombie's
most literally — *let an LLM propose Linux operations, never let it
execute without a human, prove after the fact that the human actually
approved* — even though its ergonomics (a CLI you launch yourself) are
not the ergonomics Ubuntu Zombie is going to ship (a private chat
account that lives on the machine).

That overlap of mission and divergence of shape is exactly what makes
LinuxAgent worth reading carefully. The job of this file is to read
LinuxAgent through the Ubuntu Zombie filter defined in
[`VISION.md`](VISION.md) — *Ubuntu LTS + a real local Unix account + a
private Tailscale interface + an LLM under human approval* — and
decide, capability by capability, what to **borrow**, what to
**translate**, what to **defer**, and what to **explicitly refuse**.

## What LinuxAgent actually is, in one paragraph

LinuxAgent is a Python CLI for Linux operators that puts an LLM behind
a deterministic safety boundary instead of in front of one. The model
proposes a structured `CommandPlan`; that plan is tokenised and
evaluated by a YAML-driven, capability-based policy engine which
returns `SAFE` / `CONFIRM` / `BLOCK` with a risk score, matched rules,
and the capabilities the command would exercise. First-time
LLM-generated commands always confirm; destructive commands confirm
every time and can never be conversation-whitelisted; commands hitting
sensitive paths block outright. Confirmation happens through a
LangGraph `interrupt()` checkpoint with a three-way TUI menu (`Yes`,
`Yes, don't ask again` scoped to the same argv shape in the same
conversation thread, `No`), and a non-TTY confirmation auto-denies.
Execution runs through `asyncio` subprocesses with `shell=False`,
optionally inside a sandbox runner (`noop`, `local`, or capability-
probed `bubblewrap`, with Landlock on the design roadmap). Tool output
is bounded and redacted before it is shown back to the model. Every
decision is written to a `0o600` hash-chained JSONL audit log that
`linuxagent audit verify` can re-validate. File edits use a separate
`FilePatchPlan` path: unified-diff preview, per-file approval, atomic
write through a temp file with backups under `.linuxagent-patch-*`,
and automatic rollback if any later step in the transaction fails.
Read-only workspace tools (`read_file`, `list_dir`, `search_files`)
let the planner ground itself without executing anything. An MCP
prototype (`linuxagent mcp`) exposes only the read-only policy-
classify and audit-verify surfaces — never execution. SSH cluster
operations get their own batch-confirmation flow, mandatory
`known_hosts` verification, remote-shell metacharacter blocking, and
remote-profile audit. Quality is enforced by a make-target gauntlet
(`make red-team` runs 24 adversarial cases in CI, `make benchmark`
reports P50/P95/P99 policy latency, `make sandbox` exercises the
runner boundary, plus `ruff`, `mypy`, `bandit`, and an 80% coverage
floor).

Ubuntu Zombie is much smaller and shaped very differently — a bash
installer that creates one privileged Unix account, a chat surface
bound to localhost and surfaced over Tailscale, a single Ubuntu LTS
substrate. The interesting question is which of LinuxAgent's
*primitives* are load-bearing for the safety story Ubuntu Zombie
promises in [`VISION.md`](VISION.md), and which are CLI-shaped
choices that would distort Ubuntu Zombie's chat-and-account shape if
imported wholesale.

## The axis-by-axis comparison

| Axis                          | LinuxAgent                                                                                              | Ubuntu Zombie                                                                              | Implication                                                                                                                                          |
| ----------------------------- | ------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| Host target                   | Any Linux with Python 3.11+; servers, VMs, containers, homelab                                          | Supported Ubuntu Desktop **LTS** only                                                       | Ubuntu Zombie keeps the LTS-only simplification; LinuxAgent pays a portability tax (provider matrix, distro-agnostic policy data) that Zombie should not import. |
| Install shape                 | `./scripts/bootstrap.sh` or `pip install linuxagent`; user-level launcher in `~/.local/bin`             | Transparent bash installer that creates a real Unix account and configures Tailscale       | LinuxAgent is a *user-space tool an operator runs*. Zombie is a *system change that becomes the operator*. Zombie's audit and approval story must survive that escalation. |
| Privilege model               | Runs as the invoking user; remote `sudo` is opt-in per host                                              | Dedicated `zombie` account with passwordless `sudo`                                        | Ubuntu Zombie is strictly more privileged. Every LinuxAgent safety primitive needs to be *at least as strong* in Zombie — the policy engine, the audit log, and the approval gate are not optional. |
| Interface                     | Terminal CLI with arrow-key menus, `/resume`, `/new`, `/tools`, `!direct` mode                          | Private chat surface, Tailscale-only inbound, no public listener                           | Borrow LinuxAgent's *idea* of a structured approval prompt; translate the TUI menu into a chat-native equivalent rather than copying the terminal ergonomics. |
| Inference                     | OpenAI, DeepSeek, Anthropic (extra), Ollama / any OpenAI-compatible relay                                | Cloud LLM in MVP, local models on roadmap                                                  | The "swap the model without touching policy" property is worth importing now even though Zombie has one provider today.                              |
| Human-in-the-loop             | Mandatory; three-way menu; first-LLM-command always confirms; destructive always confirms; non-TTY auto-denies | Mandatory; classify → propose → approve → run → log                                        | LinuxAgent's *defaults* (auto-deny on missing operator, never-whitelist destructive) are the right floor for Zombie too.                              |
| Action representation         | Structured `CommandPlan` (JSON-validated) and `FilePatchPlan` (unified-diff, transactional)             | Currently shell-level; runbooks/typed actions on the trajectory                            | Adopt typed actions for both commands *and* file edits. The file-edit path is the under-appreciated half of this story.                              |
| Policy engine                 | Capability-based, tokenised, YAML data files, `SAFE` / `CONFIRM` / `BLOCK` + risk score + matched rules | Policy currently implicit in code paths                                                    | Externalise policy data into a readable file the operator can review and grep. The classifier returning *why* matters as much as the verdict.        |
| Sandbox                       | Runner boundary: `noop` (metadata-only default), `local` (process limits), `bubblewrap` (capability-probed), Landlock on roadmap | None today                                                                                  | Sandboxing is a *layer*, not a switch. Land the metadata boundary first; treat real isolation as future work without pretending the early version provides it. |
| Audit log                     | `0o600` JSONL, Ed25519-style hash chain, `audit verify` CLI                                              | Per [`VISION.md`](VISION.md), every privileged action logged                               | A hash chain + a `verify` subcommand is the bar. "We wrote a log file" is not.                                                                       |
| Output handling               | Bounded and redacted before being shown to the model                                                     | Not yet specified                                                                          | Treat command output as untrusted *before* it re-enters the planner. Secrets leak this way.                                                          |
| Memory                        | Local filesystem memory at `~/.linuxagent/memories`, separate read/write switches, never alters policy   | Out of MVP scope                                                                            | If memory ever lands, copy the *invariant* — memory never edits policy, HITL, sandbox, execution, or audit.                                          |
| Extensibility                 | MCP prototype exposing only *read-only* policy/audit tools; Skills are advisory-only manifests           | Out of MVP scope                                                                            | When extensions arrive, default to read-only and advisory. Executable plugin hooks are a hole in the trust model.                                    |
| Multi-host                    | First-class SSH cluster with batch confirmation, `known_hosts` verification, remote metacharacter blocking, remote profile audit | Out of scope — one operator, one machine                                                   | Don't import this. But note the *shape* of "explicit batch confirmation" for any future fleet story.                                                 |
| Quality gates                 | `make test` / `lint` / `type` / `security` / `red-team` / `benchmark` / `sandbox` / `harness`, coverage floor, reproducible build | `make lint`, `make test`, `make package` (see `Makefile:19-49`, `tests/smoke.sh:85-125`)   | Add red-team and policy-benchmark targets as the safety surface grows. The existing make-target shape is the right place to put them.                |
| Distribution                  | Wheel + sdist + PyPI + constraints.txt + packaged data install check                                     | Bash installer + smoke test                                                                | Different vehicles, same instinct: the build verifies what shipped. Keep installer smoke tests honest about what they prove.                         |

The pattern is consistent: LinuxAgent's *safety primitives* generalise
cleanly to Ubuntu Zombie; its *surface* (CLI, multi-host SSH, plugin
matrix) does not, and should not be imitated.

## Capability deep-dives

The rest of this document walks the LinuxAgent feature set in detail
and for each capability gives an honest verdict for Ubuntu Zombie:
**borrow**, **translate**, **defer**, or **refuse**.

### 1. The structured `CommandPlan` boundary

LinuxAgent's most important design decision is that the LLM does not
emit a shell string. It emits a structured `CommandPlan` that must
validate as JSON before any policy or execution path even *sees* it.
That single contract is what makes everything downstream — tokenised
policy, capability matching, audit redaction, sandbox profile
selection, replay — actually possible. A free-form string forces every
later layer to re-parse intent out of bash; a typed plan lets each
layer reason about an object.

**Verdict: borrow, and treat as load-bearing.** This is the same lesson
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) already calls out
from SysKnife and Cline ("typed actions over raw shell strings"), but
LinuxAgent is the clearest worked example of *what the type buys you*
once you commit to it. Ubuntu Zombie should treat the planner's output
schema as a stable contract from the first release, not as something to
retrofit once free-form prompts start causing incidents.

### 2. Capability-based, YAML-driven policy engine

LinuxAgent separates *policy data* (`configs/policy.default.yaml`)
from *policy code*. The code loads, validates, and applies rules; it
does not encode them. The engine tokenises a command, derives the
capabilities it would exercise, scores risk, and returns one of
`SAFE` / `CONFIRM` / `BLOCK` together with the matched rules.

Two properties matter and are easy to under-rate:

1. **Substring matching is not safety.** A blocklist of strings is
   trivially bypassed; the project even has a blog post making this
   argument. The right unit of analysis is a tokenised command and
   the capability set it implies — "this would write to `/etc`",
   "this would open an outbound socket", "this would exec another
   shell" — not a regex over the text.
2. **The classifier returns *why*, not just *what*.** "Matched rule
   `destructive.rm_rf_root`" is auditable in a way that "blocked"
   is not.

**Verdict: borrow.** Externalise Ubuntu Zombie's policy into a YAML
file the operator can read with `cat` and review with `diff`. The
classifier's return shape (`verdict`, `risk`, `capabilities`,
`matched_rules`) is the right shape for both the approval surface
("here is *why* this is being asked") and the audit record ("here is
*what* the policy said at the time, including which rule version
matched").

### 3. The three-way confirmation menu and its scoping rules

LinuxAgent's approval surface is not a yes/no prompt. It's a three-
option menu — `Yes` (one execution), `Yes, don't ask again` (same
argv command shape, current conversation thread, surviving `/resume`
of *that* thread only), `No` — with a small but rigid set of
invariants:

- A non-TTY confirmation request **auto-denies**. The agent never
  proceeds because nobody answered.
- Destructive commands and `never_whitelist` policy matches **ask
  every time**, regardless of any conversation whitelist.
- The whitelist is scoped to the same argv *shape*, not to a free-
  form intent. Renaming a flag breaks the whitelist on purpose.
- New conversations do **not** inherit prior whitelists.

**Verdict: translate.** The TUI menu is the wrong shape for a chat
surface, but every one of the invariants above is correct and should
survive the translation:

- If the operator is not present on the chat surface, the action does
  not run. "No human, no execution" is the rule.
- Ubuntu Zombie's "approve once for this thread" must scope to the
  exact command shape, not to "things like this".
- Destructive classes always re-prompt. The operator can never opt
  out of seeing them.
- A fresh chat thread is a fresh trust context.

The chat-native equivalent of LinuxAgent's TUI menu is a structured
message with the proposed action, the policy verdict, the matched
rules, and three explicit reply tokens. The shape is different; the
guarantees should be identical.

### 4. Direct `!` command mode

`!<command>` runs an operator-authored command without involving the
LLM at all: stream stdout/stderr live, record both input and result
into conversation context, do not ask the model to explain or generate
a reply for that turn. It is the escape hatch that lets the operator
do something the agent will not propose, while still being recorded.

**Verdict: borrow the *idea*, refuse the *syntax*.** Ubuntu Zombie's
operator already has a shell — they have an Ubuntu desktop and a
terminal. The interesting half of `!` is the *recording* property: when
the operator does something on the box themselves, the chat surface
should still capture it into the audit trail, so the history of "what
happened on this machine" is not split between two unconnected logs.
That is the lesson worth keeping. The `!` prefix syntax inside chat is
not.

### 5. Intent routing as an LLM-owned decision

Conversation vs. operation vs. clarification is decided by an LLM-
owned intent router (`prompts/intent_router.md`) that returns one of
`DIRECT_ANSWER`, `COMMAND_PLAN`, or `CLARIFY`. Direct answers do not
create a command plan and therefore do not show the confirmation
panel. The router is not a Python keyword table.

**Verdict: borrow.** Two specific consequences are worth importing:

1. Cheap, read-only questions ("what is using my disk?", "why did
   this fail?") should be cheap and fast, not gated through the
   approval surface. The approval gate exists for *actions*, not for
   *answers*.
2. The router's prompt should live on disk as a readable file the
   operator can edit, not as an embedded string. This matches the
   Butterfish lesson already recorded in
   [`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) — *transparent,
   user-editable prompts and verbose logging instead of hidden
   behaviour*.

### 6. `FilePatchPlan`: the under-appreciated half of the safety story

Most agent projects spend their safety budget on commands. LinuxAgent
spends a meaningful chunk of it on *file edits*, and the design is
worth studying:

- The planner emits a structured `FilePatchPlan`, not a "write this
  string to this path" instruction. The plan carries a structured
  `request_intent` (`create` / `update` / `unknown`) instead of
  guessing from keywords.
- The plan is validated as a unified diff before anything writes.
- Approval is per file, with compact `+`/`-` snippets, high-risk
  path warnings, permission-change call-outs, and large-diff
  pagination.
- Writes go through a temp file and atomic replace. Targets are
  backed up under `.linuxagent-patch-*` and rolled back if any later
  file in the transaction fails.
- Symlink path components, hardlinks, directories, device files,
  FIFOs, sockets, oversized targets, and non-UTF-8 text are
  rejected before reading content.
- Reads and writes are limited to allowed roots (`file_patch.allow_roots`,
  defaulting to the workspace and `/tmp`); `/etc`, SSH key dirs, etc.
  are flagged as high-risk.
- The audit record captures changed files, permission changes,
  backup-path hashes, rollback outcomes, and the sandbox root.

**Verdict: borrow most of this, gated on Ubuntu Zombie's actual file-
edit scope.** Ubuntu Zombie's `zombie` user will eventually need to
edit config under `/etc` — that is part of the promise. The
LinuxAgent invariants are the right ones for that moment:

- Edits are transactional. Either the whole multi-file change applies
  or none of it does, with backups.
- Approval shows the diff, not "approve a write to `/etc/foo`?".
- High-risk roots (`/etc`, `/boot`, `~/.ssh`, anything under
  `/etc/sudoers.d`, anything systemd is going to re-read) are
  explicitly called out in the approval surface and *also* in the
  audit record.
- Symlink-component checks, FIFO/device rejection, and non-UTF-8
  guards belong in the executor regardless of how the planner is
  configured. They cost almost nothing and they close a real class of
  attack.

### 7. Read-only workspace tools and tool-sandbox permissions

The planner can call `read_file(path, offset, limit)`,
`list_dir(path)`, and `search_files(pattern, root)` with literal-text
matching (regex metacharacters treated as ordinary text) to ground
itself before proposing patches. Crucially these are *not* the same
permission as command execution: each tool carries explicit
permissions (`read_files`, `write_files`, `execute_commands`,
`system_inspect`, `network_access`, `hitl`), per-tool timeouts and
output limits, and oversized output is marked as truncated rather
than silently passed through. Telemetry records `allowed`, `denied`,
`timeout`, or `truncated`.

**Verdict: borrow the *permission split*; defer the rest.** Ubuntu
Zombie's executor should distinguish, from day one, between "read"
and "run". Read tools never call into the approval gate; they have
their own bounded scope and they record what they read. Conflating
the two is how an agent ends up needing approval to look at a log
file, which trains the operator to click through.

### 8. Sandbox runners and the honesty of "metadata only"

LinuxAgent ships three runners — `noop` (default, metadata only),
`local` (process lifecycle controls: clean env, closed stdin,
timeout, process-group cleanup, resource limits, output limits, cwd
roots), and `bubblewrap` (capability-probed, fails closed for safe
profiles if `bwrap` is missing or cannot enforce the requested
profile) — with Landlock documented as the next slice. Commands
carry their selected sandbox profile into both the audit log and
telemetry.

The non-obvious property here is **honesty about what each runner
provides**: the README is explicit that the default `noop` is *not*
a sandbox, only a metadata recorder, and that the `local` runner
does not claim filesystem or network isolation. "Safe profile +
sandbox unavailable = fail closed" is the rule.

**Verdict: borrow the honesty, defer the implementation.** Ubuntu
Zombie should not ship a sandbox before it ships a credible one.
It *should* ship the *metadata*: which profile a given command would
have run under, why it ran without one if it did, and the same
"fail closed when a safe profile is requested but unavailable"
default. That metadata is what lets a future Landlock or bwrap
layer drop in without rewriting the audit trail.

### 9. Output redaction and bounded model-facing analysis

Tool output is redacted and bounded before the model sees it. This is
a quiet but important property: an LLM that re-reads `journalctl -u
ssh` is going to encounter material it should not be allowed to
exfiltrate or reason over verbatim, including paths, IPs,
credentials in logs, and operator names.

**Verdict: borrow.** Ubuntu Zombie's executor must redact command
output before it re-enters the planner. The redaction list lives on
disk (auditable), is appended to over time, and the operator can read
it. Bounding output (a hard byte cap, with truncation explicit in
both the model-facing payload and the audit record) is a cheap
defence against an LLM being forced into a long-context attack via a
giant log file.

### 10. Hash-chained audit log + `audit verify`

The audit log is JSONL at `0o600`, hash-chained, and there is a
`linuxagent audit verify` command that re-walks the chain and detects
local tampering. Optionally, entries can be forwarded to an HTTP
sink — but the *source of truth* remains the local append, not the
network destination.

**Verdict: borrow, and inherit the invariants.** This matches the
Missy lesson from [`ALTERNATIVE-MISSY.md`](ALTERNATIVE-MISSY.md) and
the SysKnife lesson in
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md). LinuxAgent's
specific contributions to that pattern are:

- A ship-with-it `verify` command. The verification path must be
  *executable by the operator*, not something only the agent
  understands.
- Optional forwarding is fine, but the local file is canonical.
  Ubuntu Zombie has no central server to forward to and should not
  invent one.
- Permission bits matter. `0o600` is the right default and should
  be enforced at write time, not assumed at install time.

### 11. SSH cluster mode

LinuxAgent has a first-class multi-host story: batch confirmation
across two or more hosts, remote shell-metacharacter blocking,
mandatory `known_hosts` verification, and a remote-profile audit. It
also documents clearly that *SSH execution is not protected by local
OS sandboxing* — the remote host has to be configured with least-
privilege users, pre-registered `known_hosts`, a remote working
directory, and explicit sudo allowlists.

**Verdict: refuse for the MVP, file the shape.** Fleet management is
explicitly out of scope (see
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) §"What 'Ubuntu
LTS + root user + Pi + LLM' specifically implies", point 5: *one
operator, one machine, one trust boundary*). The two pieces worth
remembering for the day someone asks "can I point my zombie at three
machines?":

- Batch operations require batch confirmation, not per-host
  confirmation that the operator will rubber-stamp.
- The local sandbox does not extend over SSH and pretending it does
  is the dangerous version.

### 12. MCP prototype: read-only by default

`linuxagent mcp` starts a stdio MCP server that exposes exactly two
things: a read-only `policy.classify` and `audit.verify`. It
intentionally does **not** expose command execution, file patch
application, SSH fan-out, or secrets.

**Verdict: borrow as a principle.** When Ubuntu Zombie eventually
grows extension points (it will), the default surface should be
read-only. Executable plugin hooks are a hole in the trust model: a
plugin author should not be able to make the executor do anything
the operator-facing approval surface would not have shown. Exposing
"classify this proposed action" and "verify this audit chain" as
read-only tools that *other agents* can call is, by contrast,
strictly useful and strictly safe.

### 13. Local memory that never alters policy

LinuxAgent has a filesystem-memory pipeline (`~/.linuxagent/memories`)
that injects a redacted `memory_summary.md` as advisory context on
chat startup. The invariants are unusually strict:

- Memory never alters policy, HITL, sandbox enforcement, command
  execution, or audit records.
- Read and write are separate switches (`memory.use_memories`,
  `memory.generate_memories`); both can be disabled outright.
- Without a memory-writer provider, generation no-ops rather than
  silently copying chat snippets into long-term storage.
- Stale inputs are pruned; stale pipeline locks recover after a
  configured TTL.
- Each CLI launch starts with empty context; saved sessions only
  load via `/resume`.

**Verdict: out of MVP scope, but the invariant is the lesson.** If
Ubuntu Zombie ever grows a memory of any sort, the rule above is
the right one to copy verbatim: *memory may inform proposals,
but it is never a policy bypass*. That single sentence keeps a
class of "the agent learned to skip approval" failures from being
possible.

### 14. Skills as advisory-only manifests

LinuxAgent has an extension point called Skills — and the deliberate
design choice is that Skills are *manifests*, not executable plugin
hooks. They can give the planner advisory context; they cannot run.

**Verdict: borrow as a default posture.** Ubuntu Zombie's runbook
vocabulary (already called out in
[`ALTERNATIVES-LESSONS.md`](ALTERNATIVES-LESSONS.md) §"Top five
takeaways" point 4) should follow the same instinct: a runbook is a
named, reviewable description of *what should happen*, expanded into
typed actions that go through the same policy + approval + executor
+ audit pipeline as anything else. A runbook is never a license to
skip the gate.

### 15. Quality gate as a make-target gauntlet

The CI surface — `make test`, `make lint`, `make type`, `make
security`, `make red-team`, `make benchmark`, `make sandbox`, `make
harness`, `make verify-build`, coverage floor at 80% — does two
things that are easy to under-rate:

1. **`make red-team` runs an adversarial command corpus in CI.** The
   policy engine is not just unit-tested for "is this rule
   matched"; it is *attacked* in CI with 24 cases covering
   pipelines, subshells, command substitution, redirects, `find
   -exec`, `xargs`, `awk system()`, editor escapes, and interpreter
   inline execution.
2. **`make benchmark` reports P50/P95/P99 policy latency.** The
   policy engine is treated as a hot path with a budget, not as
   "code that runs sometimes".

**Verdict: borrow, scaled to current size.** Ubuntu Zombie already
runs `make lint`, `make test`, and `make package` (see
`Makefile:19-49`, `tests/smoke.sh:85-125`, and `.github/workflows/ci.yml:23-55`).
The slot is there. When the policy engine and approval surface land,
two new targets are the right next additions:

- A `red-team` target that runs an adversarial command corpus
  through the classifier and asserts `BLOCK` / `CONFIRM` verdicts
  for known-bad shapes. The corpus is a checked-in YAML file the
  operator can read.
- A `benchmark` (or equivalent) target that asserts the classifier
  meets a latency budget on the target hardware floor (Pi-class).
  This matters specifically because Ubuntu Zombie targets SBCs.

### 16. Reproducible release

LinuxAgent ships with `constraints.txt`, wheel + sdist + packaged-
data install check, and explicit install paths for source bootstrap,
GitHub Release wheel, PyPI, and dev extras.

**Verdict: translate.** Ubuntu Zombie's release is not a wheel; it is
an installer script and a tagged commit. The instinct still applies:
the smoke test should prove that *what shipped* still installs and
boots, not just that the source tree passes its own tests. Pinning
matters less for a bash installer than for a Python package, but
"the installer's external dependencies are named in a single
auditable place" is the same lesson.

## The honest comparison: where Ubuntu Zombie is *more* exposed

LinuxAgent runs as the invoking user. Ubuntu Zombie creates a
dedicated account with passwordless `sudo`. That escalation is not
free, and three properties have to be *stronger* in Ubuntu Zombie
than they are in LinuxAgent:

1. **The audit log is the only after-the-fact recourse.** LinuxAgent's
   operator can `ps` the agent at any time; Ubuntu Zombie's operator
   has handed the keys to a separate Unix account. The audit chain
   has to be tamper-evident and verifiable by a human with `cat` and
   a `verify` command, not by a service the agent itself runs.
2. **"Non-TTY auto-deny" generalises to "no operator on the chat
   surface, no execution".** LinuxAgent gets this for free because
   the operator is the one who launched the CLI. Ubuntu Zombie has
   to assert it — the chat surface knows whether a human is connected,
   and absent that, nothing runs. The Tailscale-only inbound posture
   helps here, but the executor still has to honour the rule.
3. **`/etc`, `/boot`, sudoers, systemd unit files, SSH keys, and PAM
   config are inside the blast radius.** LinuxAgent rejects many of
   these via path policy and treats them as high risk in the patch
   surface. Ubuntu Zombie *will* legitimately edit some of them — that
   is the point. The cost of that legitimacy is that the policy data
   has to enumerate them explicitly, the approval surface has to call
   them out visually, and the audit log has to record both the
   before-hash and the after-hash of any file under those roots.

## What Ubuntu Zombie should *refuse* from LinuxAgent

Not everything LinuxAgent does is a fit, and pretending otherwise is
how the MVP blows up. The explicit refusals:

- **CLI ergonomics as the operator surface.** LinuxAgent is a
  terminal app; Ubuntu Zombie is a chat surface bound to localhost
  and surfaced over Tailscale. Importing the TUI menu, arrow-key
  resume, slash commands, and `!` direct mode would distort the
  product shape. Translate the *invariants* of the approval flow;
  do not adopt the terminal idioms.
- **Multi-host SSH cluster.** Fleet management is out of scope, and
  importing the cluster code path would force every later safety
  decision to consider remote execution. Stay single-host.
- **Multi-provider matrix on day one.** LinuxAgent's provider
  matrix (OpenAI, DeepSeek, Ollama, Anthropic, arbitrary OpenAI-
  compatible relays) is great. Ubuntu Zombie's MVP is one cloud
  provider with local on the roadmap. The *abstraction boundary*
  (swap the model without touching policy) is worth importing; the
  *count* is not.
- **An in-product memory pipeline.** The right answer in the MVP is
  "no persistent memory beyond the audit log". If it ever lands,
  copy LinuxAgent's invariant about memory never bypassing policy —
  but do not import the pipeline pre-emptively.
- **Skills as an extension surface in the MVP.** Even LinuxAgent's
  Skills are advisory; Ubuntu Zombie should not have an extension
  surface at all in the first release. The runbook vocabulary is
  the right place to start.
- **Distro-portability gestures.** LinuxAgent runs on "any Linux
  with Python 3.11+". Ubuntu Zombie's value comes from being
  honest about its substrate. Encoding "Ubuntu LTS only" is a
  feature.

## Top five LinuxAgent-specific takeaways

If only five lessons survive from this deep read, they should be:

1. **A typed `CommandPlan` and a typed `FilePatchPlan` are the
   contracts that make everything else possible.** Commit to them
   from the first release. The *file edit* half of this is the part
   most projects under-invest in.
2. **Externalise policy as data, return the matched rules.** A YAML
   policy file the operator can read, and a classifier that returns
   `verdict + risk + capabilities + matched_rules`, is the right
   shape for both approval prompts and audit records.
3. **The approval gate has hard invariants, not just defaults.**
   No-operator-no-execution. Destructive always re-prompts. Whitelist
   scopes to argv shape and to the current thread. New threads are
   fresh trust contexts. These are *rules*, not configuration knobs.
4. **A hash-chained audit log is only as useful as the `verify`
   command beside it.** Ship the verifier. The operator must be able
   to check the chain themselves without trusting the agent.
5. **The policy engine is a hot path with a latency budget.** A
   `red-team` adversarial corpus and a P50/P95/P99 benchmark belong
   in CI alongside lint and tests, especially because Ubuntu Zombie
   targets Pi-class hardware where the budget is real.

Everything else — the CLI ergonomics, the cluster mode, the provider
matrix, the Skills surface, the memory pipeline — is shape, not
substance. The substance translates; the shape should not.
