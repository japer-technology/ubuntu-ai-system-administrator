# Upgrading and rollback

Imaginary Friend versions, artifacts, state, and rollback data are
product-owned. An update restarts only `imaginary-friend-chat.service`.

## Before update

1. Read the product changelog and release notes.
2. Verify the exact product artifact, checksums, SBOM, provenance, and cosign
   bundle as described in [`RELEASE.md`](RELEASE.md).
3. Run `friend-manage status`, `verify`, and an update dry-run.
4. Create a product backup in a root-owned, non-symlink directory outside
   Friend state and all nominated workspaces.
5. Preserve the current JSON response, receipt digest, and correlation ID.

## Update

Run the newer verified product's `scripts/manage.sh update`. Update refuses a
downgrade, validates platform and model health, snapshots compatible state,
stages root-owned code, switches only Friend resources, and performs the
health and boundary gates before writing the new marker and receipt.

Credentials, history, settings, workspace nominations, instance ID, and
suspension are preserved unless a documented migration explicitly changes a
format. An update never owns or migrates workspace file contents.

## Rollback

`friend-manage rollback --dry-run --json` reports whether a previous runtime
and compatible recovery snapshot exist. Approved rollback stops Friend,
swaps the product-owned runtime, restores compatible Friend state and
configuration, validates the restored service, and records the restored
version. It preserves suspension and does not change unrelated services.

If a switch fails, the updater attempts to restore the current runtime and
state and leaves root-only recovery data for `doctor`. Do not delete
`/opt/.imaginary-friend-rollback` or
`/var/lib/imaginary-friend/recovery` while diagnosing a failed update.
Same-version repair and reinstall also preserve those paired rollback
resources.

The first schema has no historical migration. Future releases must document
supported source versions, migration validation, and rollback compatibility
before changing it.
