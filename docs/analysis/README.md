# Analysis notes

Working notes from repository-wide reviews. Unlike the user docs one
level up, these are **internal engineering records**: each file lists
concrete issues that were found, what was decided, and whether the fix
has landed. They are kept so a future review can re-check the same
ground without rediscovering it from scratch.

- [`improvements-1.md`](improvements-1.md) — first full-repository
  review and its periodic reanalysis: each originally raised issue,
  re-checked against the current tree.
- [`improvements-2.md`](improvements-2.md) — second review pass with
  the same structure.
- [`improvements-3.md`](improvements-3.md) — design analysis of a
  component-oriented install/uninstall CLI (verb + component targets,
  standalone Forgejo, component registry and manifest).
- [`install-enhancement-1.md`](install-enhancement-1.md) — focused
  analysis of installer UX and robustness enhancements.
- [`improvements-8.md`](improvements-8.md) — external adversarial
  review (2026-07-21): mediated-tool-path bypass (F1, critical), test
  coverage realism, auth fail-open, and a sequenced remediation plan.
- [`f1-option-more-control.md`](f1-option-more-control.md) — F1 fix
  design: restore real mediation via a first-party
  `zombie-policy-gate` pi extension (and why `--mode rpc` alone would
  not mediate).
- [`f1-option-less-control.md`](f1-option-less-control.md) — F1
  alternative: accept the unmediated architecture, correct every
  doc/promotion claim, and add compensating controls (auth, bridge-log
  audit, blast-radius).

If you are looking for how to *use* or *understand* Ubuntu Zombie,
start at [`../README.md`](../README.md) (the documentation index)
instead.
