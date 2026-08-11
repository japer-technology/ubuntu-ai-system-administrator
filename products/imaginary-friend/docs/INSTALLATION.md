# Installation and removal

Use a disposable Ubuntu Desktop 22.04 or 24.04 LTS `amd64` VM for first
installation and lifecycle testing. The commands below mutate Linux
identities, groups, systemd, `/opt`, `/etc`, `/var`, `/srv`, and
`/usr/local`.

## Interactive install

Start the configured OpenAI-compatible loopback model, enter the product
directory, and run:

```bash
./scripts/install.sh
```

The installer obtains root privileges with `sudo` when needed and asks for:

- the existing non-root human owner;
- an owner password, or permission to generate one;
- the OpenAI-compatible loopback endpoint and model ID; and
- conversation-history and operational-audit retention periods.

Press Enter to accept a displayed default. The installer then displays every
non-secret setting, the plan digest, and each mutation before asking for
approval. A generated password is shown once after a successful installation.
Browse to `http://127.0.0.1:6767/`.

Use `./scripts/install.sh --dry-run` to answer the same setup questions and
render a non-mutating plan. A dry-run creates no lock, credential file, log,
directory, download, or network request; the bounded model probe is deferred
until execution.

## Unattended install

Create the password file outside the repository:

```bash
sudo install -m 0600 -o root -g root /dev/null /root/friend-owner-password
sudoedit /root/friend-owner-password
```

Then review a dry-run and execute:

```bash
sudo env \
  FRIEND_NONINTERACTIVE=1 \
  FRIEND_OWNER_USER="$SUDO_USER" \
  FRIEND_OWNER_PASSWORD_FILE=/root/friend-owner-password \
  FRIEND_MODEL_BASE_URL=http://127.0.0.1:8080/v1 \
  FRIEND_MODEL=local-model-id \
  ./scripts/manage.sh install --dry-run --json

sudo env \
  FRIEND_NONINTERACTIVE=1 \
  FRIEND_OWNER_USER="$SUDO_USER" \
  FRIEND_OWNER_PASSWORD_FILE=/root/friend-owner-password \
  FRIEND_MODEL_BASE_URL=http://127.0.0.1:8080/v1 \
  FRIEND_MODEL=local-model-id \
  ./scripts/manage.sh install --yes --json
```

The model must answer bounded `/models` and `/chat/completions` probes before
host mutation. Remove the plaintext password file when it is no longer needed.

Re-running install preserves valid credentials, history, workspace nominations,
retention, and suspension state.

## Verify and repair

```bash
sudo /usr/local/sbin/friend-manage status --json
sudo /usr/local/sbin/friend-manage verify --json
sudo /usr/local/sbin/friend-manage doctor --json
sudo /usr/local/sbin/friend-manage repair --dry-run --json
```

`verify` is read-only and exits non-zero on a required failure. `doctor`
returns a diagnosis even when degraded. Repair accepts only known-safe,
product-owned convergence from the matching installed source version.

`friend-diagnostics --output-directory /absolute/protected/directory` creates
a mode-`0600`, content-free archive. Review it before sharing.

## Suspend and resume

`friend-manage suspend` revokes sessions, disables conversation and workspace
operations, and stops only the Friend service. Reinstall, repair, and update
preserve suspension. `friend-manage resume` first validates credentials,
policy, sandbox, workspaces, runtime integrity, and the configured model.

## Uninstall

Always inspect the uninstall plan. A state-preserving uninstall removes code,
configuration, commands, the service identity, and the unit while retaining
protected state for a later reviewed install. Complete uninstall requires the
exact confirmation `DELETE IMAGINARY FRIEND STATE`.

Neither form deletes nominated workspace files. Operational audit evidence
and workspace-sharing resources can remain where needed to preserve that
data; inspect the JSON response's `changed_resources` and receipt. See
[`RECOVERY.md`](RECOVERY.md) before deleting retained state.
