# Release

Product versions use `yyyy.mm.dd.hh.nn.ss` UTC format. A release is an
independent `forgejo-<VERSION>.tar.gz` source artifact containing
`products/forgejo` and the repository license.

The Forgejo release workflow runs lint, unit, integration, and schema checks;
packages the source; creates test evidence and an SPDX SBOM; computes
checksums; attests provenance; signs every asset with keyless cosign; and
publishes tag `forgejo-v<VERSION>`.

This source release does not redistribute the upstream Forgejo binary. The
lifecycle retrieves and verifies the selected official binary during install
or update.
