# Operations

- `status`, `verify`, and `doctor` are read-only.
- `repair` converges owned files, database credentials, network boundaries,
  trust, and services without rotating recoverable secrets.
- `backup` stops server and runner briefly, then captures repositories,
  configuration, the verified binary, product source, and a PostgreSQL custom
  dump in a root-private checksum sidecar archive. If the archive completes but
  service restoration fails, the error identifies the protected archive that
  must be preserved.
- `update` creates a rollback backup before changing product or Forgejo
  versions.
- `rollback` validates the recorded archive digest, restores files and the
  originating product instance and database, then passes loopback and HTTPS
  health gates before restarting a previously active runner.
- `suspend` records server and runner boot intent, stops both services, and
  disables both units so a reboot cannot bypass suspension.
- `resume` validates static ownership and network boundaries before restoring
  recorded boot and active-service intent.
- `uninstall` removes runtime integration but retains state by default.

Inspect service failures with:

```bash
sudo journalctl -u forgejo.service
sudo journalctl -u postgresql.service
sudo journalctl -u caddy.service
sudo forgejo-manage doctor
```
