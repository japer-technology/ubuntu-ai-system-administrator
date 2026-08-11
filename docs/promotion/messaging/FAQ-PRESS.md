# FAQ for Press & Reviewers

Short, quotable answers. For the user-facing FAQ see
[`../../docs/FAQ.md`](../../docs/FAQ.md).

**What is Ubuntu Zombie in one sentence?**
A private, root-capable AI Systems Administrator that installs onto a supported
Ubuntu Desktop LTS machine so the owner can ask it to diagnose, explain,
configure, repair, and operate the computer — under explicit approval, fully
audit-logged.

**Why "Zombie"?**
It reanimates capability that already belonged to the machine's owner. The logo
is a real human skull (your actual PC) fused to a calm robot (the AI admin),
sharing one purple eye (your control). See
[`../../LOGO-MEANING.md`](../../LOGO-MEANING.md).

**Is it autonomous?**
No — deliberately not. It listens, proposes, and waits. Nothing privileged runs
without the operator's approval.

**Where does inference run?**
Either through a cloud LLM provider the operator configures with their own API
key (OpenAI, Anthropic, Gemini, xAI, Mistral, Groq, OpenRouter), or through a
local OpenAI-compatible server such as LM Studio, Ollama, or `llama.cpp`. The
installer can auto-detect a local server on the LAN, so the whole system can
run fully offline with no cloud key.

**What can the provider see?**
See [`../../SECURITY.md`](../../SECURITY.md) for the exact trust boundary and
what is sent to the provider. With a local LLM, nothing leaves the machine.

**How is it secured?**
A local policy gate classifies and gates privileged actions. The only network
listener is the chat UI, bound to `127.0.0.1` and protected by a password
(stored only as a PBKDF2 hash). The installer provisions no SSH, VNC, or other
inbound access. The administrator has a Time to Live (default seven days) and
permanently disables itself unless renewed. Every action is audit-logged.

**How do I stop or remove it?**
Type `/ttl --die` in the chat to trip the kill switch immediately, rotate or
remove the provider API key, disable the systemd service, or run
`sudo ./scripts/install.sh uninstall`. Left alone, it expires on its own when
the TTL runs out.

**What does it cost?**
The software is open source under the MIT licence. You pay your chosen cloud
LLM provider for usage — or nothing at all with a local model.

**Can it do more than administer the machine?**
Optionally, yes. The installer offers opt-in components — the first is a
self-hosted Forgejo git forge (PostgreSQL-backed, served over LAN HTTPS at the
machine's `.local` name, with an optional CI runner). All components are off by
default, idempotent, and individually removable.

**What platforms are supported?**
Ubuntu Desktop LTS 22.04 and 24.04. See
[`../../docs/PLATFORMS.md`](../../docs/PLATFORMS.md).

**Is this affiliated with Canonical / Ubuntu?**
No. Ubuntu is a trademark of Canonical Ltd. Ubuntu Zombie is an independent
third-party project.

**Can I see it do nothing first?**
Yes: `sudo ./scripts/install.sh install --dry-run` previews the entire plan and
changes nothing.
