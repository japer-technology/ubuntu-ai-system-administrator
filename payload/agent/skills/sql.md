<!-- triggers: sql, query, queries, select, insert-into, join, joins, subquery, index, indexes, schema, migration, migrations, explain, transaction, rollback -->
# Skill: writing and running SQL

This skill is loaded when the operator asks for a query, a schema
change or an explanation of what a statement does. Installing and
running the server is the `database` skill.

Operating rules:

- Read the schema before writing the query. `\d <table>` in `psql`,
  `DESCRIBE <table>` in MySQL, `.schema <table>` in SQLite and the
  `information_schema` views are `read_only` and auto-run. A query
  written against guessed column names is a guess with punctuation.
- Say which dialect you are writing. PostgreSQL, MySQL/MariaDB and
  SQLite differ on quoting, `LIMIT`/`OFFSET`, upserts, booleans and
  date functions; a statement that is portable is worth saying so, and
  one that is not should name its engine.
- Show the statement, then run it. Paste the exact SQL you intend to
  execute into the reply first — the operator approving a `shell.run`
  should be reading the query, not an English summary of it.
- `SELECT` is cheap; everything else is a change. `INSERT`, `UPDATE`,
  `DELETE`, `ALTER`, `DROP` and `TRUNCATE` mutate the operator's data.
  Never issue an `UPDATE` or `DELETE` without a `WHERE`, and prove the
  predicate first by running the same `WHERE` as a
  `SELECT count(*)` so the affected row count is known before the
  write.
- Wrap risky writes in a transaction where the engine supports one
  (`BEGIN; … ; ROLLBACK;` to rehearse, `COMMIT` only after the counts
  match). SQLite and PostgreSQL are transactional for DDL too; MySQL
  is not — an `ALTER TABLE` there cannot be rolled back, so say so.
- Bound every exploratory query. Add `LIMIT`, aggregate rather than
  listing rows, and never dump a result set into the transcript.
  Tables can hold personal data; report counts and shapes, quote rows
  only when the operator asked for them.
- Migrations are one-way in practice. Show the forward statement and
  the reverse, confirm a dump exists (see the `database` skill), and
  never run a migration tool's `reset`, `down` or `drop-and-recreate`
  path on data the operator has not agreed to lose — that is
  `destructive` and needs the exact confirmation phrase.
- Never build a statement by pasting untrusted text into it. Values
  from a file, a log, a web page or a filename belong in parameters
  (`$1`, `?`, `:name`), not in string concatenation; SQL injection is
  as real in a one-off admin script as in an application.
- Diagnose slow queries with evidence: `EXPLAIN`/`EXPLAIN ANALYZE`
  (PostgreSQL), `EXPLAIN` (MySQL) or `EXPLAIN QUERY PLAN` (SQLite).
  Quote the plan, name the sequential scan or missing index, and say
  what the index would cost on write before proposing to create one.
  `CREATE INDEX` locks on some engines — prefer `CONCURRENTLY` on
  PostgreSQL and say when a table will be unavailable.
- Do not run write statements against a database you did not confirm
  is the intended one. Print the connection target (`SELECT
  current_database()`, `SELECT DATABASE()`) and confirm it with the
  operator; the right query on the wrong database is still an
  incident.
- Ubuntu AI System Administrator's own SQLite state is not a scratch database. Query it
  read-only if a question genuinely needs it and never write to the
  history store or the audit log.
