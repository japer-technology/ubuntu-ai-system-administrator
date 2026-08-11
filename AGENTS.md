# AGENTS.md

Guidance for AI coding agents (Claude Code, Codex, Copilot, Cursor,
Aider, etc.) working in this repository. Human contributors should
read [`CONTRIBUTING.md`](CONTRIBUTING.md) first; this file restates
the bits an autonomous agent is most likely to get wrong.

## What this repository is

Ubuntu Zombie is a Bash + Python installer that adds a private,
root-capable AI Systems Administrator account (`agent`) to an Ubuntu
Desktop LTS machine. The whole product ships as shell scripts and a
small Python service. There is no compiled artifact and no package
manager registry — a "release" is a tarball produced by `make package`.

Read these before changing anything substantive:

- [`README.md`](README.md) — entry point and trust model summary.
- [`docs/VISION.md`](docs/VISION.md) — explicit in-scope / out-of-scope.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, action
  classes, trust boundaries.
- [`SECURITY.md`](SECURITY.md) — threat model and disclosure policy.
- [`CONTRIBUTING.md`](CONTRIBUTING.md) — full conventions, including
  the provider and policy-class extension recipes.

## Repository layout

```
scripts/
  install.sh              # main installer (idempotent; install/verify/doctor/repair/uninstall)
  uninstall.sh            # uninstaller
payload/                  # files copied to /opt/ai-zombie/ on the target
  agent/                  # Python chat service (audit, history, policy, providers, runner, server)
  bin/                    # operator helpers (verify, secrets-edit, collect-diagnostics, ...)
  etc/policy.yaml         # default policy gate
  systemd/                # unit files
  logrotate/              # rotation rules
tests/smoke.sh            # non-root checks: syntax, python compile, subcommands, noninteractive, standards
docs/                     # user docs + docs/design-notes/ background essays
.github/workflows/ci.yml  # CI: lint, smoke tests, package, secret scan
Makefile, VERSION
```

## Commands

Run these from the repo root. They are the same commands CI runs.

```bash
make lint     # shellcheck (warning+) on every bash file, bash -n, python compile
make test     # tests/smoke.sh all (syntax, python, subcommands, noninteractive, standards)
make package  # produce dist/ubuntu-zombie-$(cat VERSION).tar.gz
```

Always run `make lint` and `make test` after editing shell or Python.
Both must pass before you hand work back. They require `bash`,
`shellcheck`, and `python3` — nothing else.

Do **not** run `make install-local` or `scripts/install.sh install`
from an agent environment, your workstation, or any machine you are
not prepared to wipe. The installer mutates users, sudoers, and systemd
units; it is intended only for
a disposable Ubuntu Desktop LTS VM. The same applies to `uninstall.sh`,
`secrets-edit`, and anything under `/opt/ai-zombie/`.

## Non-negotiable rules

These come from `CONTRIBUTING.md` and the trust model. Violating any
of them will get a change rejected.

1. **Idempotence.** `scripts/install.sh install` must converge on
   re-run without errors. Any new step that creates files, users,
   or services must check current state first.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must work
   end-to-end; CI depends on it. Missing required env in
   non-interactive mode exits `64`.
3. **Policy gate + audit log.** Any new privileged behaviour must go
   through `payload/agent/policy.py` and be recorded by
   `payload/agent/audit.py`. Do not call `sudo` from new code paths
   without a matching policy class.
4. **No secrets in the repo.** CI fails on long `sk-…`, `sk-ant-…`,
   or `tskey-auth-…` values. Use placeholders like `sk-...` in docs.
5. **No new runtime dependencies** outside the set the installer
   already installs (see `CONTRIBUTING.md` → Conventions for the
   exact list). Standard library is always fine.
6. **No commits of local state, screenshots, or diagnostics.**

## Code conventions

- **Bash:** `#!/usr/bin/env bash`, `set -Eeuo pipefail`,
  ShellCheck-clean at `--severity=warning`. Quote expansions. Wrap
  long lines with `\` rather than disabling shellcheck rules. New
  shell helpers under `payload/bin/` are linted even without a `.sh`
  extension, so keep the bash shebang.
- **Python:** 4-space indent, type hints on public functions, no
  third-party deps beyond those the installer installs. Files must
  pass `python3 -m py_compile`. Match the style of the surrounding
  module (`payload/agent/*.py`).
- **Markdown:** wrap at ~78 columns where reasonable. Reference
  files with backticked relative paths so links work on GitHub.
- **Commits:** imperative subject under 72 characters. Group related
  changes.

## Extending the system

Follow the recipes in `CONTRIBUTING.md` literally — they encode
invariants the runtime relies on:

- **New LLM provider:** implement `BaseProvider` in
  `payload/agent/providers.py`, register in `provider_from_env()`,
  document env vars in `docs/CONFIGURATION.md`, and add an import
  smoke test in `tests/smoke.sh`.
- **New policy class:** add it to `payload/etc/policy.yaml`, handle
  it in `payload/agent/policy.py`, and describe it in
  `docs/ARCHITECTURE.md`.
- **New installer subcommand:** add it to `scripts/install.sh`,
  list it in `README.md`'s Subcommands block, and extend the
  `subcommands` case in `tests/smoke.sh` so CI checks parsing.

## Before handing work back

- [ ] `make lint` is clean.
- [ ] `make test` is clean.
- [ ] If you touched `scripts/install.sh`, you re-checked
      idempotence and the `ZOMBIE_NONINTERACTIVE=1` path.
- [ ] If you touched anything under `payload/agent/`, you verified
      no new `sudo`/privileged action bypasses the policy gate or
      audit log.
- [ ] `docs/` and `README.md` reflect any user-visible change
      (subcommands, env vars, defaults).
- [ ] `CHANGELOG.md` has an entry under the appropriate unreleased
      section for user-visible changes.
- [ ] If `CHANGELOG.md` was updated, `VERSION` was also updated in
      `yyyy.mm.dd.hh.nn.ss` UTC format with:
      `date -u +%Y.%m.%d.%H.%M.%S > VERSION`
- [ ] No secrets, screenshots, or local state are staged.

## Things to leave alone unless explicitly asked

- `LICENSE`, `CODE_OF_CONDUCT.md`, `SECURITY.md` disclosure section.
- `docs/design-notes/` — historical context; treat as read-only.
- `.github/CODEOWNERS` and workflow permissions.
