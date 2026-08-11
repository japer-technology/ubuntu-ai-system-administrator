# Llama

Llama is an independent infrastructure product that installs one pinned CPU
`llama.cpp` runtime and one checksum-verified model. It exposes an
OpenAI-compatible API only on `127.0.0.1:8080` and has no dependency on Ubuntu
Zombie.

The product preserves the established `llama-cpp` identity, `/opt/llama.cpp`,
`/etc/llama.cpp`, `/var/lib/llama.cpp`, `/var/log/llama.cpp`,
`llama-server.service`, and `llama-manager` interface.

## Safety first

The lifecycle creates a system account, downloads executables and model
weights, and changes systemd state. Test live installation only on a
disposable supported Ubuntu VM. Normal lint, unit, integration, and package
commands do not mutate the host or use the network.

## Documentation

- [`docs/VISION.md`](docs/VISION.md)
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)
- [`docs/SECURITY.md`](docs/SECURITY.md)
- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md)
- [`docs/INSTALLATION.md`](docs/INSTALLATION.md)
- [`docs/UPGRADING.md`](docs/UPGRADING.md)
- [`docs/RECOVERY.md`](docs/RECOVERY.md)
- [`docs/TROUBLESHOOTING.md`](docs/TROUBLESHOOTING.md)
- [`docs/RELEASE.md`](docs/RELEASE.md)
- [`docs/TESTING.md`](docs/TESTING.md)

## Development

From the repository root:

```bash
make -C products/llama lint
make -C products/llama test
make -C products/llama package
```
