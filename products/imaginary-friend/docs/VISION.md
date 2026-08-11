# Vision

Imaginary Friend provides one person with a persistent, private place for
conversation and deliberate work on a small set of local files. It is useful
because continuity, history, and selected workspace context remain under the
machine owner's control without granting the model authority over the host.

## Product promise

Friend must:

- authenticate one owner with product-specific credentials;
- send only conversation context and owner-selected workspace text to the
  configured loopback model;
- keep file operations within canonical, nominated workspace roots;
- make retention, export, deletion, suspension, recovery, and removal visible;
  and
- preserve policy and audit evidence without copying message or file contents
  into the operational log.

## Authority ceiling

The `friend` service account may write Friend's SQLite state and audit log and
may read or change enabled nominated workspaces. It has no `sudo`, login shell,
general command runner, host-management capability, or non-loopback provider.
Linux identity, file permissions, systemd confinement, closed application
interfaces, and negative tests establish that ceiling; the model prompt does
not.

## Honest limits

Friend is not conscious, a substitute for a human relationship or
professional care, a system administrator, or a generic automation engine.
Local state and backups are not application-encrypted. Root on the same host
can inspect them. Cloud models, remote access, multiple owners, voice, images,
proactive messaging, and arbitrary existing-tree adoption are later work.
