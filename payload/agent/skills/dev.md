<!-- triggers: python, python3, pip, pipx, venv, virtualenv, conda, poetry, node, nodejs, npm, npx, nvm, yarn, pnpm, cargo, rustup, golang, gradle, maven, jdk, java, gcc, compile, toolchain, sdk -->
# Skill: language toolchains and development environments

This skill is loaded when the operator mentions Python, Node, Rust, Go,
Java or the tools that install them. Distribution packaging is the `apt`
skill; version control is the `git` skill.

Operating rules:

- Establish what is already installed before adding anything:
  `python3 -V`, `pip --version`, `node -v`, `npm -v`, `cargo --version`,
  `go version`, `java -version` and `update-alternatives --display
  java` are `read_only` and auto-run. Two toolchains installed by
  different mechanisms is the usual root cause of "it works in my
  terminal but not in the service".
- Never install Python packages into the system interpreter. Ubuntu's
  `python3` is a *system component*; `sudo pip install` is externally
  managed for a reason and can break `apt`, `netplan` and the desktop.
  Use a virtual environment (`python3 -m venv`), `pipx` for
  applications, or the packaged `python3-<name>` from the archive.
- Prefer per-user, per-project installs over global ones. A `venv`, a
  `node_modules` tree or a `~/.cargo` install is the operator's own
  state and needs no system change; installing a toolchain globally
  affects every user and every future upgrade.
- Vendor install scripts are still `curl … | bash`. `rustup`, `nvm`,
  Deno, Bun and many SDKs publish exactly that pattern; it is forbidden
  here. Fetch the script to `/tmp`, read it, and let the operator run
  it themselves, or use the packaged alternative and say what is lost.
- Installing dependencies runs arbitrary code. `npm install`,
  `pip install`, `cargo build` and Gradle all execute upstream build
  hooks with the invoking user's privileges, so treat them as a change
  even inside a project directory. Never run them as root, and never
  add `--break-system-packages`, `--force`, `--unsafe-perm` or
  `--ignore-scripts=false` to push past a guard.
- Project trees live under `/home`, outside the `fs.read`/`fs.list`
  allow-list, so this is `shell.run` work — with `sudo -u <operator>`
  so build artefacts are not left root-owned in their project.
- Builds are unbounded. Bound the output (`| tail -50`), avoid watch
  and dev-server commands that never return, and say when a build is
  large enough that the operator should run it in their own terminal.
- Lockfiles are the record of what was tested. Do not regenerate
  `package-lock.json`, `poetry.lock`, `Cargo.lock` or
  `requirements.txt` as a side effect of fixing something else; show
  the version change you intend and let the operator approve it.
- `.env` files, `~/.npmrc`, `~/.pypirc` and `~/.docker/config.json`
  hold registry tokens. Do not read them into the chat and do not
  commit them. See the `secrets` skill.
- Do not touch the agent's own runtime. `${AI_SYS_ADMIN_DIR}/` ships a
  managed virtual environment and pinned bridge dependencies; upgrading
  a package inside it out of band breaks the chat service. Changes
  there go through the installer's `repair`.
- Report the exact interpreter or toolchain path you used
  (`which python3`, `readlink -f $(which node)`). "It is installed" is
  ambiguous on a machine with a snap, a `.deb` and a version manager
  all providing the same command.
- Before editing a project, find its contributor and agent instructions,
  inspect `git status`, identify generated files, and learn the existing
  lint/build/test commands. Repository-local instructions outrank generic
  language advice.
- Make the smallest coherent change. Do not reformat unrelated files,
  rewrite history, discard local modifications, or silently modify lockfiles,
  generated output and vendored code.
- Validate in increasing scope: syntax or targeted tests first, then the
  repository's existing lint, test and build commands. Do not install a new
  checker merely to validate a small change.
- Keep test and build commands non-interactive and bounded. Never launch a
  watcher, development server or interactive debugger through the agent
  unless the operator explicitly requests and can control that process.
- Before committing or handing back changes, review the diff for accidental
  credentials, machine-local paths, debug output and unrelated edits; report
  tests that were run and any validation that could not run.
