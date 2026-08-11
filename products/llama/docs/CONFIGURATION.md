# Llama configuration

The lifecycle accepts these non-secret inputs directly from environment
variables or the common request-file `inputs` object:

| Environment | Request input | Default | Rule |
| ----------- | ------------- | ------- | ---- |
| `LLAMA_MODEL_ID` | `model_id` | `smollm2-360m-instruct-q4_k_m` | Must exist in the product catalogue |
| `LLAMA_CONTEXT_SIZE` | `context_size` | `2048` | `512` through the selected model maximum |
| `LLAMA_CPU_THREADS` | `cpu_threads` | detected logical CPUs | `1` through `1024` |
| `LLAMA_BOOT` | `boot` | `enabled` | `enabled` or `disabled` |
| `LLAMA_BACKUP_DESTINATION` | `backup_destination` | `/var/backups/llama.cpp` | Absolute path outside product roots |
| `LLAMA_NONINTERACTIVE` | — | `0` | `1` disables every prompt |

`LLAMA_PORT` is retained for compatibility but only the value `8080` is
accepted. Unknown `LLAMA_*` variables fail closed. There are no raw secret
inputs.

The installed `/etc/llama.cpp/config.json` is lifecycle-owned, root-owned, and
mode `0644`. Do not edit it to select an unlisted model, another runtime, a
different path, or a wider listener; verification rejects those changes.

## Request files

`--request-file` accepts a root-owned, mode `0600`, non-symlink regular JSON
file matching `family/schemas/request-v1.schema.json`. Product inputs are
operation-scoped. `uninstall` requires `retain_state`; complete state deletion
also requires the exact confirmation `DELETE LLAMA STATE`.

## Runtime API

The endpoint is always `http://127.0.0.1:8080/v1`. The runtime provides the
usual `llama.cpp` OpenAI-compatible model and chat-completion routes. It is
available to all local users and has no API key.
