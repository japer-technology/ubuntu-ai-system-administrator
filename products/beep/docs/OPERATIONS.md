# Policy, tools, audit, TTL, and family operations

## Policy path

The live policy is `/etc/beep/policy.yaml`. It is root-owned, mode `0644`, and
read by the `beep` service. The manager validates its supported YAML subset,
class names, approvals, confirmation values, rules, tool overrides, and
budgets. An invalid policy falls back to destructive classification at runtime
and fails lifecycle verification. Repair restores the shipped safe policy;
the recovery snapshot retains the former file.

| Class | Default treatment |
| ----- | ----------------- |
| `read_only` | May run automatically |
| `chat_schedule` | May schedule one bounded visible continuation |
| `user_change` | Requires operator approval |
| `system_change` | Requires operator approval |
| `network_change` | Requires operator approval |
| `destructive` | Requires approval and the exact destructive phrase |

All matching command rules are considered; the highest-risk result wins.
Unknown commands and unknown policy classes are destructive. A tool-class
override can name only a class above.

## Closed tools

`payload/agent/tools.py` is the complete model-visible registry. Major groups
include:

- system, disk, process, service, network, package, file, and web inspection;
- bounded package, service, user-file, system, network, and destructive
  mutations;
- reactivation scheduling;
- family `agent.list`, `agent.status`, `agent.plan`, and `agent.manage`; and
- the root-capable command runner governed by command classification.

Unknown names, extra properties, wrong types, stale approvals, and exceeded
per-turn budgets are rejected. The model never selects a raw family
entrypoint, release URL, product path, correlation ID, or plan digest outside
the fixed family-manager flow.

## Approval and audit

An elevated tool proposal is shown to the authenticated operator with its
classification and bounded arguments. Approval applies to that exact pending
call. Destructive calls additionally compare the phrase in the current policy.
Denial, expiry, cancellation, execution, failure, and bounded output metadata
are recorded.

The append-only JSONL audit defaults to `/var/log/beep/audit.jsonl`. It records
event and correlation identifiers, operation or tool, classification,
decision, timing, exit status, and output digests. It omits credentials and
normally omits raw output. `beep-audit-recent` reads the local trail;
`beep-diagnostics` creates a redacted support bundle.

## Time to Live and terminal death

The default TTL is seven days. `/ttl`, `/ttl <duration>`, and the authenticated
TTL API inspect or extend it. Extension begins at the later of now or the
current expiry and never shortens the timer.

`/ttl --die`, `POST /api/ttl` with `{"die":true}`, or root
`beep-manage kill` writes a permanent tombstone. It cancels active turns and
pending reactivation, revokes sessions, shuts down chat, and causes the bound
health timer to stop. Missing or corrupt state is also dead. Resume, update,
repair, and reinstall cannot revive it. Deliberate recovery requires complete
state purge followed by a fresh install.

Reactivation permits one global pending continuation between 5 and 3,600
seconds, before remaining TTL. The operator can inspect, cancel, reset, or
disable it. A busy conversation defers rather than overlaps. Death, missing
conversation, disabled scheduling, or provider failure terminates the record
with audit evidence.

## Product lifecycle

| Operation | Effect |
| --------- | ------ |
| `describe` | Return the validated descriptor |
| `status` | Report version, suspension, death, and remaining TTL |
| `verify` | Check marker, runtime, policy, credentials, services, family assets, and sibling boundary |
| `doctor` | Return the same diagnosis without verify's failing exit |
| `install`, `repair`, `update` | Plan, snapshot when installed, converge, health-check, receipt, and auto-recover on failure |
| `backup` | Stop useful work, archive Beep configuration/state/logs, verify, and resume only if alive |
| `rollback` | Validate and restore the latest compatible recovery snapshot |
| `suspend`, `resume` | Stop or conditionally resume useful Beep services |
| `kill` | Write terminal death and stop useful work |
| `uninstall` | Remove proved Beep resources; retain state by default or purge with exact confirmation |

Every mutation requires confirmation, a product lock, recomputed plan digest,
an audit event, and a receipt unless complete purge removes the receipt after
writing final journal evidence.

## Family management

`/opt/beep/bin/beep-agents` manages only
`imaginary-friend`, `curriculum-flame`, `eric`, and `llama`. Beep itself is not
a target of its family manager. `list` and `status` are read-only. `prepare`
downloads and verifies a catalogue release. `plan` accepts only target
mutations. `manage` requires the exact correlation and plan digest, then
verifies target descriptor, marker, receipt, and outcome before atomically
updating Beep's inventory.

The production `family/catalog.json` remains empty until each target release
and family-admission gate passes.
