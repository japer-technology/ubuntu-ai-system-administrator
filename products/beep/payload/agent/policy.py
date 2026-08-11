"""Policy gate.

Reads ``/etc/beep/policy.yaml`` (or ``$BEEP_POLICY``) on
every classification so the operator can edit it without restarting
the chat service.

The YAML parser is a small dependency-free reader sufficient for the
flat structure of the shipped policy file. Operators are not expected
to write arbitrary YAML here; the schema is fixed.

Classification is argv-aware (env-prefix and ``sudo`` flags are
stripped before rule matching), fail-closed for unknown commands
(they escalate to ``default_class``), and honours a sudo allow-list
so that common privileged targets keep their ``system_change``
posture instead of being escalated by the fail-closed default.
"""
from __future__ import annotations

import os
import re
import shlex
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

POLICY_PATH = Path(os.environ.get("BEEP_POLICY", "/etc/beep/policy.yaml"))

# Ordered low → high severity. ``_max_class`` exploits the index.
CLASS_ORDER = (
    "read_only",
    "chat_schedule",
    "user_change",
    "system_change",
    "network_change",
    "destructive",
)

_CLASS_RANK = {name: idx for idx, name in enumerate(CLASS_ORDER)}
_AUTO_APPROVAL_CLASSES = frozenset({"read_only", "chat_schedule"})

# ``sudo`` flags that consume the following argv token (``sudo -u root cmd``
# strips both ``-u`` and ``root`` before the real target is reached).
_SUDO_FLAGS_WITH_VALUE = frozenset({
    "-u", "--user",
    "-g", "--group",
    "-D", "--chdir",
    "-h", "--host",
    "-p", "--prompt",
    "-r", "--role",
    "-t", "--type",
    "-C", "--close-from",
    "-T", "--command-timeout",
    "-U", "--other-user",
})

# Single-letter ``sudo`` flags that take no value. ``-i`` and ``-s`` open
# an interactive shell with no further argv, so there is no target to
# classify; we treat those as "no underlying program" and fall back to
# the sudo allow-list (typically not hit) and the default class.
_SUDO_BARE_FLAGS = frozenset({
    "-A", "-b", "-E", "-H", "-K", "-k", "-l", "-L",
    "-n", "-P", "-S", "-V", "-v",
})

_ENV_ASSIGN_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*=")


@dataclass
class ClassDef:
    name: str
    approval: str = "required"            # "auto" or "required"
    confirm_phrase: bool = False
    description: str = ""


@dataclass
class Rule:
    pattern: re.Pattern[str]
    class_name: str


@dataclass
class Policy:
    classes: dict[str, ClassDef] = field(default_factory=dict)
    rules: list[Rule] = field(default_factory=list)
    destructive_confirmation: str = "yes, I understand this is destructive"
    # Fail-closed: unknown commands classify as the highest gated
    # class so they cannot auto-run. Operators may relax this in
    # ``policy.yaml`` once they have proven a workflow safe.
    default_class: str = "destructive"
    # Curated ``sudo`` targets pre-classified as ``system_change``.
    # The standard approval prompt still fires; no destructive-phrase
    # ceremony is added.
    sudo_allow_list: tuple[str, ...] = ()
    # Operator overrides of per-tool default classes
    # (e.g. ``svc.status: read_only``). Empty dict = use the
    # registry-shipped defaults from ``tools.TOOL_REGISTRY``.
    tool_classes: dict[str, str] = field(default_factory=dict)
    # Per-turn agent budgets that bound runaway loops while leaving ample
    # capacity for deep local-model tasks.
    max_tool_calls_per_turn: int = 1000
    max_elevated_calls_per_turn: int = 250
    # Wall-clock idle deadline (seconds) for a single agent turn. If the
    # model/provider produces no event for this long the turn is
    # terminated and the operator sees a clean error instead of an
    # indefinitely-pending request. It measures *silence* (any streamed
    # token / tool call / tool result resets it), so a generous value
    # does not slow normal turns. ``0`` disables the watchdog. Must stay
    # the smallest of the three layered idle deadlines (Python < bridge
    # BEEP_PI_MONO_IDLE_TIMEOUT < client CLIENT_TURN_TIMEOUT_MS).
    max_turn_seconds: int = 86400

    def classify(self, command: str | Iterable[str]) -> str:
        """Return the most-elevated class implied by ``command``.

        ``command`` may be a rendered shell string (the historical
        contract) or an iterable of argv tokens. The classifier:

        1. Applies every rule to the rendered whole command so that
           shell-syntax rules (``>``, ``|``, ``sudo bash``, …) keep
           working as before.
        2. Splits the command into top-level pipeline / sequence
           segments and, for each segment, strips leading
           ``VAR=value`` env prefixes and ``sudo`` flags before
           re-applying the rules to the canonical argv. This catches
           cases the legacy regex-only matcher missed (``LC_ALL=C ls``
           was misclassified as the fail-closed default; ``sudo apt
           install`` only matched because the ``\\bapt`` rule does not
           anchor at ``^``).
        3. If a segment is a ``sudo`` invocation whose target program
           sits in ``sudo_allow_list``, ensures at least
           ``system_change``.
        4. If nothing matched, returns ``default_class`` (P0.2:
           fail-closed = the highest gated class).
        """
        whole = command if isinstance(command, str) else " ".join(command)
        matches: list[str] = []

        for rule in self.rules:
            if rule.pattern.search(whole):
                matches.append(rule.class_name)

        for segment_text, target_argv, was_sudo in _walk_segments(whole):
            if target_argv:
                # Use a plain whitespace join so that operator
                # characters (``>``, ``2>&1``) preserved by ``shlex``
                # are not re-quoted; the existing regex rules in
                # ``policy.yaml`` key on those characters appearing
                # bare. Tokens that originally contained spaces are
                # not re-quoted — that is intentional, classification
                # operates on argv, not on a shell-roundtrippable
                # rendering.
                rendered = " ".join(target_argv)
            else:
                rendered = segment_text
            for rule in self.rules:
                if rule.pattern.search(rendered):
                    matches.append(rule.class_name)
            if was_sudo and target_argv:
                target = os.path.basename(target_argv[0])
                if target in self.sudo_allow_list:
                    matches.append("system_change")

        if not matches:
            return self.default_class
        return _max_class(matches)

    def requires_approval(self, class_name: str) -> bool:
        return self.classes.get(class_name, ClassDef(class_name)).approval != "auto"

    def requires_phrase(self, class_name: str) -> bool:
        return bool(self.classes.get(class_name, ClassDef(class_name)).confirm_phrase)

    def classify_tool(self, name: str, args: dict[str, Any] | None) -> str:
        """Classify a structured tool call.

        Every ``pi-mono`` tool call is passed through this method so
        the operator-editable ``policy.yaml`` remains the single
        source of truth, even though the assistant no longer emits
        free-form shell.

        ``shell.run`` falls through to :meth:`classify` against the
        rendered argv so the existing regex/argv ruleset (and the
        sudo allow-list) continues to apply unchanged. All other tools
        are looked up in :data:`~tools.TOOL_REGISTRY` for their
        registered default class, then escalated by ``policy.yaml``
        overrides under the ``tool_classes:`` block if present.

        Unknown tools fall through to ``default_class`` (fail-closed).
        """
        try:
            from tools import TOOL_REGISTRY  # local import to avoid cycle
        except Exception:  # pragma: no cover - tools.py should always import
            TOOL_REGISTRY = {}  # type: ignore[assignment]

        args = args or {}
        if name == "shell.run":
            argv = args.get("argv")
            if isinstance(argv, list) and argv:
                return self.classify([str(a) for a in argv])
            cmd = args.get("command")
            if isinstance(cmd, str) and cmd.strip():
                return self.classify(cmd)
            # No argv and no command — refuse to auto-run.
            return self.default_class

        if name == "agent.manage":
            if args.get("operation") == "uninstall":
                return "destructive"
            return "system_change"

        spec = TOOL_REGISTRY.get(name)
        if spec is None:
            return self.default_class
        override = self.tool_classes.get(name)
        cls = override if override else str(spec.get("classification", self.default_class))
        if cls not in _CLASS_RANK:
            return self.default_class
        return cls


# ----- argv-aware helpers (P0.1) ----------------------------------------


def _max_class(names: Iterable[str]) -> str:
    best = -1
    best_name = "read_only"
    for name in names:
        rank = _CLASS_RANK.get(name, _CLASS_RANK["destructive"])
        if rank > best:
            best = rank
            best_name = name if name in _CLASS_RANK else "destructive"
    return best_name


def _split_top_level(command: str) -> list[str]:
    """Split ``command`` on unquoted ``|``, ``&&``, ``||``, ``;``.

    Newlines are **not** separators: heredocs and multi-line proposals
    must remain a single segment so that the existing
    ``(?<!<)>``-style rules and the cached whole-command match still
    line up with what the operator sees on screen.
    """
    out: list[str] = []
    buf: list[str] = []
    i, n = 0, len(command)
    quote: str | None = None
    escape = False
    while i < n:
        ch = command[i]
        if escape:
            buf.append(ch)
            escape = False
            i += 1
            continue
        if quote:
            buf.append(ch)
            if ch == "\\" and quote == '"':
                escape = True
            elif ch == quote:
                quote = None
            i += 1
            continue
        if ch in ("'", '"'):
            quote = ch
            buf.append(ch)
            i += 1
            continue
        if ch == "\\":
            buf.append(ch)
            escape = True
            i += 1
            continue
        # Two-character operators first.
        if ch == "&" and i + 1 < n and command[i + 1] == "&":
            out.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch == "|" and i + 1 < n and command[i + 1] == "|":
            out.append("".join(buf))
            buf = []
            i += 2
            continue
        if ch in ("|", ";"):
            out.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    out.append("".join(buf))
    return [s.strip() for s in out if s.strip()]


def _strip_env_prefix(argv: list[str]) -> list[str]:
    out = list(argv)
    while out and _ENV_ASSIGN_RE.match(out[0]):
        out.pop(0)
    return out


def _strip_sudo(argv: list[str]) -> tuple[list[str], bool]:
    """If ``argv[0]`` is ``sudo``, return ``(target_argv, True)``.

    ``target_argv`` is the argv that ``sudo`` would actually execute
    (``sudo`` plus its own flags removed). If ``sudo`` was invoked
    without an underlying program (``sudo -i``, ``sudo -s``,
    ``sudo --list``) the returned target argv is empty but the
    second tuple element is still ``True`` so the caller can fall
    back to the sudo allow-list / default class.
    """
    if not argv or os.path.basename(argv[0]) != "sudo":
        return argv, False
    i = 1
    while i < len(argv):
        tok = argv[i]
        if tok == "--":
            i += 1
            break
        if tok.startswith("--"):
            # Long flags. ``--preserve-env=foo`` carries its value
            # inline; ``--user``/etc. take the next token. Bare
            # ``--long`` flags that take no value are uncommon for
            # sudo but tolerated as no-op.
            head = tok.split("=", 1)[0]
            if "=" not in tok and head in _SUDO_FLAGS_WITH_VALUE:
                i += 2
            else:
                i += 1
            continue
        if tok.startswith("-") and len(tok) > 1:
            if tok in _SUDO_FLAGS_WITH_VALUE:
                i += 2
                continue
            if tok in _SUDO_BARE_FLAGS:
                i += 1
                continue
            # Unknown short flag (or a value-taking flag with the value
            # glued on, e.g. ``-uroot``). Skip just this token.
            i += 1
            continue
        break
    return argv[i:], True


def _walk_segments(command: str) -> list[tuple[str, list[str], bool]]:
    """Yield ``(segment_text, target_argv, was_sudo)`` for each segment.

    ``target_argv`` is the argv after env-prefix and sudo stripping;
    it may be empty when the segment could not be tokenised (in which
    case the caller falls back to ``segment_text``) or when ``sudo``
    was invoked without a target.
    """
    segments = _split_top_level(command) or [command]
    out: list[tuple[str, list[str], bool]] = []
    for seg in segments:
        try:
            argv = shlex.split(seg, posix=True, comments=False)
        except ValueError:
            argv = []
        argv = _strip_env_prefix(argv)
        target, was_sudo = _strip_sudo(argv)
        out.append((seg, target, was_sudo))
    return out


# ----- minimal YAML reader sufficient for our schema --------------------

def _parse_value(raw: str) -> Any:
    raw = raw.strip()
    if raw.startswith(("'", '"')) and raw.endswith(raw[0]) and len(raw) >= 2:
        return raw[1:-1]
    low = raw.lower()
    if low in {"true", "yes", "on"}:
        return True
    if low in {"false", "no", "off"}:
        return False
    if low in {"null", "~", ""}:
        return None
    if raw == "{}":
        return {}
    if raw == "[]":
        return []
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    return raw


def _load_yaml(text: str) -> dict[str, Any]:
    """Parse the subset of YAML actually used by ``policy.yaml``.

    Supports nested mappings via indentation, lists of mappings via
    ``- key: value``, scalar values, and ``#`` line comments. Does not
    support anchors, flow style, multi-line scalars, or complex keys.
    """
    root: dict[str, Any] = {}
    # Stack entries are (indent, container, owner, owner_key) where
    # ``owner[owner_key] is container``; the root has no owner.
    stack: list[tuple[int, Any, Any, Any]] = [(-1, root, None, None)]
    pending_list_item: dict[str, Any] | None = None
    pending_list_indent: int = -1

    for raw_line in text.splitlines():
        stripped_full = raw_line.split("#", 1)[0].rstrip()
        if not stripped_full.strip():
            continue
        indent = len(raw_line) - len(raw_line.lstrip(" "))
        content = stripped_full.strip()

        # Pop deeper scopes off the stack.
        while stack and indent < stack[-1][0]:
            stack.pop()
            pending_list_item = None

        parent_indent, parent, owner, owner_key = stack[-1]

        if content.startswith("- "):
            # List item. The current parent must be (or become) a list.
            item_text = content[2:].strip()
            if not isinstance(parent, list):
                # Convert: parent is the empty mapping created when the
                # previous key opened this block. Replace it with a list
                # in its owner.
                if (
                    isinstance(parent, dict)
                    and not parent
                    and isinstance(owner, dict)
                ):
                    new_list: list[Any] = []
                    owner[owner_key] = new_list
                    parent = new_list
                    stack[-1] = (parent_indent, parent, owner, owner_key)
                else:
                    raise ValueError("unexpected list item")
            if ":" in item_text:
                key, _, val = item_text.partition(":")
                item: dict[str, Any] = {key.strip(): _parse_value(val)}
                parent.append(item)
                pending_list_item = item
                pending_list_indent = indent
                stack.append((indent + 2, item, None, None))
            else:
                parent.append(_parse_value(item_text))
            continue

        if ":" in content:
            key, _, val = content.partition(":")
            key = key.strip()
            val = val.strip()
            if val == "":
                # Opens a nested mapping or list. Decide which by
                # looking ahead implicitly: create a dict; if the
                # next sibling starts with "- " we'll replace it.
                new_container: Any = {}
                container_owner: Any = None
                container_key: Any = None
                if isinstance(parent, dict):
                    parent[key] = new_container
                    container_owner, container_key = parent, key
                elif isinstance(parent, list):
                    if pending_list_item is None:
                        raise ValueError("nested mapping outside list item")
                    pending_list_item[key] = new_container
                    container_owner, container_key = pending_list_item, key
                stack.append(
                    (indent + 2, new_container, container_owner, container_key)
                )
                # Peek the next non-comment, non-blank line is handled
                # naturally: if it starts with "- ", we need a list.
            else:
                value = _parse_value(val)
                if isinstance(parent, dict):
                    parent[key] = value
                elif isinstance(parent, list):
                    if pending_list_item is None:
                        raise ValueError("scalar outside list item")
                    pending_list_item[key] = value
            continue

    # Fix-up: any empty dict whose *next* siblings would be list items
    # was created as a dict; convert when needed. We do a simple
    # post-process: walk root and look for dicts that were "intended"
    # as lists. With the shipped policy file, every list parent is
    # ``rules:`` directly under root.
    if isinstance(root.get("rules"), dict) and not root["rules"]:
        root["rules"] = []
    return root


def _coerce_rules(raw: Any) -> list[Rule]:
    """Re-parse ``rules:`` from the raw text because our minimal YAML
    creates an empty dict before it sees the first ``- pattern:`` line.
    """
    out: list[Rule] = []
    if not isinstance(raw, list):
        return out
    for item in raw:
        if not isinstance(item, dict):
            continue
        pattern = item.get("pattern")
        class_name = item.get("class")
        if not pattern or not class_name:
            continue
        try:
            # FIX-3-25: compile with re.MULTILINE so the ``^...``
            # anchors in policy.yaml match the start of each line in a
            # multi-line command, not just the very first character.
            compiled = re.compile(str(pattern), re.MULTILINE)
        except re.error:
            continue
        out.append(Rule(pattern=compiled, class_name=str(class_name)))
    return out


def _extract_rules_from_text(text: str) -> list[Rule]:
    """Robust standalone extractor for the ``rules:`` block."""
    out: list[Rule] = []
    in_rules = False
    pattern: str | None = None
    for raw_line in text.splitlines():
        stripped = raw_line.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        if stripped.lstrip() == "rules:":
            in_rules = True
            continue
        if in_rules and stripped and not stripped.startswith(" ") and stripped.endswith(":"):
            # Top-level section after rules: stop.
            break
        if not in_rules:
            continue
        line = stripped.strip()
        if line.startswith("- pattern:"):
            val = line[len("- pattern:"):].strip()
            pattern = _strip_quotes(val)
        elif line.startswith("pattern:"):
            pattern = _strip_quotes(line[len("pattern:"):].strip())
        elif line.startswith("class:") and pattern is not None:
            class_name = _strip_quotes(line[len("class:"):].strip())
            try:
                # FIX-3-25: see _coerce_rules — match every line so
                # multi-line proposals still classify correctly.
                out.append(Rule(pattern=re.compile(pattern, re.MULTILINE),
                                class_name=class_name))
            except re.error:
                pass
            pattern = None
    return out


def _strip_quotes(s: str) -> str:
    if len(s) >= 2 and s[0] == s[-1] and s[0] in ("'", '"'):
        return s[1:-1]
    return s


def _extract_sudo_allow_list_from_text(text: str) -> tuple[str, ...]:
    """Robust standalone extractor for the ``sudo_allow_list:`` block.

    Mirrors :func:`_extract_rules_from_text`: the minimal YAML loader
    creates an empty dict for any key whose value opens a block, so a
    list of bare scalars cannot be round-tripped through it. Reading
    the raw text avoids that limitation.
    """
    out: list[str] = []
    in_block = False
    for raw_line in text.splitlines():
        stripped = raw_line.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        if stripped.lstrip() == "sudo_allow_list:":
            in_block = True
            continue
        if in_block and stripped and not stripped.startswith(" ") and stripped.endswith(":"):
            break
        if not in_block:
            continue
        line = stripped.strip()
        if line.startswith("- "):
            value = _strip_quotes(line[2:].strip())
            if value:
                out.append(value)
    return tuple(out)


_cache: tuple[tuple[str, int, int], Policy] | None = None


def _policy_source_valid(text: str, data: dict[str, Any]) -> bool:
    if set(data) - {
        "settings",
        "sudo_allow_list",
        "classes",
        "rules",
        "tool_classes",
        "agent",
    }:
        return False
    settings = data.get("settings", {})
    if not isinstance(settings, dict) or set(settings) - {
        "destructive_confirmation",
        "default_class",
    }:
        return False
    confirmation = settings.get(
        "destructive_confirmation", "yes, I understand this is destructive"
    )
    default_class = settings.get("default_class", "destructive")
    if (
        not isinstance(confirmation, str)
        or not confirmation.strip()
        or len(confirmation) > 256
        or default_class not in CLASS_ORDER
    ):
        return False

    classes = data.get("classes", {})
    if not isinstance(classes, dict) or set(classes) - set(CLASS_ORDER):
        return False
    for spec in classes.values():
        if (
            not isinstance(spec, dict)
            or set(spec) - {"approval", "confirm_phrase", "description"}
            or spec.get("approval", "required") not in {"auto", "required"}
            or not isinstance(spec.get("confirm_phrase", False), bool)
            or not isinstance(spec.get("description", ""), str)
        ):
            return False

    rules = _extract_rules_from_text(text)
    in_rules = False
    pattern_count = 0
    class_count = 0
    for raw_line in text.splitlines():
        stripped = raw_line.split("#", 1)[0].rstrip()
        if not stripped.strip():
            continue
        if stripped.lstrip() == "rules:":
            in_rules = True
            continue
        if (
            in_rules
            and not stripped.startswith(" ")
            and stripped.endswith(":")
        ):
            break
        if in_rules:
            line = stripped.strip()
            pattern_count += int(line.startswith("- pattern:"))
            class_count += int(line.startswith("class:"))
    if (
        pattern_count != class_count
        or len(rules) != pattern_count
        or any(rule.class_name not in CLASS_ORDER for rule in rules)
    ):
        return False

    tool_classes = data.get("tool_classes", {})
    if not isinstance(tool_classes, dict) or any(
        not isinstance(name, str)
        or not isinstance(class_name, str)
        or class_name not in CLASS_ORDER
        for name, class_name in tool_classes.items()
    ):
        return False
    agent = data.get("agent", {})
    if not isinstance(agent, dict) or set(agent) - {
        "max_tool_calls_per_turn",
        "max_elevated_calls_per_turn",
        "max_turn_seconds",
    }:
        return False
    for name, value in agent.items():
        if (
            isinstance(value, bool)
            or not isinstance(value, int)
            or value < (0 if name == "max_turn_seconds" else 1)
        ):
            return False
    return True


def validate_policy(path: Path = POLICY_PATH) -> bool:
    """Return whether an existing policy is syntactically and semantically valid."""
    try:
        if not path.is_file() or path.is_symlink():
            return False
        text = path.read_text(encoding="utf-8")
        data = _load_yaml(text)
    except (OSError, UnicodeError, ValueError):
        return False
    return _policy_source_valid(text, data)


def load_policy(path: Path = POLICY_PATH) -> Policy:
    global _cache
    try:
        st = path.stat()
    except FileNotFoundError:
        return _default_policy()
    # FIX-3-14: use ``(st_mtime_ns, st_size)`` as the cache key. The
    # previous key was ``st_mtime`` (seconds), which loses two writes
    # inside the same FS tick (common on tmpfs / certain CI setups).
    # The path is part of the key: two different policy files can
    # share a size and mtime (common in tests and on tmpfs), and the
    # cached ``Policy`` for one must never be served for the other.
    key = (str(path), st.st_mtime_ns, st.st_size)
    if _cache is not None and _cache[0] == key:
        return _cache[1]
    try:
        text = path.read_text(encoding="utf-8")
        data = _load_yaml(text)
    except (OSError, UnicodeError, ValueError):
        policy = _default_policy()
        _cache = (key, policy)
        return policy
    if not _policy_source_valid(text, data):
        policy = _default_policy()
        _cache = (key, policy)
        return policy

    settings = data.get("settings", {}) if isinstance(data, dict) else {}
    classes_raw = data.get("classes", {}) if isinstance(data, dict) else {}

    classes: dict[str, ClassDef] = {}
    for name in CLASS_ORDER:
        spec = classes_raw.get(name, {}) if isinstance(classes_raw, dict) else {}
        if not isinstance(spec, dict):
            spec = {}
        classes[name] = ClassDef(
            name=name,
            approval=str(spec.get(
                "approval",
                "auto" if name in _AUTO_APPROVAL_CLASSES else "required",
            )),
            confirm_phrase=bool(spec.get("confirm_phrase", name == "destructive")),
            description=str(spec.get("description", "")),
        )

    rules = _extract_rules_from_text(text)
    if not rules:
        rules = _coerce_rules(data.get("rules"))

    sudo_allow_list = _extract_sudo_allow_list_from_text(text)

    tool_classes_raw = data.get("tool_classes", {}) if isinstance(data, dict) else {}
    tool_classes: dict[str, str] = {}
    if isinstance(tool_classes_raw, dict):
        for k, v in tool_classes_raw.items():
            if isinstance(k, str) and isinstance(v, str) and v in CLASS_ORDER:
                tool_classes[k] = v

    agent_raw = data.get("agent", {}) if isinstance(data, dict) else {}
    if not isinstance(agent_raw, dict):
        agent_raw = {}

    policy = Policy(
        classes=classes,
        rules=rules,
        destructive_confirmation=str(
            settings.get("destructive_confirmation", "yes, I understand this is destructive")
        ),
        # Fail-closed default. Falls back to ``destructive`` (the
        # highest gated class in ``CLASS_ORDER``) if the operator did
        # not pin a value in ``policy.yaml``.
        default_class=str(settings.get("default_class", "destructive")),
        sudo_allow_list=sudo_allow_list,
        tool_classes=tool_classes,
        max_tool_calls_per_turn=_coerce_int(
            agent_raw.get("max_tool_calls_per_turn"), 1000),
        max_elevated_calls_per_turn=_coerce_int(
            agent_raw.get("max_elevated_calls_per_turn"), 250),
        max_turn_seconds=_coerce_int(
            agent_raw.get("max_turn_seconds"), 86400, min_val=0),
    )
    _cache = (key, policy)
    return policy


def _coerce_int(value: Any, default: int, min_val: int = 1) -> int:
    try:
        n = int(value)
        return n if n >= min_val else default
    except (TypeError, ValueError):
        return default


def _default_policy() -> Policy:
    return Policy(
        classes={
            "read_only": ClassDef("read_only", approval="auto"),
            "chat_schedule": ClassDef("chat_schedule", approval="auto"),
            "user_change": ClassDef("user_change"),
            "system_change": ClassDef("system_change"),
            "network_change": ClassDef("network_change"),
            "destructive": ClassDef("destructive", confirm_phrase=True),
        },
        rules=[],
        # Fail-closed: a missing policy file is treated as maximally
        # restrictive so a misconfigured host cannot auto-run anything.
        default_class="destructive",
        sudo_allow_list=(),
    )


# Silence unused-import warnings when policy.py is the only thing
# loaded by smoke tests.
_ = time
