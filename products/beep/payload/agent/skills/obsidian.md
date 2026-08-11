<!-- triggers: obsidian, vault, vaults, note, notes, notetaking, markdown, zettelkasten -->
# Skill: Obsidian and markdown vaults

This skill is loaded when the operator mentions Obsidian, a vault, or
their markdown notes.

Operating rules:

- Obsidian is not in the Ubuntu archive. The supported install paths,
  in order of preference: Flatpak from Flathub
  (`flatpak install -y flathub md.obsidian.Obsidian`), the vendor
  `.deb` downloaded to `/tmp` and installed with
  `sudo apt-get install -y ./obsidian_*.deb`, or the vendor AppImage
  placed under `~/Applications` and made executable. All three are
  `system_change` or `user_change` and wait for approval. Do not add a
  vendor apt repository and never pipe an installer script to a shell.
- Say which path you used and how to update it later: Flatpak updates
  with `flatpak update`, the `.deb` needs a fresh download, the
  AppImage updates itself in place.
- A vault is just a directory of markdown files plus a `.obsidian/`
  configuration folder. It lives under `/home`, which is outside the
  `fs.read`/`fs.list` allow-list, so vault work goes through
  `shell.run` — and running as the agent user means using `sudo -u
  <operator>` for files the operator owns, so new files do not end up
  root-owned inside their vault.
- Notes are the operator's own writing. Read before you edit, change
  the smallest possible span, and never bulk-rewrite, reformat or
  reorganise a vault without an explicit, specific request. A
  find-and-replace across hundreds of notes is not a small change.
- Renaming or moving a note breaks `[[wikilinks]]` and embeds unless
  Obsidian itself does the rename. Prefer letting the application
  handle renames; if a shell rename is unavoidable, grep for inbound
  links first (`grep -rl '\[\[Old Title' <vault>`) and report what
  would break.
- Take a backup before any batch operation: `tar -czf
  /tmp/vault-$(date +%Y%m%d%H%M%S).tar.gz -C <parent> <vault>` and
  tell the operator the path. `.obsidian/workspace.json` and plugin
  state are part of the vault; do not delete them to "clean up".
- Do not install, enable or update community plugins on the operator's
  behalf. They are third-party code running with the operator's own
  privileges; describe the plugin and let the operator decide in the
  application.
- Sync is the operator's business. If they use Obsidian Sync, Syncthing,
  Git or a cloud folder, ask before touching files — an edit made while
  the sync client is running can produce conflict copies. For a
  Git-backed vault, prefer ordinary `git status`/`git diff` (both
  `read_only`) to explain state before proposing a commit; the `git`
  skill covers the rest.
- Vaults hold personal and often sensitive writing. Quote only the
  lines needed to answer the question, never dump note contents into
  the transcript wholesale, and never send them off the machine.
