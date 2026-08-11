# Configuration

Everything an operator can tune after a successful install.

## Provider keys

Provider credentials live in `/opt/ai-zombie/secrets/env`, mode `0600`,
owned by the local agent account (default `zombie:zombie`; whatever
name was passed to `ZOMBIE_USER` at install time). Edit them with the
safe helper, which re-asserts permissions after `$EDITOR` exits:

```bash
sudo /opt/ai-zombie/bin/secrets-edit
```

Supported variables:

| Variable             | Purpose                                  |
| -------------------- | ---------------------------------------- |
| `OPENAI_API_KEY`     | API key for the OpenAI provider          |
| `ANTHROPIC_API_KEY`  | API key for the Anthropic provider       |
| `GEMINI_API_KEY`     | API key for Google Gemini (routed via `pi-ai`'s `google` provider) |
| `XAI_API_KEY`        | API key for the xAI provider             |
| `OPENROUTER_API_KEY` | API key for the OpenRouter aggregator. Requires `ZOMBIE_MODEL` to be set to a fully-qualified id such as `anthropic/claude-3.5-sonnet`. |
| `MISTRAL_API_KEY`    | API key for the Mistral provider         |
| `GROQ_API_KEY`       | API key for the Groq provider            |
| `ZOMBIE_PROVIDER`    | One of `openai`, `anthropic`, `gemini`, `xai`, `mistral`, `groq`, `openrouter`, `lmstudio` (default: first matching key found, in that order) |
| `ZOMBIE_MODEL`       | Model used by both the agent loop and the chat surface; required for `openrouter`/`lmstudio` unless their provider-specific model env var is set; overrides provider-specific model env vars and defaults |
| `ZOMBIE_OPENAI_MODEL`     | Override the default model used when the active provider is `openai` |
| `ZOMBIE_ANTHROPIC_MODEL`  | Override the default model used when the active provider is `anthropic` |
| `ZOMBIE_GEMINI_MODEL`     | Override the default model used when the active provider is `gemini` |
| `ZOMBIE_XAI_MODEL`        | Override the default model used when the active provider is `xai` |
| `ZOMBIE_MISTRAL_MODEL`    | Override the default model used when the active provider is `mistral` |
| `ZOMBIE_GROQ_MODEL`       | Override the default model used when the active provider is `groq` |
| `ZOMBIE_OPENROUTER_MODEL` | Fully-qualified OpenRouter model id (e.g. `anthropic/claude-3.5-sonnet`); used only when `ZOMBIE_MODEL` is unset |
| `ZOMBIE_CHAT_PORT`   | Loopback port for the chat UI (default `7878`) |
| `ZOMBIE_ADMIN_PASSWORD` | Chat-UI password gate. The installer asks for it (default `braaaains`) and stores only a PBKDF2 hash as `ZOMBIE_ADMIN_PASSWORD_HASH` in `secrets/env`. |
| `ZOMBIE_TTL_DAYS`    | Initial Time to Live in whole days before the zombie is permanently disabled (default `7`). Valid existing lifecycle state is preserved on reinstall. |
| `LMSTUDIO_API_KEY`   | API key for a local OpenAI-compatible server (LM Studio / Ollama / llama.cpp). Pair with `ZOMBIE_PROVIDER=lmstudio` and `ZOMBIE_MODEL`; the server URL lives in `~/.pi/agent/models.json` (most local servers ignore the key). |
| `DISPLAY`            | Pre-seeded in the generated `secrets/env` (default `:0`); vestigial, retained for compatibility and not used by the loopback-only chat service |

Per-provider defaults if no `ZOMBIE_MODEL` / `ZOMBIE_<PROVIDER>_MODEL`
override is set (from `payload/agent/providers.py`):

| Provider     | Default model               |
| ------------ | --------------------------- |
| `openai`     | `gpt-4o-mini`               |
| `anthropic`  | `claude-3-5-sonnet-latest`  |
| `gemini`     | `gemini-2.0-flash`          |
| `xai`        | `grok-2-1212`               |
| `mistral`    | `mistral-small-latest`      |
| `groq`       | `llama-3.1-8b-instant`      |
| `openrouter` | *(no default; must be set)* |
| `lmstudio`   | *(no default; must be set)* |

All providers are routed through [`@earendil-works/pi-ai`][pi-ai].
At every install or repair, `scripts/install.sh` resolves the npm
`latest` release, verifies the registry-provided integrity hash, and
installs it globally. The resolved version is written to
`/opt/ai-zombie/agent/pi-ai.version`. The chat service shells out to
the Node bridge at `/opt/ai-zombie/agent/pi-ai-bridge.mjs`; there are
no bespoke per-provider Python clients.

`ZOMBIE_PROVIDER` + `ZOMBIE_MODEL` (plus the matching `*_API_KEY`) are
the **single source of truth** for both the status banner and the agent
loop that produces every chat answer. Resolution is:

1. explicit provider argument (internal API only), else
   `ZOMBIE_PROVIDER`, else the first configured key in the provider
   table order above;
2. explicit model argument (internal API only), else `ZOMBIE_MODEL`,
   else the provider-specific `ZOMBIE_<PROVIDER>_MODEL`, else the
   registry default.

`payload/agent/pi_mono.py` resolves the active provider/model through
the same `payload/agent/providers.py` registry and passes them to the
`pi` CLI (`--provider` / `--model`), forwarding only the active
provider's key. This means the `pi` CLI's own native configuration
(`~/.pi`) and its built-in default provider are **not** consulted when a
provider is configured here — there is no second place to set the
model. The one exception is the `lmstudio` provider: because a local
server has no fixed endpoint, the installer writes its base URL to the
`pi` custom provider file `~/.pi/agent/models.json` (the model id and
key still come from `secrets/env`). See
[Local LLM discovery](#local-llm-discovery-lan-scan).

[pi-ai]: https://github.com/earendil-works/pi

Restart the chat service after editing:

```bash
sudo systemctl restart ubuntu-zombie-chat.service
```

## Local LLM discovery (LAN scan)

During an **interactive** install the script can scan the host's IPv4
`/24` — all 256 addresses, e.g. `192.168.1.0`–`192.168.1.255` when the
host is `192.168.1.34` — for an OpenAI-compatible local LLM server
answering on `http://<ip>:1234/v1`. Servers such as
[LM Studio](https://lmstudio.ai/) (which listens on port `1234` by
default), Ollama, and `llama.cpp` expose a `/v1/models` endpoint; the
installer queries each responder, collects the model ids it advertises,
and offers them as the **starting model** in the parameter-review step.
If `ZOMBIE_MODEL` or a provider-specific model override is already non-empty
in the install environment or installed `secrets/env`, the automatic scan is
skipped and that selection is preserved.

When a model is chosen, the generated `/opt/ai-zombie/secrets/env`
records it as the `lmstudio` provider:

```
ZOMBIE_PROVIDER=lmstudio
ZOMBIE_MODEL=<the model id you picked>
LMSTUDIO_API_KEY=local
```

and the server URL is written to the `pi` custom-provider file
`~/.pi/agent/models.json` (owned by the agent account):

```json
{
  "providers": {
    "lmstudio": {
      "baseUrl": "http://<server-ip>:1234/v1",
      "api": "openai-completions",
      "apiKey": "LMSTUDIO_API_KEY",
      "compat": { "supportsDeveloperRole": false, "supportsReasoningEffort": false },
      "models": [ { "id": "<the model id you picked>" } ]
    }
  }
}
```

The agent loop (`pi-mono`, which produces every chat answer) reaches the
local server through this `lmstudio` provider; `pi --provider openai`
would ignore the base URL and hit `api.openai.com` instead, so a
dedicated local provider is required. Most local servers ignore the API
key; set `ZOMBIE_LOCAL_LLM_API_KEY` (or edit the files afterwards) if
yours requires a real one. After installation, `/locals` rescans ports
`1234`, `8080`, `11434`, and `51234` across the local `/24` and on
`127.0.0.1`, then lists the discovered API URLs and marks the active URL
when found. The private managed llama.cpp port `58080` is also checked on
loopback. `/local <url>` activates a listed API, retaining the current
model when that server advertises it, and updates the running provider,
model, and `~/.pi/agent/models.json`. `/models` lists the catalogue exposed
by the active provider, including live LM Studio models; `/model <id>`
switches models.

The chat command finder shows every command when the composer contains only
`/`, then narrows the list as you type. `/help <command>` gives detailed
usage and side-effect information for one command, aliases included;
`/help <pattern*>` gives full pages for matching commands and `/help all`
shows every full help page. `/fullwidth [on|off]` changes and remembers the
transcript width for the current browser. `/rebrand <title>` changes the
browser title, header, wordmark, login prompt, and tombstone label for the
current browser; `/rebrand` resets those labels to Ubuntu Zombie.
`/reprompt <placeholder>` changes and remembers the composer placeholder for
the current browser; `/reprompt` resets it to `AI System Administrator`. The
browser stores `/fullwidth`, `/rebrand`, and `/reprompt` preferences in local
storage, so redeploying the chat assets does not reset them. The chat header
shows only the active model, plus its IP address when the provider is local.
`/status`
makes a minimal completion against the selected provider to prove credentials and
connectivity, so hosted providers may record a very small amount of usage.
That probe is cached for 30 seconds to prevent rapid requests from multiplying
provider cost. It also reports the provider and model, primary host IP, OS and
resource facts, system and service uptime, lifecycle state, active work,
conversation/message totals, tool totals, and browser-session transfer
counters. `/version` checks
fixed GitHub and npm metadata endpoints for current Ubuntu Zombie, `pi-mono`,
and `pi-ai` releases and also reports the installed Python, Node, and SQLite
runtimes. Both commands degrade cleanly when an upstream service is offline.

The scan is best-effort and skipped automatically for `--yes`,
non-interactive, non-TTY, and already-configured-model runs. It needs `curl`
and `python3` (both already required by the product).

| Variable                 | Default | Purpose                                                              |
| ------------------------ | ------- | -------------------------------------------------------------------- |
| `ZOMBIE_SKIP_LLM_SCAN`   | `0`     | Set to `1` to skip the LAN scan entirely.                            |
| `ZOMBIE_LLM_SCAN_PORT`   | `1234`  | Extra TCP port probed by runtime `/locals`; installer discovery uses this port exclusively. |
| `ZOMBIE_LOCAL_LLM_API_KEY` | `local` | API key recorded for the discovered server (most local servers ignore it). |

You can also trigger the scan on demand from the interactive setup
review by choosing the **Local LLM** field.

## Agent account name

The installer creates a single local Linux user as the operating
identity of the AI Systems Administrator. The default name is
`zombie`. To pick a different name, pass `ZOMBIE_USER` to the
installer:

```bash
sudo ZOMBIE_USER=admin ./scripts/install.sh install
```

The same variable must be set on every later `install`, `verify`,
`doctor`, `repair`, or `uninstall` run that targets a non-default
account. `AGENT_USER` is still accepted as a backward-compatible alias
so older installs (which used `agent`) can still be repaired or
removed by exporting `AGENT_USER=agent`.

The chosen name appears throughout: `/home/<name>`, the sudoers
drop-in `/etc/sudoers.d/90-<name>-ubuntu-zombie`, the systemd
`User=`/`Group=` of `ubuntu-zombie-chat.service`, and the system
prompt the chat service hands to the LLM.

## Rotating provider keys

1. `sudo /opt/ai-zombie/bin/secrets-edit` — replace the value.
2. `sudo systemctl restart ubuntu-zombie-chat.service`.
3. Optionally revoke the old key in the provider's console.

## Revoking the agent

To stop useful agent operation immediately:

```bash
sudo /opt/ai-zombie/bin/secrets-edit   # delete every API key
sudo systemctl restart ubuntu-zombie-chat.service
```

The chat will load but refuse to call any provider.

To stop the service entirely:

```bash
sudo systemctl disable --now ubuntu-zombie-chat.service
```

To remove privileged access without uninstalling everything:

```bash
sudo rm /etc/sudoers.d/90-zombie-ubuntu-zombie
```

## Policy

`/etc/ubuntu-zombie/policy.yaml` controls what the agent may run
without approval, what requires approval, and what requires the extra
destructive confirmation phrase. See `ARCHITECTURE.md` for the action
classes. The chat service reloads the policy on every request — no
restart needed.

### Fail-closed default

`settings.default_class` is the classification used when no rule
matches a proposed command. The shipped default is `destructive` —
the highest gated class — so unknown commands cannot auto-run.
Operators may relax this to a lower class once a workflow is proven
safe.

### Sudo allow-list

`sudo_allow_list:` (a top-level list of program names) keeps common
privileged commands at `system_change` despite the conservative
fail-closed default. The standard approval prompt still fires for
these — they do not auto-run — but they are not escalated to
`destructive`. Entries are matched against the basename of the
program that `sudo` invokes (after `sudo` consumes its own flags), so
`sudo apt install foo`, `sudo -u root systemctl restart cron`, and
`sudo -E /usr/bin/apt update` are all classified by the entries for
`apt` and `systemctl`. Add entries only after confirming the
underlying program is safe to elevate.

### Tool classes and per-turn budgets

The agent emits structured tool calls from a closed registry defined in
`payload/agent/tools.py`:

| Tool              | Registry default class | Purpose                                                    |
| ----------------- | ---------------------- | ---------------------------------------------------------- |
| `shell.run`       | per-argv via `classify` | Run a shell command through the existing runner.          |
| `fs.read`         | `read_only`            | Read a UTF-8 text file within the readable allow-list.     |
| `fs.list`         | `read_only`            | List directory entries within the readable allow-list.     |
| `fs.write`        | `user_change`          | Write text content to a path within the writable allow-list. |
| `pkg.query`       | `read_only`            | Query installed package metadata via dpkg/apt-cache.       |
| `pkg.install`     | `system_change`        | Install Debian packages via apt-get.                       |
| `svc.status`      | `read_only`            | Inspect a systemd unit (status / is-active).               |
| `svc.control`     | `system_change`        | Start/stop/restart/reload/enable/disable a systemd unit.   |
| `net.status`      | `read_only`            | Read-only interface and listening-port inspection.          |
| `web.fetch`       | `read_only`            | Fetch a public http/https URL read-only (GET/HEAD).        |
| `skill.list`      | `read_only`            | Enumerate available skills.                                |
| `skill.load`      | `read_only`            | Read the markdown body of a skill by name.                 |

`fs.read` and `fs.list` resolve symlinks before checking the readable
allow-list (`/opt/ai-zombie/state`, `/etc`, `/var/log`, `/proc`, `/sys`,
`/usr/share`, `/usr/lib` and `/run/systemd`), which keeps the canonical
Ubuntu inspection files readable — `/etc/os-release`, `/etc/localtime`
and `/etc/resolv.conf` are symlinks into the last three roots — while
home directories and `/opt/ai-zombie/secrets` stay out of reach.
`/proc/<pid>/environ` is denied explicitly so provider keys held in the
chat service's environment are never returned by an auto-approved read.
Both tools then act on the resolved path, so a symlink swapped after the
check cannot escape the allow-list.
`fs.write` remains limited to `/opt/ai-zombie/state` and `/tmp`.

`web.fetch` performs read-only outbound lookups so the agent can check
an upstream version or read documentation before advising a change. It
accepts `GET`/`HEAD` on `http`/`https` URLs only, refuses URLs carrying
credentials, and refuses hosts that resolve to a non-global address —
loopback, link-local (including `169.254.169.254`) and private ranges —
on the initial request and on every redirect hop. Bodies are truncated
to `max_bytes` (64 KiB default, 1 MiB ceiling) and the request URL is
recorded in the audit log. There is no request body: the internet is
readable, not writable, so local files and secrets cannot be shipped
out through this tool.

Two `policy.yaml` blocks control them:

```yaml
tool_classes:
  # Override the registry default for a tool. shell.run is always
  # classified per-argv via classify(); listed tools take the class
  # below before classify_tool falls back to the registry default.
  fs.write: user_change
  pkg.install: system_change

agent:
  max_tool_calls_per_turn: 1000      # total tool calls per user message
  max_elevated_calls_per_turn: 250   # cap on non read_only calls
  max_turn_seconds: 86400            # idle limit; active turns reset it
```

Budget enforcement:

- `max_tool_calls_per_turn` is enforced by `pi_mono.run_turn` and the
  bridge — once exceeded, the agent receives a synthetic
  `budget_exceeded:` observation for further calls.
- `max_elevated_calls_per_turn` is enforced by `server.py` against the
  classification returned by `policy.classify_tool`. Each call past the
  budget is recorded as a `budget_exceeded` audit decision and the
  agent sees the same synthetic observation so it ends the turn
  cleanly. The same counter drives the operator-facing per-turn
  budget badge in the UI.
- `max_turn_seconds` is an inactivity watchdog, not a total-duration
  ceiling. Each model event or tool result resets it, so an active task can
  run longer than 24 hours. The bridge and browser deadlines sit slightly
  above it so the Python driver reports stalled turns cleanly first. Setting
  it to `0` disables the watchdog entirely; a wedged turn then ends only
  when the operator presses Stop.

These shipped defaults deliberately favour capable local models. Operators
can still tune all three values in `/opt/ai-zombie/etc/policy.yaml`; elevated
calls continue to require the configured approvals regardless of budget.

### pi-mono runtime

At every install or repair, the installer resolves the npm `latest`
release of `@earendil-works/pi-coding-agent`, verifies the
registry-provided integrity hash, and records the resolved version in
`/opt/ai-zombie/agent/pi-mono.version`. It renders runtime configs into
`/opt/ai-zombie/pi/`:

| Path                                   | Purpose                                  |
| -------------------------------------- | ---------------------------------------- |
| `/opt/ai-zombie/pi/settings.json`      | pi-mono settings (`--no-builtin-tools`)  |
| `/opt/ai-zombie/pi/APPEND_SYSTEM.md`   | rendered system-prompt prelude           |
| `/opt/ai-zombie/agent/pi-mono-bridge.mjs` | Node bridge wrapping `pi --mode json` |
| `/opt/ai-zombie/state/logs/pi-mono.*.log` | per-turn bridge logs, rotated daily   |
| `/opt/ai-zombie/state/pi-mono-sessions/`  | pi session/checkpoint state           |

Environment overrides for the `pi-mono` runtime are documented in
[Advanced environment overrides](#advanced-environment-overrides)
below (look for the `ZOMBIE_PI_MONO_*` variables).

## Chat access

The chat UI is served at `http://127.0.0.1:${ZOMBIE_CHAT_PORT:-7878}/`.
On a shared desktop every local user can reach the loopback socket, so the UI is protected
by a **password gate**: the installer asks for a chat password (default
`braaaains`) and stores only a PBKDF2 hash as
`ZOMBIE_ADMIN_PASSWORD_HASH` in `secrets/env`. Set a custom one with
`ZOMBIE_ADMIN_PASSWORD` or through the interactive parameter review.
(Having a root/agent shell on the box is still root-equivalent — that
matches the trust model — but the password keeps casual local users
out of the administrator.)

In the chat UI, `/password new secret` changes the password after a
browser confirmation and clears existing login sessions. `/password`
removes the password after confirmation; because the gate is disabled,
no logoff is required.

During a normal turn the browser uses an authenticated server-sent-events
stream to show live phase, token, tool, and approval updates before the
final answer. There is no extra configuration for this: if streaming is
unavailable, the UI falls back to the same JSON turn/reload behaviour used
by older versions.

The stream's queue bound, completed-turn retention window, and keepalive
interval are fixed implementation limits in `payload/agent/server.py`,
not operator-tuned environment variables. They exist to bound memory for a
disconnected browser while keeping one active local operator turn lively.

The prompt box stays editable while the agent is working. Submitting a
normal message during a busy turn stores one visible queued message and
sends it automatically when the current turn finishes; submitting another
normal message replaces that queued item with an explicit notice. Slash
commands such as `/stop`, `/approve`, and `/deny` still run immediately.

### Agent reactivation

The pi agent may call the policy-mediated `timer.reactivation` tool when work
must continue beyond the current model turn. The server keeps exactly one
future reactivation across all conversations. The chat footer shows its fire
time, reason, prompt preview, and a **Cancel** button. When it fires, a visibly
labelled synthetic user request starts an ordinary turn in the same
conversation; all tool policy and approval checks run again. That turn streams
into the transcript live — its tools and reply text appear as they happen, the
same way an operator's own message does — so a task spread across several
continuations (for example a long essay) is visibly chained rather than
appearing only once each turn has finished. When a reply schedules or rejects a
continuation, the terminal turn payload carries that outcome too, so the queued
or stopped banner appears immediately rather than on the next poll.

The shipped pi bridge presents this capability through a structured
`<ubuntu-zombie-reactivation>` request in the agent's reply. The server removes
every machine-readable block — wherever it appears, including inside a code
fence or ahead of a closing sentence — before saving the visible answer, uses
the last one, validates it against the closed `timer.reactivation` schema and
policy class, and reports whether the request was accepted. If a provider
forgets the wrapper but emits a bare top-level JSON object with exactly the
`timer.reactivation` fields, the server recovers and hides that request the
same way rather than leaving it as visible text. This lets the AI reactivate
itself; `/reactivation` is the operator control for the capability, not the
mechanism that schedules each continuation.

Continuation chains are debuggable. A due timer is never started while its
conversation still has a turn in flight (the deferral is audited as
`reactivation_deferred`), and a timer that the daemon refuses to run — TTL
expired, capability disabled, conversation gone, turn could not start — is
recorded on the durable record, written to the transcript as a visible system
message, and audited. `/reactivation` and the chat banner report the last
terminal outcome, so a chain that stops after a few continuations shows the
reason instead of simply going quiet. Each fired continuation is audited with
its `chain_index` and labelled in chat as `continuation N`. A continuation turn
that fails inside itself is audited as `reactivation_turn_failed`.

Reactivation is enabled by default with a 5-second minimum and 1-hour maximum
delay. Both limits and the enabled state are durable in `conversations.db`.
These defaults are also the hard safety bounds, and no timer may outlive the
remaining TTL. Installer reruns preserve the database and therefore retain
reactivation settings and pending timer state.

| Command | Effect |
| ------- | ------ |
| `/reactivation` | Show settings and the upcoming timer. |
| `/reactivation on` | Allow the agent to schedule a continuation. |
| `/reactivation off` | Disable scheduling and cancel the pending timer. |
| `/reactivation cancel` | Cancel the pending timer without disabling scheduling. |
| `/reactivation reset` | Restore defaults and clear queued, active, and stale status state. |
| `/reactivation minimum <duration>` | Set the minimum permitted delay. |
| `/reactivation maximum <duration>` | Set the maximum permitted delay. |
| `/reactivate ...` | Alias for `/reactivation ...`. |

Durations use the same number/unit format as `/ttl`. A reset enables
reactivation, restores the 5-second/1-hour bounds, cancels queued and active
continuations, and clears the previous outcome from current status. Historical
timer rows, transcript events, and audit records are retained. Disabling,
cancelling, resetting, or changing bounds requires an authenticated chat
session.

### Time to Live (the kill switch)

The first install gives the root-capable agent a bounded lifetime. The
**Time to Live** defaults to 7 days (`ZOMBIE_TTL_DAYS`, or set it in the
interactive review). When the TTL elapses — or an operator runs the
`/ttl --die` chat command — the zombie writes a durable tombstone and is
**permanently disabled**: it refuses to answer prompts and shows a "this
zombie has died" notice. A re-run of `scripts/install.sh install` preserves a
valid lifecycle file, including TTL extensions, remaining time, and a dead
tombstone. A full uninstall followed by a fresh install creates a new
countdown.

Chat commands:

| Command       | Effect                                                        |
| ------------- | ------------------------------------------------------------- |
| `/ttl`                   | Show the remaining Time to Live.                              |
| `/ttl <duration>`        | Extend the Time to Live by a duration from the current expiry. |
| `/ttl reset [duration]`  | Reset the Time to Live from now (default: 7 days).             |
| `/ttl --die`             | Trip the kill switch now — permanently disables the zombie.    |

Durations are written as number/unit pairs such as `14 days`,
`2 years 3 months`, or `3 hours`; a bare number is kept as the legacy
days shorthand. Months and years are fixed approximations of 30 and
365 days.

State lives in `/opt/ai-zombie/state/lifecycle.json`. It can also be
inspected from the agent account with
`python3 /opt/ai-zombie/agent/lifecycle.py status`.

## Logs and state

| Path                                       | Purpose                                         |
| ------------------------------------------ | ----------------------------------------------- |
| `/var/log/ubuntu-zombie-install.log`       | Installer transcripts                           |
| `/var/log/ubuntu-zombie/install-receipt.txt` | Install receipt (parameters + start/finish outcome) |
| `/var/log/ubuntu-zombie/audit.log`         | JSON-lines AI audit trail                       |
| `/opt/ai-zombie/state/conversations.db`    | Chat history (SQLite)                           |
| `/opt/ai-zombie/state/lifecycle.json`      | Time-to-Live state + tombstone                  |
| `/opt/ai-zombie/state/logs/pi-mono.*.log`  | Per-turn pi-mono bridge logs (rotated daily)    |
| `/opt/ai-zombie/state/pi-mono-sessions/`   | pi session/checkpoint state                     |

## Operator helpers

`scripts/install.sh` installs a small set of helper commands under
`/opt/ai-zombie/bin/`:

| Command                | Purpose                                                                 |
| ---------------------- | ----------------------------------------------------------------------- |
| `secrets-edit`         | Safely edit `secrets/env`; re-asserts `0600` mode after `$EDITOR` exits |
| `health-check`         | One-shot health summary (chat service, provider credential, disk, …)    |
| `audit-recent`         | Tail the most recent decisions from `audit.log`                         |
| `collect-diagnostics`  | Bundle logs and state into a tarball with secrets redacted              |
| `zombie-chat`          | Print the local chat URL                                               |

The installer also drops `verify` under the same directory.

## Interactive setup review

When `scripts/install.sh install` runs on an interactive terminal (i.e.
not `--yes` and not `ZOMBIE_NONINTERACTIVE=1`), it opens an editable
**parameter review** before touching the host. The review is scoped to
the selected components. Zombie runs show agent, chat, TTL, provider, and
local-LLM settings; Forgejo-only runs show Forgejo, PostgreSQL, runner,
transcript, and receipt settings. Llama-only runs display the
product-generated plan; configure it with the `LLAMA_*` inputs below.
Enter a number to edit a field (with validation and re-prompting on bad
input), toggle the boolean options, and repeat until you are satisfied;
then accept to begin the install. Cancelling at the review (`q`) exits
without changing anything.

The review uses the **Zombie Orchid** highlight (`#AC43D9`) with
compatible accent colours when colour is enabled. Colour follows the same
`ZOMBIE_COLOR=auto|always|never` / `NO_COLOR` policy as the rest of the
output, so `--no-color` produces a plain, screen-reader-friendly table.

Automated runs (`--yes`, `ZOMBIE_NONINTERACTIVE=1`, or non-TTY stdin) skip
the review entirely and use the supplied environment unchanged.

## Optional components ("Ubuntu Zombie + Options")

Beyond the baseline, the installer supports **opt-in components**. The
canonical command grammar is `scripts/install.sh <verb> [component ...]
[flags]`; public component targets are `zombie`, `forgejo`,
`forgejo-runner`, and `llama`. Existing `ZOMBIE_INSTALL_<COMPONENT>` flags
remain supported for automation and
are additive with explicit targets. Every flag defaults to `0`, so a
default install is unchanged. Enabled components appear in the
interactive review (item `9) Options` opens a nested menu), the dry-run
plan, the pre-flight banner, and the install receipt; they are checked
by `verify`/`doctor`, repaired by `repair`, and reversed by
`uninstall.sh`. The design surface for future components lives under
[`options/`](../options/README.md).

`install forgejo` installs Forgejo and PostgreSQL without creating the
zombie account or deploying the agent runtime. Explicit targets and
legacy environment selectors are additive and execute in registry order,
so `install forgejo zombie` and `install zombie forgejo` converge the
same components. `ZOMBIE_INSTALL_FORGEJO=1 install` remains equivalent
to the combined path.

`install forgejo-runner` installs the co-located Actions runner and
automatically selects its required `forgejo` dependency. It does not select
the zombie component. The legacy `ZOMBIE_INSTALL_FORGEJO_RUNNER=1` selector
remains additive and resolves to the same component pair.

`install llama` delegates to an independently versioned product without
selecting `zombie`. `ZOMBIE_INSTALL_LLAMA=1` remains an additive compatibility
selector for automation.

### Independent Llama product (`install llama` compatibility target)

Llama owns its lifecycle under `products/llama/`; the root target only maps
compatibility inputs and delegates. The product installs pinned CPU build
`llama.cpp` b10054 and a checksum-verified SmolLM2 360M Instruct Q4_K_M model.
It runs as the dedicated `llama-cpp` system account and exposes an
OpenAI-compatible API only at `http://127.0.0.1:8080/v1`. Every local user can
reach the endpoint, but it is not reachable from the LAN.

| Variable | Default | Effect |
| -------- | ------- | ------ |
| `ZOMBIE_INSTALL_LLAMA` | `0` | Add the independent `llama` component to selected install targets. |
| `LLAMA_PORT` | `8080` | Fixed loopback port; other values are rejected. |
| `LLAMA_MODEL_ID` | `smollm2-360m-instruct-q4_k_m` | Approved default model; other IDs are rejected in this release. |
| `LLAMA_CONTEXT_SIZE` | `2048` | Context size from 512 through the approved model maximum of 2048 tokens. |
| `LLAMA_CPU_THREADS` | detected logical CPUs | CPU worker count from 1 through 1024. |
| `LLAMA_BOOT` | `enabled` | `enabled` starts now and at boot; `disabled` installs the service stopped. |

The runtime lives under `/opt/llama.cpp`, configuration under
`/etc/llama.cpp`, models and state under `/var/lib/llama.cpp`, and logs
under `/var/log/llama.cpp`. Downloads are pinned by immutable release or model
revision and SHA-256. Existing legacy state is adopted only when both old
markers, identity, configuration, exact unit, runtime tree, and model checksum
validate. Any ambiguous resource stops the product before mutation.

`llama-manager` supports `status`, `start`, `stop`, `restart`, `enable`,
`disable`, `test`, `models`, and `hardware`; mutating commands require
root. `llama-manage` owns `status`, `verify`, `doctor`, `repair`, `backup`,
`update`, `rollback`, `suspend`, `resume`, and `uninstall`. Root compatibility
targets for verify, doctor, repair, and uninstall delegate to it.

The safe uninstall default removes runtime and configuration while retaining
models and state. Complete deletion is available only through
`llama-manage uninstall --purge --confirmation 'DELETE LLAMA STATE' --yes`;
`--yes` by itself is not destructive confirmation. Full product configuration
and request-file rules are in
[`products/llama/docs/CONFIGURATION.md`](../products/llama/docs/CONFIGURATION.md).

### Forgejo server (`ZOMBIE_INSTALL_FORGEJO=1`)

A self-hosted [Forgejo](https://forgejo.org/) git forge backed by
PostgreSQL, with LAN discovery and HTTPS provided by Avahi and Caddy.
An optional co-located Forgejo Actions runner uses a restricted Docker
executor with host networking. The server's independent lifecycle and direct
inputs are documented in
[`products/forgejo/`](../products/forgejo/README.md).

Forgejo itself binds only to `127.0.0.1`. Caddy is the LAN-facing entry
point on HTTPS port `443`, uses its internal certificate authority, and
proxies to Forgejo's loopback port. Avahi advertises the machine hostname
through mDNS, so the default URL is
`https://<lowercase-machine-hostname>.local/`.
The product installs Caddy from the supported Ubuntu package sources and
writes this hostname route as a marked block in
`/etc/caddy/Caddyfile` while preserving unrelated Caddy sites. Re-running
`repair forgejo` replaces that managed block and migrates the older
`/etc/caddy/conf.d/forgejo.caddy` fragment if present.

| Variable                        | Default                                  | Effect |
| ------------------------------- | ---------------------------------------- | ------ |
| `ZOMBIE_INSTALL_FORGEJO`        | `0`                                      | Set to `1` to install Forgejo + PostgreSQL. |
| `ZOMBIE_INSTALL_FORGEJO_RUNNER` | `0`                                      | Add the co-located Actions runner and its required Forgejo server component. |
| `FORGEJO_HTTP_PORT`             | `3000`                                   | Forgejo loopback web/API port behind Caddy. |
| `FORGEJO_ADMIN_USER`            | `forgejo-admin`                          | Initial admin account name. |
| `FORGEJO_ADMIN_EMAIL`           | `forgejo-admin@localhost.localdomain`    | Initial admin email. |
| `FORGEJO_ADMIN_PASSWORD`        | *(empty — generated)*                    | Compatibility input for the initial admin credential; converted to a root-private file reference. |
| `FORGEJO_DB_NAME`               | `forgejo`                                | PostgreSQL database name. |
| `FORGEJO_DB_USER`               | `forgejo`                                | PostgreSQL role name. |
| `FORGEJO_DB_PASSWORD`           | *(empty — generated)*                    | Compatibility input for the PostgreSQL credential; converted to a root-private file reference. |
| `FORGEJO_VERSION`               | *(empty — latest release)*               | Pin a Forgejo release (e.g. `11.0.3`); the resolved value is recorded in the receipt. |
| `FORGEJO_RUNNER_VERSION`        | *(empty — latest release)*               | Pin a forgejo-runner release. |
| `FORGEJO_RUNNER_LABELS`         | `ubuntu-latest:docker://node:20-bookworm`| Runner labels; the default maps `ubuntu-latest` jobs to a Docker container. |
| `FORGEJO_CONFIRM_UPDATE`        | *(empty)*                                | Legacy compatibility approval used by the root parameter review. |
| `FORGEJO_CONFIRM_DATABASE_REUSE`| *(empty)*                                | Legacy compatibility approval; ambiguous database state still fails closed. |

Every one of these decision parameters can also be set interactively:
the review's `9) Options` sub-menu lets you toggle the server and
runner and edit the port, the admin account (username, email,
password), the PostgreSQL database (name, role/username, password),
and the version pins and runner labels before anything is installed.

Secrets (`SECRET_KEY`, `INTERNAL_TOKEN`, `JWT_SECRET`,
`LFS_JWT_SECRET`) are generated at install time and stored only in
`/etc/forgejo/app.ini` (mode `640`, owner `root:git`); re-runs reuse
them rather than rotating them. Compatibility callers can set
`FORGEJO_ADMIN_PASSWORD` / `FORGEJO_DB_PASSWORD`; the shim converts those
values to private temporary references before invoking the product. No
credential value enters root or product receipts. A generated initial
administrator credential is also available once in
`/etc/forgejo/bootstrap-admin-password` (root-only, mode `600`). A generated admin
password must be changed on first sign-in; an operator-chosen one is
kept as-is. The database credential and application recovery secrets remain
only in `app.ini`. Direct product use accepts
`FORGEJO_ADMIN_PASSWORD_FILE` and `FORGEJO_DB_PASSWORD_FILE`, not raw values.

The configuration directory is mode `750` and the running Forgejo service
cannot rewrite it. During an install or upgrade, the installer stops Forgejo,
temporarily grants the `git` account write access for the one-shot database
migration, and restores the directory/file to `750`/`640` even if migration
fails. Startup is considered successful only after `/api/healthz` responds.
An existing component installation is adopted only when its root-owned
manifest, account, unit, loopback settings, and complete recovery secrets
validate exactly. The product requires the exact `ADOPT FORGEJO` confirmation;
the compatibility command supplies it only to that validator. Existing
database state with a missing, empty, mismatched, or incomplete `app.ini`
fails before credential or secret rotation. Update creates a protected backup
and never silently drops repository data. Server mutations stop an active
runner first and restart it only after Forgejo passes its health gates.

### Trust the Forgejo local certificate authority

Caddy creates and renews the site certificate automatically. A client
must trust Caddy's root certificate once before browsers and Git accept
the HTTPS URL without a warning. The installer exports the public root
certificate to:

```text
/etc/forgejo/caddy-local-ca.crt
```

Copy that file to each client over an authenticated channel (local console,
SSH, or managed device deployment), then import it into that client's
trusted root certificate store. Do not trust a copy downloaded through an
unverified browser warning: anyone able to replace that download could
substitute their own root CA. After import, open the URL shown by the
installer or run `sudo ./scripts/install.sh verify forgejo`.

The root certificate is intentionally public; Caddy's private CA key stays
under `/var/lib/caddy` and is not exported. The product also installs that
public root into the host trust bundle for same-host runner jobs. Removing
Forgejo deletes the exported and host-trust copies plus managed Caddy/Avahi
configuration, but leaves the shared `caddy`, `avahi-daemon`, and
`libnss-mdns` packages installed.
Remove the trusted root from clients when the Forgejo host is retired.

Caveats:

- `.local` discovery is link-local and requires mDNS support on the client.
  It does not replace a firewall. Caddy accepts HTTPS on host network
  interfaces so DHCP address changes keep working; restrict TCP `443` at
  the host or network firewall if the machine also has an untrusted
  interface. Forgejo's backend port remains loopback-only. Registration
  is disabled by default
  (`DISABLE_REGISTRATION = true`); the admin creates accounts.
- Co-locating the runner with the forge is contrary to upstream
  guidance. The managed runner allows one job at a time, disables privileged
  containers and arbitrary host-volume mounts, and does not expose the Docker
  socket inside jobs. It also disables the built-in Actions cache proxy,
  which otherwise listens on every host interface. Job containers still use
  host networking so they can reach loopback-only Caddy; an explicit host
  entry resolves the `.local` URL without mDNS in the image, and a read-only
  host CA bundle plus Git, OpenSSL, Python, and Node trust variables validates
  Caddy TLS. Host networking also exposes other host loopback services. The
  runner process itself has Docker-daemon access, which is root-equivalent.
  Enable it only for repositories and maintainers trusted to control this
  machine.
- Binaries are downloaded from Forgejo's release host and verified against
  published SHA-256 checksums; pin `FORGEJO_VERSION` where
  reproducibility matters.
- Direct `forgejo-manage uninstall --yes` retains repositories, database, and
  recovery secrets. Purge requires `DELETE FORGEJO STATE`. The compatibility
  uninstaller removes the dependent runner first and maps its historical
  `--yes` behavior to confirmed purge.

## Component manifest and selective lifecycle

Installed components are recorded under
`/var/lib/ubuntu-zombie/components/` by default. Set
`ZOMBIE_COMPONENT_MANIFEST_DIR` to override that directory for tests or
other hermetic workflows.

The manifest is used by `verify`, `doctor`, and `repair` to discover
installed components when you do not pass explicit targets. Selective
`uninstall` uses component targets to decide which component to remove:
`uninstall zombie` removes only the zombie account/runtime,
`uninstall forgejo-runner` removes only the runner, `uninstall forgejo`
removes Forgejo and its co-located runner, `uninstall llama` removes only
the standalone local model service, and bare `uninstall` removes all managed
components.

`--archive` and `--keep-agent` are lifecycle flags for zombie removal
only; `uninstall forgejo --archive` and
`uninstall forgejo --keep-agent` are rejected with exit code `2`.

## Install receipt

Every install writes a human-readable **receipt** recording all parameters
when the run starts and the outcome (result, duration, service status,
applied/satisfied step counts, next step) when it finishes. A failed run
appends a `FAILED` record with the line and exit code. The file is
root-only (mode `600`). Operator-supplied password values and provider
keys are never written; passwords the installer generates itself (for
optional components) are recorded in the finish record so the operator
can retrieve them.

| Variable             | Default                                        | Effect                                             |
| -------------------- | ---------------------------------------------- | -------------------------------------------------- |
| `ZOMBIE_RECEIPT`     | `1`                                            | Set to `0` to disable the receipt.                 |
| `ZOMBIE_RECEIPT_FILE`| `/var/log/ubuntu-zombie/install-receipt.txt`   | Override the receipt file path (absolute).         |

## Install command grammar

`scripts/install.sh` is idempotent and uses this canonical form:

```text
scripts/install.sh <verb> [component ...] [flags]
```

All verbs honour the same relevant `ZOMBIE_*` environment variables
documented above. Valid component targets are `zombie`, `forgejo`,
`forgejo-runner`, and `llama`.

| Verb        | Effect                                                                |
| ----------- | --------------------------------------------------------------------- |
| `install`   | Full install (default target: `zombie`). Safe to re-run.              |
| `verify`    | Read-only state check. Does not change state.                         |
| `doctor`    | Explain failures and likely fixes.                                    |
| `repair`    | Apply known-safe fixes (re-assert permissions, re-render `pi/` tree). |
| `uninstall` | Reverse the install (delegates to `scripts/uninstall.sh`). A component target removes only that component; no target removes all managed components. |

Examples:

```bash
sudo ./scripts/install.sh install zombie
sudo ./scripts/install.sh install forgejo
sudo ./scripts/install.sh install forgejo-runner
sudo ./scripts/install.sh install zombie forgejo
sudo ZOMBIE_INSTALL_FORGEJO=1 ./scripts/install.sh install
sudo ./scripts/install.sh verify zombie
sudo ./scripts/install.sh uninstall forgejo --dry-run
```

After editing `policy.yaml` or any template under
`/opt/ai-zombie/agent/templates/`, run `sudo ./scripts/install.sh
repair` to re-render the `pi/` tree and restart the chat service.

## Command-line flags

`scripts/install.sh` accepts these flags in addition to the verb and
component targets above. They can be combined (e.g. `install zombie
--yes --strict`) and may appear before or after the verb/targets:

| Flag                 | Effect                                                                       |
| -------------------- | ---------------------------------------------------------------------------- |
| `-h`, `--help`       | Grouped help with end-to-end example recipes, then exit.                     |
| `-v`, `--version`    | Print the version and exit.                                                  |
| `-n`, `--dry-run`    | Print every action; mutate nothing.                                          |
| `-y`, `--yes`        | Skip the interactive `Type YES` gate (attended scripted runs). Still prompts for any missing inputs unless `ZOMBIE_NONINTERACTIVE=1`. |
| `-q`, `--quiet`      | Only print warnings and errors.                                              |
| `--verbose`, `--debug` | Write shell xtrace to the install transcript (not the console).            |
| `--no-color`         | Disable coloured output (also honours `NO_COLOR` and `ZOMBIE_COLOR=never`).  |
| `--strict`           | Treat preflight warnings as fatal.                                           |
| `--json`             | Emit machine-readable JSON from `verify` / `doctor` (human output is default). |

Colour follows the `ZOMBIE_COLOR=auto|always|never` policy and the
widely-supported [`NO_COLOR`](https://no-color.org/) convention; output
is plain when not writing to a TTY.

### Shell completion

Completion scripts live under `scripts/completions/`:

```bash
# bash
source scripts/completions/install.bash

# zsh — add the directory to $fpath, then:
autoload -U compinit && compinit
```

## Skills

Skill files are short markdown briefs the agent loads via `skill.list`
/ `skill.load`. They are read from two directories:

| Path                         | Purpose                                                         |
| ---------------------------- | --------------------------------------------------------------- |
| `/opt/ai-zombie/skills/`     | Root-owned built-ins, including Ubuntu, file/programming, AI-agent, Hermes, OpenClaw and pi-mono operations. |
| `/etc/ubuntu-zombie/skills.d/` | Operator-extensible. Same mode/owner contract as `policy.yaml`. |

Drop additional `*.md` files into `/etc/ubuntu-zombie/skills.d/` to
extend the catalogue. Names must be unique across both directories;
shadowing is rejected at load time.

A skill is guidance, not capability: it can steer the model toward a
tool but never adds one, because the registry in
`payload/agent/tools.py` is closed. A file is auto-selected when a word
from its `<!-- triggers: ... -->` marker appears in the recent operator
turns, and the injected block names the on-disk path so the operator can
see exactly what was added to the prompt. Keep trigger words specific:
generic words load briefs on unrelated turns and waste context.

## Advanced environment overrides

Most operators never need these — the defaults match what
`scripts/install.sh` lays down — but they are honoured by the agent
processes and are useful for development, CI, and bespoke layouts:

| Variable                  | Default                                  | Consumer            |
| ------------------------- | ---------------------------------------- | ------------------- |
| `ZOMBIE_DIR`              | `/opt/ai-zombie`                         | installer, agent    |
| `ZOMBIE_SECRETS`          | `${ZOMBIE_DIR}/secrets/env`              | `server.py`, audit  |
| `ZOMBIE_POLICY`           | `/etc/ubuntu-zombie/policy.yaml`         | `policy.py`         |
| `ZOMBIE_AUDIT_LOG`        | `/var/log/ubuntu-zombie/audit.log`       | `audit.py`, `audit-recent` |
| `ZOMBIE_AUDIT_VERBOSE`    | *(unset; off)*                           | `audit.py` (opt-in: adds redacted `stdout_preview`/`stderr_preview` to `tool_call` entries to aid pre-release testing and operator debugging) |
| `ZOMBIE_AUDIT_PREVIEW_BYTES` | `2048`                                | `audit.py` (per-stream preview cap when `ZOMBIE_AUDIT_VERBOSE=1`; hard ceiling 16 KiB) |
| `ZOMBIE_HISTORY_DB`       | `/opt/ai-zombie/state/conversations.db`  | `history.py`        |
| `ZOMBIE_SKILLS_DIR`       | *(unset)*                                | `skill_loader.py` (extra directory consulted first) |
| `ZOMBIE_NODE`             | `which node`                             | pi-ai bridge spawner |
| `ZOMBIE_PI_AI_BRIDGE`     | `${ZOMBIE_DIR}/agent/pi-ai-bridge.mjs`   | pi-ai bridge spawner (used by tests) |
| `ZOMBIE_PI_MONO_BIN`      | `which pi`                               | `pi_mono.py`        |
| `ZOMBIE_PI_MONO_BRIDGE`   | `${ZOMBIE_DIR}/agent/pi-mono-bridge.mjs` | `pi_mono.py` (used by smoke tests) |
| `ZOMBIE_PI_MONO_LOG_DIR`  | `/opt/ai-zombie/state/logs`              | `pi_mono.py`        |
| `ZOMBIE_PI_MONO_SETTINGS` | `/opt/ai-zombie/pi/settings.json`        | `pi_mono.py`        |

## Health check

Run on demand:

```bash
/opt/ai-zombie/bin/health-check
```

Enable the systemd timer for periodic checks:

```bash
sudo systemctl enable --now ubuntu-zombie-health.timer
```
