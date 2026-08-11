# Mediation — the restored tool-call gate

Vertical Mermaid diagrams of the mediated design from
`docs/analysis/improvements-8-plan.md` (phase 1). The invariant both
remediation shapes restore is:

> every tool execution round-trips through `on_tool_call`.

They differ only in *where* tool execution lives. Nothing here is
implemented yet; the diagrams show the target shape.

## 1. Mediated tool-call lifecycle (the invariant)

Every tool use, regardless of remediation shape, follows this path —
the same pipeline that today only the stub exercises.

```mermaid
flowchart TD
    A["Model proposes a tool use"] --> B["Bridge emits {type: tool_call, id, name, args}<br/>on stdout"]
    B --> C["pi_mono.run_turn() —<br/>enforce max_tool_calls budget"]
    C -->|"budget exceeded"| C1["Synthetic budget_exceeded tool_result;<br/>model told to end the turn"]
    C -->|"within budget"| D["server.py on_tool_call"]
    D --> E["Schema validation against the<br/>closed registry (tools.py)"]
    E -->|"invalid"| E1["Rejected tool_result + audit record"]
    E -->|"valid"| F["policy.classify_tool"]
    F --> G{"Classification"}
    G -->|"read_only"| H["Auto-approved: tools.py executes"]
    G -->|"user_change / system_change /<br/>network_change"| I["Approval queue;<br/>pending_approval SSE to operator"]
    G -->|"destructive"| J["Approval queue + operator must type<br/>the confirmation phrase"]
    I --> K{"Operator decision"}
    J --> K
    K -->|"deny"| K1["Denied tool_result + audit record"]
    K -->|"approve"| H
    H --> L["audit.py — JSON-lines record<br/>(secret-redacted); history.py event"]
    L --> M["tool_result written to bridge stdin"]
    M --> N["Bridge returns Python's result to pi;<br/>model continues on mediated output only"]
```

## 2. Option A (preferred) — move the bridge to `--mode rpc`

pi stops executing tools itself; the bridge relays each tool request
to Python and blocks until Python answers.

```mermaid
flowchart TD
    A["pi-mono-bridge.mjs starts<br/>pi --mode rpc (JSON-RPC on stdio)"] --> B["Assert pinned bridge version from<br/>bridge-dependencies.lock at startup;<br/>fail loudly on mismatch"]
    B --> C["Map the closed registry (tools.py)<br/>to the tool surface pi expects"]
    C --> D["Model proposes a tool use"]
    D --> E["pi sends an observable RPC tool request<br/>to the bridge — it does NOT execute"]
    E --> F["Bridge translates it to a<br/>{type: tool_call} line on stdout"]
    F --> G["Python mediation pipeline<br/>(diagram 1: schema → policy →<br/>approval → tools.py → audit)"]
    G --> H["Python writes tool_result to bridge stdin"]
    H --> I["Bridge answers the RPC request<br/>with Python's result"]
    I --> J["pi feeds the mediated observation<br/>back to the model; turn continues"]
```

## 3. Option B (interim) — `--no-builtin-tools` + custom pi tools

A hard stop that keeps the model usable: pi's built-ins are disabled
and the registry tools are re-registered as extension-defined custom
tools that round-trip through Python.

```mermaid
flowchart TD
    A["pi-mono-bridge.mjs starts pi with<br/>--no-builtin-tools"] --> B["pi extension registers the<br/>Python-mediated registry tools as<br/>custom pi tools"]
    B --> C["Model sees real, usable tools<br/>(avoids the historical zero-usable-tools<br/>regression)"]
    C --> D["Model calls a custom tool"]
    D --> E["Extension forwards the call to the bridge;<br/>bridge emits {type: tool_call}"]
    E --> F["Python mediation pipeline<br/>(diagram 1)"]
    F --> G["tool_result returns through the<br/>extension to the model"]
```

## 4. Tripwire — no silent unmediated execution

Work item 4 of phase 1: log-only handling of `tool_execution_*`
events is removed or converted into a loud failure.

```mermaid
flowchart TD
    A["Bridge receives a tool_execution_* event"] --> B{"Was it preceded by a<br/>mediated tool_call?"}
    B -->|"yes"| C["Forward as display-only progress<br/>to the chat UI"]
    B -->|"no"| D["Terminate the turn with an<br/>'unmediated tool execution' error"]
    D --> E["Write an audit record"]
    E --> F["Surface turn_error to the operator<br/>(loud failure, never silence)"]
```

## 5. Trust boundaries once mediation lands

The five documented boundaries all hold on the production path, and
the system prompt no longer encourages direct sudo use.

```mermaid
flowchart TD
    A["1. Browser ↔ loopback chat service"] --> B["2. Server → LLM provider via pi-mono"]
    B --> C["3. Every tool call: schema validation +<br/>policy classification (enforced)"]
    C --> D["4. Elevated actions: operator approval +<br/>destructive-confirmation phrase (enforced)"]
    D --> E["5. Every decision and result audit-logged<br/>(per-command records restored)"]
    E --> F["Budgets, allow-lists, and TTL bound the<br/>turn; tripwire catches any bypass"]
```

## Acceptance criteria (from the plan)

- A live turn on the **real** bridge produces, for every tool
  execution: a schema-validated `tool_call`, a policy classification,
  an audit record, and (for gated classes) an approval round-trip.
- `max_tool_calls`, the elevated-call budget, the
  destructive-confirmation phrase, and the `tools.py` path
  allow-lists are demonstrably enforced on the production path.
- The tripwire converts any unmediated execution into a loud turn
  failure rather than silence.
