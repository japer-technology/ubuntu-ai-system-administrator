# Contributing

Thanks for taking the time to look at Ubuntu AI System Administrator.

## Ground rules

- The installer must remain idempotent. Re-running `install` must
  converge to the desired state without errors.
- The installer must work in non-interactive mode for CI.
- New external commands must be justified, version-pinned where
  practical, and retried on transient network failures.
- New privileged behaviour must go through the policy gate and the
  audit log.
- No commits of secrets, screenshots, or local state. The
  `.gitignore` already excludes the common cases.

## Local development

```bash
git clone https://github.com/japer-technology/ubuntu-ai-system-administrator.git
cd ubuntu-ai-system-administrator
make lint     # ShellCheck + bash -n + python compile
make test     # smoke tests (no root required)
```

You need:

- `bash`, `shellcheck`, `python3` for `lint` and `test`;
- a disposable Ubuntu Desktop LTS VM for `make install-local`.

## Layout

See `docs/ARCHITECTURE.md` for components. The repository roughly mirrors
what ends up on a target machine:

```
.
├── scripts/
│   ├── install.sh                # main installer
│   └── uninstall.sh              # uninstaller
├── payload/                      # files copied to /opt/ai-zombie/
│   ├── agent/                    # Python chat service
│   ├── bin/                      # operator helpers
│   ├── etc/policy.yaml           # default policy
│   ├── systemd/                  # unit files
│   └── logrotate/                # rotation rules
├── tests/
│   └── smoke.sh                  # syntax + non-interactive checks
├── docs/                         # user-facing docs and design notes
├── Makefile
├── VERSION
├── README.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── CODE_OF_CONDUCT.md
├── LICENSE
└── SECURITY.md
```

## Running tests

`tests/smoke.sh` runs without root and without changing system state:

- `bash -n` on the installer and every shipped shell helper;
- `python3 -m py_compile` on every shipped Python file;
- a check that the installer recognises every documented subcommand;
- checks for the non-interactive dry-run and lifecycle guard paths.

CI runs the same script on every push and pull request, plus
`shellcheck` on every shell file.

## Conventions

- Shell: `#!/usr/bin/env bash`, `set -Eeuo pipefail`, ShellCheck
  clean. Wrap long lines with `\` rather than disabling rules.
- Python: 4-space indent, type hints on public functions, no
  third-party dependencies outside what the installer already
  installs (`requests`, `pydantic`, `rich`, `typer`,
  `python-dotenv`, plus the standard library). Provider calls go
  through the Node `@earendil-works/pi-ai` bridge, not a Python SDK.
- Docs: Markdown, line-wrapped at ~78 characters where reasonable.
- Commits: imperative subject lines under 72 characters.

## Adding a provider

1. Implement `BaseProvider` in `payload/agent/providers.py`.
2. Register it in `provider_from_env()`.
3. Document the env vars in `docs/CONFIGURATION.md`.
4. Add a smoke test in `tests/smoke.sh` for the import.

## Adding a policy class

1. Add the class and matching patterns to `payload/etc/policy.yaml`.
2. Add a handler in `payload/agent/policy.py`.
3. Document the class in `docs/ARCHITECTURE.md`.

## Installer scope

`scripts/install.sh` has one subject: Ubuntu AI System Administrator. Its public lifecycle is
`install`, `verify`, `doctor`, `repair`, and `uninstall`. Infrastructure or
applications that are not part of the Ubuntu AI System Administrator runtime are out of scope
for this repository and must not be added as positional install selections or
environment-controlled side installs.

## Filing an issue

Please attach a redacted diagnostic bundle when reporting installer
failures:

```bash
sudo /opt/ai-zombie/bin/collect-diagnostics
```

Security issues: see `SECURITY.md` for responsible disclosure.
