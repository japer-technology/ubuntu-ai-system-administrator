# Documentation index

Everything an operator, contributor, or curious reader needs, sorted
by the question they are asking. The product itself lives in
[`../payload/`](../payload/) and is delivered by
[`../scripts/install.sh`](../scripts/install.sh); start at the
top-level [`README.md`](../README.md) if you have never seen Ubuntu
Zombie before.

## "I want to use it"

- [`QUICKSTART.md`](QUICKSTART.md) — install on a disposable Ubuntu
  Desktop LTS VM, step by step, including every parameter the
  installer asks for.
- [`REQUIRES.md`](REQUIRES.md) — supported hardware, OS, and network
  requirements.
- [`PLATFORMS.md`](PLATFORMS.md) — exactly which Ubuntu releases are
  supported and how the installer treats everything else.
- [`CONFIGURATION.md`](CONFIGURATION.md) — every environment
  variable, secret, provider option, and lifecycle setting.
- [`TROUBLESHOOTING.md`](TROUBLESHOOTING.md) — symptom → diagnosis →
  fix, plus the diagnostic helpers shipped in
  [`../payload/bin/`](../payload/bin/).
- [`UPGRADING.md`](UPGRADING.md) — moving an existing install to a
  newer release.
- [`FAQ.md`](FAQ.md) — short answers to the questions everyone asks.

## "I want to understand it"

- [`VISION.md`](VISION.md) — what this project is, and explicitly is
  not, trying to be.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — components, action classes,
  policy gate, audit log, and trust boundaries.
- [`INTERNET-ACCESS.md`](INTERNET-ACCESS.md) — design note on giving
  the chat agent outbound internet access.
- [`OPENSSF-SCORECARD.md`](OPENSSF-SCORECARD.md) — how the repository
  scores against OpenSSF Scorecard checks and why.

## "I want to see how it got here"

- [`RELEASE-PLAN-123.md`](RELEASE-PLAN-123.md) — the next planned
  steps for the release process.

Contributor rules (linting, tests, extension recipes) live in
[`../CONTRIBUTING.md`](../CONTRIBUTING.md) and, for coding agents,
[`../AGENTS.md`](../AGENTS.md).
