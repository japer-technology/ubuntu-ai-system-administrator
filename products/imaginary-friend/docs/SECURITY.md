# Security and threat model

Read [`VISION.md`](VISION.md) and [`ARCHITECTURE.md`](ARCHITECTURE.md) before
installation. This document describes the implemented controls; it does not
extend Friend's authority.

## Protected assets

- the owner password hash and session-signing key;
- active session and CSRF material;
- conversation history and workspace metadata;
- nominated workspace files;
- root-owned code, policy, configuration, units, marker, and receipts; and
- credentials and state belonging to other local services.

## Threats and controls

| Threat | Prevention and detection | Recovery |
| ------ | ------------------------ | -------- |
| Malicious prompt or model output requests host access | No shell or host tool exists; closed policy denies unknown, host, network-tool, and sibling capabilities | End the session, inspect content-free audit events, suspend Friend |
| Workspace traversal, symlink, mount, hard-link, or special-file escape | Descriptor-relative `O_NOFOLLOW` traversal, root device/inode checks, mount checks, one-link regular-file checks, atomic writes | Disable the workspace, restore its identity, run `doctor` and `repair` |
| Cross-site request or stolen browser state | Host-header pinning, same-origin mutation checks, session-bound CSRF, host-only `HttpOnly` `SameSite=Strict` cookie | Revoke sessions or rotate the owner password |
| Credential disclosure through logs or receipts | Recursive redaction, secret file references, content-minimised events, diagnostics allow-list | Rotate the password, repair credentials, review local audit access |
| Compromised service tries to administer the host | Non-login identity with only `friend` and `friend-share`, empty capabilities, no privilege-bearing group, hardened systemd unit | Stop the service and repair or uninstall from reviewed source |
| Untrusted lifecycle state causes ownership confusion | Root-only regular request files, strict JSON, exact namespaces, marker validation, collision preflight, product lock | Use `doctor`; restore a verified release or retained state |

## Residual risk

The model receives typed conversation context and any file text selected for a
turn. Treat it as untrusted. The service shares each nominated workspace with
the human owner, so concurrent human changes can cause conflicts or denial of
service. Filesystem permissions and sandboxing reduce impact but do not
provide confidentiality from root. The first release does not encrypt its
database or backup archives.

Only the configured loopback model transport is exposed by the application.
Systemd allows loopback networking so a compromise of the Python process is a
stronger threat than a malicious model response; deploy on a dedicated
machine when same-host root or other local services are outside the acceptable
risk boundary.

## Security reporting

Do not open a public issue for a suspected vulnerability. Use the source
repository's private vulnerability-reporting channel, identify the affected
product as Imaginary Friend, and include the product version and reproduction
details without real conversation or workspace content.
