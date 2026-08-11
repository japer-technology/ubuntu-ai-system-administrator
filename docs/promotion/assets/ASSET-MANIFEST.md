# Asset Manifest

The full inventory of visual assets needed for a launch. Tick each as it's
produced. Drop finished files in this folder (or a `dist/` subfolder) and update
the status. Follow [`../brand/BRAND-GUIDELINES.md`](../brand/BRAND-GUIDELINES.md)
for colour, logo clear-space, and usage rules.

## Existing source art
- [x] `../../LOGO.png` — master logo (split robot/skull, shared orchid eye)

## Logo derivatives to produce
| File | Size | Use | Status |
| ---- | ---- | --- | ------ |
| `logo-square.png` | 512×512, 240×240, 48×48 | Social avatars, favicon | ☐ |
| `logo-horizontal.png` | scalable | Header lock-up (logo + wordmark) | ☐ |
| `logo-mono-orchid-on-ink.png` | scalable | Dark backgrounds | ☐ |
| `logo-mono-ink-on-paper.png` | scalable | Light backgrounds | ☐ |
| `favicon.ico` | 32×32, 16×16 | Site favicon | ☐ |

## Social / share images
| File | Size | Use | Status |
| ---- | ---- | --- | ------ |
| `og-banner.png` | 1200×630 | Open Graph / Twitter / LinkedIn share | ☐ |
| `x-header.png` | 1500×500 | X/Twitter profile header | ☐ |
| `social-square.png` | 1080×1080 | Instagram / square posts | ☐ |
| `ph-thumbnail.png` | 240×240 | Product Hunt thumbnail | ☐ |

## Screenshots
See [`SCREENSHOTS.md`](SCREENSHOTS.md) for the full shot-list. Minimum set:
| File | Shows | Status |
| ---- | ----- | ------ |
| `shot-chat.png` | Local chat proposing a fix | ☐ |
| `shot-approval.png` | Policy-gate approval prompt | ☐ |
| `shot-auditlog.png` | Audit-log excerpt | ☐ |
| `shot-dryrun.png` | `install --dry-run` output | ☐ |
| `shot-verify.png` | `verify` read-only state check | ☐ |

## Video
| File | Use | Status |
| ---- | --- | ------ |
| `demo-75s.mp4` | Full demo (see ../video/DEMO-SCRIPT.md) | ☐ |
| `demo-social-cut.mp4` | 15–20s muted autoplay cut | ☐ |
| `demo.srt` | Captions / transcript | ☐ |

## Conventions
- Keep originals (SVG / high-res PNG) and export web-optimised copies separately.
- Name files lower-case with hyphens.
- Do not commit large raw video into the repo; link to hosted copies and keep
  only lightweight stills here unless the team decides otherwise.
- Redact any keys, hostnames, or IPs in every screenshot before committing.
