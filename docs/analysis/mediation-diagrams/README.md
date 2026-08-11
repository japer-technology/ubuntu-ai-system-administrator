# Mediation diagrams

Vertical Mermaid diagrams that show, side by side, how Ubuntu Zombie
runs **today** and how it runs once tool-call **mediation** is
restored per the improvements-8 remediation plan.

These are internal engineering records, like the rest of
`docs/analysis/`. Nothing in this folder changes behaviour; the
diagrams transcribe what the code and the analysis documents already
say, so the two states can be compared at a glance.

## Contents

- [`current-state.md`](current-state.md) — how the system works now:
  the installed shape, a chat turn end to end, the shipped
  (unmediated) tool-execution path, and the stub-only path that the
  mediation plumbing currently exercises.
- [`mediation.md`](mediation.md) — the mediated design: the full
  mediated tool-call lifecycle, remediation Option A (`--mode rpc`),
  remediation Option B (`--no-builtin-tools` + custom tools), and the
  unmediated-execution tripwire.

## Sources

The diagrams are derived from:

- `docs/ARCHITECTURE.md` — components, trust boundaries, chat
  transport.
- `docs/analysis/improvements-8.md` — finding F1 (mediated tool path
  is dead code on the shipped bridge) and its evidence.
- `docs/analysis/improvements-8-plan.md` — phase 1, the two
  remediation shapes and their acceptance criteria.
- `payload/agent/pi-mono-bridge.mjs`, `payload/agent/pi_mono.py`,
  `payload/agent/server.py`, `payload/agent/tools.py`,
  `payload/agent/policy.py`, `payload/agent/audit.py` — the code
  paths the diagrams describe.

If the code and a diagram ever disagree, the code wins; update the
diagram.
