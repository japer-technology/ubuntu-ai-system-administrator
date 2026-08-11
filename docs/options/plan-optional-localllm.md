# Plan: optional local LLM serving — install and manage the model runtime (`Ollama` / `llama.cpp` + optional GPU)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that installs and
manages a single-host **local LLM serving** stack — an
OpenAI-compatible model runtime (`Ollama` by default, `llama.cpp` as an
alternative), a curated set of pulled models, and *optional* GPU driver
+ runtime enablement — all bound to loopback/the tailnet. This is the
worked-out promotion of candidate **F** ("Local LLM serving",
`ZOMBIE_INSTALL_LOCALLLM`, ★) from [`brainstorm.md`](brainstorm.md).

The codebase **already** *discovers* a running local LLM and wires it up
as the `lmstudio` provider (see `discover_local_llms` in
`scripts/install.sh`, the `lmstudio` spec in
[`payload/agent/providers.py`](../payload/agent/providers.py), and
`pi-ai-bridge.mjs`). This plan is the complementary half: rather than
only *finding* a server someone else started, the installer can *stand
one up and keep it healthy*, then point the existing provider plumbing
at it so the agent can run on a model it also maintains.

The capability follows the same shape as the existing optional
components (Tailscale, the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md),
and the observability stack in
[`plan-optional-observability.md`](plan-optional-observability.md)): off
by default, toggled by an environment variable, surfaced in the
interactive parameter review, honoured in the dry-run plan, recorded in
the receipt, idempotent on re-run, gated through the policy/audit model,
verifiable by `verify`/`doctor`/`repair`, and reversible by
`uninstall.sh`.

## Why AI assistance is the unlock

Pulling a model is a one-line command; *operating* a local inference
host on desktop Ubuntu is the day-2 burden the brainstorm's thesis names
directly. The pain is almost never conceptual — it is the proprietary
**GPU driver and kernel-module** dance (the single most fragile area on
desktop Ubuntu), matching a CUDA/ROCm runtime to the installed driver,
right-sizing a model to available VRAM, diagnosing an out-of-memory or a
silently CPU-only fallback, and reclaiming disk when a model zoo grows
without bound. A resident administrator that can **read its own serving
metrics and logs**, explain "why is generation slow / why did the GPU
disappear after a kernel update?" with evidence, snapshot before a
risky driver change, and roll back if `verify` regresses, collapses
exactly that operating cost — through the policy gate and audit log. It
also dovetails with the existing provider plumbing, so a privacy-first
operator can run the agent entirely on owned hardware with no hosted key.

## Design principle: a curated runtime, not a model marketplace

The brainstorm's risk note for this candidate is explicit: proprietary
GPU drivers and kernel modules are the most fragile area on desktop
Ubuntu; treat driver changes as a high-risk `system_change`, snapshot
first, and keep CPU-only the safe default. This plan honours that by
enumerating a small, fixed runtime and making every escalation an
explicit, reversible opt-in:

- **Runtime:** one **OpenAI-compatible** server — `Ollama` by default
  (single binary, manages model storage and an `/v1` endpoint),
  `llama.cpp`'s `llama-server` as an alternative — run as an
  unprivileged system service bound to loopback.
- **Models:** a **curated, enumerated** manifest of models to pull
  (never an open-ended "install anything" fetch), with conservative disk
  and retention defaults.
- **Acceleration:** **CPU-only by default.** GPU enablement (NVIDIA
  proprietary driver + CUDA runtime, or AMD ROCm) is a separate sub-flag
  that is *never* on implicitly, is classified as a high-risk
  `system_change`, and is guarded behind a filesystem snapshot when the
  snapshots component ([`plan-optional-snapshots.md`](plan-optional-snapshots.md))
  is present.

The runtime binary and models are **operator-installed by the installer**
from apt or pinned upstream single-binary releases when the option is
on; no external control plane is contacted at runtime, and model pulls
go only to the operator-nominated registry.

## Integration with the existing provider plumbing

This component is the **producer** the existing `lmstudio` provider
**consumes**. To avoid a second source of truth (see the model-selection
invariant the codebase already enforces), the installer reuses the
discovery wiring rather than re-implementing it:

- After standing up the runtime, set the local endpoint
  (`http://127.0.0.1:${LOCALLLM_HTTP_PORT}/v1`) and the chosen default
  model into the same `LOCAL_LLM_*` variables `discover_local_llms`
  populates, so the existing code writes `ZOMBIE_PROVIDER=lmstudio`,
  `ZOMBIE_MODEL`, and `LMSTUDIO_API_KEY` to the secrets/env file and the
  `baseUrl` into `${AGENT_HOME}/.pi/agent/models.json` exactly as today.
- The chat `/model` command already lists local-provider models live
  from `GET {baseUrl}/v1/models`; a server this component manages simply
  makes that listing reflect the locally pulled set. No bridge changes
  are required beyond confirming the endpoint shape matches.
- When both *discovery* and *serving* are enabled, the locally served
  endpoint is preferred over a scanned one, and that precedence is
  documented so the two paths never fight.

## What "maximum" means

The **minimum** viable local serving is: the CPU-only runtime installed
and enabled on loopback, **one** small curated model pulled, the
`lmstudio` provider pointed at it, and a `verify` check that the
endpoint answers and the model is loadable. A **maximum** role rounds
that out, each piece an independently overridable sub-flag under a
`ZOMBIE_LOCALLLM_PROFILE=minimum|maximum` meta-flag (mirroring the
Forgejo, backup, and observability plans' profile flag):

- **GPU acceleration** — `ZOMBIE_LOCALLLM_GPU`. Detect the GPU vendor and
  enable the NVIDIA proprietary driver + CUDA runtime (or AMD ROCm) so
  the runtime offloads layers to VRAM. Off in `minimum` (CPU-only), and
  even in `maximum` it is gated behind explicit consent and a snapshot,
  because it is the plan's sharpest risk.
- **Extended model set** — `ZOMBIE_LOCALLLM_MODELS`. Pull the fuller
  curated manifest (e.g. a chat model plus an embedding/code model)
  instead of the single minimum model, still strictly enumerated.
- **Great web front door** — `ZOMBIE_LOCALLLM_WEB`. A `Caddy`
  reverse-proxy with automatic HTTPS exposing the `/v1` endpoint on the
  tailnet only (loopback when Tailscale is off), reusing the Caddy seam
  the observability and Forgejo plans define. Off in `minimum`
  (loopback-only, for `ssh -L` / the local agent). When the host-wide
  reverse-proxy candidate (`ZOMBIE_INSTALL_PROXY`) is promoted, defer the
  front door to it rather than running a second Caddy — document that
  seam.
- **Retention/disk hardening** — a conservative model-cache budget and a
  `doctor` disk-pressure check so the model store never grows without
  bound.

The maximum profile is therefore the minimum **plus** opt-in GPU
acceleration, the extended model manifest, and the tailnet-bound web
front door, reusing the same unit-and-config shape.

## A great web server (the endpoint front door)

When `ZOMBIE_LOCALLLM_WEB=1`, the runtime is fronted by **Caddy**,
consistent with the observability plan's web tier and the Forgejo plan's
Caddy component:

- **Tailnet-bound by default.** The runtime binds to `127.0.0.1`; Caddy
  listens only on `tailscale0` (loopback when Tailscale is off) and
  reverse-proxies `LOCALLLM_DOMAIN` → `127.0.0.1:${LOCALLLM_HTTP_PORT}`
  with automatic HTTPS, HTTP/2/3, and sane security headers.
- **HTTPS by design.** With a `LOCALLLM_DOMAIN` on the tailnet, Caddy
  obtains/renews a certificate (`tailscale cert` or an operator-supplied
  internal CA); otherwise it serves Caddy's built-in internal CA
  (`tls internal`), documenting the one-time trust step. The endpoint is
  never served plaintext on a routable interface, and `80`/`443` are
  restricted to `tailscale0` by UFW.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_LOCALLLM=0|1` — master switch (default `0`). When `1`,
  install and configure the local serving stack.
- `ZOMBIE_LOCALLLM_PROFILE=minimum|maximum` — switches the GPU/models/web
  sub-flags on together (default `minimum`); each remains independently
  overridable.
- `ZOMBIE_LOCALLLM_RUNTIME=ollama|llamacpp` — which runtime to install
  (default `ollama`), validated as an enum.
- `ZOMBIE_LOCALLLM_GPU=0|1|auto` — GPU acceleration (default `0`).
  `auto` enables it only when a supported GPU **and** a clean snapshot
  path are detected; `1` forces it (still snapshot-gated). High-risk
  `system_change`.
- `ZOMBIE_LOCALLLM_MODELS=0|1` — pull the extended curated manifest
  instead of just the minimum model (default follows the profile). The
  manifest of permitted model names lives in
  [`payload/etc/`](../payload/etc/), not in env, to keep it curated.
- `ZOMBIE_LOCALLLM_DEFAULT_MODEL` — the model to pull first and set as
  the agent's `ZOMBIE_MODEL` (sensible small default, validated against
  the manifest).
- `ZOMBIE_LOCALLLM_WEB=0|1` — enable the Caddy + HTTPS front door
  (default follows the profile).
- `LOCALLLM_DOMAIN` — the tailnet hostname Caddy serves the endpoint on
  when the web front door is enabled. Required only when
  `ZOMBIE_LOCALLLM_WEB=1`; absent, Caddy serves a Caddy-internal cert on
  the tailnet address.
- `LOCALLLM_HTTP_PORT` — loopback bind port for the runtime (sensible
  default, e.g. `11434` for Ollama), validated as a free integer port.
- `ZOMBIE_LOCALLLM_MODEL_DIR` — model-store path (default under the
  workspace/data dir), and `ZOMBIE_LOCALLLM_CACHE_BUDGET` — a
  conservative disk budget for the store.
- `LOCALLLM_API_KEY` — token the runtime/Caddy require for the `/v1`
  endpoint. If unset, the installer **generates** one and stores it
  root-only, reusing the existing `LMSTUDIO_API_KEY` plumbing; if set, it
  is used and stored the same way. Never printed or committed; surfaced
  in the receipt as a set/unset fingerprint only.
- `OLLAMA_VERSION` / `LLAMACPP_VERSION` / `CADDY_VERSION` — optional
  pins; defaults resolve the distribution package or the upstream
  release, recording the resolved value in the receipt (mirroring how
  `FORGEJO_VERSION` and the Node bridge pins are handled).

Generated secrets (`LOCALLLM_API_KEY` when auto-generated) are created at
install time and **never** committed or printed into the repo. They are
written only to root-owned files on the target host (e.g.
`/etc/ubuntu-zombie/localllm.env`, mode `600`, owner `root:root`, and the
existing agent secrets file for `LMSTUDIO_API_KEY`) and surfaced via the
receipt as set/unset fingerprints — not plaintext. Confirm the CI
secret-scan patterns (`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not
tripped; do not add example secrets to docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: package/binary
   presence (`ollama --version` / `llama-server --version`,
   `caddy version`, `nvidia-smi`/`rocminfo` for GPU), the env/config
   files, the systemd units, and whether each model is already pulled
   (never re-pull a present model). Re-running converges with no errors
   and no duplicate units or model fetches.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone. When `ZOMBIE_LOCALLLM_WEB=1` and
   `LOCALLLM_DOMAIN` is missing in non-interactive mode, exit `64`,
   consistent with `validate_noninteractive()`. When local serving is
   off, requirements are unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the
   gate. The runtime runs as a system service without the agent, but
   anything the chat agent may later be asked to drive — pulling/removing
   a model, restarting the runtime, reloading Caddy, and especially
   **enabling/changing a GPU driver** — must be classified in
   `payload/etc/policy.yaml` `sudo_allow_list` and described in
   `docs/ARCHITECTURE.md`. Model pulls and service restarts are a
   `system_change` class; GPU driver/kernel-module changes are the
   **highest-risk** `system_change` and must require explicit
   confirmation.
4. **No new runtime deps beyond what the installer installs.** The
   runtime, Caddy, and any GPU driver/runtime are apt packages (or pinned
   single-binary releases) installed by the installer **only when the
   option is on**, which is permitted; do not add language-level
   dependencies. Reuse existing `curl_get`/retry and architecture-mapping
   helpers if fetching a binary release.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "behaviour", "optimise", "minimise",
   "initialise").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_LOCALLLM`, the `ZOMBIE_LOCALLLM_*`,
  `LOCALLLM_HTTP_PORT`, `LOCALLLM_DOMAIN`, `LOCALLLM_API_KEY`, and the
  `*_VERSION` variables to the defaults/derivation block alongside the
  other `ZOMBIE_*` settings, with conservative defaults (`0`, profile
  `minimum`, runtime `ollama`, GPU `0`, the documented port and cache
  budget).
- Add validators (port free/integer check, the runtime and GPU enum
  checks, default-model-in-manifest check, cache-budget sanity, and the
  "`LOCALLLM_DOMAIN` required when web front door enabled" rule) and wire
  them into `validate_config()` so an invalid value is rejected before
  any host change.
- Extend `validate_noninteractive()` to exit `64` when the web front door
  is enabled but `LOCALLLM_DOMAIN` is missing.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in local-serving example (interactive and
  `ZOMBIE_NONINTERACTIVE=1`), noting the CPU-only default and the
  GPU-is-high-risk caveat.

### 2. Interactive parameter review

- Add a "Local LLM serving" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, the profile, runtime, default
  model, GPU on/off, and the endpoint/domain (host only — never the API
  key). Mirror how Tailscale, Forgejo, and the existing discovered
  "Local LLM" row render.
- Add a `_toggle_localllm()` editor (and nested profile/runtime/model/
  GPU/web/domain editors) and a new menu entry in `review_parameters()`.
  Append as the next index to minimise churn, and update the range hint
  and the "Unrecognised choice" message accordingly. Make the GPU toggle
  print an explicit high-risk warning before enabling.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary block so that,
  when local serving is enabled, the plan lists the runtime install,
  model-pull, unit, and (for `maximum`) the GPU-driver and Caddy steps,
  and when disabled it says nothing — keeping the default output
  unchanged. The GPU step must be clearly flagged as a high-risk driver
  change.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_LOCALLLM != 1`. Place them after the workspace/data and
(if present) Tailscale and snapshots sections so the data dir, the bind
interface, and a pre-change snapshot path already exist:

- `section "Snapshot before GPU change"` *(GPU only)* — when GPU
  acceleration is requested and the snapshots component is present, take
  a labelled snapshot first (reusing
  [`plan-optional-snapshots.md`](plan-optional-snapshots.md)); when it is
  absent, require explicit confirmation and warn that rollback is manual.
- `section "Enable GPU acceleration"` *(GPU only)* — detect the GPU
  vendor, install the NVIDIA proprietary driver + CUDA runtime (via
  `ubuntu-drivers`/apt) or AMD ROCm, guarded by a `nvidia-smi`/`rocminfo`
  probe so a working setup is never reinstalled. Treat as the highest-
  risk `system_change`.
- `section "Install local LLM runtime"` — `apt_install` or fetch and
  `install -m 0755` the pinned arch-matched runtime binary (Ollama or
  `llama.cpp`), guarded by a version probe; create
  `/etc/ubuntu-zombie/localllm.env` (mode `600`, `root:root`) and
  generate/reuse `LOCALLLM_API_KEY`. Bind the runtime to
  `127.0.0.1:${LOCALLLM_HTTP_PORT}` and the model store to
  `ZOMBIE_LOCALLLM_MODEL_DIR`.
- `section "Pull curated models"` — pull the default model (and, for the
  extended set, the rest of the curated manifest), each guarded so a
  model already present is skipped. Never pull anything outside the
  enumerated manifest.
- `section "Enable local LLM service"` — install and `enable --now` the
  runtime unit via the existing `render_unit()` pattern; `daemon-reload`
  once.
- `section "Point agent at local model"` — set the `LOCAL_LLM_*`
  variables to the served endpoint and default model and reuse the
  existing discovery code path that writes `ZOMBIE_PROVIDER=lmstudio`,
  `ZOMBIE_MODEL`, `LMSTUDIO_API_KEY`, and the `models.json` `baseUrl`.
  Prefer the served endpoint over any scanned one.
- `section "Local LLM web server"` *(web front door only)* — render a
  minimal `Caddyfile` reverse-proxying `LOCALLLM_DOMAIN` →
  `127.0.0.1:${LOCALLLM_HTTP_PORT}` with automatic HTTPS and security
  headers, bind Caddy to `tailscale0` (loopback when Tailscale is off),
  enable the Caddy service, and add a UFW rule restricting `443`/`80` to
  `tailscale0`.

### 5. systemd units

- Add `payload/systemd/ubuntu-zombie-localllm.service` (and reuse/extend
  the Caddy unit pattern for the web front door), header style matching
  existing units. Run the runtime as its own unprivileged system user
  with a private model dir; keep hardening consistent with the documented
  rationale for the chat unit, relaxing only what the runtime genuinely
  needs (e.g. GPU device access when acceleration is on).

### 6. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add local-serving checks
  (only when enabled): the runtime binary present and reporting a
  version; `/etc/ubuntu-zombie/localllm.env` present with correct
  ownership/modes; the service `enabled`/`active`; the `/v1/models`
  endpoint answering on loopback; the default model present and
  loadable; and, for `maximum`, GPU visible to the runtime
  (`nvidia-smi`/`rocminfo` plus an offload check), the extended models
  present, and — for the web front door — Caddy active and the endpoint
  reachable through it on the tailnet. Use `[ok]/[!]/[x]/[~]` glyphs and
  JSON records.
- Extend `cmd_doctor()` with likely-fix guidance for common failure
  modes (runtime down, port clash, a model that failed to pull, a
  **GPU that disappeared after a kernel update**, a silent CPU-only
  fallback, Caddy cert/ACME failure on the tailnet, and a
  **disk-pressure** check for the model store since unbounded growth is
  this stack's other sharp risk).
- Extend `cmd_repair()` to re-assert env/config file ownership and modes,
  re-enable a disabled unit, re-pull a missing default model, and reload
  Caddy — never to delete pulled models or downgrade a working GPU
  driver.

### 7. Receipt

- Record the local-serving selection, profile, runtime, default model,
  the extended-models and GPU and web on/off, the port, model-dir and
  cache budget, the endpoint/domain (never the API key), and the resolved
  `*_VERSION` values in `write_receipt_start`/`write_receipt_finish`.
  Record `LOCALLLM_API_KEY` only as "set"/fingerprint.

### 8. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: stop/disable the runtime and Caddy units, remove the
  units, `/etc/ubuntu-zombie/localllm.env`, the Caddyfile, drop the UFW
  rules, remove the runtime user, restore the agent provider/env to its
  prior state, and `daemon-reload`. Removal of the **model store** (the
  pulled weights) is the operator's data: delete it only behind the
  destructive confirmation phrase, never as the default path. **Do not**
  auto-remove the GPU driver on uninstall — a driver may now be load-
  bearing for the desktop session; only offer it behind explicit
  confirmation with a snapshot warning.

### 9. Policy and docs

- `payload/etc/policy.yaml`: add the model-pull/remove and runtime
  restart verbs at the `system_change` class, the `caddy reload` verb at
  `system_change`, and the **GPU driver/kernel-module** verbs at the
  highest-risk `system_change` class requiring confirmation; describe all
  of them in `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  curated model manifest location, the CPU-only default, the GPU-is-high-
  risk caveat, the tailnet-bound web model, and how the served endpoint
  relates to the existing `lmstudio` discovery path.
- `docs/ARCHITECTURE.md`: describe the optional local-serving component,
  its trust boundary (loopback runtime + a single tailnet-bound web front
  door), how it feeds the existing `lmstudio` provider, and the new
  policy entries.
- `README.md`: note the optional component and any new flag/subcommand.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 10. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_LOCALLLM=1` (and, for the web
  path, a dummy `LOCALLLM_DOMAIN`) without touching the host (extend the
  existing `noninteractive`/`subcommands` cases).
- Assert that `ZOMBIE_LOCALLLM_WEB=1` with no `LOCALLLM_DOMAIN` under
  `ZOMBIE_NONINTERACTIVE=1` exits `64`.
- Add a "standards" assertion that the new section names, the
  `ubuntu-zombie-localllm.service` unit, and the model manifest exist,
  that the rendered runtime config binds to loopback (and only
  Caddy/`/v1` is exposed), that GPU enablement is never the default, and
  that British spelling / status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python
  compile) clean — including any new `payload/bin` helpers and units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  reuse-existing-key guard, the skip-already-pulled-model guard, and the
  snapshot-before-GPU guard.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host, install kernel modules, and start listening services. All
  verification here is static (`lint`/`test`/`package`) plus dry-run
  reasoning. End-to-end serving, model pulls, GPU enablement, and the
  Caddy front door must be validated by a human on a disposable Ubuntu
  Desktop LTS VM.
- **GPU drivers are the sharp edge.** Proprietary NVIDIA/AMD drivers and
  kernel modules are the most fragile area on desktop Ubuntu and can
  break the graphical session. CPU-only is the safe default; GPU
  enablement is opt-in, snapshot-gated, the highest-risk `system_change`,
  and never reversed automatically on uninstall.
- **Disk growth is the other edge.** A model zoo fills a disk fast. The
  curated, enumerated manifest, the cache budget, and the `doctor`
  disk-pressure check are load-bearing; this is not an open-ended model
  marketplace.
- **The endpoint must stay tailnet-only.** The runtime binds to loopback;
  only Caddy exposes `/v1`, only over `tailscale0`, only with HTTPS.
  Widening this to public `0.0.0.0` breaks the project's Tailscale-only
  posture and is out of scope.
- **One runtime, one machine.** No model gateway/router across multiple
  backends, no fleet of inference nodes, no multi-tenant serving for
  outside users — that breaks the one-machine, single-operator boundary
  in [`brainstorm.md`](brainstorm.md).
- **No fine-tuning or training pipelines.** This component *serves*
  curated models; training/fine-tuning is a different, heavier workload
  and is out of scope for this plan.
