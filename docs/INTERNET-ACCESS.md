# Giving the chat agent internet access

This note explains what has to change so the **pi-mono** chat agent can
reach the internet for ordinary chat questions — fetching a web page,
checking an upstream version, looking something up — separately from the
LLM/provider traffic it already makes.

It is written as a change map: what already works, where the real gaps
are, what to change, and what to leave alone.

**Status:** implemented. The typed `web.fetch` tool ships in
`payload/agent/tools.py` (`read_only`, GET/HEAD, public hosts only), the
system prompt states that read-only lookups are allowed and that data
must not be shipped outward, `payload/etc/policy.yaml` classifies a
stdout-only `curl`/`wget` as `read_only`, and `payload/agent/skills/web.md`
carries the guidance. The rest of this note is retained as background.

## TL;DR

The host is *not* the blocker. Outbound networking is already open at the
OS level and the agent already has a `bash` tool, so it can technically
run `curl`/`wget` today. What stops the agent from *using* the internet
for chat questions is higher up:

1. **The system prompt** frames the agent as a purely local systems
   administrator and never tells it the internet is fair game.
2. **There is no first-class "fetch a URL" tool** — web access only
   exists as a side effect of `bash`, which the model does not reach for
   when answering a knowledge question.
3. **The policy gate** classifies an unrecognised `curl`/`wget` as
   `system_change`, so every fetch triggers an approval prompt instead of
   running like the read-only lookup it usually is.

Addressing those three points is the substance of the work. Everything
else (firewall, systemd sandboxing) already permits egress.

## What already works — do not change

- **OS networking.** The default install configures no host firewall,
  and outbound HTTP/HTTPS is not blocked (`scripts/install.sh`). The
  chat service listens on loopback only; egress is unrestricted.
- **systemd sandbox.** `payload/systemd/ubuntu-ai-system-administrator-chat.service`
  deliberately ships with no network confinement — there is no
  `PrivateNetwork`, `IPAddressDeny`, or `RestrictAddressFamilies`. The
  service can open sockets to the internet.
- **The `bash` tool.** `payload/agent/pi-mono-bridge.mjs` enables pi's
  real built-in tools (`read, bash, edit, write, grep, find, ls`), and
  `curl` is installed as a base package. So a shell fetch already
  functions when the agent chooses to run one.
- **Loopback-only serving.** The chat *server* binds to `127.0.0.1`
  (`payload/agent/server.py`). That is an inbound invariant and is
  unrelated to outbound internet access — keep it as-is.

The takeaway: enabling internet for chat questions is an **agent
capability and guidance** change, not a networking change.

## The gaps to close

### 1. Tell the agent it may use the internet (system prompt)

`APPEND_SYSTEM_TEMPLATE` in `payload/agent/server.py` lists the agent's
tools and casts it strictly as the machine's local administrator. It
never mentions the internet, so the model defaults to "I can't browse"
behaviour for general questions.

Change needed:

- Add a short paragraph stating that read-only internet lookups are
  allowed for answering questions and verifying facts, and *how* to do
  them (the dedicated fetch tool below, or `curl`/`wget` via `bash`).
- Keep the existing guardrail that refuses to exfiltrate secrets, and
  extend it: never POST/PUT local files, environment, or credentials to
  an external host; the internet is for *reading*, not for shipping data
  out.

### 2. Add a first-class web-fetch tool (recommended)

Relying on `bash curl` works but is fragile and noisy in the audit log.
A typed tool gives a clean schema, a stable audit record, and a natural
place to enforce safety.

Two options:

- **Typed registry path** — add a `web.fetch` tool to
  `TOOL_REGISTRY` in `payload/agent/tools.py` (URL + optional method/byte
  cap), classified `read_only`, returning status, headers, and a
  truncated body. This is the cleanest fit with the existing closed
  tool surface, schema validation, and per-tool classification.
- **pi built-in path** — if the pinned `@earendil-works/pi-coding-agent`
  version exposes a fetch/web built-in, add it to `PI_BUILTIN_TOOLS` in
  `payload/agent/pi-mono-bridge.mjs`. (As of the pinned `0.80.10` the
  documented built-ins are only `read, bash, edit, write, grep, find,
  ls`, so this likely still means "shell out to `curl`".)

If a typed `web.fetch` is added, pair it with a short skill file (for
example `payload/agent/skills/web.md` with `<!-- triggers: http, https,
url, download, fetch, online -->`) so the loader nudges the model toward
the tool when a question implies a lookup.

### 3. Make read-only fetches auto-run (policy gate)

`payload/etc/policy.yaml` sets `default_class: destructive`, so an
unrecognised `curl`/`wget` is gated behind an approval prompt every time
— painful for casual questions.

Change needed:

- Add `read_only` rules for *read-only* fetches, e.g. a bare
  `curl`/`wget` that only writes to stdout (no `-o`/`-O` into a system
  path, no `| sh`).
- Leave the existing higher-tier rules in front so a fetch piped into a
  shell (`curl … | bash`) stays `system_change`/`destructive` — that
  pattern is already matched and must not be loosened.

Note: in the current pi-mono *bridge* path, `pi` runs its own built-in
tools and the Python policy gate is not in the loop, so this mainly
matters for the typed-registry path and for any future tightening. Add a
`web.fetch` (classified `read_only`) and the gate behaves correctly
regardless.

## Security considerations

Opening internet access widens the blast radius. Address these
explicitly:

- **Secret exfiltration.** The agent holds provider API keys and can read
  local files. The system prompt must keep refusing to send secrets or
  local data outward; prefer a read-only fetch tool that does not accept
  a request body sourced from local files.
- **SSRF / internal targets.** Outbound is unrestricted, so a fetch can
  reach `127.0.0.1`, the LAN, or a cloud metadata endpoint
  (`169.254.169.254`). Consider denying private/link-local ranges in the
  fetch tool, or an egress allow-list, if the threat model warrants it.
- **Auditability.** Route fetches through a typed tool so every request
  URL is recorded in the audit log, rather than buried inside arbitrary
  `bash` strings.
- **Optional hard egress control.** If you ever need to *restrict* (not
  enable) which hosts the agent reaches, that is where UFW egress rules
  or systemd `IPAddress*` directives come in — but that is the opposite
  of this task.

## Summary of changes

| Area | File | Change |
|------|------|--------|
| Guidance | `payload/agent/server.py` (`APPEND_SYSTEM_TEMPLATE`) | State that read-only internet lookups are allowed; reinforce no-exfiltration. |
| Tooling | `payload/agent/tools.py` | Add a `read_only` `web.fetch` tool (recommended). |
| Tooling | `payload/agent/pi-mono-bridge.mjs` | Only if a pi web built-in exists, add it to `PI_BUILTIN_TOOLS`. |
| Skill | `payload/agent/skills/web.md` | New skill with internet triggers nudging toward the fetch tool. |
| Policy | `payload/etc/policy.yaml` | Classify read-only `curl`/`wget` as `read_only`; keep `curl … \| bash` gated. |
| Firewall / systemd | — | No change; outbound is already permitted. |

## Verifying it works

After the changes:

1. Ask a question that needs the internet, e.g. *"What is the latest
   stable Node.js version according to nodejs.org?"* The agent should
   perform a fetch rather than refuse.
2. Confirm the fetch appears in the audit log as a single, attributable
   tool call (`web.fetch` or the `bash` command).
3. Confirm a read-only lookup runs without an approval prompt, while a
   `curl … | bash` still requires approval.
4. Confirm the agent still refuses to send local files or secrets to an
   external host.
