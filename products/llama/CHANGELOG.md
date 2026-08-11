# Llama changelog

Llama uses independent UTC date-time versions in `yyyy.mm.dd.hh.nn.ss`
format.

## [Unreleased]

### Added

- Initial independent product with a pinned CPU `llama.cpp` runtime, verified
  model catalogue, loopback-only service, complete lifecycle, packaging,
  release automation, tests, and operator documentation.
- Safe adoption of the previous Ubuntu Zombie-managed Llama component without
  changing its account, paths, service, API port, or model.
- Compatibility delegation from Ubuntu Zombie without duplicate lifecycle
  logic or payload assets.
- Fixture-backed supported-VM coverage for install, idempotence, health,
  backup, update, rollback, suspension, retained-state recovery, purge, and
  post-purge reinstall.

### Fixed

- Create the lifecycle log boundary with protected root ownership so clean
  installs and idempotent repairs pass their ownership gate.
- Resolve model, rollback, and backup paths before enforcing product boundaries,
  preventing traversal through parent components or symlinked ancestors.
- Verify systemd stop and disable post-conditions before repair, rollback,
  suspension, or removal continues.
- Restart an active service after live configuration, runtime, model, manager,
  or unit changes, and keep repeated `resume` operations idempotent.
- Record blocked lifecycle operations as denied audit decisions.
- Verify the exact legacy unit and model checksum before adoption or removal.
- Preserve protected audit evidence after purge without blocking a later clean
  installation.
