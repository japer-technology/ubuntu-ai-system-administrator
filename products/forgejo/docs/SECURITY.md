# Security

The product is root-capable infrastructure. Compromise of its source artifact
or lifecycle entrypoint is root-equivalent.

Security properties include:

- loopback-only Forgejo HTTP;
- Caddy internal-CA TLS as the LAN boundary;
- root-owned configuration and lifecycle state;
- checksum verification for every upstream binary;
- exact ownership markers and fail-closed legacy adoption;
- no secrets in process responses, common receipts, or audit events;
- a hardened unprivileged `forgejo.service`; and
- runner coordination without granting job containers privileged mode,
  arbitrary workflow volumes, or the Docker socket.

Caddy's CA is installed into host trust because co-located job containers use
the host bundle. Trusting that CA allows certificates issued by the local
Caddy authority; protect `/var/lib/caddy` accordingly.

Report vulnerabilities through the repository process in `SECURITY.md`.
