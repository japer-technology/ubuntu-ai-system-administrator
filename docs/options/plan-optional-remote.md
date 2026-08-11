# Plan: optional remote access — bring the remote surface back as one audited component (`SSH` + `Tailscale` + `fail2ban` + `x11vnc`)

## Goal

Add an **opt-in** capability to `scripts/install.sh` that re-introduces, as
a single coherent component, every piece of remote-access machinery that
[`docs/analysis/ubuntu-zombie-zero.md`](../docs/analysis/ubuntu-zombie-zero.md)
strips out to reach "Zombie Zero": the **SSH server** (`agent`
`authorized_keys` provisioning + the sshd hardening drop-in), **Tailscale**
(install + enrolment), **fail2ban** (brute-force throttling), and the
**x11vnc** loopback desktop path (with its optional autologin companion).

The premise of this plan is the inverse of the Zombie Zero thought
experiment. Assume the baseline has been reduced to "one door — the
loopback browser at `127.0.0.1:7878`" and *all* of the "Remove" rows in
that analysis are gone. This plan brings them back — not as the old,
always-on installer phases, but as **one feature-gated component**
(`ZOMBIE_INSTALL_REMOTE`) that follows the same opt-in shape as the other
plans in this directory
([`plan-optional-proxy.md`](plan-optional-proxy.md),
[`plan-optional-backup.md`](plan-optional-backup.md)) and gives each
restored tool **more functionality and a clearer purpose** than it had as
a hard-wired phase: off by default, toggled by environment variables,
surfaced in the interactive parameter review, honoured in the dry-run
plan, recorded in the receipt, idempotent on re-run, gated through the
policy/audit model, verifiable by `verify`/`doctor`/`repair`, and
reversible by `uninstall.sh`.

This is the natural promotion of the networking-and-remote-access theme in
[`brainstorm.md`](brainstorm.md) (Tier **D**, *"beyond the existing
Tailscale option"*): rather than leaving remote access as an unconditional
installer concern, it becomes a declared, recoverable, agent-operable
opt-in like every other optional stack.

## Why AI assistance is the unlock

Installing an SSH server or `tailscale up` is one command each; *operating*
a remote-access surface safely over months is the classic day-2 burden the
brainstorm's thesis names directly. The hard parts were never the install
— they are key rotation when a workstation is lost, re-enrolling a tailnet
node after an auth-key expiry, reading `fail2ban` jails to tell a real
attack from a fat-fingered passphrase, recovering desktop access through a
VNC tunnel at 11pm when the session has wedged, and — most importantly —
*knowing the blast radius* of every one of those changes before making it.
A resident administrator that can read the audit log, run
`verify`/`doctor`/`repair`, and explain the next step in plain language
collapses exactly this toil:

- **The revocation story becomes conversational.** The MVP already prizes
  "remove the SSH key / disable Tailscale" as the kill switch. Here the
  agent can *perform* a key rotation or a tailnet logout on request,
  narrate each step, and confirm afterwards that inbound is closed — under
  approval and audit — instead of leaving the operator to remember the
  exact `tailscale logout` / `authorized_keys` surgery.
- **Brute-force triage stops being log-grepping.** The agent reads
  `fail2ban-client status`, explains which jail banned which address and
  why, and proposes the obvious revert for a self-inflicted ban.
- **Emergency desktop access is shepherded, not improvised.** The agent
  can confirm the VNC listener is loopback-only, hand the operator the
  exact SSH-tunnel command, and verify the tunnel rather than leaving them
  to reconstruct port-forward flags.

The difficulty here is **genuinely operational**, which is the sharpest
AI-assistance argument in the brainstorm — and it is precisely the
difficulty that made these phases risky enough to be the first things
Zombie Zero sheds.

## Design principle: closed by default, one switch, every door audited

Zombie Zero's safety argument is that removing the remote surface is safe
*because* the surface is gone. Re-introducing it must not silently undo
that. This plan honours the same bright line by making the whole component
**closed by default** and every re-opened door **declared and gated**:

- **One master switch, off by default.** `ZOMBIE_INSTALL_REMOTE=0` leaves
  the box exactly as Zombie Zero describes — loopback browser only. Nothing
  in this plan changes the default footprint.
- **Tailnet-bound by default when on.** Consistent with the project's
  Tailscale-only posture, the default *enabled* posture binds inbound SSH
  to `tailscale0` only (the existing "Firewall (Tailscale-only inbound)"
  shape). Allowing SSH on every interface is a separate, loudly flagged
  opt-in, never implied by simply turning the component on.
- **Each sub-surface independently gated.** SSH, Tailscale, fail2ban, and
  VNC are individually toggleable sub-flags under the master switch, so an
  operator can re-open *only* what they need (e.g. Tailscale + SSH, no VNC)
  rather than the whole 2014-era phase block.
- **Secrets stay root-owned and fingerprinted.** The SSH public key, the
  Tailscale auth key, and the VNC password are handled exactly as the
  installer already handles them — written to root-owned/agent-owned files
  with strict modes, never committed, surfaced in the receipt only as
  set/unset fingerprints. The CI secret-scan patterns (`sk-…`, `sk-ant-…`,
  `tskey-auth-…`) must not be tripped; `tskey-auth-…` in particular means
  the Tailscale auth key must never be echoed, logged, or written to the
  receipt verbatim.
- **The policy gate is the boundary, not the firewall alone.** Anything the
  chat agent may later be asked to drive — rotate a key, re-enrol the
  tailnet, unban an address, restart sshd — goes through
  [`payload/etc/policy.yaml`](../payload/etc/policy.yaml) and the audit
  log, never a fresh un-gated `sudo` path.

## What "maximum" means

The **minimum** viable remote component is: SSH server installed and
hardened (key-only, `agent`-only, the existing
`/etc/ssh/sshd_config.d/99-ubuntu-zombie.conf` drop-in), inbound bound to
`tailscale0`, with Tailscale installed and enrolled, and a `verify` check
that sshd is active, key-only, and reachable only on the tailnet. A
**maximum** role rounds that out, each piece an independently overridable
sub-flag under a `ZOMBIE_REMOTE_PROFILE=minimum|maximum` meta-flag
(mirroring the proxy, backup and Forgejo plans' profile flag):

- **Brute-force protection** — `ZOMBIE_REMOTE_FAIL2BAN`. Install and
  enable `fail2ban` with the sshd jail, plus a `verify` check that the
  jail is active and a `doctor` hint for a self-inflicted ban. On in
  `maximum`. (Largely a no-op while SSH is tailnet-only, but essential the
  moment all-interface SSH is opted into — so it is *required* whenever
  `ZOMBIE_REMOTE_SSH_PUBLIC=1`.)
- **Emergency desktop access** — `ZOMBIE_REMOTE_VNC`. The x11vnc
  loopback-only autostart entry and password store, reachable only through
  an SSH tunnel, with a `verify` check that the listener is on `127.0.0.1`
  and **not** the network. On in `maximum` *only when the GUI stack is
  present* (it depends on `ZOMBIE_ENABLE_GUI`); otherwise skipped with a
  `[~]`.
- **Unattended desktop** — `ZOMBIE_REMOTE_AUTOLOGIN`. The gdm3 autologin
  companion to the VNC path, so a rebooted box returns to a viewable
  session without a console operator. Off even in `maximum` (it weakens
  at-console security); it is an explicit convenience opt-in tied to the
  VNC story.
- **Key rotation helper + agent verbs** — `ZOMBIE_REMOTE_MANAGED`. Install
  a `payload/bin/` operator helper (e.g. `remote-access`) that wraps the
  common day-2 actions — add/rotate an authorised key, show tailnet
  status, list/clear a fail2ban ban, print the VNC tunnel command — each
  as an idempotent, audited subcommand the agent can be approved to run.
  On in `maximum`.

The maximum profile is therefore the minimum **plus** fail2ban, the
loopback VNC path (GUI permitting), and the managed day-2 helper, reusing
the same single-component shape. All-interface SSH
(`ZOMBIE_REMOTE_SSH_PUBLIC`) and autologin (`ZOMBIE_REMOTE_AUTOLOGIN`) are
**not** part of `maximum`: they are orthogonal, explicitly riskier opt-ins
that stay off in both profiles.

## Behaviour and options

New environment variables (document them all in `docs/CONFIGURATION.md` and
the `usage()` env block in `scripts/install.sh`):

- `ZOMBIE_INSTALL_REMOTE=0|1` — master switch (default `0`). When `1`,
  install and configure the remote-access component. When `0`, the host
  stays loopback-browser-only, exactly as Zombie Zero describes.
- `ZOMBIE_REMOTE_PROFILE=minimum|maximum` — switches the
  fail2ban/VNC/managed-helper sub-flags on together (default `minimum`);
  each remains independently overridable.
- `ZOMBIE_REMOTE_SSH=0|1` — install/harden the SSH server (default `1`
  when the component is on; the SSH surface is the point of the component).
- `SSH_PUBLIC_KEY` — the authorised public key for `agent`. Required in
  non-interactive mode when SSH is on and no key is already authorised
  (exit `64`, exactly as the current "SSH key setup" phase does). Validated
  with the existing `is_ssh_pubkey` helper.
- `ZOMBIE_REMOTE_TAILSCALE=0|1` — install Tailscale and bind inbound SSH to
  `tailscale0` (default `1` when the component is on). When `0`, the
  firewall falls back to the "SSH allowed on every interface" shape, which
  **implies** `ZOMBIE_REMOTE_SSH_PUBLIC` and forces `fail2ban` on.
- `TAILSCALE_AUTHKEY` — auth key for non-interactive `tailscale up`.
  Treated as a secret: never logged, never written to the receipt verbatim
  (set/unset fingerprint only). Must not trip the `tskey-auth-…` scan.
- `ZOMBIE_REMOTE_SSH_PUBLIC=0|1` — **dangerous, default `0`.** Allow SSH on
  every interface instead of restricting it to `tailscale0`. Off in both
  profiles; enabling it is loudly surfaced in the review and receipt, and
  forces `ZOMBIE_REMOTE_FAIL2BAN=1`.
- `ZOMBIE_REMOTE_FAIL2BAN=0|1` — enable brute-force protection (default
  follows the profile; forced on when SSH is exposed on all interfaces).
- `ZOMBIE_REMOTE_VNC=0|1` and `VNC_PASSWORD`, `VNC_PORT` — enable the
  loopback-only x11vnc emergency desktop path (default follows the profile,
  but only when `ZOMBIE_ENABLE_GUI=1`). `VNC_PASSWORD` is required in
  non-interactive mode when VNC is on and no password is stored (exit `64`,
  as today). The password store is the existing `~agent/.vnc/passwd`,
  mode `600`.
- `ZOMBIE_REMOTE_AUTOLOGIN=0|1` — enable the gdm3 autologin companion to
  the VNC path (default `0`, even in `maximum`).
- `ZOMBIE_REMOTE_MANAGED=0|1` — install the `remote-access` day-2 helper
  and register its agent-drivable verbs (default follows the profile).

The component holds **no new operator secrets** beyond the three the
installer already handles (the SSH public key — not itself sensitive — the
Tailscale auth key, and the VNC password). Confirm the CI secret-scan
patterns are not tripped; do not add example keys, auth keys, or passwords
to docs (use placeholders like `ssh-ed25519 AAAA...`, `tskey-auth-...`).

## Non-negotiables to honour (from `AGENTS.md`)

1. **Idempotence.** Every step checks current state first: `authorized_keys`
   is created only when absent (never truncated — preserve the FIX-1-05
   guard), the sshd drop-in is re-rendered in place, `tailscale` presence is
   probed before adding the apt repo, the VNC password store is kept if
   present, and the UFW rules are converged without duplicates (reuse the
   existing add/delete-by-comment logic for the tailnet-only vs
   every-interface SSH rule). Re-running converges with no errors and no
   duplicate rules. Run `sshd -t` before restarting sshd so a bad drop-in
   never replaces a good one.
2. **Non-interactive mode.** `ZOMBIE_NONINTERACTIVE=1` must drive the whole
   optional path from env alone. When SSH is on and `SSH_PUBLIC_KEY` is
   missing with no key already authorised, exit `64`. When VNC is on and
   `VNC_PASSWORD` is missing with no stored password, exit `64`. When the
   component is off, requirements are unchanged (no `SSH_PUBLIC_KEY`/
   `VNC_PASSWORD`/`TAILSCALE_AUTHKEY` demanded) — this is the key
   improvement over the always-on phases, which demand these inputs
   unconditionally today.
3. **Policy gate + audit.** No new privileged behaviour bypasses the gate.
   sshd, tailscaled, and fail2ban run as system services without the agent,
   but anything the chat agent may later be asked to drive — rotating an
   authorised key, `tailscale up`/`logout`, unbanning an address,
   restarting sshd, reading jail status — must be classified in
   `payload/etc/policy.yaml` and described in `docs/ARCHITECTURE.md`. Reads
   (`fail2ban-client status`, `tailscale status`, `sshd -T`, listing keys)
   are a low-risk class; key rotation / `tailscale up` / unban / sshd
   restart / firewall edits are a `system_change` class.
4. **No new runtime deps beyond what the installer installs.** `openssh-server`,
   `fail2ban`, `x11vnc`, and Tailscale (from its official apt repo) are
   installed by the installer **only when the option is on**, which is
   permitted; reuse the existing `apt_install`, `curl_get`/retry,
   `resolve_ubuntu_codename`, and `render_unit` helpers. Do not add
   language-level dependencies.
5. **British/Commonwealth spelling** in code, messages, and docs
   (e.g. "authorise", "enrol", "behaviour", "recognised", "minimise").
6. **Status glyph vocabulary**: messages use `[i]/[+]/[!]/[x]`; checklist
   rows use `[ok]/[!]/[x]/[~]`.

## Implementation steps

### 1. Option parsing and defaults (`scripts/install.sh`)

- Add `ZOMBIE_INSTALL_REMOTE`, `ZOMBIE_REMOTE_PROFILE`, and the
  `ZOMBIE_REMOTE_*` sub-flags to the defaults/derivation block alongside
  the other `ZOMBIE_*` settings, with conservative defaults (`0`, profile
  `minimum`, Tailscale-bound, public off, autologin off). Derive
  `ZOMBIE_REMOTE_FAIL2BAN=1` whenever `ZOMBIE_REMOTE_SSH_PUBLIC=1` or
  Tailscale is off.
- Add validators (a profile enum check; an `is_ssh_pubkey` check on
  `SSH_PUBLIC_KEY`; the "VNC requires the GUI stack" rule; a guard so
  `ZOMBIE_REMOTE_SSH_PUBLIC=1` is only honoured when explicitly set; a
  guard that `VNC_PORT` is a sane port) and wire them into
  `validate_config()` so an invalid value is rejected before any host
  change.
- Extend `validate_noninteractive()` to exit `64` when SSH is on without a
  key (and none authorised), or VNC is on without a password (and none
  stored) — but **only when the component is enabled**, so the default
  off-path stops demanding these inputs.
- Extend `usage()`'s environment-variable section and examples with an
  opt-in remote-access example (interactive and `ZOMBIE_NONINTERACTIVE=1`),
  showing the tailnet-bound default and the riskier all-interface variant.

### 2. Interactive parameter review

- Add a "Remote access" row to `print_parameter_table()` showing
  enabled/disabled and, when enabled, the profile, which sub-surfaces are
  on (SSH / Tailscale / fail2ban / VNC), the SSH binding (tailnet-only vs
  **every interface**, the latter loudly), and the VNC/autologin state.
  Mirror how Tailscale and the proxy plan render. Never print key material,
  the auth key, or the VNC password.
- Add a `_toggle_remote()` editor (with nested SSH/Tailscale/fail2ban/VNC/
  autologin/public editors) and a new menu entry in `review_parameters()`.
  Append as the next index to minimise churn, and update the range hint and
  the "Unrecognised choice" message accordingly. The all-interface-SSH and
  autologin editors must each require an explicit confirmation step.

### 3. Dry-run plan and the "This installer will" banner

- Extend `print_dry_run_plan()` and the pre-flight summary so that, when
  the component is enabled, the plan lists the SSH/Tailscale/firewall/
  fail2ban/VNC steps it will run (and calls out the SSH listening posture);
  when disabled it says nothing — keeping the default output unchanged.

### 4. Install sections (the core work)

Re-introduce the removed phases as **guarded** `section` blocks, each
returning early when its flag is off. The bodies are largely the
*existing* phase code (SSH key setup, Harden SSH, Install Tailscale, the
two Firewall variants, Security services/fail2ban, x11vnc, the autologin
branch of "Force Xorg session"), moved behind the gate rather than
rewritten — preserving every FIX-* guard already in those phases:

- `section "Remote: SSH key setup"` — guarded by `ZOMBIE_REMOTE_SSH`.
  Reuse the current `authorized_keys` create-if-absent + append-once +
  re-assert-mode logic verbatim (keep FIX-1-05).
- `section "Remote: harden SSH"` — render the `99-ubuntu-zombie.conf`
  drop-in, `sshd -t`, enable/restart `ssh`.
- `section "Remote: install Tailscale"` — guarded by
  `ZOMBIE_REMOTE_TAILSCALE`; the existing repo/keyring/`apt_install` +
  `enable --now tailscaled` body.
- `section "Remote: firewall"` — the existing tailnet-only-vs-every-
  interface UFW logic, selected by `ZOMBIE_REMOTE_SSH_PUBLIC`/Tailscale
  state, with the same duplicate-rule guards and the `[!]` warning when
  SSH is opened on all interfaces.
- `section "Remote: brute-force protection"` — guarded by
  `ZOMBIE_REMOTE_FAIL2BAN`; `enable --now fail2ban`. (Leave the existing
  unattended-upgrades behaviour where it is; that is not part of the remote
  surface and should not move under this gate.)
- `section "Remote: emergency desktop access (x11vnc)"` — guarded by
  `ZOMBIE_REMOTE_VNC` **and** `ZOMBIE_ENABLE_GUI`; the existing password
  store + loopback autostart entry. Skip with a `[~]` and a clear message
  when the GUI stack is absent.
- Fold the **autologin** branch into the existing "Force Xorg session"
  handling but drive it from `ZOMBIE_REMOTE_AUTOLOGIN` (superseding the old
  `ZOMBIE_ENABLE_AUTOLOGIN`, with a back-compat alias documented in
  `CHANGELOG.md`).
- `section "Remote: Tailscale authentication"` — guarded by
  `ZOMBIE_REMOTE_TAILSCALE`; the existing `tailscale up` enrolment using
  `TAILSCALE_AUTHKEY` (or the interactive login URL), never echoing the
  key.

Place these after the workspace/runtime sections and before the
verification/first-run sections, matching the current ordering so nothing
downstream is surprised.

### 5. Day-2 helper and systemd (`payload/bin/`, `payload/systemd/`)

- When `ZOMBIE_REMOTE_MANAGED=1`, deploy a `payload/bin/remote-access`
  helper (bash, `#!/usr/bin/env bash`, `set -Eeuo pipefail`,
  ShellCheck-clean, sourcing `scripts/lib.sh` conventions) with idempotent,
  best-effort (`|| true`-guarded) subcommands: `add-key`, `rotate-key`,
  `status` (sshd + tailnet + jails), `bans`, `unban`, `tunnel` (print the
  exact VNC SSH-tunnel command). No new long-running unit is required —
  sshd, tailscaled, and fail2ban use their own distribution units; do not
  add a bespoke service.

### 6. Verification, doctor, repair

- Extend `cmd_verify()` / the `check` helper to add remote checks (only
  when enabled): sshd present, active, and **key-only**
  (`sshd -T | grep passwordauthentication no`); the listener restricted to
  `tailscale0` unless `ZOMBIE_REMOTE_SSH_PUBLIC=1`; Tailscale up and
  reporting an IP; fail2ban active with the sshd jail; the VNC listener on
  `127.0.0.1` and **not** a routable interface. Use `[ok]/[!]/[x]/[~]`
  glyphs and JSON records.
- Extend `cmd_doctor()` with likely-fix guidance: sshd refusing
  connections (bad drop-in → `sshd -t`), a tailnet node logged out or
  key-expired, a self-inflicted fail2ban ban (how to unban), a VNC listener
  that drifted off loopback, and an accidental all-interface SSH bind.
- Extend `cmd_repair()` to re-render the sshd drop-in (validate before
  restart), re-assert `~agent/.ssh` ownership/modes, re-add a missing UFW
  rule, re-enable a stopped service, and re-assert the VNC autostart entry
  — never to delete an operator's authorised keys or VNC password.

### 7. Receipt

- Record the remote selection, profile, which sub-surfaces are on, the SSH
  binding posture (with the **all-interface flag prominently**), and the
  VNC/autologin state in `write_receipt_start`/`write_receipt_finish`.
  Record `SSH_PUBLIC_KEY` as a present/fingerprint only, and
  `TAILSCALE_AUTHKEY`/`VNC_PASSWORD` strictly as set/unset — never the
  values.

### 8. Uninstall (`scripts/uninstall.sh`)

- Reverse everything the component created, gated so a baseline-only
  install is untouched: remove the sshd drop-in and (optionally) the
  package, `tailscale logout` + remove the repo/daemon, disable fail2ban,
  remove the VNC autostart entry, and revert the autologin keys in
  `custom.conf`. Removal of the operator's **authorised keys**, the VNC
  **password store**, and tailnet **node state** is operator data: clear it
  only behind the destructive confirmation phrase, never as the default
  path.

### 9. Policy and docs

- `payload/etc/policy.yaml`: add the read-only verbs
  (`fail2ban-client status`, `tailscale status`, `sshd -T`, key listing) at
  a low-risk class and the `system_change` verbs (key rotation,
  `tailscale up`/`logout`, `fail2ban-client unban`, `systemctl restart ssh`,
  UFW edits) at the `system_change` class; describe both in
  `docs/ARCHITECTURE.md`.
- `docs/CONFIGURATION.md`: document every new env var, the off-by-default
  posture, the tailnet-bound-by-default SSH model, and the dangerous
  `ZOMBIE_REMOTE_SSH_PUBLIC`/`ZOMBIE_REMOTE_AUTOLOGIN` opt-ins.
- `docs/ARCHITECTURE.md`: describe the optional remote-access component, its
  trust boundary (one tailnet-bound door by default; backends stay on
  loopback), how it relates to the Zombie Zero analysis (it is the explicit
  re-introduction of what that document removes), and the new policy
  entries.
- `README.md`: note the optional component, the new flags, and the
  `remote-access` helper subcommands.
- `CHANGELOG.md`: add an entry under the unreleased section (including the
  `ZOMBIE_ENABLE_AUTOLOGIN` → `ZOMBIE_REMOTE_AUTOLOGIN` rename/alias); then
  bump `VERSION` with `date -u +%Y.%m.%d.%H.%M.%S > VERSION`.

### 10. Tests (`tests/smoke.sh`)

Non-root, no-network static checks only:

- Assert the new env vars appear in `usage()`/help and that the installer
  parses `--dry-run` with `ZOMBIE_INSTALL_REMOTE=1` (and a dummy
  `SSH_PUBLIC_KEY`) without touching the host (extend the existing
  `noninteractive`/`subcommands` cases).
- Assert that `ZOMBIE_INSTALL_REMOTE=1` with SSH on and no `SSH_PUBLIC_KEY`
  under `ZOMBIE_NONINTERACTIVE=1` exits `64`, and likewise VNC-on without
  `VNC_PASSWORD`.
- Assert that with `ZOMBIE_INSTALL_REMOTE=0` (the default) the installer no
  longer demands `SSH_PUBLIC_KEY`/`VNC_PASSWORD`/`TAILSCALE_AUTHKEY` — the
  Zombie Zero default path.
- Add a "standards" assertion that the new section names and the
  `remote-access` helper exist, that the default SSH binding is
  tailnet-only unless the public flag is set, and that British spelling /
  status glyphs are respected.

## Validation before hand-off

- `make lint` (shellcheck `--severity=warning`, `bash -n`, python compile)
  clean — including the new `payload/bin/remote-access` helper.
- `make test` (`tests/smoke.sh all`) clean.
- `make package` still produces the tarball.
- Re-check idempotence and the `ZOMBIE_NONINTERACTIVE=1` path for the new
  option by reasoning through each guarded section, especially the
  `authorized_keys` create-if-absent guard, the `sshd -t`-before-restart
  guard, and the no-duplicate-UFW-rule guards.
- Confirm no secrets, screenshots, or local state are staged, and the CI
  secret-scan patterns (`sk-…`, `sk-ant-…`, `tskey-auth-…`) are not tripped.

## Out of scope / risks

- **Do not** run the installer, `make install-local`, or any
  `/opt/ai-zombie/` helper in the agent environment — these mutate a real
  host, open listening services, and contact the live Tailscale control
  plane. All verification here is static (`lint`/`test`/`package`) plus
  dry-run reasoning. End-to-end SSH/Tailscale/VNC behaviour must be
  validated by a human on a disposable Ubuntu Desktop LTS VM.
- **All-interface SSH is the sharp edge.** The default is tailnet-only.
  `ZOMBIE_REMOTE_SSH_PUBLIC` is an explicit, loudly flagged opt-in that
  forces fail2ban on; binding SSH to every interface is the single riskiest
  thing this component does and must never be the default, never be implied
  by `maximum`, and be obvious in the review and receipt. This is exactly
  the surface Zombie Zero removes; re-opening it must be a conscious act.
- **Autologin weakens at-console security.** It returns a rebooted box to a
  logged-in desktop without a passphrase; keep it off in both profiles and
  behind its own confirmation.
- **VNC is emergency access, not a remote desktop product.** It stays
  loopback-only over an SSH tunnel; never bind it to the network, and never
  re-introduce it without the GUI stack present.
- **This re-introduces a revocation surface.** With SSH/Tailscale back, the
  kill switch regains its "remove the key / disable Tailscale" steps — the
  `remote-access` helper and policy verbs exist precisely so that
  revocation stays a one-command, audited action rather than remembered
  surgery.
- **No fleet networking.** This is remote access *to this one machine* for
  *its one operator*; mesh routing, subnet routers, exit nodes, or managing
  *other* hosts' access is fleet networking and breaks the one-machine
  boundary in [`brainstorm.md`](brainstorm.md).
