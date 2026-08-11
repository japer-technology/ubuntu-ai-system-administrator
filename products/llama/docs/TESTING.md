# Testing and assurance

## Non-root checks

From the repository root:

```bash
make -C products/llama lint
make -C products/llama test
make -C products/llama package
```

Tests use only the Python standard library and do not download the runtime or
model. Coverage includes descriptor and catalogue validation, fixed loopback
configuration, operation-scoped inputs, deterministic non-mutating plans,
archive traversal and link rejection, marker ordering, protected runtime
arguments, canonical path boundaries, verified service-state transitions,
response envelopes, fail-closed environment handling, and shared contract
conformance.

## Disposable-VM lifecycle

`tests/vm/lifecycle.sh` refuses to run unless root and
`LLAMA_DISPOSABLE_VM_TEST=1` are present. It builds tiny checksum-pinned local
fixture assets in a temporary copy of the product, then exercises clean
install, health, doctor, repair, disabled boot, idempotent reinstall, backup,
suspend, resume, update, rollback, retained-state recovery, complete removal,
post-purge reinstall, and a protected Ubuntu Zombie sibling canary. Run it only
on a disposable Ubuntu Desktop 22.04 or 24.04 LTS VM.

Real release evidence must additionally use the published runtime and model,
verify the OpenAI-compatible API, and record resource isolation from Ubuntu
Zombie and every installed sibling.

## Open gates

Source, static tests, packaging, guarded VM automation, and release machinery
can be reviewed in the repository. Catalogue admission remains open until a
published version's checksums, SBOM, provenance, signatures, supported-VM
evidence, and co-installation evidence have all been independently verified.
