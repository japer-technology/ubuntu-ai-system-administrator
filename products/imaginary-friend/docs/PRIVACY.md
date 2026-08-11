# Privacy, retention, and deletion

Imaginary Friend is local-first, not provider-free. The configured loopback
model may itself proxy data elsewhere; the operator is responsible for
understanding that model service.

## Data inventory

| Data | Location or recipient | Default retention |
| ---- | --------------------- | ----------------- |
| Conversations and messages | `/var/lib/imaginary-friend/friend.db` | 30 days from last conversation activity |
| Workspace nominations and operation events | Friend database | Paths and outcomes for 90 days by default |
| Workspace file contents | Nominated workspace | Controlled by the owner; never copied into Friend backups |
| Runtime audit | `/var/log/imaginary-friend/audit.log` | 90 days by default through product-aware rotation |
| Sessions | Friend database | 12 hours maximum; revoked on rotation, suspension, or uninstall |
| Model context | Configured loopback endpoint | Typed context plus only files explicitly selected for that turn |

History retention is configurable from 1 to 365 days. Changing the window
recomputes existing conversation expiry from its last activity. Disabling
history stops storage of future turns; it does not silently delete existing
history.

## Content minimisation

Operational audit and lifecycle receipts exclude prompts, model output,
message text, file contents, raw passwords, hashes, signing keys, and session
material. Workspace events retain only the workspace identifier, relative
path, operation, result, and timestamp.

## Owner controls

Authenticated routes provide conversation listing, deletion, and versioned
JSON export; workspace inspection and restriction; session revocation;
password rotation; retention settings; provider health; and suspension.
Exports contain conversation and configuration metadata but exclude session
material, password hashes, operational audit internals, and workspace file
contents.

Removing a workspace nomination does not delete its files. State-preserving
uninstall retains protected Friend state for recovery. Complete uninstall
requires the exact destructive confirmation and removes Friend state but still
does not delete nominated workspace files. Backup archives are mode `0600`,
exclude workspace contents and live sessions, and are not encrypted.

The product does not use conversation or workspace content for training.
Third-party rights in material selected by the owner remain the owner's
responsibility.
