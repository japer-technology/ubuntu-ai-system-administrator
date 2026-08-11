# The Meaning of the Ubuntu Zombie Logo

![Ubuntu Zombie Logo](LOGO.png)

One head. Two natures. A single purple light that answers to you.

The Ubuntu Zombie logo is a face split cleanly down the middle. On
the left, a smooth white robot wearing black over-ear headphones
with a boom microphone. On the right, a weathered, cracked human
skull. The two halves share the same eye line, the same jaw, and
the same glowing purple eye — so they read as one face, not two
images pasted together.

Nothing in the mark is decoration. Every element maps to a promise
the project makes in [`README.md`](README.md),
[`docs/VISION.md`](docs/VISION.md), and [`SECURITY.md`](SECURITY.md).
Read the logo left to right and you have read the whole trust model.

---

## The split — one machine, two identities

*The seam is the story.*

A machine running Ubuntu Zombie is still an ordinary Ubuntu Desktop
PC for the human sitting in front of it — that is the organic,
human side. And it is simultaneously the home of a root-capable AI
Systems Administrator living inside it — the manufactured, machine
side. The halves are fused into one head because they are one
computer: the same disk, the same network identity. Not a separate
appliance. Not a hosted service. One skull, shared.

The seam is deliberately clean and centered. The AI does not creep
across the line and "take over," and the human does not pretend the
AI isn't there. Coexistence, drawn as anatomy.

## The robot half (left) — the administrator

*Engineered. Inspectable. Replaceable.*

- **Smooth white shell.** The administrator is a clean,
  well-defined software surface: a named Linux user (`zombie` by
  default, renameable via `ZOMBIE_USER`), a policy gate, an audit
  log, a chat UI on `127.0.0.1:7878`. Nothing hidden under the
  plastic that you cannot open and read.
- **Headphones and boom microphone.** It acts only when spoken to.
  You open a private chat, you ask, it proposes, you approve, it
  acts. A listener with a mouth — never an autonomous agent that
  decides what your PC is for.
- **The calm, curved eye.** Drawn as a gentle upward arc: content,
  attentive, on call. A helpful operator, not a looming presence.

## The skull half (right) — the zombie

*There was a PC here before the installer arrived.*

- **Human bone, not chrome.** This is an Ubuntu *Zombie*, not an
  Ubuntu *Robot*. The machine was already someone's real computer
  with a real owner. The skull says: the AI reanimates capability
  that already belonged to the owner — it does not summon a new
  creature.
- **Cracks across the bone.** Real machines are imperfect. Drivers
  drift, packages break, configs rot. The cracks are honest about
  the administrator's actual job — diagnosing, explaining,
  repairing, and operating a messy real system, including the
  `doctor` and `repair` subcommands.
- **Bared teeth.** Not smiling, not snarling — exposed. Ubuntu
  Zombie is candid about granting a root-capable identity on your
  machine; `SECURITY.md` exists for exactly this reason. The teeth
  are a reminder, not a threat.

## The shared purple eye — the operator's light

*One light. One will. Yours.*

Both halves burn with the same purple glow: a calm curve on the
robot, a bright focused point in the skull's socket. This is the
most important element in the logo.

- **One light, one will.** The same operator owns both halves. The
  SSH private key, the LLM API key, the Tailscale account, the
  policy file, and the kill switch all belong to the human in front
  of the machine. The AI has no independent eye of its own.
- **The light is on because you switched it on.** Run
  `sudo ./scripts/install.sh uninstall` and the glow goes out on
  both sides at once. Nothing in this logo shines without consent.
- **Purple, on purpose.** Red would read as hostile; blue would
  read as a generic tech mascot. Purple belongs to neither the
  white plastic nor the bone — it is the operator's color, layered
  over both identities.

## The wired headphones — the network boundary

*Cupped ears, not antennas.*

The headphones sit only on the robot side, and they are wired. That
is the network posture from `README.md` and `SECURITY.md` made
visible: the administrator listens on a private channel — local
chat, or SSH tunneled over a private Tailscale tailnet — never on
the open internet. No public inbound exposure. The ears are cupped
and cabled, not broadcasting in every direction.

## What the logo is *not* saying

- **Not a horror mark.** The skull is weathered, not bloody; the
  robot is calm, not menacing. The tone matches the project's
  promise: a useful, auditable tool, not a stunt.
- **Not "AI replaces human."** The human half is literally still
  there, sharing the same face. The AI is an administrator *for*
  the owner of the machine, never a replacement *of* them.
- **Not a hosted-service brand.** No cloud, no swoosh, no
  third-party badge. The face is self-contained because the machine
  is self-contained: the operator owns the hardware, the keys, and
  the off switch.

---

## One-line reading

> An ordinary PC (the skull) with a calm, listening, root-capable
> AI Systems Administrator fused to it (the robot), sharing one
> glowing eye that belongs to the operator who can turn it off.
