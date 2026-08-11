# Improvement 6 plan — installation without a Git clone

## Question

Can Ubuntu Zombie offer an installation experience like Ollama:

```bash
curl -fsSL https://ollama.com/install.sh | sh
```

Can the same product install on an Ubuntu PC, a Windows PC, or a Mac,
ideally through a small number of obvious scripts that choose the
correct installation surface for an operator who does not know which
package or platform details matter?

The short answers are:

- **A one-line Ubuntu installation is practical now.** The existing
  GitHub Release tarball and `.deb` contain almost everything needed.
- **Removing the Git requirement is straightforward.** A small bootstrap
  can download and verify a release before invoking the existing
  installer.
- **"PC" needs to be made precise.** Ubuntu PCs are supported today;
  Windows PCs are not.
- **A native Mac installation is possible, but it is a port of the
  product rather than another download script.** The current runtime and
  trust model depend on Ubuntu, `apt`, Linux users, sudoers, and
  `systemd`.
- **Three friendly entry points are reasonable**, but they should share
  one release manifest and fail clearly on unsupported systems rather
  than pretending that one Linux script is portable.

This document describes the choices and recommends an incremental path.
It is an analysis and implementation plan, not an implemented install
method.

## What exists today

The primary source installation is:

```bash
git clone https://github.com/japer-technology/ubuntu-zombie.git
cd ubuntu-zombie
sudo ./scripts/install.sh install --dry-run
sudo ./scripts/install.sh install
```

The repository also builds two release artifacts:

- `ubuntu-zombie-<version>.tar.gz`, produced by `make package`;
- `ubuntu-zombie_<version>_all.deb`, produced by `make deb`.

The release workflow already creates:

- `SHA256SUMS`;
- keyless cosign bundles;
- an SPDX software bill of materials;
- SLSA provenance;
- GitHub Release attachments.

The `.deb` is deliberately a stage-1 package. It installs the source
tree under `/usr/share/ubuntu-zombie/` and exposes the
`ubuntu-zombie` command, but it does not silently create a privileged
account during package installation. The operator still runs:

```bash
sudo ubuntu-zombie install
```

That separation is valuable and should remain. Installing a package and
authorising a root-capable AI administrator are different decisions.

## Why `curl | sh` is only the front door

The Ollama-style command is a delivery mechanism, not the installer
architecture. The script received over HTTPS normally performs four
jobs:

1. detect the host platform and architecture;
2. select a compatible immutable release;
3. download and verify an artifact;
4. hand control to the real installer.

Ubuntu Zombie should follow the same model. The remotely fetched script
should be a **small bootstrap**, not a second copy of the several-
thousand-line installer.

The bootstrap should not install directly from the moving `main` branch.
It should resolve a released version, download an immutable artifact,
verify it, and then invoke the installer packaged inside that artifact.
This keeps source installs, `.deb` installs, upgrades, and one-line
installs on the same tested code path.

## Important distinction: easy and blind are not the same

A one-line command is convenient, but piping network content directly
into a shell asks the operator to trust whatever the server returns at
that instant. That risk matters more for Ubuntu Zombie than for an
ordinary user application because the eventual installation creates a
root-capable account.

The project can provide a one-liner without presenting it as the safest
method. Documentation should offer three confidence levels:

### Fast path

All `ubuntu-zombie.example` addresses below are non-operational
placeholder domains. A production URL and its ownership model remain an
implementation decision.

```bash
curl -fsSL https://get.ubuntu-zombie.example/ | sh
```

This is memorable and suitable for a disposable machine. The bootstrap
must still verify the release artifact before running it.

### Inspect-then-run path

```bash
curl -fsSLo /tmp/ubuntu-zombie-install.sh \
  https://get.ubuntu-zombie.example/
less /tmp/ubuntu-zombie-install.sh
sh /tmp/ubuntu-zombie-install.sh
```

This lets the operator inspect the bootstrap and preserves exactly what
was executed for later review.

### Fully verified path

Download the `.deb`, `SHA256SUMS`, and signature bundle separately,
verify the checksum and cosign identity, install the package, preview
with `--dry-run`, and then authorise installation.

No wording should imply that a checksum fetched from the same compromised
origin independently authenticates a download. A checksum detects
corruption; the cosign identity and provenance provide stronger origin
evidence. The bootstrap itself still has a first-download trust problem.
Serving a tiny, stable bootstrap from a separately controlled HTTPS
origin and publishing its digest through release notes can reduce, but
not entirely remove, that problem.

## Option 1 — one-line bootstrap using GitHub Releases

This is the smallest useful improvement.

The public command could eventually look like:

```bash
curl -fsSL https://get.ubuntu-zombie.example/ | sh
```

Until a project-controlled domain exists, a raw GitHub URL is possible:

```bash
curl -fsSL \
  https://raw.githubusercontent.com/japer-technology/ubuntu-zombie/main/scripts/bootstrap.sh \
  | sh
```

The raw `main` form is acceptable for experimentation but is not the
preferred long-term command. It is mutable, visually long, tied to a
source branch, and makes bootstrap changes effective immediately without
a release boundary.

### Bootstrap responsibilities

The bootstrap should:

1. require HTTPS-capable download tooling (`curl`, with `wget` as an
   optional fallback);
2. detect operating system, distribution, version, and architecture;
3. reject unsupported hosts before requesting `sudo`;
4. query a small release manifest or resolve a stable release endpoint;
5. select the `.deb` or tarball for the detected host;
6. download into a newly created temporary directory;
7. download verification metadata;
8. verify the artifact before extracting or installing it;
9. show the resolved version and source URL;
10. install the stage-1 package or unpack the tarball;
11. invoke the packaged installer's existing interactive review;
12. clean temporary files on success and explain where diagnostics remain
    on failure.

It should preserve arguments after the bootstrap separator so an
operator can request:

```bash
curl -fsSL https://get.ubuntu-zombie.example/ |
  sh -s -- --dry-run
```

Environment-based unattended options should continue to work, but the
bootstrap must not invent a parallel configuration API. Existing
`ZOMBIE_*` variables remain the contract.

### `.deb` or tarball?

The `.deb` is the best default on supported Ubuntu hosts because it:

- integrates with `dpkg`;
- records which stage-1 files are installed;
- supplies a stable `ubuntu-zombie` command;
- gives package ownership and removal semantics;
- already exists in the release workflow.

The tarball remains useful for:

- inspection without installing a package;
- development and recovery;
- hosts where the stage-1 package cannot be installed;
- retaining the exact release tree used for an installation.

The bootstrap can prefer the `.deb` and support an explicit
`--method=tarball` escape hatch. There should not be two different
privileged installation implementations.

### Latest release versus pinned release

Interactive use can default to the latest stable release. Automation
must be able to pin:

```bash
ZOMBIE_VERSION=<version> sh ubuntu-zombie-bootstrap.sh
```

The version selector should accept only the repository's canonical
version format, reject shell metacharacters, and resolve exact artifact
names from trusted metadata. It must never interpolate unvalidated input
into a command.

## Option 2 — an APT repository

The most conventional long-term Ubuntu experience is:

```bash
curl -fsSLo /tmp/ubuntu-zombie-key.asc \
  https://packages.ubuntu-zombie.example/key.asc
# Compare this fingerprint with one published through an independent
# trusted channel before installing the key.
gpg --show-keys --fingerprint /tmp/ubuntu-zombie-key.asc
sudo gpg --dearmor -o /usr/share/keyrings/ubuntu-zombie.gpg \
  /tmp/ubuntu-zombie-key.asc

echo "deb [signed-by=/usr/share/keyrings/ubuntu-zombie.gpg] \
https://packages.ubuntu-zombie.example/ubuntu stable main" |
  sudo tee /etc/apt/sources.list.d/ubuntu-zombie.list

sudo apt update
sudo apt install ubuntu-zombie
sudo ubuntu-zombie install
```

A repository setup script could shorten the first three steps, but the
signed repository remains the underlying trust mechanism.

### Benefits

- familiar installation and update flow;
- package metadata, signing, and dependency handling;
- version pinning and rollback visibility through APT;
- automatic delivery of stage-1 installer updates;
- no Git checkout and no ad-hoc extracted directory.

### Costs

- repository hosting and availability;
- an offline signing-key and rotation procedure;
- distribution suites and metadata publication;
- release promotion and rollback operations;
- expiry, compromise, and disaster-recovery procedures;
- a clear distinction between updating stage-1 files and re-running the
  privileged convergent installer.

An APT repository should be a later improvement. It is unnecessary for
proving the one-line experience and adds permanent operational
infrastructure.

## Option 3 — native operating-system packages

Native packages provide the cleanest experience on each supported
platform:

- Ubuntu: signed `.deb` or APT repository;
- macOS: signed and notarised `.pkg`, possibly distributed through a
  Homebrew tap;
- Windows: signed MSI/MSIX or a `winget` package.

Packages solve delivery and file ownership. They do **not** make the
runtime portable. A macOS package cannot install Linux `systemd` units,
and an MSI cannot make `apt` available. Native packages become useful
only after corresponding native runtime ports exist.

## What “PC and Mac” can mean

“PC” is often used in three different ways:

1. an Ubuntu desktop PC;
2. any Linux PC;
3. a Windows PC.

Those are not interchangeable for this repository.

### Ubuntu PC

This is the current product. Supported hosts are Ubuntu Desktop 22.04
and 24.04 LTS on `amd64`, with best-effort `arm64` paths. A one-line
bootstrap can be added without changing the product architecture.

### Other Linux PC

Debian, Mint, Pop!_OS, Fedora, Arch, and other distributions are not
currently supported. Supporting them requires at least:

- package-manager adapters;
- distribution-specific prerequisite names and repositories;
- service-manager and desktop integration checks;
- CI and disposable-machine integration tests;
- a documented support matrix.

Some Debian derivatives may appear to work, but the current installer
intentionally checks for Ubuntu and should keep failing closed until a
platform is tested and declared supported.

### Windows PC

Native Windows is not supported. WSL is also currently unsupported
because the product expects a real Ubuntu Desktop host, durable
`systemd` services, Linux users, and desktop integration.

There are three possible Windows directions:

- **Ubuntu virtual machine:** the quickest honest route. The supported
  installer runs inside an Ubuntu Desktop VM.
- **WSL port:** smaller than a native Windows port, but still needs a
  revised desktop and service model and should not be advertised until
  tested.
- **Native Windows agent:** a separate platform implementation using
  Windows services, local security principals, ACLs, Credential Manager,
  event logging, and elevation controls.

An `install-windows.ps1` script can initially perform detection and
explain these choices. It must not claim native support.

### Intel and Apple Silicon Mac

macOS can run an Ubuntu Desktop virtual machine today. That is the
shortest route to the current product, although it changes the product
from “administrator of the Mac” to “administrator of the Ubuntu VM”.

A native Mac agent is technically possible, but it requires a deliberate
macOS product design.

## Why the current Ubuntu installer cannot simply run on macOS

The installer and runtime assume:

- `/etc/os-release` identifies Ubuntu;
- packages are managed through `apt` and `dpkg`;
- services and timers are managed by `systemd`;
- the AI identity is a Linux local user;
- privilege is granted through Linux sudoers files;
- runtime files live under `/opt`, `/etc`, and `/var/log`;
- Ubuntu's system Python and Node installation paths are available;
- desktop and power behaviour follow Ubuntu conventions;
- helpers reason about Ubuntu packages and services.

Replacing `apt` with Homebrew addresses only one item in that list.

### Native macOS equivalents that need design

| Ubuntu concept | Possible macOS counterpart | Design concern |
| --- | --- | --- |
| `systemd` unit/timer | `launchd` daemon/agent | Correct session, ownership, restart, and log behaviour |
| Linux service user | macOS local or hidden service account | SecureToken, FileVault, home directory, and login implications |
| sudoers drop-in | tightly scoped sudoers or privileged helper | Root-capable AI remains a major trust decision |
| `/etc/ubuntu-zombie` | `/Library/Application Support/...` | Permissions and package ownership |
| `/var/log/...` | unified logging plus protected files | Audit immutability, privacy, and diagnostics |
| apt/dpkg | signed `.pkg` and/or Homebrew | Homebrew should not silently own privileged system state |
| system Python | bundled or supported Python runtime | Avoid relying on removed or mutable Apple runtimes |
| secret env file | Keychain plus protected config | Headless service access and rotation |
| browser launcher | `.app` or LaunchServices | Signing, notarisation, and user-session boundaries |

The policy gate and audit requirements must remain equivalent. A native
port must define macOS action classes rather than blindly translating
Linux commands. Commands such as `apt`, `systemctl`, and Linux-specific
file edits cannot be exposed as if they apply to a Mac.

### Product naming and scope

Native macOS support also raises a product question: is “Ubuntu Zombie”
still the name of an agent that administers macOS, or is Ubuntu Zombie
one platform edition of a broader product?

That should be decided before investing in native packaging. Otherwise,
documentation, command names, filesystem paths, package identifiers, and
service labels will encode an accidental answer.

## Three scripts: two useful interpretations

The request for “three scripts based on surface” can sensibly mean
either three operating-system entry points or three levels of installer
experience. Both can be supported without duplicating core logic.

### Interpretation A — three platform entry points

1. **`install-ubuntu.sh`**
   - supported implementation;
   - resolves and verifies a release;
   - installs the `.deb`;
   - starts the existing review and install flow.

2. **`install-macos.sh`**
   - initially detects Intel versus Apple Silicon;
   - clearly explains that native installation is not yet supported;
   - offers documentation for the Ubuntu VM route;
   - later becomes a dispatcher to a signed macOS package after a native
     port exists.

3. **`install-windows.ps1`**
   - detects native Windows, WSL, and architecture;
   - initially explains supported VM choices;
   - later dispatches to signed Windows packaging if a port is built.

A stable landing page can detect the visitor's browser platform and show
the likely command, but the command itself must independently detect and
validate the host. Browser detection is only a convenience.

### Interpretation B — three installation surfaces

1. **Quick bootstrap:** memorable `curl | sh` command.
2. **Native package:** verified `.deb` now, APT later.
3. **Source/archive:** Git clone or verified release tarball for
   developers, auditors, and recovery.

This interpretation is useful because all three can target Ubuntu now.
They offer convenience without overstating cross-platform support.

### Recommended public structure

Use one friendly dispatcher plus platform-specific implementations:

```text
https://get.ubuntu-zombie.example/        universal shell dispatcher
https://get.ubuntu-zombie.example/linux   Ubuntu implementation
https://get.ubuntu-zombie.example/macos   macOS status/implementation
```

Windows needs PowerShell rather than pretending that `sh` is universal:

```text
https://get.ubuntu-zombie.example/windows.ps1
```

The dispatcher should contain only detection and delegation. Shared
release selection and verification logic should be generated from or
tested against one release manifest, not copied into three drifting
scripts.

## Proposed release manifest

A small, versioned manifest can remove fragile GitHub API parsing from
the bootstrap. Conceptually it needs:

- release version and channel;
- publication timestamp;
- minimum supported bootstrap version;
- per-platform artifact name and URL;
- architecture;
- SHA-256 digest;
- cosign bundle URL;
- expected signing workflow identity;
- optional minimum operating-system version.

The release workflow should create and sign the manifest alongside the
artifacts. Bootstraps can then remain stable while artifact names and
platform coverage evolve.

Do not make the manifest an unsigned alternative source of truth. It
must be authenticated, and every artifact digest must match the release
outputs.

## User experience

The shortest command should not remove informed consent. A good flow is:

1. bootstrap reports detected host and chosen release;
2. artifact verification succeeds before any package execution;
3. stage-1 files are installed;
4. the installer displays the existing brand and trust warning;
5. `--dry-run` remains available before changes;
6. the interactive parameter review runs;
7. the operator explicitly approves privileged installation;
8. the receipt records version and installation source;
9. final output gives verify, secrets, reboot, and uninstall commands.

The bootstrap should support:

- `--help`;
- `--version <version>`;
- `--channel stable` with future channels rejected until implemented;
- `--method deb|tarball`;
- `--download-only <directory>`;
- `--dry-run`;
- `--no-sudo` for download-only or inspection;
- `--` followed by existing installer arguments.

Flags should remain few. Product configuration belongs to
`scripts/install.sh`, not the downloader.

### Failure messages

Unsupported-platform messages should state:

- what was detected;
- what is supported;
- whether an Ubuntu VM is a viable route;
- where the platform matrix lives;
- that overriding detection is not supported.

Verification failure must stop before extraction or package installation
and print the expected and actual artifact identity without dumping
secrets or arbitrary server responses.

## Upgrades and uninstall

A one-line installer also needs a clear repeat story:

```bash
curl -fsSL https://get.ubuntu-zombie.example/ | sh
```

On an installed host, the bootstrap should recognise the stage-1 package,
show current and target versions, update stage-1 files, and then ask
before re-running the idempotent installer.

The following concepts must remain separate:

- upgrading the downloaded installer package;
- reapplying Ubuntu Zombie's host configuration;
- upgrading optional stateful components such as Forgejo;
- uninstalling the configured product;
- removing only the stage-1 package.

Existing Forgejo update and database-reuse confirmations must not be
bypassed by a bootstrap `--yes`.

For rollback, retaining prior signed `.deb` files helps restore the
installer source, but it does not automatically reverse host migrations.
The project currently does not support downgrades, and a bootstrap must
not imply otherwise.

## Security requirements

The bootstrap is security-sensitive code even if it is short.

It must:

- use HTTPS and reject redirects to non-HTTPS destinations;
- quote every expansion and use strict shell settings;
- create temporary directories safely and clean them with traps;
- reject unsupported operating systems and architectures;
- validate versions and artifact names against strict patterns;
- never use `eval`, preventing untrusted release or argument data from
  becoming shell commands;
- never execute a downloaded artifact before verification;
- avoid passing secrets on command lines or logging secret environment
  values;
- request elevation only for the package/install stage;
- display the exact release version being installed;
- fail closed on missing or malformed verification metadata;
- retain the existing policy gate, audit log, and interactive approval
  model;
- avoid telemetry unless separately designed, documented, and consented
  to.

The script should not silently install `curl`, cosign, or other
verification tools by running an unverified package operation first.
The verification design must define a minimal trusted-tool baseline. A
practical first version can require `curl` and `sha256sum`, verify the
checksum, and provide an optional or bundled path for full cosign
verification. Before calling this production-ready, the maintainers
should decide whether signature verification is mandatory and how the
bootstrap authenticates the expected signer identity.

## Hosting choices

### Raw GitHub

Good for a prototype. No new infrastructure, but the URL is mutable,
long, branch-coupled, and less memorable.

### GitHub Pages or a project domain

Good for a stable bootstrap URL and human landing page. Use strict HTTPS,
minimal redirects, deployment review, and branch protection. Keep the
actual large artifacts on GitHub Releases unless there is a reason to
mirror them.

### Package CDN

Useful only when operating an APT repository or supporting substantial
download volume. It adds cache invalidation and origin-security work.

Whichever host is chosen, release artifacts should remain immutable and
addressable by version. A “latest” endpoint may redirect to a version,
but versioned assets must never be overwritten.

## Testing and release gates

The bootstrap needs tests distinct from the privileged installer tests:

- shell syntax and ShellCheck;
- mocked platform detection;
- Ubuntu 22.04 and 24.04 on `amd64`;
- best-effort Ubuntu `arm64`;
- rejection of Debian derivatives, macOS, Windows shells, WSL, and
  containers where appropriate;
- release-manifest parsing;
- latest and pinned version resolution;
- checksum/signature success and failure;
- interrupted and partial downloads;
- HTTPS redirect policy;
- missing `curl`, checksum tool, or privilege;
- paths containing spaces;
- `--download-only` and `--dry-run`;
- argument forwarding;
- non-interactive exit-code compatibility;
- temporary-file cleanup;
- idempotent repeat installation;
- upgrade from the previous release.

CI should test bootstrap logic against a local fixture server rather
than depending on mutable live releases. A release candidate should also
receive an end-to-end disposable-VM test using the exact public URL and
artifacts before the command is promoted on the README.

Native macOS or Windows support requires dedicated CI runners plus
periodic tests on real or virtual hosts. Merely making the shell parser
run on macOS does not constitute product support.

## Documentation changes when implemented

The implementation should update:

- `README.md` with fast, inspectable, and fully verified paths;
- `docs/QUICKSTART.md` with expected prompts and failure branches;
- `docs/PLATFORMS.md` with exact support statements;
- `docs/UPGRADING.md` with repeat-bootstrap behaviour;
- `SECURITY.md` with bootstrap trust and release verification;
- release notes with immutable installation examples;
- `CHANGELOG.md` and `VERSION` for the user-visible change.

The Git clone path should remain documented for contributors and
auditors. It simply stops being the first path shown to ordinary
operators.

## Suggested implementation phases

### Phase 0 — decisions

- Decide whether the first public command is experimental or supported.
- Choose `.deb` as the default artifact and define the tarball fallback.
- Define expected cosign workflow identity and mandatory verification.
- Choose a stable URL and ownership model.
- Decide what “PC” means in public wording.

### Phase 1 — Ubuntu download-only bootstrap

- Add a small Ubuntu-only bootstrap.
- Resolve a pinned release and support `--download-only`.
- Verify release metadata and artifact.
- Refuse unsupported platforms with useful guidance.
- Add hermetic tests and publish the script at a versioned URL.

This phase proves release selection and verification without immediately
executing privileged installation.

### Phase 2 — one-line Ubuntu installation

- Install the verified stage-1 `.deb`.
- Hand off to `sudo ubuntu-zombie install`;
- preserve `--dry-run`, arguments, environment variables, and exit codes;
- record bootstrap source and release in the receipt;
- document inspect-then-run and fully verified alternatives.

### Phase 3 — stable domain and release manifest

- Publish a signed manifest from the release workflow.
- Serve a tiny stable dispatcher from a project-controlled HTTPS domain.
- Add end-to-end release-candidate tests.
- Promote the one-line command to the README quickstart.

### Phase 4 — package repository

- Build a signed APT repository only if update convenience and adoption
  justify its operational cost.
- Document signing-key rotation, repository recovery, and package versus
  host-configuration upgrades.

### Phase 5 — platform discovery

- Publish honest macOS and Windows detection scripts that explain VM
  installation without claiming native support.
- Gather demand and define platform-specific threat models.
- Decide product naming before creating native package identifiers.

### Phase 6 — native ports, independently approved

- Design macOS and Windows policy/action models.
- Implement platform service, identity, secrets, audit, lifecycle, and
  packaging layers.
- Add dedicated platform tests and support commitments.
- Only then change those platforms from unsupported to supported.

## Recommended outcome

The best immediate result is:

1. Keep Ubuntu Desktop as the only supported host.
2. Add a small, auditable Ubuntu bootstrap.
3. Download a pinned GitHub Release `.deb`.
4. Verify the artifact before installation.
5. Preserve the separate `sudo ubuntu-zombie install --dry-run` and
   `sudo ubuntu-zombie install` decisions.
6. Retain tarball and Git clone paths for inspection and development.
7. Provide clear Mac and Windows pages that recommend an Ubuntu VM and
   do not claim native support.

This delivers the desired “no Git pull required” experience without
forking the installer or weakening the trust model.

The command can eventually be as simple as:

```bash
curl -fsSL https://get.ubuntu-zombie.example/ | sh
```

But the architecture behind that command should remain deliberately
boring: detect, select an immutable release, verify, install stage 1,
then ask the operator before creating the privileged administrator.

Native Mac and Windows versions remain possible future products. They
should be treated as full platform ports with their own security design,
services, packaging, and tests—not as extra branches in the download
script.
