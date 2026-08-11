# Vision

<p align="center">
  <picture>
    <img src="https://raw.githubusercontent.com/japer-technology/ubuntu-zombie/main/LOGO.png" alt="Ubuntu Zombie" width="420">
  </picture>
</p>

## The one-sentence vision

> **Ubuntu Zombie turns a supported Ubuntu Desktop LTS machine into a
> computer that can administer itself — by installing a private,
> root-capable AI Systems Administrator account that the owner can ask
> to diagnose, explain, configure, repair, and operate the machine, in
> plain language, under explicit human approval, with every action
> written to an auditable log.**

That sentence is the entire Ubuntu Zombie MVP. It is deliberately narrow,
and the root product remains organised to make it true, observable, and
reversible. Independently packaged family products may also be developed in
this repository under the contract below; they do not expand the authority
or default installation of Ubuntu Zombie.

## The first member of a family

Ubuntu Zombie is also the first of an independent
[AI-agent family](ai-agent/). Imaginary Friend, Curriculum Flame, ERIC,
and future products copy its proven installation, policy, audit, lifecycle,
update, and release lessons while declaring the authority their own purpose
requires. A systems-administrator variant may retain full root authority when
that authority is explicit, justified, policy-gated, approved, audited, and
tested; the existing named products retain their narrower definitions.
They remain separate products with separate credentials, data, installers,
updaters, policies, audits, and releases. Their source is co-located below
dedicated `products/<product-id>/` roots so one repository can test every
namespace and co-installation boundary without creating a shared runtime.

Ubuntu Zombie is the currently implemented generally root-capable member and
the designated machine-level family manager — the **God role**. That
designation does not reserve root authority to Ubuntu Zombie: another product
may define an equally root-capable role, and co-installed root-capable products
must be treated as mutually trusted at the operating-system boundary. With
explicit operator approval Ubuntu Zombie is intended to discover, install,
verify, diagnose, repair, update, suspend, and remove managed agents by invoking
each product's own verified lifecycle interface. It does not share their
runtime or turn them into installer components.

The existing root-capable tools can operate product-owned commands, but the
dedicated catalogue, secret-free inventory, and family management experience
are specified, not implemented MVP features. The target interfaces and work
order are fixed by the
[AI-agent implementation contract](ai-agent/implementation.md). Ubuntu
Zombie remains under human control; “God” describes host authority, not
autonomous ownership, consent, identity, guardianship, or legal authority.

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
  one trust boundary. Multi-machine fleet orchestration is out of scope;
  same-host managed-agent support is a post-MVP family direction.
- **Replacement of the human users on the desktop.** Existing logins,
  files, and workflows are left alone. Ubuntu Zombie installs
  *beside* the user, not *over* them.
- **A locked appliance or a hosted service.** This is a transparent
  bash installer on a normal Ubuntu LTS system. Every component can
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
- [`ai-agent/`](ai-agent/) — Ubuntu Zombie's family-manager role, the
  managed product definitions, and the new-agent template.
- [`ROADMAP.md`](ROADMAP.md) — what is intentionally post-MVP and
  what we have committed *not* to ship until the MVP is solid.

If an Ubuntu Zombie feature request expands beyond the one-sentence promise
above, it belongs in `ROADMAP.md` first. Family-product work instead follows
the fixed source, authority, sequencing, and release gates in
[`ai-agent/`](ai-agent/).
