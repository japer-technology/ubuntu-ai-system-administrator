# Forgejo and co-located runner repair report

Date: 2026-07-31

Host: `ericmourant-x1`

Project: Ubuntu Zombie

## Executive summary

Ubuntu Zombie had installed Forgejo, PostgreSQL, Caddy, Avahi, Docker, and a
Forgejo Actions runner on the same PC. The services appeared operational, but
the installation was not converged and would not have survived a Forgejo
restart safely:

- Forgejo was running from a configuration it had loaded earlier, but
  `/etc/forgejo/app.ini` had been deleted.
- No recoverable copy of `app.ini` remained in known backup locations or in
  the running process's open file descriptors.
- The runner relied on a manually added systemd drop-in to load
  `/var/lib/forgejo-runner/config.yaml`; the shipped unit ignored that file.
- The runner repeatedly reached Forgejo before port `3000` was ready during
  starts and restarts, producing transient connection-refused errors.
- The installer considered an active runner sufficient verification and did
  not check registration, Docker access, Docker-group membership, or the
  effective runner configuration.
- `verify forgejo` and `doctor forgejo` called Caddy helper functions before
  those functions had been defined in the script's execution path, producing
  misleading `command not found` failures.

The host was repaired without dropping the PostgreSQL database or deleting
repository data. Because the original `app.ini` was irretrievably lost, the
database password and Forgejo security secrets had to be regenerated after a
PostgreSQL backup. Existing browser sessions and values encrypted with the old
lost key may need to be recreated.

## Intended same-host topology

The repaired topology is:

```text
LAN clients
    |
    | HTTPS 443, Caddy internal CA
    v
Caddy (LAN-facing)
    |
    | HTTP loopback
    v
Forgejo 127.0.0.1:3000
    |
    +---- PostgreSQL 127.0.0.1:5432
    |
    +---- Forgejo runner (host process)
              |
              +---- Docker job containers, host network
```

Forgejo and PostgreSQL remain loopback-only. Caddy is the only LAN-facing
application endpoint. The runner registers against
`http://127.0.0.1:3000/`.

Docker job containers normally have a separate loopback namespace, so they
cannot reach a Forgejo instance registered at host `127.0.0.1`. The managed
runner configuration therefore uses `container.network: host`. This is a
deliberate co-location accommodation, not a general recommendation.

## Evidence before repair

The following was observed directly:

- `forgejo.service`, `forgejo-runner.service`, `docker.service`,
  `caddy.service`, and `postgresql.service` were enabled and active.
- Forgejo listened on `127.0.0.1:3000` and PostgreSQL on
  `127.0.0.1:5432`.
- Caddy listened on ports `80` and `443`.
- Both the loopback and HTTPS `/api/healthz` endpoints returned HTTP 200.
- `forgejo.service` specified
  `--config /etc/forgejo/app.ini`, but that pathname was absent even when
  checked as root.
- The running process continued to operate because it had loaded the now-lost
  configuration before deletion. A later restart would have failed.
- The runner's effective command used
  `-c /var/lib/forgejo-runner/config.yaml` only because of
  `/etc/systemd/system/forgejo-runner.service.d/override.conf`.
- The runner was registered and had processed jobs, but journal history showed
  repeated startup races against `127.0.0.1:3000`.
- The runner user belonged to the `docker` group.
- Unprivileged `verify forgejo` produced false missing-file results for some
  root-protected files and emitted `command not found` for Caddy diagnostic
  helpers. The documented command should be run through `sudo` when checking
  protected state.

The deletion mechanism for `app.ini` was not established. It must not be
attributed to the installer without additional audit evidence; subsequent
manual repair work occurred on the host.

## Repair performed

A guarded root repair script performed these steps:

1. Confirmed the missing `app.ini` condition.
2. Searched known local backup locations and the running Forgejo process's
   file descriptors for a valid original configuration.
3. Stopped without mutation when no recoverable copy was found.
4. On the explicitly selected emergency path, created a root-only backup and
   a PostgreSQL custom-format dump before changing credentials.
5. Pinned the already installed versions:
   - Forgejo `15.0.4`
   - Forgejo runner `12.13.0`
6. Re-ran the idempotent Forgejo installer with explicit update and database
   reuse acknowledgements.
7. Reconstructed `/etc/forgejo/app.ini`, reset the PostgreSQL role password,
   generated replacement Forgejo secrets, migrated the existing database,
   and preserved repositories and users.
8. Installed the managed runner configuration and updated runner unit.
9. Removed the now-redundant manual systemd drop-in.
10. Reloaded systemd and restarted the runner.
11. Ran root-level installer verification, Docker-access verification as
    `forgejo-runner`, and loopback/HTTPS health checks.

The authoritative root-only recovery evidence and database dump are under:

`/var/backups/ubuntu-zombie-forgejo-20260731T043645Z/`

This directory contains sensitive configuration material and must not be
attached to a public issue. This report contains no passwords or tokens.

## State after repair

Independent post-repair checks showed:

- All five services are enabled and active.
- Forgejo listens only on `127.0.0.1:3000`.
- PostgreSQL listens only on `127.0.0.1:5432`.
- Caddy listens on HTTPS port `443`.
- Loopback Forgejo health: HTTP 200.
- Caddy HTTPS Forgejo health: HTTP 200.
- The runner's effective command is:

  `/usr/local/bin/forgejo-runner -c /var/lib/forgejo-runner/config.yaml daemon`

- `forgejo-runner.service` requires both `docker.service` and
  `forgejo.service`.
- No systemd drop-in remains.
- The runner declared successfully to Forgejo after restart with label
  `ubuntu-latest`.
- Root-level verification confirmed runner registration state, managed
  host-network configuration, Docker service health, and Docker access for
  the `forgejo-runner` account.

No repository data or database was dropped.

## Installer defects and repository corrections

The working tree contains corrections for the Ubuntu Zombie team:

1. Move read-only Caddy diagnostic helpers above lifecycle dispatch so
   `verify` and `doctor` can call them.
2. Make `forgejo-runner.service` load the managed configuration explicitly.
3. Make the runner unit require both Docker and Forgejo.
4. Install a conservative same-host runner configuration:
   - one concurrent job;
   - no privileged containers;
   - no permitted arbitrary volumes;
   - Docker socket not mounted into job containers by default;
   - host network so job containers can reach host loopback Forgejo.
5. Extend `verify forgejo` to check:
   - `.runner` registration state;
   - effective managed configuration;
   - protected configuration ownership and mode;
   - Docker service state;
   - `forgejo-runner` membership in the `docker` group.
6. Reject empty registration files, fail installation unless the current
   runner invocation declares successfully, and restore root ownership of
   the managed configuration during repair.
7. Add regression tests requiring lifecycle helpers to be defined before
   dispatch and requiring the co-located unit/configuration contract.
8. Correct stale comments that still described Forgejo as binding to all
   network interfaces.
9. Update `docs/FORGEJO.md`, `CHANGELOG.md`, and `VERSION`.

## Further recommendations to the Ubuntu Zombie team

### 1. Make repair fail closed when `app.ini` is absent

`repair forgejo` currently focuses on permissions and restarts. It must never
restart a service whose configured `app.ini` is absent. It should:

- report the missing protected configuration clearly;
- create a PostgreSQL backup before emergency reconstruction;
- distinguish normal convergence from secret-rotation recovery;
- warn that encrypted database values and sessions may be invalidated;
- require a separate explicit acknowledgement for reconstruction.

### 2. Verify readiness, not only systemd activity

`After=forgejo.service` orders unit startup but does not guarantee that
Forgejo is accepting connections. The corrected installer retains
runner restart-on-failure and waits for a successful declaration from the
current runner invocation. Disposable-VM tests should also prove this after a
cold boot, not only during an in-place install.

### 3. Test the Docker-container network path

An active runner process is not end-to-end proof. CI or disposable-VM testing
should run a minimal Action using the default Docker label and prove that the
job can:

- clone from the co-located Forgejo instance;
- report logs and status;
- complete successfully after a cold boot.

### 4. Document the host-network security trade-off

Host networking solves the separate-loopback problem but allows untrusted job
containers to reach other host-loopback services. On this product that can
include PostgreSQL and the Ubuntu Zombie chat service. The runner already has
Docker-daemon reach at the host process level, so co-location is inherently a
high-trust configuration. Limit runner use to trusted repositories and
trusted maintainers.

A stronger future design would use a dedicated Docker bridge and a narrowly
bound Forgejo internal endpoint instead of host networking. That requires
careful certificate, address, and firewall design and should be implemented
and tested as a separate hardening change.

### 5. Make protected-file diagnostics privilege-aware

When an unprivileged user cannot traverse `/etc/forgejo` or
`/var/lib/forgejo-runner`, verification must report `not inspectable without
root`, not `missing`. Documentation should consistently show
`sudo ./scripts/install.sh verify forgejo` for complete results.

### 6. Preserve and test installer ownership

The installer should detect unmanaged systemd drop-ins and either preserve
and report them or remove only an exact obsolete override after confirmation.
Re-running install should leave no manual configuration required for the
supported same-host topology.

## Repository verification

Completed successfully:

- `bash -n scripts/install.sh tests/smoke.sh`
- `bash tests/smoke.sh standards`
- `make test` (with isolated Python cache and missing-secrets paths)
- `git diff --check`
- live service, listener, runner declaration, Docker-access, and HTTP/HTTPS
  checks

The malformed-manifest fixtures now include one valid inert sentinel manifest,
so rejecting the malformed fixture does not fall back to real legacy component
state on an already-installed development host. Production discovery behavior
is unchanged.

`make lint` could not run because `shellcheck` is not installed on this
workstation. It was not installed because the operator has a standing
no-install preference. CI must run the canonical lint target.
