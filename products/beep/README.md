# Beep

Beep is an independent, private, root-capable AI Systems Administrator for
Ubuntu Desktop LTS. It owns the `beep` identity, loopback chat, credentials,
policy, history, audit, lifecycle, family manager, package, and release.

The standalone source, lifecycle, family manager, tests, package, and release
workflow are implemented. Beep is not yet admitted to the production family
catalogue: recorded supported-VM, root-peer co-installation, external security
review, and published release-verification evidence remain release gates.

## Install

On a supported Ubuntu Desktop 22.04 or 24.04 LTS host, run:

```bash
./scripts/install.sh
```

The installer obtains root privileges with `sudo` when needed, asks the setup
questions, displays the complete plan, and applies it only after approval.
Press Enter to accept secure defaults. The chat password and any provider
credential are entered through protected prompts and are never printed.

## Root-equivalent warning

The installer creates a password-disabled `beep` account with passwordless
`sudo`. A compromised model, chat service, credential, policy, dependency, or
approved command can compromise the entire host. Installing Beep alongside
another root-capable service increases the host's attack surface; it does not
create redundancy or containment.

Run installation and lifecycle tests only on a disposable supported Ubuntu
Desktop 22.04 or 24.04 LTS `amd64` VM that you are prepared to rebuild.

## Documentation

- [`docs/VISION.md`](docs/VISION.md) — purpose, parity, users, and non-goals.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components, data flow, and
  trust boundaries.
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model, controls, residual
  root-equivalent risk, and reporting.
- [`docs/PRIVACY.md`](docs/PRIVACY.md) — local and provider data, retention,
  export, and deletion.
- [`docs/OPERATIONS.md`](docs/OPERATIONS.md) — policy, tools, approvals, audit,
  TTL, reactivation, and family management.
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — lifecycle inputs,
  providers, credentials, and runtime configuration.
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) — release verification,
  install, verify, suspend, kill, and removal.
- [`docs/UPGRADING.md`](docs/UPGRADING.md) — backup, update, automatic recovery,
  and rollback.
- [`docs/RECOVERY.md`](docs/RECOVERY.md) — failure states and bounded recovery.
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) — diagnostics and stable
  lifecycle failures.
- [`docs/TESTING.md`](docs/TESTING.md) — automated evidence and open VM gates.
- [`docs/RELEASE.md`](docs/RELEASE.md) — independent artifacts, signatures,
  provenance, and verification.

## Development

From the repository root:

```bash
make -C products/beep lint
make -C products/beep test
make -C products/beep package
```

These commands do not install Beep. Do not run `scripts/install.sh`,
`scripts/manage.sh install`, or the guarded VM harness on a workstation or
agent environment.
