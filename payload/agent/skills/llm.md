<!-- triggers: llm, llms, model, models, llama, gguf, ollama, lmstudio, openrouter, openai, anthropic, gemini, mistral, groq, inference, quantisation, quantization, provider, providers -->
# Skill: language models, providers and local inference

This skill is loaded when the operator asks which model the agent is
using, how to point it at a different provider, or how local inference
works.

Operating rules:

- Be honest about what is running. The active provider and model come
  from the chat service's environment (`ZOMBIE_PROVIDER`,
  `ZOMBIE_MODEL` and the per-provider overrides); report them from the
  service's own status rather than guessing from the conversation.
  Supported providers are `openai`, `anthropic`, `gemini`, `xai`,
  `mistral`, `groq`, `openrouter` and `lmstudio` (any local,
  OpenAI-compatible server).
- API keys live in the root-owned secrets file
  (`/opt/ai-zombie/secrets/env`, mode `0600`) and are edited with the
  `secrets-edit` helper by the operator. Never read that file into the
  chat, never echo a key, and never write one into a unit file, a
  script or a shell history. See the `secrets` skill.
- Changing provider or model is an operator decision that takes effect
  when the chat service restarts — which ends the conversation in
  progress. Say that before proposing it, and never restart the chat
  service to apply a preference the operator did not ask for.
- Local models are the private option. `/locals` in the chat probes the
  usual OpenAI-compatible ports (`1234`, `8080`, `11434`, `51234`) on
  the local network and loopback. `web.fetch` deliberately refuses
  loopback and private addresses, so it is not the way to inspect a
  local server — use `net.status` and `shell.run` with a bounded
  `curl`.
- Treat a local inference server as operator-managed software. Discover
  its executable, service, configuration, model directory and listener
  before proposing changes; do not assume Ubuntu Zombie installed it.
- Keep local inference endpoints on loopback unless the operator has
  explicitly designed and approved authentication, encryption and
  firewall rules for remote access.
- Models are large. Before downloading one, check free space with
  `df -h` on `/var/lib`, quote the download size, and prefer a pinned
  revision with a published SHA-256 over "the latest" — an unverified
  GGUF from an unknown repository is an unverified binary blob.
- Match the model to the machine, not to ambition. Report RAM, core
  count and whether a usable GPU exists (`nproc`, `free -h`, `lspci`)
  and say plainly when a requested model will swap the machine to a
  standstill. Context size costs memory too.
- Anything the operator types goes to the configured provider. When
  they are about to paste logs, configuration or personal data, say
  where it will be sent; that is the whole reason the local option
  exists.
- A weaker model does not get more privilege. Policy classes, the
  approval gate and the audit log are identical whichever provider is
  configured; never suggest loosening the gate because a local model
  struggles with a task.
