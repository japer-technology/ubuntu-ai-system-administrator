# Troubleshooting

| Symptom | Check | Recovery |
| ------- | ----- | -------- |
| Port conflict | `ss -ltn 'sport = :8080'` | Stop or reconfigure the unmanaged listener; Llama's port is fixed |
| Service fails | `journalctl -u llama-server.service` | Run `llama-manage verify`, then a reviewed repair |
| Runtime checksum fails | `llama-manage verify --json` | Repair re-downloads only the pinned runtime |
| Model checksum or size fails | `llama-manage verify --json` | Repair re-downloads only the approved model |
| Service intentionally stopped | `llama-manage status` | Use `resume`; inspect whether boot intent is disabled |
| Ownership collision | Product error and `stat` on named path | Reconcile manually; the lifecycle will not adopt it |
| Update plan changed | Preview again | Review the new digest and only then execute |
| No rollback available | Check `/opt/llama.cpp/rollback` | Restore an operator backup or install a reviewed release |

`doctor` succeeds when it produces a diagnosis, even if the product is
degraded. `verify` returns non-zero for a failed required check.

Do not solve a failure by widening the listener, disabling systemd hardening,
removing ownership checks, or substituting an unlisted binary or model.
