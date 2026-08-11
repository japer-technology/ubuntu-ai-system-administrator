# Install enhancement 1 — making the install procedure more beautiful

This note collects ideas for making the Ubuntu Zombie install
*experience* more beautiful, taking inspiration from two projects with
polished agent-onboarding flows:

- **OpenClaw** — <https://github.com/openclaw/openclaw> — a personal AI
  assistant whose recommended setup is an interactive `openclaw onboard`
  wizard that "guides you step by step through setting up the gateway,
  workspace, channels, and skills", plus a native **Windows Hub**
  companion app with tray status, chat, and setup.
- **Hermes Agent** — <https://github.com/NousResearch/hermes-agent> — a
  self-improving agent with "a real terminal interface": a full TUI with
  multiline editing, slash-command autocomplete, conversation history,
  interrupt-and-redirect, streaming tool output, and a banner image in
  the README.

The scope here is deliberately narrow: the *look, feel, and flow* of
installing Ubuntu Zombie, in the existing single-script installer
(`scripts/install.sh` + the shared `scripts/lib.sh`). Nothing below
should weaken the trust model, idempotence, the
`ZOMBIE_NONINTERACTIVE=1` path, the policy gate, or the audit log (see
`AGENTS.md`).

This is an analysis document, not a change. Treat it as input for a
later, focused implementation.

## What we already have

The installer is already far from a bare `apt install` wall of text.
Worth stating plainly so we build on it rather than re-inventing it:

- **Brand splash and wordmark.** `brand_splash` /`brand_wordmark` in
  `scripts/lib.sh` print an ANSI-Shadow "UBUNTU ZOMBIE" wordmark inside a
  rounded panel, in the Zombie Orchid palette (`C_BRAND` `#AC43D9` and
  friends).
- **A real palette and status vocabulary.** Truecolor brand colours that
  degrade cleanly, plus a unified glyph set (`[i] [+] [!] [x]`, and
  `[ok]/[!]/[x]/[~]` for checklist rows) via `info/ok/warn/die/status`.
- **Numbered phases with timing.** `section()` numbers each phase
  `[n/total]`, writes a breadcrumb to a step log, and reports how long
  the previous step took.
- **A spinner/heartbeat.** `run_step` shows a braille spinner with
  elapsed time for long, otherwise-silent steps, and degrades to a plain
  run off a TTY.
- **An interactive parameter review.** `review_parameters` /
  `print_parameter_table` show every setting and let the operator edit
  fields before any host change.
- **A dry-run plan.** `install --dry-run` previews the plan with no
  changes.
- **A human-readable receipt.** `write_receipt_*` records a
  start/finish/fail record (secrets excluded).
- **A first-run status, `verify`, and `doctor`.** The run ends with a
  status summary and offers read-only checks and failure explanations.

So the gap is not "we have no polish". It is that the polish is uneven,
stops at the terminal edge, and does not yet feel like a single,
guided *wizard* the way `openclaw onboard` does, nor does it offer the
"app-like" entry point that OpenClaw's Windows Hub and Hermes' README
banner give first-time users.

## Where OpenClaw and Hermes set a higher bar

- **A named, guided onboarding verb.** OpenClaw's headline path is one
  memorable command — `openclaw onboard` — explicitly framed as a
  step-by-step wizard. Ours is `install` with an embedded review; the
  wizard framing is implicit.
- **A genuine TUI feel.** Hermes leans on a full-screen terminal UI with
  autocomplete and streaming output. Ours is line-oriented printf, which
  is robust and scriptable but reads as a log, not an interface.
- **A first-class visual identity in the docs.** Both lead with a banner
  image and shields (CI, release, licence, Discord). Our README leads
  with text; the wordmark only appears once the installer runs.
- **A companion/"app" entry point.** OpenClaw's Windows Hub gives a
  native, trayed setup surface. We have nothing equivalent — the desktop
  is the product, yet setup is terminal-only.

## Enhancement ideas (terminal / existing script)

Ordered roughly by value-to-effort. All of these live in
`scripts/install.sh` and `scripts/lib.sh`, keep the
`ZOMBIE_NONINTERACTIVE=1` path untouched, and respect the
`ZOMBIE_COLOR`/`NO_COLOR` policy.

### 1. Frame the install as a named wizard

Re-present the interactive flow as an explicit, OpenClaw-style wizard:
a short "Welcome" panel after the splash that states the few decisions
the operator is about to make (identity, network, desktop access,
model), a numbered set of steps, and a closing "You're set up" panel
that mirrors the welcome. The mechanics already exist
(`review_parameters`, the phase counter); this is about narrative and
consistent framing, not new privileged behaviour. Optionally add a
`setup`/`onboard` *alias* for `install` so the memorable verb exists,
documented alongside the existing subcommands in `README.md` and the
`subcommands` case in `tests/smoke.sh`.

### 2. A persistent progress header / phase tracker

Today each phase prints a banner and scrolls away. Borrow the TUI sense
of place: when on a TTY, render a compact phase tracker that shows the
whole journey at a glance — completed phases ticked, the current one
highlighted, the rest dimmed — using the existing
`ZOMBIE_PHASE`/`ZOMBIE_PHASE_TOTAL` counters and the brand palette.
Keep it as scrolling output (no cursor save/restore gymnastics) so it
stays robust; degrade to the current banners off a TTY or under
`ZOMBIE_QUIET`.

### 3. An overall progress bar and ETA

`section()` already knows the phase number and total and times each
step. Add a single brand-coloured progress bar (e.g. a Unicode block
bar) plus a running ETA derived from elapsed phases. This is the single
biggest "feels polished" win for a 10–20 minute install, and it reuses
data we already compute.

### 4. Richer, friendlier parameter review

The review table is functional. Make it beautiful and clearer:

- Group fields into sections (Identity, Network & access, Desktop,
  Model, Logging) with `brand_rule` separators.
- Show a one-line "why this matters" hint per field, dimmed.
- Mark which values are defaults vs operator-edited vs
  required-but-unset, using the status palette.
- Offer named edit targets (e.g. `edit port`) in addition to the
  numeric `[1-13]` menu, closer to autocomplete ergonomics.

### 5. Streaming, legible long-step output

`run_step` hides noisy output behind a spinner, which is great, but a
failure then needs the transcript. Borrow Hermes' "streaming tool
output": for the longest steps (venv + Playwright/Chromium, Docker,
Node bridge), show the last one or two lines of live output beneath the
spinner so progress is visible without drowning the console. Keep the
full detail in the transcript as today.

### 6. A beautiful final summary card

The first-run status is informative but list-shaped. Add a closing
"summary card" panel (same rounded-panel style as `brand_splash`) with:
the chat URL, the kill-switch reminder, total duration, steps applied vs
already-satisfied, and the single most useful next command. This is the
emotional payoff of the install and currently underplayed.

### 7. Optional QR code for the chat URL / SSH access

A small, dependency-free ASCII QR for `http://127.0.0.1:7878` (or the
Tailscale address) makes "now open the chat" feel finished and modern,
the way good device-setup flows do. Must be optional and behind a flag
so it never blocks the non-interactive path, and must not add a runtime
dependency the installer does not already install (standard tooling or a
tiny vendored generator only).

### 8. Consistent "press to continue" pacing on a TTY

A wizard breathes between phases. On an interactive TTY only, allow a
brief, skippable pause at major milestones (e.g. after identity, after
network) so the operator can read the panel. Auto-skip entirely under
`--yes`, `ZOMBIE_NONINTERACTIVE=1`, or a non-TTY so automation is never
affected.

## Enhancement ideas (beyond the terminal — the "Hermes/OpenClaw app" feel)

These are larger and explicitly out of scope for a first pass, recorded
so the direction is captured. Each must preserve the loopback-only,
operator-holds-the-kill-switch trust model.

### A. A README banner and badges

Cheapest "beautiful installer" win of all and entirely outside the
trust model: lead `README.md` with a brand banner image (we already
ship `LOGO.png`) and a row of shields (CI, release, licence) the way
both reference projects do. Pure docs; no install behaviour changes.

### B. A browser-based setup view served by the existing chat service

Ubuntu Zombie already ships a loopback chat UI. A small, loopback-only
"Setup / health" page — reusing the existing brand styling and the
`verify`/status JSON the installer already produces — would give an
OpenClaw-Hub-like graphical surface *without* opening any new network
surface. This is a natural home for the post-install summary card, the
audit-log link, and the kill switch.

### C. A desktop launcher / first-run greeter

Since the product *is* the desktop, a `.desktop` launcher (or a one-shot
first-login greeter) that opens the chat UI and shows status would echo
OpenClaw's Windows Hub tray entry in spirit, on the platform we actually
target.

## Guardrails for any implementation

Whoever picks this up must keep all of the following true (see
`AGENTS.md`):

- **Idempotence.** No new file/user/service/rule creation without a
  state check first.
- **Non-interactive parity.** `ZOMBIE_NONINTERACTIVE=1` (with
  `SSH_PUBLIC_KEY`/`VNC_PASSWORD` where needed) must still run
  end-to-end; every animation, pause, prompt, or panel must auto-skip
  off a TTY, under `ZOMBIE_QUIET`, and in non-interactive mode. Missing
  required env still exits `64`.
- **Colour policy.** Everything routes through `lib_setup_colors` and
  honours `ZOMBIE_COLOR`/`NO_COLOR`; no raw ANSI that ignores the gate.
- **No new runtime dependencies** beyond what the installer already
  installs; standard library / standard tooling only. A QR helper, if
  added, must be vendored or built from what is already present.
- **Trust model intact.** No new network surface, no privileged action
  outside the policy gate (`payload/agent/policy.py`) and audit log
  (`payload/agent/audit.py`), no secrets printed or written to the
  receipt.
- **British/Commonwealth spelling** in all new strings and docs
  (colour, behaviour, authorise, …).
- **Validate.** `make lint` and `make test` must stay clean; extend
  `tests/smoke.sh` for any new subcommand or alias.

## Suggested first slice

If only one change ships first, do **§3 (progress bar + ETA)** plus
**§6 (final summary card)**: together they deliver the largest
perceived-beauty jump, reuse data the installer already has, touch only
`scripts/install.sh`/`scripts/lib.sh`, and carry essentially no trust-
model risk. **§A (README banner + badges)** is a free parallel win in
docs.
