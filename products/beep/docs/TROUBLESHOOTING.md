# Troubleshooting and platform support

Beep supports Ubuntu Desktop 22.04 and 24.04 LTS on `amd64`. The pinned Node
runtime is `amd64`; other distributions, Ubuntu releases, server images, and
architectures are rejected rather than guessed.

## Service does not start

1. Run `sudo beep-manage status --json` and `verify --json`.
2. Check `sudo systemctl status beep-chat.service beep-health.timer`.
3. Read `sudo journalctl -u beep-chat.service -n 100`.
4. Check lifecycle status. Dead, missing, corrupt, or expired state causes a
   clean fail-closed exit and the health timer follows the chat service down.
5. Verify `/etc/beep/secrets/session.key` and `/etc/beep/secrets/env` are
   regular, owned by `beep:beep`, and mode `0600`.

Do not manually start a dead service or edit its tombstone.

## Browser cannot connect or authenticate

- Use exactly `http://127.0.0.1:58989/` unless the configured port differs.
- Beep rejects non-loopback Host values and cross-origin mutations.
- Cookies are Beep-only, `HttpOnly`, `SameSite=Strict`, and expire after 12
  hours. Another product's cookie never authenticates.
- Password rotation clears current sessions. Lost passwords require
  root-controlled repair with a protected file.

Malformed JSON, missing JSON content type, invalid lengths, bodies over 1 MiB,
duplicate keys, unknown fields, and wrong field types return bounded `4xx`
errors.

## Provider or model fails

Run `beep-health`, inspect `/api/status` after authentication, and check only
the provider-specific variable in `/etc/beep/secrets/env`. Never paste a key
into chat, a command argument, request JSON, issue, or diagnostic bundle.
LM Studio requires a named model and a validated private or loopback base URL.

## Tool waits or is denied

Inspect the proposed class and current `/etc/beep/policy.yaml`. Elevated work
needs approval; destructive work needs the exact configured phrase. Unknown or
ambiguous commands are destructive. Pending calls can expire, turns have
budgets, and reactivation cannot exceed remaining TTL.

## Family operation fails

Use `/opt/beep/bin/beep-agents --json list`, then compare the correlation ID in
Beep's audit, the target audit, and the target receipt. Catalogue, signature,
descriptor, marker, response, and receipt failures intentionally do not
advance inventory. Do not bypass catalogue admission with a direct URL.

## Support bundle

Run `beep-diagnostics` and inspect the archive before sharing. It is intended
to redact credentials, but it can still reveal host names, package state,
paths, and operational metadata. Follow the private security process for a
suspected vulnerability.
