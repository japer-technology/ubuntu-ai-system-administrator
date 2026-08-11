<!--
Thanks for contributing. Please fill in the checklist below so reviewers
can move quickly. Delete sections that do not apply.
-->

## Summary

<!-- One or two sentences describing the change and the motivation. -->

## Related issues

<!-- e.g. "Closes #123", "Refs #45". -->

## Changes

<!-- Bulleted list of the meaningful changes. -->

## Checklist

- [ ] The installer remains **idempotent** — re-running `install` converges to the desired state without errors.
- [ ] The installer still supports **non-interactive** mode (`ZOMBIE_NONINTERACTIVE=1`) without prompting.
- [ ] Any new privileged behaviour goes through the **policy gate** and is written to the **audit log**.
- [ ] New external commands are justified, version-pinned where practical, and retried on transient network failures.
- [ ] No secrets, screenshots, or local state have been committed.
- [ ] `make lint` passes locally.
- [ ] `make test` passes locally.
- [ ] User-facing changes are documented under `docs/` and, if behaviour changed, noted in `CHANGELOG.md`.

## Risk / rollback

<!--
What is the worst case if this lands and is wrong? How would an
operator recover? (e.g. "sudo ./scripts/install.sh repair", or
"sudo ./scripts/install.sh uninstall".)
-->
