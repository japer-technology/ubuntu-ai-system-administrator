# Implementation plan for improvements 4

Source analysis: [`improvements-4.md`](improvements-4.md).

This plan adapts the proposed Zombie Floor Model to an explicit opt-in.
The normal `zombie` installation remains unchanged and does not download a
model. When enabled, the installer provisions a pinned, CPU-capable minimum
model for the zombie account and can expose that same model through a local,
OpenAI-compatible API on `127.0.0.1:58080`.

It does not implement these changes or select a production model. Runtime and
model assets must pass the supply-chain, licence, capability, and safety gates
below before their immutable identifiers are added to the repository.

## Decisions that supersede the source analysis

`improvements-4.md` describes a mandatory model on every installation and an
internal endpoint on port `11435`. This implementation must instead use these
decisions:

- The feature is off by default and enabled with
  `ZOMBIE_INSTALL_FLOOR_MODEL=1`.
- It is a sub-option owned by the existing `zombie` component, not a third
  public component. `install forgejo` never downloads or installs it.
- Enabling it installs one curated CPU model, expected to add roughly 2 GB
  after the runtime, model, metadata, and safe free-space reserve are counted.
- The model is consumed only by the zombie account by default. The inference
  process runs as a separate, non-login, non-sudo service account so model
  compromise or runtime exploitation cannot directly inherit zombie's sudo
  path or administrative privileges.
- The optional local-server mode serves the same model through an
  OpenAI-compatible `/v1` API on `127.0.0.1:58080`.
- A loopback TCP listener is host-local, not Unix-user-private. User-only
  access therefore also requires bearer authentication and restrictive key
  ownership; binding to `127.0.0.1` alone is not an access-control boundary.
- Ollama and LM Studio are not installed. A pinned `llama.cpp`
  `llama-server` provides the smallest auditable runtime and already supplies
  the required OpenAI-compatible API.
- GPU detection, larger tiers, and automatic fallback from an in-progress
  primary-provider turn are later phases. The first release is a predictable
  CPU-only minimum.

## Outcome and operating modes

One installation switch controls whether the feature exists. A separate mode
controls how the installed endpoint is presented:

| Mode | Purpose | API access |
| ---- | ------- | ---------- |
| `agent` | Private local intelligence for Ubuntu Zombie | Authenticated endpoint used by the zombie chat service; credentials are available only to root and the configured zombie account |
| `server` | LM Studio-like local service for compatible applications | The same authenticated OpenAI-compatible endpoint at `127.0.0.1:58080`; additional local clients receive access only through explicit operator-managed group membership |

Both modes run the same binary, model, systemd service, health checks, and
loopback endpoint. `server` does not weaken authentication or listen on LAN
interfaces. It adds a documented client contract and an opt-in
`ubuntu-zombie-llm-clients` group; the configured zombie account is the only
member created by the installer.

The initial OpenAI-compatible contract is deliberately narrow:

- `GET /v1/models`;
- `POST /v1/chat/completions`, including streaming when supported by the
  pinned runtime;
- bearer-token authentication on every `/v1` request;
- one immutable model ID advertised by default;
- no model upload, pull, delete, or arbitrary file APIs;
- no bind-address override beyond `127.0.0.1`;
- no unauthenticated compatibility mode.

## Public configuration

Add the following zombie-owned settings to `scripts/install.sh`,
`usage()`, interactive review, dry-run output, receipts, and
`docs/CONFIGURATION.md`:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `ZOMBIE_INSTALL_FLOOR_MODEL` | `0` | Master opt-in; accepts only `0` or `1` |
| `ZOMBIE_FLOOR_MODE` | `agent` | `agent` or `server` |
| `ZOMBIE_FLOOR_PORT` | `58080` | Must remain `58080` in the first release |
| `ZOMBIE_FLOOR_ASSET_SOURCE` | `auto` | Selects `auto`, `download`, `asset-dir`, or `cache` delivery |
| `ZOMBIE_FLOOR_ASSET_DIR` | empty | Directory containing pre-supplied pinned assets |
| `ZOMBIE_FLOOR_CACHE_DIR` | `/var/cache/ubuntu-zombie/floor` | Persistent verified download cache |
| `ZOMBIE_FLOOR_DOWNLOAD_BASE_URL` | empty | Optional operator mirror; filenames and hashes remain manifest-controlled |
| `ZOMBIE_FLOOR_KEEP_CACHE` | `1` | Preserve verified downloads after install for repair |

Do not expose an arbitrary model name, URL, checksum, runtime argument list,
bind address, or API key as an ordinary option. The repository-pinned manifest
owns those values. `ZOMBIE_FLOOR_PORT` exists for explicit validation and
receipt clarity, but values other than `58080` are rejected initially so the
documented API contract cannot drift.

Selection and validation rules:

- Ignore all floor-model settings when the option is disabled, preserving
  current default output and requirements.
- Reject the switch on a Forgejo-only target because the sub-option depends on
  the zombie account, chat runtime, policy, and audit facilities.
- In non-interactive mode, `auto` may use a valid cache and then the pinned
  online source. It must never prompt.
- `asset-dir` requires `ZOMBIE_FLOOR_ASSET_DIR`; a missing value exits `64`
  under `ZOMBIE_NONINTERACTIVE=1`.
- `download` requires successful network preflight to the approved source or
  configured mirror.
- `cache` requires complete, valid cached assets and must not access the
  network.
- A configured mirror may change only the origin prefix. Asset names, sizes,
  versions, and SHA-256 digests still come from the repository manifest.
- Reject port conflicts before downloading a multi-gigabyte model.

## Installed shape and ownership

Extend the zombie component with:

```text
/opt/ai-zombie/floor/
  bin/llama-server
  models/<pinned-model>.gguf
  manifest.json
  state/active.json

/etc/ubuntu-zombie/
  floor-model.env
  floor-api-key

/var/cache/ubuntu-zombie/floor/
  <versioned runtime asset>
  <versioned model asset>

/etc/systemd/system/
  ubuntu-zombie-floor.service
```

Ownership boundaries:

- Create `zombie-floor` as a system account with no password, no login shell,
  no home directory, and no sudo rights.
- Keep runtime, model, and manifest files root-owned and read-only to
  `zombie-floor`.
- Keep writable state in a dedicated directory writable only by
  `zombie-floor`; do not make the model directory writable by the service.
- Store the generated API key root-owned and readable through a dedicated
  client group. Add only the configured zombie account to that group in
  `agent` mode.
- In `server` mode, create the same group but require the operator to add any
  additional local client explicitly. Do not add all interactive users.
- Keep the API key out of command lines, environment displayed in receipts,
  logs, process titles, diagnostics, and audit payloads.
- Preserve the current zombie account's ownership of
  `/opt/ai-zombie/secrets/env`; add only the provider reference needed by the
  chat runtime, not a second plaintext copy of the key.

## Runtime and model manifest

Add `payload/etc/floor-models.json` as the sole catalogue. Its schema should
contain:

- schema version;
- logical runtime and model IDs;
- immutable upstream version and provenance;
- architecture-specific runtime assets;
- immutable URL path, filename, byte size, and SHA-256 for every asset;
- supported Ubuntu architectures;
- model format and quantisation;
- context size and the approved `llama.cpp` chat-template identifier;
- expected peak RAM and minimum system RAM;
- minimum free disk, including staging and safety reserve;
- licence identifier, licence URL, redistribution decision, and required
  notices;
- OpenAI-compatible runtime capabilities required by the integration;
- evaluation-suite version and pass result.

The parser must reject unknown schema versions, missing required fields,
duplicate IDs, unsafe filenames, mutable asset references, unsupported
architectures, size mismatches, missing or malformed hashes, unapproved
licences, and assets outside the selected manifest entry.

The model evaluation records the exact template identifier and a hash of the
GGUF chat-template metadata. Installation checks those values against the
approved manifest; it neither accepts an operator-supplied template nor
executes Jinja, Mustache, or another template language itself.

Start with exactly one `cpu-minimum` tier. Candidate guidance is a
0.5B–1.5B instruct model in Q4-class GGUF, but size alone is not approval.
The selected model must demonstrate reliable structured tool use and safe
Ubuntu diagnostics. Do not add placeholders that an installer could treat as
real assets.

## Supplying the roughly 2 GB installation

The normal release tarball and Debian package must remain small. They carry the
manifest and installer logic, not the GGUF. Support these delivery paths:

### 1. Verified online download

This is the normal `auto` fallback and explicit `download` path.

- Fetch the pinned runtime and model from immutable release assets.
- Download to a `.partial` file in the final cache filesystem, validate the
  expected byte count and SHA-256, then atomically rename it.
- Resume only when the server and existing partial file support a safe range
  request; otherwise restart the asset cleanly.
- Display the asset name, expected size, progress, and cache location without
  logging credentials or signed query parameters.
- Retry transient failures using existing installer download conventions.
- Never accept redirects to an unapproved scheme or an unvalidated final
  asset.

### 2. Pre-supplied offline asset directory

`asset-dir` supports air-gapped and bandwidth-controlled installations.

- Accept the exact manifest filenames in `ZOMBIE_FLOOR_ASSET_DIR`.
- Verify size and SHA-256 before copying anything into managed paths.
- Copy to a temporary file on the destination filesystem and rename
  atomically.
- Never execute a runtime directly from removable media or use an arbitrary
  GGUF supplied under another name.
- Leave the operator's source directory untouched.

### 3. Persistent verified cache

`cache` permits repeated installs and repairs without another download.

- Reuse only complete files matching the current manifest.
- Quarantine or remove corrupt cache entries; never silently trust filename
  or modification time.
- Keep the cache root-owned and non-writable by the zombie and model-service
  accounts.
- Preserve valid assets by default on zombie uninstall only when the operator
  explicitly chooses cache retention; otherwise remove them with the feature.

### 4. Sidecar offline bundle

Provide a release-process target for a separately distributed floor-model
bundle after asset selection. It must not be part of `make package`.

- Bundle the exact runtime/model assets, manifest, licence texts, and a
  checksums file.
- Version it against the Ubuntu Zombie release and manifest schema.
- Allow operators to unpack it and use the resulting directory through
  `ZOMBIE_FLOOR_ASSET_DIR`.
- Publish its checksum and provenance beside the normal release.
- Keep CI tests metadata-only; release validation may build and inspect the
  sidecar without committing it.

### 5. Operator-controlled mirror

Allow a private HTTP(S) mirror for fleets or constrained networks without
allowing model substitution.

- The mirror replaces only the approved base URL.
- Require HTTPS except for an explicitly documented loopback-only mirror.
- Resolve fixed manifest filenames beneath that base.
- Apply the same byte-size and digest checks as the upstream path.
- Do not permit mirror-provided manifests, redirects to local files, or
  inclusion of credentials in receipts.

### 6. Import from an existing exact asset

Treat an already downloaded GGUF or runtime as an offline asset-directory
input, not as a separate trust path. It is accepted only if its filename,
size, and digest exactly match the pinned manifest. Copy it into managed
storage; do not symlink to mutable user files.

### Delivery methods deliberately excluded

- Do not embed the model in the Git repository, normal release tarball, or
  default Debian package; this would make every download roughly 2 GB.
- Do not use `ollama pull`, mutable Hugging Face branch URLs, or an online
  model catalogue.
- Do not compile `llama.cpp` during normal installation; use reviewed,
  architecture-specific binaries.
- Do not require Docker, Snap, Flatpak, OCI images, Git LFS, peer-to-peer
  distribution, or a new package manager.
- Do not support a runtime-only state that reports the floor model as
  installed. If the model cannot be acquired and verified, the optional
  installation fails cleanly and the existing provider configuration remains
  usable.

### Disk, bandwidth, and failure handling

- Calculate requirements from manifest sizes rather than a hard-coded 2 GB
  estimate.
- Preflight the cache and install filesystems before download. On one
  filesystem, account for the partial asset plus final storage and reclaimable
  cache strategy. On different filesystems, reserve a full copy on each. If
  paths partially overlap or only some assets can be linked/reflinked,
  calculate each asset separately. Every case also reserves runtime space and
  a conservative post-install margin.
- Avoid a second full-size copy when cache and final model storage share a
  filesystem and a safe root-owned hard link or reflink is available; copying
  remains the portable fallback.
- Keep verified cache files after a failed service start so `repair zombie`
  does not repeat the download.
- Remove invalid partial files during repair after recording a non-secret
  diagnostic.
- A failed opt-in installation must stop before writing a successful zombie
  component manifest or final receipt status.

## Installer integration

Keep the floor model inside the registered `zombie` hooks in
`scripts/install.sh`; do not add it to `PUBLIC_COMPONENTS`.

### Configuration and review

- Add defaults and enum/flag/path validation beside existing zombie settings.
- Extend `any_option_enabled()` so default dry-run, banner, and receipt output
  remain unchanged while disabled.
- Add a “Floor model” entry to the zombie Options review. When enabled, show
  mode, fixed endpoint, model download size, source strategy, cache policy,
  and estimated disk requirement. Never show the token.
- Warn before confirmation that installation downloads approximately 2 GB,
  may take significant time, and remains CPU-only initially.
- In `server` mode, explain that the listener is loopback-only and that local
  clients still need the generated token and group access.
- Add conditional dry-run sections for account creation, asset acquisition,
  service deployment, endpoint verification, and provider integration.

### Idempotent installation sequence

Add a floor-model subroutine called by `install_zombie()` after base state is
prepared and before the chat service is started:

1. Validate the manifest and select the architecture-specific CPU runtime.
2. Check RAM, disk, port availability, and asset-source prerequisites.
3. Acquire and verify runtime and model assets using the selected delivery
   strategy.
4. Create or converge the `zombie-floor` service account and client group.
5. Generate a high-entropy API token only when no valid managed token exists.
6. Install runtime, model, manifest, environment, and state files atomically
   with restrictive ownership.
7. Render the hardened systemd unit with the fixed loopback endpoint.
8. Start the service and wait for bounded readiness.
9. Verify authenticated `/v1/models` and a short deterministic completion.
10. Configure the floor provider without replacing a valid operator-selected
    primary provider.
11. Start or restart the chat service only after provider configuration is
    internally consistent.
12. Record enabled mode, model ID, digest prefix, runtime version, endpoint,
    asset source, and cache policy in the root-only receipt; never record the
    token.

On re-run, preserve a valid token, reuse verified assets, replace corrupt or
wrong-version files, converge group membership and permissions, and restart
the floor service only when inputs or configuration changed.

## Hardened local service

Add `payload/systemd/ubuntu-zombie-floor.service` with:

- `User=` and `Group=` set to the dedicated `zombie-floor` account;
- ordering after local filesystems and before the chat service;
- restart-on-failure with bounded retry behaviour;
- loopback-only host and port fixed by managed configuration;
- credentials loaded from a protected file rather than `ExecStart`;
- no privilege escalation, capabilities, sudo, login shell, or writable model
  directory;
- read-only system and home views, private temporary storage, restricted
  devices, and a narrow writable state path;
- an outbound address-family/network policy that permits loopback serving but
  prevents Internet access during inference;
- memory, task, file-descriptor, and process limits derived from the approved
  CPU profile;
- journal output with request bodies and authorization headers disabled.

Implementation validation must also exercise stderr, bridge logs, audit
records, and diagnostic bundles to prove that alternate logging paths redact
the bearer token rather than relying only on the service's journal settings.
The restriction applies for the service's entire lifetime, including model
loading and health checks. Asset download and verification occur in the
root-run installer before service startup; the model process never needs
external network access for licence checks, configuration, or inference.

The chat unit should order itself after the floor service only when the option
is installed. A slow or failed floor start must not prevent deterministic
status/help endpoints from loading, but model-backed floor turns must report a
clear unavailable state.

## Provider and routing integration

Add a first-class internal provider name such as `floor`; do not overload
`lmstudio`, which remains the operator-managed discovery provider.

Changes span `payload/agent/providers.py`, both Node bridges,
`payload/agent/pi_mono.py`, and `payload/agent/server.py`:

- Register the floor model, key reference, and OpenAI-compatible endpoint
  independently of `ZOMBIE_PROVIDER` and `ZOMBIE_MODEL`.
- Keep existing provider selection as the primary provider.
- If no primary provider is configured and the floor option is healthy, use
  the floor provider for new turns.
- Add an explicit `/floor` selection and `/model primary` return path rather
  than rewriting the operator's primary settings.
- Restrict environment forwarding so the floor token reaches only the floor
  bridge invocation.
- Prevent `/model`, `/local`, or `/locals` from deleting or rewriting the
  managed floor endpoint, model, or credential.
- Report primary provider and floor health separately in `/status` and the UI.
- In `server` mode, retain the same zombie-provider integration; “server”
  means the API is a supported local client surface, not that Zombie stops
  using it.

The first release should not retry a failed primary turn automatically.
Fallback is selected before a turn when no usable primary exists or when the
operator explicitly chooses it. Implement automatic pre-output fallback only
in a later phase after the bridge can prove that no text, tool call, approval,
or mutation occurred. Never replay after tool activity.

## Capability restrictions, policy, and audit

A small local model must receive a stricter capability profile than a hosted
primary model. Intersect the floor profile with the normal policy result:

- allow read-only inspection, explanation, summarisation, and skill loading;
- require approval for user-owned changes;
- permit system changes only through curated skills and explicit approval;
- disable arbitrary mutating shell commands, network changes, and destructive
  actions in the first release;
- deny writes to floor runtime, model, manifest, token, service unit, and
  capability-profile paths.

Do not create a direct privileged path for model management. Installation,
repair, and removal remain operator-run lifecycle actions. Any later
chat-driven floor service control must use existing `svc.control`, normal
policy classification, approval, and audit logging.

Extend audit/history metadata with the provider role, provider, model ID,
digest prefix, floor mode, endpoint health, and fallback reason. Add the floor
token to redaction coverage. Never audit prompts or hardware identifiers
beyond existing policy, and never include the full model digest where a short
diagnostic prefix suffices.

## Lifecycle operations

### Verify

When disabled, floor checks remain silent. When installed, `verify zombie`
checks:

- manifest schema, selected architecture, runtime version, model size, and
  hashes;
- service account, group membership, ownership, and modes;
- API-key presence and restrictive permissions;
- service enabled/active state and sandbox properties;
- listener exists only on `127.0.0.1:58080`;
- unauthenticated requests fail;
- authenticated `/v1/models` advertises only the pinned model;
- a bounded authenticated completion succeeds;
- the chat runtime can resolve the floor provider;
- the service has no sudo rights and no external listener.

### Doctor

Diagnose disabled-vs-installed state, insufficient RAM/disk, unsupported
architecture, port collision, interrupted download, cache corruption, hash or
version mismatch, permissions drift, authentication failure, service crash,
out-of-memory termination, malformed OpenAI response, and chat-provider
routing failure. Include safe repair commands and log paths, never the token.

### Repair

Revalidate the manifest and existing assets, reacquire only missing or corrupt
approved assets, preserve a valid token, converge ownership and group
membership, restore managed configuration and the unit, restart when needed,
and repeat endpoint/provider checks. Honour the original source policy where
possible; an explicit offline `cache` or `asset-dir` repair must not silently
use the network.

### Uninstall

`uninstall zombie` stops and removes the floor unit, runtime, model, state,
token, generated configuration, service account, and managed group when safe.
Remove the cache unless an explicit keep-cache choice is made. Selective
`uninstall forgejo` leaves all floor resources untouched. `--keep-agent`
removes the floor service, runtime, installed model, token, and provider
integration because they are managed executable state; it preserves only a
verified cache when `ZOMBIE_FLOOR_KEEP_CACHE=1`.

## Documentation and release changes

Update:

- `README.md` for the opt-in promise, approximate download, CPU expectation,
  and local API example;
- `docs/CONFIGURATION.md` for every option, source strategy, client
  authentication, and repair behaviour;
- `docs/ARCHITECTURE.md` for the process, user, file, network, provider, and
  policy trust boundaries;
- `docs/PLATFORMS.md` for supported architectures and minimum RAM/disk;
- `SECURITY.md` for loopback limitations, bearer-token handling, model/runtime
  supply chain, and the untrusted-model boundary;
- `CONTRIBUTING.md` for manifest updates and real-model evaluation rules;
- `CHANGELOG.md` and `VERSION` for the user-visible feature.

Do not claim that every Zombie has local intelligence. State that the floor
model is available as an opt-in and is off by default.

## Test and evaluation plan

Normal CI must never download the real model or contact an inference registry.
Extend `tests/smoke.sh` and fixtures with:

- disabled-by-default and unchanged default dry-run assertions;
- option enum, flag, port, path, target, and non-interactive validation;
- zombie-only ownership and Forgejo-only isolation;
- manifest schema, duplicate, filename, size, digest, architecture, and
  licence rejection tests;
- mocked download, interrupted download, cache hit, corrupt cache, offline
  asset, and mirror tests using tiny fixtures;
- idempotent token, account, group, files, and unit rendering tests;
- systemd static hardening and fixed-loopback assertions;
- authenticated endpoint fixtures for models, chat completions, streaming,
  unauthorized access, timeout, and malformed responses;
- primary/floor provider resolution and key-isolation tests;
- floor capability-profile intersection and denied-action tests;
- audit redaction and metadata tests;
- verify/doctor/repair/uninstall fixture coverage;
- packaging checks that no GGUF, cache, partial download, token, or local state
  enters the release.

Create a separate manual or release-validation suite for the real pinned
assets. It must cover model hash/provenance, licence notices, CPU startup,
peak RAM, latency, valid structured tool calls, Ubuntu diagnostic accuracy,
approval handling, refusal of unsupported mutations, offline inference, and
clean install/repair/uninstall on supported Ubuntu LTS VMs.

## Delivery phases

### Phase 1 — Contract and asset approval

1. Finalise names, modes, fixed port, ownership, and manifest schema.
2. Evaluate candidate GGUF models and pinned `llama.cpp` builds.
3. Approve provenance, licences, redistribution, hashes, and resource limits.
4. Add tiny fixtures for all metadata and delivery tests.
5. Land documentation without changing default installation behaviour.

### Phase 2 — Asset delivery and lifecycle

1. Add manifest parsing and all source strategies.
2. Add disk preflight, resumable partial handling, cache convergence, and
   atomic installation.
3. Add account, group, token, files, and hardened service deployment.
4. Add verify, doctor, repair, and uninstall handling.
5. Prove idempotence and air-gapped installation.

### Phase 3 — Agent-only provider

1. Register the first-class floor provider.
2. Isolate floor credentials from all other providers.
3. Use floor for new turns only when no primary provider is usable or the
   operator selects it.
4. Add the restricted capability profile, UI status, audit metadata, and
   command handling.

### Phase 4 — OpenAI-compatible server mode

1. Formalise the `127.0.0.1:58080/v1` compatibility contract.
2. Add explicit local-client group access and client documentation.
3. Test compatible clients against models, chat completions, authentication,
   and streaming.
4. Confirm that server mode never changes the bind address or exposes a LAN
   service.

### Phase 5 — Optional safe fallback

1. Add bridge event tracking that proves whether meaningful output or tool
   activity began.
2. Permit one automatic fallback only before output, tools, approvals, or
   mutations.
3. Suppress replay after activity and provide an explicit new-floor-turn
   action.
4. Add failure tests for authentication, DNS, rate limits, timeouts, malformed
   responses, and local service loss.

### Phase 6 — Release hardening

1. Validate online, cache, mirror, sidecar, and air-gapped paths on supported
   Ubuntu LTS machines.
2. Run real CPU resource and model safety evaluations.
3. Verify clean upgrades, re-runs, repairs, selective uninstalls, and complete
   uninstalls.
4. Run `make lint`, `make test`, and `make package`.
5. Scan changed files and release artefacts for secrets.
6. Confirm the normal package remains model-free and document the sidecar
   checksum.

GPU acceleration and larger model tiers should be separate follow-up work.
They must not delay or complicate the first CPU-only, opt-in implementation.

## Expected file changes

Likely new files:

```text
payload/etc/floor-models.json
payload/systemd/ubuntu-zombie-floor.service
payload/bin/floor-launch
payload/bin/floor-model-health
payload/agent/floor.py
tests/fixtures/floor/
```

`floor-launch` is an internal service-initialisation wrapper used only by
`ubuntu-zombie-floor.service` to validate managed state before `llama-server`
starts. `floor-model-health` is the operator/lifecycle health helper, matching
the existing helper naming pattern.

Likely modified files:

```text
README.md
docs/ARCHITECTURE.md
docs/CONFIGURATION.md
docs/PLATFORMS.md
SECURITY.md
CONTRIBUTING.md
scripts/install.sh
scripts/uninstall.sh
payload/agent/providers.py
payload/agent/pi-ai-bridge.mjs
payload/agent/pi-mono-bridge.mjs
payload/agent/pi_mono.py
payload/agent/server.py
payload/agent/policy.py
payload/agent/audit.py
payload/etc/policy.yaml
payload/bin/verify
tests/smoke.sh
Makefile
CHANGELOG.md
VERSION
```

## Acceptance criteria

1. A normal zombie or Forgejo installation downloads no model and has
   byte-for-byte-compatible default dry-run option output.
2. `ZOMBIE_INSTALL_FLOOR_MODEL=1` installs a verified CPU model without a
   cloud key, Ollama, LM Studio, Docker, or a GPU.
3. The only listener is authenticated and bound to
   `127.0.0.1:58080`.
4. The zombie account is the only generated API client by default.
5. The inference process runs without login, sudo, or administrative
   privileges and cannot modify its model/runtime.
6. `agent` and `server` modes use the same pinned model and OpenAI-compatible
   runtime; server mode supports explicitly authorized local clients.
7. Existing primary providers and LAN-discovered `lmstudio` providers continue
   to work unchanged.
8. Floor credentials are never forwarded to another provider or printed in
   logs, receipts, diagnostics, process arguments, or audit records.
9. Online, offline-directory, cache, sidecar, exact-asset import, and mirror
   delivery all enforce the repository manifest and hashes.
10. Interrupted or corrupt downloads cannot become active assets.
11. Disk preflight accounts for the real manifest sizes and installation
    topology.
12. Re-running install and repair reuses valid assets and credentials without
    duplicate users, groups, files, or services.
13. The floor model cannot bypass tool schemas, capability restrictions,
    policy approval, or audit logging.
14. `verify`, `doctor`, `repair`, and `uninstall zombie` cover the complete
    lifecycle; Forgejo lifecycle operations do not affect it.
15. Non-interactive and air-gapped installs work with explicit inputs.
16. CI uses tiny fixtures and never downloads multi-gigabyte assets.
17. Real release assets pass provenance, licence, checksum, offline, resource,
    OpenAI-compatibility, capability, and safety evaluations.
18. The normal release package contains no model, token, cache, partial
    download, or machine-local state.
19. `make lint`, `make test`, and `make package` pass.
