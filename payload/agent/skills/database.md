<!-- triggers: database, databases, postgres, postgresql, psql, mysql, mariadb, mongodb, sqlite, sqlite3, redis, pg_dump, mysqldump -->
# Skill: local databases

This skill is loaded when the operator mentions PostgreSQL, MySQL/
MariaDB, SQLite or another database engine running on this machine.

Operating rules:

- Inspect before touching data. `svc.status` on `postgresql`,
  `mariadb` or `mysql`, `sudo -u postgres psql -c '\l'`,
  `sudo mysql -e 'SHOW DATABASES;'` and `du -sh /var/lib/postgresql`
  are `read_only` and auto-run. Say which engine, which version and
  which data directory you are talking about — a machine can host
  several.
- A database is the operator's data, not configuration. `DROP
  DATABASE`, `DROP TABLE`, `TRUNCATE`, `DELETE` without a `WHERE`,
  `dropdb`, `dropuser` and removing a data directory are `destructive`
  and need the exact confirmation phrase. Ask what the backup is before
  the operator confirms, not after.
- Read-only SQL is fine; writes are not implicit. `SELECT`, `EXPLAIN`
  and the catalogue views answer most questions. Show any statement
  that mutates rows or schema in full, wrap it in a transaction where
  the engine supports one, and say how many rows it is expected to
  touch.
- Back up with the engine's own tool, not by copying files from under
  a running server: `pg_dump`/`pg_dumpall`,
  `mysqldump --single-transaction`, or
  `sqlite3 <file> '.backup /tmp/copy.db'`. Write the
  dump to `/tmp` or a path the operator names, report its size, and
  confirm it is non-empty before proposing anything destructive.
- Never pass a password on the command line (`-p<secret>`,
  `PGPASSWORD=…` inline). It lands in the process list, the shell
  history and the audit log. Use the engine's peer/socket
  authentication, `~/.pgpass` or a client config file with `0600`
  permissions. See the `secrets` skill.
- Keep servers on loopback. PostgreSQL's `listen_addresses`, MySQL's
  `bind-address` and Redis's `bind`/`protected-mode` default to local
  for good reason; publishing one to the LAN is a `network_change` that
  changes the machine's exposure, and an unauthenticated Redis or
  MongoDB on `0.0.0.0` is a well-known compromise path.
- SQLite files are ordinary files, and that is the trap: copying one
  while a writer holds it yields a corrupt copy, and deleting the
  `-wal`/`-shm` sidecars loses committed data. Stop the writer or use
  `.backup`.
- Ubuntu AI System Administrator's own conversation history is SQLite under
  `/opt/ai-zombie/state/`. It is the agent's memory and part of the
  audit story — never delete, vacuum or rewrite it to "clean up", and
  never edit the audit log at all.
- Major-version upgrades migrate on-disk formats and can be one-way
  (`pg_upgradecluster`, `mysql_upgrade`). Never start one as a side
  effect of an `apt` upgrade without saying it is happening and that a
  verified dump exists.
- Report row counts and sizes rather than dumping result sets. Bound
  every query with a `LIMIT` and never echo personal data out of a
  table into the transcript.
