# Pinned runtime inputs and provenance

Beep maintains its chat authentication, session handling, provider adapters,
conversation history, reactivation, policy, audit, runner, closed tool
registry, lifecycle, and family manager within this product source.

The prompt templates, skills, operator helpers, systemd assets, log rotation,
default policy, module names, paths, credentials, cookie, port, lifecycle
state, catalogue, inventory, receipts, and commands are all Beep-owned.

The runtime pins Node `22.23.2` and verifies its upstream archive digest.
`payload/agent/bridge-dependencies.lock` pins each npm bridge package version,
URL, integrity digest, licence, and source. Release artifacts record the exact
Beep commit, test result, SPDX SBOM, checksums, GitHub attestation, and cosign
signature material.

Beep does not import or install files from another product's runtime or state.
Runtime changes require a reviewed Beep change and a new Beep version.
