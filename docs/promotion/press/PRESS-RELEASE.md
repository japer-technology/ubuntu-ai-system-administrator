# FOR IMMEDIATE RELEASE

<!-- DRAFT press release. Replace bracketed fields before distribution. -->

**Japer Technology releases Ubuntu Zombie, an open-source AI Systems
Administrator that lives inside your Ubuntu desktop**

*An approval-gated, audit-logged, root-capable AI administrator for Ubuntu
Desktop LTS — where the operator keeps every key and the kill switch.*

**[CITY, COUNTRY] — [DATE]** — Japer Technology today released **Ubuntu
Zombie**, an open-source tool that adds a private, root-capable AI Systems
Administrator account to supported Ubuntu Desktop LTS machines. With Ubuntu
Zombie installed, the owner can ask the computer — in plain language — to
diagnose, explain, configure, repair, and operate itself, seeing exactly what is
proposed, approving it, and watching it happen, with every action written to an
auditable log.

"Personal computers have become powerful enough to run real workloads and
complex enough that most owners cannot safely operate them," said [SPOKESPERSON
NAME], [TITLE] at Japer Technology. "Ubuntu Zombie closes that gap on the
machine itself — and it does so without ever taking the machine away from its
owner. You ask, it proposes, you approve, it acts, and it logs everything."

**Designed around operator control**

Unlike a general-purpose chatbot, Ubuntu Zombie acts with real authority on the
actual machine — but only under explicit human approval. A dedicated Linux
account serves as the operating identity of the administrator; privileged,
destructive, or system-altering actions pass through a local policy gate and
wait for the operator's approval before running. The only network surface is a
password-protected chat bound to `127.0.0.1`; the installer provisions no SSH,
VNC, or other inbound access. The administrator ships with a built-in Time to
Live and permanently disables itself unless the operator renews it. The
operator owns the LLM provider key, the chat password, and the kill switch,
and can rotate, revoke, or uninstall at any time.

**Transparent and reversible**

Ubuntu Zombie is a transparent bash installer on a normal Ubuntu LTS system;
every component can be inspected, modified, or removed. A `--dry-run` mode
previews the entire installation without making changes, and signed `.deb`
packages ship with SHA-256 checksums and keyless cosign signatures.

**Availability**

Ubuntu Zombie is available now under the MIT licence and supports Ubuntu Desktop
LTS 22.04 and 24.04. The source, documentation, and releases are at
<https://github.com/japer-technology/ubuntu-zombie>. Inference runs through a
cloud LLM provider configured by the operator with their own API key, or
through a local model server such as LM Studio, Ollama, or `llama.cpp` for
fully offline operation.

**About Japer Technology**

Japer Technology builds practical, transparent tools that keep humans in control
of the systems they own. Learn more at <https://www.japer.technology>.

*Ubuntu is a trademark of Canonical Ltd. Ubuntu Zombie is an independent,
third-party project and is not affiliated with, endorsed by, or sponsored by
Canonical.*

**Media contact**
[NAME]
[EMAIL]
[PHONE / HANDLE]

###
