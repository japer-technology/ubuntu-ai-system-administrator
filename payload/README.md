# The payload

This directory is **the product**. Everything outside it
(`scripts/install.sh`, the `Makefile`, the tests, the docs) exists to
*deliver*, *verify*, or *explain* what lives here. The payload is the
set of files that `scripts/install.sh` copies onto a target Ubuntu
Desktop LTS machine to turn it into an Ubuntu AI System Administrator: a private,
loopback-only AI Systems Administrator that can act as `root` through a
classify → propose → approve → run → log gate.

If you want the one-sentence version: **the payload is the running
AI System Administrator; `scripts/install.sh` installs and configures
it.** This document explains the payload part by part.

For the wider trust model and layer diagram, read
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md). For the rules an
agent must follow when changing these files, read
[`../AGENTS.md`](../AGENTS.md).

---

## Where it lands on the target

The installer is the only thing that reads this tree. It copies each
sub-directory to a fixed location, owned by `root` or by the
operator-chosen `AI_SYS_ADMIN_USER` (default `ai-sys-admin`), with explicit modes.
Nothing here is executed from the repository on the target — it is
*deployed* first, then run from its destination.

```mermaid
flowchart TD
    subgraph repo["payload/ (this directory, in the repo)"]
        agent_src["agent/"]
        bin_src["bin/"]
        etc_src["etc/policy.yaml"]
        sys_src["systemd/"]
        log_src["logrotate/"]
    end

    subgraph host["target host (after scripts/install.sh)"]
        opt_agent["/opt/ai-system-administrator/agent/<br/>(root-owned sources +<br/>pi-ai / pi-mono bridges)"]
        opt_bin["/opt/ai-system-administrator/bin/<br/>+ symlinks in /usr/local/bin"]
        opt_skills["/opt/ai-system-administrator/skills/<br/>(built-in catalogue)"]
        opt_pi["/opt/ai-system-administrator/pi/<br/>(rendered settings + system prompt)"]
        etc_dst["/etc/ubuntu-ai-system-administrator/policy.yaml<br/>+ /etc/ubuntu-ai-system-administrator/skills.d/"]
        sys_dst["/etc/systemd/system/<br/>ubuntu-ai-system-administrator-*.{service,timer}"]
        log_dst["/etc/logrotate.d/ubuntu-ai-system-administrator"]
        state["/opt/ai-system-administrator/state/<br/>conversations.db + per-turn logs"]
    end

    agent_src --> opt_agent
    agent_src -->|skills/*.md| opt_skills
    agent_src -->|templates rendered| opt_pi
    bin_src --> opt_bin
    etc_src --> etc_dst
    sys_src --> sys_dst
    log_src --> log_dst
    opt_agent -.->|writes at runtime| state
```

Placeholders such as `__AGENT_USER__`, `__AI_SYS_ADMIN_DIR__`, and
`__AGENT_HOME__` in the `systemd/` and `logrotate/` files are
substituted by the installer so the deployed units name the
operator-chosen account and paths.

| Source                         | Destination                              | Owner / mode (typical) |
|--------------------------------|------------------------------------------|------------------------|
| `agent/*.py`, `agent/*.mjs`    | `/opt/ai-system-administrator/agent/`                  | `AGENT_USER` 644       |
| `agent/templates/*`            | `/opt/ai-system-administrator/agent/templates/` + rendered into `/opt/ai-system-administrator/pi/` | mixed |
| `agent/skills/*.md`            | `/opt/ai-system-administrator/skills/`                 | `root` 644             |
| `bin/*`                        | `/opt/ai-system-administrator/bin/` (+ `/usr/local/bin` symlinks) | `AGENT_USER` 755 |
| `etc/policy.yaml`              | `/etc/ubuntu-ai-system-administrator/policy.yaml`         | `root` 644 (preserved if present) |
| `systemd/*`                    | `/etc/systemd/system/`                   | `root` 644             |
| `logrotate/ubuntu-ai-system-administrator`      | `/etc/logrotate.d/ubuntu-ai-system-administrator`         | `root` 644             |

---

## The runtime, end to end

The heart of the payload is the chat service in
[`agent/server.py`](agent/server.py). It binds **`127.0.0.1` only**,
serves a single-page UI, and drives the `pi-mono` agent loop
(`@earendil-works/pi-coding-agent`) through a Node bridge. The model
never emits free-form shell: every action is a structured **tool call**
against the closed registry in [`agent/tools.py`](agent/tools.py).
Read-only tools run inline; anything that mutates the host is queued
for explicit operator approval and only then dispatched — with the
decision written to the audit log *before* `sudo` is ever invoked.

```mermaid
sequenceDiagram
    actor Operator
    participant UI as Chat UI (index.html)
    participant Server as server.py
    participant Skills as skill_loader.py
    participant Bridge as pi-mono-bridge.mjs
    participant Tools as tools.py
    participant Policy as policy.py
    participant Runner as runner.py
    participant Audit as audit.py
    participant History as history.py

    Operator->>UI: type prompt
    UI->>Server: POST /api/message {prompt}
    Server->>History: add_message(user)
    Server->>Audit: audit("prompt", …)
    Server->>Skills: select_skills(recent messages)
    Skills-->>Server: skill bodies + on-disk paths
    Server->>Bridge: pi_mono.run_turn(prompt, system, history, tools)
    loop one or more tool calls
        Bridge-->>Server: {tool_call, name, args, id}
        Server->>Tools: validate_args(name, args)
        Server->>Policy: classify_tool(name, args)
        alt read_only
            Server->>Tools: dispatch(...)
            Tools->>Runner: run(argv)
            Runner-->>Server: stdout / exit code
        else elevated (user/system/network/destructive)
            Server->>UI: pending_tool_call (await approval)
            Operator->>UI: Approve (+ phrase if destructive)
            Server->>Audit: tool_call decision=approved
            Server->>Tools: dispatch(...) → may sudo
            Server->>Audit: tool_call decision=executed, exit_code
        end
        Server->>History: record tool_call / tool_observation
        Server->>Bridge: {tool_result, id, ok, result|error}
    end
    Bridge-->>Server: {final, text}
    Server-->>UI: assistant message
```

The four invariants that make this safe — and that any change to this
directory must preserve — are:

1. **Loopback only.** The server binds `127.0.0.1`. There is no remote
   API surface.
2. **Closed tool surface.** `TOOL_REGISTRY` in `agent/tools.py` is the
   only set of tools that can ever run. Adding one requires a code
   release; skills, prompts, and `policy.yaml` cannot expand it.
3. **Policy gate + approval.** Every mutating call is classified by
   `agent/policy.py` and must be approved by the operator (destructive
   actions need a confirmation phrase).
4. **Everything is audited.** `agent/audit.py` writes one redacted
   JSON object per line for every prompt, decision, command, and
   result.

---

## `agent/` — the chat service

A small, dependency-light Python service plus two Node bridges. No
third-party Python packages beyond what the installer already provides;
the standard library does the rest.

```mermaid
flowchart TB
    server["server.py<br/>loopback HTTP + UI + turn orchestration"]
    pimono["pi_mono.py<br/>Python client for the pi-mono bridge"]
    providers["providers.py<br/>provider/model resolution (pi-ai)"]
    tools["tools.py<br/>closed tool registry + schema check"]
    policy["policy.py<br/>classify argv → action class"]
    runner["runner.py<br/>subprocess exec + follow-up checks"]
    audit["audit.py<br/>JSONL audit log + secret redaction"]
    history["history.py<br/>SQLite conversations + events"]
    skills["skill_loader.py<br/>trigger-matched Markdown skills"]

    bridge_mono["pi-mono-bridge.mjs<br/>drives `pi --mode json -p`"]
    bridge_ai["pi-ai-bridge.mjs<br/>one-shot completions + model list"]

    server --> pimono --> bridge_mono
    server --> tools --> runner
    server --> policy
    server --> audit
    server --> history
    server --> skills
    providers --> bridge_ai
    pimono --> providers
    tools -.-> policy
```

| File | Responsibility |
|------|----------------|
| [`server.py`](agent/server.py) | Loopback HTTP server, single-page UI, REST endpoints (`/api/message`, `/api/version`, `/api/models`, …), per-turn orchestration, approval queue, refuses to start if `secrets/env` is group/world-readable. |
| [`pi_mono.py`](agent/pi_mono.py) | Python client for the `pi-mono` bridge; speaks a line-delimited JSON protocol over stdio and enforces a per-turn idle watchdog. |
| [`pi-mono-bridge.mjs`](agent/pi-mono-bridge.mjs) | Node bridge that runs the `pi` agent loop one-shot (`pi --mode json -p`) with pi's real built-in tools, parsing `message_update` / `message_end` / `agent_end` events. |
| [`pi-ai-bridge.mjs`](agent/pi-ai-bridge.mjs) | Node bridge over `@earendil-works/pi-ai` for one-shot `complete()` calls and live model listing (e.g. for the `/model` command). |
| [`providers.py`](agent/providers.py) | Single source of truth for provider + model selection, resolved from `AI_SYS_ADMIN_PROVIDER`, `AI_SYS_ADMIN_MODEL`, and the matching `*_API_KEY`. |
| [`tools.py`](agent/tools.py) | The **closed** tool registry, a tiny dependency-free schema validator, and the dispatcher that wraps existing helpers (`runner.run`, `Path.read_text`, …). |
| [`policy.py`](agent/policy.py) | Argv-aware classifier that reads `policy.yaml` live; fail-closed for unknown commands, with a `sudo` allow-list to keep common privileged targets at `system_change`. |
| [`runner.py`](agent/runner.py) | Command execution with timeout and stdout/stderr/exit capture, plus suggested read-only follow-up checks. |
| [`audit.py`](agent/audit.py) | Append-only JSON-lines audit log with secret redaction and SHA-256 digests of tool output. |
| [`history.py`](agent/history.py) | SQLite-backed conversations and structured `tool_call` / `tool_observation` events; forward-only schema via `PRAGMA user_version`. |
| [`skill_loader.py`](agent/skill_loader.py) | Selects trigger-matched Markdown skills and records their on-disk provenance; never expands the tool surface. |
| [`templates/`](agent/templates) | The chat UI (`index.html`) plus `settings.json.tmpl` and `APPEND_SYSTEM.md.tmpl`, rendered by the installer into `/opt/ai-system-administrator/pi/`. |
| [`skills/`](agent/skills) | Built-in skill catalogue (`apt`, `systemd`) — Markdown nudges toward the correct typed tool. |
| `pi-ai.version`, `pi-mono.version`, `bridge-dependencies.lock` | Known-good bridge versions and checksums for release validation; installs resolve npm `latest` and write the resolved versions to the deployed files. |
| [`examples.md`](agent/examples.md) | Example operator prompts surfaced in the UI. |

### Action classes

`policy.py` sorts every command into one of five ordered classes. Only
`read_only` runs without an approval prompt.

```mermaid
flowchart TD
    A["read_only<br/>(auto-run)"] --> B["user_change"]
    B --> C["system_change"]
    C --> D["network_change"]
    D --> E["destructive<br/>(needs confirmation phrase)"]
```

---

## `bin/` — operator helpers

Bash helpers a human operator runs directly (several are symlinked onto
`PATH` by the installer). They follow the repository's best-effort
convention: under `set -euo pipefail`, every external command in a
diagnostic helper is guarded so one failure does not abort collection.

| Helper | Purpose |
|--------|---------|
| [`chat`](bin/chat) | Print the loopback chat URL and every debugging entry point — the single command to discover the diagnostic surface. |
| [`health-check`](bin/health-check) | One-shot health summary (also run periodically by the health timer). |
| [`audit-recent`](bin/audit-recent) | Pretty-print recent audit-log entries (`-n`, `--all`, `-t TYPE`, `--follow`). |
| [`collect-diagnostics`](bin/collect-diagnostics) | Bundle logs and state into a tarball for bug reports, redacting secrets first. |
| [`secrets-edit`](bin/secrets-edit) | Safely edit `/opt/ai-system-administrator/secrets/env`, re-asserting `0600` and ownership on exit. |
| [`setup-agent-venv`](bin/setup-agent-venv) | Provision the unprivileged agent Python venv and operator toolkit (run as the agent user, idempotent). |
| [`verify-release`](bin/verify-release) | Verify a downloaded release: `SHA256SUMS`, cosign signatures, and SLSA provenance. |

> ⚠️ **Do not run the mutating helpers** (`secrets-edit`,
> `setup-agent-venv`) or the installer outside a disposable Ubuntu
> Desktop LTS VM. They change real system state.

---

## `etc/policy.yaml` — the gate's configuration

The default policy file. It defines the `destructive_confirmation`
phrase, the fail-closed `default_class`, and the `sudo_allow_list` of
curated privileged targets that stay at `system_change` instead of
being escalated. It is read **live** on every classification, so an
operator can edit it without restarting the chat service. The installer
*preserves* an existing `/etc/ubuntu-ai-system-administrator/policy.yaml` rather than
overwriting it.

To add a new policy class, follow the recipe in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md): list it here, handle it in
`agent/policy.py`, and document it in
[`../docs/ARCHITECTURE.md`](../docs/ARCHITECTURE.md).

---

## `systemd/` — the units

| Unit | Role |
|------|------|
| `ubuntu-ai-system-administrator-chat.service` | Runs `server.py` as `AGENT_USER` on `127.0.0.1:57878`. **Sandboxing is deliberately off** (`ProtectSystem=false`, no `NoNewPrivileges`): the agent is a full Systems Administrator that elevates via passwordless `sudo`, so a private mount namespace or `NoNewPrivileges` would break approved work. The policy gate — not a systemd sandbox — is the security boundary. |
| `ubuntu-ai-system-administrator-health.service` | Oneshot wrapper around `bin/health-check`. |
| `ubuntu-ai-system-administrator-health.timer` | Runs the health check every 15 minutes. |

---

## `logrotate/ubuntu-ai-system-administrator` — log hygiene

Rotation rules for the audit log, the install log, and the per-turn
`pi-mono` logs under `/opt/ai-system-administrator/state/logs/`. The `__AGENT_USER__`
placeholder is substituted at install time so rotated files are
re-created with the operator-chosen owner.

---

## Extending the payload

Three extension points have fixed recipes in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md); follow them literally
because they encode runtime invariants:

- **New LLM provider** → implement `BaseProvider` in
  `agent/providers.py`, register it in `provider_from_env()`, document
  its env vars, and add an import smoke test.
- **New policy class** → `etc/policy.yaml` + `agent/policy.py` +
  `docs/ARCHITECTURE.md`.
- **New installer subcommand** → `scripts/install.sh` + `README.md`
  Subcommands block + the `subcommands` case in `tests/smoke.sh`.

Always run `make lint` and `make test` after changing anything here;
both are the same checks CI runs. Never add a new runtime dependency
outside the set the installer already installs, never let a new code
path reach `sudo` without a matching policy class and audit entry, and
never commit secrets.
