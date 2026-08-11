# Raising the OpenSSF Scorecard

This note theorises how Ubuntu Zombie could earn a higher aggregate
[OpenSSF Scorecard](https://securityscorecards.dev/viewer/?uri=github.com/japer-technology/ubuntu-zombie)
than 6. It is written from the repository's own intention outward: the
project ships a *privileged, root-capable AI Systems Administrator* onto
people's Ubuntu desktops. For software like this, supply-chain trust is
not cosmetic — the artifacts an operator downloads and runs are the
attack surface. A high Scorecard is therefore directly aligned with the
project's promise that "the operator owns the machine, the provider
credentials, and the kill switch."

The Scorecard aggregate is a *weighted* average of ~18 checks, each
scored 0–10. A score of 6 almost always means a small number of
**high-weight** checks are scoring 0–3 and dragging an otherwise strong
field down. The fastest path past 6 is to fix the high-weight zeros, not
to polish checks that already score 8–10.

## What the repository already does well

These checks are very likely already scoring high, and should be
*protected* (i.e. don't regress them) rather than improved:

- **Token-Permissions** — every workflow declares a least-privilege
  top-level `permissions:` block (`contents: read` / `read-all`) and
  only widens scope per-job where genuinely required (e.g.
  `security-events: write` in CodeQL/Scorecard, `id-token: write` for
  cosign). This is the single most common Scorecard failure and the repo
  already gets it right.
- **Pinned-Dependencies (Actions)** — all third-party actions are pinned
  to a full commit SHA with a human-readable tag comment.
- **Dangerous-Workflow** — no `pull_request_target` with untrusted
  checkout, no `${{ }}` script injection of untrusted input into `run:`.
- **SAST** — CodeQL runs on push, PR, and a weekly schedule for Python
  and JavaScript with `security-and-quality` queries.
- **Security-Policy** — `SECURITY.md` is thorough and includes a private
  disclosure channel and a 90-day window.
- **Signed-Releases** — releases ship a SHA-256 checksum, an SPDX SBOM,
  and keyless cosign signatures.
- **Dependency-Update-Tool** — Dependabot is configured.
- **License**, **CI-Tests**, **Packaging** — MIT `LICENSE`, green CI on
  every PR, and a tag-driven release workflow that publishes artifacts.

## Where the score is most likely bleeding points

Ordered by expected impact (check weight × current gap).

### 1. Branch-Protection (weight: high)

Scorecard reads branch-protection settings via the API. Without an admin
token (`SCORECARD_TOKEN` / repo-admin PAT) it can only see what the
unauthenticated API exposes, and partially-configured protection scores
low. This is usually the biggest single drag on a "6".

Suggestions:

- Enable branch protection on `main` with: require pull requests before
  merging, **require at least 1 approving review**, dismiss stale
  approvals, require status checks to pass (the `CI`, `CodeQL`, and
  `Dependency Review` jobs), require branches to be up to date, and
  **require the protection rules to apply to administrators**
  (`enforce_admins`). The "include administrators" box is specifically
  rewarded.
- Block force-pushes and branch deletion on `main`.
- Optionally require signed commits (also helps the project's threat
  model). This is a documented expectation worth adding to
  `RELEASE.md` / `CONTRIBUTING.md`.
- Add a repo-admin token to the Scorecard workflow so the
  branch-protection check can actually read the settings; otherwise the
  improvements may not be visible to the scanner.

### 2. Code-Review (weight: high)

Scorecard samples recent commits and checks whether they arrived through
a reviewed pull request. On a small project, direct pushes to `main`
(even by the maintainer) tank this check.

Suggestions:

- Route **all** changes through PRs, including maintainer changes — the
  Branch-Protection "require reviews" rule above enforces this
  mechanically.
- For a solo/small maintainer team, enabling required reviews plus
  GitHub's "Require review from Code Owners" (the repo already has
  `CODEOWNERS`) makes the review trail visible to the scanner over time.
- This check improves *historically*: it looks at the last N commits, so
  the score climbs as reviewed PRs replace direct pushes.

### 3. Pinned-Dependencies (install-time pip / npm) (weight: high)

The Actions side is pinned, but Scorecard also parses shell scripts and
flags unpinned package installs. `payload/bin/setup-agent-venv` runs
`pip install --upgrade <pkgs>` with no version constraints, and
`scripts/install.sh` runs `npm install -g --ignore-scripts yarn pnpm
typescript ts-node` unpinned. The `@earendil-works/pi-*` packages also
track npm `latest`, but their registry-provided integrity hashes are
verified before their tarballs are passed to `npm install
--ignore-scripts`.

Suggestions:

- Pin the Python toolkit. Move the package list into a
  `requirements.txt` (or constraints file) with `==` versions and a
  hash-locked variant (`pip install --require-hashes -r ...`). Drop
  `--upgrade` so the pinned versions are authoritative.
- Pin the globally-installed npm tools (`yarn`, `pnpm`, `typescript`,
  `ts-node`) to explicit versions, mirroring how `pi-ai` /
  `pi-coding-agent` are already pinned via `*.version` files. Continue
  using `--ignore-scripts`.
- Pin apt/NodeSource bootstrap steps where feasible (pin
  the NodeSource setup to a known distribution, verify GPG keys by
  fingerprint rather than trusting whatever the endpoint serves).
- A committed `requirements.txt` / `package.json` has a useful
  side-effect: it gives **Dependency-Review** and Dependabot real
  manifests to scan (see check 5).

### 4. Fuzzing (weight: medium)

Almost certainly scoring 0 — there is no fuzz harness. The project has
genuinely fuzzable surfaces: the policy engine
(`payload/agent/policy.py`), the command/argument classifier, the audit
log redaction, and any prompt/response parsing in the chat server.

Suggestions:

- Add a lightweight Python fuzzing harness with
  [Atheris](https://github.com/google/atheris) targeting the policy
  classifier and the secret-redaction path — exactly the code where a
  miss is a security incident (a "destructive" command misclassified as
  "read-only", or an unredacted key in the audit log).
- Run it in CI on a nightly schedule (mirrors the existing
  `integration.yml` cadence). Even a single committed harness that
  Scorecard can detect moves this check off 0.
- OSS-Fuzz integration would score full marks but is heavier; the
  in-repo Atheris harness is the pragmatic first step.

### 5. Dependency-Update-Tool coverage (weight: high)

Dependabot is enabled, but `.github/dependabot.yml` only declares the
`github-actions` ecosystem. The agent payload pulls in **pip** and
**npm** packages, which are currently invisible to automated updates.

Suggestions:

- Add `pip` and `npm` ecosystems to `dependabot.yml`, pointing at the
  committed `requirements.txt` / `package.json` from check 3. This both
  strengthens this check and feeds **Vulnerabilities** and
  **Dependency-Review** with real manifests to evaluate.

### 6. CII-Best-Practices (weight: low, but a guaranteed 0 today)

Scorecard awards this only if the project holds an
[OpenSSF Best Practices](https://www.bestpractices.dev) badge. There is
no badge today, so it scores 0.

Suggestions:

- Register the project on bestpractices.dev and complete the
  questionnaire. The repo already satisfies most "passing" criteria
  (versioned releases, `CONTRIBUTING.md`, `CODE_OF_CONDUCT.md`,
  `SECURITY.md`, CI, static analysis), so this is mostly form-filling.
- Add the resulting badge to `README.md` next to the existing badges.

### 7. Maintained (weight: high)

Scorecard rewards recent commit and issue activity (commits in the last
~90 days, issues addressed). For a young project this can wobble.

Suggestions:

- Keep a steady cadence of merged PRs (the security/pinning work above
  naturally supplies several) and respond to issues. Nothing to "fix" in
  code; it is a function of ongoing activity, so schedule small,
  regular, reviewed changes rather than infrequent large drops.

### 8. Vulnerabilities (weight: high)

Driven by open advisories (OSV) against the repo's dependencies. With no
committed pip/npm manifests, the scanner has little to flag — but once
manifests are committed (check 3/5), keep them clean.

Suggestions:

- After committing manifests, watch the OSV/Dependabot alerts and keep
  the pinned versions current so this check stays at 10.

## Lower-priority / likely-already-fine

- **Contributors** — rewards contributors across multiple organisations;
  effectively out of the maintainer's direct control on a small project.
  Not worth engineering for.
- **Webhooks** — experimental; ignore for aggregate purposes.

## Suggested order of work (highest leverage first)

1. **Branch protection on `main`** with required reviews, required
   status checks, and "include administrators" — and give the Scorecard
   workflow an admin read token so it can see the settings. *(Fixes
   Branch-Protection and, over time, Code-Review — the two heaviest
   drags.)*
2. **Commit pinned `requirements.txt` and `package.json`**, switch
   `setup-agent-venv` and the global npm install to those pinned
   versions, and drop `--upgrade`. *(Fixes Pinned-Dependencies; unlocks
   Dependency-Review/Vulnerabilities.)*
3. **Extend `dependabot.yml`** to cover `pip` and `npm`. *(Fixes
   Dependency-Update-Tool coverage.)*
4. **Add an Atheris fuzz harness** for the policy classifier and audit
   redaction, run nightly. *(Moves Fuzzing off 0.)*
5. **Earn the OpenSSF Best Practices badge** and add it to `README.md`.
   *(Fixes CII-Best-Practices.)*
6. **Keep merging reviewed PRs and triaging issues.** *(Sustains
   Maintained and Code-Review.)*

Items 1–3 alone should push the aggregate comfortably past 6, because
they target the highest-weight checks that a "6" repository typically
fails. Items 4–6 then carry it toward the 8+ range. None of these
changes weaken the project's existing strengths (least-privilege tokens,
SHA-pinned actions, signed releases, CodeQL), so the work is purely
additive.
