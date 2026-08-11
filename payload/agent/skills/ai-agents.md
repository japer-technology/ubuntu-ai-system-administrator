<!-- triggers: ai-agent, ai-agents, agentic, subagent, subagents, multi-agent, multiagent, orchestration, orchestrator, mcp, a2a, tool-calling, toolcalling -->
# Skill: AI agent management

This skill is loaded when the operator manages agent runtimes, tool servers,
delegated workers or multi-agent workflows.

Operating rules:

- Establish which product and instance is meant before acting. Record the
  executable path, version, service/user, working directory, configuration
  roots, provider endpoint and state location without exposing credentials.
- Treat an agent as executable automation, not as a model setting. Inventory
  its tools, filesystem reach, network listeners, delegated identities,
  approval model, persistence and audit trail before enabling it.
- Keep agents isolated under dedicated unprivileged users or containers.
  Grant only the directories and tools required for the task; do not share
  Ubuntu Zombie's account, sudoers entry, secrets file or writable state.
- A skill, MCP server, extension or plugin is code from another trust domain.
  Pin its source and version, inspect its requested capabilities, and require
  explicit operator approval before installation or activation.
- Avoid recursive delegation. Set finite task, tool-call and time budgets;
  identify the parent responsible for approvals; and ensure cancellation
  reaches every child. Never let one agent approve another agent's privileged
  action.
- Bind local control planes to loopback unless the operator has designed and
  approved authentication, encryption and firewall rules for remote access.
  Check existing listeners before starting another gateway.
- Keep provider credentials in each runtime's supported secret store. Confirm
  that a credential exists without printing its value, and never copy keys
  between agents through chat, logs or command-line arguments.
- Use native status, doctor and dry-run commands before manual repair. Back up
  configuration and state, make one reversible change at a time, then inspect
  logs and run a bounded health check.
- Ubuntu Zombie can inspect or manage another runtime only through its closed
  tools and policy gate. A skill cannot add a tool or delegate approval.
- Report the exact instance affected, actions and approvals used, residual
  listeners/processes, and where the runtime records its own audit history.
