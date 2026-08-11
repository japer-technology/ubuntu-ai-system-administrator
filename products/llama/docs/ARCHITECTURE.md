# Llama architecture

## Components and identity

`scripts/manage.sh` is the source lifecycle entry point. An installed product
uses `/usr/local/sbin/llama-manage` and product-owned Python under
`/opt/llama.cpp/product`. The lifecycle runs as root only for mutating
operations and serialises them with `/run/lock/llama.lock`.

`/usr/local/bin/llama-manager` is the non-installing runtime helper used by
operators and `llama-server.service`. The service runs as the non-login
`llama-cpp:llama-cpp` identity and executes the pinned `llama-server` from
`/opt/llama.cpp/current`.

| Boundary | Path or identity |
| -------- | ---------------- |
| Runtime and product code | `/opt/llama.cpp` |
| Configuration | `/etc/llama.cpp` |
| Models and lifecycle state | `/var/lib/llama.cpp` |
| Audit and receipts | `/var/log/llama.cpp` (protected by `product-ownership`) |
| Download cache | `/var/cache/llama.cpp` |
| Service | `llama-server.service` |
| Listener | `127.0.0.1:8080/tcp` |

The listener is intentionally available to every local process and user. It is
never a LAN listener, an authentication boundary, or a route to privileged
host operations.

## Lifecycle and integrity

The lifecycle implements `describe`, `status`, `install`, `verify`, `doctor`,
`repair`, `backup`, `update`, `rollback`, `suspend`, `resume`, and `uninstall`.
Mutating plans are deterministic and support plan-digest revalidation.
Installation validates collisions before mutation, writes a transaction marker
for safe retry, verifies downloaded bytes and extracted paths, health-checks
the selected service state, and writes
`/var/lib/llama.cpp/installation.json` only after boundary checks pass.

Update creates a configuration backup and one previous-version rollback
snapshot before switching. Rollback restores product code, catalogues,
configuration, unit files, and the previous runtime link. Model binaries and
runtime versions are content-addressed by their pinned metadata and are not
silently deleted during updates. Install, repair, and update restart an active
service whenever its live runtime, model, manager, unit, or configuration
changes, then apply the loopback health gate before reporting success.

Every completed mutation writes a secret-free receipt and a correlated JSON
Lines audit event. Llama has no credential store and does not use Ubuntu
Zombie's policy or audit implementation.

## Legacy adoption

The first product release can adopt the previously supported component only
when both exact `managed-by-ubuntu-zombie` markers, the `llama-cpp` identity,
configuration boundary, runtime checksum manifest, manager, exact unit asset,
model size and checksum, and declared resources validate. Partial or ambiguous
state fails before mutation. A successful install replaces the legacy markers
with the common product ownership marker without moving model state or changing
paths. Product-owned removal can adopt that exact legacy state solely to remove
or retain it safely.
