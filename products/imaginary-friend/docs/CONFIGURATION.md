# Configuration and owner interfaces

Unknown `FRIEND_*` names and unknown request keys fail closed.

## Interactive installation

Run `./scripts/install.sh` from the product directory. The installer asks for
the existing non-root human owner, an optional owner password, the loopback
model endpoint and model ID, and conversation and audit retention periods.
Press Enter to accept each displayed default. An empty password response
generates a strong password that is shown once after installation.

The installer displays all non-secret settings, the plan digest, and every
mutation step before asking for approval.

## Unattended install, repair, and update inputs

| Environment variable | Request input | Rule |
| -------------------- | ------------- | ---- |
| `FRIEND_NONINTERACTIVE=1` | command flag | Never prompt; missing required input exits `64` |
| `FRIEND_OWNER_USER` | `owner_user` | Existing non-root local owner; required for first unattended install |
| `FRIEND_OWNER_PASSWORD_FILE` | `owner_password_file` | Absolute root-owned regular file with no group/other access; required for first unattended install |
| `FRIEND_MODEL_BASE_URL` | `model_base_url` | Plain HTTP loopback URL; default `http://127.0.0.1:8080/v1` |
| `FRIEND_MODEL` | `model` | Non-empty model ID; required for first unattended install |
| `FRIEND_WORKSPACES_FILE` | `workspaces_file` | Optional root-owned JSON array of canonical absolute paths |
| `FRIEND_HISTORY_RETENTION_DAYS` | `history_retention_days` | Integer `1..365`; default `30` |
| `FRIEND_AUDIT_RETENTION_DAYS` | `audit_retention_days` | Integer `30..3650`; default `90` |

These configuration inputs are accepted by `install`, `repair`, and `update`.
`backup` accepts only `backup_destination`. Other lifecycle operations accept
an empty `inputs` object; values inappropriate for the selected operation are
rejected instead of ignored. `uninstall` also requires the top-level boolean
`retain_state`.

Secret values never belong in arguments, ordinary environment variables,
plans, JSON output, receipts, diagnostics, or audit fields. A password file
contains the password as one UTF-8 line and should use root ownership and mode
`0600`. Owner passwords must contain at least 12 characters and no more than
1,024 UTF-8 bytes.

## Workspace nomination file

The file contains a JSON array, for example:

```json
[
  "/srv/imaginary-friend/projects"
]
```

The product-created `/srv/imaginary-friend/workspace` remains nominated
automatically. New roots must be direct children of
`/srv/imaginary-friend`. An existing additional root is accepted only after a
prior Friend install created `friend-share` and the root already uses that
group with group read, write, and execute access plus setgid inheritance.
Repair with a reviewed workspace file adds or restricts root-controlled
nominations; it never recursively changes an existing tree.

## Runtime owner controls

The authenticated loopback API exposes:

| Method and route | Purpose |
| ---------------- | ------- |
| `POST /api/login`, `POST /api/logout` | Create or revoke one owner session |
| `GET /api/session` | Validate the session and rotate its CSRF token |
| `POST /api/chat` | Send text and explicitly selected file context |
| `GET /api/conversations`, `GET /api/conversations/<id>` | Inspect retained history |
| `DELETE /api/conversations/<id>` | Delete one conversation and its messages |
| `GET /api/conversations/export` | Download versioned JSON without workspace contents or secrets |
| `GET /api/workspaces`, `PATCH /api/workspaces/<id>/state` | Inspect or restrict an installed nomination |
| workspace `list`, `read`, `write`, `mkdir`, `move`, and `path` routes | Perform bounded file operations |
| `GET /api/workspace-events` | Inspect content-free workspace operation history |
| `GET`, `PATCH /api/settings` | Inspect or change retention and the loopback model |
| `POST /api/password`, `POST /api/sessions/revoke` | Rotate the password or revoke all sessions |
| `GET /api/health`, `POST /api/suspend` | Check local state/provider health or activate the kill switch |

Every state-changing request needs an exact Friend origin, an authenticated
cookie, and the current `X-Friend-CSRF` value. Workspace identifiers are
opaque IDs and child paths are canonical relative paths. Provider changes are
probed before they are stored. Root-assisted resume uses the installed
configuration and does not accept configuration changes.
