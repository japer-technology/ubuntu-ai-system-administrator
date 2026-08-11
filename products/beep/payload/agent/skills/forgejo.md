<!-- triggers: forgejo, gitea, forge, runner, caddy, avahi, mdns -->
# Skill: an independently installed Forgejo service

This skill is loaded when the operator mentions Forgejo, the Actions
runner, or the Caddy/Avahi edge that publishes it. Ordinary working-copy
questions belong to the `git` skill.

Operating rules:

- Beep never installs, updates, repairs, or removes Forgejo as part of its
  own lifecycle. Treat Forgejo as separately owned software. Check whether
  it is actually present
  (`svc.status` on `forgejo.service`, `fs.list` on `/etc/forgejo`)
  before answering as though it were.
- Know the shape: Forgejo listens on loopback only
  (`127.0.0.1:3000` by default) with PostgreSQL on `127.0.0.1:5432`;
  Caddy terminates HTTPS on `443` with its internal CA and
  reverse-proxies to the backend; Avahi advertises
  `https://<hostname>.local/`. Caddy is the only LAN-facing part —
  never move Forgejo itself onto `0.0.0.0` to "make it reachable".
- Use Forgejo's independently reviewed lifecycle interface, if installed,
  for verification, diagnosis, repair, update, and removal. Never claim its
  account, configuration, data, service, receipt, or ownership marker as a
  Beep resource.
- Editing `/etc/forgejo/app.ini` by hand is a privileged change: the
  file is deliberately `640` and owned by the service account, and
  Forgejo must be restarted to pick a change up. Read it first, keep a
  timestamped backup, and never widen its mode or its directory's mode
  to make an edit convenient.
- `/var/lib/forgejo` holds every repository and LFS object, and the
  PostgreSQL database holds the rest. Dropping the database, deleting
  that directory, or removing Forgejo are `destructive` and need the
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
- A runner registers once; its token commonly lives in
  `/var/lib/forgejo-runner/.runner`. Never echo a registration token,
  the admin password or the database password into the chat or a
  diagnostic report.
- `.local` resolution depends on Avahi and on the machine's hostname.
  Renaming the host changes the advertised URL and the marked Caddy
  block that serves it; if the operator wants a rename, say what will
  break and direct them to Forgejo's own lifecycle interface.
- Certificate warnings on first visit are expected: Caddy's internal CA
  is not a public one. Explain trusting the CA on the client rather
  than disabling TLS verification anywhere.
