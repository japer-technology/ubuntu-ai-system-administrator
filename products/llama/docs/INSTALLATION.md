# Installing and operating Llama

Run live lifecycle commands only on a supported Ubuntu host. Installation
downloads roughly 271 MB of model data plus the pinned runtime and changes
users and systemd.

From a reviewed source checkout:

```bash
products/llama/scripts/manage.sh install --dry-run
sudo products/llama/scripts/manage.sh install --yes
products/llama/scripts/manage.sh status
sudo products/llama/scripts/manage.sh verify
```

During the compatibility period this source command delegates to the same
product lifecycle:

```bash
sudo ./scripts/install.sh install llama
```

The matching `verify`, `doctor`, `repair`, and `uninstall llama` compatibility
targets also delegate; no Llama mutation implementation remains in the root
installer or uninstaller.

Re-running `install` converges the same declared state. A supported legacy
component is adopted only after its exact markers and resources validate.
Unmanaged paths, account collisions, unexpected unit overrides, or a listener
conflict stop the operation before mutation.

## Day-two operations

```bash
sudo llama-manage repair --yes
sudo llama-manage suspend --yes
sudo llama-manage resume --yes
sudo llama-manage backup --yes
llama-manager status
llama-manager models
sudo llama-manager restart
```

`LLAMA_BOOT=disabled` installs and verifies assets without enabling or starting
the server. `resume` starts a healthy suspended service without changing its
saved boot intent.

## Removal

The safe default removes runtime and configuration while retaining downloaded
models and state:

```bash
sudo llama-manage uninstall --yes
```

Complete state deletion is explicit and irreversible:

```bash
sudo llama-manage uninstall --purge \
  --confirmation 'DELETE LLAMA STATE' --yes
```

Lifecycle receipts and audit evidence remain under `/var/log/llama.cpp`.
Removal does not inspect or modify Ubuntu Zombie or another product.
The retained root-owned log marker lets a later clean install distinguish that
evidence from an unmanaged path.
