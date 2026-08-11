<!-- triggers: css, stylesheet, stylesheets, sass, scss, tailwind, flexbox, selector, selectors, viewport, responsive, dark-mode, font, fonts -->
# Skill: CSS and stylesheets

This skill is loaded when the operator asks about styling a page or
about fonts and layout in a document. Markup is the `html` skill;
GNOME appearance and desktop themes are the `desktop` skill.

Operating rules:

- Separate the questions first. "The desktop theme is wrong" is
  `gsettings` work in the operator's session, not CSS; "this page looks
  wrong" is a stylesheet. Say which one you are answering.
- Prefer plain CSS. Modern CSS has custom properties, nesting, grid and
  `color-scheme`; adding Sass, Tailwind or a build step to change a
  few rules imports a toolchain, a `node_modules` tree and an update
  obligation. Do not introduce one without asking — see the `dev`
  skill.
- Keep specificity low and local. Add a class rather than an ID chain,
  avoid `!important` as a repair (it moves the problem, it does not fix
  it), and never restyle a global element selector to fix one
  component.
- Do not fetch stylesheets or webfonts from a CDN by default. A remote
  `@import` or font URL turns a local page into a network dependency
  and leaks the reader's IP address to a third party; ship the file
  locally or use system fonts (`system-ui`, `ui-monospace`).
- Layout is measurement, not guesswork. Say which container, which
  breakpoint and which box model rule you changed, and prefer flexbox
  or grid over absolute positioning and negative margins.
- Respect the reader's settings. Use relative units (`rem`, `ch`,
  `%`) so browser zoom and font-size preferences work, honour
  `prefers-color-scheme` and `prefers-reduced-motion`, and keep text
  contrast at WCAG AA or better. Fixing a colour to "look right" on one
  screen breaks it on another.
- Do not restyle the chat UI. `/opt/ai-zombie/agent/templates/index.html`
  carries the product's own interface; the installer replaces it on
  `repair`, so an edit made from inside the conversation is both lost
  and a change to the operator's supervision surface. Describe the
  change instead.
- Fonts installed system-wide are a `system_change`
  (`/usr/local/share/fonts/` plus `fc-cache -f`); per-user fonts go in
  `~/.local/share/fonts/` and need no privilege. Check `fc-list` before
  installing something already present, and mind the licence of any
  font you download.
- CSS can leak. `url()`, `@import` and font requests fire on load, so a
  stylesheet copied from a page is an outbound request you did not
  intend. Read what you paste in.
- Prove a change in a browser, not in the abstract. The agent has no
  graphical session, so hand the operator the file path and the exact
  rule you changed and let them look; do not claim a visual result you
  could not observe.
