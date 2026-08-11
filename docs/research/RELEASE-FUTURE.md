# Release Future

The decision is to **not** chase more packaging formats first. The class-leading move is to turn the repo into a **trustworthy, upgradeable, policy-verifiable release system**.

The uploaded analysis says the repo already has a credible base: installer lifecycle commands, runtime payload, operator tools, systemd/config assets, `.deb` packaging, tag-driven GitHub release, tarball, SBOM, checksums, and cosign signing. 

## Recommended decision stack

| Priority | Decision                                           | Verdict                                                             |
| -------: | -------------------------------------------------- | ------------------------------------------------------------------- |
|        1 | Keep `.deb` as the primary Linux package           | **Yes**                                                             |
|        2 | Split the package into installer + agent runtime   | **Yes, next major packaging move**                                  |
|        3 | Add an APT repository                              | **Yes, before broad production rollout**                            |
|        4 | Add OCI/container image                            | **Yes, but mainly for CI, test, demos, and controlled deployments** |
|        5 | Strengthen provenance beyond checksums/signatures  | **Critical**                                                        |
|        6 | Keep deployment separate from package installation | **Yes — this is architecturally correct**                           |

## The best-in-class architecture

### 1. Keep the current install/deploy separation

The current model is strong: the `.deb` stages files, while `sudo ubuntu-zombie install` performs host mutation and service setup. That is the right separation.

Debian maintainer scripts can run during install, upgrade, and removal, so pushing too much deployment logic into package scripts increases upgrade risk and reversibility problems. ([Debian][1])

**Decision:** keep the `.deb` boring and deterministic. Let the installer own deployment.

---

### 2. Split into two packages

Move from:

```text
ubuntu-zombie.deb
```

to:

```text
ubuntu-zombie          # CLI wrapper, installer, lifecycle tooling
ubuntu-zombie-agent    # runtime payload, server, policy, runner, skills, bridges
```

This is the highest-value packaging split because the runtime payload will change faster than the installer. The uploaded analysis identifies the payload as the heaviest and fastest-moving component, already naturally separated under `payload/`. 

**Decision:** split on lifecycle boundary, not folder convenience.

Best package shape:

```text
ubuntu-zombie
  depends: bash, coreutils, sudo, ca-certificates, curl
  contains: /usr/sbin/ubuntu-zombie, install/verify/doctor/repair/uninstall

ubuntu-zombie-agent
  depends: ubuntu-zombie
  contains: /usr/share/ubuntu-zombie/payload/
  owns: agent runtime, skills, bridges, systemd units, config templates

ubuntu-zombie-tools
  optional: diagnostics, audit-recent, health-check, collect-diagnostics
```

I would make `ubuntu-zombie-tools` optional later, not first.

---

### 3. Add an APT repository before serious rollout

GitHub Release `.deb` files are acceptable for early adoption. They are not ideal for production fleet operations.

APT gives you:

```text
apt update
apt install ubuntu-zombie
apt upgrade ubuntu-zombie-agent
apt pinning
signed repository metadata
staged channel promotion
```

Recommended channels:

```text
stable
candidate
edge
```

Do not start with a PPA unless you want Ubuntu-specific distribution constraints. A private or public APT repository gives better control.

**Decision:** GitHub Release remains the immutable artifact store; APT becomes the operational distribution channel.

---

### 4. Upgrade supply-chain posture to provenance-based verification

The repo already has checksums, SBOM, and cosign signing. That is good. It is not yet class-leading unless consumers can verify:

```text
this artifact came from this commit,
built by this workflow,
from this tag,
with this source tree,
using this release process.
```

SLSA is designed for this exact purpose: artifact integrity, tamper resistance, and supply-chain trust. ([Open Source Security Foundation][2])

Cosign is already aligned with this direction because it supports keyless signing and transparency-log-backed artifact signing. ([GitHub][3])

**Decision:** move from “signed files” to “verifiable release provenance.”

Minimum best-in-class release bundle:

```text
ubuntu-zombie_<ver>_all.deb
ubuntu-zombie-agent_<ver>_all.deb
ubuntu-zombie-<ver>.tar.gz
SHA256SUMS
SHA256SUMS.sig
*.spdx.json
*.intoto.jsonl / provenance attestation
cosign bundle
release verification script
```

---

### 5. Add an OCI image, but do not make it the flagship package

An OCI image is valuable for:

```text
CI testing
policy/runner integration tests
demo environments
air-gapped staging
Kubernetes or container-hosted agent experiments
```

It should not replace the `.deb` because this project appears host-administration oriented. Host mutation, systemd integration, audit logs, and local operator tooling are more natural in native packaging.

**Decision:** OCI image is a validation and deployment variant, not the primary product.

---

### 6. Pin Node bridge inputs

The uploaded analysis correctly flags `pi-ai.version` and `pi-mono.version` as supply-chain gaps. 

Best decision:

```text
bridge name
version
source URL
SHA256
license metadata
included in SBOM
verified during build
blocked if checksum mismatch
```

Do not let release builds fetch mutable bridge assets without checksum enforcement.

---

## Final recommendation

Make this the roadmap:

```text
Phase 1 — Harden current release
  - enforce VERSION == Git tag
  - keep tarball + .deb + SBOM + checksums + cosign
  - add provenance attestation
  - add release verification command

Phase 2 — Split packages
  - ubuntu-zombie
  - ubuntu-zombie-agent
  - optional later: ubuntu-zombie-tools

Phase 3 — Add APT distribution
  - stable/candidate/edge channels
  - signed repository metadata
  - documented upgrade/rollback flow

Phase 4 — Add OCI image
  - CI/test/runtime parity
  - signed image
  - SBOM + provenance
  - not the primary install route

Phase 5 — Enterprise-grade trust
  - checksum-pinned bridge dependencies
  - reproducible build target
  - offline verification docs
  - policy gate for deployment
```

The best strategic call: **ship a native, signed, provenance-verifiable Debian package family distributed through APT, with OCI as a secondary runtime/test artifact.**

[1]: https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html?utm_source=chatgpt.com "6. Package maintainer scripts and installation procedure - Debian"
[2]: https://openssf.org/projects/slsa/?utm_source=chatgpt.com "SLSA – Open Source Security Foundation"
[3]: https://github.com/sigstore/cosign?utm_source=chatgpt.com "GitHub - sigstore/cosign: Code signing and transparency for containers ..."
