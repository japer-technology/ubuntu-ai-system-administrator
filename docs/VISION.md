# Vision

## The one-sentence vision

> **Ubuntu Zombie turns a supported Ubuntu Desktop LTS machine into a
> computer that can administer itself — by installing a private,
> root-capable AI Systems Administrator account that the owner can ask
> to diagnose, explain, configure, repair, and operate the machine, in
> plain language, under explicit human approval, with every action
> written to an auditable log.**

That sentence is the entire Ubuntu Zombie product. Its scope is deliberately
narrow: every shipped file exists to make that promise true, observable, and
reversible.

## Why this exists

Personal computers have become powerful enough to run real workloads
and complex enough that most owners cannot safely operate them. The
gap between *"my laptop is broken"* and *"here is the exact `systemd`
unit, kernel parameter, or `apt` pin that will fix it"* is filled,
today, by a friend, a forum thread, or a paid technician.

Ubuntu Zombie closes that gap on the machine itself. The owner asks
the computer a question; the computer answers as an administrator
would, proposes the commands it would run, waits for approval, runs
them, and writes down what happened. The operator stays in charge of
the machine the whole time.

## What the MVP promises

1. **A controlled sysadmin assistant with local authority.** A
   dedicated `zombie` account (renameable at install time) holds
   passwordless `sudo` and serves as the operating identity of the AI
   Systems Administrator — never a shared human login.
2. **An explicit policy and approval model before privileged
   actions.** Destructive, networked, or system-altering commands are
   classified, gated, and surfaced to the operator before they run.
3. **An auditable trail of every command the AI proposes or runs.**
   What was asked, what was proposed, what was approved, and what the
   system did — all recorded and inspectable after the fact.
4. **Operator revocation as a first-class feature.** Rotating the
   provider API key, expiring the Time to Live, or running `uninstall`
   stops the agent. Control is the operator's, not the vendor's.

## What the MVP does not promise

- **Autonomous ownership of the machine.** The operator is the
  principal. The agent is a tool with hands, not a tenant.
- **Multi-tenant or fleet management.** One machine, one operator,
  one trust boundary. Multi-machine fleet orchestration is out of scope.
- **Replacement of the human users on the desktop.** Existing logins,
  files, and workflows are left alone. Ubuntu Zombie installs
  *beside* the user, not *over* them.
- **A locked appliance or a hosted service.** This is a transparent
  bash installer on a normal Ubuntu LTS system. Every installed file can
  be inspected, modified, or removed.

## Trust model summary

The local `zombie` account (renameable with `ZOMBIE_USER=<name>`)
holds passwordless `sudo` and is the operating identity of the AI
Systems Administrator. The configured provider powers the
administrator. The operator owns the machine and can rotate the API key,
expire the Time to Live, or uninstall the system at any time. Ubuntu
Zombie exposes only a loopback chat service by default.

## How to read the rest of the docs

- [`SECURITY.md`](../SECURITY.md) — the full trust boundary, what the
  provider sees, and the disclosure policy.
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — components, action classes,
  and the approval pipeline.
- [`CONFIGURATION.md`](CONFIGURATION.md) — provider, policy, chat, and
  lifecycle settings.

If a feature request expands beyond the one-sentence promise above, it is out
of scope for this repository until the vision is deliberately revised.
