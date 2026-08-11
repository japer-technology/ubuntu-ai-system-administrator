# Tests

Everything here runs as a normal user on any machine with `bash`,
`shellcheck`, and `python3` — no root, no network, no Ubuntu target
required. These are the exact checks CI runs.

```bash
make lint   # shellcheck + bash -n + python compile
make test   # bash tests/smoke.sh all
```

## What's here

- [`smoke.sh`](smoke.sh) — the main harness. Run a single group with
  `bash tests/smoke.sh <group>`:
  - `syntax` — `bash -n` every shell file.
  - `python` — compile every Python file under `payload/agent/`.
  - `branding` — user-facing naming stays consistent.
  - `subcommands` — every `install.sh` subcommand parses.
  - `bad-usage` — wrong invocations exit `2`.
  - `flags` — UX contract: `--help`, `--version`, `--dry-run`,
    `--no-color`, `--quiet`, `--json`, helper-script `--help`.
  - `noninteractive` — the `ZOMBIE_NONINTERACTIVE=1` path end-to-end.
  - `diagnostics` — the diagnostic helpers work and redact secrets.
  - `standards` — repository invariants (no secrets, changelog
    discipline, workflow requirements, packaging list honesty).
  - `all` — everything above, in order.
- [`python/`](python/) — pytest unit tests (run in CI as
  `python3 -m pytest tests/python`; needs `pip install pytest`
  locally) for the agent modules in
  [`../payload/agent/`](../payload/agent/) (`policy.py`, `audit.py`,
  server chat commands). `conftest.py` puts `payload/agent/` on
  `sys.path` so tests can `import policy` directly.
- [`fixtures/`](fixtures/) — stub Node bridge processes
  (`stub-pi-*.mjs`, `fake-pi-json.mjs`, `hang-pi-mono.mjs`) used to
  exercise the chat service without real provider credentials or
  network access.

When you add an installer subcommand, extend the `subcommands` case in
`smoke.sh`; when you add an operator helper, give it `--help` and add
it to the `flags` group. See [`../AGENTS.md`](../AGENTS.md) for the
full contract.
