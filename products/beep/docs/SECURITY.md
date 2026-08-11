# Security and threat model

Beep intentionally grants passwordless `sudo` to its dedicated service
identity. Compromise of Beep is compromise of the host. The policy and approval
flow reduce accidental and model-driven harm; they do not sandbox an approved
root command or protect Beep from another root-capable product.

## Protected assets

- chat password hash, session-signing key, provider credentials, and active
  sessions;
- policy, configuration, code, lifecycle tombstone, history, audit, receipts,
  recovery snapshots, family catalogue, and inventory;
- operator files and host state reachable through approved root tools; and
- every sibling product's credentials, data, marker, lifecycle, and release
  cache.

## Threats and controls

| Threat | Prevention and detection | Recovery |
| ------ | ------------------------ | -------- |
| Prompt injection or malicious model requests root work | Closed tool registry, exact schemas, highest-risk policy result, explicit approval, destructive phrase, budgets, output limits, and audit | Deny, stop the turn, inspect audit, suspend or kill |
| Local cross-site or unauthenticated access | Loopback Host pinning, same-origin mutations, strict JSON content type and size, PBKDF2 password, signed expiring cookie, and session revocation | Rotate password and session key; repair |
| Corrupt lifecycle revives useful work | Strict finite state schema, mode and owner checks, fail-closed startup, durable tombstone, service shutdown, and reinstall/resume rejection | Inspect status; purge and reinstall only if deliberate |
| Unsafe path or ownership takeover | Marker validation, no-follow protected files, symlink and type rejection, collision preflight, exact roots, and deployed-tree comparison | Stop, inspect ownership, restore verified snapshot |
| Malformed policy lowers approval | Semantic validation, destructive fallback, unknown-class promotion, manager verification, and safe-default repair | Restore reviewed policy and run verify |
| Dependency or release substitution | Pinned Node and npm digests, fixed repository workflow identity, checksums, SBOM, attestation, cosign bundles, bounded extraction, and catalogue digests | Reject artifact; retain prior version |
| Failed update leaves a mixed runtime | Services stop first, recovery snapshot, atomic file replacement, health gate, and automatic product rollback | Run doctor; use explicit rollback or verified backup |
| Family target confuses identity or outcome | Fixed catalogue product, tag, asset, descriptor, entrypoint, correlation, plan digest, receipt, dual audit, and inventory validation | Do not advance inventory; inspect both products |
| Audit or receipt omits secrets but loses useful evidence | Stable IDs, statuses, digests, timing, redaction, protected append, and manager failure event | Preserve local journal and product logs; collect diagnostics |

## Residual risks

- An authorised destructive command can erase data or make the host unbootable.
- A compromised process can use the account's sudo policy outside the Python
  process; this is inherent in the declared root-capable design.
- Loopback authentication is a shared secret, not per-human attribution.
- PBKDF2 slows password guessing but cannot prevent denial of service by a
  hostile same-host user.
- Conversation databases and backups are permission-protected, not encrypted.
- System package changes and external side effects cannot always be reversed by
  product rollback.
- Two root-capable peers can inspect or alter each other's resources despite
  namespace and audit separation.

## Reporting

Do not publish a suspected vulnerability or real diagnostic bundle in an
issue. Follow the repository's private process in
[`SECURITY.md`](../../../SECURITY.md), identify Beep and its version, and omit
real credentials, conversations, host data, and sibling state.
