# Llama security model

## Authority

The running model service has the permissions of `llama-cpp`. It can read the
selected model and runtime and write only its state and log directories.
It has no sudo rule, shell login, Ubuntu Zombie policy authority, home-directory
access, or general host-administration interface.

The root lifecycle may create and remove only resources declared in
`PRODUCT.json`. Ownership markers do not authorise unexpected paths, accounts,
units, or ports.

## Supply chain

Runtime and model catalogues pin exact HTTPS sources and lowercase SHA-256
digests. Model URLs pin an immutable upstream revision. Downloads are bounded,
redirects remain on approved HTTPS asset hosts, and archives reject absolute
paths, traversal, devices, FIFOs, and escaping links. Extracted runtime files
receive a local tree checksum manifest and are root-owned and non-writable.

Product releases have an independent version, artifact, checksum manifest,
SBOM, provenance, and signature material. Source-checkout installation is
recorded separately from a verified artifact installation.

Complete state removal retains audit evidence under `/var/log/llama.cpp`.
A root-owned, non-writable `product-ownership` marker proves that this residual
log directory may be reused by a later installation; an unmarked log collision
still fails closed.

## Network and local-user boundary

`llama-manager serve` supplies the host and port itself; configuration cannot
change `127.0.0.1:8080`. The API has no authentication and is intentionally
shared by local users. Any local process can submit prompts, consume CPU and
memory, and observe model names. Do not treat it as suitable for mutually
untrusted local tenants, and never forward it to an untrusted network.

Systemd applies `NoNewPrivileges`, private devices and temporary storage,
kernel and control-group protection, a strict filesystem view, and explicit
writable paths. Ubuntu Zombie's install, configuration, and component-state
roots are explicitly inaccessible to the service. `MemoryDenyWriteExecute`
remains disabled because the upstream inference runtime may require executable
mappings.

## Residual risks

- A compromised upstream runtime could act with the `llama-cpp` service
  identity despite checksum and release review.
- A malicious local user can create denial-of-service load through the shared
  unauthenticated loopback API.
- Model output is untrusted text and must not be treated as instructions.
- Root can inspect or alter all product state; Llama is not a boundary against
  the machine administrator.

Report vulnerabilities using the repository process in `SECURITY.md`. Do not
include prompts, local files, diagnostics, or other private data in a report.
