# Ubuntu Zombie improvements 1 — reanalysis

Last reanalysed: 2026-07-04.

This document rechecks the issues previously raised in this file against
this checkout of the repository. It is written for an AI coding agent
starting from a fresh checkout and should be treated as an implementation
backlog, not as a record of completed work.

Before changing code, read:

- `AGENTS.md`
- `README.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`

Do not run `make install-local`, `scripts/install.sh install`,
`scripts/install.sh repair`, or `scripts/uninstall.sh` on the current
workstation. Those commands mutate users, sudoers, services, package
state, and systemd state. Use only non-root tests unless the user
explicitly provides a disposable Ubuntu Desktop LTS VM.

After shell or Python changes, run:

```bash
make lint
make test
```

If the local environment cannot run those commands, say exactly why.
Documentation-only changes do not need to run the installer or the
host-mutating commands above.

## Executive summary

The original analysis was directionally right but several items are now
stale. The current install is much smaller than the older analysis
assumed: `scripts/install.sh` no longer provisions SSH, Tailscale, VNC,
Docker, GUI automation, autologin, UFW, or fail2ban by default. The
remaining serious gap is narrower and more important:

1. The pi-mono production bridge still lets pi execute its own built-in
   host tools (`read`, `bash`, `edit`, `write`, `grep`, `find`, `ls`) in
   `--mode json`; Python logs those events diagnostically but does not
   mediate them through `tools.py`, `policy.py`, approvals, or audit
   before execution.
2. The effective policy loaded by `policy.py` is conservative because the
   minimal YAML loader falls back to code defaults when it encounters the
   shipped list blocks, but the text in `payload/etc/policy.yaml` still
   says `default_class: system_change` and marks `user_change`,
   `system_change`, and `network_change` as `approval: auto`. That is a
   dangerous mismatch between file contents and runtime behavior.
3. The system prompt and some docs now honestly describe the current
   pi-built-in tool path, while other docs still describe the intended
   closed Python registry as if it were the only execution path. This
   contradiction must be resolved before adding more capabilities.
4. The standing privilege model remains passwordless sudo for the
   `zombie` account. Docker root-equivalence and broad inbound SSH are no
   longer default issues, but passwordless sudo is still root-equivalent.

## Status of the original issues

- **Closed tool and policy boundary — P0, still open.** The production
  bridge intentionally enables pi built-ins and does not turn
  `tool_execution_*` events into Python-mediated `tool_call` frames.
- **Safe shipped policy defaults — P0, partially effective but still
  defective.** Runtime defaults are conservative; the YAML file text
  remains permissive and is being masked by parser fallback.
- **Reduce root-equivalent privilege exposure — P1, still open.**
  Passwordless sudo remains; Docker group membership is obsolete in the
  default installer.
- **Action previews before approval — P1, still open.** Audit
  stdout/stderr previews are not approval previews.
- **Filesystem read/write boundaries — P1, still open.** The Python
  registry path needs sensitive-path denial, and pi built-ins currently
  bypass those boundaries.
- **Real Ubuntu VM integration tests — P1, still open.** The installer
  still lacks guarded disposable-VM coverage.
- **Operator approval UI — P2, partially present.** Pending actions and
  approve/deny exist, but evidence and client-side phrase handling are
  weak.
- **Network exposure safer by default — closed/watch.** Default install is
  loopback-only and does not configure SSH, Tailscale, VNC, Docker, GUI
  automation, or a firewall. Keep this invariant.
- **Align names/docs/state — P2, partially resolved.** Default `zombie` is
  documented in several files, but `SECURITY.md` and some analysis docs
  still say `agent` for the account identity.
- **First-class read-only web fetch — P2, still open.** Wait until the
  bridge boundary is fixed.
- **Audit and evidence — P3, partially improved.** Structured audit and
  optional redacted stdout/stderr previews exist; classification evidence
  fields are still missing.

## P0: make the execution boundary true or document the bypass

### Current state

The intended architecture is still a closed Python tool registry:

- `payload/agent/tools.py` defines `TOOL_REGISTRY`, validates schemas,
  and dispatches typed shims.
- `payload/agent/server.py` calls `tools.validate_args`,
  `policy.classify_tool`, queues approvals when required, dispatches
  auto-approved calls, and audit-logs decisions.
- `payload/agent/pi_mono.py` still documents a bridge protocol with
  `tool_call` frames from the bridge and `tool_result` frames from
  Python.

The production bridge does not currently use that path for real pi tools.
`payload/agent/pi-mono-bridge.mjs` starts `pi --mode json -p` with:

```js
const PI_BUILTIN_TOOLS = ["read", "bash", "edit", "write", "grep", "find", "ls"];
```

When pi emits `tool_execution_start` or `tool_execution_end`, the bridge
logs those events as diagnostics only. It does not convert them into
logical tool calls such as `shell.run` or `fs.read`, and Python does not
approve them before execution. The smoke test currently locks in that
behavior: the `on_tool_call` callback must not fire for the fake
production bridge, and `tool_execution_*` events must not be surfaced as
mediated `tool_call` frames.

The prompt templates also reflect the current bypass. They tell the model
that it can act with pi built-ins (`read`, `ls`, `write`, `edit`,
`grep`, `find`, `bash`) rather than the logical Python registry names.

### Desired behavior

Choose one product position and make code, tests, and docs agree:

1. **Preferred:** every host action initiated by the model is mediated by
   Python before execution.
2. **Fallback:** pi built-ins stay enabled, but docs and security copy say
   plainly that those actions bypass Python policy/approval/audit until
   the bridge is replaced.

The preferred position should restore this invariant:

1. The model emits a logical tool call.
2. Python validates it with `tools.validate_args`.
3. Python classifies it with `policy.classify_tool`.
4. Read-only calls may auto-run.
5. Elevated calls are queued for approval.
6. Phrase-gated calls require the configured phrase.
7. Python dispatches the call only after the gate allows it.
8. Python records proposed, queued, approved, executed, denied, and
   errored decisions in `audit.log`.
9. Tool observations are returned to the model.

No model-visible host tool should bypass that path.

### Implementation notes

Investigate whether the pinned `@earendil-works/pi-coding-agent` version
can be driven in an RPC mode that accepts external tool results. If it
can, replace the current `--mode json`/built-in flow with a bridge that
maps pi tool calls to Python logical tools and writes Python results back
to pi.

If the pinned pi protocol cannot support externally-dispatched tools
cleanly, do not keep a silent bypass. Disable host tools in production or
keep the assistant in explanation-only mode until a mediated tool path
exists.

### Files likely to change

- `payload/agent/pi-mono-bridge.mjs`
- `payload/agent/pi_mono.py`
- `payload/agent/server.py`
- `payload/agent/templates/APPEND_SYSTEM.md.tmpl`
- `payload/agent/templates/settings.json.tmpl`
- `tests/fixtures/fake-pi-json.mjs`
- `tests/fixtures/stub-pi-mono.mjs`
- `tests/smoke.sh`
- `tests/python/`
- `docs/ARCHITECTURE.md`
- `docs/INTERNET-ACCESS.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Tests to add or change

- A regression test that fails if the production bridge enables pi
  built-in host tools without Python mediation.
- A server-level test where a stub emits `shell.run` for an elevated
  command and `tools.dispatch` is not called before approval.
- An audit test that queued/executed tool calls include matching
  `tool_call` audit entries with decisions.
- A bridge protocol test that verifies Python returns observations to the
  model before the model continues.

### Acceptance criteria

- No shell, file edit, package, service, network, or skill action can run
  unless Python dispatches it, or the product explicitly documents that
  pi built-ins are an insecure compatibility limitation.
- Tests fail if direct pi built-in host execution is reintroduced under a
  supposedly Python-mediated mode.
- Prompt text, architecture docs, and security docs describe the same
  execution path that the code actually uses.

## P0: align the shipped policy file, parser, tests, and docs

### Current state

The text of `payload/etc/policy.yaml` still contains permissive-looking
values:

```yaml
settings:
  default_class: system_change

classes:
  read_only:
    approval: auto
  user_change:
    approval: auto
  system_change:
    approval: auto
  network_change:
    approval: auto
    confirm_phrase: true
  destructive:
    approval: required
    confirm_phrase: true

agent:
  max_tool_calls_per_turn: 128
  max_elevated_calls_per_turn: 32
  max_turn_seconds: 600
```

However, loading that file with `ZOMBIE_POLICY=payload/etc/policy.yaml`
currently yields conservative effective values:

- `default_class == "destructive"`
- `user_change`, `system_change`, `network_change`, and `destructive`
  require approval
- budgets are `12`, `3`, and `600`

This happens because the minimal YAML loader raises on list blocks such
as `sudo_allow_list:` and falls back to code defaults for `settings`,
`classes`, and `agent`; rules and the sudo allow-list are then recovered
with text-specific extractors. The tests assert the conservative effective
values, but the shipped file text still communicates the opposite.

That is unsafe because a future parser fix could suddenly make the
permissive text effective.

### Desired behavior

Make all four layers agree:

1. `payload/etc/policy.yaml` text is conservative.
2. `policy.py` parses the shipped policy deterministically.
3. Tests assert both effective values and key file contents.
4. Docs describe the shipped behavior, not accidental fallback behavior.

Recommended shipped defaults:

```yaml
settings:
  default_class: destructive

classes:
  read_only:
    approval: auto
    description: Diagnostics and inspection only.
  user_change:
    approval: required
    description: Changes within the agent account's home directory or user-owned files.
  system_change:
    approval: required
    description: Package, service, file, or privileged mutation.
  network_change:
    approval: required
    confirm_phrase: true
    description: Firewall, interface, sshd, or remote-access mutation.
  destructive:
    approval: required
    confirm_phrase: true
    description: Irreversible mutation. Requires confirmation phrase.

agent:
  max_tool_calls_per_turn: 12
  max_elevated_calls_per_turn: 3
  max_turn_seconds: 600
```

### Files likely to change

- `payload/etc/policy.yaml`
- `payload/agent/policy.py`
- `tests/smoke.sh`
- `tests/python/test_policy.py`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `docs/INTERNET-ACCESS.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Tests to add or adjust

- Parse the shipped YAML and assert the effective values above.
- Assert the shipped file text does not contain permissive defaults for
  `default_class`, `system_change`, `network_change`, or budgets.
- Add a parser regression for list-containing YAML so `settings`,
  `classes`, `agent`, `rules`, `sudo_allow_list`, and `tool_classes` can
  coexist without silent fallback.
- Keep existing fail-closed tests for unknown commands and tools.

### Acceptance criteria

- A parser improvement cannot accidentally activate permissive defaults.
- Unknown commands and unknown tools require approval by default.
- Only read-only actions auto-run by default.
- Docs and tests match the effective policy.

## P1: reduce standing sudo exposure

### Current state

The installer creates the configurable account `ZOMBIE_USER` (default
`zombie`), adds it to `sudo`, and writes a sudoers drop-in granting:

```text
<user> ALL=(ALL) NOPASSWD:ALL
```

This is intentional for the MVP but root-equivalent. The older concern
that the user is also added to the Docker group is stale: the current
installer does not install Docker or add Docker group membership by
default.

### Desired direction

Keep the product promise that the AI can administer the machine, but
make broad passwordless sudo a compatibility mode rather than the only
mode.

Recommended staged approach:

1. Keep `NOPASSWD: ALL` as explicit `compat` mode.
2. Add a `strict` mode with a narrow privileged helper or allow-list.
3. Move common privileged actions into typed tools where possible.
4. Keep Docker absent from the default install; if Docker support returns,
   make it opt-in and document root equivalence.

### Files likely to change

- `scripts/install.sh`
- `scripts/uninstall.sh`
- generated verify helper in `scripts/install.sh`
- `payload/bin/health-check` if privilege checks move there
- `payload/agent/tools.py` if typed privileged tools change
- `docs/CONFIGURATION.md`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `README.md`
- `tests/smoke.sh`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Operators can select a stricter privilege posture at install time.
- The default is either stricter, or `compat` is explicitly justified in
  the installer and security docs.
- Docker remains off by default unless deliberately reintroduced as an
  opt-in root-equivalent feature.

## P1: add approval previews for elevated actions

### Current state

The approval flow queues elevated actions and exposes pending calls, but
it does not compute a safe impact preview before approval. Audit has an
optional verbose stdout/stderr preview mode, but that is post-execution
output evidence, not a pre-approval preview of what will change.

### Desired behavior

Before approval, expose a bounded, redacted preview where safe:

- file writes: target path, old hash, new hash, and unified diff;
- package installs/removals: `apt-get --simulate` output;
- service control: current state and requested action;
- network changes: current state and proposed mutation;
- destructive actions: touched path/device summary, or no preview if
  previewing would itself be risky.

If no safe preview exists, return:

```json
{"available": false, "reason": "..."}
```

### Files likely to change

- `payload/agent/server.py`
- `payload/agent/tools.py` or a new `payload/agent/previews.py`
- `payload/agent/templates/index.html`
- `payload/agent/audit.py` if preview redaction needs extra coverage
- `tests/python/`
- `tests/smoke.sh`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Pending approval prompts show enough evidence for a real decision.
- Preview generation does not mutate host state.
- Preview output is bounded and redacted.

## P1: tighten filesystem boundaries

### Current state

The Python registry path allows `fs.read` and `fs.list` under:

- `${ZOMBIE_DIR}/state`
- `/etc`
- `/var/log`
- `/proc`
- `/sys`
- `/usr/share/doc`

It allows `fs.write` under:

- `${ZOMBIE_DIR}/state`
- `/tmp`

The path check resolves paths before testing allow-list membership, which
is good. There is still no deny-list for obvious sensitive files such as
`/etc/shadow`, `/etc/sudoers.d`, host SSH private keys,
`/proc/*/environ`, or `/opt/ai-zombie/secrets`.

This only protects the Python `fs.*` tools. While pi built-ins remain
enabled, pi's `read`, `grep`, `find`, `bash`, `write`, and `edit` can
still bypass these boundaries.

### Desired behavior

After resolving the path, reject sensitive exact paths and prefixes.
Start with:

- `/etc/shadow`
- `/etc/gshadow`
- `/etc/sudoers`
- `/etc/sudoers.d`
- `/etc/ssh/ssh_host_*_key`
- `/etc/NetworkManager/system-connections`
- `/proc/*/environ`
- `/opt/ai-zombie/secrets`
- any path configured by `ZOMBIE_SECRETS`

Consider redaction or approval-gated access for sensitive diagnostics
such as `/var/log/auth.log` and `/proc/*/cmdline`.

### Files likely to change

- `payload/agent/tools.py`
- `payload/agent/audit.py` if new redaction is needed
- `payload/bin/collect-diagnostics`
- `tests/python/test_tools.py`
- `tests/smoke.sh`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Python `fs.read` and `fs.list` cannot read obvious local secrets.
- Denials use resolved paths so symlinks cannot bypass the deny-list.
- Docs explain what local state the model/provider may see.
- The bridge bypass is fixed or explicitly documented as bypassing this
  protection.

## P1: add real disposable-VM integration tests

### Current state

The repository has useful non-root smoke tests and Python unit tests, but
real installer behavior is host-mutating and still lacks disposable VM
coverage.

### Desired coverage

A guarded integration harness should verify at least:

1. `install --dry-run`
2. non-interactive install with generated placeholder inputs
3. re-run install for idempotence
4. `verify`
5. `doctor`
6. `repair`
7. chat service binds only to loopback
8. secrets permission failure causes service refusal
9. policy blocks elevated action before approval
10. uninstall with archive on a disposable host

The runner must refuse to mutate a normal workstation unless an explicit
marker is present, for example:

```bash
ZOMBIE_INTEGRATION_ALLOW_HOST_MUTATION=I_AM_IN_A_DISPOSABLE_VM
```

### Files likely to change

- `.github/workflows/integration.yml`
- `scripts/integration-vm.sh` or `tests/integration/*`
- `docs/PLATFORMS.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Maintainers have a repeatable way to test real installer behavior.
- The harness cannot accidentally run destructive install steps on a
  normal workstation.
- Idempotence is verified by running install twice.

## P2: improve the operator approval UI

### Current state

`payload/agent/templates/index.html` renders pending calls and provides
Approve and Deny buttons. The server enforces the confirmation phrase on
approval, and slash commands can approve or deny pending calls.

The UI still does not show enough decision evidence. It does not render a
pre-approval preview, touched paths, audit id, matched policy rule, sudo
involvement, or a compact structured summary of risk. The approve button
is not disabled until the phrase is correct; phrase mistakes are caught
only after submission.

### Desired behavior

For each pending action, show:

- tool name;
- classification;
- matched policy rule or tool default;
- whether sudo/root is involved;
- structured args or normalized argv;
- preview output;
- touched paths;
- audit id and tool-call id;
- exact phrase when required;
- deny button;
- approve button disabled until a required phrase matches.

### Files likely to change

- `payload/agent/templates/index.html`
- `payload/agent/server.py`
- `docs/ARCHITECTURE.md`
- `tests/smoke.sh`
- optional browser/UI tests if a harness is added
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Operators can understand what they are approving without reading raw
  logs.
- The approve button cannot accidentally submit phrase-gated actions.
- Existing `/approve` and `/deny` commands still work.

## Closed/watch: preserve the safer default network footprint

### Current state

The older analysis assumed SSH ingress, Tailscale, VNC, UFW, and related
remote-access services were part of the default install. They are not in
this checkout.

`docs/ARCHITECTURE.md` and `SECURITY.md` say the default install does not
provision SSH, Tailscale, VNC, Docker, a configured firewall, or GUI
automation, and `scripts/install.sh` does not include those package or
configuration steps. The only intended access surface is the chat service
on `127.0.0.1:${ZOMBIE_CHAT_PORT:-7878}`.

### Recommendation

Do not implement the older `ZOMBIE_ENABLE_SSH_INGRESS` work as a P2
safety fix unless SSH provisioning is deliberately reintroduced. Instead,
add tests or documentation guards that preserve the loopback-only default.

### Acceptance criteria

- Default install remains loopback-only.
- Any future remote-access feature is explicit opt-in and documented as a
  new exposure.
- `verify`, `doctor`, and `repair` do not imply that broad SSH ingress is
  expected by default.

## P2: align account naming in remaining docs

### Current state

The installer and primary user docs have largely moved to the default
Linux account name `zombie` with `ZOMBIE_USER` as the configuration
variable and `AGENT_USER` as a legacy alias. Remaining stale text exists,
notably in `SECURITY.md`, which still says the operating identity is
`agent` and refers to removing the `agent` user.

Some analysis documents, such as `docs/analysis/ubuntu-zombie-zero.md`,
also still use `agent` for account-identity text. Historical research
under `docs/research/` can remain as-is unless it is actively presented
as current product documentation.

### Desired behavior

Use one canonical account model:

- product role: AI Systems Administrator;
- default Linux account: `zombie`;
- configurable env var: `ZOMBIE_USER`;
- legacy alias: `AGENT_USER`, documented only for backward compatibility.

Keep the word "agent" when it refers to the AI concept, Python package,
or general runtime role. Change only account-identity text.

### Files likely to change

- `SECURITY.md`
- `docs/analysis/ubuntu-zombie-zero.md` if still considered current
- targeted references in `README.md`, `docs/`, `CONTRIBUTING.md`,
  `payload/`, `scripts/`, and `tests/`

### Acceptance criteria

- A new reader does not need to reconcile `agent` vs `zombie` as the
  default account name.
- Backward-compatible `AGENT_USER` behavior remains documented.

## P2: add first-class read-only web fetch after P0

### Current state

There is no `web.fetch` tool in `payload/agent/tools.py`. Outbound
networking is available and `curl`/`wget` are installed, but web access is
only available through shell/pi built-ins. `docs/INTERNET-ACCESS.md`
still contains stale statements about `default_class: system_change` and
about the pi-built-in path; revise it when web fetch work begins.

### Desired behavior

After the bridge boundary is fixed, add a typed read-only tool:

```text
web.fetch
```

Arguments:

- `url`: string, required;
- `max_bytes`: integer, optional, default bounded value;
- `timeout`: integer, optional, default bounded value;
- `headers`: object, optional, allow only safe request headers.

Restrictions:

- only `http` and `https`;
- no request body;
- no POST/PUT/PATCH/DELETE;
- deny loopback, link-local, private RFC1918, and cloud metadata targets
  by default;
- follow redirects only within safe schemes;
- cap and redact response bodies before audit/history.

### Files likely to change

- `payload/agent/tools.py`
- `payload/agent/templates/APPEND_SYSTEM.md.tmpl`
- `payload/agent/skills/web.md`
- `payload/etc/policy.yaml`
- `tests/smoke.sh`
- `tests/python/test_web_fetch.py`
- `docs/INTERNET-ACCESS.md`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- The assistant can fetch public web pages for read-only lookups.
- Fetches are audit-visible as `web.fetch`.
- Fetch cannot read local files, send request bodies, or reach local and
  private network targets by default.
- `curl ... | bash` remains gated as an elevated or destructive action.

## P3: strengthen audit and evidence

### Current state

Audit logging records structured events and redacts obvious secrets.
Verbose mode can attach redacted stdout/stderr previews. The audit log
still does not explain why a classification was chosen.

### Improvements

Add bounded fields such as:

- policy rule id or pattern that determined classification;
- tool schema version;
- preview hash;
- working directory;
- effective user;
- whether sudo was present;
- parent conversation id and message id;
- bridge version and provider/model per turn;
- normalized argv separately from rendered shell.

Avoid storing full stdout/stderr by default.

### Files likely to change

- `payload/agent/audit.py`
- `payload/agent/policy.py`
- `payload/agent/server.py`
- `payload/agent/runner.py`
- `payload/bin/audit-recent`
- `tests/python/`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`

### Acceptance criteria

- An operator can answer "why was this classified this way?"
- Audit entries remain bounded and redacted.
- Existing audit readers tolerate new fields.

## Suggested implementation order

Implement in this order:

1. Fix or explicitly disable/document the pi built-in bridge bypass.
2. Align `payload/etc/policy.yaml`, the YAML parser, tests, and docs.
3. Update prompt templates and architecture/security docs to match the
   real execution path.
4. Add filesystem sensitive-path denials on the Python registry path.
5. Add approval previews.
6. Improve approval UI evidence.
7. Add stricter privilege mode or a privileged helper.
8. Add disposable-VM integration tests.
9. Finish account-name doc alignment.
10. Add `web.fetch` safely.
11. Add audit classification evidence fields.

Do not combine all items in one large pull request. The first PR should
focus only on making the execution boundary and policy defaults true,
tested, and documented.

## Definition of done for the first implementation PR

The first implementation PR should be considered complete when:

- pi cannot execute host tools outside Python mediation, or host tools are
  disabled and the limitation is documented;
- `payload/etc/policy.yaml` text is conservative and matches effective
  runtime behavior;
- `make lint` passes;
- `make test` passes;
- tests fail if elevated actions auto-dispatch under the shipped policy;
- tests fail if the production bridge reintroduces unmediated host tool
  execution under the claimed closed-registry mode;
- `docs/ARCHITECTURE.md`, `SECURITY.md`, `docs/CONFIGURATION.md`, and
  `docs/INTERNET-ACCESS.md` match the implemented behavior;
- `CHANGELOG.md` records the user-visible safety change;
- `VERSION` is bumped if `CHANGELOG.md` is updated, using:

```bash
date -u +%Y.%m.%d.%H.%M.%S > VERSION
```
