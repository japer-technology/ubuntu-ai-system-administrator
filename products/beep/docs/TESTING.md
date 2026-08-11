# Testing and assurance evidence

## Non-root checks

From the repository root:

```bash
make -C products/beep lint
make -C products/beep test
make -C products/beep package
```

`lint` runs ShellCheck, Bash syntax, and Python compilation. `test` runs:

- unit tests for strict lifecycle state, terminal death, policy fail-closed
  behaviour, runtime permissions, collisions, recovery, history deletion, and
  family tool contracts;
- hermetic CLI and loopback HTTP integration tests for common envelopes,
  required-input exit `64`, kill planning, secret rejection, Host/origin
  checks, strict bounded JSON, fail-closed lifecycle, cookies, export, and
  deletion;
- a machine-readable product parity fixture; and
- installer entrypoint, interactive setup, complete plan, standalone package,
  and product-boundary checks.

The tests use temporary files and loopback servers. They do not install
packages, create users, invoke sudo, mutate systemd, or contact a model or
release service.

## Guarded disposable-VM lifecycle

`tests/vm/lifecycle.sh` mutates real users, sudoers, system packages, systemd,
and reserved paths. It refuses to run unless all of these are true:

- the process is root;
- `BEEP_DISPOSABLE_VM_TEST=1`;
- `/run/beep-disposable-vm` exists; and
- `/etc/os-release` identifies Ubuntu.

Use it only on a disposable supported Desktop LTS VM. It exercises install,
idempotent reinstall, verify, backup, suspend, resume, terminal kill, rejected
revival, tombstone preservation across reinstall, and complete removal.

## Required external matrices

| Gate | Repository evidence | Release evidence state |
| ---- | ------------------- | ---------------------- |
| Source lint, unit, integration, parity | `Makefile`, `tests/` | Automated |
| Package contents and version | `make package` | Automated |
| Release checksum, SBOM, provenance, signatures | `beep-release.yml` | Automated when published |
| Ubuntu 22.04 Desktop `amd64` lifecycle | Guarded harness | Recorded pass still required |
| Ubuntu 24.04 Desktop `amd64` lifecycle | Guarded harness | Recorded pass still required |
| Root-peer co-installation | Namespace and marker assertions | Open |
| Full admitted-family co-installation | Family contract and target suites | Open |
| Update/rollback failure injection on host | Automatic source tests and VM plan | Recorded VM matrix open |
| Independent security review and red team | Threat model and negative source tests | Open |
| Downloaded release verification | `beep-verify-release` | Published-asset run open |

The release test-evidence JSON explicitly records standalone VM and
co-installation as `not_run`; a source suite must never imply those host gates
passed.

Never use real credentials, conversations, audit logs, sibling state, or
personal host data as fixtures.
