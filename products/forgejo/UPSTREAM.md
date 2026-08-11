# Upstream inputs

The lifecycle installs official Forgejo Linux binaries from Forgejo's release
service, with Codeberg as a fallback. Every binary must match the adjacent
upstream `.sha256` file before installation.

`FORGEJO_VERSION` can pin a release such as `11.0.3`. With no pin, a new
installation resolves `latest` once and records the resolved version,
checksum, and source URL in `/etc/forgejo/binary.json`. Repair reuses that
recorded release. Update is the operation that intentionally resolves or
selects another release.

Release metadata and assets are accepted only over HTTPS from the allowlisted
Forgejo origins. Loopback HTTP fixtures are enabled only by the guarded
disposable-VM test sentinel.
