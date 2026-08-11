# Installation

Use a supported Ubuntu Desktop 22.04 or 24.04 LTS host:

```bash
cd products/forgejo
./scripts/install.sh
sudo /usr/local/sbin/forgejo-manage verify
```

The installer obtains root privileges when needed. It asks for the initial
administrator, PostgreSQL names, Forgejo version, and boot preference. Every
question has a default; the installer then shows the complete plan and asks
for approval before changing the host.

The product installs Forgejo, Git LFS, PostgreSQL, Caddy, Avahi, certificate
tools, and mDNS NSS support.

For an unattended installation, set any desired variables from
`docs/CONFIGURATION.md`, then run:

```bash
sudo ./scripts/manage.sh install --yes --non-interactive
```

An external migration adapter may offer an existing installation by setting
`FORGEJO_MIGRATION_MANIFEST` to its root-owned manifest. Adoption occurs only
when the manifest, account, loopback configuration, complete recovery secrets,
unit, and unmanaged-drop-in boundary all validate. It also requires:

```bash
sudo env FORGEJO_MIGRATION_MANIFEST=/absolute/path/to/manifest \
  ./scripts/manage.sh install --yes \
  --confirmation "ADOPT FORGEJO"
```

Ambiguous partial state is rejected before mutation.

After installation, import `/etc/forgejo/caddy-local-ca.crt` into any LAN
client that does not already trust the host's Caddy CA.
