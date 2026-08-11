# Recovery

Start with:

```bash
sudo beep-manage status --json
sudo beep-manage doctor --json
sudo journalctl -u beep-chat.service -u beep-health.service
beep-audit-recent --all
```

Do not delete or replace a marker merely to bypass ownership validation.

| Condition | Meaning | Bounded recovery |
| --------- | ------- | ---------------- |
| `NOT_INSTALLED` | No valid marker exists | Inspect collisions; install only from verified source |
| `OWNERSHIP_COLLISION` or `UNSAFE_PATH` | A user, group, path, type, or link is not proved Beep-owned | Stop and identify the owner; do not force deletion |
| `INVALID_MARKER` | Installation identity cannot be trusted | Restore marker and product from a verified backup or remove only after manual ownership review |
| Runtime, policy, credential, or service check fails | Beep is degraded and useful service must not be trusted | Run reviewed `repair`; rotate credentials if exposure is possible |
| `HEALTH_CHECK_FAILED` during converge | New state failed the gate | Confirm automatic rollback evidence, then run doctor |
| `AUTOMATIC_ROLLBACK_FAILED` | Both convergence and product restoration failed | Keep services stopped; restore a verified external backup |
| `ROLLBACK_INTEGRITY_FAILED` | Snapshot identity, path, ownership, or digest changed | Do not use it; restore an external backup |
| `state_missing` or `invalid_state` | Lifecycle fails closed as dead | Inspect tampering or storage loss; do not synthesize a live state |
| `expired` or `operator_killed` | Terminal death | Retain for evidence or perform complete purge and a deliberate fresh install |
| Lost chat password | Authentication cannot succeed | Supply a new protected password file to root `repair`; all sessions are revoked |
| Malformed policy | Runtime uses destructive fallback and verify fails | Preserve the file, run repair to restore the reviewed safe default, then reapply reviewed changes |
| Provider unavailable | Local control remains but model work fails | Inspect provider status, rotate only the affected credential, retry later |
| Family outcome verification fails | Target may have changed but Beep did not accept its evidence | Inspect both correlated audits and target receipt; do not hand-edit inventory |

Automatic rollback covers Beep-owned code, configuration, state, host files,
permissions, and service state captured in the recovery snapshot. It cannot
reliably reverse system packages, network calls, provider actions, target
product work, or an approved root command.

Before complete purge, copy any required conversation export, audit, receipt,
inventory, backup, and journal evidence to a protected operator destination.
