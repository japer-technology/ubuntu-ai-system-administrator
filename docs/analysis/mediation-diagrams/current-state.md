# Current state — how Ubuntu Zombie works now

Vertical Mermaid diagrams of the system as shipped today. The key
fact, established by `docs/analysis/improvements-8.md` (finding F1),
is that the production bridge runs pi's built-in tools **in-process**,
so the Python mediation pipeline (schema validation → policy
classification → approval queue → audit) is never invoked on the
shipped path. Diagrams 3 and 4 show the two paths side by side.

## 1. Installed shape

What `scripts/install.sh install` puts on the machine.

```mermaid
flowchart TD
    A["scripts/install.sh install"] --> B["Dedicated Linux account: agent<br/>(passwordless sudo via /etc/sudoers.d/)"]
    A --> C["/opt/ai-zombie/"]
    C --> C1["agent/ — Python chat service + pi bridges"]
    C --> C2["bin/ — operator helpers"]
    C --> C3["etc/policy.yaml — default action policy"]
    C --> C4["pi/ — rendered pi-mono settings + prompt prelude"]
    C --> C5["state/ — conversations.db, lifecycle.json, logs/"]
    A --> D["/etc/ubuntu-zombie/ — operator policy/skills overlays"]
    A --> E["/etc/systemd/system/ — chat service + health timer"]
    E --> F["Chat service on 127.0.0.1:7878<br/>(loopback only — no SSH, VNC, Tailscale)"]
```

## 2. A chat turn, end to end

The transport described in `docs/ARCHITECTURE.md` ("Chat turn
transport"). This part works the same before and after mediation.

```mermaid
flowchart TD
    A["Browser (loopback)"] -->|"POST /api/message"| B["server.py<br/>validate prompt, session cookie, TTL"]
    B --> C["Register opaque turn_id<br/>start model turn in worker thread"]
    C --> D["Return turn_id immediately"]
    D --> E["Browser opens GET /api/stream/{turn_id}<br/>(EventSource, same session gate)"]
    C --> F["pi_mono.run_turn()<br/>spawn pi-mono-bridge.mjs, idle watchdog"]
    F --> G["Bridge drives the LLM provider turn"]
    G --> H["Bridge events: token / progress /<br/>tool activity / final"]
    H --> I["SSE events to browser:<br/>phase, token, tool_start/tool_end,<br/>pending_approval, turn_done / turn_error"]
    H --> J["history.py — persist conversation<br/>+ tool events in SQLite"]
    I --> K["Browser renders live turn;<br/>persisted conversation stays authoritative"]
```

## 3. Shipped tool execution path (unmediated)

What actually happens when the model uses a tool today
(`payload/agent/pi-mono-bridge.mjs` + finding F1). The policy gate is
on the diagram only to show that it is **not** on the path.

```mermaid
flowchart TD
    A["pi-mono-bridge.mjs spawns<br/>pi --mode json -p"] --> B["--tools read,bash,edit,write,grep,find,ls<br/>(pi's real built-in tools)"]
    B --> C["Model proposes a tool use"]
    C --> D["pi executes the tool ITSELF, in-process<br/>(bash runs as the agent account:<br/>NOPASSWD sudo)"]
    D --> E["Bridge sees tool_execution_start /<br/>tool_execution_end events"]
    E --> F["Bridge only LOGS them as progress hints<br/>(never emits a tool_call event)"]
    F --> G["pi_mono.py forwards display-only<br/>progress to the UI"]
    G --> H["Turn continues; final text returned"]

    X["server.py on_tool_call:<br/>schema validation → policy.classify_tool →<br/>approval queue → tools.py → audit.py"]
    F -. "never invoked on this path" .-> X

    style X stroke-dasharray: 5 5
```

Consequences (unenforced on this path):

- `max_tool_calls` and elevated-call budgets
- the destructive-confirmation phrase
- `payload/agent/tools.py` path allow-lists
- per-command audit records

## 4. Where the mediation plumbing runs today (stub only)

The full pipeline exists and is exercised — but only by
`tests/fixtures/stub-pi-mono.mjs`, never by the production bridge
(finding F2).

```mermaid
flowchart TD
    A["tests/fixtures/stub-pi-mono.mjs<br/>(test fixture, not shipped)"] -->|"emits {type: tool_call}"| B["pi_mono.run_turn()<br/>count against max_tool_calls budget"]
    B --> C["server.py on_tool_call(call_id, name, args)"]
    C --> D["Schema validation against the<br/>closed registry (tools.py)"]
    D --> E["policy.classify_tool →<br/>read_only / user_change / system_change /<br/>network_change / destructive"]
    E --> F{"Requires approval?"}
    F -->|"read_only: auto"| G["tools.py executes the call"]
    F -->|"gated class"| H["Approval queue +<br/>pending_approval SSE to operator"]
    H --> I["Operator approves / denies"]
    I --> G
    G --> J["audit.py — JSON-lines record<br/>(secret-redacted)"]
    J --> K["tool_result written back to bridge stdin"]
    K --> L["Model sees the mediated result;<br/>turn continues"]
```

## 5. Trust boundaries as they stand

The documented boundary list versus reality: boundary 3–5 hold only on
the stub path.

```mermaid
flowchart TD
    A["1. Browser ↔ loopback chat service<br/>(session cookie, password)"] --> B["2. Server → LLM provider via pi-mono"]
    B --> C["3. Tool calls: schema + policy classification"]
    C --> D["4. Elevated actions: operator approval"]
    D --> E["5. Every decision audit-logged"]
    C -. "F1: bypassed by the shipped bridge" .-> F["pi built-in tools execute<br/>in-process as root-capable agent"]
    style F stroke-dasharray: 5 5
```
