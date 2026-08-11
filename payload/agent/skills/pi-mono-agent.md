<!-- triggers: pi-mono, pi-coding-agent, pi-agent, pi-rpc, pi-settings -->
# Skill: pi-mono agent runtime

This skill is loaded for the pi-mono coding-agent runtime embedded in Ubuntu
Zombie.

Operating rules:

- Distinguish the embedded runtime from a user's standalone `pi`
  installation. Ubuntu AI System Administrator pins `@earendil-works/pi-coding-agent`, renders
  settings under `/opt/ai-zombie/pi/`, and starts it through
  `/opt/ai-zombie/agent/pi-mono-bridge.mjs`.
- The Python chat service owns provider/model selection and starts the Node
  bridge over line-delimited JSON. The bridge emits model, tool, progress and
  final events; it is not a separate network service and should not gain a
  listening socket.
- Ubuntu AI System Administrator disables pi's built-in tools. Every effective tool call must
  return through the Python closed registry, policy classification, approval
  queue and audit log. Never enable built-in shell or filesystem tools to
  work around a denial.
- Inspect the pinned version files, rendered settings, service status and
  bounded per-turn logs before changing anything. `/version` reports the
  installed and available runtime versions without modifying the install.
- Per-turn logs live under `/opt/ai-zombie/state/logs/`; session/checkpoint
  state lives under `/opt/ai-zombie/state/pi-mono-sessions/`. Redact prompts,
  tool arguments and provider errors before sharing diagnostics.
- Provider credentials come from Ubuntu AI System Administrator's root-owned secrets flow.
  Do not add keys to pi settings, a user's native pi configuration, command
  arguments or bridge logs.
- Do not update the global package, edit generated settings, or replace the
  bridge in place. The installer owns the pin and rendered files; use
  `verify`/`doctor`, then an operator-approved `repair` or code release.
- A bridge failure can come from Node availability, a missing pin, malformed
  protocol output, provider failure, cancellation or the idle watchdog.
  Diagnose those layers separately and retain the first concrete error.
- Restarting `ubuntu-zombie-chat.service` terminates the active conversation.
  Warn the operator and obtain approval before applying a runtime change.
