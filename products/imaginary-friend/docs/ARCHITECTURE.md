# Architecture

Imaginary Friend owns its source, installation, runtime, state, release, and
Python environment below `/opt/imaginary-friend`.

## Components

| Component | Identity | Responsibility |
| --------- | -------- | -------------- |
| `friend-manage` | root | Validate and execute the product lifecycle contract |
| `imaginary-friend-chat.service` | `friend` | Serve the loopback owner UI and closed HTTP API |
| `FriendApplication` | `friend` | Mediate authentication, policy, model calls, history, and workspace operations |
| `Database` | `friend` | Store settings, authentication hashes, sessions, conversations, and workspace metadata in SQLite |
| `Workspace` | `friend` plus `friend-share` | Resolve descriptor-relative paths without following links or crossing the nominated root |
| `ModelClient` | `friend` | Call only the configured OpenAI-compatible loopback endpoint |
| audit and receipts | service or root lifecycle | Record content-minimised runtime and correlated lifecycle events |

## Data flow

1. A browser connects to `127.0.0.1:6767` and authenticates with the
   product-specific owner password.
2. State-changing requests pass same-origin and session-bound CSRF checks.
3. Conversation turns use stored context only when history is enabled.
4. Workspace text enters model context only when the owner selects a specific
   file for that turn.
5. `ModelClient` validates the loopback URL and makes bounded model-list or
   completion requests without redirects.
6. Message text remains in SQLite according to retention settings. Operational
   audit records contain decisions, identifiers, paths, and outcomes, not
   message or file contents.

## Filesystem and process boundaries

Executable code, policy, configuration, unit files, lifecycle commands, and
the ownership marker are root-controlled. The service can write only its
database, export directory, audit log, and rendered workspace paths. The unit
uses `NoNewPrivileges`, an empty capability set, strict system protection,
device and namespace restrictions, restricted host paths, and loopback-only IP
policy.

Workspace operations keep the nominated root open by descriptor, walk each
relative component with `O_NOFOLLOW`, compare device and inode identity, reject
hard links and special files, use conflict-checked atomic replacement, and
perform moves with atomic no-replace semantics. Destructive changes require the
canonical relative path as confirmation.

## Lifecycle boundary

`scripts/manage.sh` and installed `/usr/local/sbin/friend-manage` implement the
same JSON contract. Mutations require root, a reviewed plan, the product lock,
and a valid marker or clean-install transaction. Direct operators and approved
automation use that exact entry point without receiving Friend credentials or
private content.

Same-version repair and reinstall use a transient recovery point and preserve
the previous-version runtime and state snapshot reserved for explicit rollback.
