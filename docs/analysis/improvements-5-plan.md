# Implementation plan for improvements 5

This plan adds managed `llama.cpp` installation in two deliberately separate
forms:

1. a standalone, PC-wide `llama` component on `127.0.0.1:8080`; and
2. an optional Zombie-private instance on `127.0.0.1:58080`.

It does not implement either installation or select a production
`llama.cpp` commit or model. Those immutable inputs must pass the build,
licence, provenance, compatibility, resource, and safety gates below before
they are added to the repository.

## Decisions

### Two installations, not two modes of one installation

The public and private installations must be independently selectable,
configured, upgraded, repaired, and removed.

| Property | Standalone PC instance | Zombie-private instance |
| -------- | ---------------------- | ----------------------- |
| Selection | `scripts/install.sh install llama` | Zombie-owned opt-in during `install zombie` |
| Legacy environment selector | `ZOMBIE_INSTALL_LLAMA=1` | `ZOMBIE_INSTALL_ZOMBIE_LLAMA=1` |
| Component model | Public `llama` component | Sub-option of `zombie` |
| Listener | `127.0.0.1:8080` | `127.0.0.1:58080` |
| Base URL | `http://127.0.0.1:8080/v1` | `http://127.0.0.1:58080/v1` |
| Primary consumers | Authorised local applications and users | Ubuntu Zombie only |
| Manager default | `llama-manager` | Protected Zombie lifecycle/provider integration |
| Active runtime | `/opt/llama.cpp/current/` | `/opt/ai-zombie/llama/current/` |
| Configuration | `/etc/llama.cpp/` | `/etc/ubuntu-zombie/llama/` |
| Models and state | `/var/lib/llama.cpp/` | `/opt/ai-zombie/llama/` and protected state |
| Service | `llama-server.service` | `ubuntu-zombie-llama.service` |
| Service account | Dedicated non-login `llama-cpp` account | Dedicated non-login `zombie-llama` account |

`ZOMBIE_INSTALL_LLAMA` is reserved for selecting the public `llama`
component. A different name is necessary for the private sub-option so an
existing automation input cannot accidentally install both instances.

The standalone component has no dependency on `zombie`. These are valid:

```text
scripts/install.sh install llama
scripts/install.sh install zombie
scripts/install.sh install zombie llama
scripts/install.sh verify llama
scripts/install.sh repair zombie llama
scripts/install.sh uninstall llama
```

The private instance is valid only when `zombie` is selected. A Forgejo-only
or llama-only installation must never create a Zombie account, private model,
private key, provider configuration, or port-58080 listener.

### Meaning of public and private

“Public” means available to explicitly authorised applications and users on
the PC. It does not mean Internet-facing or LAN-facing. The first release
must bind only to `127.0.0.1`; exposing it through a reverse proxy or another
interface is out of scope.

“Private” means that an unprivileged local user cannot perform inference,
read the model configuration, obtain the API credential, or control the
service. Loopback binding alone does not provide Unix-user isolation, so the
private endpoint must also require a generated bearer credential readable
only by root, the Zombie account, and the private service where required.
The plan cannot protect the instance from host root, which is outside the
threat boundary.

Both endpoints require authentication by default. The public instance uses a
dedicated local-client group so the operator can authorise additional local
applications without weakening the private instance.

### Relationship to improvements 4

This plan replaces the runtime-management portions of
[`improvements-4-plan.md`](improvements-4-plan.md) with the private
port-58080 instance described here. The private instance remains compatible
with the floor-model intent, but gains:

- the same pinned build and management principles as the standalone
  component;
- explicit CPU/GPU, model, quantisation, boot, loading, and idle policies;
- exact manager-reported state;
- clean coexistence with a standalone PC instance.

Implementation must choose one private-instance specification and remove
duplicate floor-model units, options, ports, and provider identities. It
must not install both `ubuntu-zombie-floor.service` and
`ubuntu-zombie-llama.service` for the same role.

## Product outcome

After a standalone installation, the operator can use:

```text
llama-manager status
llama-manager start
llama-manager stop
llama-manager restart
llama-manager enable
llama-manager disable
llama-manager test
llama-manager models
llama-manager hardware
```

The standalone application remains useful if Ubuntu Zombie is not installed
or is later removed.

Ubuntu Zombie must use the same control contract for state and lifecycle
operations, rather than reimplementing systemd, model, and health logic in
the chat server. Private control must additionally pass through the existing
policy gate, approval path, and audit log whenever it is initiated from chat.

The implementation must let the operator choose:

- an approved model family and size;
- an approved GGUF quantisation for that model;
- context size within tested limits;
- CPU-only or GPU-assisted inference;
- a specific detected GPU;
- full, partial, or zero GPU offload;
- CPU thread count within detected limits;
- whether the service starts at boot;
- `resident`, `sleep`, `on-demand`, or `manual` loading policy.

Recommendations are advisory. The installer must display the detected
hardware, recommendation, expected RAM/VRAM/disk use, and any warning before
the operator confirms a selection. It must never silently turn a
recommendation into consent.

## Installed layout

### Standalone PC instance

Use the requested independent application layout:

```text
/opt/llama.cpp/
  versions/
    <build-id>/
      bin/
        llama-server
        llama-cli
        llama-bench
      build.json
  current -> versions/<build-id>

/usr/local/bin/
  llama-manager

/usr/local/libexec/llama-manager/
  launcher
  hardware-detect
  model-inspect
  benchmark
  control-service

/etc/llama.cpp/
  config.json
  build.json
  model-catalog.json
  api-key
  managed-by-ubuntu-zombie

/var/lib/llama.cpp/
  models/
  downloads/
  benchmarks/
  state/

/var/log/llama.cpp/

/etc/systemd/system/
  llama-server.service
```

`/opt/llama.cpp/current` changes only by atomic symlink replacement after the
new build and a staged health test succeed. Keep at least the previously
working managed build for rollback.

### Zombie-private instance

Use a separate namespace:

```text
/opt/ai-zombie/llama/
  versions/
    <build-id>/
      bin/
        llama-server
        llama-cli
        llama-bench
      build.json
  current -> versions/<build-id>
  models/
  state/

/opt/ai-zombie/bin/
  zombie-llama-manager

/etc/ubuntu-zombie/llama/
  config.json
  build.json
  model-catalog.json
  api-key

/var/cache/ubuntu-zombie/llama/
  source/
  models/

/etc/systemd/system/
  ubuntu-zombie-llama.service
```

Do not symlink binaries, configuration, models, credentials, state, service
units, or active-version pointers between the installations. A verified
download cache could be shared only in a later design with safe reference
tracking; the first release should favour isolation over disk optimisation.

## Existing-installation safety

The installer must not adopt, upgrade, stop, reconfigure, or remove an
unmanaged `llama.cpp` installation.

Before final selection, inspect:

- port `8080` and port `58080`;
- existing `llama-server` processes and units;
- `/opt/llama.cpp`, `/etc/llama.cpp`, `/var/lib/llama.cpp`, and
  `/usr/local/bin/llama-manager`;
- package-manager, Snap, Flatpak, container, user-local, and source-tree
  installations where they can be identified without mutation;
- existing `llama-cpp` and `zombie-llama` users and groups.

The standalone paths require a root-owned ownership marker containing the
component and manifest format. If any requested path, service name, account,
or port exists without a valid marker from this installer, fail before
mutation and explain the conflict. Do not rename, delete, or reuse it.

The private installer never scans for and adopts another server. It owns only
its port-58080 namespace. Existing servers continue to be discoverable
through the current operator-managed local-provider flow.

Uninstall removes only files and identities recorded as managed by the
selected component. It never searches for and removes similarly named
third-party files.

## Configuration contract

### Standalone component

Add these settings to `scripts/install.sh`, help, interactive review,
dry-run output, receipts, and `docs/CONFIGURATION.md`:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `ZOMBIE_INSTALL_LLAMA` | `0` | Compatibility selector for the public component |
| `LLAMA_PORT` | `8080` | Fixed standalone loopback port in the first release |
| `LLAMA_MODEL_ID` | none | Approved model-catalogue identifier |
| `LLAMA_QUANTISATION` | none | Approved quantisation for the selected model |
| `LLAMA_CONTEXT_SIZE` | `recommended` | Tested context size or explicit approved value |
| `LLAMA_COMPUTE` | `cpu` | Lowercase backend enum; accelerator validity comes from the selected build/model catalogue entries |
| `LLAMA_GPU_DEVICE` | none | Stable detected device identifier |
| `LLAMA_GPU_OFFLOAD` | `0` | Layer count or `full` |
| `LLAMA_CPU_THREADS` | `recommended` | Positive value not exceeding detected threads |
| `LLAMA_BOOT` | `enabled` | `enabled` or `disabled` |
| `LLAMA_LOAD_POLICY` | `resident` | `resident`, `sleep`, `on-demand`, or `manual` |
| `LLAMA_IDLE_SECONDS` | `900` | Idle threshold when `sleep` is selected |
| `LLAMA_API_KEY` | generated | Optional operator-supplied public-instance key |
| `LLAMA_SOURCE_MODE` | `download` | `download`, `cache`, or `source-dir` |
| `LLAMA_MODEL_SOURCE_MODE` | `download` | `download`, `cache`, or `model-dir` |

`LLAMA_API_KEY` follows the repository's credential convention: if unset,
generate it and record it only in the root-only receipt; if supplied, use it
without recording its plaintext. The active key is stored in a protected
file and never placed in `ExecStart`, process titles, general logs, or
diagnostic bundles.

### Zombie-private sub-option

Add parallel but separately named settings:

| Variable | Default | Purpose |
| -------- | ------- | ------- |
| `ZOMBIE_INSTALL_ZOMBIE_LLAMA` | `0` | Private-instance opt-in |
| `ZOMBIE_LLAMA_PORT` | `58080` | Fixed private loopback port |
| `ZOMBIE_LLAMA_MODEL_ID` | none | Approved private model identifier |
| `ZOMBIE_LLAMA_QUANTISATION` | none | Approved model quantisation |
| `ZOMBIE_LLAMA_CONTEXT_SIZE` | `recommended` | Tested context size |
| `ZOMBIE_LLAMA_COMPUTE` | `cpu` | Selected backend |
| `ZOMBIE_LLAMA_GPU_DEVICE` | none | Stable detected device identifier |
| `ZOMBIE_LLAMA_GPU_OFFLOAD` | `0` | Layer count or `full` |
| `ZOMBIE_LLAMA_CPU_THREADS` | `recommended` | Private-instance thread limit |
| `ZOMBIE_LLAMA_BOOT` | `enabled` | Boot enablement |
| `ZOMBIE_LLAMA_LOAD_POLICY` | `sleep` | Private loading policy |
| `ZOMBIE_LLAMA_IDLE_SECONDS` | `900` | Private sleep threshold |
| `ZOMBIE_LLAMA_SOURCE_MODE` | `download` | Runtime source policy |
| `ZOMBIE_LLAMA_MODEL_SOURCE_MODE` | `download` | Model source policy |

Do not accept a private API key through the normal environment. Generate it
on the target, preserve it on convergent re-runs, and make it readable only
by the required root-owned client group. This avoids leaking it through
automation environments.

Use `quantisation` in prose, user-facing text, and Ubuntu Zombie environment
names, following the repository convention. Translate it to any differently
spelled upstream runtime flag only inside the managed launcher.

### Validation and non-interactive behaviour

Validate all selected values before installing packages, downloading source,
or changing the host.

- Ports remain fixed at `8080` and `58080` for the first release.
- Model and quantisation must be a permitted catalogue pair.
- Context size must be supported by that pair and fit the resource policy.
- CPU threads cannot exceed detected logical threads.
- GPU selection requires a detected, usable backend and stable device.
- Offload cannot exceed the model's tested layer count or estimated VRAM.
- `sleep` requires a pinned runtime with tested native idle sleep.
- `on-demand` permits automatic `ensure-running` only for the private Zombie
  provider. Public third-party clients must run `llama-manager start`
  explicitly or select `resident` or `sleep`; the public instance never
  starts automatically in response to an API connection.
- `manual` disables automatic start and automatic recovery.
- A public and private combined install must have enough RAM, VRAM, disk, and
  port capacity for both selections, including simultaneous loading.

In interactive mode, show recommendations and require a final choice. In
`ZOMBIE_NONINTERACTIVE=1`, require explicit model, quantisation, compute,
offload, boot, and load-policy values; missing required input exits `64`.
Non-interactive mode must never infer consent from a recommendation.

## Hardware inspection and recommendations

### Read-only inspection

Run inspection before presenting installation choices and do not alter the
host during this phase. Collect:

- Ubuntu release and supported status;
- architecture and CPU model;
- physical cores and logical threads;
- relevant CPU instruction sets;
- total and currently available RAM;
- free space on source, build, cache, and model filesystems;
- GPU vendor, model, stable identifier, VRAM, and device nodes;
- loaded driver and userspace-toolkit versions;
- available CPU, CUDA, ROCm, Vulkan, and SYCL build prerequisites;
- port ownership for `8080` and `58080`;
- existing managed and unmanaged llama installations.

Write a redacted hardware report suitable for the screen and receipt. Do not
collect hardware serial numbers or send the report over the network.

### Recommendation engine

Use repository-owned data rather than free-form heuristics. The model
catalogue records tested combinations of:

- model and quantisation;
- minimum and expected RAM;
- model and temporary download sizes;
- context-memory growth;
- supported backends;
- layer count and estimated per-layer VRAM;
- recommended threads;
- expected CPU and GPU performance class.

The report should distinguish:

1. detected capacity;
2. recommended selection;
3. operator selection;
4. warning or rejection reason.

Allow an operator to override a soft recommendation after a prominent
resource warning. Reject a selection only when it cannot satisfy a hard
compatibility, disk-safety, backend, or minimum-memory requirement.

When both instances are selected, recommend jointly. Do not recommend the
same GPU at full capacity to both services unless the simultaneous-load
estimate retains a conservative VRAM reserve.

## Pinned source and build pipeline

### Source policy

Pin one reviewed `ggml-org/llama.cpp` commit in a repository-owned build
manifest. Never build a moving branch or resolve “latest” during install.
The manifest must record:

- source repository;
- immutable commit SHA;
- source archive URL and SHA-256;
- CMake options for each supported backend and architecture;
- required compiler and toolkit ranges;
- expected binaries;
- build-test version;
- build provenance and licence notices.

The normal installer builds on the target only after source verification and
selection confirmation. A later release may provide reproducible,
architecture-specific binary assets, but those must have equivalent
provenance and hash metadata.

### Build variants

Always produce and retain a CPU-optimised build. Optionally build one
selected accelerator variant:

- NVIDIA CUDA;
- AMD ROCm;
- Vulkan;
- Intel SYCL only for catalogue-approved Intel hardware, driver, compiler,
  and oneAPI toolkit combinations.

Prefer separately tested variants instead of one binary containing every
backend. This reduces dependency and compatibility risk and preserves a CPU
rollback path.

Do not install or replace proprietary GPU drivers automatically in the first
release. A GPU build may use an already functioning, supported driver and
toolkit. Missing prerequisites produce guidance, not an implicit kernel or
desktop driver change.

Build in a root-owned staging directory with restrictive permissions. Verify
the source digest, compile without network access, run version and smoke
probes, copy only expected binaries into a new version directory, write
`build.json`, and atomically switch `current` only after the staged server
passes a bounded health and inference test.

The build identity should include the pinned commit, architecture, backend,
and build-option digest. An identical valid build is reused on re-run.

### Upgrades and rollback

An upgrade must:

1. retain the active build;
2. acquire and verify the newly pinned source;
3. build into a new immutable directory;
4. test with the selected model on a non-public staging port;
5. stop only the selected managed instance;
6. switch `current` atomically;
7. restart and verify the normal endpoint;
8. roll back the symlink and service if readiness or inference fails.

Do not change both public and private active builds in one untracked
transaction. Upgrade and record each instance independently.

## Model catalogue and acquisition

Add a repository-owned catalogue with:

- schema version and logical model ID;
- model family, parameter size, GGUF format, and quantisation;
- immutable source revision, filename, byte size, and SHA-256;
- licence identifier, source, redistribution decision, and notices;
- chat-template identifier and metadata digest;
- context limits and tested default;
- layer count;
- expected RAM, VRAM, and disk use;
- tested backend and `llama.cpp` build-manifest compatibility;
- required OpenAI-compatible capabilities;
- evaluation-suite version and result.

Reject mutable branch URLs, unknown schema versions, unsafe filenames,
duplicate IDs, missing hashes, size mismatches, unapproved licences,
untested templates, and model/build combinations outside the catalogue.
Installation compares the exact GGUF chat-template identifier and metadata
digest with the approved catalogue entry. Only the pinned `llama.cpp` runtime
interprets that verified template during inference; installer and manager
processes treat it as opaque data.

Download to a partial file in the managed cache, verify size and SHA-256,
then rename atomically. Support exact offline source directories and verified
caches without changing the trust path. Never execute a binary or load a
model directly from removable or user-writable storage.

Normal CI uses tiny fixtures and never downloads or builds the real runtime
or model.

## Manager and exact state model

Implement `llama-manager` with the Python standard library and small shell
launchers where appropriate; do not add a language-level dependency.

The manager reads configuration as data, validates ownership and schema, and
combines:

- managed ownership marker;
- active build and build metadata;
- active model metadata;
- systemd enabled, active, failed, and restart state;
- process identity and command;
- listener address and port;
- authenticated `/health` response;
- model loading, ready, sleeping, and error states;
- last successful API test;
- current compute backend and actual offload.

Expose a stable machine-readable JSON mode as well as concise human output.
Define explicit states such as:

```text
absent
installed-stopped
starting
loading
ready
sleeping
stopping
failed
degraded
conflict
```

Never report `ready` from process existence alone. Readiness requires the
expected managed process, fixed listener, authenticated health response,
selected model, and expected build identity.

Read-only commands (`status`, `hardware`, and safe metadata inspection)
should work without root where file permissions permit. Mutating commands
require root or the existing approved Zombie control path. The manager must
not implement a setuid helper.

The private wrapper fixes the instance to `zombie`, loads only protected
private paths, and cannot be redirected to an arbitrary unit, path, port, or
command through environment variables.

## Loading and boot policies

Define the policies precisely:

| Policy | Boot behaviour | Idle behaviour | Start trigger |
| ------ | -------------- | -------------- | ------------- |
| `resident` | Respects the instance boot setting (`enabled` or `disabled`) | Model remains loaded after it is started | Automatic through systemd when boot is enabled, or manual through the manager |
| `sleep` | Respects the instance boot setting (`enabled` or `disabled`) | Pinned native runtime sleep after idle threshold | Manager start or an authenticated request to a running, sleeping service |
| `on-demand` | Service disabled at boot | Service stops when no longer needed | Manager `ensure-running`; Zombie provider uses this before a private turn |
| `manual` | Service disabled at boot | No automatic transition | Operator runs manager `start` |

For `resident` and `sleep`, a disabled boot setting leaves the installed
service stopped after boot until the manager starts it. `on-demand` and
`manual` always require boot to be disabled; reject conflicting input.

Do not emulate transparent on-demand startup by placing an unreviewed proxy
in front of the API. Public third-party clients must call
`llama-manager start` or use `resident`/`sleep`. The private Zombie provider
may call the protected `ensure-running` operation before a turn.

The pinned-build release validation must prove native sleep by observing the
documented health-state transition, then sending an authenticated inference
request and observing a bounded return to ready with a valid response. If the
selected runtime cannot pass that integration test, omit `sleep` rather than
approximating it with an unreliable process watcher.

## systemd and process isolation

Both services run as dedicated non-login, non-sudo users and use separate
groups, runtime directories, credentials, models, and writable state.

Each unit must include:

- fixed executable and configuration paths;
- fixed loopback bind address and instance-specific port;
- no shell-expanded arbitrary argument string;
- `NoNewPrivileges` and no capabilities;
- read-only runtime and model trees;
- a narrow writable state/runtime directory;
- private temporary storage;
- restricted devices, widened only to the selected GPU nodes;
- bounded restart behaviour and startup timeout;
- memory, task, process, and file-descriptor limits;
- journal output that excludes prompts, API keys, and authorisation headers;
- no outbound network requirement during inference.

The public `llama-clients` group receives the public credential. Add only the
invoking desktop user after explicit confirmation. The private client group
contains only the configured Zombie account. Never add all interactive users
or reuse group membership between instances.

Starting one service must not stop, restart, reconfigure, or consume the
credential of the other.

## OpenAI-compatible and health contract

Validate the exact pinned runtime rather than assuming compatibility from
upstream documentation. The release gate must prove:

- `GET /health` reports loading and ready states;
- `GET /v1/models` returns the selected logical model;
- `POST /v1/chat/completions` works;
- streaming chat completions work where advertised;
- responses and embeddings work only for catalogue entries that claim them;
- unauthenticated requests fail;
- malformed authentication does not leak the key;
- request and model-loading timeouts are bounded;
- shutdown and restart leave no stale listener.

The public endpoint remains `http://127.0.0.1:8080/v1`; the private endpoint
remains `http://127.0.0.1:58080/v1`.

## Ubuntu Zombie integration

Add a first-class private provider identity such as `zombie-llama`. Do not
overload `lmstudio`, which remains the generic operator-managed local-server
provider.

Private integration must:

- preserve an existing selected primary provider unless the operator chooses
  the private model;
- configure the exact private base URL and logical model ID;
- pass the private credential only to the private bridge invocation;
- call `ensure-running` before each inference request for `on-demand`;
- report `starting`, `loading`, `sleeping`, `ready`, and failure states in
  chat status and model UX;
- provide clear recovery guidance without exposing credentials or command
  internals;
- prevent `/model`, `/local`, and `/locals` from rewriting the managed
  endpoint or credential;
- keep deterministic status/help available if inference is unavailable.

The standalone public instance may also be selected through the existing
generic local-provider flow, but installing it must not automatically replace
the operator's provider choice.

Any chat-driven start, stop, restart, enable, disable, model change, compute
change, or benchmark is classified by `payload/agent/policy.py`, requires the
appropriate approval, and is written by `payload/agent/audit.py`. The agent
must call the manager's constrained operation, not construct arbitrary
systemd or build commands.

Model or compute changes are staged transactions:

1. validate catalogue and hardware compatibility;
2. acquire and verify required assets;
3. render a temporary configuration;
4. test on a staging port;
5. activate atomically;
6. restart only the selected instance;
7. verify health and inference;
8. restore the previous configuration on failure.

## Installer integration

### Public component registration

Register `llama` after the existing independent components in
`scripts/component-registry.sh` usage. Implement all required hooks:

- configuration validation;
- target-scoped review;
- dry-run;
- receipt start and finish;
- install;
- manifest write;
- final summary;
- legacy detection;
- verify;
- doctor;
- repair;
- phase count;
- uninstall removal.

The component has no `zombie` dependency. Installing it must not create the
Zombie account, deploy chat, alter Zombie policy, or require provider input.

Write the `llama` component manifest only after the selected build, model,
service policy, authentication, health, and API tests pass.

### Private zombie sub-option

Keep the private instance inside the registered `zombie` hooks. Add it to the
Zombie Options menu, review, dry-run, receipt, phase count, install, verify,
doctor, repair, manifest sub-options, and uninstall path.

When disabled, it must not prompt, inspect ports beyond existing preflight,
download, build, alter default dry-run output, or change provider selection.

### Idempotent install sequence

For each selected instance:

1. inspect the host without mutation;
2. display hardware and conflict report;
3. compute recommendations;
4. collect and validate final operator choices;
5. confirm build, download, RAM, VRAM, disk, port, and service impact;
6. install only missing build prerequisites;
7. acquire and verify pinned source and model assets;
8. build or reuse the exact CPU and selected accelerator variants;
9. create or converge the dedicated user, groups, directories, and key;
10. install versioned assets and configuration atomically;
11. render the hardened unit;
12. apply boot and load policy;
13. start only when the policy requires it;
14. wait for bounded health and run the API test when started;
15. configure Zombie provider integration only for the private sub-option;
16. write receipt and component state only after success.

On re-run, preserve valid credentials, models, selections, and working
builds. Rebuild or restart only when an input, selected version, or managed
configuration changed.

## Lifecycle behaviour

### Verify

For each selected installed instance, verify:

- ownership marker and component manifest;
- configuration and catalogue schemas;
- source, build, binary, and model identity;
- active-version symlink target;
- users, groups, ownership, and modes;
- key presence and restrictive permissions;
- unit hardening and expected boot state;
- process user and fixed arguments;
- listener exists only at the expected loopback address and port;
- unauthenticated requests fail;
- health, selected model, and API test match the configured state;
- selected backend and actual GPU offload match policy;
- the other instance's files, service, and port were not altered.

`manual` and stopped `on-demand` are valid states, not verification failures,
when configuration and a manager-started health test succeed.

### Doctor

Diagnose:

- unmanaged path, account, unit, or port conflicts;
- unsupported host, architecture, CPU feature, GPU, driver, or toolkit;
- insufficient build, model, RAM, VRAM, or disk capacity;
- source/model download interruption or digest mismatch;
- compile and linker failures;
- invalid current symlink or failed rollback;
- model loading, sleep/wake, authentication, and API failures;
- OOM termination and incorrect GPU offload;
- stale process or listener;
- service enablement drift;
- public/private credential or ownership crossover;
- Zombie provider and manager integration failures.

Give safe, instance-specific commands and log paths. Never include a
credential, prompt, authorisation header, or unrestricted environment dump.

### Repair

Repair revalidates immutable inputs, rebuilds only a missing or corrupt
managed build, reacquires only approved missing assets, preserves valid keys
and operator selections, converges permissions and units, restores the
configured boot/load policy, and repeats health/API checks.

Repair never adopts an unmanaged installation, installs GPU drivers, changes
models or compute policy without explicit selection, or touches the other
instance.

### Uninstall

`uninstall llama` removes only the standalone service, manager, managed
builds, configuration, key, account/group where safe, component manifest,
and explicitly confirmed model/data directories.

`uninstall zombie` removes the private instance with the Zombie component.
It leaves the standalone `llama` component running and its manifest intact.
`uninstall llama` leaves Zombie and the private instance untouched.

Model deletion is destructive and requires the existing confirmation
boundary. Preserve an operator-requested verified cache only when its
ownership and later repair semantics are clear.

## Security and supply-chain requirements

- Pin source and models by immutable identifier, byte size, and SHA-256.
- Record licences and redistribution decisions before release.
- Build verified source in a root-owned staging directory.
- Do not execute CMake or model metadata from an operator-writable tree.
- Treat GGUF chat templates and similar model metadata as untrusted input.
- Do not evaluate arbitrary GGUF chat-template or model-metadata code in
  installer or manager processes.
- Require authentication even on loopback.
- Keep private and public credentials, groups, and environment forwarding
  separate.
- Redact keys from receipts, logs, diagnostics, audit, process arguments,
  and exception messages.
- Prevent user-controlled instance names, paths, unit names, and manager
  operation names from reaching shell evaluation.
- Parse JSON as data; never source generated configuration.
- Keep inference processes without login, sudo, capabilities, or writable
  runtime/model trees.
- Apply policy approval and audit logging to every agent-driven mutation.
- Never expose either listener on `0.0.0.0`, `::`, LAN, or tailnet in the
  first release.

## Test plan

Extend `tests/smoke.sh` and fixtures with no-root, no-network tests for:

- registration and dispatch of the `llama` component;
- standalone installation having no Zombie dependency;
- private selection requiring the `zombie` target;
- disabled-by-default behaviour and unchanged default Zombie dry-run;
- all option enums, bounds, required values, and exit codes;
- non-interactive explicit-selection requirements;
- fixed ports and collision rejection;
- public/private path, user, group, key, unit, and port separation;
- combined resource recommendation and rejection;
- managed ownership marker and unmanaged conflict handling;
- hardware-report parsing with CPU, NVIDIA, AMD, Intel, multiple-GPU, and
  no-GPU fixtures;
- model-catalogue and build-manifest schema rejection;
- source and model size/hash/provenance checks;
- interrupted downloads and corrupt cache handling;
- deterministic build identity and reuse;
- atomic activation and rollback;
- manager state transitions and JSON output;
- resident, sleep, on-demand, and manual semantics;
- unit hardening and GPU-device scoping;
- authenticated health, models, chat, streaming, timeout, and malformed
  endpoint fixtures;
- actual-offload mismatch reporting;
- private provider selection, manager startup, error UX, and key isolation;
- policy classification, approvals, audit records, and redaction;
- target-scoped verify, doctor, repair, and uninstall;
- packaging exclusion of source trees, models, keys, downloads, build output,
  benchmarks, and machine-local state.

Create a separate disposable-VM matrix for Ubuntu 22.04 and 24.04 on supported
architectures:

1. fresh CPU-only standalone install;
2. re-run and upgrade/rollback;
3. fresh private-only Zombie install;
4. combined public and private install;
5. public-first then private, and private-first then public;
6. every boot/load policy;
7. supported GPU backends and multi-GPU selection;
8. full and partial offload;
9. offline source/model input;
10. simulated port and unmanaged-path conflicts;
11. selective repair and uninstall in both directions;
12. non-interactive installation;
13. reboot, sleep/wake, OOM, failed-build, and failed-model-load recovery.

Do not run mutating installer or uninstaller paths in an agent environment.
The live matrix requires disposable Ubuntu Desktop LTS VMs.

## Delivery phases

### Phase 1 — contracts and asset approval

1. Finalise names, layouts, ownership markers, state schema, and fixed ports.
2. Pin and review a `llama.cpp` source commit and build matrix.
3. Approve model catalogue entries, licences, templates, and hashes.
4. Define manager JSON, health, OpenAI, and loading-policy contracts.
5. Add tiny fixtures and documentation without changing default install.

### Phase 2 — read-only detection and recommendations

1. Implement hardware, backend, capacity, port, and conflict inspection.
2. Implement catalogue-driven recommendations and combined-instance sizing.
3. Add target-scoped interactive and non-interactive selection validation.
4. Prove inspection causes no host mutation.

### Phase 3 — CPU standalone component

1. Register `llama` as an independent component.
2. Build the pinned CPU runtime and acquire approved models.
3. Add versioned activation, public credential/group, service, and manager.
4. Add lifecycle hooks, receipt, manifest, rollback, and uninstall.
5. Prove standalone operation without Zombie.

### Phase 4 — Zombie-private instance

1. Add the Zombie-owned private sub-option and isolated port-58080 layout.
2. Add the protected credential, unit, manager wrapper, and provider identity.
3. Add state/error UX, policy classification, approval, audit, and redaction.
4. Reconcile and retire duplicate improvements-4 floor-model design paths.
5. Prove coexistence and selective lifecycle isolation.

### Phase 5 — GPU backends and compute changes

1. Add separately tested CUDA, ROCm, Vulkan, and supported SYCL variants.
2. Add stable multi-GPU selection and constrained device access.
3. Add full/partial offload validation, benchmarking, and actual-offload
   reporting.
4. Add staged compute-policy changes and CPU rollback.

### Phase 6 — loading policies and release hardening

1. Validate resident and native sleep behaviour.
2. Add manager-driven on-demand startup and explicit manual mode.
3. Complete online, cache, offline, interrupted, and rollback VM matrices.
4. Run repository validation, secret scans, code review, and CodeQL.
5. Confirm packages contain no model, source cache, credential, or local
   state.

## Expected file changes

Likely new files:

```text
payload/etc/llama-builds.json
payload/etc/llama-models.json
payload/systemd/llama-server.service
payload/systemd/ubuntu-zombie-llama.service
payload/bin/llama-manager
payload/bin/zombie-llama-manager
payload/bin/llama-launch
tests/fixtures/llama/
```

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
scripts/component-registry.sh
scripts/completions/install.bash
scripts/completions/_install.sh
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
CHANGELOG.md
VERSION
```

Implementation should use the smallest actual set. Do not add parallel
helpers when an existing safe component, download, receipt, manifest, policy,
or audit helper already provides the required behaviour.

## Documentation and validation

Update user documentation only as each phase becomes real. Do not advertise
GPU backends, loading policies, or models before their complete lifecycle is
implemented and tested.

For every implementation phase:

```text
make lint
make test
make package
```

Also scan changed files for secrets, inspect package contents, run code review
and CodeQL, and use disposable VMs for live lifecycle testing.

## Acceptance criteria

1. `install llama` produces a standalone managed application on
   `127.0.0.1:8080` without installing Zombie.
2. The Zombie opt-in produces a separate authenticated instance on
   `127.0.0.1:58080`.
3. Both instances can run simultaneously without shared active paths,
   credentials, accounts, units, models, or state.
4. Neither endpoint listens beyond loopback.
5. An unprivileged unauthorised local user cannot use the private endpoint or
   read its credential/configuration.
6. Existing unmanaged llama installations are detected and left unchanged.
7. CPU capability is always available; GPU use is explicit and never installs
   or replaces a driver automatically.
8. Recommendations are shown separately from selections and overrides receive
   resource warnings.
9. Source, builds, and models use pinned immutable metadata and verified
   hashes.
10. Atomic activation and rollback preserve the last working build and
    configuration.
11. The manager reports exact service, loading, health, model, backend, and
    offload state in human and JSON forms.
12. `resident`, `sleep`, `on-demand`, and `manual` have documented and tested
    semantics.
13. Ubuntu Zombie uses the manager contract, reports failures clearly, and
    does not duplicate service-control logic.
14. Agent-driven mutations pass through policy, approval, and audit.
15. Verify, doctor, repair, upgrade, and uninstall are target-scoped,
    idempotent, non-interactive-capable, and reversible.
16. Removing Zombie leaves the standalone instance untouched; removing
    `llama` leaves the private instance untouched.
17. CI performs no real source build or model download.
18. Release packages contain no models, source cache, build output,
    credentials, or machine-local state.
19. `make lint`, `make test`, and `make package` pass.

## Maintainer decisions before implementation

Confirm these points before Phase 1:

1. Use `ZOMBIE_INSTALL_ZOMBIE_LLAMA` for the private sub-option and reserve
   `ZOMBIE_INSTALL_LLAMA` for the public component compatibility selector.
2. Treat the improvements-4 floor model as the private instance rather than
   shipping two private llama services.
3. Require authentication for the public loopback endpoint as well as the
   private endpoint.
4. Keep ports fixed at `8080` and `58080` initially.
5. Build pinned source on the target in the first release instead of
   distributing prebuilt binaries.
6. Do not install or replace GPU drivers automatically.
7. Require explicit model and compute selections in non-interactive mode.
8. Keep public and private model stores and download caches separate in the
   first release.
9. Implement only loading policies proven by the pinned runtime; do not add an
   unreviewed activation proxy.

If any decision changes, update this plan before implementation so option
names, ownership, migration, tests, and user documentation remain consistent.
