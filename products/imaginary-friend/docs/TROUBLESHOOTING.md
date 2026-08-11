# Troubleshooting

Start with:

```bash
sudo /usr/local/sbin/friend-manage status --json
sudo /usr/local/sbin/friend-manage doctor --json
sudo friend-diagnostics --output-directory /root
```

Diagnostics omit the database, message text, workspace contents, password
hash, session material, and signing key. The systemd journal can still contain
platform-level failures, so review it before sharing.

## Common symptoms

| Symptom or code | Meaning and action |
| --------------- | ------------------ |
| `MISSING_INPUT`, exit `64` | Supply the named required unattended input; non-interactive mode never prompts |
| `MODEL_UNAVAILABLE`, exit `69` | Start the configured loopback model and confirm that `/v1/models` contains the selected ID |
| `UNSAFE_COLLISION`, exit `73` | A reserved identity, path, unit, command, port, or workspace is unmarked or has unexpected ownership; do not force adoption |
| `TARGET_BUSY`, exit `75` | Another mutation holds `/run/lock/imaginary-friend.lock`; wait for it rather than deleting a live lock |
| `PLAN_CHANGED`, exit `78` | Inputs or installation identity changed after review; render and approve a new plan |
| `SANDBOX_INVALID`, exit `78` | Keep Friend suspended and repair from the matching verified release |
| `WORKSPACE_CHANGED` | Restore the nominated root's device/inode or explicitly review a replacement through repair |
| Browser login loops | Confirm the exact `127.0.0.1:6767` or `localhost:6767` origin, then rotate the password if session state is suspect |
| Conversation works but is not saved | `history_enabled` is off; existing retained history is unaffected |

`verify` exits `1` when a required check fails. `doctor` exits `0` when it
successfully explains degraded state. Do not interpret a healthy `/healthz`
response alone as proof that credentials, workspaces, sandbox, model, and
ownership all validate; use `verify`.

For account loss, failed update, or retained-state recovery, see
[`RECOVERY.md`](RECOVERY.md). Report suspected vulnerabilities privately as
described in [`SECURITY.md`](SECURITY.md).
