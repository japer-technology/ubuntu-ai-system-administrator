# Architecture and trust boundaries

## Components

| Component | Source | Responsibility |
| --------- | ------ | -------------- |
| Root lifecycle | `payload/agent/beep/management.py` | Strict plans, ownership, install, integrity, backup, update, recovery, kill, receipts, and removal |
| Chat service | `payload/agent/server.py` | Loopback HTTP, authentication, conversations, approvals, streaming, lifecycle enforcement, and operator APIs |
| Authentication | `payload/agent/auth.py` | PBKDF2 password verification and signed 12-hour Beep-only sessions |
| Agent bridge | `payload/agent/pi_mono.py` and bridge files | Bounded structured model loop using pinned Node packages |
| Policy and tools | `policy.py`, `tools.py`, `runner.py` | Closed schemas, highest-risk classification, approval, execution, and output bounds |
| Audit and history | `audit.py`, `history.py` | Secret-minimised JSONL evidence and Beep-only SQLite state |
| Lifecycle tombstone | `lifecycle.py` | Durable TTL and permanent death decision consulted before useful work |
| Family manager | `family.py`, `beep-agents` | Verified catalogue releases, exact target plans, correlated outcomes, inventory, and manager audit |
| systemd | `payload/systemd/` | Dedicated `beep` execution, loopback service, and bound health timer |

## Chat data flow

```text
browser on loopback
  -> Host/origin/body/authentication checks
  -> Beep application and conversation history
  -> pinned pi-mono bridge and configured model provider
  -> exact closed tool schema
  -> policy classification and operator approval
  -> bounded runner, including approved sudo
  -> result, history, and secret-minimised audit
```

The model cannot invoke a shell merely by emitting text. A tool name must
exist, its arguments must satisfy the exact schema, the current policy must
classify it, required approval must still be valid, and the runner must record
the result.

## Lifecycle flow

The root lifecycle is separate from the `beep` service process. It validates
the product descriptor and platform, refuses unowned collisions, converges the
dedicated identity and paths, installs protected credentials, copies and
root-owns code, writes units, starts only Beep services, verifies boundaries,
then writes the ownership marker and correlated receipt.

Existing install, repair, and update operations stop useful work and create a
verified recovery snapshot first. A later failure invokes product-owned
rollback before returning the bounded failure. System-package changes cannot
be transactionally removed; recovery therefore verifies the restored product
and reports any remaining host-level remediation.

The lifecycle file is owned by `beep`, mode `0600`. Missing, malformed,
non-finite, non-regular, or expired state is dead. Death cancels active turns
and pending reactivation, revokes sessions, stops the chat service, and stops
the bound health timer. Reinstall and resume never clear a tombstone.

## Family-manager flow

Beep reloads the root-owned catalogue for each operation, downloads only fixed
HTTPS release assets, verifies digests and signing identity, extracts within
bounds, validates the target descriptor, and invokes only that target's
installed lifecycle. A mutation requires the exact prior correlation ID and
plan digest. The target writes its receipt and audit; Beep independently
verifies and records the outcome. Post-target verification failures receive
correlated manager-side failure evidence and do not claim a successful
inventory transition.

## Owned namespaces

- identity: `beep` user and group;
- code: `/opt/beep`;
- configuration and credentials: `/etc/beep`;
- state and recovery: `/var/lib/beep`;
- audit and receipts: `/var/log/beep`;
- listener and cookie: `127.0.0.1:58989`, `beep_session`; and
- units and commands: names prefixed with `beep`.

Other products remain outside these roots. Unix ownership cannot isolate Beep
from another compromised root-capable process; independent namespaces prevent
accidental sharing and make lifecycle evidence attributable.
