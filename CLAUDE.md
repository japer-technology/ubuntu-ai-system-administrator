# CLAUDE.md

This repository uses a single source of truth for AI-agent guidance:
[`AGENTS.md`](AGENTS.md). Claude Code, please read it before making
changes. Everything that applies to other coding agents applies to
Claude as well.

Quick reminders specific to working in this repo:

- Run `make lint` and `make test` after every change; both must
  pass. They are the same checks CI runs.
- Do **not** execute `scripts/install.sh install`, `make
  install-local`, `scripts/uninstall.sh`, or any helper under
  `/opt/ai-zombie/` from an agent environment or any machine you
  are not prepared to wipe — they mutate a real Ubuntu Desktop
  system. Use a disposable VM.
- The installer must stay idempotent and must work with
  `ZOMBIE_NONINTERACTIVE=1`. Any privileged behaviour goes through
  the policy gate (`payload/agent/policy.py`) and the audit log
  (`payload/agent/audit.py`).
- No secrets in commits; CI scans for `sk-…`, `sk-ant-…`, and
  `tskey-auth-…` patterns.

See [`AGENTS.md`](AGENTS.md) for the full conventions, layout,
extension recipes (new provider, new policy class, new subcommand),
and the pre-handoff checklist.
