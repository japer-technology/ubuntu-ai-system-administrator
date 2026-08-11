# Release process and trust

Llama has an independent UTC date-time `VERSION`, changelog, package, and tag.
A root Ubuntu Zombie release does not change the Llama version.

| Item | Convention |
| ---- | ---------- |
| Version | `yyyy.mm.dd.hh.nn.ss` UTC |
| Tag | `llama-v<VERSION>` |
| Artifact | `llama-<VERSION>.tar.gz` |
| SBOM | SPDX JSON |
| Checksums | SHA-256 manifest |
| Provenance | GitHub artifact attestation bundle |
| Signatures | Keyless cosign material for each release asset |
| Test evidence | Product/version/commit JSON after validation and packaging |

The source artifact contains only `products/llama/`, applicable
`family/schemas/`, and `LICENSE`. The pinned
`.github/workflows/llama-release.yml` workflow runs lint, unit, integration,
family, and package checks before producing the SBOM, checksums, provenance,
signatures, and test evidence.

Before a release install, verify the tag against `VERSION`, asset checksums,
attestation subject, and expected workflow signing identity. A source checkout
records a source-tree digest and is not represented as a verified artifact.
`family/catalog.json` stays empty until the independent release and supported
VM gates have recorded evidence.
