# Requirements for full pi-mono agent functionality

> **Status:** research note. This is a deep, implementation-grounded
> inventory of *everything the payload needs* for the **pi-mono AI
> agent loop to be fully operational** — not just to install, but to
> think, propose tool calls, get them approved, execute them, automate
> the desktop, and leave an audit trail. It complements the operator
> reference in [`docs/REQUIRES.md`](../REQUIRES.md): `REQUIRES.md`
> lists *what the installer pulls onto the machine*; this file explains
> *which of those things each part of the running agent actually
> depends on, and why*. Where the two disagree, trust the code and the
> citations here.

---

## 1. What "full pi-mono functionality" means

Ubuntu Zombie runs a resident AI Systems Administrator. The agent
brain is the Node CLI **`pi`** from
[`@earendil-works/pi-coding-agent`](https://www.npmjs.com/package/@earendil-works/pi-coding-agent)
("pi-mono"), driven by a Python chat service. A turn flows like this:

```mermaid
flowchart TD
    browser["browser (loopback)"] -->|"HTTP<br/>POST /api/message {prompt, conversation_id}"| server["server.py (chat service)"]
    server -->|"renders system prompt + skills"| turn["pi_mono.run_turn()"]
    turn -->|"spawns: node pi-mono-bridge.mjs"| bridge["pi-mono-bridge.mjs"]
    bridge -->|"spawns: pi --mode json --no-builtin-tools …"| pi["pi (the model loop)"]
    pi -->|"HTTPS"| provider["LLM provider"]
    pi -->|"emits tool_call events"| tools["tools.py (closed registry)"]
    tools -->|"classify → policy gate → (approve) → runner.run()"| exec["bash / sudo / apt / systemctl / docker / xdotool …"]
    exec -->|"reply + events + audit"| browser
```

For this whole chain to work end-to-end ("full functionality"), the
payload needs **eight layers** to all be present and correctly wired:

1. A supported **OS + desktop** (§3).
2. **Operator-supplied secrets** — at minimum one LLM key (§4).
3. **System (apt) packages** that back the tools (§5).
4. The **Node runtime + the two pinned npm packages** (`pi-ai`,
   `pi-coding-agent`) (§6).
5. **Python** — the stdlib chat service *plus* the agent venv for
   desktop automation (§7).
6. The **filesystem layout, ownership, and systemd units** (§8, §9).
7. The **configuration + secret files** the service reads at runtime
   (§10) and the full **environment-variable contract** (§11).
8. The **policy gate, skills, audit log, and history store** that make
   the loop safe and stateful (§12–§15).

Sections §16–§17 then map every tool to its concrete dependency and
distinguish a *minimal* loop from *full* functionality.

---

## 2. The runtime components (where the requirements come from)

| Component | File | Role |
| --------- | ---- | ---- |
| Chat service | `payload/agent/server.py` | Loopback HTTP server; renders prompt, mediates every tool call, gates approvals, writes audit + history. |
| pi-mono client | `payload/agent/pi_mono.py` | Spawns the Node bridge; speaks line-delimited JSON; returns `{final, events}`. |
| pi-mono bridge | `payload/agent/pi-mono-bridge.mjs` | Wraps the `pi` CLI (`--mode json`), translates its tool-call stream. |
| Tool registry | `payload/agent/tools.py` | The **closed** set of 13 tools the agent may ever call. |
| Policy gate | `payload/agent/policy.py` + `payload/etc/policy.yaml` | Classifies each command/tool and decides auto/approval/confirm-phrase. |
| Provider adapter | `payload/agent/providers.py` + `payload/agent/pi-ai-bridge.mjs` | One-shot LLM completions via `@earendil-works/pi-ai` (status banner, non-agent calls). |
| Runner | `payload/agent/runner.py` | Executes approved commands through `bash -c`, caps output, proposes follow-ups. |
| Skills | `payload/agent/skill_loader.py` + `payload/agent/skills/*.md` | Trigger-matched guidance injected into the system prompt. |
| Audit | `payload/agent/audit.py` | Redacted JSON-lines forensic log. |
| History | `payload/agent/history.py` | SQLite conversation + event store. |

---

## 3. Operating system and desktop

- **Ubuntu Desktop LTS**, x86-64 or arm64 — **22.04 (jammy)** or
  **24.04 (noble)**. Other releases are rejected by the apt-repo
  codename probes in `scripts/install.sh`. (See
  [`docs/PLATFORMS.md`](../PLATFORMS.md).)
- **Root access** (installer runs under `sudo`).
- A **real Xorg desktop session** logged in as the agent account is
  required for the `gui.*` tools to succeed. The screenshot/click/type
  helpers target `DISPLAY=:0` via `/opt/ai-zombie/bin/gui-env`
  (`tools.py:250-276`). Without an active session the GUI tools fail
  even though every other tool works (`verify` reports this explicitly,
  `scripts/install.sh:2262`).
- **Outbound HTTPS** to the configured LLM provider (always) and to the
  apt/PyPI/npm registries (install/upgrade only).

---

## 4. Operator-supplied inputs (not installed — you bring them)

| Input | Required for | How supplied |
| ----- | ------------ | ------------ |
| **One LLM provider key** | **The agent to think at all.** Pick exactly one of `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `XAI_API_KEY`, `OPENROUTER_API_KEY`, `MISTRAL_API_KEY`, `GROQ_API_KEY`. | Added *after* install via `sudo /opt/ai-zombie/bin/secrets-edit`, stored in `/opt/ai-zombie/secrets/env`. |
| **SSH public key** | Remote access to the `zombie` account (key-only SSH). | Interactive prompt or `SSH_PUBLIC_KEY=…`. |
| **VNC password** | Loopback-only `x11vnc` emergency desktop. | Interactive prompt or `VNC_PASSWORD=…`. |
| **Tailscale account / auth key** | *Only if* you opt in with `ZOMBIE_SKIP_TAILSCALE=0`. | `TAILSCALE_AUTHKEY=…`. |

Without a provider key the chat service starts but every turn fails:
the provider is auto-detected from the first key present, else
`NoProviderConfigured` is raised (`providers.py:277-307`). **The LLM
key is the single hard prerequisite for any agent functionality.**

For **OpenRouter** there is **no default model**, so `ZOMBIE_MODEL`
must also be set; all other providers fall back to a built-in default
(see §11 table and `providers.py:84-100`).

---

## 5. System (apt) packages — grouped by why pi-mono needs them

The installer provisions a broad toolbox; this section ties packages to
the actual agent code paths. (The full installed list lives in
`scripts/install.sh` "Base packages" / "Desktop…" sections and in
[`docs/REQUIRES.md` §4](../REQUIRES.md).)

### 5.1 Required for the core loop and tool shims
- `python3`, `python3-venv`, `python3-pip` — the chat service and the
  agent venv (`server.py`, `setup-agent-venv`).
- `sudo` — every elevated tool runs via `sudo …`; passwordless sudo for
  the agent account is the privilege boundary (`tools.py:211,232`;
  `policy.yaml`).
- `ca-certificates`, `curl`/`wget`, `gnupg`, `apt-transport-https` —
  TLS trust + repo/key plumbing for both install and the provider
  HTTPS calls.
- `iproute2` (ships with Ubuntu) — `net.status` uses `ip -brief addr`
  (`tools.py:243`). **Note:** `net-tools`/`dnsutils`/`iputils-ping` are
  installed but the typed `net.status` tool does *not* use them; they
  are only available to the model through `shell.run`.

### 5.2 Backing the typed mutation tools
- `apt`/`dpkg`/`apt-cache` — `pkg.query`, `pkg.install`
  (`tools.py:196-214`).
- `systemd` (`systemctl`) — `svc.status`, `svc.control`
  (`tools.py:217-233`).
- `ufw`, plus `tailscale` when enabled — `net.status` targets
  (`tools.py:236-247`).

### 5.3 Required for the `gui.*` tools (desktop automation)
- `ubuntu-desktop-minimal`, `gdm3`, `xorg` — the desktop session.
- `x11vnc` — emergency loopback desktop.
- `xdotool` — `gui.click`, `gui.type` (`tools.py:259-276`).
- `gnome-screenshot` — `gui.screenshot` (the `screenshot` helper calls
  it; `scrot`/`imagemagick` are installed but unused by the helper).
- `dbus-x11` — `gui-env` exports a session bus for the above.

### 5.4 Used by the operator helper scripts (not the agent loop)
- `jq` — pretty-prints the audit log in `audit-recent`.
- `tree` — `collect-diagnostics`.
- `psmisc` (`fuser`) — port checks in helpers.
- `tmux` — `agent-shell` convenience session.
- `pwgen` — VNC password generation at install.

### 5.5 Capability packages — provisioned *for the agent to use*, not loop-critical
- **Docker** (`docker-ce`, `docker-ce-cli`, `containerd.io`,
  buildx/compose) — the agent can drive Docker via `shell.run` (see the
  `docker` skill, §13), but no payload code imports it.
- Convenience CLIs (`ripgrep`, `fd-find`, `git`, `vim`, `nano`,
  `htop`, `rsync`, `zip`/`unzip`) — available through `shell.run`.
- `build-essential` — only needed if a Python wheel must compile.

> **Practical implication:** the *minimum* apt set for a non-GUI agent
> loop is §5.1 + §5.2. The desktop stack (§5.3) is required only for
> "computer use". §5.4–§5.5 are operator/agent conveniences. See the
> matrix in §16.

---

## 6. Node runtime and the two pinned npm packages

The agent brain is Node, not Python. Full functionality requires:

- **Node.js 22.x** from the **NodeSource** apt repo
  (`/etc/apt/sources.list.d/nodesource.sources`, pinned via
  `/etc/apt/preferences.d/nodejs`). Ubuntu's archive Node 18 is too old
  for `npm@latest` (needs `^20.17.0 || >=22.9.0`).
- **`npm@latest`**, then global installs of:
  - **`@earendil-works/pi-coding-agent`** — provides the `pi` binary
    that *is* the agent loop. Version pinned by
    `payload/agent/pi-mono.version` (currently `0.80.10`). Installed
    with `--ignore-scripts`.
  - **`@earendil-works/pi-ai`** — the provider library used by the
    one-shot completion path / status banner. Pinned by
    `payload/agent/pi-ai.version` (currently `0.80.10`). Installed with
    `--ignore-scripts`.
  - `yarn`, `pnpm`, `typescript`, `ts-node` — installed globally but
    **not referenced by any payload code**; they exist as an agent
    toolbox only.

The two bridges that glue Python to these packages are shipped (not
installed via npm) at `/opt/ai-zombie/agent/pi-mono-bridge.mjs` and
`/opt/ai-zombie/agent/pi-ai-bridge.mjs`.

**How `pi` is launched** (`pi-mono-bridge.mjs`):

```
pi --mode json -p "<prompt>" --no-builtin-tools \
   [--tools "shell.run,fs.read,…"] \
   [--append-system-prompt "<text>"]
```

- `--no-builtin-tools` + `--tools` enforce the **closed registry** —
  `pi` may only emit calls for the 13 names in `settings.json.tmpl`.
- The binary name is overridable with `ZOMBIE_PI_MONO_BIN` (default
  `pi`); the Node binary with `ZOMBIE_NODE` / discovered via
  `shutil.which("node")` (`pi_mono.py:64-72`).

---

## 7. Python: the chat service vs. the agent venv

There are **two** Python contexts, and full functionality needs both:

### 7.1 The chat service (Python stdlib only)
`server.py`, `tools.py`, `policy.py`, `audit.py`, `history.py`,
`runner.py`, `providers.py`, `pi_mono.py`, `skill_loader.py` are
**dependency-free** — they import only the standard library. `tools.py`
deliberately avoids `jsonschema`/`pydantic` (`tools.py:17`). This is
why the chat loop itself does **not** need the venv *libraries*.

It is, however, **launched by the venv's Python interpreter** — the
systemd unit's `ExecStart` points at
`__AGENT_HOME__/agent-env/bin/python` (§9). So the venv must *exist* for
the service to start, but the service uses only the standard library
from it; the third-party packages in §7.2 are for desktop/computer-use
helpers, not the chat loop. (Any CPython ≥ 3.10 interpreter would do;
the venv is simply the interpreter the unit is configured to use.)

### 7.2 The agent venv (`~<agent>/agent-env`) — for desktop/computer-use
Created by `payload/bin/setup-agent-venv` as the agent user, with
pinned-latest:
`pip`/`wheel`/`setuptools`, `requests`, `pydantic`, `rich`, `typer`,
`python-dotenv`, `playwright` (+ `python -m playwright install
chromium`), `pyautogui`, `pillow`, `mss`, `opencv-python`,
`python-xlib`. The matching **Chromium system libraries** are installed
as root via `playwright install-deps chromium`.

> These venv libraries are **not imported by the chat loop**; they back
> browser/computer-use helpers (e.g. the Playwright smoke at
> `/opt/ai-zombie/tools/browser-test.py`) that the agent invokes
> through `shell.run`. For full "drive a browser / automate the GUI"
> functionality they are required; for a headless command agent they
> are not.

---

## 8. Filesystem layout, ownership, and permissions

Created/asserted by `scripts/install.sh`. `ZOMBIE_DIR` defaults to
`/opt/ai-zombie`; the agent account defaults to `zombie`
(`ZOMBIE_USER`).

| Path | Mode / owner | Purpose |
| ---- | ------------ | ------- |
| `/opt/ai-zombie/agent/` | 755 agent | Python chat-service sources + bridges + `*.version`. |
| `/opt/ai-zombie/bin/` | 755 agent | `verify`, `health-check`, `audit-recent`, `secrets-edit`, `collect-diagnostics`, `setup-agent-venv`, `zombie-chat`, and the inline GUI helpers `gui-env`, `screenshot`, `click`, `type-text`, `key`, `agent-shell`. |
| `/opt/ai-zombie/pi/` | 755 **root** | Rendered runtime config: `settings.json`, `APPEND_SYSTEM.md` (world-readable, root-owned so the agent can't rewrite its own policy surface). |
| `/opt/ai-zombie/skills/` | 755 root, files 644 | Built-in skill catalogue. |
| `/opt/ai-zombie/secrets/` | **700** agent | Holds `env` (mode **600**) — the only secret store. |
| `/opt/ai-zombie/state/` | 755 agent | Runtime state. |
| `/opt/ai-zombie/state/logs/` | 750 agent | pi-mono per-turn logs. |
| `/opt/ai-zombie/state/pi-mono-sessions/` | 750 agent | pi session dir (`settings.json: sessionDir`). |
| `/opt/ai-zombie/state/conversations.db` | agent | SQLite history (`ZOMBIE_HISTORY_DB`). |
| `/etc/ubuntu-zombie/policy.yaml` | 644 root | Operator-editable policy (hot-reloaded). |
| `/etc/ubuntu-zombie/skills.d/` | 755 root | Operator skill drop-ins (take precedence). |
| `/var/log/ubuntu-zombie/audit.log` | **640** agent | Redacted forensic audit trail. |
| `~<agent>/agent-env/` | agent | The Python venv (§7.2). |

---

## 9. systemd units

| Unit | Key directives |
| ---- | -------------- |
| `ubuntu-zombie-chat.service` | `User=/Group=__AGENT_USER__`; `WorkingDirectory=/opt/ai-zombie`; `EnvironmentFile=-/opt/ai-zombie/secrets/env`; `Environment=ZOMBIE_CHAT_PORT=7878` (fallback); `ExecStart=__AGENT_HOME__/agent-env/bin/python /opt/ai-zombie/agent/server.py --host 127.0.0.1 --port ${ZOMBIE_CHAT_PORT}`; `After/Wants=network-online.target`; `Restart=on-failure`. |
| `ubuntu-zombie-health.service` + `.timer` | Periodic `health-check`; timer `OnBootSec=5min`, `OnUnitActiveSec=15min`, `Persistent=true`. |

Hardening on the chat service: `PrivateTmp=true`,
`ProtectKernelTunables/Modules/ControlGroups=true`,
`RestrictRealtime=true`, `RestrictSUIDSGID=true`, `LockPersonality=true`.
`ProtectSystem` is deliberately **disabled** (`false`): a read-only
`/usr`/`/etc` mount would block the agent's approved package installs and
config edits (see the `NoNewPrivileges` note below — `sudo` inherits the
unit's mount namespace).

**Critical, intentional exception:** `NoNewPrivileges` is **absent**.
The agent elevates through passwordless `sudo` (a setuid binary) once
the policy gate approves; `NoNewPrivileges=true` would block every
elevation. **The policy gate is the *primary* security boundary**, with
the systemd hardening above (and an optional AppArmor profile) providing
**defense-in-depth** rather than the main control. `/var/log` is left
writable so the service can keep appending the audit log.

> The service is started by the **agent venv's** Python interpreter
> (`ExecStart=…/agent-env/bin/python …`). The venv must therefore exist
> for the core path to run, but — as noted in §7.1 — the chat loop uses
> only the standard library from it; the venv's third-party packages are
> for desktop/computer-use, not the loop.

---

## 10. Runtime configuration and secret files

| File | Read by | Contents / contract |
| ---- | ------- | ------------------- |
| `/opt/ai-zombie/secrets/env` | chat service (`EnvironmentFile`) + `gui-env` | One provider key (`*_API_KEY`); optional `ZOMBIE_PROVIDER`, `ZOMBIE_MODEL`, `ZOMBIE_CHAT_PORT`; plus `DISPLAY=:0`, `ZOMBIE_DIR`, `AGENT_USER`, `AGENT_HOME`. Mode 600, agent-owned. Edited only via `secrets-edit` (backs up, re-asserts perms). |
| `/opt/ai-zombie/pi/settings.json` | `pi_mono.py` → bridge → `pi` | `mode: "rpc"`, `noBuiltinTools: true`, the 13-name `tools` list, `sessionDir`, `appendSystemPromptFile`. Rendered from `templates/settings.json.tmpl` every install/repair. |
| `/opt/ai-zombie/pi/APPEND_SYSTEM.md` | injected into the system prompt | Rendered from `templates/APPEND_SYSTEM.md.tmpl`; substitutes `__AGENT_USER__` and auto-collected `__FACTS__`. Tells the model it has passwordless sudo, a closed tool registry, and a policy gate it cannot bypass. |
| `/etc/ubuntu-zombie/policy.yaml` | `policy.py` (hot-reloaded by mtime) | Action classes, ordered regex rules, `sudo_allow_list`, `tool_classes` overrides, per-turn budgets. |
| `/etc/ubuntu-zombie/APPEND_SYSTEM.md` (optional) | operator override | Survives re-render if referenced from an operator `settings.json`. |

---

## 11. Environment-variable contract (complete)

| Variable | Default | Consumed by | Effect |
| -------- | ------- | ----------- | ------ |
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` / `GEMINI_API_KEY` / `XAI_API_KEY` / `OPENROUTER_API_KEY` / `MISTRAL_API_KEY` / `GROQ_API_KEY` | — | `providers.py`, `pi-ai-bridge.mjs`, `pi` | Provider credential. Exactly one needed. |
| `ZOMBIE_PROVIDER` | auto-detect | `providers.py:261` | Force provider when several keys are present. |
| `ZOMBIE_MODEL` | per-provider default | `providers.py:236` | Override model. **Required** for OpenRouter (no default). |
| `ZOMBIE_OPENAI_MODEL` … `ZOMBIE_OPENROUTER_MODEL` | provider default | `providers.py:84-100` | Per-provider model override. |
| `ZOMBIE_SECRETS` | `/opt/ai-zombie/secrets/env` | `server.py:52`, `audit.py` | Secrets path (also redacted in audit). |
| `ZOMBIE_CHAT_PORT` | `7878` | `server.py`, unit | Loopback port. |
| `ZOMBIE_DIR` | `/opt/ai-zombie` | many | Install root / state dir. |
| `ZOMBIE_USER` | `zombie` | `server.py:59`, unit | Agent account name. |
| `ZOMBIE_POLICY` | `/etc/ubuntu-zombie/policy.yaml` | `policy.py:27` | Policy file path. |
| `ZOMBIE_AUDIT_LOG` | `/var/log/ubuntu-zombie/audit.log` | `audit.py:44` | Audit log path. |
| `ZOMBIE_AUDIT_VERBOSE` | off | `audit.py`, `audit-recent` | Include redacted stdout/stderr previews. |
| `ZOMBIE_AUDIT_PREVIEW_BYTES` | `2048` | `audit.py:63` | Preview cap. |
| `ZOMBIE_HISTORY_DB` | `/opt/ai-zombie/state/conversations.db` | `history.py:20` | SQLite store. |
| `ZOMBIE_COMMAND_TIMEOUT` | `300` | `runner.py:11` | Per-command timeout (seconds). |
| `ZOMBIE_SKILLS_DIR` | unset | `tools.py:288`, `skill_loader.py` | Extra skill dir (non-empty only). |
| `ZOMBIE_PI_MONO_BIN` | `pi` | `pi-mono-bridge.mjs:108` | pi binary path. |
| `ZOMBIE_NODE` | discovered | `providers.py:133`, `pi_mono.py` | Node binary path. |
| `ZOMBIE_PI_MONO_BRIDGE` | shipped `.mjs` | `pi_mono.py:57` | Override bridge (used by smoke test stub). |
| `ZOMBIE_PI_MONO_SETTINGS` | `/opt/ai-zombie/pi/settings.json` | `pi_mono.py:47` | Settings path. |
| `ZOMBIE_PI_MONO_LOG_DIR` | `/opt/ai-zombie/state/logs` | `pi_mono.py:45` | Per-turn pi logs. |
| `ZOMBIE_PI_AI_BRIDGE` | shipped `.mjs` | `providers.py:126` | Override pi-ai bridge. |
| `DISPLAY` | `:0` | `gui-env`, GUI tools | X display for desktop automation. |

Install-time only (not runtime agent behaviour): `ZOMBIE_NONINTERACTIVE`,
`ZOMBIE_ENABLE_AUTOLOGIN`, `ZOMBIE_SKIP_TAILSCALE`, `ZOMBIE_ASSUME_YES`,
`ZOMBIE_STRICT`, `ZOMBIE_VERBOSE`, `ZOMBIE_QUIET`, `ZOMBIE_COLOR`,
`ZOMBIE_JSON` (see `scripts/install.sh` and
[`docs/CONFIGURATION.md`](../CONFIGURATION.md)).

---

## 12. The policy gate (what makes execution safe)

Every proposed command/tool is classified before it can run
(`policy.py`, `policy.yaml`):

- **Action classes** (increasing friction): `read_only` → `user_change`
  → `system_change` → `network_change` → `destructive`.
- **Approval:** `read_only` auto-runs; everything else needs operator
  approval; `destructive` additionally needs the exact
  **confirmation phrase** (`"yes, I understand this is destructive"`).
- **Classification:** ordered regex `rules` matched per pipeline segment
  (env-prefix and `sudo`-flag stripped), with a `sudo_allow_list` that
  keeps curated privileged programs at `system_change` instead of the
  fail-closed `default_class: destructive`. **Highest matched class
  wins.**
- **Closed registry:** `shell.run` is reclassified per-argv; the other
  12 tools use registry defaults overridable via `tool_classes`.
  Because the gate runs on *every* tool call independently, chaining
  `shell.run` cannot bypass it.
- **Budgets:** `max_tool_calls_per_turn` (12) and
  `max_elevated_calls_per_turn` (3) bound runaway loops; overflow yields
  a synthetic `budget_exceeded` observation.

The 13 tools and their default classes (`tools.py`): `shell.run`
(per-argv), `fs.read` (read_only), `fs.write` (user_change), `pkg.query`
(read_only), `pkg.install` (system_change), `svc.status` (read_only),
`svc.control` (system_change), `net.status` (read_only),
`gui.screenshot` (read_only), `gui.click`/`gui.type` (user_change),
`skill.list`/`skill.load` (read_only). Filesystem tools are bounded to
allow-lists: reads under `state`,`/etc`,`/var/log`,`/proc`,`/sys`,
`/usr/share/doc`; writes under `state` and `/tmp` (`tools.py:111-123`).

---

## 13. Skills (capability guidance the agent loads on demand)

Trigger-matched markdown injected into the system prompt by
`skill_loader.py`, exposed to the model via `skill.list`/`skill.load`.
Each teaches safe use of an external subsystem — and therefore implies
the matching package must be present for the advice to be actionable:

| Skill | Triggers | Implies |
| ----- | -------- | ------- |
| `apt.md` | apt, dpkg, package, install… | apt/dpkg (always present). |
| `systemd.md` | systemctl, service, journal… | systemd (always present). |
| `ufw.md` | ufw, firewall, iptables, port… | `ufw`. |
| `tailscale.md` | tailscale, tailnet, magicdns… | `tailscale` (only if opted in). |
| `docker.md` | docker, container, compose, image… | Docker stack (§5.5). |
| `gui.md` | screenshot, click, type, x11, xdotool… | Desktop stack + `xdotool` + `gnome-screenshot` (§5.3). |

Operator drop-ins in `/etc/ubuntu-zombie/skills.d/` override shipped
skills and load without a restart.

---

## 14. Audit trail

`audit.py` appends redacted JSON-lines to
`/var/log/ubuntu-zombie/audit.log` for prompts, proposals, approvals,
executions, tool calls, and provider errors. Redaction is recursive and
covers `sk-…`/`sk-ant-…`/`tskey-…` tokens, SSH keys, PEM private-key
blocks, `*_API_KEY`/`TAILSCALE_AUTHKEY`/`VNC_PASSWORD` assignments, and
the secrets path itself. `tool_call` entries carry classification,
decision, exit code, duration, and SHA-256 digests; stdout/stderr
previews appear only under `ZOMBIE_AUDIT_VERBOSE=1`. Inspect with
`audit-recent` (pretty via `jq`, falling back to `grep`). The service
**must** retain write access to `/var/log/ubuntu-zombie/`. The unit
leaves `ProtectSystem` **disabled** (`false`) so approved elevations can
also write `/usr` (package installs) and `/etc` (configuration); a
read-only system mount would break the agent's core job, since `sudo`
cannot escape the unit's mount namespace.

---

## 15. Conversation history

`history.py` persists conversations and per-message events to the
SQLite DB at `/opt/ai-zombie/state/conversations.db` (`ZOMBIE_HISTORY_DB`),
making `conversation_id` continuity in `POST /api/message` possible and
keeping timestamped backups (`*.db.bak.<ts>`). Requires only the Python
stdlib `sqlite3`.

---

## 16. Minimal loop vs. full functionality (dependency matrix)

| Capability | Hard requirements |
| ---------- | ----------------- |
| **Agent thinks + replies** (no tools) | OS, the venv's Python interpreter (stdlib only — see §7.1), Node 22 + `pi-coding-agent` + `pi-ai`, the bridges, `settings.json`, **one LLM key**, chat service running on `127.0.0.1:7878`. |
| **Diagnostics** (`read_only` tools) | + base tools: `ip` (iproute2), `systemctl`, `dpkg`/`apt-cache`, `ufw status`. Auto-runs, no approval. |
| **System administration** (`*_change`) | + `sudo`, `apt-get`, `systemctl`, and the policy gate + operator approval. |
| **Networking changes** | + `ufw` (+ `tailscale` if opted in). |
| **Container ops** | + Docker stack (§5.5). |
| **Desktop / computer-use** (`gui.*`) | + full desktop stack (`ubuntu-desktop-minimal`, `gdm3`, `xorg`, `xdotool`, `gnome-screenshot`, `dbus-x11`) **and a live Xorg login as the agent** + the agent venv/Playwright/Chromium for browser automation. |
| **Safe + auditable operation** | + `policy.yaml`, `/var/log/ubuntu-zombie/audit.log` writable, `conversations.db`, skills catalogue. |

"**Full** pi-mono functionality" = **all** rows above, i.e. the agent
can think, diagnose, change the system and network, drive containers,
automate the desktop/browser, and do so under the policy gate with a
complete audit trail.

---

## 17. Verifying the requirements are met

- `make lint`, `make test`, `make package` — repo-level validation.
- `tests/smoke.sh` — exercises the bridge protocol with the stub at
  `tests/fixtures/stub-pi-mono.mjs` (no real LLM key needed).
- On a live host: `/opt/ai-zombie/bin/verify` (checks Node/pi pinning,
  service active, secrets perms, desktop screenshot), `health-check`
  (periodic, every 15 min via the timer), and `collect-diagnostics`
  for bug reports.

---

## 18. Notes and caveats

- This file is a **research note** and may drift from the code. If you
  change a dependency, env var, path, package, or the tool registry,
  update the relevant section *and* the operator-facing
  [`docs/REQUIRES.md`](../REQUIRES.md) in the same commit.
- "Installed" ≠ "required by the loop." Several installed packages
  (Docker, `yarn`/`pnpm`/`typescript`/`ts-node`, `scrot`/`imagemagick`,
  `net-tools`/`dnsutils`, and the convenience CLIs) are an **agent
  toolbox** reachable only through `shell.run`, not dependencies of the
  pi-mono loop itself. Treat §16 as the source of truth for what "full
  functionality" actually needs.
