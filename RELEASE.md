# Release process

How to cut a new release of Ubuntu Zombie. For maintainers only.

## Cadence

There is no fixed cadence. Cut a release when:

- A security-impacting bug has been fixed (within two weeks of the
  fix landing on `main`).
- A user-visible feature has stabilised on `main` and the changelog
  for it is written.
- The `[Unreleased]` section of `CHANGELOG.md` has grown to "enough
  to justify a tag".

We use **date-time versioning**. Every version is the UTC timestamp
of the release, formatted `yyyy.mm.dd.hh.nn.ss` (year, month, day,
hour, minute, second — each zero-padded). For example, a release cut
at 2026-06-02 03:59:05 UTC has version `2026.06.02.03.59.05`. Versions
therefore sort chronologically and are never reused.

## Steps

1. **Land everything on `main`** that should be in the release.
   `main` must be green: `make lint && make test` plus all CI
   workflows.

2. **Update `VERSION`** to the new version (no `v` prefix, no
   leading/trailing whitespace). Use the current UTC timestamp in
   `yyyy.mm.dd.hh.nn.ss` form:

   ```bash
   date -u +%Y.%m.%d.%H.%M.%S > VERSION
   ```

3. **Update `CHANGELOG.md`**: rename the `[Unreleased]` heading to
   `[<version>] - <YYYY-MM-DD>` and start a fresh empty
   `[Unreleased]` section above it.

4. **Update `debian/changelog`**: prepend a stanza for the new
   version.

   ```
   ubuntu-zombie (2026.06.02.03.59.05) UNRELEASED; urgency=medium

     * See /CHANGELOG.md.

    -- Japer Technology <ops@japer.technology>  <RFC-2822 date>
   ```

5. **Open a "Release `<version>`" PR** with the three file changes above.
   Merge once green. When the `VERSION` change lands on `main`, the
   `Release` workflow automatically builds and publishes the matching
   GitHub Release.

6. **Watch the `Release` workflow** finish. It will:

   - Re-run lint + smoke.
   - Verify checksum-pinned Node bridge inputs.
   - Build the source tarball (`make package`).
   - Build the `.deb` (`make deb`).
   - Compute `SHA256SUMS`.
   - Generate an SPDX SBOM with Syft.
   - Generate a SLSA provenance attestation for the artifacts.
   - Keyless-sign every artifact with cosign.
   - Create the `v<VERSION>` tag if the workflow was triggered by the
     `VERSION` change on `main`.
   - Create the GitHub Release and upload everything.

7. **Manual fallback:** if you need to re-run a release for an already
   merged version, dispatch the `Release` workflow with the existing tag or
   push the matching tag from `main`:

   ```bash
   git fetch origin
   git checkout main
   git pull --ff-only
   git tag -s "v$(cat VERSION)" -m "Release v$(cat VERSION)"
   git push origin "v$(cat VERSION)"
   ```

   The tag *must* match `v<VERSION>` exactly; the release workflow
   refuses to publish otherwise.

8. **Verify the release page**:

   - Tarball, `.deb`, `SHA256SUMS`, SPDX, provenance (`*.intoto.jsonl`), and
     `.sig`/`.pem`/`.cosign.bundle` for each artifact must all be attached.
   - Download the assets into one directory, unpack the tarball, then run:

     ```bash
     mkdir ubuntu-zombie-<version>
     tar -xzf ubuntu-zombie-<version>.tar.gz -C ubuntu-zombie-<version>
     bash ubuntu-zombie-<version>/payload/bin/verify-release .
     ```

   - Release notes should contain the relevant CHANGELOG section and
     the verification command above.

9. **Announce** in the
   [Discussions › Announcements](https://github.com/japer-technology/ubuntu-zombie/discussions/categories/announcements)
   category. Link the release page.

## Hotfix releases

For a single security-impacting fix:

1. Branch from the previous release tag: `git checkout -b hotfix v2026.06.02.03.59.05`.
2. Cherry-pick the fix.
3. Follow steps 2–9 above. The new `VERSION` is simply the current
   UTC timestamp, so it naturally sorts after the release being fixed.

## Rolling back a release

GitHub Releases are immutable in spirit. To roll back:

1. Mark the release as "Pre-release" in the GitHub UI so it does
   not appear under "Latest".
2. Cut a new patch that supersedes it.
3. Update the release notes of the bad release with a link to the
   replacement.

Never delete an existing release: external installers may have
pinned to the tarball URL by SHA.

## What goes in a "non-release" build

Pushing to `main` creates a release only when `VERSION` changes. Other
pushes run CI and build the source bundle for sanity, but are never
published. Operators who track `main` use
`git pull && sudo ./scripts/install.sh install`.
