# Beep vision and scope

Beep lets an operator ask a private AI Systems Administrator to diagnose,
operate, and repair one Ubuntu Desktop LTS machine without translating every
goal into shell commands. It deliberately has root-equivalent authority.

## Product promise

Beep is independently installable, authenticatable, configurable, auditable,
killable, upgradable, recoverable, removable, and releasable. Every installed
resource is Beep-owned.

The operator remains the principal. Model output is an untrusted proposal.
Sensitive tools require policy classification and explicit approval;
destructive tools also require the configured phrase. Every attempted tool and
lifecycle result has local audit evidence.

## Intended users

- the owner/operator of the machine;
- local users explicitly authorised by that operator; and
- automation explicitly authorised by the operator through Beep's fixed root
  lifecycle request interface.

## In scope

- authenticated local chat and supported cloud or loopback model providers;
- complete host inspection and policy-mediated root administration;
- bounded reactivation and durable conversation history;
- diagnostics, backup, update, rollback, suspension, terminal death, and
  removal; and
- verified, catalogue-pinned lifecycle management of other admitted products.

## Out of scope

Beep is not a security boundary against host root, a remote multi-user service,
an autonomous legal or human authority, a high-availability peer, or a
containment layer for another root-capable process. It does not share
credentials or state with a sibling and does not automatically inherit sibling
releases.

Production family admission remains gated on recorded supported-VM,
co-installation, security-review, and published-release evidence.
