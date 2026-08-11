# Source and binary provenance

The product extraction preserves the standalone Llama implementation shipped
by Ubuntu Zombie immediately before this product root was introduced. The
copied files are:

- `payload/bin/llama-manager`;
- `payload/etc/llama-builds.json`;
- `payload/etc/llama-models.json`; and
- `payload/systemd/llama-server.service`.

The runtime catalogue pins upstream `ggml-org/llama.cpp` release `b10054`,
commit `ac2557cb24def295888ef47f1a35b401d978c510`, with a SHA-256 digest per
architecture. The model catalogue pins the exact Hugging Face revision,
filename, size, licence, and SHA-256 digest.

Llama does not import Ubuntu Zombie runtime code. Its lifecycle, audit,
receipts, tests, documentation, and releases are product-owned.
