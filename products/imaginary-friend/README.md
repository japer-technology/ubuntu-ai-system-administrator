# Imaginary Friend

Imaginary Friend is a private, single-owner conversational companion with
access only to its own state and explicitly nominated workspaces. It runs as an
unprivileged service with a password-protected loopback interface.

## Install

Start the configured OpenAI-compatible local model, then run the installer on a
supported Ubuntu Desktop 22.04 or 24.04 LTS `amd64` host:

```bash
cd products/imaginary-friend
./scripts/install.sh
```

The installer obtains root privileges with `sudo` when needed. It asks for the
human owner, owner password, local model, and retention settings, then displays
the complete plan and applies it only after approval. Press Enter to accept a
displayed default; leaving the password empty generates a strong password shown
once after installation.

On success, open `http://127.0.0.1:6767/`.

## Safety first

The lifecycle installer creates users, groups, systemd units, protected state,
and workspace permissions. Test installation only on a disposable supported
Ubuntu Desktop LTS VM. Do not run it on an agent host or workstation you are
not prepared to rebuild.

Friend is not a system administrator, shell, coding sandbox, network agent, or
security boundary against root. A same-host machine administrator can inspect
its unencrypted local state.

## Manage

After installation:

```bash
sudo friend-manage verify
sudo friend-manage doctor
sudo friend-manage repair --dry-run
sudo friend-manage backup
sudo friend-manage update
sudo friend-manage suspend
sudo friend-manage resume
sudo friend-manage uninstall
```

For unattended installation, provide the required `FRIEND_*` inputs and run
`sudo ./scripts/manage.sh install --yes --non-interactive`.

## Documentation

- [`docs/VISION.md`](docs/VISION.md) — purpose, users, and excluded uses.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — components and trust
  boundaries.
- [`docs/SECURITY.md`](docs/SECURITY.md) — threat model, controls, residual
  risks, and disclosure.
- [`docs/PRIVACY.md`](docs/PRIVACY.md) — data, provider disclosure, retention,
  export, and deletion.
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — install inputs, runtime
  settings, authentication, and HTTP interfaces.
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md) — install, verify, repair,
  suspend, and removal.
- [`docs/UPGRADING.md`](docs/UPGRADING.md) — backup, update, and rollback.
- [`docs/RECOVERY.md`](docs/RECOVERY.md) — drift, account recovery, and retained
  state.
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md) — diagnostics and stable
  lifecycle failures.
- [`docs/RELEASE.md`](docs/RELEASE.md) — product versions, artifacts, SBOM,
  provenance, and signatures.
- [`docs/TESTING.md`](docs/TESTING.md) — test suites and assurance coverage.

## Development

From the product directory:

```bash
make lint
make test
make package
```

These commands do not install the product. Root lifecycle testing is guarded
and belongs only on a disposable VM; see
[`docs/TESTING.md`](docs/TESTING.md).
