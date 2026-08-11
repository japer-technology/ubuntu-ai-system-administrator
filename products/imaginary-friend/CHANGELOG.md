# Imaginary Friend changelog

Imaginary Friend uses independent UTC date-time versions in
`yyyy.mm.dd.hh.nn.ss` format.

## [Unreleased]

### Changed

- Add a primary interactive installer that obtains root privileges, validates
  setup answers, displays all non-secret settings and the complete plan, and
  preserves unattended lifecycle operation.
- Remove unrelated product names and source, runtime, test, documentation, and
  release-package coupling.

### Fixed

- Preserve the paired previous-version runtime and recovery snapshot across
  same-version repair and reinstall, while retaining failure recovery for the
  active operation.
- Prevent workspace moves from replacing a concurrently created destination,
  keep the live audit path writable across log rotation, reject fractional
  lifecycle retention inputs, and create diagnostics archives exclusively.
- Export every retained conversation from one consistent database snapshot,
  keep conversations beyond the UI's former 100-record ceiling accessible,
  and disclose an explicitly selected workspace file for one turn only.
- Reject oversized model replies before they can make retained conversations
  unusable, validate owner passwords against the runtime's exact format and
  size limits, and allow the loopback service to restart promptly.
- Audit invalid workspace-path denials and require setgid inheritance on
  existing shared roots so Friend-created files retain `friend-share` access.
- Preserve suspension across reinstall and update, recompute existing history
  expiry when its retention window changes, reject lifecycle inputs that the
  selected operation cannot apply, and retain correlation in unexpected
  failure responses and audit events while recording the correct operation
  phase and failure type.
- Require the `friend` service identity to have only its product groups and
  verify that a suspended service is stopped.

### Added

- Initial standalone implementation with one owner, authenticated local chat,
  bounded workspaces, retention and export, local-model access, and the full
  product-owned lifecycle interface.
- Independent policy, audit, credentials, systemd confinement, packaging,
  tests, and operator documentation.
- Product-owned vision, architecture, security, privacy, configuration,
  installation, upgrading, recovery, troubleshooting, release, and test
  evidence, with an explicit record of remaining release assurance gates.
- Regression and negative-boundary coverage for suspension convergence,
  retention changes, service groups, lifecycle input isolation, failure
  correlation, sandbox assets, and the guarded disposable-VM lifecycle.
