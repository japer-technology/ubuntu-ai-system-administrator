# GitHub Actions workflows

This directory contains the GitHub Actions workflows that protect the
Ubuntu Zombie source tree, exercise installer behavior, publish security
signals, and produce signed release artifacts. The workflows are designed
around the repository's trust model: run fast checks on every pull request,
keep privileged installer paths covered by scheduled integration checks,
and publish release artifacts with provenance and signatures.

All third-party actions are pinned to full commit SHAs, with the
human-readable upstream tag kept in a trailing comment. Keep that convention
when updating existing actions or adding new ones so reviewers can verify
both the exact code that runs and the intended upstream release.

## Workflow summary

Workflows are documented in ascending order by workflow file name. Keep the
summary table and the detailed sections below in the same order so additions,
removals, and trigger changes are easy to review.

| File | Workflow | Primary purpose | Main triggers |
| --- | --- | --- | --- |
| `ci.yml` | CI | Lint, syntax, smoke, pytest, package, and secret-pattern checks | Pull requests and pushes to `main` |
| `codeql.yml` | CodeQL | Static analysis for Python and JavaScript security/quality issues | Pull requests, pushes to `main`, weekly schedule |
| `dependency-review.yml` | Dependency Review | Block vulnerable or incompatible new dependencies in PRs | Pull requests targeting `main` |
| `forgejo-release.yml` | Forgejo Release | Build, attest, sign, and publish the independent Forgejo artifact | Forgejo `VERSION` changes, product tags, manual dispatch |
| `imaginary-friend-release.yml` | Imaginary Friend Release | Build, attest, sign, and publish the independent Friend artifact | Friend `VERSION` changes, product tags, manual dispatch |
| `integration.yml` | Integration | Best-effort installer dry-run and container checks outside the lint sandbox | Nightly schedule and manual dispatch |
| `llama-release.yml` | Llama Release | Build, attest, sign, and publish the independent Llama artifact | Llama `VERSION` changes, product tags, manual dispatch |
| `release.yml` | Release | Build, attest, sign, upload, and publish release artifacts | `VERSION` changes on `main`, version tags, manual dispatch |
| `scorecard.yml` | OpenSSF Scorecard | Produce OpenSSF Scorecard SARIF and publish it to code scanning | Pushes to `main`, weekly schedule, branch protection changes |

## `ci.yml` — CI

The CI workflow is the main pull-request and `main` branch quality gate.
It has a single `lint` job that runs on a matrix covering the supported
Ubuntu Desktop LTS targets and their default Python versions:

- Ubuntu 22.04 with Python 3.10.
- Ubuntu 24.04 with Python 3.12.

The job checks out the repository, installs ShellCheck, and then runs the
same categories of checks contributors are expected to run locally:

- ShellCheck at warning severity for tracked and untracked Bash files,
  including Bash helpers in `payload/bin/` that do not use a `.sh`
  extension.
- `bash tests/smoke.sh syntax` for shell syntax checks.
- `bash tests/smoke.sh python` for Python compilation checks.
- `bash tests/smoke.sh subcommands` to ensure installer subcommand parsing
  stays valid.
- `bash tests/smoke.sh noninteractive` to protect
  `ZOMBIE_NONINTERACTIVE=1` behavior.
- `bash tests/smoke.sh standards` for repository policy and standards
  checks.
- `python3 -m pytest tests/python -q` for policy and audit regression tests.
- Independent Imaginary Friend, Forgejo, and Llama product lint and test suites.
- Root, Imaginary Friend, Forgejo, and Llama package builds.
- A final `git grep` scan for long `sk-`, `sk-ant-`, and
  `tskey-auth-` token-shaped strings.

The workflow grants only `contents: read` by default. It is intentionally
broad for pull requests because it catches most breakage before a change
reaches `main`.

## `codeql.yml` — CodeQL

The CodeQL workflow runs GitHub's static analysis for the code CodeQL can
inspect in this repository. It analyzes two language categories:

- `python` for the agent service under `payload/agent/`.
- `javascript` for shipped JavaScript bridge modules such as
  `payload/agent/pi-mono-bridge.mjs` and
  `payload/agent/pi-ai-bridge.mjs`.

The workflow runs on pull requests targeting `main`, pushes to `main`, and
a weekly Monday schedule. The scheduled run is important because it picks
up newly published CodeQL query packs even if the repository has not
changed.

The `analyze` job initializes CodeQL with `+security-and-quality` queries,
runs the CodeQL autobuilder, and uploads results with language-specific
categories. The workflow grants the job the minimum extra permissions it
needs to publish security results: `security-events: write`, plus read
access to packages, actions, and contents.

CodeQL does not provide a first-party Bash analyzer, so shell coverage lives
in `ci.yml` through ShellCheck and smoke-test syntax checks.

## `dependency-review.yml` — Dependency Review

The Dependency Review workflow runs on pull requests into `main`. Its job
uses `actions/dependency-review-action` to inspect dependency manifest
changes and fail the PR when newly introduced dependencies have high or
higher known vulnerabilities.

The workflow also enforces a permissive-license allow-list aligned with the
repository's MIT licensing posture. Allowed licenses currently include
0BSD, Apache-2.0, BSD-2-Clause, BSD-3-Clause, CC0-1.0, ISC, MIT, MPL-2.0,
Python-2.0, Unlicense, and Zlib.

Although Ubuntu Zombie has few build-time dependencies, this workflow is
useful because payload manifests such as `package.json`,
`requirements*.txt`, or `pyproject.toml` could be added in the future. On
failure, the action is configured to comment a summary on the pull request.
The job uses `contents: read` and `pull-requests: write` only where the
dependency review action needs them.

## `forgejo-release.yml` — Forgejo Release

This workflow validates and packages only `products/forgejo/` plus the
applicable family schemas and repository license. Product tags use
`forgejo-v<VERSION>`. The workflow publishes a checksum, SPDX SBOM, test
evidence, provenance, and keyless cosign material independently of the root
Ubuntu Zombie release.

## `imaginary-friend-release.yml` — Imaginary Friend Release

This workflow validates and packages only `products/imaginary-friend/` plus
the repository license. Product tags use
`imaginary-friend-v<VERSION>`. The workflow publishes a checksum, SPDX SBOM,
test evidence, provenance, and keyless cosign material independently of the
root Ubuntu Zombie release.

## `integration.yml` — Integration

The Integration workflow is a scheduled and manually dispatched safety net
for installer behavior. It does not run on every pull request and is not the
same as local installation testing on a disposable Ubuntu Desktop VM.
Instead, it provides best-effort coverage for install paths that are too
heavy or too system-specific for the normal CI workflow.

It contains five jobs:

### `dry-run`

The `dry-run` job runs `sudo -E ./scripts/install.sh install --dry-run`
directly on GitHub-hosted Ubuntu 22.04 and 24.04 runners. It sets
`ZOMBIE_NONINTERACTIVE=1`, skips Tailscale with `ZOMBIE_SKIP_TAILSCALE=1`,
and supplies dummy SSH and VNC credentials so the installer can build a
full plan without prompting.

This checks that the non-interactive dry-run path remains usable on both
supported Ubuntu LTS versions without mutating the host.

### `install-in-container`

The `install-in-container` job runs inside privileged `ubuntu:22.04` and
`ubuntu:24.04` containers. It bootstraps the minimal tools needed for the
repository checks, runs `bash tests/smoke.sh all`, and then runs
`./scripts/install.sh install --dry-run` with the same non-interactive
dummy environment used by the host-runner job.

Container execution cannot model every systemd, display, or Tailscale
interaction a real Ubuntu Desktop host exposes. The workflow comments call
this out explicitly: failures are still a strong signal that installer
validation or idempotency paths need attention, but the authoritative place
for a real install remains a disposable Ubuntu Desktop LTS VM.

### `imaginary-friend-lifecycle`

This job exercises Friend install, verify, reinstall, backup, rollback,
suspend, resume, retained-state recovery, and complete removal on disposable
Ubuntu 22.04 and 24.04 runners against a hermetic loopback model fixture. The
harness requires an explicit disposable-VM sentinel before it will mutate a
host.

### `llama-lifecycle`

This job uses checksum-pinned tiny loopback fixtures to exercise clean Llama
install, health, idempotent reinstall, backup, suspend, resume, update,
rollback, retained-state recovery, complete removal, and post-purge reinstall
on Ubuntu 22.04 and 24.04 runners. The harness refuses to mutate a host without
the explicit `LLAMA_DISPOSABLE_VM_TEST=1` sentinel and rejects pre-existing
Llama resources.

### `forgejo-lifecycle`

This job uses checksum-pinned loopback Forgejo fixtures while exercising real
PostgreSQL, Caddy, Avahi, systemd, certificate trust, clean install,
idempotent reinstall, backup, suspend, resume, update, rollback, repair,
same-host runner coordination, sibling isolation, and complete removal on
Ubuntu 22.04 and 24.04 runners. The harness refuses pre-existing Forgejo state
and requires `FORGEJO_DISPOSABLE_VM_TEST=1`.

## `llama-release.yml` — Llama Release

This workflow validates and packages only `products/llama/` plus the
applicable family schemas and repository license. Product tags use
`llama-v<VERSION>`. The workflow publishes a checksum, SPDX SBOM, test
evidence, provenance, and keyless cosign material independently of the root
Ubuntu Zombie release.

## `release.yml` — Release

The Release workflow turns a repository version into distributable,
verifiable artifacts. It runs when:

- `VERSION` changes on `main`.
- A version-like tag matching `v*.*.*` is pushed.
- A maintainer manually dispatches the workflow with an existing tag.

The workflow has two jobs: `build` and `publish`.

### `build`

The `build` job checks out the requested ref with full history, resolves
the release version from `VERSION`, and enforces that the release tag is
exactly `v${VERSION}`. It then installs packaging tooling and runs the
release validation and packaging steps:

- `make lint` and `bash tests/smoke.sh all`.
- `make verify-bridge-pins` for checksum-pinned bridge inputs.
- `make package` for the source tarball.
- `make deb` for the Debian package.
- `sha256sum` over generated `.tar.gz` and `.deb` artifacts.
- Syft SPDX-JSON SBOM generation.
- GitHub SLSA provenance attestation with `actions/attest`.
- Keyless cosign signatures, certificates, and bundles for the tarball,
  `.deb`, checksum file, SBOM, and provenance file.
- Upload of the complete `dist/` directory as a temporary workflow
  artifact named `release-artifacts`.

The job exposes the resolved `version` and `tag` as outputs for publishing.
It requests `id-token: write` for cosign keyless signing and
`attestations: write` for GitHub provenance generation.

### `publish`

The `publish` job downloads the build artifacts and creates or updates the
matching GitHub Release. When the workflow was triggered by a `VERSION`
change on `main`, it first ensures the expected release tag exists. If a
tag with the same name already points at another commit, the job fails and
requires another version increment.

Release notes are built from the matching `CHANGELOG.md` section when one
exists, with fallback text otherwise. The workflow appends a short artifact
verification snippet that extracts the release tarball and runs
`payload/bin/verify-release`.

The GitHub Release upload includes:

- Source tarball.
- Debian package.
- `SHA256SUMS`.
- SPDX SBOM.
- SLSA provenance bundle.
- Cosign signatures, certificates, and bundles.

## `scorecard.yml` — OpenSSF Scorecard

The OpenSSF Scorecard workflow measures repository security posture and
publishes the result as SARIF. It runs on pushes to `main`, on a weekly
Monday schedule, and when branch protection rules change.

The `analysis` job checks out the repository without persisting
credentials, runs `ossf/scorecard-action`, writes `results.sarif`, uploads
that file as a short-lived artifact named `scorecard-sarif`, and uploads
the same SARIF to GitHub code scanning.

The workflow uses `permissions: read-all` at the workflow level and grants
the job `security-events: write`, `id-token: write`, and read access to
contents and actions so Scorecard can publish results and GitHub can ingest
the SARIF.

## Maintenance checklist

When changing these workflows:

- Keep action references pinned to commit SHAs and update the trailing tag
  comments at the same time.
- Preserve least-privilege `permissions` blocks; add permissions only for
  a documented step that requires them.
- Keep CI-aligned commands in sync with `Makefile`, `tests/smoke.sh`, and
  contributor documentation.
- Keep the summary table and workflow sections ordered by workflow file name.
- Avoid real installer mutation in GitHub-hosted runners. Use dry-run paths
  here and reserve full installation checks for disposable Ubuntu Desktop
  LTS VMs.
- Update this README whenever a workflow is added, removed, renamed, or
  given materially different triggers, permissions, jobs, or artifacts.
