# Hermes Chat Commands Selected for Ubuntu Zombie

This note filters the Hermes command catalogue in
`docs/research/HERMES-CHAT-COMMANDS.md` through Ubuntu Zombie's product
shape: one operator, one Ubuntu Desktop LTS host, a loopback-only chat
service, a closed tool registry, policy classification, and an audit log
for agent actions.

Here "command" means the chat slash-command surface, not the root
installer subcommands exposed by `scripts/install.sh` or the packaged
`ubuntu-zombie` wrapper.

It is a research note, not a committed roadmap. The goal is to separate
commands that make Ubuntu Zombie a better private AI sysadmin from
commands that belong to a gateway, multi-platform chat bot, generic agent
runtime, or cosmetic terminal shell.

## Selection rules

Use these rules when deciding whether a Hermes command belongs in Ubuntu
Zombie:

- Prefer deterministic UI/API actions over prompts sent back through the
  model. A slash command should not spend tokens unless its job is to ask
  the agent to reason.
- Keep the closed tool registry as the security boundary. A command that
  mutates the host must be backed by a typed tool, classified by
  `policy.py`, and audited before and after execution.
- Keep the chat surface local. Do not add platform handoff, public upload,
  shareable debug links, or gateway administration commands.
- Avoid modes that weaken human review. More autonomy is acceptable only
  when the plan, policy class, approvals, and audit trail become clearer.
- Make common operations discoverable before adding broad new capability.
  Aliases, history search, export, copy, skill preview, policy display, and
  snapshots are higher leverage than cosmetic skins or platform controls.

## Current implementation baseline

Ubuntu Zombie now implements the full "Ship or keep now" set in the web
chat UI:

- Discovery and local view control: `/help`, `/commands`, `/clear`,
  `/redraw`, `/new`, `/reset`, `/examples`, `/shortcuts`, and `/stop`.
- Conversation navigation: `/conversations`, `/history`, `/sessions`,
  `/load <id>`, and `/resume <id>`.
- Conversation state controls: `/title <text>`, `/branch [name]`,
  `/retry`, `/undo [n]`, and `/compress`.
- Local transcript utilities: `/export`, `/save`, and `/copy [n]`.
- Runtime/status inspection: `/tools`, `/skills [name]`, `/health`,
  `/status`, `/version`, `/model [id]`, `/config`, `/policy`,
  `/whoami`, `/profile`, and `/audit`.
- Approval queue controls: `/approve [id] [phrase]` and `/deny [id]`.

The backend exposes only the local state needed to support those
commands: `/api/health`, `/api/version`, `/api/conversations`,
`/api/conversation/{id}`, `/api/audit`, `/api/tools`, `/api/models`,
`/api/config`, `/api/profile`, `/api/whoami`, `/api/policy`,
`/api/skills`, `/api/skill/{name}`, and `/api/pending`.
State-changing command support is scoped to conversation
metadata/history and the existing approval queue: `POST /api/model`,
`POST /api/approve`, and
`POST /api/conversation/{id}/{title,branch,retry,undo,compress}`.

This keeps the implementation aligned with the selection rules: no
slash command adds a new privileged host action, `/retry` is the only
one that intentionally spends model tokens, `/undo` rewinds only the
conversation branch, and `/compress` stores a summary without deleting
raw SQLite history or audit entries.

## Recommended command set

### Ship or keep now

These commands either already exist or can be implemented with browser
state, SQLite conversation state, or existing read-only APIs. They do not
need new privileged host capability.

| Command | Recommendation | Ubuntu Zombie shape |
| --- | --- | --- |
| `/help` | Keep. | Current command list. Eventually back it with `/commands`. |
| `/commands` | Add. | Searchable/paginated command palette over the same registry as `/help`. |
| `/clear` | Keep. | Browser-only transcript clear; does not delete history. |
| `/redraw` | Add as alias. | Re-render current transcript from SQLite, or reload the current conversation. |
| `/new` | Keep. | Starts a fresh conversation. Preserve `/reset` as local alias. |
| `/history` | Keep alias. | Current alias for `/conversations`. |
| `/sessions` | Add alias. | Same as `/conversations`; Hermes users expect this word. |
| `/resume <id>` | Add alias. | Same as `/load <id>`. |
| `/save` | Add as `/export`. | Download current transcript as Markdown and JSON. `/save` can alias it. |
| `/title <text>` | Add. | Update the SQLite conversation title through a small API endpoint. |
| `/copy [n]` | Add. | Browser Clipboard API copy of the last assistant response, or response `n`. |
| `/retry` | Add. | Re-send the last user message after removing the last assistant turn/events from display; backend should preserve an audit-visible retry marker. |
| `/undo [n]` | Add carefully. | Conversation-only rewind; never undo host side effects. Must say that host changes remain real. |
| `/branch [name]` | Add after title/export. | Copy messages/events up to current point into a new conversation. |
| `/compress` | Add. | Create a conversation summary for future context, but never delete raw SQLite history or audit entries. |
| `/status` | Keep. | Compact host/provider status. |
| `/version` | Keep. | Ubuntu Zombie and bridge versions. |
| `/model [id]` | Keep. | Existing provider catalogue and process-local model selection. |
| `/tools` | Keep. | Current closed tool registry display. |
| `/skills [name]` | Add. | List skills and preview a skill body via existing `skill.list`/`skill.load`; do not install skills from chat. |
| `/config` | Add. | Read-only, redacted runtime summary: host, provider name/model, policy path, history DB path, chat port, skill dirs. |
| `/policy` | Add, Ubuntu-specific. | Show action classes, confirmation phrase presence, tool overrides, and rule count. Avoid dumping secrets; policy is not secret. |
| `/whoami` | Add. | Show effective agent user, hostname, browser access path, and whether the service is loopback. |
| `/profile` | Add. | Similar to `/whoami`, plus `ZOMBIE_DIR` and conversation DB path. No secrets. |
| `/stop` | Keep. | Cancel the in-flight browser request. Later, pair with server-side turn cancellation. |
| `/approve` | Add after approval queue API polish. | Text alternative to clicking approve for the single pending action, with phrase prompt when required. |
| `/deny` | Add after approval queue API polish. | Text alternative to clicking deny for the single pending action. |

### Ship after backend support

These commands fit Ubuntu Zombie, but only after the server has explicit
state, typed tools, or audit support. They should not be implemented as
ad hoc shell from the slash-command parser.

| Command | Recommendation | Required shape |
| --- | --- | --- |
| `/snapshot` | Add. | Snapshot conversations DB plus files touched by approved changes. For host config, make this a typed tool or installer helper, not a raw tar of the whole system. |
| `/rollback` | Add. | Restore only known snapshots with clear diff/metadata and policy/audit. Never imply package-manager or whole-disk rollback unless implemented. |
| `/usage` | Add when usage data exists. | Tokens, estimated cost, model, and turn counts per conversation. Must tolerate providers that do not return usage. |
| `/insights [days]` | Add later. | Local analytics from SQLite/audit log: tool counts, approvals, failures, cost. No upload. |
| `/memory` | Add only as curated machine facts. | Operator-visible durable facts, review/approve/reject workflow, audit every write. Do not silently learn secrets. |
| `/goal` and `/subgoal` | Defer, scoped. | Accept only per-conversation goals unless scheduled-task support exists. No autonomous standing work by default. |
| `/busy` | Add after queue/streaming work. | Let Enter queue, steer, or interrupt while a turn is active. Default should stay conservative. |
| `/queue` | Add after request queue exists. | Queue the next prompt locally/server-side; show it visibly and allow removal. |
| `/steer` | Add after live tool timeline exists. | Inject operator guidance into the current turn, audited as an operator message. |
| `/background` | Defer. | Requires an explicit background job model, cancellation, status, and audit. Useful for long diagnostics, risky for autonomous mutation. |
| `/agents` | Rename if added. | Show background jobs and running turns, not multiple autonomous agents. |
| `/cron` | Add only through typed tools. | Promote a reviewed operation into a systemd timer. Requires schema, policy class, audit, and uninstall/disable path. |
| `/browser` | Defer to a typed browser tool. | Ubuntu Zombie has desktop automation; CDP/Playwright control should be a closed tool, not a free-form connection command. |
| `/paste` | Add as attachment support. | Accept pasted files/images into `/opt/ai-zombie/state` or `/tmp` with size limits and visible provenance. |
| `/image <path>` | Add as attachment support. | Upload/attach operator-selected files; do not let the browser ask the server to read arbitrary paths. |
| `/reload` | Add narrowly. | Re-read `secrets/env` and provider status without service restart, after permission checks; log a reload event. |
| `/reload-skills` | Add as status/no-op. | Skills are already scanned from disk when needed; command can show the current catalogue and note that no restart is needed. |
| `/verbose` | Add as UI preference. | Toggle display of tool details already present in history/audit. Do not expose hidden chain-of-thought. |
| `/reasoning` | Add only as model option/status. | Show or set provider-supported reasoning effort if the provider supports it. Do not display private reasoning traces. |
| `/statusbar` | Add. | Toggle the existing provider/status banner density. |
| `/footer` | Add. | Toggle local runtime metadata such as model, tool budget, and turn duration. |

### Do not implement

These commands are poor fits for Ubuntu Zombie's trust model or product
scope.

| Command | Verdict | Reason |
| --- | --- | --- |
| `/start` | Reject. | Platform ping for Telegram-style bots; no value in loopback web chat. |
| `/topic` | Reject. | Telegram DM topic routing is out of scope. |
| `/handoff` | Reject. | Cross-platform handoff conflicts with the local-only interface. |
| `/sethome` | Reject. | Home channel concept belongs to a gateway, not one local chat. |
| `/platforms`, `/platform` | Reject. | Gateway platform administration is out of scope. |
| `/restart` | Reject as slash command. | Restarting the chat service can be done through the agent with `svc.control` and policy/audit when needed. A local slash command should not kill its own UI. |
| `/codex-runtime` | Reject. | Codex-specific runtime switch, unrelated to Ubuntu Zombie. |
| `/gquota` | Reject. | Gemini Code Assist-specific quota, not provider-neutral. |
| `/personality` | Reject. | The AI Systems Administrator persona should be stable for safety and auditability. |
| `/yolo` | Reject strongly. | A one-command approval bypass contradicts the core policy gate. |
| `/fast` | Reject/defer. | Provider priority modes are vendor-specific and cost-sensitive; expose model/provider config instead. |
| `/skin`, `/indicator` | Reject for now. | Cosmetic terminal affordances; not worth product surface before operational commands. |
| `/voice` | Reject for MVP. | Adds privacy, dependency, and UX complexity outside the sysadmin loop. |
| `/toolsets` | Reject. | Runtime toolset switching conflicts with the closed registry model. |
| `/bundles` | Reject. | Skill bundles imply install/curation machinery that Ubuntu Zombie does not have. |
| `/curator` | Reject. | Background skill maintenance is unnecessary and risky for a small root-capable system. |
| `/kanban` | Reject. | Multi-profile collaboration board is outside one-machine administration. |
| `/reload-mcp` | Reject. | Ubuntu Zombie does not expose runtime MCP servers; tools require code release. |
| `/plugins` | Reject. | Runtime plugin listing/enablement conflicts with the closed tool surface. |
| `/update` | Reject. | Self-upgrade is an explicit non-goal; upgrades stay `git pull` plus `install`, or package-manager driven. |
| `/debug` | Reject as upload. | Local diagnostics are useful; automatic upload/shareable links are not compatible with local-only trust. Use `collect-diagnostics`. |
| `/quit` | Reject for web UI. | Closing a browser tab is enough; deleting history should be a separate explicit command if ever added. |

## Keyboard and input affordances

These are not slash commands, but they are worth borrowing because they
make the chat feel like an operations console without expanding
privilege.

### Should implement

- Up/down prompt history, with prefix-filtered recall.
- Reverse search over prior prompts, either `Ctrl-R` or a command-palette
  search box.
- Slash-command autocomplete and fuzzy filtering.
- Autocomplete for skill names and conversation ids.
- Native multiline input stays as-is: Enter sends, Shift+Enter inserts a
  newline.
- `Esc` should close palettes or cancel an in-progress edit.
- PageUp/PageDown transcript scrolling should remain native.
- Markdown rendering is already present and should stay.

### Implement only with guardrails

- `@path` mention can be useful, but the browser cannot safely enumerate
  arbitrary server paths. If added, path suggestions must come from a
  read-only, allow-listed server endpoint and should attach the path as
  operator context rather than bypassing `fs.read`.
- `! command` should not be a quick bypass. If added, it must create a
  normal `shell.run` proposal that goes through schema validation,
  classification, approval, execution, and audit. It is lower priority
  than plain-language admin requests.
- `# note` should wait for the curated memory store. Notes must be visible,
  editable, and audited; they must not silently persist secrets.
- Custom aliases should wait until command export/history is mature. Stored
  command chains become automation and need provenance.

### Should not implement

- `$VAR` or `${VAR}` prompt expansion from `secrets/env`. Ubuntu Zombie's
  environment contains provider keys and other sensitive values. Use
  `/config` for redacted non-secret state instead.
- Intercepting common browser shortcuts such as `Ctrl-C` and `Ctrl-L`.
  Keep `/stop` and `/clear` explicit in the web UI.

## Proposed implementation order

1. Done: normalize the command surface with `/commands`, `/sessions`,
   `/resume`, `/save`/`/export`, `/copy`, `/title`, `/whoami`,
   `/profile`, `/config`, `/skills`, and `/policy`.
2. Add browser ergonomics: prompt history, prefix recall, command palette,
   and autocomplete for commands, skills, and conversations.
3. Done: add conversation controls: `/retry`, `/undo`, `/branch`, and
   transcript export with a clear warning that host side effects are not
   undone.
4. Add observability commands: richer `/audit`, `/usage`, `/insights`,
   visible budgets, and UI toggles for status/footer/verbosity.
5. Add safety-backed operations: `/snapshot`, `/rollback`, `/approve`,
   `/deny`, attachments, and eventually `/cron`, each through typed tools
   or explicit audited server state.
6. Revisit queued/background work only after streaming and live tool
   timelines exist. Without live visibility, background autonomy is too
   easy to misunderstand.

## Short selected list

The high-confidence set Ubuntu Zombie should grow toward is:

`/commands`, `/help`, `/clear`, `/redraw`, `/new`, `/history`,
`/conversations`, `/sessions`, `/load`, `/resume`, `/save`, `/export`,
`/copy`, `/title`, `/retry`, `/undo`, `/branch`, `/status`, `/version`,
`/model`, `/tools`, `/skills`, `/config`, `/policy`, `/whoami`,
`/profile`, `/audit`, `/usage`, `/insights`, `/snapshot`, `/rollback`,
`/approve`, `/deny`, `/stop`, `/busy`, `/queue`, `/steer`, `/memory`,
`/paste`, `/image`, `/reload`, `/reload-skills`, `/verbose`,
`/reasoning`, `/statusbar`, and `/footer`.

Of those, the first command implementation tranche is now implemented:
`/commands`, `/sessions`, `/resume`, `/export`, `/copy`, `/title`,
`/skills`, `/config`, `/policy`, `/whoami`, and `/profile`. Prompt
history and autocomplete remain browser ergonomics, not slash-command
capabilities, and should be implemented separately.
