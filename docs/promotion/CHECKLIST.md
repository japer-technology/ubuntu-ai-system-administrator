# Launch Checklist

Walk this top to bottom. Boxes are grouped by phase. See
[`social/CONTENT-CALENDAR.md`](social/CONTENT-CALENDAR.md) for timing.

## 1. Repository readiness
- [ ] README is current; logo renders; badges are green (CI, CodeQL, Scorecard)
- [ ] GitHub "About" set to the approved short description (messaging/TAGLINES.md)
- [ ] Repository topics added (ubuntu, linux, ai, sysadmin, open-source, security)
- [ ] `SECURITY.md`, `SUPPORT.md`, `CONTRIBUTING.md`, `LICENSE` present and linked
- [ ] Latest release published with signed `.deb`, checksum, and cosign signatures
- [ ] Discussions enabled and a "Welcome / Ask us anything" thread seeded
- [ ] Every command in the promo copy dry-run tested on a clean VM

## 2. Assets produced (assets/ASSET-MANIFEST.md)
- [ ] Logo derivatives (square, horizontal, mono variants, favicon)
- [ ] OG/social banner (1200×630) and platform headers
- [ ] Screenshots captured and redacted (assets/SCREENSHOTS.md)
- [ ] Demo video recorded, captioned, and a social cut exported (video/)

## 3. Copy finalised (all bracketed fields filled, British spelling)
- [ ] Every claim checked against messaging/KEY-FEATURES.md (approved claims)
- [ ] Taglines / boilerplate / positioning reviewed
- [ ] Social posts (social/SOCIAL-POSTS.md)
- [ ] Show HN (community/SHOW-HN.md) + prepared answers
- [ ] Product Hunt (community/PRODUCT-HUNT.md)
- [ ] Reddit posts adapted per subreddit (community/REDDIT.md)
- [ ] Blog announcement (blog/LAUNCH-ANNOUNCEMENT.md)
- [ ] Press release + press kit (press/)
- [ ] Launch email (email/LAUNCH-EMAIL.md)
- [ ] Every link clicked and verified; no broken or placeholder URLs

## 4. Accounts & access
- [ ] X/Twitter, Mastodon, Bluesky, LinkedIn profiles updated (logo, header, bio link)
- [ ] Product Hunt page drafted and scheduled
- [ ] Email list / sender domain warmed and authenticated (SPF/DKIM)
- [ ] Analytics / UTM links prepared (optional)

## 5. Launch day (see CONTENT-CALENDAR.md for order/times)
- [ ] Show HN posted; author monitoring the thread
- [ ] Social posts live (X thread, Mastodon, Bluesky, LinkedIn)
- [ ] Reddit posts live with author disclosure
- [ ] Blog published
- [ ] Launch email sent
- [ ] Team available to answer questions; point hard ones to SECURITY.md

## 6. Post-launch (T+1 to T+14)
- [ ] Reply to every comment/issue/Discussion within the first 48h
- [ ] Feature-drip social posts scheduled (--dry-run, audit log, doctor/repair,
      local LLM discovery, TTL kill switch, optional Forgejo forge)
- [ ] Product Hunt launch (its own day if possible)
- [ ] Recap post: what we learned + top questions
- [ ] Log feedback/feature requests into the issue tracker / roadmap

## 7. Guardrails (don't skip)
- [ ] Never imply the AI is autonomous or "takes over" the machine
- [ ] Always make the operator's control and kill switch (TTL) obvious
- [ ] Never claim SSH/VNC/Tailscale features — the loopback chat is the only
      network surface (see messaging/KEY-FEATURES.md)
- [ ] Include the Canonical/Ubuntu trademark disclaimer where space allows
- [ ] Disclose authorship on HN / Reddit; no upvote solicitation or alt accounts
- [ ] No secrets, real keys, hostnames, or IPs in any asset
