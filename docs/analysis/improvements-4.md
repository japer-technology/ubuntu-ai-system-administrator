# Zombie Floor Model

## Status

Implementation specification for Ubuntu Zombie.

Suggested repository path:

`docs/PLAN-ZOMBIE-FLOOR-MODEL.md`

The implementing agent must read these files before making changes:

* `AGENTS.md`
* `README.md`
* `docs/VISION.md`
* `docs/ARCHITECTURE.md`
* `SECURITY.md`
* `CONTRIBUTING.md`
* `options/plan-optional-localllm.md`
* `payload/agent/providers.py`
* `payload/agent/pi_mono.py`
* `payload/agent/server.py`
* `payload/agent/tools.py`
* `payload/agent/policy.py`
* `scripts/install.sh`
* `scripts/uninstall.sh`
* `scripts/component-registry.sh`
* `tests/smoke.sh`

## 1. Goal

Ubuntu Zombie must possess a guaranteed minimum level of local intelligence without requiring:

* an Internet connection after installation;
* a cloud API key;
* Ollama;
* LM Studio;
* a separately configured model server;
* a functioning external provider;
* a GPU.

This guaranteed local intelligence is called the **Zombie Floor Model**.

The Floor Model is not intended to compete with large hosted or local models. Its purpose is to ensure that Ubuntu Zombie can always:

* converse with the operator;
* explain its current state;
* inspect basic Ubuntu problems;
* interpret diagnostic output;
* select an appropriate built-in skill;
* propose safe next steps;
* explain policy and approval decisions;
* help configure or recover a more capable provider;
* continue providing limited assistance when the primary provider fails.

The product invariant is:

> An installed and living Ubuntu Zombie always has a local model available.

## 2. Product decision

The Floor Model is part of the baseline `zombie` component.

It is not:

* an optional component;
* an Ollama installation;
* a model marketplace;
* a replacement for `ZOMBIE_INSTALL_LOCALLLM`;
* a user-managed provider;
* exposed to the LAN;
* permitted to bypass the existing policy or approval system.

The existing optional local-LLM plan remains valid. Its purpose is to install an operator-managed, potentially much larger local inference stack. Such a stack may become the primary provider, but the Floor Model remains installed underneath it as the emergency minimum.

The provider hierarchy is:

```mermaid
flowchart TD
    primary["Selected primary provider"]
    primary --> cloud["OpenAI, Anthropic, Gemini, etc."]
    primary --> local["operator-managed Ollama or llama.cpp"]
    primary --> lan["operator-managed LAN model"]
    primary --> floor["Zombie Floor Model"]
    floor --> deterministic["Deterministic commands, help and lifecycle reporting"]
```

## 3. Meaning of “hardwired”

“Hardwired” does not require linking model inference directly into the Python process.

For Ubuntu Zombie it means:

1. The runtime is installed automatically with the Zombie baseline.
2. The minimum model is installed automatically.
3. Runtime and model versions are pinned by Ubuntu Zombie.
4. Model files are verified against pinned cryptographic hashes.
5. The endpoint and provider identity are known to Ubuntu Zombie.
6. No user configuration or API key is required.
7. The model remains available when the primary provider is absent.
8. The model cannot be removed through `/model` or ordinary chat commands.
9. `verify`, `doctor`, `repair` and `uninstall zombie` manage its complete lifecycle.
10. The runtime never contacts an external service during inference.

The Floor Model should run as an isolated local process rather than inside the chat process. A model crash or out-of-memory condition must not crash the chat server, policy engine or audit logger.

## 4. Core architecture

Use a pinned `llama.cpp` `llama-server` runtime.

Do not use Ollama for the hardwired floor. Ollama remains suitable for the optional operator-managed local-LLM component, but introduces a separate model manager and mutable model catalogue that the floor does not need.

Installed shape:

```text
/opt/ai-zombie/
  floor/
    bin/
      llama-server
      floor-launch
    models/
      cpu-minimum.gguf
      raised-model.gguf          # only when selected and installed
    manifest.json
    selection.json
    logs/

/etc/ubuntu-zombie/
  floor-model.env
  floor-api-key

/etc/systemd/system/
  ubuntu-zombie-floor.service
```

The inference endpoint must bind only to:

```text
127.0.0.1:11435
```

Port `11435` is deliberately separate from Ollama’s customary `11434` and LM Studio’s customary `1234`.

The endpoint must require a generated high-entropy API key stored in a root-owned file. The key must never be written to command-line arguments, logs, receipts or documentation.

The service should run as a dedicated unprivileged system user such as:

```text
zombie-floor
```

The `zombie-floor` user must have:

* no login shell;
* no password;
* no sudo rights;
* read access only to the selected model and runtime;
* write access only to its own runtime/log directory;
* GPU device-group access only when a usable GPU backend was selected.

The root-capable `zombie` account remains the agent identity. The model server itself must never hold administrative privileges.

## 5. Guaranteed CPU floor

Every supported installation must install a CPU-capable minimum model.

The minimum model must:

* use GGUF format;
* use an approved quantisation, initially Q4-class;
* run on the supported Ubuntu `amd64` CPU baseline;
* have an `arm64` variant or documented best-effort behaviour;
* require no more than a conservative amount of RAM;
* support the chat template required by the existing agent bridge;
* produce valid structured tool calls at an acceptable rate;
* permit commercial redistribution and local use;
* pass Ubuntu Zombie’s safety and capability evaluation;
* have an immutable version, URL and SHA-256 digest.

No model name is to be hard-coded into installer logic. Models are selected from a signed or repository-pinned manifest.

The initial CPU model should normally be in the approximate range of:

```text
0.5B–1.5B parameters
approximately 0.5–1.5 GB quantised
approximately 4K context
CPU-only compatible
```

These are selection guidelines, not a licence to choose an arbitrary model. The model must pass the evaluation gate described later in this plan.

## 6. Raising the floor when a GPU is available

The installer must always provision the CPU minimum first.

It may then raise the floor when it detects a **usable and validated** GPU configuration.

Merely finding a GPU in `lspci` is insufficient. A raised floor may be selected only when:

1. A supported GPU is physically present.
2. A functioning driver and userspace backend already exist.
3. The model service account can access the relevant device.
4. Total VRAM satisfies a model tier’s requirement with safety headroom.
5. System RAM and free disk satisfy that tier’s requirements.
6. The pinned GPU-enabled runtime starts successfully.
7. A local test inference succeeds.
8. The runtime confirms that layers were actually offloaded to the GPU.
9. The resulting service passes its health check.

The baseline installer must not automatically install or replace proprietary GPU drivers.

If a GPU is present but its driver is unavailable or unsuitable:

* installation continues with the CPU floor;
* `selection.json` records why the floor was not raised;
* `doctor zombie` reports the detected hardware and missing prerequisite;
* the operator may repair the driver separately;
* `repair zombie` re-evaluates the machine and may raise the floor later.

### 6.1 Two forms of raising

The floor can be raised in two ways.

#### Acceleration raise

The same minimum model runs with GPU offload.

This improves response speed without changing model capability.

#### Capability raise

A larger approved model is installed and made active.

This improves reasoning and tool-selection capability.

The CPU minimum remains installed even when a larger raised model is active. It is the final fallback if the GPU later becomes unavailable.

### 6.2 Initial tier structure

The model manifest should support at least these logical tiers:

```text
cpu-minimum
gpu-accelerated-minimum
gpu-small
gpu-medium
```

Example intent:

| Tier                      | Purpose                        | Indicative model class |
| ------------------------- | ------------------------------ | ---------------------- |
| `cpu-minimum`             | Guaranteed universal floor     | 0.5B–1.5B              |
| `gpu-accelerated-minimum` | Faster universal floor         | Same CPU model         |
| `gpu-small`               | Better reasoning on modest GPU | Approximately 3B       |
| `gpu-medium`              | Stronger local floor           | Approximately 7B–8B    |

The exact VRAM, RAM and disk requirements must live in the manifest, not as scattered shell conditionals.

The first implementation should cap automatic model selection at `gpu-medium`. Larger models belong to the optional local-LLM component rather than the guaranteed floor.

### 6.3 Resource safety

A raised floor must not consume nearly all available VRAM.

Each manifest entry must specify:

* estimated model RAM;
* estimated VRAM;
* minimum system RAM;
* minimum total VRAM;
* minimum free disk;
* maximum permitted fraction of total VRAM;
* supported accelerator backends;
* supported architectures.

Selection must reserve sufficient GPU resources for the Ubuntu desktop and other applications.

A candidate must be rejected when either of these is true:

```text
estimated_vram > configured maximum fraction of total VRAM
estimated_vram + safety reserve > total VRAM
```

The manifest, rather than installer source code, owns the numeric thresholds.

## 7. Hardware detection

Create one hardware-detection function with machine-readable output.

It must report:

```json
{
  "cpu_arch": "amd64",
  "cpu_threads": 16,
  "ram_mib": 32768,
  "free_disk_mib": 120000,
  "gpu_present": true,
  "gpu_vendor": "nvidia",
  "gpu_model": "example",
  "gpu_vram_mib": 12288,
  "backend": "cuda",
  "backend_usable": true,
  "reason": "validated"
}
```

Detection should use available host tools and device files, with guarded fallbacks.

Potential signals include:

* `lspci`;
* `nvidia-smi`;
* `/dev/nvidia*`;
* `/dev/kfd`;
* `/dev/dri/renderD*`;
* `rocminfo`, when already installed;
* Vulkan capability, when the pinned runtime supports it;
* a short `llama.cpp` backend probe.

Do not add a mandatory dependency merely to identify hardware when equivalent information is already available from `/proc`, `/sys`, PCI information or the runtime probe.

Detection results must contain no serial numbers or other unnecessary hardware identifiers.

## 8. Model manifest

Add:

```text
payload/etc/floor-models.json
```

Suggested schema:

```json
{
  "schema_version": 1,
  "runtime": {
    "version": "PINNED_VERSION",
    "assets": {
      "linux-amd64-cpu": {
        "url": "IMMUTABLE_URL",
        "sha256": "PINNED_SHA256"
      },
      "linux-amd64-cuda": {
        "url": "IMMUTABLE_URL",
        "sha256": "PINNED_SHA256"
      }
    }
  },
  "tiers": [
    {
      "id": "cpu-minimum",
      "mandatory": true,
      "model_id": "zombie-floor-cpu-v1",
      "filename": "zombie-floor-cpu-v1.gguf",
      "url": "IMMUTABLE_URL",
      "sha256": "PINNED_SHA256",
      "size_bytes": 0,
      "licence": "APPROVED_LICENCE",
      "context_tokens": 4096,
      "architectures": ["amd64", "arm64"],
      "backends": ["cpu"],
      "minimum_ram_mib": 0,
      "minimum_disk_mib": 0,
      "estimated_ram_mib": 0
    },
    {
      "id": "gpu-small",
      "mandatory": false,
      "model_id": "zombie-floor-gpu-small-v1",
      "filename": "zombie-floor-gpu-small-v1.gguf",
      "url": "IMMUTABLE_URL",
      "sha256": "PINNED_SHA256",
      "size_bytes": 0,
      "licence": "APPROVED_LICENCE",
      "context_tokens": 8192,
      "architectures": ["amd64"],
      "backends": ["cuda", "rocm", "vulkan"],
      "minimum_ram_mib": 0,
      "minimum_vram_mib": 0,
      "minimum_disk_mib": 0,
      "estimated_ram_mib": 0,
      "estimated_vram_mib": 0,
      "maximum_vram_fraction": 0.0
    }
  ]
}
```

Replace all placeholders only after the model and runtime assets have passed review.

The installer must reject:

* an unknown schema version;
* duplicate tier IDs;
* mutable or unapproved URLs;
* missing checksums;
* unsupported architecture/backend combinations;
* a selected model whose hash does not match;
* a model not present in the curated manifest.

The installer must never accept an arbitrary model name from this manifest path.

## 9. Installer behaviour

The normal baseline installation sequence becomes:

```mermaid
flowchart TD
    baseline["Install Zombie baseline"] --> runtime["install chat, agent, policy and audit runtime"]
    runtime --> hw["detect hardware"]
    hw --> cpu_runtime["install pinned CPU llama.cpp runtime"]
    cpu_runtime --> cpu_model["install and verify CPU minimum model"]
    cpu_model --> cpu_floor["configure CPU floor"]
    cpu_floor --> gpu["probe usable GPU backends"]
    gpu --> tier["select highest safe approved tier"]
    tier --> raised["optionally install raised runtime/model"]
    raised --> test["perform local test inference"]
    test --> activate["activate raised tier or retain CPU tier"]
    activate --> start["start floor service"]
    start --> verify["verify provider routing"]
```

### 9.1 Public configuration

Keep configuration deliberately small:

```text
ZOMBIE_FLOOR_PROFILE=auto|cpu
ZOMBIE_FLOOR_MAX_TIER=cpu-minimum|gpu-small|gpu-medium
ZOMBIE_FLOOR_ASSET_DIR=/path/to/offline/assets
ZOMBIE_FLOOR_PORT=11435
```

Defaults:

```text
ZOMBIE_FLOOR_PROFILE=auto
ZOMBIE_FLOOR_MAX_TIER=gpu-medium
ZOMBIE_FLOOR_PORT=11435
```

There should be no ordinary `ZOMBIE_INSTALL_FLOOR=0` option. The Floor Model is part of the product baseline.

A test-only mechanism may suppress downloads during CI dry runs, but it must be clearly internal and must not silently create an installation that claims to have a functioning floor.

### 9.2 Air-gapped installation

`ZOMBIE_FLOOR_ASSET_DIR` allows an operator to supply all pinned assets locally.

The installer must still verify every asset against the repository manifest.

The offline directory does not permit arbitrary model substitution.

### 9.3 Idempotence

On re-run, the installer must:

* reuse valid runtime binaries;
* reuse models whose hashes match;
* replace corrupt or wrong-version assets;
* preserve a valid generated API key;
* re-evaluate hardware;
* raise or lower the selected tier safely;
* restart the floor service only when required;
* never duplicate users, groups, files or units.

## 10. Provider integration

Add a first-class internal provider identity:

```text
floor
```

Do not continue calling all local providers `lmstudio`.

The existing `lmstudio` provider remains for backwards compatibility and operator-managed OpenAI-compatible servers.

The Floor Model must use the existing pi-mono/pi-ai agent loop. Do not implement a second independent agent loop.

The provider system must distinguish:

```text
primary provider
fallback floor provider
```

`ZOMBIE_PROVIDER` and `ZOMBIE_MODEL` continue to select the primary provider.

Floor configuration is read from root-owned generated configuration, not from ordinary user provider variables.

Suggested generated state:

```text
ZOMBIE_FLOOR_PROVIDER=floor
ZOMBIE_FLOOR_MODEL=zombie-floor-gpu-small-v1
ZOMBIE_FLOOR_BASE_URL=http://127.0.0.1:11435/v1
```

The base URL and API key must be passed to the bridge without exposing them to unrelated providers.

## 11. Fallback routing

Use the Floor Model when:

* no primary provider is configured;
* the configured provider key is missing;
* the primary provider cannot be resolved;
* DNS or Internet connectivity is unavailable;
* the provider rejects authentication;
* the provider is rate-limited;
* the provider times out before producing output;
* the primary local model service is unavailable;
* the operator explicitly selects floor operation.

### 11.1 Replay safety

Automatic fallback must occur only before the primary turn has:

* emitted meaningful assistant output;
* requested a tool;
* started a tool;
* produced an approval request;
* caused any state mutation.

Never automatically replay a prompt through the Floor Model after tool activity has begun. Doing so could duplicate an administrative operation.

When failure occurs after tool activity, the UI must:

* preserve the existing history and audit records;
* report the provider failure;
* state that automatic replay was suppressed;
* allow the operator to begin a new Floor Model turn.

### 11.2 No fallback loop

The Floor Model never falls back to itself.

If the floor is unavailable, the deterministic chat layer must still display:

* floor service status;
* lifecycle status;
* relevant log paths;
* `verify`, `doctor` and `repair` commands.

## 12. Floor capability profile

A very small model must not receive unrestricted administrative freedom merely because a larger provider failed.

Add a model capability profile that intersects with the existing policy result.

Initial Floor Model permissions:

| Action                            | Floor behaviour                                   |
| --------------------------------- | ------------------------------------------------- |
| Read-only inspection              | Permitted through normal policy                   |
| Explanation and summarisation     | Permitted                                         |
| Skill selection                   | Permitted                                         |
| User-owned changes                | Approval required                                 |
| System changes                    | Only through curated skills and explicit approval |
| Network changes                   | Disabled in the first release                     |
| Destructive actions               | Disabled in the first release                     |
| Arbitrary mutating shell commands | Disabled                                          |

The effective decision must be the more restrictive result of:

```text
existing action policy
AND
active provider capability profile
```

The Floor Model may use deterministic Ubuntu Zombie skills for operations such as:

* reading package state;
* reading service state;
* gathering network status;
* explaining logs;
* preparing an `apt` repair plan;
* preparing a `systemd` repair plan.

Any approved mutation must still travel through the existing policy gate and audit log.

The Floor Model must never edit its own:

* runtime;
* model files;
* manifest;
* API key;
* systemd unit;
* capability profile.

Those operations belong to `install`, `repair` and `uninstall`, not conversational model autonomy.

## 13. Systemd service

Add:

```text
payload/systemd/ubuntu-zombie-floor.service
```

Required properties:

* starts after local filesystems;
* starts before or alongside the chat service;
* binds only to loopback;
* runs as `zombie-floor`;
* restarts on failure with bounded restart behaviour;
* has no privilege escalation;
* has a read-only system view;
* has a private temporary directory;
* may write only to its assigned state/log directory;
* has no outbound network access other than loopback;
* receives GPU device access only when required;
* has memory and process limits appropriate to the selected tier;
* does not place secrets in `ExecStart`;
* reads secrets from a protected environment/credentials file.

The chat service should not fail permanently merely because the Floor Model takes longer to start. It should expose a clear “floor starting” state and retry within a bounded period.

## 14. Runtime selection and automatic degradation

Create a `floor-launch` wrapper.

At service start it must:

1. Read `selection.json`.
2. Validate the selected runtime and model hashes.
3. Check that the selected GPU backend remains usable.
4. Attempt the raised configuration.
5. Fall back to the CPU runtime/model when raised startup fails.
6. Record the actual active tier and reason.
7. Never download assets during service startup.
8. Exit non-zero only when even the CPU floor cannot start.

This handles cases such as:

* a kernel update breaks the NVIDIA module;
* an external GPU is disconnected;
* ROCm stops recognising the card;
* GPU device permissions drift;
* the raised model becomes corrupt;
* insufficient VRAM is available.

`repair zombie` may later restore the raised tier.

## 15. User interface

The chat UI must show two separate concepts:

```text
Primary: Anthropic / Claude …
Floor: Raised — GPU small
```

or:

```text
Primary: unavailable
Operating on: Zombie Floor — CPU minimum
Reason: provider authentication failed
```

Add commands or extend existing model commands to support:

```text
/floor
/floor status
/floor test
/model primary
```

Exact command naming should follow the current command parser conventions.

`/floor status` should report:

* installed CPU tier;
* selected raised tier;
* active tier;
* runtime version;
* model ID and digest prefix;
* CPU/GPU backend;
* floor health;
* why the floor was or was not raised;
* primary-provider status;
* no secrets.

## 16. Audit and history

Every turn must record:

```text
provider_role: primary | floor
provider_name
model_id
model_digest_prefix
floor_tier
floor_backend
fallback_reason
fallback_stage
automatic_fallback: true | false
```

Hardware detection and tier changes must be audit-logged without unnecessary hardware identifiers.

Examples:

```text
floor_selected: cpu-minimum
reason: no usable GPU backend
```

```text
floor_selected: gpu-small
reason: CUDA backend validated; test inference passed
```

```text
floor_degraded: cpu-minimum
reason: raised runtime failed after kernel update
```

Secret redaction must cover the floor API key.

## 17. Verify, doctor, repair and uninstall

### 17.1 Verify

`verify zombie` must check:

* floor user and permissions;
* runtime presence and version;
* manifest validity;
* CPU model presence and checksum;
* raised model checksum, when installed;
* generated API-key file permissions;
* systemd unit state;
* loopback-only listening address;
* endpoint authentication;
* `/v1/models`;
* short inference health request;
* active tier;
* selected hardware backend;
* chat-to-floor routing;
* no external listener.

### 17.2 Doctor

`doctor zombie` must explain:

* missing or corrupt model;
* runtime/version mismatch;
* failed checksum;
* port conflict;
* service crash;
* out-of-memory condition;
* GPU detected but unusable;
* missing GPU driver;
* broken GPU backend after a kernel update;
* incorrect device permissions;
* raised tier rejected due to RAM, disk or VRAM;
* primary-provider failure and floor fallback state.

### 17.3 Repair

`repair zombie` may:

* restore runtime files;
* restore model files from approved assets;
* regenerate missing service configuration;
* restore ownership and permissions;
* regenerate a missing API key;
* re-run hardware detection;
* retest GPU acceleration;
* raise or lower the selected tier;
* restart and verify the service.

It must not install proprietary GPU drivers automatically.

### 17.4 Uninstall

`uninstall zombie` must remove:

* floor service and unit;
* floor runtime;
* all floor models;
* generated floor API key;
* generated configuration;
* floor state;
* dedicated service account, where safe;
* associated group membership;
* manifest/receipt state.

Selective `uninstall forgejo` must leave the Floor Model untouched.

## 18. Supply-chain and security requirements

Runtime and model assets must use:

* immutable versioned URLs;
* pinned SHA-256 hashes;
* documented upstream provenance;
* approved redistribution licences;
* release-time malware and secret scanning;
* reproducible model metadata where practical.

Do not use:

* mutable `latest` assets;
* arbitrary Hugging Face branch URLs;
* `ollama pull <mutable-tag>`;
* an operator-provided unverified model;
* a model catalogue discovered from the Internet;
* runtime downloads during ordinary inference.

The floor service must not have general Internet access.

The model is untrusted input-processing code. All of its proposed tool calls remain subject to:

* schema validation;
* capability restrictions;
* policy classification;
* operator approval;
* audit logging.

## 19. Model evaluation gate

Do not select a production Floor Model solely because it is small.

Add an evaluation set covering:

* recognising common Ubuntu faults;
* selecting the appropriate read-only tool;
* interpreting `systemctl` output;
* interpreting `apt` and `dpkg` output;
* distinguishing DNS, route and interface problems;
* asking for missing information;
* refusing unsupported destructive work;
* avoiding invented command output;
* respecting approval boundaries;
* producing valid tool-call JSON;
* explaining provider configuration failures;
* recovering from malformed or truncated tool results;
* concise responses on CPU.

A model must meet explicit thresholds before entering the manifest.

Suggested initial thresholds:

* at least 95% syntactically valid tool calls;
* no unauthorised destructive execution in the safety set;
* at least 90% correct selection among built-in diagnostic tools;
* acceptable completion latency on the reference i7 CPU;
* no network dependency;
* deterministic enough for repeatable smoke evaluation at low temperature.

The normal CI suite must not download multi-gigabyte model assets.

Use:

* mocked hardware detection;
* mocked model endpoints;
* manifest-validation tests;
* routing tests;
* policy-profile tests;
* systemd-unit static checks;
* dry-run tests.

Run real-model evaluations in a separate nightly or release-validation workflow.

## 20. Purpose-built Zombie model

The first implementation may use an approved general instruct model if it passes the evaluation gate.

The longer-term target is a purpose-built model artifact named along the lines of:

```text
Zombie Floor Model v1
```

Its training or fine-tuning data should emphasise:

* inspect before changing;
* use tools rather than inventing state;
* choose the narrowest relevant skill;
* explain commands before execution;
* recognise action classes;
* request approval correctly;
* never claim a command succeeded without its result;
* stop when evidence is insufficient;
* help restore a stronger provider;
* concise Ubuntu systems-administration language.

No private operator conversations, secrets or unsanitised production logs may enter training data.

The training pipeline may live in a separate repository. The Ubuntu Zombie repository consumes only an approved, versioned GGUF release and its metadata.

## 21. Implementation sequence

### Phase 1 — Contract and tests

1. Add this plan and update `ROADMAP.md`.
2. Define the manifest schema.
3. Add manifest parser and validation tests.
4. Add mocked hardware profiles.
5. Add routing and capability-profile tests.
6. Add model evaluation fixtures.
7. Do not yet change default installation behaviour.

### Phase 2 — CPU minimum

1. Select and approve the CPU model.
2. Pin the CPU runtime and model assets.
3. Add the `zombie-floor` account.
4. Install runtime, model, API key and systemd unit.
5. Add the `floor` provider.
6. Route no-provider installations to the Floor Model.
7. Add verify/doctor/repair/uninstall support.
8. Prove idempotent install and reinstall.

### Phase 3 — Primary-provider fallback

1. Separate primary-provider state from floor state.
2. Add pre-output automatic fallback.
3. Add replay-safety guards.
4. Add UI status.
5. Add audit fields.
6. Test authentication, timeout, DNS and local-provider failures.

### Phase 4 — GPU acceleration

1. Implement hardware detection.
2. Add pinned GPU runtime variants.
3. Validate actual offload.
4. Accelerate the CPU minimum when safe.
5. Add automatic degradation to CPU.

### Phase 5 — Raised capability tiers

1. Evaluate larger candidate models.
2. Add approved `gpu-small` tier.
3. Add approved `gpu-medium` tier.
4. Implement resource-headroom selection.
5. Preserve the CPU model as permanent fallback.
6. Add `repair`-time re-evaluation.

### Phase 6 — Release hardening

1. Add real-machine CPU release tests.
2. Add available NVIDIA/AMD/Intel backend tests.
3. Add air-gapped installation validation.
4. Confirm package and release asset checksums.
5. Update all user documentation.
6. Add `CHANGELOG.md` entry.
7. Bump `VERSION`.
8. Run `make lint`, `make test` and `make package`.

## 22. Expected file changes

Likely new files:

```text
docs/PLAN-ZOMBIE-FLOOR-MODEL.md
payload/etc/floor-models.json
payload/systemd/ubuntu-zombie-floor.service
payload/bin/floor-launch
payload/bin/floor-model-health
payload/agent/floor.py
tests/floor/
```

Likely modified files:

```text
ROADMAP.md
README.md
docs/ARCHITECTURE.md
docs/CONFIGURATION.md
docs/PLATFORMS.md
SECURITY.md
CONTRIBUTING.md
scripts/install.sh
scripts/uninstall.sh
payload/agent/providers.py
payload/agent/pi_mono.py
payload/agent/server.py
payload/agent/tools.py
payload/agent/policy.py
payload/agent/audit.py
payload/etc/policy.yaml
payload/bin/verify
tests/smoke.sh
CHANGELOG.md
VERSION
```

The implementing agent must inspect the current component registry before editing. The Floor Model must be integrated into the existing `zombie` component hook rather than registered as a new optional public component.

## 23. Acceptance criteria

The implementation is complete only when all of these pass:

1. A fresh CPU-only supported Ubuntu installation has a working Floor Model.
2. No cloud provider key is required.
3. The machine can be disconnected after installation and still converse.
4. The floor endpoint is loopback-only and authenticated.
5. The model process has no sudo rights.
6. Primary providers continue to work unchanged.
7. A missing primary provider automatically selects the floor.
8. A pre-output provider failure safely falls back.
9. A failure after tool activity is not automatically replayed.
10. TTL expiration disables Floor Model chat access along with the rest of Zombie.
11. A usable GPU raises or accelerates the floor when all checks pass.
12. A merely detected but unusable GPU does not break installation.
13. A broken GPU configuration degrades to the retained CPU model.
14. `doctor` explains why the floor was not raised.
15. `repair` can raise the floor after GPU support is restored.
16. The CPU model and all raised models have verified hashes.
17. Re-running install is idempotent.
18. Non-interactive installation works.
19. Air-gapped installation works with pre-supplied approved assets.
20. Uninstall removes all Floor Model resources.
21. All model-driven actions remain policy-gated and audited.
22. `make lint`, `make test` and `make package` pass.

## 24. Explicit non-goals

The first release does not:

* install or update proprietary GPU drivers;
* expose the floor endpoint beyond loopback;
* provide arbitrary model downloads;
* replace the optional local-LLM component;
* make destructive actions available to the Floor Model;
* make network changes available to the Floor Model;
* train a model during Ubuntu Zombie installation;
* support fleet-wide model distribution;
* use the Floor Model as an autonomous root process;
* guarantee large-model quality from a sub-billion-parameter model.

## 25. Final design statement

The Zombie Floor Model gives Ubuntu Zombie a permanent lowest level of intelligence.

Every installation receives a small CPU-capable local model. When installation detects a functioning GPU and sufficient resources, it may safely raise that floor with acceleration or a larger approved model. The CPU minimum remains installed underneath it.

Cloud and operator-managed models provide greater intelligence, but they are enhancements rather than prerequisites.

Ubuntu Zombie therefore always wakes up with a brain of its own.
