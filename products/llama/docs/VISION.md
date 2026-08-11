# Llama product vision

Llama gives applications and local users on one Ubuntu PC a predictable,
private model endpoint without granting an AI agent system authority. It owns
one curated CPU runtime, one approved model selection, and the lifecycle needed
to keep that service verifiable and reversible.

The first release is deliberately narrow:

- Ubuntu Desktop 22.04 and 24.04 LTS on `amd64` or `arm64`;
- a checksum-pinned `llama.cpp` CPU runtime;
- models from a product-owned, revision- and checksum-pinned catalogue;
- one OpenAI-compatible listener fixed to `127.0.0.1:8080`; and
- no dependency on, import from, or authority inherited from Ubuntu Zombie.

Llama is infrastructure, not an AI agent. It does not execute tools, administer
the host, accept arbitrary model URLs, expose the API to the LAN, install GPU
drivers, train models, or combine credentials and state with another product.
