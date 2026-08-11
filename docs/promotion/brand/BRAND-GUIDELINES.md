# Brand Guidelines

These rules apply to every promotional asset for Ubuntu Zombie. They derive
from [`../../LOGO-MEANING.md`](../../LOGO-MEANING.md) and the brand palette
defined in `scripts/lib.sh`.

## The name

- The product is **Ubuntu Zombie** — two words, both capitalised.
- The publisher is **Japer Technology** (`japer.technology`).
- Never write "ubuntu-zombie" in prose except when it is literally a
  repository, package, or command name (e.g. `ubuntu-zombie_<ver>_all.deb`).
- "Ubuntu" is a trademark of Canonical. Always present Ubuntu Zombie as a
  third-party project *for* Ubuntu, never as an official Canonical product.
  Include the disclaimer in [`../messaging/BOILERPLATE.md`](../messaging/BOILERPLATE.md)
  wherever space allows.

## Colour palette — "Zombie Orchid"

| Token | Hex | RGB | Use |
| ----- | --- | --- | --- |
| Brand (Orchid) | `#AC43D9` | 172, 67, 217 | Primary highlight, headlines, the eye |
| Brand tint | `#C77BE6` | 199, 123, 230 | Lighter accents, gradients, hovers |
| Accent (Teal) | `#43D9AC` | 67, 217, 172 | Complementary call-outs, "approved/ok" states |
| Magenta | `#D943AC` | 217, 67, 172 | Warm secondary accent, sparingly |
| Ubuntu Orange | `#E95420` | 233, 84, 32 | Only when pairing with the Ubuntu badge/identity |
| Ink | `#1A1320` | 26, 19, 32 | Near-black background that flatters the orchid |
| Paper | `#F7F4FA` | 247, 244, 250 | Light background |

- **Orchid is the operator's colour.** In the logo it is the single shared eye.
  Use it as the one consistent thread across every asset.
- Purple, never red. Red reads as hostile; this product is calm and consented.
- Maintain WCAG AA contrast for any text. Orchid on ink passes for large text;
  check small text before shipping.

## The logo

- Canonical artwork: [`../../LOGO.png`](../../LOGO.png).
- It is a single head split vertically: a calm white robot (the AI Systems
  Administrator) on the left, a weathered human skull (the owner's real PC) on
  the right, sharing one glowing purple eye (the operator's control).
- **Clear space:** keep at least the height of the purple eye clear on all
  sides.
- **Minimum size:** 48 px tall on screen; do not use below this — the split
  face stops reading.
- **Do not:** recolour the eye away from orchid, separate the two halves, add a
  drop shadow that turns it into a horror mark, place it on a low-contrast
  background, or stretch/skew it.
- Full symbolism (and what the logo deliberately does *not* say) lives in
  [`../../LOGO-MEANING.md`](../../LOGO-MEANING.md). Read it before designing
  anything — every element maps to a real product promise.

## Typography

- Prefer a clean, neutral sans for UI and body (system UI stack or Inter).
- Use a monospace face (e.g. JetBrains Mono, Fira Code) for commands, terminal
  output, and the `127.0.0.1:7878` chat motif — the product is a transparent
  bash installer, and the type should feel that way.

## Imagery rules

- Show the real terminal and the local chat UI. Authenticity is the brand.
- Prefer the local-only motif (`127.0.0.1`, an SSH tunnel) over generic
  "cloud" imagery — there is no public inbound exposure to depict.
- Avoid stock "evil AI" / glowing-red-robot clichés. They contradict the
  consented, auditable posture.

## Logo file inventory (to produce — see assets manifest)

- [ ] `LOGO.png` (exists, repo root)
- [ ] Square avatar crop (favicon / social profile)
- [ ] Horizontal lock-up (logo + wordmark) for headers
- [ ] Monochrome (orchid-on-ink and ink-on-paper) variants
- [ ] Open Graph / social share banner (1200×630)
