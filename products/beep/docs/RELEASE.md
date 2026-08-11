# Independent release and verification

Beep has its own version, tag, artifact, evidence, SBOM, checksums,
attestation, signatures, and GitHub release.

| Item | Convention |
| ---- | ---------- |
| Version | `yyyy.mm.dd.hh.nn.ss` UTC |
| Tag | `beep-v<VERSION>` |
| Source artifact | `beep-<VERSION>.tar.gz` |
| Test evidence | `beep-<VERSION>.test-evidence.json` |
| SBOM | `beep-<VERSION>.spdx.json` |
| Checksums | `beep-<VERSION>.sha256` |
| Provenance | `beep-<VERSION>.intoto.jsonl` |
| Signatures | Cosign bundle, signature, and certificate per release asset |

`.github/workflows/beep-release.yml` is triggered by the independent Beep
version or tag. Every third-party action is pinned by commit. The workflow
runs product lint and tests, packages only `products/beep/` and the repository
licence, generates an SPDX SBOM and test evidence, computes SHA-256 checksums,
creates a GitHub artifact attestation, signs every asset with keyless cosign,
and publishes the product tag and release.

Test evidence distinguishes automated source gates from external standalone
VM and co-installation gates. A successful release workflow does not by itself
admit Beep to `family/catalog.json`.

## Operator verification

Download every asset for exactly one `beep-v<VERSION>` release into a clean
directory and run:

```bash
beep-verify-release /path/to/release-directory
```

The verifier requires exactly one versioned checksum manifest, rejects unsafe
artifact names, verifies every listed digest, verifies the checksum and listed
assets against the cosign identity for
`.github/workflows/beep-release.yml` in
`japer-technology/beep`, and verifies each attested subject with the
local provenance bundle.

Then confirm:

1. the tag equals the extracted `products/beep/VERSION`;
2. `PRODUCT.json` still declares only Beep namespaces and operations;
3. test evidence names the expected commit and does not claim unrun host gates;
4. the SBOM and [`UPSTREAM.md`](../UPSTREAM.md) match reviewed dependencies;
5. the changelog describes the intended migration and open risks; and
6. the install plan names only Beep resources.

Do not install a lone archive, copy another product's runtime, use a release
from another repository, weaken the certificate identity, or treat
source-checkout tests as signed-release evidence.
