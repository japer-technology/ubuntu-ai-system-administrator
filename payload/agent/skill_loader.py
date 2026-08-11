"""Skill loader for the pi-mono runtime.

A *skill* is a short on-disk markdown document that nudges the agent
toward the correct typed tool for a class of operator request.
Skills never expand the tool registry — adding a tool still requires
a code release.

A skill file is plain markdown with an optional first-line HTML-comment
trigger marker, for example::

    <!-- triggers: apt, dpkg, package -->
    # Skill: APT package management
    ...

The loader scans two directories:

* ``/opt/ai-zombie/skills/``        — root-owned, ships with the package.
* ``/etc/ubuntu-zombie/skills.d/``  — operator-extensible, same
  mode/owner contract as ``/etc/ubuntu-zombie/policy.yaml``.

When a chat turn starts, :func:`select_skills` returns the skills whose
trigger words appear in the last *N* user messages.
:func:`render_skills_block` wraps the selected skills in a prompt
fragment that includes the on-disk path of each skill so the operator
can see *what* was injected (skill provenance). The selected skills
are also recorded as ``skill_active`` history events by the chat
service for the same reason.

Skill content is *never* mutated; it is read verbatim from disk so a
file-level audit (``ls -l``, ``sha256sum``) reflects what the model
actually saw.
"""
from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable


# Default trigger-window: how many of the most recent user messages to
# scan for trigger words. Small on purpose — operators do not want a
# skill from ten turns ago to come back to life.
DEFAULT_RECENT_USER_MESSAGES = 4

# Trigger marker — first matching HTML comment within the first
# ``_TRIGGER_SCAN_BYTES`` of the file. Tokens are comma- or
# whitespace-separated and matched case-insensitively against word
# boundaries in the user message.
_TRIGGER_RE = re.compile(r"<!--\s*triggers?\s*:\s*([^>]+?)\s*-->", re.IGNORECASE)
_TRIGGER_SCAN_BYTES = 4096

# Skill name must be filesystem-safe; mirrors the validator in
# ``tools._shim_skill_load``.
_NAME_RE = re.compile(r"^[A-Za-z0-9_-]+$")


@dataclass(frozen=True)
class Skill:
    """One on-disk skill."""

    name: str
    path: Path
    triggers: tuple[str, ...] = field(default_factory=tuple)

    def read(self) -> str:
        """Return the skill body verbatim (UTF-8, errors replaced)."""
        return self.path.read_text(encoding="utf-8", errors="replace")


def default_skill_dirs() -> list[Path]:
    """Return the ordered list of directories to scan for skills.

    The override env var ``ZOMBIE_SKILLS_DIR`` is honoured first so
    tests and ``make package`` smoke runs can point at the in-tree
    ``payload/agent/skills/`` directory without root-owned paths.
    """
    dirs: list[Path] = []
    env = os.environ.get("ZOMBIE_SKILLS_DIR")
    if env:
        for chunk in env.split(os.pathsep):
            chunk = chunk.strip()
            if chunk:
                dirs.append(Path(chunk))
    dirs.append(Path("/opt/ai-zombie/skills"))
    dirs.append(Path("/etc/ubuntu-zombie/skills.d"))
    return dirs


def _extract_triggers(body: str) -> tuple[str, ...]:
    head = body[:_TRIGGER_SCAN_BYTES]
    match = _TRIGGER_RE.search(head)
    if not match:
        return ()
    raw = match.group(1)
    tokens = [t.strip().lower() for t in re.split(r"[,\s]+", raw) if t.strip()]
    # Preserve order but drop duplicates.
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return tuple(out)


def load_skills(dirs: Iterable[Path] | None = None) -> list[Skill]:
    """Discover all ``*.md`` skills under ``dirs``.

    The earliest directory wins on name collision so an operator file
    in ``/etc/ubuntu-zombie/skills.d/`` cannot quietly shadow the
    shipped skill of the same name (and vice versa, depending on
    ordering). Files whose stem is not a valid skill name (per
    ``_NAME_RE``) are skipped — the same constraint ``skill.load``
    enforces — so a typo cannot become an unreachable skill.
    """
    seen: dict[str, Skill] = {}
    for directory in (dirs if dirs is not None else default_skill_dirs()):
        if not directory or not directory.is_dir():
            continue
        for path in sorted(directory.glob("*.md")):
            name = path.stem
            if not _NAME_RE.match(name) or name in seen:
                continue
            try:
                body = path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            seen[name] = Skill(name=name, path=path, triggers=_extract_triggers(body))
    return list(seen.values())


def _tokenize(text: str) -> set[str]:
    """Return the set of lowercased word tokens found in ``text``."""
    return {tok.lower() for tok in re.findall(r"[A-Za-z0-9][A-Za-z0-9_-]*", text or "")}


def select_skills(
    user_messages: Iterable[str],
    *,
    recent: int = DEFAULT_RECENT_USER_MESSAGES,
    dirs: Iterable[Path] | None = None,
    skills: Iterable[Skill] | None = None,
) -> list[Skill]:
    """Return the skills whose trigger words match recent user input.

    ``user_messages`` is iterated in order; only the *last* ``recent``
    are considered (the most recent operator turn is always one of
    them). A skill is selected when *any* of its triggers appears as
    a whole word in any of the considered messages. Skills with an
    empty trigger list are never auto-selected; they may still be
    fetched explicitly via the ``skill.load`` tool.
    """
    msgs = list(user_messages)
    if recent > 0:
        msgs = msgs[-recent:]
    haystack: set[str] = set()
    for m in msgs:
        haystack |= _tokenize(m)
    if not haystack:
        return []
    catalogue = list(skills) if skills is not None else load_skills(dirs)
    matched: list[Skill] = []
    for skill in catalogue:
        if not skill.triggers:
            continue
        if any(trig in haystack for trig in skill.triggers):
            matched.append(skill)
    return matched


def render_skills_block(skills: Iterable[Skill]) -> str:
    """Render the selected skills as a system-prompt fragment.

    The block is empty when no skills match. Each skill is preceded by
    a provenance header naming the on-disk path so prompt-injection via
    a skill remains visible (§6.4 — "skill provenance"). The body of
    each skill is included verbatim.
    """
    parts: list[str] = []
    for skill in skills:
        body = skill.read()
        parts.append(
            "# Active skill: {name}\n"
            "# Source: {path}\n\n"
            "{body}".format(name=skill.name, path=skill.path, body=body.rstrip())
        )
    if not parts:
        return ""
    header = (
        "The following skills were loaded because their trigger words "
        "appeared in your recent prompts. They are guidance, not new "
        "tools. The closed tool registry is unchanged."
    )
    return header + "\n\n" + "\n\n---\n\n".join(parts)
