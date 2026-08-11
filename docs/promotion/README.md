# Ubuntu Zombie — Promotion Kit

This folder is the scaffold for every piece of promotional material used to
promote **Ubuntu Zombie**. It collects brand rules, ready-to-edit copy, and
launch checklists in one place so a launch can be assembled quickly and stay
on-message.

Everything here is a *starting point*. Treat the files as editable templates:
fill in the bracketed `[PLACEHOLDER]` fields, swap in real screenshots and
links, and adapt the tone to each channel before publishing.

## The product in one line

> **Ubuntu Zombie adds a private, root-capable AI Systems Administrator account
> to a supported Ubuntu Desktop LTS machine, so the owner can ask the computer
> to diagnose, explain, configure, repair, and operate itself — in plain
> language, under explicit human approval, with every action audit-logged.**

Source of truth for messaging: [`../README.md`](../README.md),
[`../docs/VISION.md`](../docs/VISION.md), and
[`../LOGO-MEANING.md`](../LOGO-MEANING.md). If anything in this kit contradicts
those documents, those documents win.

## What's in here

| Path | What it holds |
| ---- | ------------- |
| [`brand/`](brand/) | Brand guidelines, voice & tone, logo usage, colour palette |
| [`messaging/`](messaging/) | Taglines, elevator pitch, positioning, key features / approved claims, boilerplate, press FAQ |
| [`social/`](social/) | Per-platform social posts (X/Twitter, LinkedIn, Mastodon, Bluesky, Reddit) |
| [`community/`](community/) | Show HN, Product Hunt, and Reddit launch copy |
| [`blog/`](blog/) | Launch announcement / blog post draft |
| [`press/`](press/) | Press release and a one-page press kit |
| [`email/`](email/) | Launch and newsletter email drafts |
| [`video/`](video/) | Demo video script and storyboard |
| [`landing-page/`](landing-page/) | Static landing-page draft(s) |
| [`assets/`](assets/) | Asset manifest and screenshot shot-list |
| [`CHECKLIST.md`](CHECKLIST.md) | End-to-end launch checklist |

## How to use this kit

1. Read [`brand/BRAND-GUIDELINES.md`](brand/BRAND-GUIDELINES.md) and
   [`brand/VOICE-AND-TONE.md`](brand/VOICE-AND-TONE.md) first. They govern
   every other file.
2. Check every claim against
   [`messaging/KEY-FEATURES.md`](messaging/KEY-FEATURES.md) — the approved
   claims matrix. If the product changes, update that file first, then the
   channel copy.
3. Lift the core copy from [`messaging/`](messaging/) and adapt it per channel.
4. Produce the assets listed in [`assets/ASSET-MANIFEST.md`](assets/ASSET-MANIFEST.md).
5. Walk [`CHECKLIST.md`](CHECKLIST.md) on launch day.

## House style

- **British / Commonwealth English** everywhere (colour, organise, behaviour,
  authorise, recognise). This matches the rest of the repository.
- Lead with **honesty and control**, not hype. This project grants a
  root-capable identity on someone's machine; the copy should always make the
  operator's ownership and kill switch obvious.
- Never imply the AI is autonomous or "takes over" the machine. It listens,
  proposes, waits for approval, acts, and logs.
- Only make claims listed in
  [`messaging/KEY-FEATURES.md`](messaging/KEY-FEATURES.md) or backed by the
  repository docs. In particular: the installer provisions **no SSH, VNC, or
  Tailscale**; the only network surface is the password-protected loopback
  chat; local LLMs are **shipped**, not roadmap; and the administrator has a
  built-in Time to Live.
