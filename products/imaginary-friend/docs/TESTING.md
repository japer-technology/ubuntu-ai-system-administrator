# Testing and assurance evidence

## Non-root checks

Run from the product directory:

```bash
make lint
make test
make package
```

`lint` runs ShellCheck, Bash syntax checks, and Python compilation. `test`
runs unit, hermetic integration, HTTP, and lifecycle tests. Model tests use
`tests/fixtures/openai_fixture.py`; they do not require a real model or
external network.

Coverage includes scrypt authentication, session and CSRF revocation, strict
configuration, complete and consistent exports, retention, secret redaction,
loopback-only model transport, bounded conversation context, one-turn selected
file disclosure, policy denial and audit evidence, workspace traversal/symlink/
hard-link/special-file controls, atomic no-clobber conflicts, systemd boundary
assets and rotation paths, exclusive diagnostic archives, lifecycle plans,
rollback preservation, strict input types, descriptor validation, and source
independence.

## Disposable-VM lifecycle

`tests/vm/lifecycle.sh` refuses to run unless it is root and
`IMAGINARY_FRIEND_DISPOSABLE_VM_TEST=1` is set. It mutates real users, groups,
systemd, and reserved paths. Run it only on a disposable Ubuntu Desktop 22.04
or 24.04 LTS `amd64` VM with a non-root test owner.

The harness exercises missing-input exit `64`, dry-run non-mutation, install,
identity and file permissions, service-account denial, verify, idempotent
reinstall, suspension preservation, resume, backup, rollback, retained-state
recovery, complete uninstall, and workspace preservation against a hermetic
loopback model.

## Evidence and open gates

| Gate | Repository evidence | State |
| ---- | ------------------- | ----- |
| Product source and fixed slice | `payload/`, `PRODUCT.json`, product documentation | Implemented |
| Unit and integration tests | `tests/unit/`, `tests/integration/` | Automated |
| Standalone host lifecycle | `tests/vm/lifecycle.sh`, integration workflow | Requires recorded supported-VM pass per release |
| Negative security boundary | policy, workspace, model, HTTP, asset, and VM tests | Implemented set; continued red-team review required |
| Artifact verification | release workflow | Independent signed release |

Never use real personal conversations, credentials, workspace contents, child
data, or sibling secrets as fixtures.
