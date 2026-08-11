# Supported platforms

This is the canonical statement of what Ubuntu Zombie supports. Every
other doc that mentions versions or architectures should link here.

## Hosts

| OS                     | Architecture | Status        | Notes                                                        |
| ---------------------- | ------------ | ------------- | ------------------------------------------------------------ |
| Ubuntu Desktop 24.04 LTS | `amd64`    | **Supported** | Primary target. CI runs on `ubuntu-24.04` runners.           |
| Ubuntu Desktop 22.04 LTS | `amd64`    | **Supported** | CI runs on `ubuntu-22.04` runners.                           |
| Ubuntu Desktop 24.04 LTS | `arm64`    | Best-effort   | Installer code paths exist. Not exercised in CI; report issues. |
| Ubuntu Desktop 22.04 LTS | `arm64`    | Best-effort   | Same caveats as 24.04 arm64.                                 |
| Ubuntu Server (any)    | any          | **Unsupported** | The installer targets Ubuntu Desktop LTS and is not tested on Server. |
| Other Ubuntu flavours (Kubuntu, Xubuntu, …) | any | Best-effort | Report flavour-specific issues with full diagnostics. |
| Debian, Mint, PopOS, other Debian derivatives | any | **Unsupported** | The installer reads `/etc/os-release` and refuses to proceed unless `ID=ubuntu`. |
| Non-LTS Ubuntu (24.10, 25.04, …) | any | **Unsupported** | The installer warns and continues, but you are on your own. We test only LTS. |
| WSL, containers without systemd | any | **Unsupported** | The chat service is a `systemd` unit. Without systemd, nothing runs. CI's integration job uses containers solely for the `--dry-run` path. |

## Python

The chat service runs under the system Python that ships with the
host:

- Ubuntu 22.04 → Python 3.10
- Ubuntu 24.04 → Python 3.12

CI exercises both interpreters in the matrix. No other Python
versions are supported.

## Node.js

The installer pins Node.js to **22.x** from the official NodeSource
apt repository. Earlier versions cannot self-upgrade `npm` (see
CHANGELOG.md for the gory detail). Do not override.

## Network requirements

- **Outbound**: HTTPS to `archive.ubuntu.com`, `deb.nodesource.com`,
  `registry.npmjs.org`, `pypi.org`, and the configured LLM provider's
  API endpoint.
- **Inbound**: Ubuntu Zombie opens no inbound network listener. The chat
  service binds to `127.0.0.1` only.

## What "Supported" means

A platform listed as **Supported** has the following guarantees:

1. CI exercises lint, smoke, dry-run, and (nightly) container install
   on that platform.
2. Issues filed against that platform are triaged.
3. Release artifacts are tested against that platform before tagging.

**Best-effort** platforms get bug-fix attention when somebody files
a clear, reproducible report, but are not guaranteed to keep working
release-to-release.

**Unsupported** platforms will not be debugged.
