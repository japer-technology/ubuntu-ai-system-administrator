<!-- triggers: openclaw, openclaw-agent, openclaw-cli, openclawagent -->
# Skill: OpenClaw agent operations

This skill is loaded when the operator asks about an OpenClaw installation,
gateway or agent.

Operating rules:

- Identify the installed OpenClaw build, executable, package source, process
  owner, configuration, workspace and state before acting. Inspect the local
  command help because onboarding and gateway options can change by release.
- Treat onboarding as a security review, not a harmless wizard. Before
  accepting choices, explain the provider credentials, channels, tools,
  persistence and network listeners that will be enabled.
- Keep the gateway loopback-only by default. Do not expose it through a
  wildcard bind, reverse proxy, tunnel or firewall opening without explicit
  operator approval and a reviewed authentication design.
- Run OpenClaw separately from Ubuntu Zombie: a distinct unprivileged user,
  state tree, secrets and service. Never reuse Ubuntu Zombie's sudo access,
  provider secrets, policy file or loopback chat endpoint.
- Review extensions, skills and connectors as executable third-party code.
  Pin versions and grant the narrowest workspace, network and shell access
  needed. An OpenClaw approval must not stand in for Ubuntu Zombie's gate.
- Use native status, doctor and dry-run facilities where the installed
  version offers them. Bound log output, redact tokens and channel payloads,
  and verify both process health and the expected listening address.
- Before upgrade or removal, back up operator-owned configuration and state,
  identify managed versus user data, and provide a rollback or export path.
  Never use a remote `curl | bash` installer.
- Follow the broader `ai-agents` skill for multi-agent delegation, secret
  separation, plugin trust, cancellation and audit requirements.
