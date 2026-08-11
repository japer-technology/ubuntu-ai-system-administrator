# Research notes

The files in this directory are **research notes**, not product
documentation. They were written while exploring the design space of
Ubuntu Zombie:

- `ALTERNATIVES.md` and `ALTERNATIVES-LESSONS.md` — the broad survey
  of how other people have tried to build "an AI sysadmin on a Linux
  box", and what we took away from each attempt.
- `ALTERNATIVE-*.md` — deep-dive notes on individual alternatives we
  evaluated (LinuxAgent, LinuxOSAI, Missy, SysAdminAgents, SysKnife).
- `SIMILAR.md` — a shorter catalog of adjacent projects that overlap
  with parts of the design.
- `OPEN-WEBUI-POSSIBILITIES.md` and `OPEN-WEBUI-LESSONS.md` — a study
  of the Open WebUI chat platform (what it offers, and which of its
  capabilities Zombie's chat should borrow, translate, defer, or
  refuse) and the distilled lessons for making Zombie's local chat —
  the operator's only interface — world class.
- `OPEN-WEBUI-LESSONS-PLAN.md` — a phased implementation plan that
  turns the distilled shortlist in `OPEN-WEBUI-LESSONS.md` into
  concrete work items against the current codebase.
- `OPEN-WEBUI-LESSONS-PLAN-PHASE-A.md` — a detailed, step-by-step
  implementation plan for Phase A of that plan (SSE streaming of
  tool activity and tokens; never losing operator input during a
  busy turn), grounded in the current turn transport.

If you are trying to **use** Ubuntu Zombie, you almost certainly want
[`docs/QUICKSTART.md`](../QUICKSTART.md),
[`docs/CONFIGURATION.md`](../CONFIGURATION.md),
[`docs/TROUBLESHOOTING.md`](../TROUBLESHOOTING.md), or
[`docs/ARCHITECTURE.md`](../ARCHITECTURE.md) instead.

These files are kept because they explain *why* the product looks the
way it does. They are not maintained as carefully as the user-facing
docs and may drift from the current implementation.
