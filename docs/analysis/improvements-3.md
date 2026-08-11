# Ubuntu Zombie improvements 3 — component-oriented install syntax

Last analysed: 2026-07-14.

This document analyses how the installer's command syntax should evolve
so that `scripts/install.sh` can install and uninstall *complex
applications as first-class components* — starting with the Ubuntu
Zombie baseline itself and, as the first optional component, Forgejo
backed by PostgreSQL. It is a design analysis and recommendation, not a
record of completed work.

Before changing code, read:

- `AGENTS.md`
- `README.md`
- `docs/VISION.md`
- `docs/ARCHITECTURE.md`
- `SECURITY.md`
- `CONTRIBUTING.md`
- `options/README.md` and `options/PLAN.md`
- `multipliers/README.md`

Do not run `make install-local`, `scripts/install.sh install`,
`scripts/install.sh repair`, `scripts/uninstall.sh`, or installed
helpers from `/opt/ai-zombie/` on the current workstation. Those
commands mutate users, sudoers, services, package state, and systemd
state. Use only non-root tests unless the user explicitly provides a
disposable Ubuntu Desktop LTS VM.

After shell or Python changes, run:

```bash
make lint
make test
```

If `CHANGELOG.md` is updated for user-visible changes, also update
`VERSION` with:

```bash
date -u +%Y.%m.%d.%H.%M.%S > VERSION
```

## Executive summary

The request: turn the installer's CLI from a *verb-only* interface
(`install.sh install`, with components chosen by environment flags)
into a *component-aware* interface where the zombie baseline is just
the first installable component:

- `install.sh zombie` — install only the zombie.
- `install.sh forgejo` — install Forgejo (which pulls in PostgreSQL),
  possibly **without** the zombie at all.
- Uninstall should be symmetric per component.
- The scheme must scale to every future plan in `options/` and every
  packaging target in `multipliers/` without another syntax break.

The recommendation, argued in detail below, is to keep the existing
lifecycle **verbs** (`install`, `verify`, `doctor`, `repair`,
`uninstall`) and add **component targets** after the verb:

```
install.sh <verb> [component ...] [flags]
```

so `install.sh install forgejo`, `install.sh uninstall forgejo`,
`install.sh verify zombie forgejo`, and so on. Bare
`install.sh install` keeps its current meaning (baseline zombie) for
back-compatibility, and the existing `ZOMBIE_INSTALL_<COMPONENT>=1`
environment flags remain the non-interactive API — component tokens
simply set the same flags. This grammar preserves the four lifecycle
verbs the product already promises for *every* piece of managed
software, which the pure `install.sh forgejo` grammar would lose.

Getting to "Forgejo without the zombie" is the structurally expensive
part: today the Forgejo section rides inside the baseline install flow
of `scripts/install.sh` and assumes the baseline preflight, logging,
receipt, and apt plumbing have already run. That coupling must be
replaced by an explicit shared **core layer** plus a per-component
**registry** and an on-host **component manifest**, described in items
3–5.

## 1. Current state (what the syntax is today)

- `scripts/install.sh` accepts one subcommand from a fixed verb set:
  `install` (default), `verify`, `doctor`, `repair`, `uninstall`
  (which delegates to `scripts/uninstall.sh`).
- Component selection is *environmental*, not positional:
  `ZOMBIE_INSTALL_FORGEJO=1` and `ZOMBIE_INSTALL_FORGEJO_RUNNER=1`
  (both default `0`), validated in `validate_config`, surfaced in the
  interactive parameter review (Options, item 9), the dry-run plan,
  and the install receipt.
- The Forgejo/PostgreSQL section is a guarded block *inside* the
  baseline install flow (marked with `option-sections` comments). It
  runs only after the zombie baseline steps and reuses baseline
  helpers (`apt_install`, `run`, `section`, receipts, preflight).
  There is no path that installs Forgejo alone.
- `scripts/uninstall.sh` is all-or-nothing: it reverses the whole
  install, detecting Forgejo remnants from on-host state rather than
  from flags. There is no "remove only Forgejo, keep the zombie".
- Unknown subcommands exit `2`; a second subcommand token is rejected
  as an unexpected positional (`reject_unexpected_positional_args`).
  That guard is exactly where component targets would be parsed.
- `tests/smoke.sh` (the `subcommands` check), the completions in
  `scripts/completions/`, `README.md`'s Subcommands block, and
  `docs/CONFIGURATION.md` all encode the current verb set, so any
  grammar change fans out to all of them.

## 2. Choosing the grammar

Three plausible grammars were considered.

### Option A — component as the subcommand (the proposal as stated)

```
install.sh zombie
install.sh forgejo
uninstall.sh forgejo
```

Pros: shortest possible invocation; reads naturally for the two-verb
world of install/uninstall.

Cons, and they are decisive:

- It silently drops `verify`, `doctor`, and `repair` — or forces them
  into flags (`install.sh forgejo --verify`), which inverts the
  existing, documented verb model. Per-component `verify`/`doctor`/
  `repair` is precisely the capability that makes complex applications
  manageable by the zombie, so the grammar must keep a verb slot.
- `install.sh zombie` colliding with the existing `install` verb set
  means every future component name is a reserved word competing with
  future verbs in one flat namespace. That is the kind of ambiguity
  the current parser explicitly rejects (see the second-subcommand
  guard).
- Installing several components in one converging run
  (`zombie` + `forgejo` + a future `backup`) has no natural spelling.

### Option B — verb first, component targets after (recommended)

```
install.sh install zombie
install.sh install forgejo
install.sh install zombie forgejo
install.sh uninstall forgejo
install.sh verify forgejo --json
install.sh doctor zombie
```

Pros:

- Preserves all five verbs unchanged, and extends each of them
  per-component for free. `verify`/`doctor`/`repair` scoped to one
  component is a major operational win and matches the receipts and
  `option-sections` structure already in place.
- Multiple targets in one run is natural and keeps the single
  idempotent converge pass (one preflight, one review, one receipt).
- Back-compatible: bare `install.sh install` keeps meaning "the zombie
  baseline", bare `verify`/`doctor` mean "everything the manifest says
  is installed", and `ZOMBIE_INSTALL_FORGEJO=1 install.sh install`
  keeps working — the env flag and the positional token set the same
  internal state.
- Matches the ecosystem conventions operators already know
  (`apt install <pkg>`, `snap install <pkg>`, `systemctl <verb>
  <unit>`), which lowers the learning cost as the component list grows
  through `options/`.

Cons: two words instead of one for the common case. This is the right
trade — see the mitigation below.

### Option C — component first, verb second

```
install.sh forgejo install
install.sh forgejo verify
```

Pros: groups everything about one component together. Cons: breaks
every existing invocation (`install.sh install` becomes ambiguous),
reads worse for multi-component runs, and offers nothing Option B does
not.

### Recommendation and a bridge to the short form

Adopt **Option B** as the canonical grammar. If the one-word
ergonomics of Option A matter, add them as *sugar on top*, not as the
grammar: accept a bare known component name as shorthand for
`install <component>` (`install.sh forgejo` ==
`install.sh install forgejo`), resolved *after* the verb match so
verbs always win. Component names must then be validated against the
registry (item 4) so a typo like `install.sh forgeoj` still exits `2`
instead of doing something surprising. Document only the canonical
two-word form in `README.md`; mention the shorthand once.

`zombie` becomes the name of the baseline component in this grammar.
`install.sh install` with no targets stays equivalent to
`install.sh install zombie` for at least one deprecation cycle, so
existing docs, CI, and cloud-init snippets keep working unmodified.

## 3. Making Forgejo installable without the zombie

This is the real architectural change hiding behind the syntax
request. Today the Forgejo block assumes it runs *after* the baseline:
it reuses the baseline's root check, preflight, apt/network helpers,
logging/transcript, dry-run plumbing, and the receipt writer, and its
verify/doctor entries live inside the zombie-centric `cmd_verify` /
`cmd_doctor`. None of that requires the zombie *account or services* —
it requires the installer's *infrastructure*. So the work is to name
that infrastructure and make it a layer every component sits on:

- **Core layer (always runs, installs nothing user-visible):**
  argument parsing, `validate_config`, preflight (root, OS, network,
  disk), logging/transcript, dry-run engine, receipts, and the
  component manifest (item 5). This is a refactor of what already
  exists at the top of `scripts/install.sh`, not new behaviour.
- **`zombie` component:** the current baseline body — agent user,
  sudoers, `/opt/ai-zombie/` payload, chat service, policy, logrotate,
  TTL — moved behind the same guarded-section contract Forgejo already
  follows (`option-sections` markers, receipt stanzas, verify/doctor/
  repair hooks, uninstall reversal).
- **`forgejo` component:** the existing guarded block, unchanged in
  behaviour, but reachable when `zombie` is not selected and not
  installed. Its only true dependencies are packages (`git`,
  `postgresql`, …), which the core layer's apt helper provides.

Decisions to make explicit in this refactor:

- **Receipts and logs without the zombie.** The receipt and transcript
  paths under `/var/log/ubuntu-zombie/` are created by the core layer
  today in practice; confirm and document that a forgejo-only install
  still writes them, because they are where generated passwords are
  recorded (see the option-passwords contract in
  `docs/CONFIGURATION.md`).
- **What "the zombie manages it" means when there is no zombie.** The
  vision (`docs/VISION.md`, `options/README.md`) frames optional
  components as software the resident AI administrator can verify,
  doctor, and explain. A forgejo-only host has no resident agent; it
  still gets `install.sh verify forgejo` / `doctor forgejo` from the
  operator's shell, which is a perfectly good standalone product — but
  the docs should say plainly that agent-assisted operation requires
  the `zombie` component.

## 4. A component registry instead of scattered guards

Generalise the current per-flag `if` blocks into a small declarative
registry inside `scripts/install.sh` (bash associative arrays are
sufficient; no new dependencies): for each component, its name, its
`ZOMBIE_INSTALL_<COMPONENT>` flag, its dependency list, and the names
of its `install` / `verify` / `doctor` / `repair` / `uninstall`
functions. The dispatcher walks the selected targets in dependency
order and calls the phase functions. This gives every future plan in
`options/` (backup, snapshots, observability, proxy, …) a fixed recipe
— add one registry entry plus the phase functions — and it replaces
the growing chain of `ZOMBIE_INSTALL_FORGEJO`-style conditionals with
one loop. The existing extension recipe in `CONTRIBUTING.md` should be
updated to describe registration rather than hand-placed guards.

Dependency semantics to encode from day one:

- **Implicit internal dependencies** stay invisible: PostgreSQL is
  part of installing `forgejo` (as it is today), not a top-level
  component the operator names. If a later component also needs
  PostgreSQL, promote it to a shared component *then*, with reference
  counting on uninstall — do not build that machinery speculatively.
- **Explicit component dependencies** are named and enforced:
  `forgejo-runner` requires `forgejo` (today's runner flag becomes a
  proper sub-component or stays a Forgejo option — keeping it a
  Forgejo option is simpler and recommended for now).
- **Unknown targets** exit `2` with the valid component list, matching
  the existing bad-usage convention.

## 5. An on-host component manifest

Selective uninstall and accurate `verify` need the host to know what
was installed, independent of the flags used at install time. Today
`uninstall.sh` infers Forgejo state by probing the host. That works
for one component; it will not scale to ten. Record a small root-owned
manifest (one file per component under a fixed state directory, or a
single flat file) written at install time and removed at uninstall
time, carrying the component name, version, and install timestamp.
Then:

- `install.sh verify` / `doctor` with no targets iterate over the
  manifest, not over env flags.
- `install.sh uninstall forgejo` removes exactly that component and
  its manifest entry, leaving the zombie (or vice versa: uninstalling
  `zombie` leaves a standalone Forgejo running, with a clear warning
  that the host no longer has its administrator).
- `uninstall.sh` with no targets keeps its current meaning — reverse
  everything — so the existing documented behaviour is unchanged.
- The manifest location must survive a `zombie` uninstall (i.e. live
  outside `/opt/ai-zombie/`), since forgejo-only hosts need it too.

## 6. Uninstall symmetry

Mirror the grammar in both entry points: `install.sh uninstall
[component ...]` remains the documented front door (it already
delegates), and `scripts/uninstall.sh [component ...]` accepts the
same targets for operators who reach for it directly. Per-component
uninstall must honour the existing flags where they make sense
(`--dry-run`, `--yes`; `--archive`/`--keep-agent` only apply when the
`zombie` component is in the target set — reject them otherwise, as
the installer already rejects them for non-uninstall verbs). Each
component's uninstall function owns reversing exactly its
`option-sections`, which is how the Forgejo reversal is already
structured.

## 7. Compatibility, non-negotiables, and blast radius

Invariants that must survive the change (from `AGENTS.md`):

- **Idempotence** per component and for any target combination:
  re-running `install forgejo` on a host that has it converges
  silently; installing `forgejo` then later `zombie` works; order
  never matters.
- **`ZOMBIE_NONINTERACTIVE=1`** end-to-end for every target set, with
  missing required env exiting `64`. Env flags remain the primary
  non-interactive selector; positional targets are equivalent sugar.
- **Exit codes** unchanged: `2` for bad usage (including unknown
  components), `64`/`65`/`66` as documented.
- **Policy gate and audit** are `zombie`-component concerns and are
  untouched by the grammar change.
- **Dry-run** prints a per-component plan; the default (zombie-only)
  dry-run output should stay byte-for-byte stable, as the
  `any_option_enabled` guard already ensures.

Files that must move together with the parser change:

- `scripts/install.sh` — parser, dispatcher, registry, core-layer
  extraction.
- `scripts/uninstall.sh` — target parsing, per-component reversal.
- `scripts/completions/install.bash` and `_install.sh` — complete
  component names after verbs.
- `tests/smoke.sh` — extend the `subcommands` case for verb+target
  parsing, unknown-component rejection, shorthand resolution, and the
  noninteractive path per target.
- `README.md` (Subcommands block), `docs/QUICKSTART.md`,
  `docs/CONFIGURATION.md` (Optional components section),
  `docs/ARCHITECTURE.md` (component/registry model),
  `CONTRIBUTING.md` (extension recipe), `options/README.md`
  (contract wording), `CHANGELOG.md`, `VERSION`.

## 8. Phased implementation plan

Each phase lands independently, keeps `make lint` / `make test` green,
and leaves the default install byte-identical.

1. **Grammar.** Accept component targets after the verb; map them onto
   the existing `ZOMBIE_INSTALL_*` flags; treat bare `install` as
   `install zombie`; reject unknown targets with exit `2`. Add the
   bare-component shorthand last, if at all. Update completions,
   smoke tests, and docs. No behavioural change for existing
   invocations.
2. **Manifest.** Write/remove per-component manifest entries; make
   no-target `verify`/`doctor` manifest-driven; implement
   `uninstall forgejo` (remove Forgejo + PostgreSQL artefacts only)
   and `uninstall zombie` (baseline only, warn if other components
   remain).
3. **Standalone Forgejo.** Extract the core layer; move the baseline
   body behind a `zombie` component boundary; make
   `install.sh install forgejo` converge on a host with no zombie.
   This is the largest diff and should be reviewed against the
   idempotence and noninteractive checklists line by line.
4. **Registry generalisation.** Convert the remaining per-flag guards
   into registry entries; update `CONTRIBUTING.md`'s recipe; unblock
   the next `options/` plan (per `options/PLAN.md` sequencing) as the
   proof that adding component N+1 no longer touches the dispatcher.

Future multipliers (`multipliers/`) are unaffected by the grammar but
benefit from phase 3: a portable core layer with named components is
exactly the seam the packaging work wants to cut along.

## 9. Open questions for the maintainer

- Should the bare-component shorthand (`install.sh forgejo`) ship at
  all, or is the canonical `install forgejo` enough? (Recommendation:
  ship canonical first; add sugar only if usage demands it.)
- When `zombie` is uninstalled but other components remain, is a
  warning sufficient, or should it require an extra `--yes`-style
  acknowledgement that the host is losing its administrator?
- Does the runner stay a Forgejo option (`ZOMBIE_INSTALL_FORGEJO_RUNNER`)
  or become a dependent component (`forgejo-runner`) in the registry?
  (Recommendation: keep it an option until a second dependent
  component exists.)
