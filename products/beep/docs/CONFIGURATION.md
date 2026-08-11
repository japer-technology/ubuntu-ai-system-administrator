# Configuration and credential rotation

## Interactive installation

Run `./scripts/install.sh` from the product directory. The installer asks for
the loopback chat port, model provider and applicable model settings, and
initial time to live. Press Enter to accept each displayed default. The
installer then shows the selected values, plan digest, and every lifecycle step
before asking for approval.

After approval, protected prompts collect the chat password and any required
provider credential. These secrets are hashed or written directly to the
protected Beep environment and are never included in plan output, arguments,
receipts, or audit events.

## Unattended installation

## Lifecycle inputs

The manager rejects unknown `BEEP_*` variables. Secret values must be supplied
through root-owned regular files with mode `0600`; raw password, credential,
and API-key environment variables are rejected.

| Input | Environment | Default or rule |
| ----- | ----------- | --------------- |
| Agent user | `BEEP_USER` | Fixed to `beep` |
| Chat port | `BEEP_CHAT_PORT` | `58989`, unprivileged loopback port |
| Chat password file | `BEEP_ADMIN_PASSWORD_FILE` | Required for unattended first install; prompted interactively |
| Provider | `BEEP_PROVIDER` | Optional: `openai`, `anthropic`, `gemini`, `xai`, `openrouter`, `mistral`, `groq`, or `lmstudio` |
| Provider credential file | `BEEP_PROVIDER_CREDENTIAL_FILE` | Required unattended for a non-local provider unless already stored |
| Model | `BEEP_MODEL` | Provider model override; required for OpenRouter and LM Studio |
| Model base URL | `BEEP_MODEL_BASE_URL` | HTTPS, or literal private/loopback HTTP; only OpenAI-compatible or LM Studio |
| TTL days | `BEEP_TTL_DAYS` | `7`; integer 1–3,650 |
| Backup destination | `BEEP_BACKUP_DESTINATION` | Absolute path outside every product root |
| Non-interactive mode | `BEEP_NONINTERACTIVE=1` | Missing required input exits `64` |
| Artifact digest | `BEEP_ARTIFACT_SHA256` | Set by the verified family-release path and retained in the marker |

`BEEP_SOURCE_ROOT` is a development and installed-wrapper input.
`BEEP_DISPOSABLE_VM_TEST=1` is only for the separately guarded destructive VM
harness.

Use `--yes --non-interactive` with automation. `--yes` skips setup questions
and plan approval; `--non-interactive` guarantees that missing protected inputs
exit `64` rather than prompting.

Family requests use an absolute root-owned mode-`0600` JSON request file. The
request fixes product `beep`, operation, canonical correlation UUID, actor,
typed inputs, confirmation, and uninstall retention. Beep rejects extra keys
and operation-inapplicable inputs.

## Stored configuration

- `/etc/beep/config.json`: non-secret user, port, provider, model, base URL, and
  TTL defaults; root-owned and group-readable.
- `/etc/beep/secrets/env`: password hash, provider credential, and runtime
  environment; owned by `beep`, mode `0600`.
- `/etc/beep/secrets/session.key`: independent session signing key; owned by
  `beep`, mode `0600`.
- `/etc/beep/policy.yaml`: root-owned reviewed policy.
- `/etc/beep/agents/catalog.json`: root-owned family release catalogue.

The installer stores only a PBKDF2-SHA256 hash of the chat password. Provider
credentials are never accepted in request JSON, command arguments, receipts,
inventory, or audit.

## Provider configuration

Cloud providers receive the conversation context needed for a turn and are
subject to their own terms. LM Studio must use a local/private HTTP endpoint
and a named model; Beep writes its separate pi-mono model configuration below
the `beep` home. An OpenAI base URL is accepted only through the validated
model URL input.

If no provider is configured, local lifecycle, history, status, audit, and
diagnostics remain available but model turns cannot complete.

## Rotation

- Run `sudo beep-secrets-edit` to edit provider material through a protected
  temporary file, then restart `beep-chat.service`.
- Rotate the chat password through the authenticated password API or supply a
  new protected `BEEP_ADMIN_PASSWORD_FILE` to `repair`. Rotation clears every
  in-memory session.
- A valid session key is preserved by repair and reinstall. To rotate it, stop
  Beep, replace it with 32–4,096 random bytes owned by `beep` mode `0600`, then
  restart; all old cookies become invalid.
- Never copy another product's credential files into `/etc/beep`.

Run `sudo beep-manage verify --json` after any root configuration change.
