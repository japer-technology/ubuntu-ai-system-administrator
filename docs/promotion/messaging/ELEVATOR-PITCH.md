# Elevator Pitches

Three lengths of the same story. Use the shortest that fits.

## 10 seconds (one breath)

Ubuntu Zombie puts a private, root-capable AI Systems Administrator inside your
Ubuntu desktop. You ask it to fix or change something, it shows you exactly
what it would do, you approve, and it acts — with every step audit-logged and
reversible.

## 30 seconds (a meeting opener)

Most people own computers they can't safely operate. When something breaks, the
gap between "my laptop is broken" and "here's the exact systemd unit that fixes
it" gets filled by a forum thread or a paid technician. Ubuntu Zombie closes
that gap on the machine itself. It installs a dedicated `zombie` account with
passwordless sudo as the operating identity of an AI Systems Administrator. You
open a private, password-protected chat on `127.0.0.1`, ask in plain English,
and it proposes the commands it would run. Destructive or system-altering
actions pass through a local policy gate and wait for your approval. Everything
is written to an audit log. You own the API key, the chat password, and the
kill switch — the administrator ships with a Time to Live and disables itself
unless you renew it, and uninstall reverses the whole thing.

## 60 seconds (a podcast / press intro)

Personal computers have become powerful enough to run real workloads and
complex enough that most owners can't safely operate them. Ubuntu Zombie is a
transparent bash installer that turns a supported Ubuntu Desktop LTS machine
into a computer that can administer itself. It adds a private, root-capable AI
Systems Administrator — a dedicated Linux account, not a shared human login —
that the owner can ask to diagnose, explain, configure, repair, and operate the
machine in plain language.

The design is built around control. Privileged actions are classified and
gated; the operator approves them before they run. Every proposal and command
is audit-logged and inspectable after the fact. The only network surface is a
password-protected chat bound to `127.0.0.1` — the installer provisions no
SSH, no VNC, and no inbound remote access. The administrator ships with a
Time to Live: unless the operator renews it from the chat, it permanently
disables itself. Revocation is first-class: rotate the provider key, run
`/ttl --die`, disable the service, or run uninstall, and the agent stops.
Inference can be a cloud provider with the operator's own key or a fully
local LLM server (LM Studio, Ollama, `llama.cpp`) that the installer
auto-discovers — offline operation with no cloud key at all.

It deliberately does *not* promise an autonomous machine, fleet management, or
replacing the humans on the desktop. One machine, one operator, one trust
boundary. The logo says it best: an ordinary PC with a calm, listening,
root-capable administrator fused to it, sharing one glowing eye that belongs
to the operator — who can always turn it off.
