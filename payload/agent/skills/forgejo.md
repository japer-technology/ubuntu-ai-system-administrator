<!-- triggers: forgejo, gitea, forge, runner, caddy, avahi, mdns -->
# Skill: the optional Forgejo forge component

This skill is loaded when the operator mentions Forgejo, the Actions
runner, or the Caddy/Avahi edge that publishes it. Ordinary working-copy
questions belong to the `git` skill.

Operating rules:

- Forgejo is an *optional component* of this product, installed only
  when the operator asked for it (`install forgejo`, or the legacy
  `ZOMBIE_INSTALL_FORGEJO=1`). Check whether it is actually present
  (`svc.status` on `forgejo.service`, `fs.list` on `/etc/forgejo`)
  before answering as though it were.
- Know the shape: Forgejo listens on loopback only
  (`127.0.0.1:3000` by default) with PostgreSQL on `127.0.0.1:5432`;
  Caddy terminates HTTPS on `443` with its internal CA and
  reverse-proxies to the backend; Avahi advertises
  `https://<hostname>.local/`. Caddy is the only LAN-facing part —
  never move Forgejo itself onto `0.0.0.0` to "make it reachable".
- The installer owns this component. `verify forgejo`, `doctor forgejo`
  and `repair forgejo` are the supported way to inspect and correct it;
  they re-assert ownership and permissions on `/etc/forgejo`,
  `app.ini` and `/var/lib/forgejo` and restart the service. Prefer them
  over hand-editing.
- Editing `/etc/forgejo/app.ini` by hand is a privileged change: the
  file is deliberately `640` and owned by the service account, and
  Forgejo must be restarted to pick a change up. Read it first, keep a
  timestamped backup, and never widen its mode or its directory's mode
  to make an edit convenient.
- Unattended updates of an existing install need
  `FORGEJO_CONFIRM_UPDATE=YES`, and reusing an existing database or
  role needs `FORGEJO_CONFIRM_DATABASE_REUSE=YES`. Those confirmations
  exist because both paths can touch operator data — quote the
  requirement rather than working around it.
- `/var/lib/forgejo` holds every repository and LFS object, and the
  PostgreSQL database holds the rest. Dropping the database, deleting
  that directory, or `uninstall forgejo` are `destructive` and need the
  exact confirmation phrase and a stated backup. Ask what the backup is
  before, not after.
- Registration is disabled by design; the admin creates accounts.
  Re-enabling open registration on a LAN-published forge is a security
  decision for the operator, not a fix for "my colleague cannot sign
  up".
- The Actions runner executes repository-supplied jobs through Docker.
  That means untrusted code with the Docker daemon's reach — say so
  before enabling it, and see the `containers` skill for what the
  docker socket implies.
- The runner registers once; its token lives in
  `/var/lib/forgejo-runner/.runner`. Never echo a registration token,
  the admin password or the database password into the chat or a
  diagnostic report — they are recorded in the install receipt for the
  operator.
- `.local` resolution depends on Avahi and on the machine's hostname.
  Renaming the host changes the advertised URL and the marked Caddy
  block that serves it; if the operator wants a rename, say what will
  break and let `repair forgejo` re-render the route afterwards.
- Certificate warnings on first visit are expected: Caddy's internal CA
  is not a public one. Explain trusting the CA on the client rather
  than disabling TLS verification anywhere.
