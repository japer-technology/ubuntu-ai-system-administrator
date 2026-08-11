<!-- triggers: git, clone, commit, commits, branch, branches, merge, rebase, checkout, gitignore, submodule, worktree, stash -->
# Skill: git working copies

This skill is loaded when the operator mentions git, a working copy, or
an operation on their history. Hosting a forge on this machine is the
`forgejo` skill; language toolchains are the `dev` skill.

Operating rules:

- Read the repository before touching it. `git status`, `git log
  --oneline -20`, `git diff`, `git remote -v` and `git branch -vv` are
  `read_only` and auto-run. Say which branch, which remote and how far
  ahead or behind the working copy is before proposing anything.
- Working copies live under `/home`, which is outside the
  `fs.read`/`fs.list` allow-list, so this is `shell.run` work. Run it
  with `-C <path>` rather than relying on the working directory, and
  use `sudo -u <operator>` so new objects are not left root-owned
  inside the operator's repository.
- Never rewrite published history on the operator's behalf. `git
  rebase`, `git commit --amend`, `git filter-branch` and any
  `git push --force`/`--force-with-lease` change commits other clones
  already have. Describe what would change and let the operator decide.
- Uncommitted work is the thing most easily destroyed. `git checkout
  -- <path>`, `git restore`, `git reset --hard`, `git clean -fd` and
  `git stash drop` discard changes with no undo; they are `destructive`
  and need the exact confirmation phrase. Show `git status --short`
  first so the operator sees exactly what disappears.
- Prefer additive recovery. A stash, a scratch branch, or a copy of the
  tree under `/tmp` costs nothing and turns an irreversible step into a
  reversible one.
- Commit messages and authorship are the operator's voice. Do not
  invent a message, do not change `user.name`/`user.email`, and do not
  commit files the operator did not mention — read the staged diff and
  name every path.
- Never commit secrets. Check the diff for keys, tokens, `.env` files
  and private keys before staging; once pushed, a secret is leaked and
  the answer is rotation, not a follow-up commit. See the `secrets`
  skill.
- `git push` publishes to a remote and can leave the machine. Treat it
  as an explicit operator decision, name the remote and branch, and
  never push to a remote the operator did not ask for.
- Submodules and worktrees surprise people: `git status` in a
  superproject hides changes inside a submodule, and `git worktree`
  directories share one object store. Report their state explicitly
  rather than assuming a clean parent means a clean tree.
- Merge conflicts are a decision, not a chore. Show both sides, say
  which you would keep and why, and leave the resolution to the
  operator when the content is theirs.
- Repositories can be large. Bound history reads (`-n`, `--since`,
  `--stat`) instead of dumping a full `git log -p` into the transcript.
