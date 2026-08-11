# F1 option report — MORE control: restore real tool mediation

Companion to [`improvements-8.md`](improvements-8.md) finding F1.
This report designs the fix that makes the documented trust model
**true**: every agent tool call passes through `policy.py`, the
approval queue, and `audit.py` before it executes. The alternative —
keeping the current unmediated architecture and correcting the docs —
is [`f1-option-less-control.md`](f1-option-less-control.md).

## 1. What F1 actually is (recap, verified)

`payload/agent/pi-mono-bridge.mjs:246-270` spawns
`pi --mode json -p` with pi's built-in tools enabled
(`PI_BUILTIN_TOOLS` at `:141`). pi executes those tools **in its own
process**. The bridge only *logs* `tool_execution_*` events
(`:397-444`); it never emits the `tool_call` frame that
`payload/agent/pi_mono.py:313` would route into
`server.py:736 on_tool_call` (schema check → `policy.classify_tool` →
approval queue → audit). Therefore, on the shipped path:

- no policy classification, no operator approval, no per-command
  audit record;
- the 1,000-call / 250-elevated budgets are unenforced;
- the model's `bash` runs with `NOPASSWD:ALL`
  (`scripts/install.sh:3093`). Prompt injection in anything the agent
  reads is unmediated root.

## 2. Key upstream finding: `--mode rpc` does NOT mediate either

`packages/coding-agent/docs/rpc.md` (upstream, pi 0.80.x): RPC mode
is a **control channel** — `prompt`, `steer`, `abort`, `get_state`,
`set_model`, etc. LLM tool calls still execute inside the pi process;
RPC only streams the same events. Moving the bridge to `--mode rpc`
would change the transport, not the trust boundary. The F1 note in
`improvements-8.md` recommending rpc mode is hereby **refined**: rpc
is necessary neither for mediation nor worth the translation cost the
bridge authors feared.

The actual mediation hook is the **extension system**
(`packages/coding-agent/docs/extensions.md`):

- `pi.on("tool_call", handler)` fires **before** the tool executes and
  may return `{ block: true, reason }` to deny the call. The handler
  is async and awaited — the agent turn pauses until it returns. This
  is exactly an approval-gate shape.
- `pi.on("tool_result", ...)` / `tool_execution_end` fire after, for
  outcome auditing.
- `pi.registerTool()` registers custom tools whose `execute()` runs
  arbitrary TypeScript — which can forward execution anywhere.
- Built-in tools can be **overridden** by extensions (upstream ships
  `examples/extensions/gondolin/` doing exactly this) and disabled
  with `--no-builtin-tools`.
- Extensions auto-load from `~/.pi/agent/extensions/` — the installer
  already owns that home (`models.json`, settings), so shipping one
  first-party extension is a natural fit.

## 3. Recommended design: the `zombie-policy-gate` extension

Keep `pi --mode json -p` exactly as today. Add one first-party pi
extension that turns pi's own hook into the mediation channel.

### 3.1 Data flow per tool call

```
LLM (in pi) ──tool_call──► zombie-policy-gate (in pi, awaited)
                              │  HTTP POST 127.0.0.1:7878/internal/gate
                              │  {turn_token, tool, args}
                              ▼
                    server.py mediation endpoint
                    schema check (tools.py rules)
                    → policy.classify_tool
                    → read_only/system_change: allow (+ audit)
                    → destructive/approval-required: queue for
                      operator, AWAIT decision (chat UI prompt
                      already exists — server.py:822 pending map)
                    → deny on timeout/denial
                              │
                              ▼
              allow  → extension returns nothing (pi executes)
              deny   → extension returns { block: true, reason }
                       (model sees the refusal as the tool result)
tool_execution_end ──► extension POSTs outcome → audit.py record
```

### 3.2 Components

1. **`payload/agent/pi-extensions/zombie-policy-gate/index.ts`** (new,
   ~150 lines TS). Installed by `scripts/install.sh` to
   `${AGENT_HOME}/.pi/agent/extensions/zombie-policy-gate/`.
   - `pi.on("tool_call")`: POST `{tool, args}` to the gate endpoint
     with the per-turn bearer token; map allow/deny/approve-pending to
     pi's return protocol. Hard-fail **closed**: if the gate is
     unreachable, return `{ block: true, reason: "policy gate
     unreachable" }`.
   - `pi.on("tool_execution_end")`: POST outcome (ok, exit code,
     output size) for the audit record.
   - No npm dependencies beyond what pi provides (typebox unused —
     no custom tools in this design).
2. **Gate endpoint in `server.py`** (`/internal/gate`, loopback-only,
   per-turn random token). Reuses the *existing* machinery:
   `tools.py` schema validation, `policy.classify_tool`, the pending
   approval dict (`server.py:822-823`), `audit.log_tool_call`. Most of
   `on_tool_call` (`server.py:736-893`) moves behind this endpoint —
   which is also the F5 decomposition, done once.
3. **Per-turn token**: the bridge generates it, exports it to the pi
   child env (`ZOMBIE_GATE_TOKEN`), and the endpoint requires it.
   Residual risk (below) acknowledged: the agent identity can read its
   own process env.
4. **Budgets**: the endpoint counts calls per turn and returns deny
   past `max_tool_calls` / elevated budget — enforcement finally real.
5. **Installer**: copy the extension, `chown` agent, record it in the
   component manifest so `verify`/`repair`/`uninstall` cover it.

### 3.3 Why this beats the alternatives

| Design | Mediation | Effort | Risk |
|---|---|---|---|
| A. Gate extension around pi built-ins (recommended) | Full pre-execution classify/approve/audit | ~2 files + endpoint + tests | pi hook semantics must be confirmed in `--mode json -p` (step 0) |
| B. `--no-builtin-tools` + re-register registry tools via `registerTool`, forwarding to Python | Maximal — `tools.py` path allow-lists also become effective | High: re-implements pi's tool UX; the exact config that previously produced "zero usable tools" (`pi-mono-bridge.mjs:137-139`) | Model behaviour regression risk |
| C. `--mode rpc` bridge rewrite | **None** (tools still in-process) | High, and buys nothing for F1 | — |

Design A keeps pi's well-tested tool implementations (truncation,
timeouts, shell handling) and adds the gate at the one point pi
exposes for it. Design B remains available later if the closed
registry's path allow-lists are wanted as well; A does not preclude B.

### 3.4 Residual risks (state them honestly in SECURITY.md)

- The gate token lives in the agent's process env; a root-capable
  agent could call the endpoint directly. This is a *confused-deputy*
  residual, not a bypass: a direct call still gets classified and
  audited, and approving still requires the operator. Document it.
- The extension executes inside pi with full permissions; pin it in
  the component manifest and checksum it in `verify`.
- `--mode json` event-schema fragility (F6) is unchanged.

## 4. Implementation sequence

0. **Spike (half day):** minimal extension logging `tool_call` events;
   run `pi --mode json -p "list files in /tmp"` headless; confirm the
   hook fires and `{ block: true }` prevents execution in this mode.
   If it does not fire in json mode, fall back to `--mode rpc` for
   transport (docs confirm extensions load in rpc mode) — the gate
   design is unchanged.
1. Extract `on_tool_call` core from `server.py` into a mediator
   callable from both the (stub) bridge path and the new endpoint.
2. Add `/internal/gate` + per-turn token; wire approvals to the
   existing chat approval UI.
3. Write the extension; installer + manifest + verify integration.
4. Tests (fixes F2 on this path):
   - unit: gate endpoint classifies/denies/audits (extend
     `tests/python/test_policy.py` style);
   - smoke: real bridge + fake pi emitting a destructive call without
     approval → assert the tool did not execute and the audit record
     exists;
   - smoke: approval granted → executes exactly once.
5. Docs: SECURITY.md trust model updated to describe the *real* gate;
   ARCHITECTURE.md gains the extension component; CHANGELOG entry.

## 5. What "done" looks like

A live chat turn in which `sudo cat /etc/shadow`:
1. appears in the chat as a pending approval before execution,
2. executes only after operator approval,
3. has a `policy=destructive` record with argv in `audit.log`, and
4. counts against the elevated budget.

Until that demonstration exists, the docs claims addressed in
[`f1-option-less-control.md`](f1-option-less-control.md) must be
treated as aspirational either way — the doc fixes are needed under
**both** options; only their final wording differs.
