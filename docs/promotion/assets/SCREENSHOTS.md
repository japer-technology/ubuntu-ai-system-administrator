# Screenshot Shot-List

What to capture, how to stage it, and what to redact. Use a clean throwaway VM
so nothing sensitive ever appears. Redact any API keys, hostnames, IP addresses,
or usernames in post.

## Staging
- Fresh Ubuntu Desktop LTS VM (22.04 or 24.04).
- Terminal: dark theme, monospace font (e.g. JetBrains Mono), comfortable size.
- Browser/chat: open to `http://127.0.0.1:7878/` — keep the localhost address
  visible; it's part of the story.
- Window chrome: clean; hide personal bookmarks/extensions.

## Shots

### 1. Chat proposing a fix — `shot-chat.png`
- Prompt typed by the user, e.g. "Wi-Fi drops after suspend — can you fix it?"
- Agent reply visible: short explanation + the exact commands it would run.
- This is the hero screenshot; make it the cleanest one.

### 2. Approval / policy gate — `shot-approval.png`
- The approval prompt for a privileged action, clearly showing the operator is
  being asked to confirm before anything runs.

### 3. Audit log — `shot-auditlog.png`
- An excerpt of the audit log showing asked → proposed → approved → done.

### 4. Dry run — `shot-dryrun.png`
- Terminal output of `sudo ./scripts/install.sh install --dry-run`, showing the
  plan with the "no changes" framing visible.

### 5. Verify — `shot-verify.png`
- `sudo ./scripts/install.sh verify` (or `/opt/ai-zombie/bin/verify`) read-only
  state check with healthy output.

### 6. Subcommands — `shot-subcommands.png` (optional)
- `--help` or the subcommand list (install / verify / doctor / repair /
  uninstall) for docs and the press kit.

## Optional / nice-to-have
- `doctor` explaining a simulated failure.
- The password gate on the chat UI (redact the password field).
- `/ttl` output showing the remaining Time to Live.
- `/lmstudio` discovering a local model server, or `/models` listing local
  models — the fully-offline story.
- The optional Forgejo forge at `https://<host>.local` (redact the hostname
  or use a staged one).
- An SSH tunnel command (`ssh -L 7878:127.0.0.1:7878 user@host`) to illustrate
  the do-it-yourself remote-access story (SSH is the operator's own, not
  provisioned by the installer).
- A composite "before/after" of a fixed issue.

## Redaction checklist (every shot)
- [ ] No API keys or secrets
- [ ] No real hostnames / IPs / MAC addresses
- [ ] No personal usernames or file paths
- [ ] No unrelated notifications or windows
