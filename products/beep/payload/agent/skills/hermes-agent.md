<!-- triggers: hermes, hermes-agent, hermes-cli, hermesagent -->
# Skill: Hermes agent operations

This skill is loaded when the operator asks about a Hermes agent installation
or runtime.

Operating rules:

- Confirm the product is Hermes Agent and discover its executable, version,
  installation method, process owner, configuration and state paths before
  suggesting commands. Do not infer a layout from the name alone.
- Prefer Hermes' own help, status, doctor and session commands for the
  installed version. Command surfaces evolve; inspect `--help` rather than
  copying commands from unrelated Beep research notes.
- Treat onboarding, provider login, messaging-channel setup, tool/plugin
  installation and background-service enablement as separate operator
  decisions. Explain files, listeners and credentials each step creates.
- Never paste tokens into chat or command arguments. Use Hermes' documented
  secret mechanism and confirm presence without reading values back.
- Inventory enabled tools and integrations before running a task. Restrict
  workspace access, disable unused network channels and require explicit
  approval for shell, filesystem mutation or external side effects.
- Do not point Hermes at Beep's secrets, sudoers rule, state
  directory or chat port. Run it as a separate unprivileged identity and
  avoid competing service names or listeners.
- Before upgrades, identify the package source and pinned/current version,
  preserve configuration and sessions, read the migration notes, and retain a
  rollback path. Do not pipe an upstream install script into a shell.
- For faults, collect bounded status and logs with secrets redacted, check the
  provider and channel independently, and change one layer at a time.
- Follow the broader `ai-agents` skill for delegation, plugin trust, network
  exposure and audit requirements.
