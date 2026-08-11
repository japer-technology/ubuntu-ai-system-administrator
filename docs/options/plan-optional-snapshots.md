# Plan: optional filesystem snapshots and boot rollback (`ZOMBIE_INSTALL_SNAPSHOTS`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that turns a
snapshot-capable root filesystem (Btrfs or ZFS) into a *time machine for
the system*: automatic, labelled **filesystem snapshots** taken before
every `apt` transaction and before any risky change the agent proposes,
plus **boot-time rollback** so a bad upgrade is one reboot-and-select
away. This is the worked-out promotion of candidate **A** ("ZFS or Btrfs
root with snapshots + boot rollback", `ZOMBIE_INSTALL_SNAPSHOTS`, ★★) from
[`brainstorm.md`](brainstorm.md): the local, instant-recovery complement
to off-host backup
([`plan-optional-backup.md`](plan-optional-backup.md)). Where backup
protects against *losing the machine*, snapshots protect against
*breaking the machine* — they close the loop the audit log already opens
by making the agent's "I'll snapshot before I change this" promise real.

The capability follows the same shape as the existing optional
components (Tailscale, the Forgejo options in
[`plan-optional-forgejo-server.md`](plan-optional-forgejo-server.md),
backup, observability and inventory): off by default, toggled by an
environment variable, surfaced in the interactive parameter review,
honoured in the dry-run plan, recorded in the receipt, idempotent on
re-run, gated through the policy/audit model, verifiable by
`verify`/`doctor`/`repair`, and reversible by `uninstall.sh`.

## The load-bearing constraint: configure, never convert

This is the single most important boundary in this plan, and the one the
brainstorm's risk note names directly: *root-filesystem layout changes
are deep; likely new-install only rather than in-place, and must not
touch existing partitions without explicit consent.* Therefore:

- **This plan never repartitions, reformats, or converts a root
  filesystem.** It only *configures snapshotting on a root that is
  already Btrfs or ZFS*. A default Ubuntu Desktop LTS install is `ext4`,
  which cannot be snapshotted at the filesystem level; converting it in
  place is destructive and out of scope.
- The snapshot-capable root must have been chosen at **OS-install time**
  (the Ubuntu installer offers ZFS-on-root, and Btrfs via manual
  partitioning). This option *adopts* that root; it does not create it.
- On an incompatible root the option **refuses cleanly and explains** how
  to obtain a snapshot-capable root, rather than doing anything risky.
  Refusal is a first-class, well-tested code path, not an afterthought.

## Why AI assistance is the unlock

Snapshot tooling has existed on Linux for years; almost nobody runs it,
because the day-2 burden is exactly the kind the brainstorm's thesis
names. Setting up `snapper` configs, wiring the `apt` pre/post hook,
installing `grub-btrfs` so snapshots appear in the boot menu, regenerating
GRUB, pruning old snapshots before they fill the disk, and — at the
crucial moment — knowing *which* snapshot to roll back to and how, is a
chain most owners never complete. A resident administrator changes the
calculus in two specific ways:

1. **Snapshot before harm.** The agent can take a **labelled snapshot
   immediately before any `system_change` it proposes** (a kernel
   upgrade, a driver swap, a config edit), so a regression caught by
   `verify` has an instant, local undo. This is the natural partner to
   the high-risk local-LLM/GPU-driver work the brainstorm flags as
   "snapshot first".
2. **Rollback in plain language.** When something breaks, the agent can
   *enumerate the labelled snapshots with their timestamps and the change
   that prompted each*, explain what rolling back will and will not undo,
   and walk the operator through the confirmation-gated rollback — instead
   of leaving them to decode `snapper list` under stress.

The unique value is that snapshots make the agent's own actions
**reversible at the system level**, which strengthens every other
optional component: a risky change becomes safe to *try* when it is cheap
to *undo*.

## Design principle: a thin adapter over the distro's own tooling

Do not reinvent snapshot management. Ubuntu and its ecosystem already
ship mature, well-understood tools; this plan is a **thin, idempotent
adapter** that detects the root filesystem and configures the *native*
tool for it, then exposes a small uniform helper surface to the agent:

- **Btrfs root** → [`snapper`](http://snapper.io) for snapshot management
  and retention, its `snapper` APT plugin for the pre/post-transaction
  snapshot pair, and [`grub-btrfs`](https://github.com/Antynea/grub-btrfs)
  to surface bootable read-only snapshots as a GRUB submenu. This is the
  primary, best-supported path on Ubuntu.
- **ZFS root** → Ubuntu's ZFS-on-root integrates snapshots and boot
  environments via the bootloader menu already; where `zsys` is present
  it provides APT-integrated automatic snapshots and boot rollback
  out of the box. This plan **detects and adopts** an existing ZFS-on-root
  setup and fills only the gaps (labelled-snapshot helper, retention
  sanity, `verify` checks); it does not re-implement boot-environment
  management. Because `zsys` is in maintenance, treat ZFS support as
  *adopt-what-exists* and keep Btrfs the first-class target.

Keep the adapter focused: render a `snapper` config, install the APT hook
and `grub-btrfs`, ship thin `snapshot-take`/`snapshot-list`/
`snapshot-rollback` wrappers, and stop. Do not build a cross-filesystem
abstraction layer beyond what these two backends actually need.

## What "maximum" means

The **minimum** viable role is: detect a Btrfs (or ZFS) root, configure
snapshotting, install the **pre/post-`apt` snapshot hook** so every
package transaction is bracketed by a labelled snapshot pair, and a
`verify` check that snapshots are being taken and are listable. A
**maximum** role hardens and rounds that out, each piece an independently
overridable sub-flag under a `ZOMBIE_SNAPSHOTS_PROFILE=minimum|maximum`
meta-flag (mirroring the Forgejo and backup plans' profile flag):

- **Boot-into-snapshot menu** — `ZOMBIE_SNAPSHOTS_BOOT_MENU`. Install and
  configure `grub-btrfs` (Btrfs) so read-only snapshots appear as GRUB
  entries, making rollback possible even when the system will not finish
  booting. On in `maximum`; on Btrfs this is the feature that makes "boot
  rollback" literally true. (On ZFS the boot-environment menu already
  provides the equivalent.)
- **Timeline snapshots** — `ZOMBIE_SNAPSHOTS_TIMELINE`. Enable `snapper`'s
  periodic timeline snapshots (e.g. hourly) with number/timeline cleanup,
  so there is a recovery point even between `apt` runs. Off in `minimum`
  (only `apt`- and agent-triggered snapshots), on in `maximum`.
- **Retention/cleanup policy** — `ZOMBIE_SNAPSHOTS_KEEP_*`. Configure
  `snapper`'s number-cleanup and timeline-cleanup limits so snapshots
  cannot silently consume the whole volume. Sensible defaults; a periodic
  cleanup is enabled in `maximum` and disk-pressure is surfaced by
  `doctor`.
- **Free-space guard** — `ZOMBIE_SNAPSHOTS_MIN_FREE`. A pre-snapshot
  check (and a `doctor` check) that refuses to keep stacking snapshots
  when the volume is below a free-space floor, since a full Btrfs volume
  is itself a failure mode. On in `maximum`.

The maximum profile is therefore the minimum **plus** the boot menu,
timeline snapshots, an enforced cleanup policy, and the free-space guard.
Snapshots are explicitly **not** a backup: they live on the same device
and disappear with it, so the docs must steer operators of stateful data
to tier A (backup) *as well*, never *instead*.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md`
and the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_SNAPSHOTS=0|1` — master switch (default `0`). When `1`,
  detect the root filesystem and configure snapshotting + the `apt` hook.
- `ZOMBIE_SNAPSHOTS_PROFILE=minimum|maximum` — switches the boot-menu,
  timeline, cleanup and free-space sub-flags on together (default
  `minimum`); each remains independently overridable.
- `ZOMBIE_SNAPSHOTS_FS=auto|btrfs|zfs` — filesystem backend (default
  `auto`, which detects the root filesystem). An explicit value that
  disagrees with the detected root is a validation error, never a
  conversion instruction.
- `ZOMBIE_SNAPSHOTS_APT_HOOK=0|1` — install the pre/post-`apt` snapshot
  hook (default `1`; this is the core feature).
- `ZOMBIE_SNAPSHOTS_BOOT_MENU=0|1` — install/configure `grub-btrfs`
  (default `0` in `minimum`, `1` in `maximum`).
- `ZOMBIE_SNAPSHOTS_TIMELINE=0|1` — enable periodic timeline snapshots
  (default off in `minimum`, on in `maximum`).
- `ZOMBIE_SNAPSHOTS_KEEP_NUMBER` / `_KEEP_TIMELINE_*` — `snapper`
  number-/timeline-cleanup limits with conservative defaults.
- `ZOMBIE_SNAPSHOTS_MIN_FREE` — free-space floor (percentage or absolute)
  below which new snapshots are refused and `doctor` warns.
- `ZOMBIE_SNAPSHOTS_REQUIRE=0|1` — when `1`, an incompatible root is a
  hard error; when `0` (default), an incompatible root is reported and the
  option is **skipped** with a `[~]` row rather than failing the whole
  install. The non-interactive contract (below) reads from this flag.

There are **no secrets** introduced by this component: snapshots are a
local filesystem feature with no credentials, no network surface, and no
listening service. Confirm the CI secret-scan patterns (`sk-…`,
`sk-ant-…`, `tskey-auth-…`) are not tripped and add no example secrets to
docs.

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: the detected
   root filesystem type, whether a `snapper` config already exists (create
   only when absent; never clobber an operator's existing config), whether
   the APT plugin/hook is already present, whether `grub-btrfs` is
   installed and its unit enabled, and whether GRUB has already been
   regenerated for this state. Re-running converges with no errors, no
   duplicate configs, and no redundant `update-grub`.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the
   whole optional path from env alone. When `ZOMBIE_INSTALL_SNAPSHOTS=1`
   **and** the root is not snapshot-capable **and**
   `ZOMBIE_SNAPSHOTS_REQUIRE=1`, exit `64`, consistent with
   `validate_noninteractive()`. With `ZOMBIE_SNAPSHOTS_REQUIRE=0` the
   incompatible root is logged and skipped, not fatal. When the option is
   off, requirements are unchanged.
3. **Policy gate + audit.** No new privileged behaviour bypasses the gate.
   The `apt` hook and timers run as root without the agent, but anything
   the chat agent may later be asked to drive must be classified in
   `payload/etc/policy.yaml` and described in `docs/ARCHITECTURE.md`:
   - **Take/list snapshot** — a low-risk routine class the agent should
     prefer to use *before* any `system_change` it proposes.
   - **Rollback** — its own **destructive, higher-risk class**, never
     automatic, requiring the confirmation phrase (see implementation
     step 5). Rolling back the running system is the sharp edge; the
     agent's safe default is to *create* a snapshot and *offer* rollback,
     not to perform one unprompted.
4. **No new runtime deps beyond what the installer installs.** `snapper`,
   the `snapper` APT plugin, and `grub-btrfs` are apt packages installed
   by the installer **only when the option is on and the root is Btrfs**,
   which is permitted; do not add language-level dependencies. Reuse the
   existing `apt_install`/retry helpers.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "initialise", "behaviour", "minimise", "unrecognised").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]` (`[~]` for the skipped-incompatible-root
   case).

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_SNAPSHOTS`, `ZOMBIE_SNAPSHOTS_*` to the
  defaults/derivation block alongside the other `ZOMBIE_*` settings, with
  conservative defaults (`0`, profile `minimum`, `FS=auto`, `APT_HOOK=1`,
  `REQUIRE=0`).
- Add a **root-filesystem detector** helper (e.g. read the fstype of `/`
  via `findmnt`/`stat -f`) and validators: a profile enum check, an
  `FS` enum check, integer checks for the keep-/free-space limits, and the
  rule that an explicit `ZOMBIE_SNAPSHOTS_FS` must match the detected root.
  Wire them into `validate_config()` so an invalid value is rejected
  before any host change.
- Extend `validate_noninteractive()` to exit `64` only when the option is
  enabled, the root is incompatible, **and** `ZOMBIE_SNAPSHOTS_REQUIRE=1`.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in snapshots example (interactive and `ZOMBIE_NONINTERACTIVE=1`),
  noting the Btrfs/ZFS-root prerequisite prominently.

### 2. Interactive parameter review

- Add a "Filesystem snapshots" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, the **detected root filesystem**,
  profile, `apt`-hook on/off, and boot-menu on/off. When the root is
  incompatible, the row must say so plainly (e.g. "requires Btrfs/ZFS
  root").
- Add a `_toggle_snapshots()` editor (and nested profile/boot-menu/
  timeline editors) and a new menu entry in `review_parameters()`. Append
  as the next index to minimise churn, and update the range hint and the
  "Unrecognised choice" message accordingly.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary so that, when
  snapshots are enabled on a compatible root, the plan lists the
  package-install/config/hook/`grub-btrfs`/`update-grub` steps; when the
  root is incompatible it states it will **skip** (or, with `REQUIRE=1`,
  abort) with the reason; when disabled it says nothing — keeping the
  default output unchanged.

### 4. Install sections (the core work)

Add new guarded `section` blocks, each returning early when
`ZOMBIE_INSTALL_SNAPSHOTS != 1`. Place them after the base-system sections
so GRUB and `apt` are already in their final state:

- `section "Detect snapshot-capable root"` — resolve the root filesystem.
  On an incompatible root, emit a clear `[~]`/`[!]` explanation and either
  return (when `REQUIRE=0`) or `die 64` (when `REQUIRE=1`). All later
  sections short-circuit on the same detection result.
- `section "Install snapshot tools"` *(Btrfs)* — `apt_install snapper`
  and, when `ZOMBIE_SNAPSHOTS_APT_HOOK=1`, the `snapper` APT plugin,
  guarded by binary/plugin presence.
- `section "Configure snapshots"` — create a `snapper` config for `/`
  **only when absent** (`snapper -c root create-config /` guarded by
  `snapper list-configs`); apply the retention/timeline settings from the
  env via `snapper set-config`. On ZFS, *adopt* the existing
  configuration and only record/verify it.
- `section "Enable apt snapshot hook"` — ensure the pre/post-transaction
  snapshot pair is active (the `snapper` APT plugin provides this; verify
  it is enabled rather than hand-rolling a duplicate hook). Each `apt`
  transaction must then be bracketed by a labelled snapshot pair.
- `section "Enable boot rollback menu"` *(maximum / boot-menu, Btrfs)* —
  `apt_install grub-btrfs`, enable its path-watching unit, and run
  `update-grub` **once** (guard against repeated regeneration) so
  snapshots appear in a GRUB submenu.
- `section "Install snapshot helpers"` — ship the thin `payload/bin`
  wrappers (below) used by the agent and operator.

### 5. Snapshot helpers and rollback (operator/agent-driven)

Provide a small, uniform helper surface so the agent does not shell out to
backend-specific commands directly:

- `payload/bin/snapshot-take` — create a **labelled, descriptive**
  snapshot (e.g. `snapshot-take "before kernel upgrade"`); this is the
  low-risk verb the agent uses *before* a proposed `system_change`.
- `payload/bin/snapshot-list` — list snapshots with id, timestamp, type,
  and description in a stable, parseable form the agent can summarise.
- `payload/bin/snapshot-rollback` — perform a rollback. This is
  **destructive**: it must require the **confirmation phrase** (consistent
  with `uninstall.sh`'s destructive steps), is its own high-risk policy
  class, is **never** scheduled or automatic, and prints loudly that a
  running-system rollback may require a reboot and will discard changes
  made since the target snapshot. Boot-time rollback via the GRUB submenu
  remains the human recovery path when the system will not boot.

All helpers use the bash shebang/header, are ShellCheck-clean, and follow
the best-effort guard convention (`|| true`) for any read-only probing per
the diagnostics convention; the destructive path is explicitly *not*
best-effort and must surface failures.

### 6. systemd units / timers

- Reuse `snapper`'s own `snapper-timeline.timer`/`snapper-cleanup.timer`
  rather than shipping bespoke units; enable them only when
  `ZOMBIE_SNAPSHOTS_TIMELINE=1` / the cleanup policy is on. If any thin
  wrapper unit is needed (e.g. a free-space guard), add it under
  `payload/systemd/` with header style matching existing units, and
  `daemon-reload`/`enable --now` idempotently.

### 7. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add snapshot checks (only
  when enabled and on a compatible root): the backend tool is present and
  reports a version; a `snapper` config for `/` exists with the expected
  retention; the APT hook/plugin is active; recent `apt`-triggered
  snapshots exist; (maximum) `grub-btrfs` is installed and its unit
  enabled and snapshots appear in GRUB; and free space is above the floor.
  Use `[ok]/[!]/[x]/[~]` glyphs and JSON records; on an incompatible root
  with the option enabled-but-skipped, emit `[~]` with the reason.
- Extend `cmd_doctor()` with likely-fix guidance for common failure modes
  (no snapshot-capable root → explain the OS-install prerequisite; disk
  near-full from accumulated snapshots → prune guidance; APT hook
  inactive; `grub-btrfs` unit disabled or GRUB not regenerated).
- Extend `cmd_repair()` to re-assert the `snapper` config values, re-enable
  the APT hook and `grub-btrfs` unit, and re-run `update-grub` if the menu
  is stale — **never** to perform a rollback and never to create or delete
  the `snapper` config destructively.

### 8. Receipt

- Record the snapshots selection, detected root filesystem, profile,
  `apt`-hook on/off, boot-menu on/off, timeline on/off, and the resolved
  retention/free-space settings in
  `write_receipt_start`/`write_receipt_finish`. There are no secrets to
  fingerprint. When skipped on an incompatible root, record that fact and
  the reason.

### 9. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the option created, gated so a baseline-only install
  is untouched: disable the APT hook/plugin, disable and (when this option
  installed it) remove `grub-btrfs` and re-run `update-grub`, disable the
  timeline/cleanup timers this option enabled, and remove the `payload/bin`
  helpers from `/opt/ai-zombie/`. **Do not delete existing snapshots or
  the `snapper` config by default** — they are recovery points the
  operator may still need, and deleting them is irreversible. Offer
  snapshot/config deletion strictly behind the destructive confirmation
  phrase, never as the default path, and warn that it discards recovery
  points.

### 10. Policy and docs

- `payload/etc/policy.yaml`: add the snapshot-tool invocations to
  `sudo_allow_list` at a routine class for **take/list**, and add
  **rollback** as its own higher-risk/destructive class (see
  non-negotiable #3 and step 5).
- `docs/CONFIGURATION.md`: document every new env var, defaults, the
  Btrfs/ZFS-root prerequisite, the `REQUIRE`/skip behaviour, and the
  rollback safety model. State plainly that **snapshots are not a backup**
  and point to [`plan-optional-backup.md`](plan-optional-backup.md).
- `docs/ARCHITECTURE.md`: describe the optional snapshots component, its
  trust boundary (a local filesystem feature with no network surface and
  no secrets), the "configure-never-convert" constraint, and the new
  policy entries, emphasising the rollback class.
- `README.md`: note the optional component, its Btrfs/ZFS-root
  prerequisite, and any new flag/subcommand.
- `CHANGELOG.md`: add an entry under the unreleased section; then bump
  `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 11. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_SNAPSHOTS=1` without touching the
  host (extend the existing `noninteractive`/`subcommands` cases).
- Assert the incompatible-root contract by reasoning over the detector:
  with `ZOMBIE_SNAPSHOTS_REQUIRE=1` on a non-Btrfs/ZFS root under
  `ZOMBIE_NONINTERACTIVE=1` the planned exit is `64`; with `REQUIRE=0` the
  option is skipped, not fatal. (Because CI runs on whatever filesystem
  the runner provides, drive this through the validation/plan layer rather
  than real snapshotting.)
- Add a "standards" assertion that the new section names, helpers, and any
  units exist and that British spelling / status glyphs are respected, and
  that `snapshot-take`/`snapshot-list`/`snapshot-rollback` pass `bash -n`.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python compile)
  clean — including the new `payload/bin` helpers and any units.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  create-config-only-when-absent, single-`update-grub`, and
  incompatible-root short-circuit guards.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host's bootloader and filesystem. All verification here is static
  (`lint`/`test`/`package`) plus dry-run reasoning. End-to-end
  snapshotting and a real rollback must be validated by a human on a
  disposable Ubuntu Desktop LTS VM with a **Btrfs (or ZFS) root**.
- **No in-place conversion.** This plan refuses to convert an `ext4` (or
  other non-snapshot) root; obtaining a Btrfs/ZFS root is an OS-install
  decision and is the operator's responsibility. Never touch existing
  partitions without explicit consent — the brainstorm's hard line.
- **Snapshots are not backups.** They share the device and fail with it;
  they protect against bad changes, not against disk loss, theft, or
  ransomware. Stateful-data operators must also enable tier A (backup).
  The docs must make this non-substitution explicit.
- **Rollback is the sharp edge.** A running-system rollback discards
  changes since the target snapshot and may need a reboot; it stays
  operator-driven, confirmation-gated, and in its own policy class. The
  agent's default offering is to *create* a labelled snapshot and *offer*
  rollback, never to perform one unprompted.
- **Disk pressure is a real failure mode.** Unbounded snapshots can fill a
  Btrfs volume and wedge the system; the cleanup policy and free-space
  guard are load-bearing in `maximum`, and `doctor` surfaces pressure.
- **ZFS support is adopt-what-exists.** Because `zsys` is in maintenance,
  this plan adopts and verifies an existing ZFS-on-root rather than
  re-implementing boot-environment management; Btrfs + `snapper` +
  `grub-btrfs` is the first-class target.
