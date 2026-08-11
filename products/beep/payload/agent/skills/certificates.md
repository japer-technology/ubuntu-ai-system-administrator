<!-- triggers: certificate, certificates, tls, ssl, letsencrypt, certbot, openssl, x509, csr, expiry, keypair, ca-certificates, self-signed -->
# Skill: TLS certificates and trust stores

This skill is loaded when the operator mentions certificates, TLS/SSL
errors, expiry, or certificate authorities. Web fetching itself is the
`web` skill; key files and passphrases follow the `secrets` skill.

Operating rules:

- Diagnose with read-only inspection first. `openssl x509 -in <file>
  -noout -text` (local file), `openssl s_client -connect host:443
  -servername host </dev/null 2>/dev/null | openssl x509 -noout
  -dates -subject -issuer` (live endpoint) and `certbot certificates`
  answer most "is the cert valid / when does it expire / who issued
  it" questions without changing anything.
- Name the actual failure before fixing. "Certificate error" splits
  into: expired, hostname mismatch (SAN does not include the name
  used), untrusted issuer (missing CA or incomplete chain), and clock
  skew on the *client*. Each has a different fix; check `timedatectl`
  before touching any certificate, because a wrong clock fails all of
  them.
- An incomplete chain works in browsers (which cache intermediates)
  and fails in `curl` and language runtimes. `openssl s_client
  -showcerts` reveals whether the server sends the intermediate; the
  fix is serving the full chain, not adding the intermediate to the
  client's trust store.
- Private keys are secrets. Never print, chat, or copy a key's
  contents; confirm existence and permissions only (`ls -l`, expect
  root-owned, mode `600` or `640`). Verify a key matches a
  certificate by comparing public-key digests
  (`openssl pkey -pubout` vs `openssl x509 -pubkey`), never by
  displaying the key.
- Trusting a new CA system-wide (copy into
  `/usr/local/share/ca-certificates/` + `update-ca-certificates`) is a
  security decision: every TLS connection on the machine will trust
  what that CA signs. It is `system_change`, needs the operator to
  know exactly whose CA it is, and must never be the workaround for a
  misconfigured server.
- Never disable verification (`curl -k`, `verify=False`,
  `GIT_SSL_NO_VERIFY`) as a fix, and do not leave it in any script or
  configuration even "temporarily". It converts a visible failure into
  a silent man-in-the-middle exposure. Say this when the operator asks
  for it, and offer the real fix instead.
- Self-signed certificates are fine for loopback and lab use when the
  operator says so — generate with a SAN for the exact name used
  (modern clients ignore CN), state the expiry chosen, and trust it
  narrowly (per-application) rather than system-wide where possible.
- Let's Encrypt renewals are the routine failure. `certbot renew
  --dry-run` tests without issuing; check that the renewal timer
  exists (`systemctl list-timers | grep -i certbot`), that port 80 or
  the DNS hook still works, and remember rate limits make repeated
  failed issuance attempts expensive — dry-run first, always.
- Renewing a certificate does not deploy it. The consuming service
  must reload to pick up the new file; name the reload step
  (`system_change`) in the same plan, and verify afterwards with a
  live `openssl s_client` date check, not just the file on disk.
- Report expiry dates, issuer, the exact names covered, and which
  services were reloaded, so the operator can put the next renewal on
  their calendar rather than rediscovering it as an outage.
