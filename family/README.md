# Independent product data contract

This directory is the only source shared by independently installed products.
It contains data schemas and the release catalogue; it contains no runtime
Python or shell code. AI-agent products apply the additional family rules in
`docs/ai-agent/`; infrastructure products such as Llama do not become agents
or inherit Ubuntu Zombie's authority by conforming to this data contract.

`catalog.json` remains empty until a product release has passed its checksum,
SBOM, provenance, signature, and disposable-VM gates. A source implementation
is not a production catalogue entry.

The normative contract is
[`docs/ai-agent/implementation.md`](../docs/ai-agent/implementation.md).
