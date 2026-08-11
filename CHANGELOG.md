# Changelog

All notable changes to Ubuntu Zombie are documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and the project uses **date-time versioning**: each release is stamped
with its UTC release time as `yyyy.mm.dd.hh.nn.ss`.

## [Unreleased]

### Independent Forgejo product

- **Complete server extraction:** added `products/forgejo/` with an independent
  descriptor, version, lifecycle, package, signed-release workflow, guarded
  disposable-VM harness, audit/receipt boundary, tests, and operator
  documentation.
- **Preserved infrastructure boundary:** retained PostgreSQL, the `git`
  identity, loopback port 3000, Caddy internal-CA HTTPS, Avahi discovery,
  host certificate trust, protected recovery secrets, service hardening, and
  ownership-safe adoption.
- **Delegating compatibility targets:** root install, verify, doctor, repair,
  and uninstall targets delegate Forgejo server work to the product. The
  not-yet-extracted runner remains a dependent compatibility component.
- **Correct same-host runner path:** job containers retain host networking and
  restricted Docker settings while gaining deterministic `.local` resolution,
  a read-only host CA bundle, and Git, OpenSSL, Python, and Node trust
  variables. Server mutations stop and restore an active runner only across
  health-gated operations, and server removal refuses an installed runner.

### Independent Beep product

- **Complete standalone implementation:** added `products/beep/` as an
  independently installed, root-capable functional duplicate of Ubuntu Zombie
  with Beep-owned identity, credentials, lifecycle, policy, approval, audit,
  chat, history, provider, tool, and family-manager boundaries.
- **Terminal and recoverable lifecycle:** added strict fail-closed TTL state,
  approved terminal kill, collision and integrity checks, idempotent
  convergence, automatic recovery-snapshot rollback, protected backup and
  restore, and ownership-safe retention and purge.
- **Hardened local runtime:** constrained loopback HTTP Host and mutation
  origin, bounded and strictly validated JSON, isolated sessions,
  confirmation-bound deletion, authenticated export, destructive handling for
  malformed policy, and correlated manager/target failure evidence.
- **Independent assurance and release:** added unit, integration, parity,
  family, and guarded disposable-VM suites; complete product-owned
  documentation; package and provenance records; and a pinned, signed Beep
  release workflow. Production family admission, recorded supported-VM and
  co-installation runs, external security review, and published-release
  verification remain explicit open gates.

### Independent Llama product

- **Complete product extraction:** added `products/llama/` with an independent
  descriptor, version, lifecycle, package, signed-release workflow, guarded
  disposable-VM harness, tests, catalogues, audit/receipt boundary, and
  operator documentation.
- **Delegating compatibility targets:** `install`, `verify`, `doctor`,
  `repair`, and `uninstall llama` now invoke the product-owned lifecycle.
  Duplicate root Llama runtime, model catalogue, service, manager, installation,
  and removal implementations were removed while preserving existing paths,
  identity, API, and automation inputs.
- **Safe migration and removal:** exact supported legacy installations can be
  adopted or removed only after their markers, identity, configuration, unit,
  runtime, and model checksum validate. Safe removal retains model state;
  complete deletion requires the product's explicit destructive confirmation.

### Documentation

- **Complementary AI-agent product definitions:** added ten template-complete,
  documentation-only proposals for code review, household finance, asset
  maintenance, meeting records, adult language practice, photo cataloguing,
  imported-mail drafting, project planning, cognitive accessibility, and
  read-only host telemetry. Each definition fixes an independent namespace,
  least-authority boundary, data and network contract, Ubuntu Zombie lifecycle
  interface, validation plan, threat model, and honest release gate. The
  proposal index does not claim implementation or family admission.
- **Product-defined family authority:** removed the family-wide rule that
  reserved general root authority to Ubuntu Zombie. Future
  systems-administrator products may retain full root capability when their
  definitions justify it and preserve policy, approval, audit, revocation, and
  root-equivalent risk disclosure. Existing Imaginary Friend, Curriculum
  Flame, and ERIC authority boundaries are unchanged.
- **ERIC identity and cognition record:** renamed ERIC to Evolving Record of
  Identity and Cognition and clarified that its primary purpose is to preserve
  an attributable, verifiable history of who a person is, what they know, and
  how they think, rather than merely generating a simulation.
- **Implementation-ready in-repository AI-agent family:** made
  `docs/ai-agent/` authoritative for implementing Imaginary Friend,
  Curriculum Flame, ERIC, and Ubuntu Zombie family management in this
  repository. The new contract fixes product source roots, schemas,
  ownership markers, lifecycle requests/results, receipts, audit
  correlation, secret handling, release identities, CI expectations, and
  dependency order. Each product definition now fixes its first-release
  scope, inputs, identities, services, storage, safety boundaries, and
  deferred features; linked vision and option documents no longer require
  external product repositories or conflicting platform layouts.
- **Complete AI-agent catalogue and God-level management contract:** added
  `docs/ai-agent/` with an Ubuntu-Zombie-first catalogue, complete product
  definitions for Ubuntu Zombie, Imaginary Friend, Curriculum Flame, and
  ERIC, shared installation/update/co-installation contracts, and a
  hand-authored agent template. Ubuntu Zombie is now explicitly the
  root-level family manager: it may orchestrate product-owned lifecycle
  operations under operator approval and dual audit without sharing target
  credentials, data, runtimes, or lifecycle implementations. The existing
  family plan, vision, options index, and documentation indexes now link to
  the extracted definitions. Documentation only; the dedicated family
  inventory and management experience are not yet implemented.
- **ERIC personal continuity agent:** expanded
  `docs/options/ghosts-in-the-machine-plan.md` with ERIC (Evolving
  Record of Identity and Cognition), a lifelong AI apprentice for
  one consenting person. The plan separates source evidence from
  inference, requires provenance on every response, preserves beliefs and
  decisions over time, splits the Twin, Evidence Vault, Executor,
  Guardians, and Constitution, and defines consent, posthumous,
  co-installation, validation, legal, grief, and misrepresentation
  boundaries. Documentation only; no behaviour changes.
- **Independent AI-agent family plan:** revised
  `docs/options/ghosts-in-the-machine-plan.md` to record the decision that
  Ubuntu Zombie is the first of a wider family and its designated manager.
  Family members are separate products with product-owned installers, updates,
  runtimes, policies, passwords and other credentials, state, audit trails,
  tests, documentation, releases, and purpose-defined authority. The plan
  replaces the shared ghost registry and capability-tier proposal with a
  copy-separate-improve process, independent update requirements,
  co-installation boundaries, and cross-product credential-isolation tests.
  Documentation only; no behaviour changes.

### Installer setting preservation

- **Configured models suppress discovery:** interactive reinstalls no longer
  scan the LAN for a local LLM when `ZOMBIE_MODEL` or a provider-specific model
  override is already set in the install environment or existing
  `secrets/env`.
- **Lifecycle state survives reinstalls:** valid TTL state is preserved,
  including extensions and dead tombstones, instead of being reset to the
  install default. Browser-local branding, prompt, and width preferences and
  SQLite-backed reactivation settings remain untouched.

### Forgejo runner component target

- **Direct runner installation:** `install forgejo-runner` now selects the
  required Forgejo server dependency and installs the existing restricted,
  checksum-verified Actions runner without selecting the zombie account or
  runtime. The target has dedicated dry-run, receipt, manifest, verification,
  doctor, repair, uninstall, and shell-completion support.
- **Legacy automation preserved:** `ZOMBIE_INSTALL_FORGEJO_RUNNER=1` remains
  additive and resolves through the same component lifecycle.

### Forgejo runner convergence

- **Safe same-host runner defaults:** co-located runners now load a managed,
  root-owned configuration with one-job capacity, host networking for the
  loopback Forgejo callback path, privileged containers and arbitrary volumes
  disabled, no Docker socket mounted into jobs, and the all-interface cache
  proxy disabled. The systemd unit requires both Docker and Forgejo and
  explicitly loads that configuration.
- **Runner readiness verification:** installation now rejects empty
  registrations and fails unless the current service invocation declares to
  Forgejo. Verify and doctor also check registration, protected config,
  exact effective service arguments, unit and boot state, Docker
  service/group access, and the current declaration. Re-runs preserve runner
  intent from the component manifest or installed artifacts.
- **Fail-closed lifecycle repair:** all Forgejo lifecycle helpers are defined
  before early subcommand dispatch, protected files are reported as
  uninspectable rather than missing for non-root diagnostics, and install and
  repair refuse to reconstruct Forgejo when `app.ini` is missing, empty, or
  lacks the preserved database password or security secrets.
- **Systemd override convergence:** the exact obsolete runner
  `override.conf` from the documented repair is removed automatically;
  other drop-ins are preserved and reported instead of silently overriding
  the managed unit.

### Installer dependencies

- **Earendil modules now track npm `latest`:** every install and repair
  resolves the newest `@earendil-works/pi-ai` and
  `@earendil-works/pi-coding-agent` releases, verifies each
  registry-provided integrity hash, installs the tarballs with lifecycle
  scripts disabled, and records the resolved versions for `/version` and
  the deployed health check.

### Agent replies

- **Post-tool answers are no longer dropped:** the pi-mono bridge now
  recovers the completed assistant message from terminal `turn_end` and
  `agent_end` snapshots when an OpenAI-compatible provider omits the final
  `message_end` event after tool use.

### Agent reactivation debugging

- **Reactivation reset:** `/reactivation reset` now restores the enabled
  5-second/1-hour defaults, cancels queued and active continuations, clears
  stale current-status UX, and restarts chain numbering without deleting
  historical timer rows, transcript events, or audit evidence.
- **Chains no longer break on reply formatting:** structured
  `<ubuntu-zombie-reactivation>` requests are now recognised wherever
  they appear in a reply — followed by a closing sentence, wrapped in a
  code fence, or emitted more than once (the last one wins) — instead of
  only when the block is the very last thing in the message. Every block
  is removed from the visible answer, and a fence left empty by the
  removal is cleaned up. Minor JSON slips such as a surrounding fence,
  single-quoted strings, and trailing commas are also accepted.
- **Unwrapped request recovery:** a provider that forgets the
  `<ubuntu-zombie-reactivation>` wrapper but emits a bare top-level JSON
  object with exactly the `timer.reactivation` fields no longer leaks
  that payload into the visible reply; the server consumes the last such
  object and schedules (or rejects) it through the normal policy path.
  Ordinary JSON examples with extra or missing keys remain untouched.
- **Five-second continuation floor:** the hard/default minimum reactivation
  delay is now 5 seconds (existing databases migrate 1-second defaults and
  lower custom values safely). Chained continuations no longer fire on a
  1-second cadence that could leave the browser still settling the previous
  live turn when the next one started.
- **Immediate queued-state rendering:** the terminal `turn_done` payload now
  carries the canonical reactivation outcome (`accepted`, `replaced`, or the
  rejection reason), and the chat renders the queued banner from that frame
  immediately instead of waiting for the next `/api/reactivation` poll.
- **Verbose reactivation accounting:** browser activity statistics now
  count fired reactivations and report them in verbose turn and session
  summaries.
- **No overlapping continuation turns:** the timer daemon re-reads the
  durable record after sleeping and refuses to claim a timer whose
  conversation still has a turn in flight, closing a race where a timer
  that came due exactly as the daemon woke skipped the busy check and
  started a second concurrent turn. Deferrals are audited as
  `reactivation_deferred`.
- **Visible failures:** a continuation the daemon refuses to run (TTL
  expired, capability disabled, conversation gone, turn could not start)
  is now written to the conversation as a system message and history
  event as well as the audit log, and a continuation turn that fails
  inside itself is audited as `reactivation_turn_failed`.
- **Last-outcome reporting:** `/api/reactivation` returns the most
  recent terminal timer, `/reactivation` prints it, and the chat banner
  keeps a stopped chain's reason on screen. Fired continuations record a
  `chain_index` and are labelled `continuation N` in chat, so "it stops
  after three" is diagnosable from the transcript and the audit log.

### Read-only web access

- **New `web.fetch` tool:** the closed registry gains a `read_only`
  outbound fetch so the agent can check an upstream version or read
  documentation before advising a change. It accepts `GET`/`HEAD` on
  `http`/`https` URLs only, refuses embedded credentials, and refuses
  hosts that resolve to loopback, link-local or private addresses — on
  the first request and on every redirect hop — so an auto-approved
  fetch cannot reach the loopback chat service, the LAN or a cloud
  metadata endpoint. Bodies are truncated (64 KiB default, 1 MiB
  ceiling) and every request URL is audited. There is no request body,
  so local files and secrets cannot leave through it.
- **Prompt guidance:** the system prompt now states that read-only
  internet lookups are allowed and expected, and reinforces that the
  internet is for reading — no shipping local files, environment or
  credentials outward, and no `curl … | bash`.

### Built-in skills

- **Fourth wave — five more briefs, catalogue at 43:** the catalogue
  now also covers `services` (unit dependency analysis, startup
  ordering, health trends from the journal, and coordinated
  bottom-up restarts and reconfigurations), `packages` (cross-format
  package health spanning deb/snap/flatpak — broken and unmet
  dependencies, repository and mirror hygiene, holds/pins/downgrades
  and routine cleanup), `process` (per-process and process-tree
  monitoring, attributing resource spikes to the owning tree or unit,
  and safe containment or termination of runaway, defunct and
  unresponsive processes), `certificates` (TLS certificate
  lifecycle, chain and expiry diagnosis, trust stores and renewal
  without disabling verification) and `reactivation` (using the
  one-shot `timer.reactivation` continuation transparently: honest
  reasons and prompts, bounded chains, respecting operator
  cancellation, and deferring recurring work to host timers). The
  `backup` brief is enhanced
  with orchestration ordering for database-plus-file runs, rotation
  and retention policy (`borg prune`/`restic forget` with dry-run
  first), restore rehearsal into scratch locations, integrity checks
  and 3-2-1 reporting. The `systemd`, `apt`, `snap` and `performance`
  briefs gained cross-references so a prompt lands on the narrowest
  brief.
- **Management catalogue expansion:** new focused briefs cover coordinated
  Ubuntu maintenance, general AI-agent orchestration, and safe operation of
  Hermes, OpenClaw and Ubuntu Zombie's embedded pi-mono runtime. The existing
  `dev` and `files` briefs now add repository-aware programming workflows,
  metadata-preserving atomic file changes and safer bulk operations. Smoke
  tests verify discovery, unique triggers, representative selection and
  package/deployment coverage for all 38 built-ins.
- **Third wave — eleven more briefs:** the catalogue now also covers
  `css`, `database`, `dev`, `forgejo`, `git`, `html`, `json`, `llm`,
  `secrets`, `sql` and `virtualization`. These close the gaps an
  Ubuntu Desktop operator hits next — working copies and history
  rewrites, language toolchains that must not be installed into the
  system interpreter, hypervisors and guest disks, database servers
  and the SQL run against them, JSON/HTML/CSS handling with escaping
  and injection called out, credential handling that confirms presence
  instead of value, and the product's own optional components (the
  Forgejo forge and the local llama.cpp/provider setup). Existing
  briefs gained cross-references so a prompt lands on the narrowest
  one.
- **Second wave — ten more briefs:** on top of the ten below, the
  catalogue now also covers `backup`, `containers`, `hardware`,
  `kernel`, `locale`, `obsidian`, `performance`, `scheduling`, `web`
  and `zram`, so ordinary Ubuntu Desktop administration — snapshots and
  restores, drivers and peripherals, boot and kernel modules,
  time/locale/keyboard settings, container
  runtimes, scheduled work, compressed swap, markdown vaults and
  read-only web lookups — has a brief that names the right tool, the
  policy class the operator will be asked to approve, and the failure
  mode that matters in that domain.
- **First wave — ten briefs:** the shipped catalogue grew from `apt` and
  `systemd` to also cover `desktop`, `disk`, `files`, `journal`,
  `network`, `security`, `snap`, `troubleshoot`, `users` and `zombie`.
  Each brief points the model at the correct typed tool, states the
  policy class the operator will be asked to approve, and restates the
  product invariants that matter in that domain — no new inbound network
  surface, no self-widening of the policy gate, and no disabling of the
  chat service. Skills remain guidance only: the tool registry is
  unchanged and still closed.
- **Unique trigger words:** trigger markers no longer overlap across
  built-in skills, so a prompt loads only the briefs that apply. The
  smoke tests enforce both the catalogue contents and trigger
  uniqueness, and `verify` checks every brief reached
  `/opt/ai-zombie/skills/`.

### Agent reactivation

- **Durable `timer.reactivation`:** pi can schedule one bounded future
  continuation in the same conversation. The authenticated chat shows the
  upcoming request and lets the operator cancel it; `/reactivation` and
  `/reactivate` control durable enablement and delay bounds. Due requests start
  ordinary policy-gated turns, remain subject to TTL, and are fully audited.
- **Agent-initiated continuations:** the shipped pi bridge now gives the model
  a structured, runtime-consumed self-reactivation request instead of exposing
  only the operator controls. Streamed completion frames also omit redundant
  full-history data so long command transcripts do not remain stuck at
  “Finalising the reply”.
- **Shorter reactivation bounds:** continuations may be scheduled from 5 seconds
  up to 1 hour in the future. Existing durable defaults are migrated safely.
- **Preserved-policy compatibility:** installations upgraded from releases
  before `chat_schedule` existed now retain automatic approval for bounded
  reactivations unless the operator explicitly overrides that class.
- **Visible reactivation progress:** queued reactivations now respect
  `/fullwidth`, and firing, processing, and completion appear in the active
  chat. Agent-selected timers prefer the configured minimum delay unless a
  longer wait is specifically needed.
- **Live reactivation turns:** fired continuations now stream into the active
  conversation exactly like operator sends — tools and reply text appear in
  real time instead of only after the turn finishes — so a multi-turn task
  (for example a long essay written across several reactivations) is visibly
  chained. The browser polls reactivation state more tightly while a
  continuation is about to fire or streaming so it attaches early enough to
  show the live activity.
- **Accurate turn completion:** successful streamed turns now finish with
  “Done.” instead of leaving “Finalising the reply…” visible.
- **Controllable reactivation turns:** processing reactivations now always show
  pause and stop controls. Stop terminates the active bridge turn, while pause
  detaches the live view for later resumption. Structured reactivation data is
  hidden from streamed replies and remains available to the server for
  scheduling.

### Agent capacity

- **Long-running local-model turns:** the shipped pi agent now allows up to
  1,000 tool calls (250 elevated) per turn and waits up to 24 hours of
  inactivity. Active turns may run longer because model and tool events reset
  the watchdog. Python, bridge, and browser deadlines are aligned while all
  elevated actions still pass through the policy approval gate.

### Policy gate

- **Fail-closed policy restored:** the shipped `policy.yaml` again defaults
  unknown commands to `destructive`, requires approval for `user_change`,
  and no longer escalates every `sudo`/`doas`/`pkexec` invocation — the
  argv-aware classifier strips `sudo` and classifies the target program.
- **Safe `/dev` pseudo-devices:** system-path rules now exclude
  `/dev/null`, `/dev/stdout`, `/dev/stderr`, `/dev/tty` and `/dev/fd/N`,
  so `tee /dev/stderr` and `>/dev/null` stay `read_only`.

### Payload bug fixes

- **No more silent turns after tool use:** a model that ran tools and then
  stopped without saying anything used to end the turn with an empty
  reply, which the transcript renders as nothing at all — tool activity
  followed by silence. The chat service now replaces a blank answer with
  a short note (including how many tools ran) so the turn is always
  visible, records it in history, and audits an `empty_reply` event.
  The browser also keeps whatever text it streamed instead of clearing
  it when the terminal frame carries no reply.
- **Provider errors are no longer masked by a preamble:** when `pi`
  streamed some text ("Let me check…") and then failed, the bridge
  returned the stale preamble as the answer and dropped the error.
  A late error now wins and carries the partial reply with it.
- **Tool argument hardening:** `pkg.query`, `pkg.install`, `svc.status` and
  `svc.control` now reject names that start with `-` and pass `--` before
  operator-supplied arguments, so an option-shaped package or unit name can
  no longer be parsed as an `apt-get`/`dpkg`/`systemctl` flag.
- **Symlink-safe filesystem tools:** `fs.read`, `fs.list`, `fs.write` and
  `shell.run`'s `cwd` now operate on the resolved path they validated
  instead of re-traversing the original one, closing a check/use gap.
- **No process-environment reads:** `fs.read` refuses `/proc/<pid>/environ`,
  which would otherwise hand the chat service's provider API keys back to
  the model under the auto-approved `read_only` class.
- **Policy cache keyed by path:** `load_policy()` no longer returns a cached
  policy from a different file that happens to share a size and mtime.
- **Correct summary truncation:** the local conversation summary no longer
  falls back to the whole transcript when the head fills the message budget.
- **Robust bridge handling:** a non-object JSON reply from the pi-ai bridge
  raises a clean provider error instead of `AttributeError`, a tool callback
  that returns a non-object is reported as a tool error, and the idle
  watchdog no longer counts time spent waiting on operator approval.
- **Stream queue overflow:** emitting an event onto a queue that the SSE
  consumer just drained no longer raises `IndexError`.
- **Anthropic key redaction:** the `sk-ant-` rule now runs before the generic
  `sk-` rule in both the audit redactor and `collect-diagnostics`.

### Chat fixes

- **Disabled turn watchdog is honoured:** `max_turn_seconds: 0` now really
  disables the idle deadline. Because streamed turns always supply an
  operator-stop event, the watchdog thread kept running and killed every
  streamed turn about half a second in with a bogus "timed out after 0s"
  error.
- **Readable system files:** `fs.read` and `fs.list` resolve symlinks
  before checking the allow-list, so `/etc/os-release`, `/etc/localtime`
  and `/etc/resolv.conf` — the most common read-only lookups — no longer
  fail with "outside readable allow-list". Home directories and the
  secrets file remain unreachable.
- **Orphaned tool results render:** a `tool_end` or `pending_approval`
  frame that arrives without its `tool_start` no longer throws
  `ReferenceError` in the browser, which had also prevented the approval
  buttons for that call from being drawn.
- **`/copy` works after streamed replies:** streamed answers are now
  recorded in the visible transcript, so `/copy` no longer reports "No
  assistant response matched that number" for every live turn.
- **`/retry` cannot clobber a live turn:** retrying while a turn is
  streaming is refused with a clear message instead of orphaning the live
  EventSource and the Stop button; starting a stream also closes any
  previous one.
- **Faster `/locals`:** local API discovery pre-checks TCP reachability and
  scans with more workers, cutting a full `/24` sweep from roughly 48
  seconds to a few seconds.

### Chat discovery and layout

- **Tighter verbose tool lines:** each streamed tool line now shows the
  first few words of its arguments inline, the inspector is a bare
  disclosure arrow at the end of the line (labelled "Inspect tool call"
  for assistive technology), and byte counts moved into the
  click-to-expand detail alongside the raw outcome payload.
- **Quieter verbose API accounting:** frequent API request lines (for
  example reactivation polling) are no longer logged or shown by
  default; `/verbose api` toggles API-call display within verbose mode.
- **New `/verbose none`:** suppresses all tool information, including
  tool names in the status line, while approval prompts stay visible.
- **`/load last` and multi-conversation `/load`:** `/load last` opens the
  newest stored conversation, and `/load <id> <id> ...` renders several
  conversations into one transcript in the order given, with the last id
  becoming the active conversation for new messages.
- **New `/purpose` command:** re-shows the welcome starter purpose buttons
  inline in the transcript, so more starter questions can be asked without
  leaving the current conversation.
- **Quiet tool activity by default:** with `/verbose` off, ordinary tool calls,
  results, failures, counters, and live tool status are hidden from the chat
  transcript. `/verbose on` enables tool tracking and detailed transcript
  logging with arguments, policy decisions, outcomes, timings, output sizes,
  and per-turn activity totals. Required approval prompts remain visible in
  both modes, and security audit logging is unchanged.
- **Persistent verbose diagnostics:** `/verbose` now retains statistics and
  previously written activity for the full browser session. Every streamed tool
  execution has an expandable record containing its call identifier,
  arguments, policy metadata, outcome, timing, and output size; API requests
  and turn phases are also recorded without exposing hidden model reasoning.
- **Broader local API discovery:** `/locals` now scans ports `1234`, `8080`,
  `11434`, and `51234` across the local IPv4 `/24` and on loopback, while
  retaining private managed llama.cpp discovery on loopback port `58080`.
- **Consistent transcript layout:** user questions now use the same transcript
  width and offset as assistant responses.
- **Visible conversation output:** the chat transcript now remains visible when
  the welcome panel is hidden after the first message.
- **Persistent full-width display:** `/fullwidth [on|off]` toggles or explicitly
  controls a full-width transcript and composer and remembers the setting in
  the current browser.
- **Readable Markdown tables:** assistant table syntax now renders as
  accessible, high-contrast tables with padded cells, borders, alignment,
  striping, content-sized columns, and horizontal overflow for narrow screens.
- **Readable Markdown math symbols:** common LaTeX-style symbols inside dollar
  delimiters, such as `$\rightarrow$`, now display as mathematical glyphs
  without requiring an online rendering dependency.
- **Deeper command discovery:** a bare `/` shows every command;
  `/help <command>` explains canonical commands and aliases, `/help <pattern*>`
  gives full pages for matches, and `/help all` shows every full help page.
- **Component update visibility:** `/version` reports installed bridge and
  runtime versions and checks fixed GitHub/npm sources for latest releases.
- **Proof-of-life status:** `/status` now probes the configured LLM and reports
  latency, provider/model, host/IP/resources, lifecycle, runtime work, local
  conversation/tool totals, and browser-session activity.
- **Browser-local rebranding:** `/rebrand <title>` rebrands the browser title,
  header, wordmark, login prompt, and tombstone label; `/rebrand` resets them
  to Ubuntu Zombie.
- **Browser-local prompt text:** `/reprompt <placeholder>` replaces and
  remembers the composer placeholder; `/reprompt` restores the default.
- **Compact model status:** the chat header now shows only the active model,
  with its IP address appended when the model server is local.
- **Visible installed version:** the chat footer now shows the Ubuntu Zombie
  version beneath the composer buttons, and the decorative green header dot
  has been removed.
- **Reliable exact slash commands:** exact command names such as
  `/conversations` are selected ahead of longer autocomplete matches and
  submit normally.
- **Reliable slash-command input:** command arguments retain internal
  whitespace, numeric arguments reject malformed values, `/exit` and `/quit`
  now log out as documented, and `//` sends a message beginning with `/`.
- **Working command aliases:** slash-command aliases are now resolved in one
  place before dispatch, so every alias runs its canonical command — including
  `/exit` and `/quit`, which previously reported "Unknown command."

### Documentation

- **Vertical mermaid diagrams everywhere:** every diagram in the docs is
  now a vertical (top-to-bottom) Mermaid diagram. ASCII-art flows in
  `docs/FORGEJO.md`, `docs/ARCHITECTURE.md`,
  `docs/research/REQUIREMENTS.md`, and `docs/analysis/improvements-4.md`
  were converted to `flowchart TD`, and existing horizontal
  (`flowchart LR`) diagrams in `docs/RELEASE-PLAN-123.md`,
  `docs/research/ARCHITECTURE-IDEA.md`, and `payload/README.md` were
  reoriented to `flowchart TD`.
- **Forgejo install guide:** new `docs/FORGEJO.md` documents the
  `install.sh` Forgejo component end to end — the loopback backend +
  Caddy/Avahi LAN HTTPS architecture, every install phase, password
  and secret handling, update/re-run safety gates, files installed,
  lifecycle subcommands, exit codes, and troubleshooting.
  `docs/CONFIGURATION.md` links to it from the Forgejo section.

### Installer and upgrades

- **Upgrades restart the chat service:** re-running `install` in place now
  restarts `ubuntu-zombie-chat.service` after deploying the agent tree instead
  of relying on `enable --now`, which leaves an already-running unit untouched.
  A stale process serving the freshly written `templates/index.html` was the
  cause of the literal `v{{VERSION}}` footer and the blank transcript reported
  after upgrades; the newly deployed `server.py` and UI now run together.

- **Independent PC-wide llama:** `install llama` now installs a pinned,
  checksum-verified CPU llama.cpp runtime and small default model on
  `127.0.0.1:8080`, with an isolated account, paths, systemd unit,
  `llama-manager`, full component lifecycle, and conflict-safe uninstall.
  It does not install or modify the Zombie component.
- **Managed llama discovery:** chat `/locals` now checks loopback ports
  `8080` and `58080` in addition to the configured LAN scan port.

### Dependency updates

- **Current pi agent stack:** updated `@earendil-works/pi-ai` and
  `@earendil-works/pi-coding-agent` from 0.75.5 to 0.80.10 with refreshed
  tarball checksums, and migrated the provider bridge to pi-ai's compatibility
  entrypoint and assistant-message return shape.

### Analysis notes

- **Phase 1 Option A deep analysis:** new
  `docs/analysis/improvements-8-plan-phase-1-option-a.md` analyses
  the best implementation of Phase 1 Option A of the improvements-8
  plan against the pinned pi 0.80.10 upstream contract: `--mode rpc`
  plus a shipped fail-closed mediation extension (gate-in-place),
  an operator-controlled router on/off mode with audited toggling,
  honest per-call telemetry in the chat UX (`/verbose`), a
  server-assembled full-dump `/export` (events, audit slice, bridge
  logs, policy digest), and a docs-truthful-at-every-commit delivery
  sequence. Design analysis only; no behaviour change. The analysis
  index in `docs/analysis/README.md` now lists the document.
- **Mediation diagrams:** new `docs/analysis/mediation-diagrams/`
  folder with vertical Mermaid diagrams — `current-state.md` shows how
  the system works today (installed shape, chat turn transport, the
  shipped unmediated tool path, and the stub-only mediated path), and
  `mediation.md` shows the restored mediation designs from the
  improvements-8 plan (mediated tool-call lifecycle, Option A
  `--mode rpc`, Option B custom tools, tripwire). Design analysis
  only; no behaviour change. The analysis index in
  `docs/analysis/README.md` now lists the folder.
- **Improvements-8 remediation plan:** new
  `docs/analysis/improvements-8-plan.md` turns every finding of the
  external adversarial review (`docs/analysis/improvements-8.md`,
  F1–F12) into a phased implementation plan with work items,
  acceptance criteria, and sequencing — restoring bridge tool
  mediation first, then production-path testing, auth/TTL hardening,
  turn ceilings and durable approvals, structural and supply-chain
  hardening, and documentation/reference integrity. Design analysis
  only; no behaviour change. The analysis index in
  `docs/analysis/README.md` now lists the plan.
- **Windows 11 port plan:** new
  `docs/analysis/improvements-7-windows11-plan.md` analyses what a
  Windows 11 version of Ubuntu Zombie would require — a PowerShell
  sibling installer, Windows-native equivalents for the privileged
  surfaces (hidden local Administrator account, Windows Service,
  Scheduled Task, ACLs, winget), a Windows fail-closed policy rule
  set, a portable-core/per-OS-adapter split of the agent tools, a
  phased implementation plan, and open questions for maintainers.
  Design analysis only; no behaviour change.

### Policy design notes

- **Owner-centric superuser policy draft:** new `docs/policy-new-v2.yaml`
  revises `docs/policy-new.yaml` around the `docs/VISION.md` promise —
  this machine only (fleet/remote tools like `ansible`, `terraform`,
  `kubectl`, `ssh` become destructive), the owner's revocation levers
  (`/opt/ai-zombie`, sudoers, agent units, audit/journal vacuuming)
  cannot be touched without the confirmation phrase, `/home` mutations
  need approval, exposure-expanding services (sshd, VNC, Tailscale,
  `ufw allow`) are destructive, and per-turn budgets are resized for a
  single desktop (24 tool calls / 8 elevated / 900 s idle).

### Promotion kit

- **Promotion copy refresh:** `promotion/**` now matches the shipped
  product — the password-protected loopback chat is described as the
  only network surface (no SSH/VNC/Tailscale claims), local LLM
  support (LM Studio / Ollama / `llama.cpp`) is presented as shipped,
  and the chat password, Time to Live, and `/ttl --die` kill switch
  are covered across messaging, social, community, blog, press,
  email, video, and landing-page drafts.
- **Approved claims matrix:** new `promotion/messaging/KEY-FEATURES.md`
  lists every claim the kit may make with its repository source, plus
  claims that must not be made and feature-drip topics; the kit README
  and launch checklist now reference it.

### Chat provider discovery

- **Runtime local API selection:** `/locals` rescans the local network and
  lists discovered API URLs, marking the active one when found, while
  `/local <url>` switches to a listed API. `/models` lists the active
  provider's available models, and `/status` includes the local API address.
- **Local LM Studio discovery:** `/locals` checks `127.0.0.1` before scanning
  the LAN, so it finds LM Studio's default loopback-only server.
- **Local provider completions repaired:** the pi-ai bridge no longer
  crashes with `Cannot read properties of undefined (reading 'api')`
  when the active provider (e.g. the shipped local `lmstudio`/llama.cpp
  endpoint) or model has no entry in pi-ai's static catalogue. The
  bridge now synthesises a model handle from `~/.pi/agent/models.json`
  and passes the API key explicitly, restoring the `/status`
  connectivity probe and completion calls for local LLM deployments;
  in-band provider errors are surfaced instead of reported as success.

### Phase 4 — Registry generalisation

- **Deep Caddy diagnostics:** Forgejo verify and doctor now check the Caddy
  binary and unit, boot enablement, the exact managed host/port/internal-TLS
  route, configuration validity, legacy fragment cleanup, and whether the
  exported client CA matches Caddy's active local CA root.
- **Forgejo first-install convergence:** fresh Caddy installs discard only
  the packaged port-80 welcome site, Forgejo must recover from its public-URL
  restart before Caddy activates the proxy, and verification accepts the
  health endpoint's successful HTTP status instead of requiring a nonexistent
  `"healthy"` response field.
- **Accurate installer status:** local `lmstudio` credentials now satisfy
  install, doctor, and deployed health checks; prompted Forgejo passwords are
  described as operator-set and not recorded; and discovered model rows no
  longer contain a wide blank label column.
- **Forgejo Caddy installation:** Forgejo installs now configure Caddy's
  official signed stable APT repository before installing the package, so
  hosts no longer require manual Caddy repository setup.
- **Chat command status UX:** live `bash`/shell tool progress now
  labels non-zero command statuses as completed with a non-zero
  status instead of a failed tool execution, matching Linux exit-code
  semantics for probes such as `dpkg -s`, including pi's nested shell
  result metadata.
- **Forgejo Caddy repair:** the machine's `.local` Forgejo route is now
  rendered directly in `/etc/caddy/Caddyfile`, preserving unrelated sites
  while replacing the managed route on repair and migrating legacy route
  fragments.
- **Forgejo LAN HTTPS:** Forgejo now binds only to loopback and is exposed
  at the machine's `.local` name through Avahi discovery and Caddy HTTPS
  using Caddy's internal CA. Install, verify, doctor, repair, receipts,
  summaries, uninstall, and client CA trust documentation cover the full
  lifecycle.
- **Forgejo update safety:** re-runs now detect existing Forgejo and matching
  PostgreSQL state before mutation, require separate exact, capitalized `YES`
  approvals (including explicit environment acknowledgements for unattended
  updates), and state that repositories and database data are preserved.
- **Uninstall hardening:** `uninstall forgejo --yes` now reliably removes the
  Forgejo PostgreSQL database and role when PostgreSQL is present, even after
  Forgejo files are cleaned up, so test hosts can be reset to a clean slate.
- **Verify fallback:** partial legacy zombie installs now report component-aware
  verify failures (including JSON output) instead of aborting when the deployed
  verifier script is missing.
- **Verify and doctor reliability:** lifecycle checks no longer delegate to a
  stale deployed verifier or source shell-sensitive password hashes, preventing
  unbound-variable aborts while preserving text and JSON diagnostics.
- **Validated component registry:** shared selection, validation, review,
  dry-run, receipt, phase counting, install, manifest, final-summary, and
  uninstall paths dispatch trusted component hooks from one ordered
  registry. Missing hooks and invalid dependencies fail before mutation.
- **Registry hardening:** dependencies must be registered before their
  dependants (making dependency cycles unrepresentable), duplicate hook
  fields are rejected instead of silently overwritten, and installing a
  component automatically selects its registered dependencies in registry
  order.
- **Extension contract:** a hermetic sample component proves registration
  and dispatch require no parser changes, and contributor documentation
  now defines one lifecycle contract for future packaging targets.
- **Target-scoped review:** `install zombie` no longer asks about optional
  components; only explicitly selected component pages are shown.

### Phase 3 — Standalone Forgejo

- **Forgejo runner release source:** runner installs now resolve latest
  releases from Forgejo's current metadata host and download binaries from
  Forgejo's canonical release host, with legacy Codeberg fallbacks for pinned
  releases.
- **Forgejo URL canonicalization:** generated Forgejo `DOMAIN` and
  `ROOT_URL` values now lowercase the host name so mixed-case Ubuntu
  hostnames do not trigger Forgejo's canonical URL warning in browsers.
- **Runner Docker compatibility:** Forgejo runner installation now reuses an
  existing Docker Engine instead of forcing Ubuntu's `docker.io` package, and
  fails without changing packages when an orphaned `containerd.io` installation
  would conflict.
- **Standalone Forgejo install:** `install forgejo` now installs
  PostgreSQL, Forgejo, and the optional runner without creating the zombie
  account or deploying its Node/Python runtime, policy, audit, chat, or
  desktop settings.
- **Component hooks:** zombie and Forgejo mutations are isolated behind
  target-aware install hooks, execute in registry order, and write each
  manifest only after that component's install and health path completes.
- **Target-aware experience:** preflight capacity guidance, interactive
  review, dry-run plans, receipts, progress totals, and final summaries
  now include only selected component state. Generated Forgejo passwords
  are disclosed only in the root-only receipt.
- **Compatibility:** no-target `install` remains zombie-only, and
  `ZOMBIE_INSTALL_FORGEJO=1 install` remains equivalent to
  `install zombie forgejo`.

### Phase 2 — Component manifest and selective lifecycle

- **Selective uninstall**: `uninstall zombie` and `uninstall forgejo` now work as
  targeted component removals. No-target `uninstall` retains the previous
  all-managed-artefacts behaviour.
- **Component manifest**: `/var/lib/ubuntu-zombie/components/` records installed
  components. Manifest entries are written only after a successful install and
  health check, and removed only after successful uninstall. Each component's
  entry is retained independently when that component's cleanup fails.
- **Flag isolation**: `--archive` and `--keep-agent` are now rejected (exit 2)
  when the `zombie` component is not being removed.
- **Manifest directory**: Independent of `/opt/ai-zombie` so zombie removal does
  not lose Forgejo's manifest entry.
- **Safe parsing**: Manifest files are parsed as fixed key/value data and never
  sourced. Malformed or unknown entries produce a warning and are skipped.

### Added
- **Component-aware installer grammar (Phase 1).** `scripts/install.sh`
  now accepts `scripts/install.sh <verb> [component ...] [flags]` with
  public `zombie` and `forgejo` targets, while preserving the default
  no-target zombie install and existing `ZOMBIE_INSTALL_FORGEJO`
  automation path. Standalone `install forgejo` remains gated until the
  Phase 3 component extraction work lands. Bash and Zsh completions
  include the component targets.
- **`docs/analysis/improvements-3.md` design analysis.** A written
  recommendation for evolving the installer CLI to component-oriented
  syntax (`install.sh <verb> [component ...]`): keep the five lifecycle
  verbs, add component targets (`zombie`, `forgejo`), support
  standalone Forgejo without the zombie via a shared core layer, a
  component registry, an on-host component manifest, and symmetric
  per-component uninstall. Analysis only — no behaviour change.
- **Live slash-command completion in chat.** Typing `/` now opens an
  accessible, keyboard-navigable command picker that narrows as you type;
  use arrow keys and Tab or Enter to complete a valid command.
- **`/verbose` chat command for background-activity detail.** The chat
  now tallies everything the page can observe moving — HTTP API calls
  with request/response byte sizes, live-stream frames, tool calls and
  failures, bytes of tool stdout/stderr, and streamed reply
  characters — for both the current turn and the whole browser
  session. `/verbose` (or `/verbose on|off`) toggles the detail: when
  on, live tool lines show the policy decision, argument summary,
  duration and output size, and every completed turn — including a
  failed one — ends with a muted "Turn activity" tally that also
  reports elapsed time. Verbose always assumes **off**: it is a
  per-page opt-in and resets on reload. The server's `tool_end` stream
  event now includes `stdout_bytes`/`stderr_bytes` so sizes can be
  reported without shipping full output over the progress stream, and
  the pi-mono bridge's tool progress frames now carry the tool
  arguments, outcome, wall-clock duration and output byte count so
  bridge-executed tools report more than a bare "done".

### Fixed
- **Forgejo installation and upgrades are resilient to config migrations.**
  Forgejo could not migrate its database when it needed to persist a missing,
  malformed, or newly introduced generated setting in the root-owned
  `app.ini`. The installer now validates and preserves JWT secrets, stops an
  existing daemon before migration, permits config writes only for that
  one-shot command, restores restrictive permissions on success or failure,
  creates the admin before startup, and waits for `/api/healthz`.
- **Chat and installer presentation is tighter and clearer.** `/help` is
  now a compact category index, the oversized wordmark is a stable
  responsive sign, installer deployment work is split into focused phases,
  and the final install summary keeps only the next action and essential
  operational paths.
- **Policy file is honoured again.** The minimal YAML reader in
  `payload/agent/policy.py` raised on the first scalar list item
  (e.g. `sudo_allow_list:`) and the loader silently swallowed the
  error, so every `settings:`, `classes:`, `tool_classes:` and
  `agent:` value in `policy.yaml` was discarded in favour of code
  defaults. The parser now converts an opened mapping into a list
  when the block turns out to be a sequence.
- **Policy defaults re-aligned with the documented, tested semantics**
  that the parser bug had been masking: `default_class` is again
  fail-closed at `destructive`, elevated classes (`user_change`,
  `system_change`, `network_change`) require operator approval, and
  the per-turn budgets are 12 tool calls / 3 elevated / 600 s idle —
  matching `docs/CONFIGURATION.md` and the layered-timeout invariant.
- **Destructive `rm` detection matches flag variants.** The rule only
  caught the literal `rm -rf /`; `rm -fr /`, `rm -Rf`, long options
  (`--recursive --force`), option-separated forms, and
  `--no-preserve-root` now classify as `destructive` too.
- **`install.sh uninstall` forwards its flags.** `--dry-run`, `--yes`,
  `--quiet`, and `--no-color` were consumed by the wrapper and never
  reached `uninstall.sh`, so `install.sh uninstall --dry-run`
  performed a **real** uninstall instead of a preview, and
  `--archive`/`--keep-agent` were rejected outright. All six flags now
  reach the uninstaller.
- **Uninstall reverses more of the install.** It now unmasks the
  sleep/suspend/hibernate targets and removes the installer's
  unattended-upgrades auto-reboot policy
  (`/etc/apt/apt.conf.d/52unattended-upgrades-local`); the NodeSource
  apt repository is documented in the "left intact" notice.
- **Chat spinner no longer sticks on session expiry or kill-switch.**
  A streamed turn that hit 401 (login expired) or 410 (zombie dead)
  returned before clearing the "Thinking…" bubble, leaving it — and
  its ticking interval — on screen forever.
- **Markdown links survive emphasis rendering.** URLs containing
  `__`, `**`, or `*` (e.g. `https://example.com/a__b__c`) were being
  rewritten inside the generated `href`, breaking the link; rendered
  links are now stashed behind placeholders like code spans.
- **Stop button feedback is uniform.** Aborting a turn on the
  non-streaming fallback path now resets the composer, refocuses the
  prompt, drains the queued message, and keeps the "Stopped." status
  visible instead of having it instantly blanked.
- **Streaming replies render smoothly.** Live markdown is re-rendered
  at most once per animation frame instead of once per token, removing
  the quadratic re-parse jank on long answers.
- **Live streams survive transient drops.** The server releases a
  turn-stream attachment when the connection breaks so the browser's
  automatic EventSource reconnect can resume it, and the client no
  longer tears down the live view while the source is still
  reconnecting.
- **pi-mono bridge stderr can no longer deadlock a turn.** stderr is
  drained concurrently into a bounded buffer; previously a chatty
  bridge could fill the pipe, stall stdout, and get killed by the idle
  watchdog with a misleading timeout error.
- **Audit previews redact before truncating** so a secret split at the
  preview byte cap can no longer leak a partial token, and
  `collect-diagnostics` now also redacts `tskey-…` values and
  `AUTHKEY=` assignments.
- **`/ttl set 30 s` works.** The lifecycle duration parser stripped
  the plural `s` from the bare seconds unit, rejecting it.
- **New chat answers stay visible and render Markdown while streaming.**
  The transcript now keeps following the active answer when it was already
  at the bottom, while still respecting an operator who deliberately scrolls
  up. Loaded conversations explicitly open at their newest content, and
  streamed assistant text uses the same safe Markdown renderer as the final
  reply instead of showing raw Markdown until completion.
- **Offline installer preflight no longer stalls for 45 seconds.** The
  outbound-connectivity check now makes one bounded HTTP probe before its
  fallback checks instead of using the download helper's exponential retry
  loop.
- **Chat UX hardening after a deep review.** Five browser-side fixes
  in the chat page, all UI-only: a failed turn no longer renders its
  error bubble twice; stopping a streamed turn now disarms the
  client-side turn timeout (a stale timer could previously fire
  minutes later and abort a *newer* in-flight turn); the transcript
  only auto-follows streaming output when the operator is already
  reading the tail, so scrolling up to study earlier output is no
  longer yanked back to the bottom (sending a message still snaps to
  the bottom); a `tool_end` stream frame arriving without its
  matching `tool_start` no longer leaves a consumed activity line in
  the bookkeeping where it could swallow the next result for the same
  tool; and the Approve/Deny buttons on a pending elevated call
  recover from a network failure instead of wedging disabled.
- **No more stray blank lines around tool activity.** An empty live
  activity block no longer reserves vertical space in the assistant
  bubble (it is collapsed until the first tool line arrives), streamed
  replies have their trailing newline trimmed when the live bubble
  settles, and replaying a conversation skips stored messages with no
  content instead of painting empty bubbles. UI only; stored
  transcripts are unchanged.
- **Tool observations no longer paint a stray dark line.** Tool
  output almost always ends with a newline; the transcript's dark
  `<pre>` blocks rendered that trailing newline as an extra empty
  dark line under every bash/tool observation. Trailing whitespace is
  now trimmed and whitespace-only output is skipped (falling back to
  the existing `(no output)` note). UI only; stored transcripts are
  unchanged.

### Changed
- **The chat now feels at home on every screen.** A polished responsive
  shell adds an informative empty state with starter prompts, clearer
  host and provider context, comfortable message bubbles, a growing
  composer with visible keyboard guidance, mobile-friendly controls,
  and light/dark-aware surfaces. Assistant replies have a one-click
  copy action, confirmation fields have explicit labels, errors announce
  themselves to assistive technology, and the Send control visibly
  becomes Queue during an active turn so pointer users can queue a
  follow-up just as keyboard users can.
- **Installer phase timings now read as plain English.** The line
  printed after each install phase is a clean bracketed duration —
  `[35 seconds]` or `[1 minute 5 seconds]` — instead of the cryptic
  `(previous step took 1m05s)`. `fmt_duration` in `scripts/lib.sh`
  now spells out hours/minutes/seconds with correct singular/plural
  forms and omits zero units, so the spinner, install receipt, and
  final "Install took …" summary all use the same friendly format.
- **Live streamed turns now show real activity instead of empty
  boxes.** The chat's live turn view renders one compact activity
  line per tool execution (running → done/failed, updated in place)
  inside the assistant bubble, animated thinking dots until the
  first token arrives, and a status row with a spinner, humanized
  phase labels ("Model is thinking…", "Running tools…"), and an
  elapsed-seconds timer. Previously, mid-turn tool events drew
  proposal/observation boxes with empty argument and result bodies.
  Stopping a turn now freezes the live bubble with a clear notice.
  Transcript rendering also stops emitting contentless fragments:
  empty tool observations say `(no output)`, `exit null` lines are
  suppressed, and empty argument code blocks are omitted. UI only;
  no server or protocol changes.
- **Chat turns now stream live progress and never silently drop busy
  input.** `POST /api/message` keeps its synchronous JSON behaviour but
  also accepts `stream: true`, returning a `turn_id` for the authenticated
  `GET /api/stream/{turn_id}` SSE endpoint. The UI uses `EventSource` to
  show turn phases, best-effort token deltas, live tool activity, and
  pending approvals before the final reply, with automatic fallback to
  the existing reload path if streaming is unavailable. Submitting a
  normal prompt during a running turn now stores one visible queued
  message (replaceable/discardable) and sends it when the current turn
  finishes; slash commands still run immediately.
- **`LOGO-MEANING.md` rewritten for clarity and voice.** The logo
  explainer now opens with a one-line reading, gives each section an
  evocative tagline, and tightens the prose throughout while keeping
  every claim anchored to `README.md`, `docs/VISION.md`, and
  `SECURITY.md`. Documentation only; no behaviour changes.

### Added
- **New research note
  `docs/research/OPEN-WEBUI-LESSONS-PLAN-PHASE-A.md`.** A detailed,
  step-by-step implementation plan for Phase A (liveness plumbing)
  of `docs/research/OPEN-WEBUI-LESSONS-PLAN.md`: SSE streaming of
  tool activity and best-effort token deltas (two-step turn
  protocol, `GET /api/stream/{turn_id}`, bridge `progress`/`token`
  events, client `EventSource` with a poll-once fallback) and a
  client-side one-deep queue so operator input submitted during a
  busy turn is never silently dropped. Includes ground-truth
  analysis of the current turn transport, an event vocabulary,
  sequencing with per-step gates, tests, docs obligations, and
  risks. Linked from `docs/research/README.md`. Documentation only;
  no behaviour changes.
- **New research note `docs/research/OPEN-WEBUI-LESSONS-PLAN.md`.**
  A phased implementation plan that turns the distilled ten-item
  shortlist in `docs/research/OPEN-WEBUI-LESSONS.md` into concrete
  work items grounded in the current codebase — five phases
  (liveness plumbing, input/output ergonomics, continuity, memory
  and hygiene, proactivity and installer work), each naming touch
  points, design, policy/audit obligations, tests, docs, and an
  acceptance check, plus cross-cutting guardrails and open
  questions to settle before work starts. Linked from
  `docs/research/README.md`. Documentation only; no behaviour
  changes.
- **New research note `docs/research/OPEN-WEBUI-LESSONS.md`.**
  A companion to `OPEN-WEBUI-POSSIBILITIES.md` that distils the
  study into lessons for Zombie's local chat — the operator's only
  interface — grouped into perceived liveness (SSE streaming,
  rendering), context ergonomics (`#` injection, curated skills,
  auto-compaction), continuity (machine memory, FTS + tags,
  audit-grounded export), proactivity (scheduled read-only
  check-ups, `/` presets, fixed filters), and what the chat must
  refuse to become, with a distilled ten-item shortlist. Linked
  from `docs/research/README.md`. Documentation only; no behaviour
  changes.
- **New research note `docs/research/OPEN-WEBUI-POSSIBILITIES.md`.**
  A deep study of the Open WebUI chat platform
  (`open-webui/open-webui` 0.10.2): architecture, license history
  (BSD-3 plus branding clause), full feature inventory, the
  Pipelines/Functions extension systems, and security posture — each
  capability read through the Ubuntu Zombie trust model with a
  borrow / translate / integrate / defer / refuse verdict, plus a
  ranked shortlist of chat upgrades implementable without new
  runtime dependencies. Linked from `docs/research/README.md`.
  Documentation only; no behaviour changes.
- **New `multipliers/` analysis library.** A documentation-only
  design surface (like `options/`) analysing how to multiply the
  existing Ubuntu installation mechanism across Windows and macOS
  with cleaner native delivery artifacts (`.deb` + apt repository,
  signed/notarised `.pkg` + Homebrew, signed EXE/MSI + winget). It
  inventories the portable agent core versus the platform shell,
  defines the platform-shell contract, records prior art from the
  `lmstudio-vampire` packaging tree and the `forgejo-society`
  installation library, and lays out a phased roadmap with risks
  and explicit non-goals. No runtime behaviour changes.
- **The installer now bootstraps its own prerequisites.** A fresh
  Ubuntu image ships without `curl` (and a minimal image can lack
  `python3`), which made the local LM Studio / LLM network scan and
  the preflight connectivity check skip or fail. `install.sh` now
  installs whichever of `curl`/`python3` is missing via `apt-get`
  right after the root check, before any step that needs them.
- **The Forgejo Options menu now covers every decision parameter.**
  New menu items let the operator interactively edit the PostgreSQL
  database name, role (username), and password (item 5) and the
  Forgejo/runner release pins plus runner labels (item 6), matching
  the existing prompts for the port and admin account. The database
  password prompt follows the shared contract: blank auto-generates a
  password and records it in the root-only receipt.
  `FORGEJO_RUNNER_LABELS` is now validated (conservative character
  set) before it is interpolated into the runner registration
  command.
- **Optional-component passwords are now options.**
  `FORGEJO_ADMIN_PASSWORD` and `FORGEJO_DB_PASSWORD` environment
  variables let the operator choose the Forgejo admin and PostgreSQL
  role passwords (8–256 printable characters, validated before any
  host change). When left unset the installer generates them randomly,
  as before, and now records the generated values in the root-only
  install receipt (mode `600`) so they can be retrieved later;
  operator-supplied passwords are never recorded. The interactive
  Options review can also set the admin password, and an
  operator-chosen admin password is not forced to change on first
  sign-in. Same contract intended for the parameters of every future
  optional component.
- **`uninstall.sh` now speaks the same UX flag vocabulary as
  `install.sh`.** New `-q`/`--quiet` (warnings and errors only),
  `--no-color`/`--no-colour` (disable ANSI; `NO_COLOR` and
  `ZOMBIE_COLOR` are also honoured), `-v`/`--version`, and `-n` as a
  short alias for `--dry-run`. The startup splash now prints only for
  a real uninstall run — `--help`, `--version`, and bad-usage errors
  stay concise — and unknown arguments exit `2` (bad usage) instead of
  `1`, matching `install.sh`. The smoke tests (`flags` and `branding`
  groups) assert the new contract.

### Changed
- The optional-components review table no longer prints a
  "Coming soon" teaser row.

### Fixed
- **`die()` no longer leaks its exit-code argument into the error
  message.** `scripts/lib.sh` printed `$*`, so calls like
  `die "Unknown flag: --x (try --help)" 2` rendered a stray `2` at the
  end of the line in `install.sh` and `uninstall.sh` error output.
- **Consistent `--help` across every operator-facing script.** The
  payload helpers (`collect-diagnostics`, `health-check`,
  `secrets-edit`, `setup-agent-venv`, `zombie-chat`) and the delivery
  scripts (`scripts/build-deb.sh`, `scripts/verify-bridge-pins.sh`)
  now answer `-h`/`--help` with a usage summary and reject unknown
  arguments with exit `2`, matching `install.sh`, `uninstall.sh`,
  `audit-recent`, and `verify-release`. The smoke tests (`flags`
  group) now assert the `--help`/bad-argument contract for every
  helper.
- **README landing pages for every top-level folder.** New
  `docs/README.md` (documentation index by reader intent),
  `scripts/README.md` (delivery-script guide with VM warning),
  `tests/README.md` (test groups and how to run them), and
  `docs/analysis/README.md` (what the analysis notes are), so every
  directory in the repository now explains itself.
- **Optional components mechanism ("Ubuntu Zombie + Options") and the
  first component: a self-hosted Forgejo git forge.** Opt-in
  `ZOMBIE_INSTALL_<COMPONENT>` flags (all default `0`) now plug into a
  shared contract: validated settings, a nested `9) Options` sub-menu in
  the interactive parameter review, dry-run and pre-flight stanzas that
  leave the default output unchanged, receipt records, an honest
  `[n/total]` phase counter, `verify`/`doctor`/`repair` checks, policy
  classes, and `uninstall.sh` reversal. `ZOMBIE_INSTALL_FORGEJO=1`
  installs Forgejo backed by PostgreSQL — checksum-verified binary from
  codeberg.org (pin with `FORGEJO_VERSION`), generated secrets stored
  only in `/etc/forgejo/app.ini` (`root:git`, `640`), an auto-generated
  admin account printed once, a hardened `forgejo.service`, and normal
  network access on all interfaces (`FORGEJO_HTTP_PORT`, default
  `3000`). `ZOMBIE_INSTALL_FORGEJO_RUNNER=1` adds a co-located Forgejo
  Actions runner using the standard Docker executor (labels default to
  `ubuntu-latest:docker://node:20-bookworm`), with a visible warning
  that co-location is contrary to upstream guidance. Documented in
  `docs/CONFIGURATION.md`, `docs/ARCHITECTURE.md`, and `README.md`.
- **Chat-UI password gate and Time-to-Live (TTL) kill switch.** The chat
  service is reachable by every local user on `http://127.0.0.1:7878`, so
  it is now protected by a shared password (the installer asks for it;
  default `braaaains`, stored only as a PBKDF2 hash in
  `secrets/env` as `ZOMBIE_ADMIN_PASSWORD_HASH`). Each install also gets a
  Time to Live (default 7 days, set with `ZOMBIE_TTL_DAYS` or the
  interactive review). Once the TTL elapses — or an operator runs
  `/ttl --die` — the zombie writes a durable tombstone and is permanently
  disabled until the next reinstall. The new `/ttl` chat command shows the
  remaining time, `/ttl <days>` extends it, and `/ttl --die` kills the
  zombie immediately. New server endpoints back it: `GET /api/session`,
  `POST /api/login`, `POST /api/logout`, and `GET`/`POST /api/ttl`. State
  lives in `payload/agent/lifecycle.py`; the password helpers live in
  `payload/agent/auth.py`.
- Added `/ttl reset [duration]` and duration-based `/ttl` inputs such as
  `14 days`, `2 years 3 months`, and `3 hours`. Added `/password
  [new password]` to change or remove the chat password after confirmation.

### Changed
- Expanded the in-chat example prompt library with richer inspection,
  recovery, maintenance, security, and Ubuntu Zombie self-operation
  requests.
- The chat interface now includes a top-centre **Logoff** control, a
  `/logout` slash command that reopens the password gate, and a grouped,
  alphabetised `/help` command list.
- The installer now shows the Ubuntu Zombie logo as soon as install mode
  starts, the uninstaller shows the same logo, the default TTL is 7 days,
  and the default chat password is `braaaains`.
- **Zombie Zero default footprint.** Removed the installer/runtime
  surfaces identified in `docs/analysis/ubuntu-zombie-zero.md`: SSH
  server setup, Tailscale, fail2ban/UFW wiring, VNC/x11vnc, graphical
  autologin, Docker, GUI/browser automation, and their built-in skills.
  The product now installs a loopback-only chat surface plus the local
  policy/audit runtime.
- **Documentation aligned with Zombie Zero.** Updated `SECURITY.md`,
  `AGENTS.md`, `CONTRIBUTING.md`, `docs/CONFIGURATION.md`, and
  `docs/INTERNET-ACCESS.md` to drop stale references to SSH, Tailscale,
  UFW, VNC, autologin, Docker, and GUI/browser automation, and to
  correct the Python dependency list to match `setup-agent-venv`.

### Fixed
- **The installer no longer aborts at "Install verification script" with
  `JSON: unbound variable`.** A generated `verify` line now preserves
  `${JSON}` for runtime evaluation instead of expanding it while
  `install.sh` writes the script under `set -u`.
- **Uninstall now continues cleanup after non-critical host failures.** A
  failed `systemctl daemon-reload`, global npm package removal, or stubborn
  install directory now records an error but no longer prevents later cleanup
  steps such as shim and user removal. Path removals are quoted before passing
  through the dry-run/eval helper, and directory removals are verified before
  printing success.
- **`/whoami` no longer errors when provider configuration is broken or
  incomplete.** The chat UI now calls a dedicated `/api/whoami`
  endpoint, and `/profile` no longer builds itself through `/config`, so
  local identity commands stay available even before a model provider is
  configured.
- **The installer no longer aborts at "Install verification script" with
  `PI_AI_VERSION: unbound variable`.** The generated `verify` script and
  the install-time pin checks referenced `PI_AI_VERSION` and
  `PI_MONO_VERSION`, but those variables were never defined, so under
  `set -u` the installer crashed on line ~2780. They are now read once
  from their source of truth (`payload/agent/pi-ai.version` and
  `payload/agent/pi-mono.version`) and degrade to `unknown` if a pin file
  is missing rather than aborting.
- Clarified provider/model setup in `README.md`, `docs/QUICKSTART.md`,
  and `docs/CONFIGURATION.md`: Ubuntu Zombie reads
  `/opt/ai-zombie/secrets/env`, maps `ZOMBIE_PROVIDER=gemini` to pi-ai's
  `google` provider internally, passes the resolved provider/model to
  `pi` on each turn, and treats `ZOMBIE_MODEL` as taking precedence over
  provider-specific model fallback variables.
- **Approved package installs and `/etc` edits no longer fail with
  "Read-only file system."** The chat service unit ran under
  `ProtectSystem=full`, which read-only bind-mounts `/usr`, `/boot`, and
  `/etc` inside the unit's private mount namespace. Because `sudo` does
  not open a new mount namespace, every approved elevation — including
  `pkg.install` (`apt-get install`) and configuration edits — inherited
  the read-only `/usr` and failed regardless of any live
  `mount -o remount,rw`. `ProtectSystem` is now disabled (`false`) so the
  agent can write `/usr`/`/etc` as its job requires; the policy gate and
  closed tool registry remain the security boundary (same rationale as
  the deliberately-absent `NoNewPrivileges`).
- Periodic post-install health checks now report unhealthy runtime state in
  the journal without leaving `ubuntu-zombie-health.service` failed after the
  timer runs.

### Added
- The installer, `zombie-chat` helper, and browser chat UI now start with
  the full ANSI Shadow `UBUNTU ZOMBIE` wordmark.
- **`payload/README.md`** — a world-class tour of the payload tree: what
  each file is, where the installer deploys it, and the four runtime
  invariants (loopback-only, closed tool surface, policy gate +
  approval, full audit), with Mermaid diagrams for deployment, the
  per-turn tool-call flow, the `agent/` module graph, and the action
  classes.
- Release builds now generate a SLSA provenance attestation, publish it with
  the release assets, and ship `payload/bin/verify-release` so consumers can
  check `SHA256SUMS`, cosign signatures, and provenance in one command.
- Node bridge inputs are now recorded in
  `payload/agent/bridge-dependencies.lock` with source URLs, SHA-256 hashes,
  integrity strings, and license metadata; release builds verify the pins and
  installs consume the checksum-verified tarballs.
- Changing `VERSION` on `main` now triggers the release workflow, creates the
  matching `v<VERSION>` tag when needed, and publishes the release artifacts.
- **`/model` chat command.** The chat UI now lists the models the
  configured provider offers and lets the operator switch between them at
  runtime. `/model` (no argument) lists the provider's catalogue with the
  active model marked `*`; `/model <id>` pins a different model for the
  running chat service. Backed by pi-ai's bundled model catalogue
  (`getModels`) via a new `list_models` op in `pi-ai-bridge.mjs`, the
  `providers.list_models` / `current_model` / `set_active_model` helpers,
  and the `GET /api/models` + `POST /api/model` endpoints. Providers
  without a catalogue (e.g. `lmstudio`) accept a free-form id.
- **Local LLM discovery on the LAN.** On an interactive install,
  `scripts/install.sh install` now scans the host's IPv4 `/24` (all 256
  addresses) for an OpenAI-compatible local LLM server answering on
  `http://<ip>:1234/v1` — LM Studio, Ollama, llama.cpp, etc. — queries
  each responder's `/v1/models`, and offers the advertised models as the
  starting model. Choosing one writes `ZOMBIE_PROVIDER=lmstudio`,
  `ZOMBIE_MODEL`, and `LMSTUDIO_API_KEY` to `secrets/env` and the server's
  base URL to the `pi` custom-provider file `~/.pi/agent/models.json`, so
  the agent loop reaches the local server through a dedicated `lmstudio`
  provider (rather than `openai`, whose base URL the `pi` CLI ignores).
  Best-effort and skipped for `--yes` / non-interactive / non-TTY runs;
  tune with `ZOMBIE_SKIP_LLM_SCAN`, `ZOMBIE_LLM_SCAN_PORT`, and
  `ZOMBIE_LOCAL_LLM_API_KEY`.
- **Interactive install parameter review.** On an interactive terminal,
  `scripts/install.sh install` now opens an editable, branded summary of
  every parameter (agent user, install root, chat/VNC ports, autologin,
  Tailscale, transcript/receipt paths, SSH public key, VNC password)
  before touching the host. Edit any field with validation and re-prompt
  until satisfied, then accept to proceed; `q` cancels without changes.
  Automated runs (`--yes`, `ZOMBIE_NONINTERACTIVE=1`, non-TTY) skip it.
- **Zombie Orchid setup theme.** The setup UI is highlighted in
  `#AC43D9` with compatible accent colours (lighter orchid tint,
  complementary teal, warm magenta) via shared helpers in
  `scripts/lib.sh`. Honours the existing `ZOMBIE_COLOR` / `NO_COLOR`
  policy, so `--no-color` still emits plain text.
- **Install receipt.** Every install writes a human-readable receipt
  with all parameters at start and the outcome (result, duration,
  service status, step counts, next step) at finish; failures append a
  `FAILED` record. Secrets are never written (only an SSH key
  fingerprint and a VNC password set/unset flag). Controlled by
  `ZOMBIE_RECEIPT` (default on) and `ZOMBIE_RECEIPT_FILE` (default
  `/var/log/ubuntu-zombie/install-receipt.txt`).
- **Chat slash commands.** The chat web UI now recognises client-side
  commands (handled in the browser, never sent to the agent): `/help`,
  `/clear`, `/new` (alias `/reset`), `/examples`, `/tools`, `/health`,
  `/status`, `/version`, `/audit`, `/conversations` (alias `/history`),
  `/load <id>`, and `/shortcuts`. Diagnostic commands read the existing
  read-only API endpoints; `/version` is backed by a new
  `GET /api/version` endpoint and the deployed `VERSION` file.
- **Expanded chat command surface.** The web UI now also supports
  `/commands`, `/redraw`, `/sessions`, `/resume`, `/export`/`/save`,
  `/copy`, `/title`, `/retry`, `/undo`, `/branch`, `/compress`,
  `/skills`, `/config`, `/policy`, `/whoami`, `/profile`, `/approve`,
  and `/deny`. Conversation rewinds and retries create new branches so
  the original transcript and audit trail stay intact, and destructive
  approval phrase mistakes keep the pending action available for retry.
- **`install.sh --dry-run`.** Prints the agent user, install root,
  package groups, file paths, and firewall rules that a real
  `install` would change, then exits without modifying the host.
  Works without `sudo`. Usable for change review before granting
  privilege.
- **Step-trace log on installer failure.** A failed
  `scripts/install.sh install` now records the completed sections in
  `<log-file>.steps` and prints the last five plus a recovery hint
  in the error footer, so an operator pasting the failure into an
  issue has both the line number and the install phase.
- **`.deb` packaging.** `make deb` (or `bash scripts/build-deb.sh`)
  produces an installable `ubuntu-zombie_<version>_all.deb` under
  `dist/`. The package stages the source tree under
  `/usr/share/ubuntu-zombie/` and exposes a wrapper at
  `/usr/sbin/ubuntu-zombie`. It deliberately does NOT run the
  installer at apt time. The `prerm` refuses to remove the package
  while the host is still set up (override with
  `UBUNTU_ZOMBIE_FORCE_REMOVE=1`). `debian/` skeleton committed.
- **Signed releases.** `.github/workflows/release.yml` builds the
  source tarball, the `.deb`, an SPDX-JSON SBOM (Syft), per-artifact
  cosign keyless signatures, and `SHA256SUMS`, and uploads everything
  to the matching GitHub Release. Release notes include the cosign
  verify-blob snippet.
- **OpenSSF Scorecard, CodeQL, dependency-review.** New
  `.github/workflows/{codeql,dependency-review,scorecard}.yml`
  cover the Python agent code, the npm bridges, and PR-time
  dependency checks. Scorecard publishes the SARIF for the badge in
  README.
- **CI matrix.** `ci.yml` now runs lint + smoke + pytest on both
  Ubuntu 22.04 (Python 3.10) and Ubuntu 24.04 (Python 3.12). All
  third-party actions are pinned to commit SHAs with the
  human-readable tag in a trailing comment.
- **Integration workflow.** `.github/workflows/integration.yml`
  exercises `scripts/install.sh install --dry-run` on
  `ubuntu-22.04` and `ubuntu-24.04` runners nightly and on demand,
  plus a container-based smoke run.
- **`secrets-edit` backup-on-edit.** A timestamped backup of
  `/opt/ai-zombie/secrets/env` (mode 600, owned by the agent user)
  is written to `/opt/ai-zombie/secrets/backups/` every time the
  editor is opened. The ten most recent are kept; older backups are
  pruned. Empty saves trigger a roll-back hint.
- **Pre-commit hooks.** `.pre-commit-config.yaml` wires up
  shellcheck, shfmt, ruff (+ formatter), standard hygiene hooks,
  and the smoke `syntax`/`python`/`standards` blocks so local
  commits get the same checks CI runs. `ruff.toml` lives at the
  repository root.
- **`pytest` regression suite.** `tests/python/` mirrors the policy
  classification and audit-redaction blocks from `tests/smoke.sh
  python` with a real pytest layout so individual cases can be run
  with `-k`. Both runners stay in CI: smoke is the safety net,
  pytest is the readable surface.
- **Docs.**
  - [`docs/PLATFORMS.md`](docs/PLATFORMS.md) — supported Ubuntu
    versions, architectures, and what is explicitly unsupported.
  - [`docs/FAQ.md`](docs/FAQ.md) — quick answers distilled from
    TROUBLESHOOTING and SECURITY.
  - [`docs/UPGRADING.md`](docs/UPGRADING.md) — version-by-version
    upgrade notes.
  - [`SUPPORT.md`](SUPPORT.md) — discussions vs. issues vs.
    security disclosure routing.
  - [`RELEASE.md`](RELEASE.md) — release cut process for
    maintainers.
  - Research notes under `docs/ALTERNATIVE-*.md`,
    `docs/ALTERNATIVES*.md`, and `docs/SIMILAR.md` moved to
    `docs/research/` with a stub README so the user-facing TOC is
    shorter.
  - README gains CI, CodeQL, Scorecard, Latest-release, and
    Ubuntu-LTS badges and a `.deb` install snippet.
  - TROUBLESHOOTING gains a table mapping symptoms to
    `repair`-vs-`install` fixes.

### Changed
- **Version scheme is now date-time based.** Releases are versioned
  `yyyy.mm.dd.hh.nn.ss` (UTC release timestamp) instead of Semantic
  Versioning. `VERSION`, `RELEASE.md`, `debian/changelog`,
  `.github/workflows/release.yml`, and `README.md` updated accordingly.
- **Tailscale is now off by default.** `scripts/install.sh` no longer
  installs or enrols Tailscale unless you opt in with
  `ZOMBIE_SKIP_TAILSCALE=0`. With the default, inbound SSH is allowed
  on every interface (still key-only and root-disabled); opting in
  restricts inbound SSH to the `tailscale0` interface as before.
  `TAILSCALE_AUTHKEY` is used only when `ZOMBIE_SKIP_TAILSCALE=0`.
  `README.md`, `docs/QUICKSTART.md`, `docs/CONFIGURATION.md`,
  `SECURITY.md`, `docs/FAQ.md`, and `docs/REQUIRES.md` updated, and
  `docs/QUICKSTART.md`/`README.md` now document every parameter the
  installer requires to proceed.

### Fixed
- **Chat memory and command execution in the pi-mono agent loop.** The
  `pi-mono` bridge (`payload/agent/pi-mono-bridge.mjs`) now forwards the
  prior conversation into pi's one-shot `-p` prompt, so the agent
  remembers names and earlier context across turns instead of starting
  fresh every message. It also enables pi's real built-in tools (`read`,
  `bash`, `edit`, `write`, `grep`, `find`, `ls`) instead of passing the
  Python registry's logical names (`fs.read`, `shell.run`, …) — which pi
  does not recognise — together with `--no-builtin-tools`, a combination
  that left the agent with zero usable tools and made it emit
  tool-call-shaped text (e.g. `<|tool_call>call:fs.list{…}`) rather than
  acting. The chat system prompt now describes these built-in tools.
- **Loading a past conversation in the chat UI.** The `/load <id>`
  command now reports unknown ids instead of silently showing an empty
  transcript: `GET /api/conversation/<id>` returns a `404` with an
  `{"error": …}` body for an unknown conversation (and the existing
  `400 bad id` for a non-numeric id), and the chat UI surfaces that
  server message rather than a bare `HTTP 4xx`. Loaded transcripts now
  interleave chat messages and tool events in their recorded
  chronological order — matching the live turn view — instead of
  rendering every message first and bunching all tool calls at the end.
  A smoke test (`tests/smoke.sh python`) guards the conversation
  endpoint's existing / bad-id / not-found responses.
- **`collect-diagnostics` aborted before writing its bundle.** The
  `capture` helper ran each diagnostic command under `set -euo
  pipefail` without guarding its exit status, so the first tool that
  returned non-zero — `systemctl status` of an inactive unit (exit
  3), `docker version` with no daemon, or a `tailscale` binary that
  is not installed — aborted the whole script. The EXIT trap then
  deleted the partial staging directory, leaving no tarball. These
  failures are exactly the broken states an operator runs diagnostics
  to capture. `capture` now swallows the command's exit status (its
  output is still recorded via `2>&1`), so every section is collected
  regardless of individual failures. A smoke test
  (`tests/smoke.sh diagnostics`) guards the behaviour.
- **Installer Node runtime.** `scripts/install.sh` now installs
  Node.js 22.x from the official NodeSource apt repository instead
  of the Ubuntu-archive `nodejs`/`npm` packages. The bundled npm on
  Ubuntu 22.04 / 24.04 (npm 9.x on Node 18) could not self-upgrade to
  `npm@latest`, which now requires Node `^20.17.0 || >=22.9.0`, so
  the "Node runtime" section failed with `EBADENGINE` and aborted
  the install after retries. The NodeSource source is configured
  with a `signed-by` keyring at `/usr/share/keyrings/nodesource.gpg`
  and the `nodejs` package is pinned to the NodeSource origin via
  `/etc/apt/preferences.d/nodejs`. `docs/REQUIRES.md` updated.

### Added
- **Verbose scribe (opt-in debugging).** `payload/agent/audit.py`
  honours `ZOMBIE_AUDIT_VERBOSE=1` to attach a redacted
  `stdout_preview` / `stderr_preview` (default 2 KiB, tunable via
  `ZOMBIE_AUDIT_PREVIEW_BYTES`, hard-capped at 16 KiB) to every
  `tool_call` entry. Existing SHA-256 digests are unchanged so the
  integrity contract holds. Every audit entry now also carries
  `ts_utc` (ISO-8601 UTC) and `pid` so testers can correlate audit
  lines with `journalctl` without timezone math. `payload/bin/audit-recent`
  gained `--follow`/`-f` (tail -F across logrotate) and `-t TYPE`
  filters and now surfaces previews when present. Smoke tests cover
  the redaction round-trip and the always-on `pid` / `ts_utc` fields.
  Documented in `docs/CONFIGURATION.md` and `docs/TROUBLESHOOTING.md`.
- Phase 4 of `docs/UPGRADE-TO-PI-PLAN.md` — hardening pass:
  - **P4.1** Per-turn budget defaults realigned with
    `docs/UPGRADE-TO-PI.md` §6.1–§6.2 (`max_tool_calls_per_turn` 12,
    `max_elevated_calls_per_turn` 3) in `payload/etc/policy.yaml` and
    `payload/agent/policy.py`. `server.py` now enforces
    `max_elevated_calls_per_turn` and `pi_mono.py` emits a uniform
    synthetic `budget_exceeded:` observation when either budget is
    exceeded; the synthetic observation is recorded in the JSONL audit
    (`decision="budget_exceeded"`) and the history `events` table.
    `tests/smoke.sh` gained regression tests against
    `tests/fixtures/stub-pi-mono.mjs` that drive both budgets through
    the soft-failure path. `docs/CONFIGURATION.md` updated.
  - **P4.2** Persistent `pi-mono` evaluated and declined (no-go).
    Rationale recorded in `docs/UPGRADE-TO-PI-PLAN.md` §11; no code
    change.
- Phase 2 of `docs/UPGRADE-TO-PI-PLAN.md` — atomic cutover from the
  fenced-bash parser to the `pi-mono` agent loop:
  - **P2.1** Pinned `@earendil-works/pi-coding-agent` via
    `payload/agent/pi-mono.version`; installer runs `npm install -g`
    against the pinned version and `verify` asserts the pin.
  - **P2.2** Closed 13-tool registry in `payload/agent/tools.py`
    (`shell.run`, `fs.read`, `fs.write`, `pkg.query`, `pkg.install`,
    `svc.status`, `svc.control`, `net.status`, `gui.screenshot`,
    `gui.click`, `gui.type`, `skill.list`, `skill.load`) with per-tool
    schema validation, path allow-lists for filesystem tools, and
    fail-closed dispatch.
  - **P2.3** Additive history schema migration in
    `payload/agent/history.py` via `PRAGMA user_version`, with a
    pre-migration snapshot saved to
    `state/conversations.db.bak.<ts>`. New `events` table records
    structured `tool_call`/`tool_observation`/`pending_tool_call`
    events for the UI replay.
  - **P2.4** Node bridge (`payload/agent/pi-mono-bridge.mjs`) wraps
    `pi --mode json --no-builtin-tools --tools <names>` and speaks a
    line-delimited JSON protocol to the Python client
    (`payload/agent/pi_mono.py`). `ZOMBIE_PI_MONO_BRIDGE` lets the
    smoke suite swap in `tests/fixtures/stub-pi-mono.mjs`.
  - **P2.5** Per-tool approval UI: `payload/agent/templates/index.html`
    replaces `renderProposal` with `tool_call`/`tool_observation`/
    `pending_tool_call` renderers, a per-turn budget counter, and
    `tool_call_id`-keyed approval POSTs.
  - **P2.6** New `policy.yaml` blocks (`tool_classes:` and
    `agent: max_tool_calls_per_turn / max_elevated_calls_per_turn`),
    classified via `policy.classify_tool`. Audit log gains
    `log_tool_call(...)` recording SHA-256 + byte count of stdout/
    stderr (never raw content), plus extended sensitive-env redaction.
  - Installer + `uninstall.sh` updates: deploy `pi-mono-bridge.mjs`,
    render `/opt/ai-zombie/pi/{settings.json,APPEND_SYSTEM.md}`,
    create `state/logs/` and `state/pi-mono-sessions/`, snapshot the
    DB before migration, add pi-mono checks to `verify`, re-render
    pi configs from `cmd_repair`, and prompt to remove the global
    `@earendil-works/pi-coding-agent` package on uninstall.

### Added
- `LICENSE`, `CODE_OF_CONDUCT.md`, and `.editorconfig` so the repository
  metadata matches the documented GitHub project layout.
- Smoke coverage and CI checks for required repository metadata and the
  release package source bundle.
- `ZOMBIE_USER` env var to choose the local Linux account name used as
  the operating identity of the AI Systems Administrator. The legacy
  `AGENT_USER` is still honoured as a backward-compatible alias.
- Phase 0 of `docs/UPGRADE-TO-PI-PLAN.md` (the security prerequisites
  Phase 2 depends on):
  - **P0.1** Argv-aware classifier in `payload/agent/policy.py`. The
    classifier now splits pipelines/sequences, strips leading
    `VAR=value` env prefixes and `sudo` flags, and re-applies every
    rule to the canonical argv in addition to the rendered whole
    command. This catches `LC_ALL=C ls`, `sudo -u root systemctl …`,
    and `rm -rf "/quoted path"` that the legacy regex-only matcher
    missed.
  - **P0.2** Fail-closed default: `settings.default_class` ships as
    `destructive` so unknown commands cannot auto-run. Documented in
    `docs/CONFIGURATION.md`.
  - **P0.3** `sudo_allow_list:` in `payload/etc/policy.yaml` keeps
    common privileged targets (`apt`, `systemctl`, `ufw`, `tailscale`,
    …) at `system_change` despite the conservative default. Documented
    in `docs/CONFIGURATION.md`.

### Changed
- The agent account created by the installer is now called `zombie` by
  default (previously `agent`). The name is overridable at install time
  via `ZOMBIE_USER`, and is propagated to the sudoers drop-in, the
  systemd `User=`/`Group=` of `ubuntu-zombie-chat.service`, the venv
  ownership, the SSH `AllowUsers` line, and the chat service system
  prompt. Existing installs are unaffected — re-run the installer with
  `ZOMBIE_USER=agent` (or `AGENT_USER=agent`) to keep the old name.

## [0.2.0] - 2026-05-24

### Added — MVP product loop
- Subcommand dispatch on `install.sh`:
  `install`, `verify`, `doctor`, `repair`, `uninstall`.
- Separate `uninstall.sh` with `--dry-run` and `--archive`
  modes that remove sudoers drop-ins, SSH drop-ins, x11vnc autostart,
  the chat systemd service, generated helpers, and (optionally) the
  `agent` user. User data under `/home/agent` and
  `/opt/ai-zombie/state/` is only deleted with explicit confirmation.
- Stronger preflight: detect free disk and memory, DNS resolution,
  `apt`/`dpkg` lock contention, conflicting display managers, public-SSH
  install path, and an existing Tailscale login.
- Retry with exponential backoff around `apt-get`, `curl`, `pip`, `npm`,
  and `playwright install`.
- `ZOMBIE_ENABLE_AUTOLOGIN` opt-in for graphical autologin (default off).
  The installer documents the trade-off and verifies the choice.
- Policy file `/etc/ubuntu-zombie/policy.yaml` with the action classes
  `read_only`, `user_change`, `system_change`, `network_change`,
  `destructive`. Defaults require approval for anything beyond read-only
  diagnostics and require an extra confirmation phrase for destructive
  actions.
- JSON-lines audit log at `/var/log/ubuntu-zombie/audit.log` with
  `logrotate` rules. Every prompt, proposed action, approval decision,
  command, exit code, and verification result is recorded. Secrets are
  redacted before logging.
- Local web chat service bound to `127.0.0.1`, served from
  `/opt/ai-zombie/agent/`. SQLite conversation history under
  `/opt/ai-zombie/state/conversations.db`. The conversation survives
  process restart.
- Provider abstraction with `openai` and `anthropic` backends, selected
  via `ZOMBIE_PROVIDER`. A clear error is raised if no provider is
  configured.
- Approval gate before privileged or destructive commands; safe-command
  runner that captures stdout, stderr, exit code, and proposed follow-up
  checks.
- systemd unit `ubuntu-zombie-chat.service` running as `agent`.
- Helper scripts under `/opt/ai-zombie/bin/`:
  - `zombie-chat` — print the chat URL and Tailscale tunnel example.
  - `audit-recent` — pretty-print recent audit entries.
  - `health-check` — single-command health summary (agent service,
    Tailscale, SSH, firewall, Docker, desktop, provider token, disk).
  - `collect-diagnostics` — collect logs and state into a redacted
    bundle in `/tmp/`.
  - `secrets-edit` — safe editor wrapper that re-asserts `0600`.
  - `doctor`, `repair` — wrappers around the installer subcommands.
- Optional systemd timer `ubuntu-zombie-health.timer` that runs
  `health-check` every 15 minutes.
- First-run status summary printed at the end of `install`, with the
  exact next command for each pending step.
- Safe example prompts shipped in `/opt/ai-zombie/agent/examples.md`
  and exposed in the chat UI.

### Added — packaging and developer ergonomics
- `VERSION` file consumed by the installer.
- `Makefile` with `lint`, `test`, `install-local`, `verify`, `package`.
- GitHub Actions CI: ShellCheck on shell scripts, `bash -n` syntax
  checks on the installer and all generated helpers, secret-pattern
  scan, Python syntax check on the chat service, and Markdown link
  sanity.
- `.gitignore` covering logs, state, screenshots, virtualenvs,
  `node_modules`, Debian build artifacts, and editor files.

### Added — documentation
- `VISION.md` — the one-sentence MVP promise.
- `QUICKSTART.md` — install in the shortest safe path.
- `CONFIGURATION.md` — provider keys, Tailscale, VNC, chat access.
- `TROUBLESHOOTING.md` — apt locks, Tailscale, Docker group, desktop
  automation, Playwright, VNC, secrets permissions.
- `ARCHITECTURE.md` — components and trust boundaries.
- `SECURITY.md` — trust boundary, what the provider sees, rotation,
  revocation, known risks, responsible disclosure.
- `CONTRIBUTING.md` — how to test and change the installer.
- `ROADMAP.md` — post-MVP ideas extracted from the possibility docs.
- README rewritten as a concise front door pointing to the new docs.

### Changed
- `install.sh` reads the version from the `VERSION` file at the
  repository root when present.
- Graphical autologin is no longer enabled by default; the installer
  prints the recommended override when the choice matters for
  desktop-automation flows.

## [0.1.0] - 2025-Q4

### Added
- Initial proof-of-concept installer (`install.sh`) that creates
  the `agent` user, configures passwordless sudo, hardens SSH,
  installs Tailscale + UFW, forces Xorg + autologin, installs Docker,
  Python and Node runtimes, Playwright + Chromium, GUI automation
  tools, and a loopback-only x11vnc desktop, plus an end-of-install
  verification script.
