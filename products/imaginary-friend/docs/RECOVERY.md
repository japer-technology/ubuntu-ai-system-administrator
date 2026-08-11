# Recovery

Recovery must not weaken policy, adopt unmarked resources, or copy nominated
workspace contents into Friend state.

## Diagnose first

Run `friend-manage status --json`, `verify --json`, then `doctor --json`.
Preserve the correlation IDs and redacted diagnostics. Do not edit the SQLite
database, ownership marker, policy, unit, or recovery directory by hand while
the service is running.

## Common recovery paths

| Condition | Recovery |
| --------- | -------- |
| Root-owned code, unit, configuration, or permissions drifted | Stop Friend and run a reviewed `repair` from the exact installed version |
| Configured model is unavailable | Restore the loopback endpoint and model ID, then verify or resume |
| Workspace root moved, mounted, or replaced | Keep Friend suspended; restore the recorded device/inode or review a new nomination through repair |
| Owner password lost | As root, supply a new password file to `repair`; every session is revoked |
| Update failed after staging | Use `doctor`, then the product-owned `rollback` if its runtime and recovery snapshot validate |
| Software removed with state retained | Run a reviewed install from a compatible release; retained suspension and credentials remain in force |
| SQLite integrity failed | Keep the service stopped and recover from protected operator backup media or the compatible product recovery snapshot |

## Backups

`friend-manage backup` accepts an absolute root-owned destination outside
Friend state and workspaces. The mode-`0600` archive contains a consistent
SQLite copy without sessions, root-controlled configuration and signing
material, the installation marker, and a manifest. It excludes nominated
workspace files and is not encrypted.

The fixed lifecycle interface exposes rollback rather than an arbitrary
archive-restore operation. Archive recovery is therefore an operator disaster
procedure: preserve the original installation, verify the archive and product
version, and test restoration on a disposable VM before replacing any state.
Do not extract an untrusted archive over a live installation.

## Retained and complete removal

State-preserving uninstall is the supported reversible removal path. Complete
uninstall deliberately requires a separate destructive confirmation. Neither
path removes workspace files; protect or relocate those files according to the
human owner's normal backup policy.
