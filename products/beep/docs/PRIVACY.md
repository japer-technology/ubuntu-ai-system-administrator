# Privacy, retention, export, and deletion

Beep is a single-machine product. It stores operator data locally and sends
model context only to the provider the operator configures.

| Data | Location or recipient | Default retention | Export or deletion |
| ---- | --------------------- | ----------------- | ------------------ |
| Conversations, summaries, tool events, and reactivation | `/var/lib/beep/runtime/conversations.db`, mode-protected | Until explicit deletion or state purge | Authenticated conversation JSON export; confirmation-bound conversation deletion |
| Audit events | `/var/log/beep/audit.jsonl` | Installation lifetime and log rotation | `beep-audit-recent`; remove only through the root lifecycle |
| Management receipts | `/var/log/beep/receipts` | Installation lifetime | Copy as JSON; complete uninstall removes them |
| Credentials and policy | `/etc/beep` | Until rotation or removal | Never exported by the chat API; root-controlled backup/removal |
| Recovery snapshots and backups | `/var/lib/beep/recovery` and operator destination | Until replaced or operator deletion | Root-controlled archives and lifecycle purge |
| Family inventory | `/var/lib/beep/agents/inventory.json` | Until target purge or Beep purge | Secret-free JSON inspection and removal |
| Model request context | Configured cloud or loopback provider | Provider terms | Provider controls plus local conversation deletion |

Provider requests can include the current system prompt, relevant conversation
messages, machine facts, selected skill instructions, proposed tool calls, and
bounded tool results. Beep does not intentionally send provider credentials,
chat password material, session keys, lifecycle secrets, sibling credentials,
or full audit logs to the model.

Use `GET /api/conversation/<id>/export` after authentication to receive a
portable JSON record. Delete one conversation with
`POST /api/conversation/<id>/delete` and the exact confirmation
`DELETE CONVERSATION <id>`. SQLite foreign keys remove its messages, tool
events, and pending reactivation. Audit evidence records the deletion without
copying conversation content.

The normal uninstall retains configuration and state. Complete deletion
requires `--purge` and the exact lifecycle confirmation `DELETE BEEP STATE`.
Backups and previously exported files are outside that purge and remain the
operator's responsibility.

Beep does not encrypt local state. Host root, a root-capable peer, filesystem
backups, provider operators, and anyone with the operator's exported files may
be able to read it.
