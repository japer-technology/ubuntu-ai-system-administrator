# Architecture

## Owned resources

The descriptor in `PRODUCT.json` declares the stable roots, `git` identity,
`forgejo.service`, and loopback port 3000. The lifecycle additionally owns:

- the Forgejo PostgreSQL role and database named by `app.ini`;
- one exactly marked block in the shared `/etc/caddy/Caddyfile`;
- `/etc/avahi/services/forgejo.service`;
- the exported and host-trusted Caddy local CA copies; and
- `/usr/local/bin/forgejo` plus its checksum record.

It never owns `forgejo-runner.service`, Docker, runner state, or resources
outside the declared Forgejo boundary.

## Request path

`scripts/manage.sh` selects source or installed management code and executes
the standard-library Python lifecycle. Mutations require root, a lifecycle
lock, a confirmed plan, and a valid product or narrowly validated legacy
ownership boundary. Responses, receipts, and append-only audit events use the
stable product lifecycle contracts.

## Network and runner boundary

Forgejo binds `127.0.0.1:3000`; Caddy terminates internal-CA TLS on port 443.
Avahi advertises `_https._tcp`.

For a co-located runner, registration uses the loopback server URL. Job
containers use host networking to reach the loopback Caddy edge, an explicit
`.local` host mapping so image-specific mDNS is unnecessary, and a read-only
mount of the host CA bundle. Global job environment variables select that CA
for Git, OpenSSL consumers, Python Requests, and Node.js. Workflow-provided
volumes remain denied, privileged containers remain disabled, and jobs do not
receive the Docker socket.

Server backup, update, repair, rollback, suspend, and uninstall stop the runner
first when required. A previously active runner is restarted only after the
Forgejo health gate passes. Server uninstall refuses while runner resources
remain.
