# Changelog

## 2026.08.11.01.50.22

- Add a primary interactive installer that obtains root privileges, validates
  setup answers, shows the complete plan, and preserves unattended lifecycle
  operation.
- Keep legacy adoption behind an adapter-supplied migration manifest while
  removing unrelated product coupling from source, tests, documentation, and
  runtime metadata.
- Tighten service filesystem protection and make release archives contain only
  the standalone product and license.

## 2026.08.11.00.00.30

- Correct the installation marker and shared family schemas, safely migrate the
  exact marker emitted by the first product release, and preserve verified
  artifact provenance during installed-entrypoint repairs.
- Stream PostgreSQL dumps and restores over inherited file descriptors, bind
  rollback archives to their product instance, and preserve primary backup
  errors while reporting completed archives when service restoration fails.
- Enforce the complete HTTPS and runner boundary during repair, failed
  mutations, rollback, suspend, and resume, including persistent runner boot
  intent and suspension across repair or update.
- Preserve ownership when retaining a legacy installation, reject additional
  unmanaged resource collisions, and harden Caddy ownership checks.
- Expand unit, family-contract, and disposable-VM coverage, including failed
  migration recovery.

## 2026.08.10.01.56.59

- Extract the Forgejo server into an independent product lifecycle.
- Preserve PostgreSQL, Caddy, Avahi, local CA trust, secrets, hardening, and
  the loopback application boundary.
- Add verified upstream downloads, ownership-safe legacy adoption, backup,
  update, rollback, repair, suspension, resume, and retained or purged
  uninstall.
- Coordinate server mutations with an installed co-located Actions runner.
- Add unit, integration, family-contract, disposable-VM, packaging, and
  release coverage.
