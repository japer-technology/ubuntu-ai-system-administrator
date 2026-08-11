# Ubuntu Zombie improvements 2 — all-powerful pi plan

Last reanalyzed: 2026-07-04.

This document supersedes `docs/analysis/improvements-1.md` as the next
implementation backlog. It intentionally changes the product direction:
Ubuntu Zombie should stop pretending to be a small, closed, narrowly
mediated assistant. The true product is a private, root-capable AI Systems
Administrator whose `pi` runtime can operate the machine, inspect the web,
and leave a durable trail of what it did.

The goal is not to make Ubuntu Zombie quiet or weak. The goal is to make it
**honestly powerful**: broad capability, explicit operator control, and
strong evidence after every action.

Before changing code, read:

- `AGENTS.md`
- `README.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `docs/INTERNET-ACCESS.md`

Do not run `make install-local`, `scripts/install.sh install`,
`scripts/install.sh repair`, `scripts/uninstall.sh`, or installed helpers
from `/opt/ai-zombie/` on the current workstation. Those commands mutate
users, sudoers, services, package state, and systemd state. Use only
non-root tests unless the user explicitly provides a disposable Ubuntu
Desktop LTS VM.

After shell or Python changes, run:

```bash
make lint
make test
```

If `CHANGELOG.md` is updated for user-visible changes, also update
`VERSION` with:

```bash
date -u +%Y.%m.%d.%H.%M.%S > VERSION
```

## Executive summary

`improvements-1.md` treated the pi built-in tool path as a gap to close.
This plan treats it as the product direction to make true, documented, and
observable.

The current checkout already gives pi meaningful host power through the
production bridge: `read`, `bash`, `edit`, `write`, `grep`, `find`, and
`ls`. The installed Linux account also has passwordless `sudo`, and the
service has outbound network access. That is the zombie's real nature: it
is not merely a chat UI with a few safe shims; it is an administrator with
hands.

The next work should therefore prioritize:

1. **Make pi openly all-powerful.** Document that pi can use broad host
   tools and root-equivalent sudo as the core capability, not as an
   accidental bypass.
2. **Give pi first-class web access.** Add a typed, auditable read-only web
   fetch path and update prompts/docs so the assistant knows the web is
   available for ordinary lookups.
3. **Make the documentation match reality.** Remove stale claims that every
   host action is mediated only through the Python registry, replace stale
   `agent` account naming with `zombie`, and align policy/default text with
   the current root-capable posture.
4. **Enhance logging and evidence.** Keep the zombie powerful, but make it
   loud: per-turn provider/model metadata, pi tool events, sudo/effective
   user details, web fetch records, command previews, and bounded outputs.
5. **Make power configurable, not hidden.** Introduce explicit posture
   language such as `power`/`strict` or `zombie`/`contained`, with the
   current all-powerful behavior documented as the default or as an explicit
   install choice.

## Updated product stance

Use this language consistently across product docs:

- Ubuntu Zombie installs a private, root-capable AI Systems Administrator.
- The default Linux account is `zombie`, configurable with `ZOMBIE_USER`.
- The account is intentionally root-equivalent when passwordless sudo is
  enabled.
- The pi runtime is allowed to inspect, repair, configure, and operate the
  local machine.
- The assistant may perform read-only internet lookups when useful.
- Local secrets must not be exfiltrated to arbitrary web destinations.
- The security boundary is operator ownership, loopback chat access,
  password/TTL controls, policy where it applies, and auditability — not a
  claim that the account is unprivileged.

Avoid wording that implies the current runtime is sandboxed more tightly
than it is. In particular, do not say all model-initiated host actions pass
through the Python `TOOL_REGISTRY` unless the implementation is changed to
make that true.

## P0: make pi's host power explicit and supported

### Current state

`payload/agent/pi-mono-bridge.mjs` runs pi in JSON mode with built-in host
tools. The current source declares the tool list exactly as:

```js
const PI_BUILTIN_TOOLS = ["read", "bash", "edit", "write", "grep", "find", "ls"];
```

The bridge logs `tool_execution_start` and `tool_execution_end` events as
pi diagnostics. Those actions are not converted into Python logical tool
calls such as `shell.run` or `fs.read` before execution.

`README.md`, `docs/ARCHITECTURE.md`, `SECURITY.md`, and some analysis docs
still describe a cleaner closed-registry model than the production pi path
actually provides.

### Desired behavior

Accept pi's built-in host tools as a supported capability and make the
runtime/docs agree:

1. The system prompt tells pi it is a root-capable local administrator with
   host tools.
2. The bridge exposes the full intended tool set intentionally, not as a
   hidden compatibility leak.
3. Python records every pi tool start/end event in local audit/history with
   bounded, redacted details.
4. Docs distinguish between:
   - pi built-in host tools;
   - Python typed tools;
   - policy/approval paths that apply to Python-dispatched tools;
   - operator review and audit controls that apply to the complete system.
5. Security docs state plainly that the `zombie` account is
   root-equivalent when passwordless sudo is enabled.

### Files likely to change

- `payload/agent/pi-mono-bridge.mjs`
- `payload/agent/pi_mono.py`
- `payload/agent/server.py`
- `payload/agent/audit.py`
- `payload/agent/history.py`
- `payload/agent/templates/APPEND_SYSTEM.md.tmpl`
- `payload/agent/templates/settings.json.tmpl`
- `docs/ARCHITECTURE.md`
- `docs/VISION.md`
- `docs/CONFIGURATION.md`
- `docs/INTERNET-ACCESS.md`
- `SECURITY.md`
- `README.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- No current product documentation claims a fully closed Python mediation
  boundary unless code makes that claim true.
- The pi built-in tool path is documented as intentional administrator
  power.
- Pi tool starts and completions are locally visible in audit/history.
- The operator can understand that Ubuntu Zombie is powerful by design and
  must be treated like root.

## P0: give pi first-class web access

### Current state

`docs/INTERNET-ACCESS.md` already notes that the host can reach the web and
that `curl` exists. The missing piece is first-class product behavior: the
assistant is not clearly told that the web is available, and there is no
stable `web.fetch` audit record.

Using `bash` plus `curl` can work, but it hides read-only web lookups inside
arbitrary shell text and makes logs less useful.

### Desired behavior

Add a dedicated read-only web capability that pi can naturally choose:

- tool name: `web.fetch`;
- allowed schemes: `http` and `https`;
- method: read-only GET/HEAD only;
- bounded response size and timeout;
- no request body;
- safe request headers only;
- redirects only within safe schemes;
- deny loopback, link-local, private RFC1918, and cloud metadata targets by
  default unless the operator explicitly enables local-network fetches;
- audit URL, status, byte count, duration, content type, redirect chain,
  and truncation state;
- redact sensitive headers and never include provider keys.

The system prompt should say that the assistant may access the public web
for lookups, version checks, documentation references, and troubleshooting.
It should also say that web access is for reading public information, not
for uploading local secrets or command output to arbitrary services.

### Files likely to change

- `payload/agent/tools.py`
- `payload/agent/policy.py`
- `payload/agent/audit.py`
- `payload/agent/server.py`
- `payload/agent/templates/APPEND_SYSTEM.md.tmpl`
- `payload/agent/skills/web.md`
- `payload/etc/policy.yaml`
- `tests/python/test_web_fetch.py`
- `tests/python/test_tools.py`
- `tests/smoke.sh`
- `docs/INTERNET-ACCESS.md`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `SECURITY.md`
- `README.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- A normal question that needs current web context causes a read-only
  fetch instead of a refusal.
- `web.fetch` appears as a distinct, bounded, redacted audit event.
- Public web lookups do not require an approval prompt by default.
- `curl ... | bash` is a critical security anti-pattern because it
  fetches arbitrary remote code and executes it directly, bypassing the
  bounded `web.fetch` audit trail; it must stay blocked or require explicit
  confirmation. File uploads, request bodies, and local-network probes
  remain separately classified as higher-risk actions.
- Documentation states that outbound web access is enabled for the agent
  capability, while inbound chat exposure remains loopback-only.

## P0: update stale documentation to reflect the true zombie

### Current stale themes

The documentation set still contains mixed eras of the product:

- Some docs describe a closed Python registry as if it were the only action
  path.
- `SECURITY.md` still names the operating Linux user as `agent`, while the
  documented default elsewhere is `zombie`.
- Some internet-access text refers to permissive policy YAML defaults and
  should be aligned with the current policy direction.
- Historical analysis can remain historical, but current user-facing docs
  should not force readers to reconcile `agent`, `zombie`, strict registry
  claims, and all-powerful pi behavior.

### Desired behavior

Documentation should consistently explain three truths:

1. Ubuntu Zombie is powerful: the installed account can be root-equivalent.
2. Pi is the active administrator runtime and can use broad host tools.
3. Power is paired with local ownership, TTL/password controls, audit logs,
   and explicit warnings, not hidden behind stale safety claims.

### Files likely to change

- `README.md`
- `SECURITY.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE.md`
- `docs/CONFIGURATION.md`
- `docs/INTERNET-ACCESS.md`
- `docs/FAQ.md`
- `docs/QUICKSTART.md`
- `docs/TROUBLESHOOTING.md`
- `CONTRIBUTING.md`
- `AGENTS.md`
- `payload/README.md`
- analysis docs that are still presented as current

Do not rewrite historical research notes under `docs/research/` unless they
are linked as current operating guidance.

### Acceptance criteria

- New readers see one coherent model: `zombie` is the default account,
  `ZOMBIE_USER` configures it, and `AGENT_USER` is only a legacy alias.
- Docs do not overstate policy mediation on the pi built-in path.
- Docs explain outbound web access separately from inbound loopback-only
  chat access.
- Security docs explicitly call passwordless sudo root-equivalent.
- The README, architecture, internet-access, and security pages agree.

## P0: enhance logging for a harder, louder zombie

### Current state

Audit logging is structured and redacts obvious secrets. Verbose mode can
attach bounded stdout/stderr previews. Pi bridge logs exist under the state
log directory, but the audit trail does not yet provide a complete,
operator-friendly picture of pi tool decisions, provider/model context,
working directory, sudo status, or web fetch metadata.

### Desired behavior

Make every turn reconstructable without dumping unlimited command output:

- conversation id, turn id, and parent message id;
- provider and model for the turn;
- bridge package/version and pi mode;
- enabled pi built-in tool list;
- tool start/end timestamps;
- normalized command or target path;
- working directory;
- effective user and whether sudo/root was involved;
- exit code, duration, stdout/stderr byte counts, and bounded redacted
  previews;
- web fetch URL, host, status, content type, byte count, redirect chain, and
  truncation state;
- policy class/rule when Python policy is involved;
- approval id, approver action, denial reason, and confirmation-phrase
  requirement where applicable;
- redaction version so readers know what filter was applied.

Add a compact helper view for operators, but keep the raw JSON-lines log as
the source of truth.

### Files likely to change

- `payload/agent/audit.py`
- `payload/agent/history.py`
- `payload/agent/pi_mono.py`
- `payload/agent/server.py`
- `payload/bin/audit-recent`
- `payload/bin/collect-diagnostics`
- `payload/systemd/ubuntu-zombie-chat.service`
- `tests/python/test_audit.py`
- `tests/python/test_pi_mono.py`
- `tests/smoke.sh`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `docs/TROUBLESHOOTING.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Operators can answer: what did pi do, why did it do it, which model did
  it use, did it touch root, and what evidence was produced?
- Audit entries remain bounded and redacted by default.
- Existing audit readers tolerate new fields.
- Diagnostic bundles include enough context to debug failures without
  leaking secrets.

## P1: introduce explicit power posture controls

### Current state

The product has powerful default behavior but does not expose a clean
operator-facing vocabulary for power posture. `policy.yaml` describes
classes, but it does not clearly answer whether the install is meant to be
contained or all-powerful.

### Desired behavior

Add explicit posture language and configuration. Recommended names:

- `power`: broad pi host tools and passwordless sudo, optimized for the
  owner who wants the zombie to operate the machine fully;
- `strict`: narrower Python-typed tools and approvals, optimized for
  cautious environments;
- `observe`: no host mutation, useful when provider trust is low.

The user request for this plan is clearly in the `power` direction. If this
mode becomes the default, docs must say so loudly. If maintainers choose a
safer default, the installer must make `power` an explicit, memorable opt-in
rather than a hidden implementation detail.

### Files likely to change

- `scripts/install.sh`
- `payload/etc/policy.yaml`
- `payload/agent/server.py`
- `payload/agent/templates/APPEND_SYSTEM.md.tmpl`
- `payload/agent/templates/settings.json.tmpl`
- generated verify helper in `scripts/install.sh`
- `docs/CONFIGURATION.md`
- `docs/QUICKSTART.md`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `README.md`
- `tests/smoke.sh`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- The installer and docs use the same posture vocabulary.
- Operators can tell whether their zombie is in all-powerful mode.
- Verification reports the active posture.
- Prompt text and enabled tools match the active posture.

## P1: harden power without weakening it

### Desired behavior

Make the all-powerful mode more robust rather than less capable:

- better turn timeouts and per-turn tool budgets;
- clearer recovery after bridge crashes;
- health checks that report provider/model/tool availability;
- stronger redaction before audit/history/diagnostics;
- optional local-network web fetch allow-list for advanced operators;
- explicit warnings before destructive commands;
- durable receipts for install-time posture and enabled capabilities;
- tests that fail when docs, prompt, policy, and enabled tool list diverge.

### Files likely to change

- `payload/agent/pi_mono.py`
- `payload/agent/providers.py`
- `payload/agent/audit.py`
- `payload/agent/tools.py`
- `payload/bin/health-check`
- `payload/bin/verify`
- `scripts/install.sh`
- `tests/python/`
- `tests/smoke.sh`
- `docs/TROUBLESHOOTING.md`
- `docs/ARCHITECTURE.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- Power mode remains able to administer the machine.
- Failures are easier to diagnose from logs and helpers.
- Secret redaction is tested against provider keys, chat password hashes,
  and common token patterns.
- Health output shows whether web fetch, pi tools, provider credentials, and
  TTL are usable.

## P1: align policy defaults with the chosen posture

### Current state

`improvements-1.md` recommended conservative YAML defaults. That remains a
reasonable `strict` posture, but it conflicts with the requested direction
if presented as the only desired future.

### Desired behavior

Policy should be posture-aware:

- `power`: pi built-ins and broad sudo are expected; policy still classifies
  Python tools and approvals where those paths are used, but docs do not
  pretend it mediates every pi action.
- `strict`: all host actions should flow through Python typed tools and
  approvals before execution.
- `observe`: no host mutation tools.

Regardless of posture, keep destructive actions clearly visible and logged.
If `payload/etc/policy.yaml` remains single-mode, make it match the shipped
runtime. If multiple postures are added, store clear per-posture policy
files or generated policy sections.

### Files likely to change

- `payload/etc/policy.yaml`
- `payload/agent/policy.py`
- `payload/agent/server.py`
- `payload/agent/templates/APPEND_SYSTEM.md.tmpl`
- `tests/python/test_policy.py`
- `tests/smoke.sh`
- `docs/CONFIGURATION.md`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

### Acceptance criteria

- A parser improvement cannot silently activate surprising defaults.
- Docs explain what policy controls in each posture.
- Tests cover the shipped policy text and effective runtime values.
- Unknown commands fail closed in strict paths while power-mode pi behavior
  is documented and logged.

## P2: improve approval UI evidence

Even in all-powerful mode, approvals remain useful where Python dispatch or
higher-risk flows require them.

For each pending action, show:

- tool name;
- classification;
- matched rule or default;
- whether sudo/root is involved;
- normalized args or command;
- touched paths;
- preview output where safe;
- audit id and tool-call id;
- exact phrase when required;
- approve button disabled until a required phrase matches;
- deny button and denial reason.

Files likely to change:

- `payload/agent/templates/index.html`
- `payload/agent/server.py`
- `payload/agent/audit.py`
- `tests/smoke.sh`
- `docs/ARCHITECTURE.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

Acceptance criteria:

- Operators can understand approval prompts without reading raw logs.
- The UI cannot accidentally approve phrase-gated actions.
- Slash command approval and denial still work.

## P2: add disposable-VM integration tests

The more powerful the zombie becomes, the more important real integration
coverage becomes.

A guarded harness should verify:

1. `install --dry-run`;
2. non-interactive install with generated placeholder inputs;
3. re-run install for idempotence;
4. `verify`;
5. `doctor`;
6. `repair`;
7. active posture appears in verify/receipt output;
8. chat service binds only to loopback;
9. web fetch can reach a public test endpoint;
10. logs record pi tool and web fetch events;
11. secrets permission failure causes service refusal;
12. uninstall with archive on a disposable host.

The runner must refuse to mutate a normal workstation unless an explicit
marker is present, for example:

```bash
ZOMBIE_INTEGRATION_ALLOW_HOST_MUTATION=I_AM_IN_A_DISPOSABLE_VM
```

Files likely to change:

- `.github/workflows/integration.yml`
- `scripts/integration-vm.sh` or `tests/integration/*`
- `docs/PLATFORMS.md`
- `CONTRIBUTING.md`
- `CHANGELOG.md`
- `VERSION` if `CHANGELOG.md` changes

Acceptance criteria:

- Maintainers can test real install behavior repeatably.
- The harness cannot accidentally run destructive install steps on a normal
  workstation.
- Idempotence and all-powerful posture are verified on a disposable host.

## Suggested implementation order

Implement in small pull requests:

1. Create the documentation alignment PR: update README, security,
   architecture, internet-access, configuration, and FAQ to describe the
   root-capable pi-powered zombie honestly.
2. Add audit/history records for pi tool start/end events and provider/model
   metadata.
3. Add `web.fetch`, its skill brief, policy classification, tests, prompt
   guidance, and docs.
4. Add enhanced audit fields for sudo/effective user, working directory,
   byte counts, durations, and redacted previews.
5. Add explicit posture naming (`power`, `strict`, `observe`) or otherwise
   document the chosen all-powerful default in installer output and verify.
6. Align shipped policy text, parser behavior, tests, and docs with the
   chosen posture model.
7. Improve approval UI evidence for paths that still require approval.
8. Add disposable-VM integration coverage.
9. Add optional stricter posture implementation if maintainers still want a
   contained mode.

Do not combine every item in one pull request. The first implementation PR
should make stale documentation impossible to miss and should clearly say
what Ubuntu Zombie is today: a powerful, private AI administrator with local
root-equivalent capability, outbound web ambitions, and audit-first
operator accountability.

## Definition of done for the first implementation PR

The first implementation PR is complete when:

- `README.md`, `docs/ARCHITECTURE.md`, `SECURITY.md`,
  `docs/CONFIGURATION.md`, and `docs/INTERNET-ACCESS.md` agree on the
  product stance;
- stale `agent` account-identity text is replaced with `zombie` /
  `ZOMBIE_USER` except where `agent` refers to the AI concept or legacy
  alias behavior;
- docs no longer claim complete Python mediation for pi built-in actions;
- docs clearly state that outbound internet lookup support is intended and
  separate from inbound loopback-only chat exposure;
- enhanced logging requirements are captured in architecture/security docs;
- `CHANGELOG.md` records the user-visible documentation correction;
- `VERSION` is bumped if `CHANGELOG.md` changes;
- `make lint` and `make test` pass when shell or Python changes are made;
- documentation-only changes are checked for secrets and obvious stale
  contradictions.
