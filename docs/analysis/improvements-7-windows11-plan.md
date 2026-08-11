# Improvement 7 plan — a Windows 11 version of Ubuntu Zombie

## Question

Can the Ubuntu Zombie installation script — and the product it
installs — be ported to Windows 11, so a Windows PC gains the same
private, root-capable (Administrator-capable) AI Systems Administrator
account, with the same policy gate, approval flow, audit trail, and
Time to Live?

The short answers are:

- **Yes, but it is a port of the product, not a port of the script.**
  `scripts/install.sh` is ~4,800 lines of Bash that manipulates
  `apt`, Linux users, `sudoers`, `systemd`, and POSIX file modes.
  None of those exist on Windows. The Windows version needs a
  PowerShell installer and Windows-native equivalents for every
  privileged surface.
- **The Python agent core is largely portable.** `policy.py`,
  `audit.py`, `history.py`, `lifecycle.py`, `providers.py`,
  `server.py`, and the pi-mono bridge are standard-library Python and
  Node.js. The Linux-specific parts are concentrated in `tools.py`
  (shell/package/service tools), the default `policy.yaml` rules, and
  path/permission handling.
- **The trust model translates, with different primitives.** Linux
  `zombie` + passwordless `sudo` maps to a hidden local Windows
  account in the `Administrators` group (or a service running as a
  virtual service account), with UAC, ACLs, and DPAPI replacing
  sudoers, `chmod 600`, and root-owned receipts.
- **It should live behind a clear platform boundary**, ideally as a
  sibling product (working name: *Windows Zombie*), sharing the
  portable agent core rather than growing `install.sh` into a
  cross-platform script. `docs/analysis/improvements-6-plan.md`
  reached the same conclusion for macOS: one release manifest, per-OS
  installers that fail clearly on the wrong system.

This document is an analysis and implementation plan, not an
implemented port.

## What exists today (and how Ubuntu-specific it is)

| Component | Today (Ubuntu) | Portability |
| --------- | -------------- | ----------- |
| Installer | `scripts/install.sh` — Bash, `install/verify/doctor/repair/uninstall`, component registry, receipts, dry-run, `ZOMBIE_NONINTERACTIVE=1` | Not portable; behaviour and UX are the spec for a PowerShell rewrite |
| Uninstaller | `scripts/uninstall.sh` | Same |
| Agent account | `useradd`, `/etc/sudoers.d/`, hidden from GDM | Windows: `New-LocalUser`, `Administrators` group, `SpecialAccounts` registry hide, or a service SID |
| Chat service | `payload/agent/server.py` on `127.0.0.1:7878` via `ThreadingHTTPServer` | Portable Python; loopback bind works identically |
| Service management | `payload/systemd/*.service`, `*.timer` | Windows Service (via a small service wrapper) + Scheduled Task for the health timer |
| Tool registry | `payload/agent/tools.py`: shell (`bash`), filesystem, `apt` package tool, `systemctl` service tool, network status | Needs a Windows tool set: PowerShell shell tool, `winget` package tool, `sc`/`Get-Service` service tool |
| Policy gate | `payload/agent/policy.py` + `payload/etc/policy.yaml` (argv-aware, strips `sudo`, `/dev/*` exceptions, system-path rules) | Engine portable; the rule set is Linux-specific and needs a Windows rule set (PowerShell verbs, `C:\Windows`, registry, UAC bypass patterns) |
| Audit log | `payload/agent/audit.py` JSON-lines with redaction | Portable; destination and ACLs change |
| Secrets | root-only env file edited by `secrets-edit`, `0600` | Windows: ACL-restricted file under `%ProgramData%` and/or DPAPI encryption |
| History | SQLite via `payload/agent/history.py` | Portable |
| TTL / lifecycle | `payload/agent/lifecycle.py` state file | Portable |
| LLM bridge | Node.js 22 + `pi-mono-bridge.mjs` / `pi-ai-bridge.mjs` | Portable; Node installs via `winget` |
| Local models | `llama.cpp` component, pinned builds | Portable; upstream ships Windows binaries |
| Forgejo component | Linux service + PostgreSQL + Caddy | Out of scope for the first Windows release (see below) |
| Log rotation | `payload/logrotate/` | Windows: size-capped JSONL rotation in-process or a Scheduled Task |
| Tests | `tests/smoke.sh` (Bash), `make lint/test` | Windows needs Pester + PSScriptAnalyzer; Python tests stay shared |
| CI | `.github/workflows/ci.yml` on `ubuntu-*` runners | Add `windows-latest` jobs |

The concentration matters: roughly 80% of the Python agent is
OS-neutral; nearly 100% of the Bash is not.

## Decisions

### 1. A sibling installer, not a cross-platform `install.sh`

Do **not** teach `scripts/install.sh` about Windows. Bash-on-Windows
(WSL, Git Bash) cannot create Windows services, local accounts, or
ACLs correctly, and `docs/PLATFORMS.md` already declares WSL
unsupported. Instead:

- `scripts/install.ps1` (and `scripts/uninstall.ps1`): PowerShell 7+
  installers that mirror the verb + component CLI
  (`install/verify/doctor/repair/uninstall`, `--dry-run`,
  `ZOMBIE_NONINTERACTIVE=1`, exit `64` on missing required env).
- `scripts/install.sh` gains an early guard that detects Windows
  environments (WSL interop, `OSTYPE=msys`) and points the operator
  at the PowerShell installer with a clear error.
- Whether the port ships from this repository or a sibling
  `windows-zombie` repository is an open question (see below); either
  way the Python/Node agent core must be shared, not forked.

### 2. Windows-native equivalents for every privileged surface

| Ubuntu primitive | Windows 11 equivalent |
| ---------------- | --------------------- |
| `zombie` user + passwordless sudo | Local user `zombie` in `Administrators`; hidden from the login screen via `HKLM\...\Winlogon\SpecialAccounts\UserList`; password random, recorded only in the Administrators-only receipt |
| `systemd` service | Windows Service running the chat server as the `zombie` account (or a per-service virtual account), auto-start, failure restart policy |
| `systemd` health timer | Scheduled Task running `health-check` every N minutes |
| `/opt/ai-zombie/` | `C:\Program Files\WindowsZombie\` (binaries, read-only) |
| `/etc/ubuntu-zombie/` + state | `C:\ProgramData\WindowsZombie\` (`etc\`, `state\`, `logs\`), ACL'd to `Administrators` + the agent account |
| `chmod 600` secrets | `icacls` reset + explicit ACE for the agent account; optionally DPAPI-protect provider keys at rest |
| `apt`/NodeSource pins | `winget install` with pinned versions of Python 3.12 and Node.js 22 (with checksum-verified direct download fallback for offline/managed machines) |
| `logrotate` | In-process size/age rotation for the audit JSONL, or a Scheduled Task |
| root-only install receipt | Receipt under `%ProgramData%` readable by `Administrators` only |
| `os-release` gate (`ID=ubuntu`) | `Get-ComputerInfo` gate: Windows 11 (build ≥ 22000), 64-bit, refuse Server SKUs, warn on Home (no Group Policy surface) |

### 3. Same trust model, restated for Windows

The Ubuntu invariants carry over verbatim in intent:

- **Loopback only.** The chat service binds `127.0.0.1` and the
  installer must add no inbound firewall rule; verify explicitly that
  Windows Defender Firewall has no allow rule for the service.
- **Fail-closed policy.** The Windows `policy.yaml` keeps
  `default_class: destructive`, `user_change` approval required, and
  no blanket elevation rule — mirroring the contract in
  `payload/etc/policy.yaml` and `tests/smoke.sh`.
- **Everything audited.** Same JSON-lines audit format, same
  redaction, plus optional mirroring of elevated actions to the
  Windows Event Log for operators who live in Event Viewer.
- **Operator revocation.** TTL, key rotation, and `uninstall.ps1`
  (removes service, task, account, files, firewall verification)
  remain first-class.

New Windows-specific policy concerns the rule set must cover:

- PowerShell is both the shell and a scripting engine; classify by
  resolved command/cmdlet, not raw text (`Set-`, `Remove-`, `Stop-`
  verbs; `reg add`, `bcdedit`, `schtasks`, `netsh`, `Set-MpPreference`
  as `system_change`/`network_change`/`destructive`).
- Registry writes are the Windows analogue of `/etc` edits — they
  need path-based rules like today's system-path rules.
- `-EncodedCommand`, `Invoke-Expression`, and download-and-execute
  patterns classify as `destructive` (fail-closed already covers
  unknowns, but these deserve explicit rules and tests).
- Exclude safe pseudo-targets (`NUL`, `$null`) the way Ubuntu excludes
  `/dev/null` and friends.

### 4. Portable core, per-OS adapters

Restructure only as much as the port needs:

- Keep `policy.py`, `audit.py`, `history.py`, `lifecycle.py`,
  `providers.py`, `runner.py`, `server.py`, `pi_mono.py`,
  `skill_loader.py`, and the web UI shared and platform-neutral.
  Replace hard-coded POSIX paths with a small platform module that
  resolves install/state/config/secrets paths per OS (env overrides
  such as `ZOMBIE_HISTORY_DB` already exist and stay).
- Split `tools.py`'s OS-facing tools behind the same tool names and
  schemas: `shell.run` executes PowerShell on Windows; the package
  tool drives `winget`; the service tool drives the Service Control
  Manager. The registry stays closed; tool names and audit records
  stay identical so the UI, policy classes, and history schema do not
  fork.
- Ship a Windows skills set (`winget`, `services`, `defender`,
  `windows-update`) parallel to the current `apt`/`systemd` skills.
- `payload/bin/` helpers get PowerShell counterparts
  (`verify-release.ps1`, `secrets-edit.ps1`,
  `collect-diagnostics.ps1`, `zombie-chat.ps1`).

### 5. Component scope for the first Windows release

- **In:** the `zombie` component (agent account, chat service, policy,
  audit, TTL, health task) and the standalone `llama` component
  (upstream publishes Windows builds; `llama-manager` becomes
  PowerShell; listener stays `127.0.0.1:8080`).
- **Out (initially):** the Forgejo component. Its PostgreSQL, Caddy
  `.local` TLS, and runner/Docker integration are a separate port with
  little overlap; the component registry keeps it unselectable on
  Windows with a clear message.

## Phased implementation plan

### Phase 0 — decisions and scaffolding

1. Answer the open questions below (repo split, account model,
   naming).
2. Write `docs/PLATFORMS.md` and `docs/VISION.md` updates only insofar
   as they must state that Windows support is in development and where
   it lives; Ubuntu docs otherwise unchanged.
3. Add the Windows-detection guard and error message to
   `scripts/install.sh`.

### Phase 1 — portable core extraction

1. Introduce the platform path/permission module in
   `payload/agent/`; route all filesystem locations through it.
   Behaviour on Ubuntu must be byte-identical (existing `make test`
   proves it).
2. Split platform tools in `tools.py` behind the existing tool names;
   Linux implementations move without behaviour change.
3. Add Windows implementations (PowerShell shell tool, winget package
   tool, SCM service tool, netsh-based network status) with unit-level
   tests that run on any OS via injection/mocking.
4. Author the Windows `policy.yaml` rule set and extend the policy
   tests with Windows classification cases (elevation verbs, registry
   paths, encoded commands, `NUL` exclusions).

### Phase 2 — installer

1. `scripts/install.ps1`: prerequisite gate (Windows 11 build, admin
   elevation, disk, network), review screen, dry-run, receipts,
   non-interactive mode with exit `64`, idempotent re-run convergence
   — feature-for-feature with the Bash installer's `zombie`
   component, including a PowerShell port of the component registry
   dispatch (`scripts/component-registry.sh` semantics: deps
   registered before dependants, uninstall reverses order).
2. Create/verify: agent account (hidden, Administrators, random
   password to receipt), directory tree + ACLs, Python/Node via
   winget with pinned versions, venv + bridge dependencies from
   `payload/agent/bridge-dependencies.lock`, secrets file,
   Windows Service, health Scheduled Task, Start Menu shortcut to
   `http://127.0.0.1:7878`.
3. `verify`/`doctor`/`repair` verbs re-checking each of the above;
   `scripts/uninstall.ps1` reversing all of it, including account and
   receipt removal, with the same confirmation-phrase safeguards.

### Phase 3 — llama component

1. Pin Windows `llama.cpp` builds in `payload/etc/llama-builds.json`
   (or a Windows sibling) with checksums; port `llama-manager` to
   PowerShell; service on `127.0.0.1:8080`.
2. Keep `/locals` discovery unchanged — it is already generic loopback
   port probing.

### Phase 4 — tests, CI, docs, release

1. Windows smoke suite: PSScriptAnalyzer on all `.ps1`,
   `python3 -m py_compile` on shared code, subcommand parsing,
   non-interactive behaviour, policy contract tests, standards checks
   — the Windows analogue of `tests/smoke.sh` sections, plus a
   `windows-latest` CI matrix leg running it and the shared Python
   tests.
2. Dry-run installer job on `windows-latest`; full install job on a
   disposable Windows 11 VM (manual or nightly, mirroring the Ubuntu
   container caveat — CI runners are not a real desktop).
3. Docs: Windows quickstart, configuration (paths, env vars, service
   names), security notes (UAC, Defender, SmartScreen, script
   signing), troubleshooting; `docs/PLATFORMS.md` gains a Windows
   hosts table with explicit Home/Server/ARM64 statuses.
4. Release: extend `make package` (or the release workflow) to emit a
   Windows zip with `SHA256SUMS`/cosign coverage; document Authenticode
   signing as a prerequisite for a non-hostile SmartScreen experience,
   even if the first releases ship unsigned with instructions.

## Risks and mitigations

- **UAC vs. passwordless sudo.** An Administrators-group account still
  gets a filtered token in interactive sessions; the service context
  avoids UAC prompts but must be designed deliberately. Mitigation:
  run all privileged tool execution inside the elevated service
  context, never via interactive elevation; document this in the
  Windows trust model.
- **Defender/SmartScreen friction.** Unsigned PowerShell + a local
  admin account + an LLM executing commands resembles malware to
  heuristics. Mitigation: Authenticode signing plan, no execution
  policy weakening beyond `-ExecutionPolicy Bypass -File` for the
  installer itself, transparent docs, and submission to Microsoft's
  false-positive process if needed.
- **PowerShell classification is harder than argv.** Pipelines,
  aliases, and `-EncodedCommand` obscure intent. Mitigation:
  fail-closed default already covers the unknown; invest test effort
  in the explicit rules; consider resolving aliases before
  classification as the analogue of today's `sudo`-stripping.
- **Windows Home lacks some management surfaces** (Group Policy,
  certain service hardening). Mitigation: decide supported SKUs up
  front and gate in the installer.
- **Divergence between the two products.** Mitigation: shared agent
  core with per-OS adapters (Phase 1) and a shared policy/tests
  contract; any repo split must vendor or submodule the core, not
  copy it.

## Clarifying questions for the maintainers

Answers to these gate Phase 0; the plan above assumes the defaults in
parentheses.

1. **Repository:** should the Windows port live in this repository
   under per-OS installer scripts, or in a sibling
   `windows-zombie` repository sharing the agent core? (Assumed:
   decision explicitly open; plan works for both, sibling repo
   preferred by precedent — `lmstudio-vampire`, `forgejo-society`.)
2. **Account model:** hidden local Administrator account named
   `zombie` (closest to the Ubuntu trust model), or a virtual service
   account with no interactive identity? (Assumed: hidden local
   Administrator, renameable via `ZOMBIE_USER`.)
3. **Supported SKUs:** Windows 11 Pro only, or Pro + Home? Server
   excluded? ARM64 best-effort? (Assumed: Pro supported, Home
   best-effort, Server unsupported, ARM64 best-effort.)
4. **Service wrapper:** is a small MIT-licensed service wrapper (or a
   `pywin32`-free stdlib approach via a Scheduled Task at logon of the
   service account) acceptable, given rule 5 (no new runtime
   dependencies)? The "exact list" of allowed dependencies in
   `CONTRIBUTING.md` is Ubuntu-specific and needs a Windows
   equivalent list.
5. **Forgejo:** confirm it is out of scope for the first Windows
   release.
6. **Code signing:** is there (or will there be) an Authenticode
   certificate for release signing, and should unsigned releases ship
   in the meantime?
7. **Naming:** "Windows Zombie" and `C:\Program Files\WindowsZombie\`
   are placeholders — confirm product and path naming before any code
   lands.

## Summary

The Windows 11 version is a real port with a well-defined seam: keep
the Python/Node agent core shared behind a small platform layer, write
a PowerShell installer that reproduces the Bash installer's verbs,
receipts, idempotence, and non-interactive contract using Windows
primitives (local admin account, Windows Service, Scheduled Task,
ACLs, winget), author a Windows fail-closed policy rule set, and ship
`zombie` + `llama` first while explicitly deferring Forgejo. The
largest non-code risks are SmartScreen/Defender trust and the UAC
elevation model, both of which need decisions before implementation
starts.
