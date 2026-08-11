# 05 — Windows: "Windows Zombie"

Windows is the larger port: no bash, no sudoers, no systemd, a
different privilege model, and different filesystem semantics. It is
also the port where the "EXE installer" expectation is strongest and
easiest to meet, because Windows users already expect a setup wizard
followed by a running service.

## Platform mapping

| Ubuntu concept | Windows equivalent |
| -------------- | ------------------ |
| `zombie` Linux account | Dedicated local account (`New-LocalUser`) or, preferably, a **virtual service account** (`NT SERVICE\ZombieAgent`) — passwordless, non-interactive, per-service identity |
| Passwordless sudo | Service runs with required privileges; elevation is a property of the service identity, not a per-command `sudo` |
| systemd unit | Windows Service (SCM), via `pywin32` service wrapper or WinSW/NSSM around the Python entry point |
| systemd health timer | Scheduled Task (`schtasks` / `Register-ScheduledTask`) |
| `/opt/ai-zombie/` | `C:\Program Files\ZombieAgent\` (binaries) + `%ProgramData%\ZombieAgent\` (state, logs, config) |
| `/etc/` overlays | `%ProgramData%\ZombieAgent\etc\` |
| logrotate | Built-in rotation in `audit.py`/logging config (simplest cross-platform answer) |
| apt / NodeSource | winget (`winget install Python.Python.3.12 OpenJS.NodeJS.LTS`) or runtimes bundled in the installer |
| File modes `0600` | NTFS ACLs (`icacls` / pywin32) restricting to SYSTEM + Administrators |
| `apt.md` / `systemd.md` skills | `winget.md` / `services.md` / `powershell.md` skills |
| bash operator helpers | PowerShell equivalents (`verify.ps1`, …) |

## The privilege model difference (the important part)

On Ubuntu, every privileged action is an explicit `sudo` invocation
— a natural choke point for the policy gate. On Windows, the service
itself holds the privilege, so **the policy gate becomes the only
brake**. Consequences:

1. `policy.windows.yaml` must be strict from day one: PowerShell,
   `reg`, `sc`, `net`, `bcdedit`, `diskpart` classifications, with
   `destructive` defaults for anything registry- or boot-touching.
2. The runner should execute tool calls in a *deliberately
   de-elevated* child where possible (restricted token) and only run
   elevated when the approved policy class requires it — recreating
   the sudo choke point in reverse.
3. Command classification must handle PowerShell's aliasing and
   quoting (`ri`, `del`, `Remove-Item` are one verb). Classify on
   resolved cmdlet names, not raw strings.

This is the single riskiest piece of the Windows port and should be
designed and reviewed before any packaging work.

## Delivery mechanisms, best-first

1. **Setup EXE (Inno Setup).** The headline "just an EXE" answer.
   The `lmstudio-vampire` repo already pairs a PyInstaller build
   with an Inno Setup installer in `packaging/windows/` — reuse that
   recipe. The wizard is inherently attended, so unlike Linux/macOS
   the stage-1/stage-2 split can *fold into one flow*: the final
   wizard page is an explicit opt-in checkbox ("Activate the agent
   service now") plus API-key entry; unticked, it behaves stage-1
   (files + `zombie.exe` CLI, activate later with
   `zombie install` from an elevated prompt).
2. **MSI (WiX).** Needed later for winget's preferred format and any
   enterprise/GPO story; more toolchain ceremony than Inno. Start
   with Inno EXE, add MSI when winget submission happens.
3. **winget.** `winget install JaperTechnology.ZombieAgent` via a
   manifest in `microsoft/winget-pkgs`. Free, official, and the
   Windows analogue of the apt repo. Requires a signed installer.
4. **Chocolatey/Scoop.** Community channels; take PRs, don't own.

**Code signing is mandatory in practice** — an unsigned EXE that
creates admin services is indistinguishable from malware to
SmartScreen and AV heuristics. Budget for an Authenticode (ideally
EV) certificate and CI signing before public artifacts.

## Runtime packaging

Bundle Python via PyInstaller (per the `lmstudio-vampire`
precedent) or an embedded CPython distribution so the installer has
zero prerequisites; install Node 22 via winget or bundle the pi-mono
bridge's runtime. Do not depend on a system Python on Windows.

## WSL is not a shortcut

WSL is explicitly unsupported today
([`docs/PLATFORMS.md`](../docs/PLATFORMS.md)) and reusing the Ubuntu
installer inside WSL would administer the WSL guest, not the Windows
host — failing the product's entire point. Native port only.

## Deliverables

1. `platform/windows/` shell in PowerShell + a Python service
   wrapper: account/identity, service + scheduled task, ACLs,
   `install/verify/doctor/repair/uninstall`, receipts, reversal.
2. De-elevation design + `policy.windows.yaml` (reviewed first).
3. `winget.md`/`services.md`/`powershell.md` skills.
4. PyInstaller + Inno Setup EXE from CI (`windows-latest` job:
   lint via PSScriptAnalyzer, python compile, dry-run); signed.
5. winget manifest once the signed installer is stable.
6. Platform tier entry in `docs/PLATFORMS.md`.
