<!-- triggers: user, users, account, accounts, group, groups, sudo, sudoers, adduser, useradd, usermod, deluser, passwd, password, chown, chmod, ownership, umask -->
# Skill: users, groups and permissions

This skill is loaded when the operator mentions accounts, groups, sudo
rights, passwords or file ownership.

Operating rules:

- Inspect with the `read_only` tools first: `id <user>`,
  `getent passwd <user>`, `getent group <group>`, `groups <user>`,
  `who`, `last`. `fs.read` can read `/etc/passwd`, `/etc/group` and
  the files under `/etc/sudoers.d/` because `/etc` is on the readable
  allow-list.
- Every identity mutation is `system_change` and waits for approval:
  `useradd`, `adduser`, `usermod`, `groupadd`, `groupmod`, `gpasswd`,
  `chpasswd`, `chage`, `visudo`, `passwd`, and also `chmod`, `chown`,
  `chgrp` and `setfacl`.
- `userdel`/`deluser` and locking or deleting a password
  (`passwd -l`, `passwd -d`) are `destructive`. Deleting an account can
  orphan its files and destroy the only administrative login on the
  machine; say that plainly before the operator confirms.
- Never widen sudo rights as a convenience. A new `NOPASSWD` entry, a
  blanket `ALL=(ALL) ALL` rule, or adding an account to `sudo` is a
  change to who controls the machine, not a fix for a permission error.
  Propose the narrowest grant that solves the stated problem.
- Do not modify the `agent` account, its sudoers drop-in, its home
  directory or the `zombie-*` groups. That is Ubuntu Zombie's own
  privilege boundary; changing it edits the trust model from inside the
  agent. If the operator wants it changed, point them at
  `scripts/install.sh` and its `repair` subcommand.
- Never echo password material, hashes from `/etc/shadow`, or SSH
  private keys into the chat. `/etc/shadow` is not readable through
  `fs.read` for the same reason, and the `secrets` skill covers
  credential handling in general.
- Prefer group membership over broadened file modes. `chmod 777` on a
  shared directory is almost always the wrong repair for "permission
  denied", and it is irreversible in the sense that nobody remembers
  what the mode used to be — record the original mode before changing
  it.
- Group changes take effect on the next login. Say so, rather than
  leaving the operator to wonder why the fix "did not work".
