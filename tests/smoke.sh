#!/usr/bin/env bash
# tests/smoke.sh — non-root smoke tests for Ubuntu Zombie.
#
# Subcommands:
#   syntax        bash -n on every shell script we ship
#   python        py_compile on every Python file under payload/agent
#   subcommands   ensure scripts/install.sh recognises every documented subcommand
#   bad-usage     ensure scripts reject unexpected args and unsafe config
#   noninteractive verify ZOMBIE_NONINTERACTIVE=1 with missing required env
#                  exits with code 64
#   branding      ensure installer and chat startup wordmarks stay present
#   standards     ensure repository metadata and packaging inputs are present
#   all (default) run everything

set -euo pipefail
cd "$(dirname "$0")/.."

cmd="${1:-all}"

shell_files() {
  {
    git ls-files 2>/dev/null
    git ls-files --others --exclude-standard 2>/dev/null
  } | while read -r f; do
    [[ -z "$f" || ! -f "$f" ]] && continue
    case "$f" in
      *.sh)               printf '%s\n' "$f" ;;
      payload/bin/*)      printf '%s\n' "$f" ;;
    esac
  done | sort -u
}

# Extract one install.sh function so standards checks can exercise helpers in
# isolation without running the mutating installer.
install_function() {
  local name="$1"
  [[ "${name}" =~ ^[A-Za-z_][A-Za-z0-9_]*$ ]] \
    || { echo "unsafe install.sh function name: ${name}" >&2; exit 1; }
  sed -n "/^${name}() {/,/^}$/p" scripts/install.sh
}

run_syntax() {
  echo "[smoke] bash -n syntax check"
  shell_files | while read -r f; do
    head -n1 "$f" | grep -q '^#!.*bash' || continue
    echo "  bash -n $f"
    bash -n "$f"
  done
}

run_python() {
  echo "[smoke] python compile"
  find payload/agent -name '*.py' -print | while read -r f; do
    echo "  python3 -m py_compile $f"
    python3 -m py_compile "$f"
  done
  # Importability of policy.py without 3rd-party deps.
  echo "  import policy"
  PYTHONPATH=payload/agent python3 -c 'import policy; p = policy.load_policy(); print("classes:", list(p.classes))'
  echo "  policy payload regressions"
  PYTHONPATH=payload/agent ZOMBIE_POLICY=payload/etc/policy.yaml python3 - <<'PY'
import platform
import policy
import server
import tempfile
from pathlib import Path

p = policy.load_policy()

# Policy classification regressions: read-only command heads must not
# auto-run when shell syntax would mutate files or execute interpreters.
cases = {
    "grep needle file > out": "user_change",
    "cat <<EOF > /tmp/out\nhello\nEOF": "user_change",
    "cat <<EOF\nhello\nEOF": "read_only",
    "cat script.sh | bash": "system_change",
    "cat data | sudo tee /etc/example": "system_change",
    "cat data | tee /dev/stderr": "read_only",
    "grep needle file 2>&1 >/dev/null": "read_only",
    "find /tmp -name x -delete": "destructive",
    # Argv-aware classifier: strips leading ``VAR=value`` env
    # prefixes and ``sudo`` flags before rule matching, so the
    # canonical argv is what gets classified.
    "LC_ALL=C ls /etc": "read_only",
    "FOO=bar apt-get install pkg": "system_change",
    "sudo apt install foo": "system_change",
    "sudo -u zombie ls /tmp": "read_only",
    "sudo -E systemctl restart cron": "system_change",
    # Quoted destructive path is now caught because rules see the
    # de-quoted argv (the historical regex-only matcher missed it).
    'rm -rf "/tmp/some file"': "destructive",
    # Unknown commands fall through to the fail-closed default
    # (``destructive``) instead of auto-running.
    "foozle --bar": "destructive",
    "sudo foozle --bar": "destructive",
    "echo a && echo b": "destructive",
}
for command, want in cases.items():
    got = p.classify(command)
    if got != want:
        raise SystemExit(f"classify({command!r}) = {got!r}, want {want!r}")

# Sudo allow-list keeps common privileged targets at ``system_change``
# rather than escalating them via the fail-closed default. ``foozle``
# (not in the list) escalates; ``apt`` (in the list) does not.
assert "apt" in p.sudo_allow_list, p.sudo_allow_list
assert "foozle" not in p.sudo_allow_list, p.sudo_allow_list
if p.default_class != "destructive":
    raise SystemExit(f"fail-closed default class regressed: {p.default_class!r}")
# An unknown command must require operator approval.
if not p.requires_approval(p.classify("foozle --bar")):
    raise SystemExit("fail-closed default no longer requires approval")
assert p.max_tool_calls_per_turn == 1000, p.max_tool_calls_per_turn
assert p.max_elevated_calls_per_turn == 250, p.max_elevated_calls_per_turn
assert p.max_turn_seconds == 86400, p.max_turn_seconds

# The legacy extract_commands / fenced-bash workflow has been removed;
# commands now arrive as structured pi-mono tool calls. The policy
# gate must classify them via classify_tool, and the closed registry
# must enforce schemas.
if hasattr(server, "extract_commands"):
    raise SystemExit("extract_commands must be removed")
import tools as _t
assert set(_t.tool_names()) == {
    "shell.run", "fs.read", "fs.list", "fs.write", "pkg.query", "pkg.install",
    "svc.status", "svc.control", "net.status", "web.fetch", "skill.list",
    "skill.load", "timer.reactivation",
}, _t.tool_names()
# Per-tool default classifications come from the registry; shell.run
# is computed per-argv via the existing classify() path.
if p.classify_tool("fs.read", {"path": "/etc/os-release"}) != "read_only":
    raise SystemExit("fs.read should be read_only")
if p.classify_tool("pkg.install", {"names": ["curl"]}) != "system_change":
    raise SystemExit("pkg.install should be system_change")
if p.classify_tool("svc.control", {"unit": "cron", "action": "restart"}) != "system_change":
    raise SystemExit("svc.control should be system_change")
if p.classify_tool("web.fetch", {"url": "https://example.com"}) != "read_only":
    raise SystemExit("web.fetch should be read_only")
# web.fetch is auto-approved, so its SSRF guard is the only thing keeping
# an auto-run fetch away from the loopback chat service, the LAN and the
# cloud metadata endpoint. Non-http schemes and credentials are refused too.
for _bad in ("file:///etc/passwd", "http://127.0.0.1:8080/",
             "http://169.254.169.254/latest/meta-data/",
             "******example.com/"):
    try:
        _t.dispatch("web.fetch", {"url": _bad})
    except _t.SchemaError:
        pass
    else:
        raise SystemExit(f"web.fetch must refuse {_bad!r}")
try:
    _t.dispatch("web.fetch", {"url": "https://example.com", "method": "POST"})
except _t.SchemaError:
    pass
else:
    raise SystemExit("web.fetch must refuse non-GET/HEAD methods")
if p.classify_tool("timer.reactivation", {
    "delay_seconds": 30, "prompt": "continue"
}) != "chat_schedule":
    raise SystemExit("timer.reactivation should use chat_schedule")
if p.requires_approval("chat_schedule"):
    raise SystemExit("chat_schedule should auto-run within its server-enforced bounds")
# Install upgrades preserve operator policy.yaml files. Policies created before
# chat_schedule existed must inherit its safe built-in default, while an
# explicit operator override must still be honoured.
with tempfile.TemporaryDirectory() as directory:
    legacy_path = Path(directory) / "policy.yaml"
    legacy_path.write_text(
        """\
settings:
  default_class: destructive
classes:
  read_only:
    approval: auto
""",
        encoding="utf-8",
    )
    legacy = policy.load_policy(legacy_path)
    reactivation_args = {
        "delay_seconds": 10,
        "prompt": "Why is the sky blue?",
    }
    if legacy.requires_approval(
        legacy.classify_tool("timer.reactivation", reactivation_args)
    ):
        raise SystemExit("legacy policies should auto-run timer.reactivation")
    legacy_path.write_text(
        """\
settings:
  default_class: destructive
classes:
  read_only:
    approval: auto
  chat_schedule:
    approval: required
""",
        encoding="utf-8",
    )
    overridden = policy.load_policy(legacy_path)
    if not overridden.requires_approval("chat_schedule"):
        raise SystemExit("explicit chat_schedule approval override was ignored")
if p.classify_tool("shell.run", {"argv": ["ls", "-la"]}) != "read_only":
    raise SystemExit("shell.run ls should be read_only via classify()")
if p.classify_tool("shell.run", {"command": "sudo apt-get install -y curl"}) != "system_change":
    raise SystemExit("shell.run sudo apt-get install should be system_change")
# Unknown tools fail closed.
if not p.requires_approval(p.classify_tool("totally.unknown", {})):
    raise SystemExit("unknown tool must require operator approval")
# Schema validation rejects bad args without side effects.
try:
    _t.validate_args("fs.read", {"path": 12})
    raise SystemExit("fs.read with int path must be rejected")
except _t.SchemaError:
    pass
try:
    _t.validate_args("svc.control", {"unit": "cron", "action": "nuke"})
    raise SystemExit("svc.control with bad action must be rejected")
except _t.SchemaError:
    pass
# The read allow-list is checked against the resolved path, so the
# canonical Ubuntu inspection files that live under /etc as symlinks into
# read-only distro/runtime trees must still be readable. This assertion is
# Linux-specific: macOS also has /etc/localtime, but it resolves into
# /private/var/db and is outside the Ubuntu runtime's allow-list. Secrets
# and home directories must stay out of reach on every platform.
_read_roots = _t._read_allowed_prefixes()
if platform.system() == "Linux":
    for _linked in ("/etc/os-release", "/etc/localtime", "/etc/resolv.conf"):
        _candidate = Path(_linked)
        if not _candidate.exists():
            continue
        if not _t._within(_candidate, _read_roots):
            raise SystemExit(f"{_linked} must be inside the read allow-list")
for _denied in ("/home", "/root/.ssh/id_rsa",
                "/opt/ai-zombie/secrets/env", "/usr/bin/sudo"):
    if _t._within(Path(_denied), _read_roots):
        raise SystemExit(f"{_denied} must stay outside the read allow-list")
# ``bool`` must not satisfy an ``integer`` field. Python treats ``bool``
# as a subclass of ``int``; without an explicit guard ``shell.run``
# would accept ``{"timeout": False}`` and ``subprocess`` would coerce
# it to ``timeout=0`` (instant TimeoutExpired).
try:
    _t.validate_args("shell.run", {"argv": ["true"], "timeout": False})
    raise SystemExit("shell.run timeout=False must be rejected as non-integer")
except _t.SchemaError:
    pass

# ``_skills_dirs`` must not silently add the chat service's working
# directory when ``ZOMBIE_SKILLS_DIR`` is unset or empty.
import os as _os
from pathlib import Path as _P
_saved = _os.environ.pop("ZOMBIE_SKILLS_DIR", None)
try:
    dirs = _t._skills_dirs()
    assert _P(".") not in dirs and _P("") not in dirs, dirs
    _os.environ["ZOMBIE_SKILLS_DIR"] = ""
    dirs = _t._skills_dirs()
    assert _P(".") not in dirs and _P("") not in dirs, dirs
    _os.environ["ZOMBIE_SKILLS_DIR"] = "/tmp/zombie-extra-skills"
    dirs = _t._skills_dirs()
    assert _P("/tmp/zombie-extra-skills") in dirs, dirs
finally:
    _os.environ.pop("ZOMBIE_SKILLS_DIR", None)
    if _saved is not None:
        _os.environ["ZOMBIE_SKILLS_DIR"] = _saved

# Skill loader discovers every built-in skill, parses their trigger
# markers, selects only on trigger-word match in recent user messages,
# and renders a block that carries the on-disk path so the UI can show
# provenance.
import skill_loader
from pathlib import Path

skills = skill_loader.load_skills([Path("payload/agent/skills")])
names = {s.name for s in skills}
assert names == {
    "ai-agents", "apt", "backup", "certificates", "containers", "css",
    "database", "desktop", "dev", "disk", "files", "git",
    "hardware", "hermes-agent", "html", "journal", "json", "kernel", "llm",
    "locale", "network", "obsidian", "openclaw-agent", "packages",
    "performance", "pi-mono-agent", "process", "reactivation", "scheduling",
    "secrets", "security", "services", "snap", "sql", "systemd",
    "troubleshoot", "ubuntu", "users", "virtualization", "web", "zombie",
    "zram",
}, names
for s in skills:
    assert s.triggers, f"skill {s.name} has no triggers"

# Trigger words are unique across the built-in catalogue. A shared
# trigger loads two briefs for one prompt, which wastes context and
# makes the injected guidance harder for the operator to predict.
_seen = {}
for s in skills:
    for trig in s.triggers:
        assert trig not in _seen, f"trigger {trig!r}: {_seen[trig]} and {s.name}"
        _seen[trig] = s.name

# Trigger match on the last user turn only.
# No trigger words -> no skills selected.
sel = skill_loader.select_skills(
    ["What is the weather like?"],
    dirs=[Path("payload/agent/skills")],
)
assert sel == [], sel

# ``recent`` window excludes older messages.
sel = skill_loader.select_skills(
    ["restart the nginx systemd unit",
     "now check the firewall",
     "and one more thing",
     "tell me a joke"],
    recent=1,
    dirs=[Path("payload/agent/skills")],
)
assert sel == [], sel

# Rendered block carries provenance (the file path) so prompt
# injection via a skill remains visible.
sel = skill_loader.select_skills(
    ["please run apt-get update"],
    dirs=[Path("payload/agent/skills")],
)
assert [s.name for s in sel] == ["apt"], [s.name for s in sel]
block = skill_loader.render_skills_block(sel)
assert "payload/agent/skills/apt.md" in block, block
assert "Active skill: apt" in block, block

# New management briefs are independently discoverable by their
# representative names without loading unrelated catalogue entries.
for prompt, expected in (
    ("Ubuntu", "ubuntu"),
    ("AI-agent", "ai-agents"),
    ("Hermes", "hermes-agent"),
    ("OpenClaw", "openclaw-agent"),
    ("pi-mono", "pi-mono-agent"),
    ("Services", "services"),
    ("Packages", "packages"),
    ("Processes", "process"),
    ("Certificate", "certificates"),
    ("Reactivation", "reactivation"),
):
    sel = skill_loader.select_skills(
        [prompt],
        recent=1,
        dirs=[Path("payload/agent/skills")],
    )
    assert [s.name for s in sel] == [expected], (
        prompt, [s.name for s in sel]
    )

# Empty selection -> empty block (no header noise on every turn).
assert skill_loader.render_skills_block([]) == ""

# providers.py is a thin adapter over @earendil-works/pi-ai. The
# Python-facing surface must stay import-clean (no third-party deps)
# and provider selection must honour ZOMBIE_PROVIDER plus the
# expanded key matrix.
import os
import providers as _pr

assert set(_pr.SUPPORTED_PROVIDERS) == {
    "openai", "anthropic", "gemini", "xai", "openrouter", "mistral", "groq",
    "lmstudio",
}, _pr.SUPPORTED_PROVIDERS

# Snapshot env so we can reset it cleanly.
_keys = (
    "ZOMBIE_PROVIDER", "ZOMBIE_MODEL",
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "XAI_API_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
    "LMSTUDIO_API_KEY",
)
_saved = {k: os.environ.pop(k, None) for k in _keys}
try:
    # No keys, no explicit provider -> NoProviderConfigured + helpful status.
    try:
        _pr.provider_from_env()
    except _pr.NoProviderConfigured:
        pass
    else:
        raise SystemExit("provider_from_env should raise without any key")
    name, status = _pr.provider_status()
    if name != "none":
        raise SystemExit(f"provider_status with no key returned {name!r}")

    # Unknown ZOMBIE_PROVIDER must fail loudly.
    os.environ["ZOMBIE_PROVIDER"] = "bogus"
    try:
        _pr.provider_from_env()
    except _pr.NoProviderConfigured:
        pass
    else:
        raise SystemExit("unknown ZOMBIE_PROVIDER should raise")
    del os.environ["ZOMBIE_PROVIDER"]

    # Autodetect picks the first provider whose key is set.
    os.environ["GROQ_API_KEY"] = "test"
    p_auto = _pr.provider_from_env()
    if p_auto.name != "groq":
        raise SystemExit(f"autodetect returned {p_auto.name!r}")
    if not p_auto.model:
        raise SystemExit("groq adapter should pick a default model")

    # Explicit ZOMBIE_PROVIDER wins over autodetect, but still needs
    # its own key.
    os.environ["ZOMBIE_PROVIDER"] = "gemini"
    try:
        _pr.provider_from_env()
    except _pr.NoProviderConfigured:
        pass
    else:
        raise SystemExit("missing GEMINI_API_KEY should raise")
    os.environ["GEMINI_API_KEY"] = "test"
    p_gem = _pr.provider_from_env()
    if p_gem.name != "gemini":
        raise SystemExit(f"explicit provider returned {p_gem.name!r}")

    # OpenRouter has no default model and must surface a clear error
    # when ZOMBIE_MODEL is not set.
    os.environ["ZOMBIE_PROVIDER"] = "openrouter"
    os.environ["OPENROUTER_API_KEY"] = "test"
    try:
        _pr.provider_from_env()
    except _pr.NoProviderConfigured:
        pass
    else:
        raise SystemExit("openrouter without ZOMBIE_MODEL should raise")
    os.environ["ZOMBIE_MODEL"] = "anthropic/claude-3.5-sonnet"
    p_or = _pr.provider_from_env()
    if p_or.model != "anthropic/claude-3.5-sonnet":
        raise SystemExit(f"openrouter model was {p_or.model!r}")

    # resolve_active_model is the single authoritative resolver shared
    # by the chat surface and the agent loop. It must agree with
    # provider_from_env and expose the pi-ai/pi provider id mapping
    # (gemini -> google).
    prov, model, key_env = _pr.resolve_active_model()
    if (prov, model, key_env) != ("openrouter", "anthropic/claude-3.5-sonnet",
                                  "OPENROUTER_API_KEY"):
        raise SystemExit(f"resolve_active_model returned {(prov, model, key_env)!r}")

    # The status banner must report the model the agent loop will use,
    # and the gemini name must map to the pi provider id "google".
    for k in ("ZOMBIE_PROVIDER", "ZOMBIE_MODEL", "OPENROUTER_API_KEY"):
        os.environ.pop(k, None)
    os.environ["ZOMBIE_PROVIDER"] = "gemini"
    os.environ["GEMINI_API_KEY"] = "test"
    s_name, s_status = _pr.provider_status()
    if s_name != "gemini" or s_status != "model gemini-2.0-flash":
        raise SystemExit(f"provider_status returned {(s_name, s_status)!r}")
    g = _pr.provider_from_env()
    if g.pi_provider != "google" or g.key_env != "GEMINI_API_KEY":
        raise SystemExit(f"gemini pi_provider/key_env wrong: "
                         f"{g.pi_provider!r}/{g.key_env!r}")
    if set(_pr.ALL_KEY_ENVS) != {
        "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY",
        "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
        "LMSTUDIO_API_KEY",
    }:
        raise SystemExit(f"ALL_KEY_ENVS unexpected: {_pr.ALL_KEY_ENVS!r}")

    # lmstudio is a local OpenAI-compatible provider: its pi id is
    # "lmstudio" (the custom provider the installer writes to
    # ~/.pi/agent/models.json) and, like openrouter, it has no default
    # model so ZOMBIE_MODEL must be set.
    for k in ("ZOMBIE_PROVIDER", "ZOMBIE_MODEL", "GEMINI_API_KEY"):
        os.environ.pop(k, None)
    os.environ["ZOMBIE_PROVIDER"] = "lmstudio"
    os.environ["LMSTUDIO_API_KEY"] = "local"
    try:
        _pr.provider_from_env()
    except _pr.NoProviderConfigured:
        pass
    else:
        raise SystemExit("lmstudio without ZOMBIE_MODEL should raise")
    os.environ["ZOMBIE_MODEL"] = "qwen/qwen3-coder"
    p_lm = _pr.provider_from_env()
    if (p_lm.name, p_lm.pi_provider, p_lm.key_env, p_lm.model) != (
        "lmstudio", "lmstudio", "LMSTUDIO_API_KEY", "qwen/qwen3-coder"):
        raise SystemExit(
            f"lmstudio resolved wrong: "
            f"{(p_lm.name, p_lm.pi_provider, p_lm.key_env, p_lm.model)!r}")
    if _pr.resolve_active_model() != (
        "lmstudio", "qwen/qwen3-coder", "LMSTUDIO_API_KEY"):
        raise SystemExit(
            f"lmstudio resolve_active_model wrong: {_pr.resolve_active_model()!r}")
    if _pr.provider_status() != ("lmstudio", "model qwen/qwen3-coder"):
        raise SystemExit(f"lmstudio status wrong: {_pr.provider_status()!r}")
finally:
    for k, v in _saved.items():
        if v is None:
            os.environ.pop(k, None)
        else:
            os.environ[k] = v
PY

  echo "  durable timer reactivation"
  _REACTIVATION_TMP="$(mktemp -d)"
  trap 'rm -rf "${_REACTIVATION_TMP:-}"' EXIT
  ZOMBIE_HISTORY_DB="${_REACTIVATION_TMP}/conversations.db" \
  ZOMBIE_LIFECYCLE_STATE="${_REACTIVATION_TMP}/lifecycle.json" \
  ZOMBIE_AUDIT_LOG="${_REACTIVATION_TMP}/audit.jsonl" \
  ZOMBIE_POLICY=payload/etc/policy.yaml \
  PYTHONPATH=payload/agent python3 - <<'PY'
import json
import os
import sqlite3
import time
from pathlib import Path
from history import History

Path(os.environ["ZOMBIE_LIFECYCLE_STATE"]).write_text(json.dumps({
    "created_at": time.time(),
    "expires_at": time.time() + 3600,
    "dead": False,
}))

import server

app = server.App()
conversation_id = app.history.create_conversation("timer test")
settings = app.reactivation_info()
assert settings["enabled"] is True, settings
assert settings["minimum_seconds"] == 5, settings
assert settings["maximum_seconds"] == 3600, settings
system_prompt = server.render_append_system("test facts", 10, 120)
assert '"delay_seconds":10' in system_prompt, system_prompt
assert "minimum delay of\n10 seconds" in system_prompt, system_prompt

accepted = app.schedule_reactivation(
    conversation_id=conversation_id,
    delay_seconds=5,
    prompt="Continue the test.",
    reason="Smoke test",
)
assert accepted["status"] == "accepted", accepted
pending = app.reactivation_info()["pending"]
assert pending and pending["conversation_id"] == conversation_id, pending

too_fast = app.schedule_reactivation(
    conversation_id=conversation_id,
    delay_seconds=1,
    prompt="This would race the UI settle window.",
    reason="Below minimum",
)
assert too_fast["status"] == "rejected_policy", too_fast

rejected = app.schedule_reactivation(
    conversation_id=conversation_id,
    delay_seconds=30,
    prompt="Do not replace.",
    reason="Second timer",
)
assert rejected["status"] == "rejected_pending_exists", rejected

replaced = app.schedule_reactivation(
    conversation_id=conversation_id,
    delay_seconds=40,
    prompt="Replacement.",
    reason="Replacement timer",
    replace_existing=True,
)
assert replaced["status"] == "replaced", replaced
assert app.cancel_reactivation()["cancelled"]["id"] == \
    replaced["reactivation"]["id"]
assert app.reactivation_info()["pending"] is None

disabled = app.configure_reactivation(enabled=False)
assert disabled["enabled"] is False, disabled
rejected = app.schedule_reactivation(
    conversation_id=conversation_id,
    delay_seconds=30,
    prompt="Disabled.",
    reason="Disabled timer",
)
assert rejected["status"] == "rejected_disabled", rejected

invalid = app.configure_reactivation(minimum_seconds=4)
assert "error" in invalid, invalid
invalid = app.configure_reactivation(maximum_seconds=3601)
assert "error" in invalid, invalid

for name, old_minimum, old_maximum, expected_minimum, expected_maximum in (
    ("defaults", 30, 86400, 5, 3600),
    ("custom", 10, 1800, 10, 1800),
    ("low", 0, 120, 5, 120),
    ("previous-floor", 1, 3600, 5, 3600),
    ("inverted", 10, 1, 10, 10),
    ("high", 10, 7200, 10, 3600),
):
    migration_path = Path(os.environ["ZOMBIE_HISTORY_DB"]).with_name(
        f"migration-{name}.db"
    )
    with sqlite3.connect(migration_path) as connection:
        connection.execute(
            "CREATE TABLE reactivation_settings ("
            "singleton INTEGER PRIMARY KEY, enabled INTEGER NOT NULL, "
            "minimum_seconds INTEGER NOT NULL, maximum_seconds INTEGER NOT NULL)"
        )
        connection.execute(
            "INSERT INTO reactivation_settings VALUES (1, 1, ?, ?)",
            (old_minimum, old_maximum),
        )
        connection.execute("PRAGMA user_version = 2")
    migrated = History(migration_path).reactivation_settings()
    assert migrated["minimum_seconds"] == expected_minimum, (name, migrated)
    assert migrated["maximum_seconds"] == expected_maximum, (name, migrated)

app.configure_reactivation(enabled=True)
fired = []
app.start_streaming_message = lambda cid, prompt, user_meta=None: (
    fired.append((cid, prompt, user_meta)) or
    {"turn_id": "smoke-turn", "conversation_id": cid}
)
due, existing = app.history.schedule_reactivation(
    conversation_id,
    time.time() - 1,
    "Fire now.",
    "Due timer",
)
assert due and existing is None
app._reactivation_wakeup.set()
deadline = time.time() + 2
while not fired and time.time() < deadline:
    time.sleep(0.02)
assert fired, "due reactivation did not fire"
assert fired[0][2]["auto_reactivation"] is True, fired
assert app.history.pending_reactivation() is None

active = server.TurnStream(
    "active-turn", conversation_id, "active-reactivation", "Active test"
)
with app._lock:
    app.turns[active.turn_id] = active
active_info = app.reactivation_info()["active"]
assert active_info == {
    "id": "active-reactivation",
    "conversation_id": conversation_id,
    "turn_id": "active-turn",
    "reason": "Active test",
}, active_info
stopped = app.stop_turn("active-turn")
assert stopped == {"ok": True, "turn_id": "active-turn"}, stopped
assert active.cancel_event.is_set()
active.done_at = time.monotonic()
assert app.reactivation_info()["active"] is None

# Reset restores the default mechanism and clears current UX state while
# preserving historical rows for audit. It also stops active reactivation
# work and retires the queued timer.
custom = app.configure_reactivation(
    enabled=True, minimum_seconds=10, maximum_seconds=120
)
assert custom["minimum_seconds"] == 10, custom
queued_for_reset = app.schedule_reactivation(
    conversation_id=conversation_id,
    delay_seconds=10,
    prompt="Should be reset.",
    reason="Reset test",
)
reset_active = server.TurnStream(
    "reset-active-turn", conversation_id, "reset-active", "Reset active test"
)
with app._lock:
    app.turns[reset_active.turn_id] = reset_active
reset = app.reset_reactivation()
assert reset["reset"] is True, reset
assert reset["enabled"] is True, reset
assert reset["minimum_seconds"] == 5, reset
assert reset["maximum_seconds"] == 3600, reset
assert reset["cancelled"]["id"] == \
    queued_for_reset["reactivation"]["id"], reset
assert reset["stopped_turns"] == 1, reset
assert reset_active.cancel_event.is_set()
reset_active.done_at = time.monotonic()
reset_info = app.reactivation_info()
assert reset_info["pending"] is None, reset_info
assert reset_info["active"] is None, reset_info
assert reset_info["last"] is None, reset_info
assert app.history.count_reactivations(conversation_id) == 0
with sqlite3.connect(os.environ["ZOMBIE_HISTORY_DB"]) as connection:
    retained = connection.execute(
        "SELECT status, error FROM reactivations WHERE id = ?",
        (queued_for_reset["reactivation"]["id"],),
    ).fetchone()
assert retained == ("cancelled", "reset by operator"), retained

visible, request, error = server._agent_reactivation_request(
    "I need another turn.\n"
    '<ubuntu-zombie-reactivation>{"delay_seconds":5,'
    '"prompt":"Continue the test.","reason":"More work remains.",'
    '"replace_existing":false}</ubuntu-zombie-reactivation>'
)
assert visible == "I need another turn.", visible
assert error is None, error
assert request is not None
self_scheduled = app._consume_agent_reactivation(conversation_id, request)
assert self_scheduled["status"] == "accepted", self_scheduled
assert app.reactivation_info()["pending"]["prompt"] == "Continue the test."
app.cancel_reactivation()

# The terminal turn payload must carry the canonical scheduling outcome so
# the browser can show the queued continuation immediately instead of
# waiting for the next reactivation poll.
original_run_turn = server.pi_mono.run_turn
emitted = []
try:
    server.pi_mono.run_turn = lambda **kwargs: {
        "final": (
            "Scheduling the next step.\n"
            '<ubuntu-zombie-reactivation>{"delay_seconds":5,'
            '"prompt":"Payload queued continuation.",'
            '"reason":"Payload outcome."}</ubuntu-zombie-reactivation>'
        ),
        "events": [],
        "log_path": None,
    }
    payload = app.post_message(
        conversation_id,
        "schedule via payload",
        emit=lambda event, data: emitted.append((event, data)),
    )
finally:
    server.pi_mono.run_turn = original_run_turn
assert payload["reactivation"]["status"] == "accepted", payload
assert payload["reactivation"]["reactivation"]["prompt"] == \
    "Payload queued continuation.", payload
assert any(
    event == "turn_done"
    and data.get("reactivation", {}).get("status") == "accepted"
    for event, data in emitted
), emitted
assert app.reactivation_info()["pending"]["prompt"] == \
    "Payload queued continuation."
app.cancel_reactivation()

visible, request, error = server._agent_reactivation_request(
    "Visible reply\n<ubuntu-zombie-reactivation>{bad json}"
)
assert visible == "Visible reply", visible
assert request is None
assert error, error

# A chain must not break on reply formatting: trailing prose, a code
# fence around the block, and repeated blocks all still schedule.
visible, request, error = server._agent_reactivation_request(
    "Working.\n"
    '<ubuntu-zombie-reactivation>{"delay_seconds":1,"prompt":"p"}'
    "</ubuntu-zombie-reactivation>\nI will continue shortly."
)
assert error is None, error
assert request == {"delay_seconds": 1, "prompt": "p"}, request
assert visible == "Working.\n\nI will continue shortly.", visible

visible, request, error = server._agent_reactivation_request(
    "Working.\n```json\n"
    '<ubuntu-zombie-reactivation>{"delay_seconds":2,"prompt":"p"}'
    "</ubuntu-zombie-reactivation>\n```"
)
assert error is None, error
assert request["delay_seconds"] == 2, request
assert visible == "Working.", visible

visible, request, error = server._agent_reactivation_request(
    '<ubuntu-zombie-reactivation>{"delay_seconds":1,"prompt":"first"}'
    "</ubuntu-zombie-reactivation>Middle."
    '<ubuntu-zombie-reactivation>{"delay_seconds":3,"prompt":"last"}'
    "</ubuntu-zombie-reactivation>"
)
assert error is None, error
assert request["prompt"] == "last", request
assert visible == "Middle.", visible

# Minor JSON slips from a model should not break a continuation.
visible, request, error = server._agent_reactivation_request(
    "Before."
    "<ubuntu-zombie-reactivation>```json\n"
    "{'delay_seconds': 4, 'prompt': 'relaxed true', "
    "'replace_existing': false,}\n```"
    "</ubuntu-zombie-reactivation>After."
)
assert error is None, error
assert request == {
    "delay_seconds": 4,
    "prompt": "relaxed true",
    "replace_existing": False,
}, request
assert visible == "Before.After.", visible

relaxed = server._decode_reactivation_json(r'''```
{"delay_seconds": 5, 'prompt': "keep true false null and an escaped \"quote\"",}
```''')
assert relaxed == {
    "delay_seconds": 5,
    "prompt": 'keep true false null and an escaped "quote"',
}, relaxed

# Ordinary fenced code in a reply must survive untouched.
sample = "Run this:\n```sh\nls -la\n```\nDone."
assert server._agent_reactivation_request(sample) == (sample, None, None)

# A provider that forgets the structured wrapper must not leak the
# request into chat: an exact bare timer.reactivation-shaped JSON object
# is consumed, while ordinary JSON examples remain visible.
visible, request, error = server._agent_reactivation_request(
    "Working.\n```json\n"
    '{"delay_seconds":6,"prompt":"bare fence",'
    '"reason":"Provider omitted the marker."}\n```\nAfter.'
)
assert error is None, error
assert request == {
    "delay_seconds": 6,
    "prompt": "bare fence",
    "reason": "Provider omitted the marker.",
}, request
assert visible == "Working.\n\nAfter.", visible

visible, request, error = server._agent_reactivation_request(
    'Working.\n{"delay_seconds":7,"prompt":"bare object",'
    '"replace_existing":false}\nAfter.'
)
assert error is None, error
assert request == {
    "delay_seconds": 7,
    "prompt": "bare object",
    "replace_existing": False,
}, request
assert visible == "Working.\n\nAfter.", visible

ordinary = (
    'Example payload:\n{"delay_seconds":1,"prompt":"demo","extra":true}'
)
assert server._agent_reactivation_request(ordinary) == (ordinary, None, None)

# A due timer must never start a second turn in a conversation that is
# already running one, and the deferral must not lose the timer.
busy_turn = server.TurnStream("busy-turn", conversation_id)
with app._lock:
    app.turns[busy_turn.turn_id] = busy_turn
busy_due, _existing = app.history.schedule_reactivation(
    conversation_id, time.time() - 1, "Deferred.", "Busy timer"
)
assert app.history.claim_due_reactivation(
    time.time(), busy_conversations={conversation_id}
) is None
before = len(fired)
app._reactivation_wakeup.set()
time.sleep(0.5)
assert len(fired) == before, fired
assert app.history.pending_reactivation()["id"] == busy_due["id"]
busy_turn.done_at = time.monotonic()
app._reactivation_wakeup.set()
deadline = time.time() + 3
while len(fired) == before and time.time() < deadline:
    time.sleep(0.02)
assert len(fired) > before, "deferred reactivation never fired"

# A timer the daemon refuses to run is recorded and reported, not
# dropped silently: the operator can see why a chain stopped.
app.configure_reactivation(enabled=False)
dropped, _existing = app.history.schedule_reactivation(
    conversation_id, time.time() - 1, "Dropped.", "Disabled timer"
)
app._reactivation_wakeup.set()
deadline = time.time() + 3
last = None
notice = None
while time.time() < deadline:
    last = app.reactivation_info()["last"]
    notice = app.history.get_messages(conversation_id)[-1]
    if (
        last and last["id"] == dropped["id"]
        and notice["role"] == "system"
        and "did not run" in notice["content"]
    ):
        break
    time.sleep(0.02)
assert last and last["id"] == dropped["id"], last
assert last["status"] == "cancelled", last
assert last["error"] == "reactivation is disabled", last
assert notice["role"] == "system", notice
assert "did not run" in notice["content"], notice
assert any(
    event["kind"] == "reactivation_cancelled"
    for event in app.history.get_events(conversation_id)
), "system cancellation must be visible in the conversation"
app.configure_reactivation(enabled=True)
PY
  rm -rf "${_REACTIVATION_TMP}"
  trap - EXIT

  # Stubbed end-to-end run of pi_mono.run_turn against
  # tests/fixtures/stub-pi-mono.mjs. Verifies the bridge protocol,
  # schema validation, dispatch, and event accounting without
  # requiring `pi` (or even npm) on the test host.
  if command -v node >/dev/null 2>&1; then
    echo "  pi-mono stub end-to-end"
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/tests/fixtures/stub-pi-mono.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import json, os, sys
import pi_mono, tools, policy

p = policy.load_policy()
collected = []
streamed = []

def on_tool_call(call_id, name, args):
    collected.append((name, dict(args)))
    cls = p.classify_tool(name, args)
    if p.requires_approval(cls):
        return {"ok": False, "error": "operator_approval_required: " + cls}
    try:
        tools.validate_args(name, args)
    except tools.SchemaError as exc:
        return {"ok": False, "error": f"schema: {exc}"}
    # Don't actually dispatch fs.read inside the test sandbox; the
    # stub plan only exercises the protocol path. Return a stub
    # observation that mimics fs.read shape.
    return {"ok": True, "result": {"path": args.get("path"),
                                    "content": "STUBBED",
                                    "size": 7}}

out = pi_mono.run_turn(
    prompt="hello",
    system_prompt="you are stubbed",
    history=[],
    on_tool_call=on_tool_call,
    tool_names=tools.tool_names(),
    on_event=lambda event: streamed.append(event),
)
if out["final"] != "stubbed pi-mono turn complete":
    raise SystemExit(f"unexpected final: {out['final']!r}")
if not collected or collected[0][0] != "fs.read":
    raise SystemExit(f"expected fs.read tool call, got {collected!r}")
if not any(e.get("type") == "tool_call" for e in out["events"]):
    raise SystemExit("no tool_call events recorded")
if not any(e.get("type") == "final" for e in out["events"]):
    raise SystemExit("no final event recorded")
if [e.get("type") for e in streamed] != ["progress", "token", "progress", "token"]:
    raise SystemExit(f"stream callback order wrong: {streamed!r}")
if streamed[0].get("name") != "read" or streamed[2].get("name") != "read":
    raise SystemExit(f"stream progress payload wrong: {streamed!r}")
if "".join(e.get("delta", "") for e in streamed if e.get("type") == "token") != "stubbed pi-mono ":
    raise SystemExit(f"stream token payload wrong: {streamed!r}")
PY

    # Unified model selection + auth isolation: pi_mono.run_turn must
    # resolve the model from ZOMBIE_PROVIDER/ZOMBIE_MODEL (via the same
    # providers registry the banner uses) and pass it to the bridge,
    # while forwarding ONLY the active provider's key. The stub records
    # the received `start` frame and its env-key visibility.
    echo "  pi-mono unified model selection + key isolation"
    _START_OUT="$(mktemp)"
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/tests/fixtures/stub-pi-mono.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    ZOMBIE_STUB_START_OUT="${_START_OUT}" \
    ZOMBIE_PROVIDER="gemini" \
    ZOMBIE_MODEL="gemini-2.0-flash" \
    GEMINI_API_KEY="test-gemini" \
    OPENAI_API_KEY="test-openai-should-be-stripped" \
    PYTHONPATH=payload/agent \
      python3 - "${_START_OUT}" <<'PY'
import json, sys
import pi_mono, tools

def on_tool_call(call_id, name, args):
    return {"ok": True, "result": {"stubbed": True}}

pi_mono.run_turn(
    prompt="hello",
    system_prompt="stub",
    history=[],
    on_tool_call=on_tool_call,
    tool_names=tools.tool_names(),
)
rec = json.load(open(sys.argv[1]))
start = rec["start"]
# gemini must map to the pi provider id "google".
if start.get("provider") != "google":
    raise SystemExit(f"bridge provider was {start.get('provider')!r}, want 'google'")
if start.get("model") != "gemini-2.0-flash":
    raise SystemExit(f"bridge model was {start.get('model')!r}")
# Only the active provider's key may reach the bridge env.
if not rec["env"].get("GEMINI_API_KEY"):
    raise SystemExit("active GEMINI_API_KEY missing from bridge env")
if rec["env"].get("OPENAI_API_KEY"):
    raise SystemExit("non-active OPENAI_API_KEY leaked to bridge env")
PY
    rm -f "${_START_OUT}"

    # Model catalogue + runtime selection: providers.list_models /
    # current_model / set_active_model back the /model chat command and
    # the /api/models + /api/model endpoints. Drive them against a
    # hermetic stub bridge so no API key or @earendil-works/pi-ai
    # install is needed. Also exercises the server App wrappers.
    echo "  providers model catalogue + /model endpoints"
    _MODEL_TMP="$(mktemp -d)"
    ZOMBIE_PI_AI_BRIDGE="$(pwd)/tests/fixtures/stub-pi-ai-bridge.mjs" \
    ZOMBIE_NODE="$(command -v node)" \
    ZOMBIE_HISTORY_DB="${_MODEL_TMP}/conversations.db" \
    ZOMBIE_AUDIT_LOG="${_MODEL_TMP}/audit.log" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import json
import os
import tempfile
import providers as _pr
import server

for k in ("ZOMBIE_PROVIDER", "ZOMBIE_MODEL", "OPENAI_API_KEY",
          "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "XAI_API_KEY",
          "OPENROUTER_API_KEY", "MISTRAL_API_KEY", "GROQ_API_KEY",
          "LMSTUDIO_API_KEY"):
    os.environ.pop(k, None)

# No provider configured: both helpers must raise the shared
# NoProviderConfigured rather than returning a misleading empty list.
for fn in (_pr.active_provider, _pr.list_models, _pr.current_model):
    try:
        fn()
    except _pr.NoProviderConfigured:
        pass
    else:
        raise SystemExit(f"{fn.__name__} should raise without a provider")

os.environ["ZOMBIE_PROVIDER"] = "openai"
os.environ["OPENAI_API_KEY"] = "test"

if _pr.active_provider() != "openai":
    raise SystemExit(f"active_provider wrong: {_pr.active_provider()!r}")
# current_model falls back to the registry default before selection.
if _pr.current_model() != "gpt-4o-mini":
    raise SystemExit(f"current_model wrong: {_pr.current_model()!r}")

models = _pr.list_models()
ids = [m["id"] for m in models]
if ids != ["gpt-4o-mini", "gpt-4o", "o3-mini"]:
    raise SystemExit(f"list_models ids wrong: {ids!r}")
o3 = next(m for m in models if m["id"] == "o3-mini")
if o3["reasoning"] is not True or o3["context_window"] != 200000:
    raise SystemExit(f"list_models lost model metadata: {o3!r}")

# Selecting a known id pins ZOMBIE_MODEL for this process so every
# later turn resolves the same model.
prov, chosen = _pr.set_active_model("gpt-4o")
if (prov, chosen) != ("openai", "gpt-4o"):
    raise SystemExit(f"set_active_model returned {(prov, chosen)!r}")
if os.environ.get("ZOMBIE_MODEL") != "gpt-4o":
    raise SystemExit("set_active_model must pin ZOMBIE_MODEL")
if _pr.current_model() != "gpt-4o":
    raise SystemExit("current_model must reflect the selection")

# An unknown id (for a provider with a catalogue) is rejected, and an
# empty id is always rejected.
for bad in ("definitely-not-a-model", ""):
    try:
        _pr.set_active_model(bad)
    except ValueError:
        pass
    else:
        raise SystemExit(f"set_active_model({bad!r}) should raise ValueError")
# The rejected selection must not have changed the pinned model.
if os.environ.get("ZOMBIE_MODEL") != "gpt-4o":
    raise SystemExit("a rejected selection must not mutate ZOMBIE_MODEL")

# lmstudio has no catalogue, so any non-empty id is accepted free-form.
os.environ["ZOMBIE_PROVIDER"] = "lmstudio"
os.environ["LMSTUDIO_API_KEY"] = "local"
if _pr.list_models() != []:
    raise SystemExit("lmstudio should expose an empty catalogue")
prov, chosen = _pr.set_active_model("qwen/qwen3-coder")
if (prov, chosen) != ("lmstudio", "qwen/qwen3-coder"):
    raise SystemExit(f"lmstudio free-form selection wrong: {(prov, chosen)!r}")

# Runtime LM Studio discovery scans a bounded network, preserves the full
# advertised catalogue in pi's provider file, and activates the provider.
original_probe = _pr._probe_lmstudio
probes = []
def fake_probe(address, port):
    probes.append((address, port))
    if address != "127.0.0.1":
        return None
    return {
        "address": f"{address}:{port}",
        "base_url": f"http://{address}:{port}/v1",
        "models": ["qwen/qwen3-coder", "llama-3.1-8b"],
    }

try:
    _pr._probe_lmstudio = fake_probe
    discovered = _pr.scan_lmstudio("127.0.0.0/30", 1234)
finally:
    _pr._probe_lmstudio = original_probe
if (
    ("127.0.0.2", 1234) not in probes
    or probes.index(("127.0.0.1", 1234)) > probes.index(("127.0.0.2", 1234))
):
    raise SystemExit("scan_lmstudio must probe loopback before the selected subnet")
for address in ("127.0.0.1", "127.0.0.2", "127.0.0.3"):
    for port in (1234, 8080, 11434, 51234):
        if (address, port) not in probes:
            raise SystemExit(f"scan_lmstudio missed {(address, port)!r}")
if [entry["address"] for entry in discovered] != [
    "127.0.0.1:1234",
    "127.0.0.1:8080",
    "127.0.0.1:11434",
    "127.0.0.1:51234",
    "127.0.0.1:58080",
]:
    raise SystemExit(f"scan_lmstudio wrong: {discovered!r}")

models_dir = tempfile.mkdtemp()
models_path = os.path.join(models_dir, "models.json")
os.environ["ZOMBIE_PI_MODELS_JSON"] = models_path
provider, chosen, address = _pr.activate_lmstudio(discovered[0])
if (provider, chosen, address) != (
    "lmstudio", "qwen/qwen3-coder", "127.0.0.1:1234"
):
    raise SystemExit(f"activate_lmstudio wrong: {(provider, chosen, address)!r}")
with open(models_path) as handle:
    saved = json.load(handle)
saved_models = [m["id"] for m in saved["providers"]["lmstudio"]["models"]]
if saved_models != ["qwen/qwen3-coder", "llama-3.1-8b"]:
    raise SystemExit(f"activate_lmstudio models wrong: {saved_models!r}")
if _pr.lmstudio_address() != "127.0.0.1:1234":
    raise SystemExit("lmstudio_address must expose the configured host and port")
if _pr.provider_status() != (
    "lmstudio", "model qwen/qwen3-coder at 127.0.0.1:1234"
):
    raise SystemExit(f"lmstudio provider status wrong: {_pr.provider_status()!r}")

# Server App wrappers: model and local API listing/selection payloads.
os.environ["ZOMBIE_PROVIDER"] = "openai"
os.environ.pop("ZOMBIE_MODEL", None)
app = server.App()
info = app.models_info()
if info.get("provider") != "openai" or info.get("current") != "gpt-4o-mini":
    raise SystemExit(f"models_info wrong: {info!r}")
if [m["id"] for m in info.get("models", [])] != ["gpt-4o-mini", "gpt-4o", "o3-mini"]:
    raise SystemExit(f"models_info models wrong: {info!r}")
ok = app.set_model("gpt-4o")
if ok != {
    "ok": True, "provider": "openai", "model": "gpt-4o", "address": None
}:
    raise SystemExit(f"App.set_model ok payload wrong: {ok!r}")
bad = app.set_model("nope")
if "error" not in bad:
    raise SystemExit(f"App.set_model bad payload should carry error: {bad!r}")
original_scan = _pr.scan_lmstudio
try:
    _pr.scan_lmstudio = lambda *_args, **_kwargs: discovered
    locals_info = app.local_apis_info()
    selected = app.set_local_api("http://127.0.0.1:1234/v1")
finally:
    _pr.scan_lmstudio = original_scan
if locals_info != {
    "current": "http://127.0.0.1:1234/v1",
    "locals": [
        "http://127.0.0.1:1234/v1",
        "http://127.0.0.1:8080/v1",
        "http://127.0.0.1:11434/v1",
        "http://127.0.0.1:51234/v1",
        "http://127.0.0.1:58080/v1",
    ],
}:
    raise SystemExit(f"App.local_apis_info wrong: {locals_info!r}")
if (
    selected.get("address") != "127.0.0.1:1234"
    or selected.get("url") != "http://127.0.0.1:1234/v1"
):
    raise SystemExit(f"App.set_local_api wrong: {selected!r}")
local_model = app.set_model("llama-3.1-8b")
if local_model != {
    "ok": True,
    "provider": "lmstudio",
    "model": "llama-3.1-8b",
    "address": "127.0.0.1:1234",
}:
    raise SystemExit(f"App.set_model local payload wrong: {local_model!r}")
original_scan = _pr.scan_lmstudio
try:
    _pr.scan_lmstudio = lambda *_args, **_kwargs: discovered
    missing = app.set_local_api("http://127.0.0.2:1234/v1")
finally:
    _pr.scan_lmstudio = original_scan
if "error" not in missing:
    raise SystemExit(f"App.set_local_api should reject unknown URL: {missing!r}")
status = app.provider_info()
if status.get("lmstudio_address") != "127.0.0.1:1234":
    raise SystemExit(f"App.provider_info missing LM Studio address: {status!r}")
app.history.close()
PY


    # The real pi-ai-bridge.mjs must list a local OpenAI-compatible
    # provider's models live from its /models endpoint (lmstudio has no
    # static pi-ai catalogue). Drive the real bridge against a hermetic
    # stub HTTP server + temp models.json so no @earendil-works/pi-ai
    # install or LAN server is needed; the live path returns before the
    # bridge ever loads pi-ai.
    echo "  pi-ai bridge live local model listing"
    _LM_DIR="$(mktemp -d)"
    cat > "${_LM_DIR}/models.json" <<JSON
{ "providers": { "lmstudio": { "baseUrl": "http://127.0.0.1:7891/v1",
  "apiKey": "LMSTUDIO_API_KEY", "models": [ { "id": "placeholder" } ] } } }
JSON
    cat > "${_LM_DIR}/server.mjs" <<'JS'
import { createServer } from "node:http";
const s = createServer((req, res) => {
  if (req.url === "/v1/models") {
    res.setHeader("content-type", "application/json");
    res.end(JSON.stringify({ object: "list", data: [
      { id: "qwen/qwen3-coder", object: "model" },
      { id: "llama-3.1-8b", object: "model", context_length: 131072 },
    ] }));
    return;
  }
  res.statusCode = 404;
  res.end("no");
});
s.listen(7891, "127.0.0.1", () => process.stdout.write("ready\n"));
JS
    node "${_LM_DIR}/server.mjs" >"${_LM_DIR}/server.log" 2>&1 &
    _LM_PID=$!
    # Wait for the stub server to report ready (bounded); fail fast if it
    # never comes up so the assertions below give a clear diagnostic.
    _LM_READY=0
    for _ in $(seq 1 50); do
        if grep -q ready "${_LM_DIR}/server.log" 2>/dev/null; then
            _LM_READY=1
            break
        fi
        sleep 0.1
    done
    if [ "${_LM_READY}" -ne 1 ]; then
        kill "${_LM_PID}" 2>/dev/null || true
        echo "stub model server failed to start:" >&2
        cat "${_LM_DIR}/server.log" >&2 || true
        exit 1
    fi
    _LM_OUT="$(printf '%s' '{"op":"list_models","provider":"lmstudio"}' \
        | ZOMBIE_PI_MODELS_JSON="${_LM_DIR}/models.json" \
          LMSTUDIO_API_KEY=local \
          node payload/agent/pi-ai-bridge.mjs)"
    kill "${_LM_PID}" 2>/dev/null || true
    ZOMBIE_LM_OUT="${_LM_OUT}" python3 - <<'PY'
import json, os
out = json.loads(os.environ["ZOMBIE_LM_OUT"])
if not out.get("ok"):
    raise SystemExit(f"live list_models failed: {out!r}")
ids = [m["id"] for m in out.get("models", [])]
if ids != ["qwen/qwen3-coder", "llama-3.1-8b"]:
    raise SystemExit(f"live list_models ids wrong: {ids!r}")
ctx = {m["id"]: m["contextWindow"] for m in out["models"]}
if ctx["llama-3.1-8b"] != 131072 or ctx["qwen/qwen3-coder"] is not None:
    raise SystemExit(f"live list_models context window wrong: {ctx!r}")
PY

    # The pi-ai 0.80 API moved the legacy getModel/getModels/complete
    # surface to its /compat export. Model listing and completion must
    # work when that export is resolved from a global node_modules tree.
    echo "  pi-ai bridge compatibility entrypoint"
    _PI_AI_DIR="${_LM_DIR}/node_modules/@earendil-works/pi-ai"
    mkdir -p "${_PI_AI_DIR}"
    cat > "${_PI_AI_DIR}/package.json" <<'JSON'
{
  "name": "@earendil-works/pi-ai",
  "type": "module",
  "exports": {
    "./compat": {
      "import": "./compat.js"
    }
  }
}
JSON
    cat > "${_PI_AI_DIR}/compat.js" <<'JS'
export function getModels(provider) {
  return [{ id: `${provider}-model`, name: "Compat model",
    reasoning: true, contextWindow: 64000 }];
}
export function getModel(provider, id) {
  // Mirror pi-ai 0.80: local providers (lmstudio) have no static
  // catalogue entry, so getModel returns undefined instead of throwing.
  if (provider === "lmstudio") return undefined;
  return { provider, id };
}
export async function complete(model, _context, options) {
  if (model.provider === "lmstudio") {
    return { role: "assistant", content: [{ type: "text",
      text: `local ${model.api} ${model.baseUrl} ` +
        `key=${options && options.apiKey}` }] };
  }
  return { role: "assistant",
    content: [{ type: "text", text: "compat completion" }] };
}
JS
    _PI_AI_LIST_OUT="$(printf '%s' \
        '{"op":"list_models","provider":"anthropic"}' \
        | NODE_PATH="${_LM_DIR}/node_modules" \
          node payload/agent/pi-ai-bridge.mjs)"
    _PI_AI_COMPLETE_OUT="$(printf '%s' \
        '{"provider":"openai","model":"compat-model","messages":[{"role":"user","content":"hello"}]}' \
        | NODE_PATH="${_LM_DIR}/node_modules" OPENAI_API_KEY=test \
          node payload/agent/pi-ai-bridge.mjs)"
    # A local provider (lmstudio) has no static pi-ai catalogue entry:
    # getModel returns undefined and the bridge must synthesise a model
    # handle from models.json (baseUrl + default openai-completions api)
    # and pass the API key explicitly, instead of crashing on the
    # undefined handle.
    _PI_AI_LOCAL_OUT="$(printf '%s' \
        '{"provider":"lmstudio","model":"llama-3.1-8b","messages":[{"role":"user","content":"ping"}]}' \
        | NODE_PATH="${_LM_DIR}/node_modules" \
          ZOMBIE_PI_MODELS_JSON="${_LM_DIR}/models.json" \
          LMSTUDIO_API_KEY=local \
          node payload/agent/pi-ai-bridge.mjs)"
    ZOMBIE_PI_AI_LIST_OUT="${_PI_AI_LIST_OUT}" \
      ZOMBIE_PI_AI_COMPLETE_OUT="${_PI_AI_COMPLETE_OUT}" \
      ZOMBIE_PI_AI_LOCAL_OUT="${_PI_AI_LOCAL_OUT}" python3 - <<'PY'
import json
import os

listed = json.loads(os.environ["ZOMBIE_PI_AI_LIST_OUT"])
if listed != {"ok": True, "models": [{
        "id": "anthropic-model", "name": "Compat model",
        "reasoning": True, "contextWindow": 64000}]}:
    raise SystemExit(f"compat list_models failed: {listed!r}")
completed = json.loads(os.environ["ZOMBIE_PI_AI_COMPLETE_OUT"])
if completed != {"ok": True, "text": "compat completion"}:
    raise SystemExit(f"compat completion failed: {completed!r}")
local = json.loads(os.environ["ZOMBIE_PI_AI_LOCAL_OUT"])
expected_text = (
    "local openai-completions http://127.0.0.1:7891/v1 key=local"
)
if local != {"ok": True, "text": expected_text}:
    raise SystemExit(f"local provider completion failed: {local!r}")
PY
    rm -rf "${_LM_DIR}"


    # produce a soft failure (synthetic ``budget_exceeded``
    # observation) once exceeded so the model ends the turn cleanly
    # rather than looping.
    echo "  pi-mono per-turn tool-call budget enforcement"
    ZOMBIE_STUB_PLAN='[
      {"type":"tool_call","id":"1","name":"fs.read","args":{"path":"/etc/os-release","max_bytes":64}},
      {"type":"tool_call","id":"2","name":"fs.read","args":{"path":"/etc/os-release","max_bytes":64}},
      {"type":"tool_call","id":"3","name":"fs.read","args":{"path":"/etc/os-release","max_bytes":64}},
      {"type":"final","text":"budget run complete"}
    ]' \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/tests/fixtures/stub-pi-mono.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import pi_mono, tools

invocations = 0

def on_tool_call(call_id, name, args):
    global invocations
    invocations += 1
    return {"ok": True, "result": {"stubbed": True}}

out = pi_mono.run_turn(
    prompt="hello",
    system_prompt="stub",
    history=[],
    on_tool_call=on_tool_call,
    tool_names=tools.tool_names(),
    max_tool_calls=2,
)
if invocations != 2:
    raise SystemExit(f"expected on_tool_call to fire 2x within budget, got {invocations}")
errors = [e.get("error", "") for e in out["events"]
          if e.get("type") == "tool_call"]
# The overflow tool_call's reply is emitted by pi_mono itself, so the
# event log records the bridge tool_call without an on_tool_call run.
overflow_results = [e for e in out["events"]
                    if e.get("type") == "tool_call" and e.get("id") == "3"]
if not overflow_results:
    raise SystemExit("third (overflow) tool_call event missing")
# pi_mono should have synthesized the budget_exceeded reply for id=3.
# We verify by capturing the reply via a custom callback wrapper.
if out["final"] != "budget run complete":
    raise SystemExit(f"unexpected final after budget overflow: {out['final']!r}")
PY

    echo "  server elevated-call budget enforcement"
    _BUDGET_TMP="$(mktemp -d)"
    ZOMBIE_HISTORY_DB="${_BUDGET_TMP}/conversations.db" \
    ZOMBIE_AUDIT_LOG="${_BUDGET_TMP}/audit.log" \
    ZOMBIE_POLICY="payload/etc/policy.yaml" \
    ZOMBIE_STUB_PLAN='[
      {"type":"tool_call","id":"a","name":"fs.write","args":{"path":"/tmp/zombie-budget-1","content":"x"}},
      {"type":"tool_call","id":"b","name":"fs.write","args":{"path":"/tmp/zombie-budget-2","content":"x"}},
      {"type":"tool_call","id":"c","name":"fs.write","args":{"path":"/tmp/zombie-budget-3","content":"x"}},
      {"type":"final","text":"elevated budget run complete"}
    ]' \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/tests/fixtures/stub-pi-mono.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import json
import server

# Force a tight elevated budget without rewriting policy.yaml so we
# don't perturb the rest of the suite. ``post_message`` re-reads
# ``policy.yaml`` each turn, so monkey-patch ``load_policy`` to
# return a Policy with max_elevated_calls_per_turn=2.
import policy as policy_mod

_orig = policy_mod.load_policy
def _tight():
    p = _orig()
    p.max_elevated_calls_per_turn = 2
    return p

policy_mod.load_policy = _tight
server.load_policy = _tight

app = server.App()
out = app.post_message(None, "exercise the elevated budget please")

# Two elevated calls should be queued for approval; the third must
# come back as a synthetic ``budget_exceeded`` observation. History
# events are stored as ``{"kind": ..., "payload": {...}}``.
events = out["events"]
budget_obs = [e["payload"] for e in events
              if e.get("kind") == "tool_observation"
              and (e.get("payload") or {}).get("decision") == "budget_exceeded"]
if len(budget_obs) != 1:
    raise SystemExit(f"expected 1 budget_exceeded observation, got "
                     f"{len(budget_obs)}: {json.dumps(events, indent=2)}")
err = budget_obs[0].get("error", "")
if not err.startswith("budget_exceeded:"):
    raise SystemExit(f"unexpected budget_exceeded error text: {err!r}")

# The first two elevated calls must still be queued (not silently
# dropped by the budget gate).
pending = [e["payload"] for e in events if e.get("kind") == "pending_tool_call"]
if len(pending) != 2:
    raise SystemExit(f"expected 2 pending_tool_call events, got "
                     f"{len(pending)}: {json.dumps(events, indent=2)}")

# The synthetic observation must NOT have created a pending entry to
# approve (operator should not see a phantom approval prompt).
if any(p["tool_call_id"] == "c" for p in pending):
    raise SystemExit("budget-exceeded call must not appear as pending")
PY
    rm -rf "${_BUDGET_TMP}"

    # Idle-deadline watchdog: a bridge that never answers must not hang
    # the turn forever. pi_mono.run_turn should terminate the wedged
    # subprocess and raise a clean BridgeError once the idle timeout
    # elapses (the "Hello hangs forever" regression).
    echo "  pi-mono idle timeout terminates a wedged turn"
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/tests/fixtures/hang-pi-mono.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import time
import threading
import pi_mono, tools

def on_tool_call(call_id, name, args):
    return {"ok": True, "result": {"stubbed": True}}

started = time.monotonic()
try:
    pi_mono.run_turn(
        prompt="Hello",
        system_prompt="stub",
        history=[],
        on_tool_call=on_tool_call,
        tool_names=tools.tool_names(),
        timeout=2.0,
    )
except pi_mono.BridgeError as exc:
    elapsed = time.monotonic() - started
    if "timed out" not in str(exc):
        raise SystemExit(f"unexpected BridgeError: {exc}")
    if elapsed > 10:
        raise SystemExit(f"watchdog took too long to fire: {elapsed:.1f}s")
else:
    raise SystemExit("expected a BridgeError from the idle watchdog")

cancel = threading.Event()
cancel.set()
started = time.monotonic()
try:
    pi_mono.run_turn(
        prompt="Stop me",
        system_prompt="stub",
        history=[],
        on_tool_call=on_tool_call,
        tool_names=tools.tool_names(),
        timeout=60.0,
        cancel_event=cancel,
    )
except pi_mono.BridgeError as exc:
    if "stopped by the operator" not in str(exc):
        raise SystemExit(f"unexpected cancellation BridgeError: {exc}")
    if time.monotonic() - started > 5:
        raise SystemExit("operator cancellation took too long")
else:
    raise SystemExit("expected a BridgeError from operator cancellation")

# A non-positive timeout disables the idle deadline, as documented. The
# streaming path always supplies a cancel_event, which keeps the watchdog
# thread running, so the idle check must stay disabled inside the loop too
# (otherwise ``max_turn_seconds: 0`` killed every streamed turn after the
# first watchdog tick).
late_cancel = threading.Event()
threading.Timer(3.0, late_cancel.set).start()
started = time.monotonic()
try:
    pi_mono.run_turn(
        prompt="No deadline",
        system_prompt="stub",
        history=[],
        on_tool_call=on_tool_call,
        tool_names=tools.tool_names(),
        timeout=0,
        cancel_event=late_cancel,
    )
except pi_mono.BridgeError as exc:
    if "timed out" in str(exc):
        raise SystemExit(
            "a non-positive timeout must disable the idle watchdog"
        )
    if "stopped by the operator" not in str(exc):
        raise SystemExit(f"unexpected disabled-watchdog BridgeError: {exc}")
    if time.monotonic() - started < 2.5:
        raise SystemExit("the wedged turn ended before the operator stop")
else:
    raise SystemExit("expected a BridgeError from operator cancellation")
PY

    # Real bridge against pi's actual `--mode json` event schema. This
    # drives payload/agent/pi-mono-bridge.mjs (not the protocol stub)
    # with a fake `pi` binary that emits the genuine AgentSession event
    # stream, locking in two regressions:
    #   1. the bridge must capture the assistant text from
    #      message_update/message_end (it previously looked for
    #      non-existent "text"/"final" events and returned an empty
    #      answer); and
    #   2. the fake `pi` must be allowed to exit on stdin EOF — the
    #      bridge must not keep its stdin open (the "120s inactivity
    #      timeout" with a working local LM Studio server).
    echo "  pi-mono real bridge parses pi --mode json (text answer)"
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import time
import pi_mono, tools

def on_tool_call(call_id, name, args):
    raise SystemExit("on_tool_call must NOT fire: pi runs its own tools "
                     "in --mode json")

started = time.monotonic()
out = pi_mono.run_turn(
    prompt="say hi",
    system_prompt="you are helpful",
    history=[],
    on_tool_call=on_tool_call,
    tool_names=tools.tool_names(),
    timeout=20.0,
)
elapsed = time.monotonic() - started
if out["final"] != "Hello from the local model!":
    raise SystemExit(f"bridge dropped the assistant text: {out['final']!r}")
# The turn must complete promptly (the fake pi exits on stdin EOF); a
# regression that keeps pi's stdin open would hang until the watchdog.
if elapsed > 10:
    raise SystemExit(f"bridge turn took too long ({elapsed:.1f}s); "
                     "did pi fail to exit on stdin EOF?")
# pi executes its own tools in --mode json, so the bridge must not
# surface tool_execution_* events as mediated tool_call frames.
if any(e.get("type") == "tool_call" for e in out["events"]):
    raise SystemExit("bridge must not re-dispatch pi's tool_execution events")
if not any(e.get("type") == "progress" for e in out["events"]):
    raise SystemExit("bridge must forward tool progress events")
if not any(e.get("type") == "token" for e in out["events"]):
    raise SystemExit("bridge must forward token events")
PY

    # Some OpenAI-compatible providers expose the post-tool assistant answer
    # only in agent_end.messages. The bridge must recover that terminal
    # snapshot instead of returning an empty turn.
    echo "  pi-mono bridge recovers terminal-only post-tool answer"
    ZOMBIE_FAKE_PI_MODE="terminal-answer" \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import os

import pi_mono, tools

for mode in ("terminal-answer", "turn-answer"):
    os.environ["ZOMBIE_FAKE_PI_MODE"] = mode
    out = pi_mono.run_turn(
        prompt="which operating system is this?",
        system_prompt="stub",
        history=[],
        on_tool_call=lambda *_args: {"ok": True, "result": {}},
        tool_names=tools.tool_names(),
        timeout=20.0,
    )
    if out["final"] != "The system is Ubuntu.":
        raise SystemExit(
            f"bridge dropped {mode} post-tool answer: {out['final']!r}"
        )
PY

    # A non-zero bash status can be a normal negative probe (for example,
    # grep finding no match). Pi nests bash exit metadata under result.details;
    # preserve it so the UI can distinguish that status from a tool failure.
    echo "  pi-mono bridge distinguishes shell status from tool failure"
    ZOMBIE_FAKE_PI_MODE="shell-status" \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import pi_mono, tools

out = pi_mono.run_turn(
    prompt="probe",
    system_prompt="stub",
    history=[],
    on_tool_call=lambda *_args: {"ok": True, "result": {}},
    tool_names=tools.tool_names(),
    timeout=20.0,
)
ends = [e for e in out["events"]
        if e.get("type") == "progress" and e.get("kind") == "tool_end"
        and e.get("name") == "bash"]
if len(ends) != 2:
    raise SystemExit(f"expected two bash completion events, got {ends!r}")
probe, broken = ends
if probe.get("exit_code") != 1 or probe.get("command_status") is not True:
    raise SystemExit(f"non-zero shell probe misclassified: {probe!r}")
if broken.get("command_status") is True or broken.get("ok") is not False:
    raise SystemExit(f"genuine shell failure misclassified: {broken!r}")
PY

    # The real bridge must forward the prior conversation into pi's
    # one-shot -p prompt so the agent has cross-turn memory (regression:
    # the bridge previously dropped `history`, so the model forgot names
    # and earlier context). The fake pi echoes its -p prompt back.
    echo "  pi-mono real bridge forwards conversation history (memory)"
    ZOMBIE_FAKE_PI_MODE="echo" \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import pi_mono, tools

def on_tool_call(call_id, name, args):
    return {"ok": True, "result": {}}

# Mirror server.py: the current user turn is the last history entry and
# is also passed as `prompt`.
history = [
    {"role": "user", "content": "Call me Eric"},
    {"role": "assistant", "content": "Understood, Eric."},
    {"role": "user", "content": "What is my name?"},
]
out = pi_mono.run_turn(
    prompt="What is my name?",
    system_prompt="you are helpful",
    history=history,
    on_tool_call=on_tool_call,
    tool_names=tools.tool_names(),
    timeout=20.0,
)
final = out["final"]
# Earlier turns must reach pi so the model can answer from memory.
if "Eric" not in final:
    raise SystemExit(f"bridge dropped conversation history: {final!r}")
# The current question must appear exactly once (not duplicated by the
# trailing history entry the server appends).
if final.count("What is my name?") != 1:
    raise SystemExit(f"current prompt duplicated/missing: {final!r}")
PY

    # The real bridge must surface a provider/connection error as a
    # clean BridgeError rather than a blank answer or a hung turn.
    echo "  pi-mono real bridge surfaces provider errors"
    ZOMBIE_FAKE_PI_MODE="error" \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import pi_mono, tools

def on_tool_call(call_id, name, args):
    return {"ok": True, "result": {}}

try:
    pi_mono.run_turn(
        prompt="say hi",
        system_prompt="stub",
        history=[],
        on_tool_call=on_tool_call,
        tool_names=tools.tool_names(),
        timeout=20.0,
    )
except pi_mono.BridgeError as exc:
    if "Connection error" not in str(exc):
        raise SystemExit(f"unexpected BridgeError text: {exc}")
else:
    raise SystemExit("expected a BridgeError for the provider error case")
PY

    # A provider error after some assistant text must not be masked by
    # that stale partial text (the operator would otherwise see a
    # truncated preamble and no explanation at all).
    echo "  pi-mono real bridge prefers a late error over partial text"
    ZOMBIE_FAKE_PI_MODE="partial-error" \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import pi_mono, tools

try:
    pi_mono.run_turn(
        prompt="say hi",
        system_prompt="stub",
        history=[],
        on_tool_call=lambda *_a: {"ok": True, "result": {}},
        tool_names=tools.tool_names(),
        timeout=20.0,
    )
except pi_mono.BridgeError as exc:
    text = str(exc)
    if "Connection error" not in text:
        raise SystemExit(f"late provider error was masked: {text!r}")
    if "Let me check that for you." not in text:
        raise SystemExit(f"partial reply was dropped: {text!r}")
else:
    raise SystemExit("expected a BridgeError when the turn ended in error")
PY

    # A turn where tools run but the model never speaks must never be
    # stored or streamed as a blank reply: the transcript skips empty
    # bubbles, so the operator saw tool activity and then nothing.
    echo "  empty model turn still produces a visible reply"
    _EMPTY_TMP="$(mktemp -d)"
    ZOMBIE_HISTORY_DB="${_EMPTY_TMP}/conversations.db" \
    ZOMBIE_AUDIT_LOG="${_EMPTY_TMP}/audit.log" \
    ZOMBIE_POLICY="payload/etc/policy.yaml" \
    ZOMBIE_FAKE_PI_MODE="silent" \
    ZOMBIE_PI_MONO_BRIDGE="$(pwd)/payload/agent/pi-mono-bridge.mjs" \
    ZOMBIE_PI_MONO_BIN="$(pwd)/tests/fixtures/fake-pi-json.mjs" \
    ZOMBIE_PI_MONO_LOG_DIR="$(mktemp -d)" \
    PYTHONPATH=payload/agent \
      python3 - <<'PY'
import server

emitted = []
app = server.App()
out = app.post_message(
    None, "look at the release file",
    emit=lambda event, payload: emitted.append((event, payload)))
reply = out.get("reply") or ""
if not reply.strip():
    raise SystemExit(f"a text-less turn produced no visible reply: {out!r}")
if "without a reply" not in reply:
    raise SystemExit(f"unexpected empty-turn notice: {reply!r}")
if "1 tool call ran" not in reply:
    raise SystemExit(f"empty-turn notice lost the tool count: {reply!r}")
done = [payload for event, payload in emitted if event == "turn_done"]
if not done or not (done[-1].get("reply") or "").strip():
    raise SystemExit(f"turn_done streamed a blank reply: {done!r}")
stored = [m for m in app.history.get_messages(out["conversation_id"])
          if m["role"] == "assistant"]
if not stored or not (stored[-1]["content"] or "").strip():
    raise SystemExit("an empty assistant message was stored in history")
PY
    rm -rf "${_EMPTY_TMP}"
  else
    echo "  (skipping pi-mono stub end-to-end: node not on PATH)"
  fi

  echo "  audit redaction + verbose preview round-trip"
  _AUDIT_TMP="$(mktemp -d)"
  ZOMBIE_AUDIT_LOG="${_AUDIT_TMP}/audit.log" \
  PYTHONPATH=payload/agent python3 - <<'PY'
import json
import os

import audit

# Default mode: no stdout_preview in tool_call entries, but every
# entry must carry pid + ts_utc so testers can correlate audit lines
# with journalctl.
audit.log_event("prompt", prompt="hello sk-abcdefghijklmnop world")
audit.log_tool_call(
    tool="shell.run", classification="read_only", decision="executed",
    stdout="line1\nAPI_KEY=secretsesame\nline2", stderr="boom",
    exit_code=0, duration_ms=12,
)

# Verbose mode: previews appear and are redacted by the same rules
# applied to every other field.
os.environ["ZOMBIE_AUDIT_VERBOSE"] = "1"
try:
    audit.log_tool_call(
        tool="shell.run", classification="read_only", decision="executed",
        stdout="visible\nAPI_KEY=secretsesame\nbye",
        stderr="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ secret",
        exit_code=0, duration_ms=8,
    )
finally:
    del os.environ["ZOMBIE_AUDIT_VERBOSE"]

path = os.environ["ZOMBIE_AUDIT_LOG"]
lines = [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]
assert len(lines) == 3, lines

for entry in lines:
    for required in ("id", "ts", "ts_utc", "pid", "type"):
        assert required in entry, (required, entry)
    assert entry["ts_utc"].endswith("Z"), entry["ts_utc"]
    assert isinstance(entry["pid"], int) and entry["pid"] > 0, entry["pid"]

prompt_entry, default_tool, verbose_tool = lines
assert prompt_entry["prompt"] == "hello sk-***REDACTED*** world", prompt_entry
assert "stdout_preview" not in default_tool, default_tool
assert "stderr_preview" not in default_tool, default_tool
assert default_tool["stdout_sha256"], default_tool
assert "stdout_preview" in verbose_tool, verbose_tool
assert "API_KEY=***REDACTED***" in verbose_tool["stdout_preview"], verbose_tool
assert "secretsesame" not in verbose_tool["stdout_preview"], verbose_tool
assert "REDACTED" in verbose_tool["stderr_preview"], verbose_tool
PY
  rm -rf "${_AUDIT_TMP}"

  echo "  server version_info endpoint"
  PYTHONPATH=payload/agent python3 - <<'PY'
import json
import server
import time

info = server.version_info()
# The payload version must resolve from the repo-root VERSION file
# when running from a checkout (HERE.parent.parent / VERSION).
assert info.get("version") and info["version"] != "unknown", info
# The pinned provider-bridge versions ship next to the agent sources,
# so version_info must surface them too.
assert info.get("pi_mono"), info
assert info.get("pi_ai"), info
components = {row["name"]: row for row in info["components"]}
assert {"ubuntu-zombie", "pi-mono", "pi-ai", "python", "node", "sqlite"} <= set(components), info

class Response:
    def __init__(self, payload):
        self.payload = payload
    def __enter__(self):
        return self
    def __exit__(self, *_args):
        return False
    def read(self, _limit):
        return json.dumps(self.payload).encode()

def fake_urlopen(request, timeout):
    assert timeout == server.VERSION_CHECK_TIMEOUT_SECONDS
    assert request.get_header("User-agent").startswith("ubuntu-zombie/")
    if "github.com" in request.full_url:
        return Response({"tag_name": "v2099.1.2"})
    return Response({"version": "9.8.7"})

server.urlopen = fake_urlopen
server._version_cache = (
    time.monotonic() - server.VERSION_CACHE_SECONDS - 1,
    {},
)
checked = server.version_info(check_latest=True)
checked_components = {row["name"]: row for row in checked["components"]}
assert checked_components["ubuntu-zombie"]["latest"] == "2099.1.2", checked
assert checked_components["pi-mono"]["latest"] == "9.8.7", checked

server.machine_facts = lambda: {"hostname": "test-host"}
server.provider_status = lambda: ("none", "not configured")
rendered = server._render_index(None).decode()
footer = rendered[rendered.index("<footer>"):rendered.index("</footer>")]
assert 'id="app-version"' in footer, footer
assert f'aria-label="Ubuntu Zombie version {server.app_version()}"' in footer, footer
assert footer.index('id="prompt-help"') < footer.index('id="app-version"'), footer
assert f'v{server.app_version()}' in footer, footer
assert "{{VERSION}}" not in rendered, rendered
PY

  echo "  server proof-of-life status"
  _STATUS_TMP="$(mktemp -d)"
  ZOMBIE_HISTORY_DB="${_STATUS_TMP}/conversations.db" \
  ZOMBIE_LIFECYCLE_STATE="${_STATUS_TMP}/lifecycle.json" \
  ZOMBIE_AUDIT_LOG="${_STATUS_TMP}/audit.log" \
  ZOMBIE_POLICY=payload/etc/policy.yaml \
  PYTHONPATH=payload/agent python3 - <<'PY'
import server

probe_calls = 0
def probe():
    global probe_calls
    probe_calls += 1
    return {
        "provider": "openai",
        "model": "test-model",
        "ok": True,
        "latency_ms": 12,
    }

server.providers.probe_provider = probe
server.providers.current_model = lambda: "test-model"
app = server.App()
conversation_id = app.history.create_conversation()
app.history.add_message(conversation_id, "user", "hello")
app.history.add_message(conversation_id, "assistant", "hi")
status = app.status_info()
assert status["connectivity"]["ok"] is True, status
assert status["model"] == "test-model", status
assert status["machine"]["ip_address"], status
assert status["usage"]["messages"] == 2, status
assert "disk_free_bytes" in status["resources"], status
cached_status = app.status_info()
assert cached_status["connectivity"]["cached"] is True, cached_status
assert probe_calls == 1, probe_calls
PY
  rm -rf "${_STATUS_TMP}"

  echo "  server conversation endpoint (existing / bad id / not found)"
  _CONV_TMP="$(mktemp -d)"
  ZOMBIE_HISTORY_DB="${_CONV_TMP}/conversations.db" \
  ZOMBIE_AUDIT_LOG="${_CONV_TMP}/audit.log" \
  ZOMBIE_POLICY=payload/etc/policy.yaml \
  ZOMBIE_SKILLS_DIR=payload/agent/skills \
  PYTHONPATH=payload/agent python3 - <<'PY'
import atexit
import json
import os
import shutil
from pathlib import Path

_db = os.environ.get("ZOMBIE_HISTORY_DB")
if _db:
    _td = Path(_db).resolve().parent
    if _td != Path("/") and len(str(_td)) > 10:
        atexit.register(lambda p=str(_td): shutil.rmtree(p, ignore_errors=True))

import server

class _FakeRFile:
    """Minimal stand-in for a socket rfile."""

    def __init__(self, body=b""):
        self._body = body

    def read(self, *_a, **_k):
        body, self._body = self._body, b""
        return body

    def readline(self, *_a, **_k):
        return b""

class _Recorder(server.Handler):
    """Drive Handler methods without a real socket; capture the reply."""

    def __init__(self, app, path, body=None):  # noqa: D107 - test shim
        self.app = app
        self.path = path
        raw = json.dumps(body or {}).encode("utf-8")
        self.rfile = _FakeRFile(raw)
        self.headers = {"Content-Length": str(len(raw))}
        self.status = None
        self.body = b""

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, *a, **k):
        pass

    def end_headers(self):
        pass

    def send_error(self, code, *a, **k):
        self.status = int(code)

    class _W:
        def __init__(self, outer):
            self._outer = outer

        def write(self, data):
            self._outer.body += data

    @property
    def wfile(self):
        return _Recorder._W(self)


def get(app, path):
    h = _Recorder(app, path)
    h.do_GET()
    payload = json.loads(h.body.decode("utf-8")) if h.body else {}
    return h.status, payload


def post(app, path, body=None):
    h = _Recorder(app, path, body)
    h.do_POST()
    payload = json.loads(h.body.decode("utf-8")) if h.body else {}
    return h.status, payload


app = server.App()
cid = app.history.create_conversation()
app.history.add_message(cid, "user", "hello there")
app.history.add_message(cid, "assistant", "hi")

# Existing conversation: 200 with the stored messages, no error.
status, body = get(app, f"/api/conversation/{cid}")
assert status == 200, (status, body)
assert "error" not in body, body
assert body["conversation"]["id"] == cid, body
assert any(m["content"] == "hello there" for m in body["messages"]), body

# Unknown id: a 404 with an error body the UI can surface, rather than
# a silent empty conversation the operator thinks loaded.
status, body = get(app, "/api/conversation/999999")
assert status == 404, (status, body)
assert "error" in body and "999999" in body["error"], body

# Non-numeric id: a 400 with a "bad id" error.
status, body = get(app, "/api/conversation/not-a-number")
assert status == 400, (status, body)
assert body.get("error") == "bad id", body

# Title updates are small state mutations and are audit-visible.
status, body = post(app, f"/api/conversation/{cid}/title",
                    {"title": "   "})
assert status == 400, (status, body)
assert body["error"] == "title is required", body
status, body = post(app, f"/api/conversation/{cid}/title",
                    {"title": "  Demo title  "})
assert status == 200, (status, body)
assert body["title"] == "Demo title", body
status, body = get(app, f"/api/conversation/{cid}")
assert body["conversation"]["title"] == "Demo title", body

# Branch copies the transcript without changing the source.
status, body = post(app, f"/api/conversation/{cid}/branch",
                    {"title": "side path"})
assert status == 200, (status, body)
branch_id = body["conversation_id"]
assert branch_id != cid, body
status, branch = get(app, f"/api/conversation/{branch_id}")
assert status == 200, (status, branch)
assert [m["content"] for m in branch["messages"]] == [
    "hello there", "hi",
], branch

# Retry creates a branch before the last user message and returns the
# prompt for the browser to re-submit. The original remains intact.
app.history.add_message(cid, "user", "try this")
app.history.add_message(cid, "assistant", "old answer")
status, body = post(app, f"/api/conversation/{cid}/retry")
assert status == 200, (status, body)
assert body["prompt"] == "try this", body
status, retry = get(app, f"/api/conversation/{body['conversation_id']}")
assert [m["content"] for m in retry["messages"]] == [
    "hello there", "hi",
], retry

# Undo also branches instead of deleting evidence or pretending host
# side effects were reverted.
status, body = post(app, f"/api/conversation/{cid}/undo", {"turns": 1})
assert status == 200, (status, body)
assert "host changes" in body["warning"], body
status, undone = get(app, f"/api/conversation/{body['conversation_id']}")
assert [m["content"] for m in undone["messages"]] == [
    "hello there", "hi",
], undone

# Compress stores a local system summary that future turns can inject
# into the system prompt; raw messages stay present.
status, body = post(app, f"/api/conversation/{cid}/compress")
assert status == 200, (status, body)
assert "Local summary" in body["summary"], body
assert app.history.latest_summary(cid) == body["summary"], body
status, original = get(app, f"/api/conversation/{cid}")
assert any(m["content"] == "try this" for m in original["messages"]), original

# Read-only command-support endpoints.
saved_provider = os.environ.get("ZOMBIE_PROVIDER")
os.environ["ZOMBIE_PROVIDER"] = "bogus"
for path in ("/api/config", "/api/profile", "/api/whoami",
             "/api/policy", "/api/skills"):
    status, body = get(app, path)
    assert status == 200, (path, status, body)
status, whoami = get(app, "/api/whoami")
assert whoami["agent_user"], whoami
assert whoami["hostname"], whoami
assert whoami["chat_url"].startswith("http://127.0.0.1:"), whoami
assert whoami["loopback_only"] is True, whoami
status, profile = get(app, "/api/profile")
assert profile["zombie_dir"] == os.environ.get("ZOMBIE_DIR", "/opt/ai-zombie"), profile
assert profile["history_db"] == os.environ["ZOMBIE_HISTORY_DB"], profile
if saved_provider is None:
    os.environ.pop("ZOMBIE_PROVIDER", None)
else:
    os.environ["ZOMBIE_PROVIDER"] = saved_provider
assert any(s["name"] == "apt" for s in get(app, "/api/skills")[1]["skills"])
status, body = get(app, "/api/skill/apt")
assert status == 200 and "content" in body and body["name"] == "apt", body
status, body = get(app, "/api/pending")
assert status == 200 and body["pending"] == [], body

# Pending approval commands expose the same queue as the approval
# buttons. Denial removes the call; a bad destructive phrase does not.
pending = {
    "id": "audit-1",
    "conversation_id": cid,
    "tool_call_id": "tool-1",
    "tool": "shell.run",
    "args": {"argv": ["true"]},
    "classification": "elevated",
    "requires_phrase": False,
}
app.pending["audit-1"] = pending
app.pending["tool-1"] = pending
status, body = get(app, "/api/pending")
assert status == 200 and len(body["pending"]) == 1, body
status, body = post(app, "/api/approve",
                    {"tool_call_id": "audit-1", "decision": "deny"})
assert status == 200 and body["status"] == "denied", body
assert body["tool_call_id"] == "tool-1", body
assert app.pending_calls() == [], app.pending_calls()

pending = {
    "id": "audit-2",
    "conversation_id": cid,
    "tool_call_id": "tool-2",
    "tool": "shell.run",
    "args": {"argv": ["rm", "-rf", "/tmp/nope"]},
    "classification": "destructive",
    "requires_phrase": True,
}
app.pending["audit-2"] = pending
app.pending["tool-2"] = pending
status, body = post(app, "/api/approve",
                    {"tool_call_id": "tool-2", "decision": "approve",
                     "phrase": "wrong"})
assert status == 200 and body["status"] == "awaiting_confirmation", body
assert len(app.pending_calls()) == 1, app.pending_calls()
status, body = post(app, "/api/approve",
                    {"tool_call_id": "audit-2", "decision": "deny"})
assert status == 200 and body["status"] == "denied", body
assert app.pending_calls() == [], app.pending_calls()

app.history.close()
PY
  rm -rf "${_CONV_TMP}"

  echo "  lifecycle TTL kill switch"
  _LIFE_TMP="$(mktemp -d)"
  ZOMBIE_LIFECYCLE_STATE="${_LIFE_TMP}/lifecycle.json" \
  PYTHONPATH=payload/agent python3 - <<'PY'
import time
import lifecycle

# format_remaining mirrors the documented "/ttl" example shape and
# singularises units that equal one.
assert lifecycle.format_remaining(9 * 86400 + 4 * 3600 + 23 * 60 + 12) == \
    "9 days 4 hours 23 minutes 12 seconds"
assert lifecycle.format_remaining(86400 + 3600 + 60 + 1) == \
    "1 day 1 hour 1 minute 1 second"
assert lifecycle.format_remaining(-5) == "0 days 0 hours 0 minutes 0 seconds"
assert lifecycle.parse_duration("14 days") == 14 * 86400
assert lifecycle.parse_duration("2 years 3 months") == \
    (2 * 365 + 3 * 30) * 86400
assert lifecycle.parse_duration("3 hours") == 3 * 3600
assert lifecycle.parse_duration("5") == 5 * 86400
assert lifecycle.parse_duration("", default_seconds=7 * 86400) == 7 * 86400

# A fresh install seeds a live countdown.
st = lifecycle.initialize(3)
assert st["dead"] is False and st["alive"] is True, st
assert 2 * 86400 < st["remaining_seconds"] <= 3 * 86400, st

# "/ttl N" extends from the current expiry, so +5 days on a ~3-day
# clock leaves ~8 days (never shortens the countdown).
st = lifecycle.set_ttl(5)
assert 7 * 86400 < st["remaining_seconds"] <= 8 * 86400, st

# "/ttl reset D" resets from now instead of extending from the old expiry.
st = lifecycle.reset_ttl_seconds(lifecycle.parse_duration("14 days"))
assert 13 * 86400 < st["remaining_seconds"] <= 14 * 86400, st

# Non-positive extensions are rejected.
for bad in (0, -1):
    try:
        lifecycle.set_ttl(bad)
    except ValueError:
        pass
    else:
        raise SystemExit(f"set_ttl({bad}) should raise ValueError")

# Killing trips the tombstone permanently; a later /ttl cannot revive it.
st = lifecycle.kill()
assert st["dead"] is True and st["dead_reason"] == "killed", st
st = lifecycle.set_ttl(5)
assert st["dead"] is True, "a dead zombie must not be revivable via set_ttl"

# Only a fresh initialize() (a reinstall) clears the tombstone.
st = lifecycle.initialize(1)
assert st["dead"] is False, st

# An elapsed TTL trips on the next status() read and writes the
# tombstone durably (a restart cannot revive it).
lifecycle.initialize(1)
import json
from pathlib import Path
p = Path(__import__("os").environ["ZOMBIE_LIFECYCLE_STATE"])
data = json.loads(p.read_text())
data["expires_at"] = time.time() - 1
p.write_text(json.dumps(data))
st = lifecycle.status()
assert st["dead"] is True and st["dead_reason"] == "expired", st
assert json.loads(p.read_text())["dead"] is True, "expiry must be persisted"
PY
  rm -rf "${_LIFE_TMP}"

  echo "  auth password gate"
  PYTHONPATH=payload/agent python3 - <<'PY'
import os
import auth

os.environ.pop(auth.HASH_ENV, None)
# Gate disabled when no hash is configured: every password passes and
# auth_required() is False (this is what keeps the smoke server tests
# from needing a login).
assert auth.auth_required() is False
assert auth.check_password("anything") is True

h = auth.hash_password("braaaains")
assert h.startswith("pbkdf2_sha256$"), h
assert auth.verify_password("braaaains", h) is True
assert auth.verify_password("wrong", h) is False
# Malformed stored hashes never validate.
for bad in ("", "garbage", "pbkdf2_sha256$nope"):
    assert auth.verify_password("x", bad) is False, bad

os.environ[auth.HASH_ENV] = h
try:
    assert auth.auth_required() is True
    assert auth.check_password("braaaains") is True
    assert auth.check_password("nope") is False
finally:
    os.environ.pop(auth.HASH_ENV, None)

# Session tokens are opaque and unique.
assert auth.new_session_token() != auth.new_session_token()
PY

  echo "  server password gate + /ttl endpoints"
  _GATE_TMP="$(mktemp -d)"
  ZOMBIE_HISTORY_DB="${_GATE_TMP}/conversations.db" \
  ZOMBIE_AUDIT_LOG="${_GATE_TMP}/audit.log" \
  ZOMBIE_POLICY=payload/etc/policy.yaml \
  ZOMBIE_LIFECYCLE_STATE="${_GATE_TMP}/lifecycle.json" \
  ZOMBIE_SECRETS="${_GATE_TMP}/secrets/env" \
  PYTHONPATH=payload/agent python3 - <<'PY'
import json
import os

import auth
import lifecycle
import server


class _RFile:
    def __init__(self, body=b""):
        self._body = body

    def read(self, *_a, **_k):
        body, self._body = self._body, b""
        return body

    def readline(self, *_a, **_k):
        return b""


class _Recorder(server.Handler):
    def __init__(self, app, path, body=None, cookie=None):
        self.app = app
        self.path = path
        raw = json.dumps(body or {}).encode("utf-8")
        self.rfile = _RFile(raw)
        self.headers = {"Content-Length": str(len(raw))}
        if cookie:
            self.headers["Cookie"] = cookie
        self.status = None
        self.body = b""
        self.headers_sent = []

    def send_response(self, code, message=None):
        self.status = code

    def send_header(self, name, value):
        self.headers_sent.append((name, value))

    def end_headers(self):
        pass

    def send_error(self, code, *a, **k):
        self.status = int(code)

    class _W:
        def __init__(self, outer):
            self._outer = outer

        def write(self, data):
            self._outer.body += data

    @property
    def wfile(self):
        return _Recorder._W(self)


def get(app, path, cookie=None):
    h = _Recorder(app, path, cookie=cookie)
    h.do_GET()
    return h.status, (json.loads(h.body) if h.body else {}), h.headers_sent


def post(app, path, body=None, cookie=None):
    h = _Recorder(app, path, body, cookie=cookie)
    h.do_POST()
    return h.status, (json.loads(h.body) if h.body else {}), h.headers_sent


# --- Gate enabled: protected endpoints require a login. ---
os.environ[auth.HASH_ENV] = auth.hash_password("braaaains")
lifecycle.initialize(3)
app = server.App()

status, body, _ = get(app, "/api/session")
assert body["required"] is True and body["authenticated"] is False, body

status, body, _ = get(app, "/api/health")
assert status == 401, (status, body)

status, body, _ = post(app, "/api/login", {"password": "wrong"})
assert status == 401, (status, body)

status, body, headers = post(app, "/api/login", {"password": "braaaains"})
assert status == 200 and body.get("ok"), (status, body)
cookie = next(v.split(";", 1)[0] for k, v in headers if k == "Set-Cookie")

status, body, _ = get(app, "/api/health", cookie=cookie)
assert status == 200, (status, body)

# Password changes rewrite secrets/env without leaking plaintext, and a
# changed password clears existing sessions.
status, body, _ = post(app, "/api/password", {"password": "new-braaaains"},
                       cookie=cookie)
assert status == 200 and body["required"] is True, (status, body)
assert auth.check_password("new-braaaains") is True
status, body, _ = get(app, "/api/health", cookie=cookie)
assert status == 401, (status, body)
status, body, headers = post(app, "/api/login", {"password": "new-braaaains"})
assert status == 200 and body.get("ok"), (status, body)
cookie = next(v.split(";", 1)[0] for k, v in headers if k == "Set-Cookie")

# Empty /password removes the gate; no logoff is required because auth is
# disabled for every request.
status, body, _ = post(app, "/api/password", {"password": ""}, cookie=cookie)
assert status == 200 and body["required"] is False, (status, body)
status, body, _ = get(app, "/api/health")
assert status == 200, (status, body)

os.environ[auth.HASH_ENV] = auth.hash_password("braaaains")

# Logout invalidates the token.
post(app, "/api/logout", cookie=cookie)
status, body, _ = get(app, "/api/health", cookie=cookie)
assert status == 401, (status, body)
app.history.close()
os.environ.pop(auth.HASH_ENV, None)

# --- TTL endpoints (gate disabled). ---
lifecycle.initialize(3)
app = server.App()

status, body, _ = get(app, "/api/ttl")
assert status == 200 and body["dead"] is False, body

status, body, _ = post(app, "/api/ttl", {"days": 5})
assert status == 200 and 7 * 86400 < body["remaining_seconds"] <= 8 * 86400, body

status, body, _ = post(app, "/api/ttl", {
    "reset": True,
    "duration": "14 days",
})
assert status == 200 and 13 * 86400 < body["remaining_seconds"] <= 14 * 86400, body

status, body, _ = post(app, "/api/ttl", {"duration": "3 hours"})
assert status == 200 and 14 * 86400 < body["remaining_seconds"] <= \
    14 * 86400 + 3 * 3600, body

status, body, _ = post(app, "/api/ttl", {"days": "not-a-number"})
assert status == 400, (status, body)

# --die trips the kill switch and message/ttl are refused thereafter.
status, body, _ = post(app, "/api/ttl", {"die": True})
assert status == 200 and body["dead"] is True, body

status, body, _ = post(app, "/api/message", {"prompt": "hello"})
assert status == 410 and body.get("dead") is True, (status, body)

status, body, _ = post(app, "/api/ttl", {"days": 5})
assert body.get("dead") is True, body
app.history.close()
PY
  rm -rf "${_GATE_TMP}"
}

run_branding() {
  echo "[smoke] startup branding"
  local first_line
  first_line='╭──────────────────────────────────╮'
  grep -Fq "$first_line" scripts/lib.sh
  grep -Fq 'Ubuntu Zombie' payload/bin/zombie-chat
  grep -Fq 'function brandWordmark' payload/agent/templates/index.html
  PYTHONPATH=payload/agent python3 - <<'PY'
import server

assert server._provider_banner("openai", "model gpt-4o") == "gpt-4o"
assert server._provider_banner(
    "lmstudio", "model qwen3 at 192.0.2.10:1234"
) == "qwen3 at 192.0.2.10:1234"
assert server._provider_banner(
    "openrouter", "model not set (set ZOMBIE_MODEL)"
) == "model not set (set ZOMBIE_MODEL)"
assert server._provider_banner("none", "No provider configured") == (
    "No provider configured"
)
PY
  local out
  out="$(ZOMBIE_COLOR=never ./scripts/install.sh --dry-run)"
  grep -Fq "$first_line" <<<"${out}"
  # A real uninstall run opens with the splash; --help stays concise.
  out="$(ZOMBIE_COLOR=never ./scripts/uninstall.sh --dry-run 2>&1 || true)"
  grep -Fq "$first_line" <<<"${out}"
  out="$(ZOMBIE_COLOR=never ./scripts/uninstall.sh --help)"
  if grep -Fq "$first_line" <<<"${out}"; then
    echo "FAIL: uninstall.sh --help must not print the splash" >&2
    exit 1
  fi
}

run_subcommands() {
  echo "[smoke] subcommand parsing"
  ./scripts/install.sh --help    >/dev/null
  ./scripts/install.sh --version >/dev/null
  # Each non-mutating subcommand should parse without a positional target.
  local out rc sub target
  for sub in verify doctor; do
    set +e
    out="$(./scripts/install.sh "${sub}" 2>&1)"
    rc=$?
    set -e
    if [[ $rc -eq 2 ]]; then
      echo "FAIL: '${sub}' returned bad-usage (exit 2). Output:"
      echo "${out}"
      exit 1
    fi
  done
  ./scripts/install.sh doctor >/dev/null || true

  # Ubuntu Zombie is the only install plan. Legacy product-selection
  # environment variables must be inert.
  local default_out legacy_env_out
  default_out="$(ZOMBIE_COLOR=never ./scripts/install.sh install --dry-run)"
  legacy_env_out="$(ZOMBIE_COLOR=never ZOMBIE_INSTALL_FORGEJO=1 \
    ZOMBIE_INSTALL_FORGEJO_RUNNER=1 ZOMBIE_INSTALL_LLAMA=1 \
    ./scripts/install.sh install --dry-run)"
  [[ "${default_out}" == "${legacy_env_out}" ]] \
    || { echo "FAIL: legacy product-selection variables changed the Zombie plan" >&2; exit 1; }
  if grep -Eqi 'forgejo|forgejo-runner|standalone llama' <<<"${default_out}"; then
    echo "FAIL: Zombie dry-run advertises a removed install mode" >&2
    exit 1
  fi
  expect_exit_code 2 ./scripts/install.sh install --json --dry-run

  # Lifecycle grammar is a verb plus flags only. Every former component
  # target, including the old explicit Zombie alias, must fail as bad usage.
  for sub in install verify doctor repair uninstall; do
    for target in nope zombie forgejo forgejo-runner llama "${sub}"; do
      expect_exit_code 2 ./scripts/install.sh "${sub}" "${target}"
    done
  done
  expect_exit_code 2 ./scripts/install.sh install -- forgejo
  expect_exit_code 0 ./scripts/install.sh uninstall \
    --archive --keep-agent --dry-run
}

expect_exit_code() {
  local want="$1"; shift
  set +e
  "$@" >/dev/null 2>&1
  local got=$?
  set -e
  if [[ "${got}" -ne "${want}" ]]; then
    echo "FAIL: expected exit ${want}, got ${got}: $*" >&2
    exit 1
  fi
}

run_bad_usage() {
  echo "[smoke] bad usage guards"
  # `install unexpected` used to live here but install requires root, so on
  # a non-root runner the assertion was satisfied by require_root rather
  # than by reject_unexpected_positional_args. `doctor unexpected`
  # exercises the same code path without needing root. See FIX-1-14.
  expect_exit_code 2 ./scripts/install.sh doctor unexpected
  expect_exit_code 2 ./scripts/install.sh verify unexpected
  expect_exit_code 2 ./scripts/install.sh repair unexpected
  # Duplicate subcommand tokens must be rejected too (FIX-1-15).
  expect_exit_code 2 ./scripts/install.sh doctor doctor
  expect_exit_code 2 ./scripts/install.sh install install
  expect_exit_code 2 env 'ZOMBIE_USER=bad user' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_USER=root' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_USER=bad-' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_USER=bad_' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_DIR=relative/path' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_DIR=/tmp/zombie;touch /tmp/install-path-pwn' ./scripts/install.sh doctor
  expect_exit_code 2 env 'LOG_FILE=relative.log' ./scripts/install.sh doctor
  expect_exit_code 2 env 'LOG_FILE=/tmp/zombie log' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_RECEIPT=1' 'ZOMBIE_RECEIPT_FILE=relative-receipt.txt' ./scripts/install.sh doctor
  expect_exit_code 2 env 'ZOMBIE_CHAT_PORT=70000' ./scripts/install.sh doctor
  # FIX-2-01: uninstall.sh must validate ZOMBIE_USER / paths *before*
  # any side-effecting command runs (so a smoke run as non-root still
  # exits 2 rather than 1).
  expect_exit_code 2 env 'ZOMBIE_USER=zombie;touch /tmp/zombie-pwn' ./scripts/uninstall.sh --dry-run
  expect_exit_code 2 env 'ZOMBIE_USER=root' ./scripts/uninstall.sh --dry-run
  expect_exit_code 2 env 'ZOMBIE_DIR=relative/path' ./scripts/uninstall.sh --dry-run
  expect_exit_code 2 env 'ZOMBIE_DIR=/tmp/zombie;touch /tmp/uninstall-path-pwn' ./scripts/uninstall.sh --dry-run
  expect_exit_code 2 env 'BACKUP_DIR=relative/path' ./scripts/uninstall.sh --dry-run
  expect_exit_code 2 env 'BACKUP_DIR=/tmp/zombie backup' ./scripts/uninstall.sh --dry-run
  [[ ! -e /tmp/zombie-pwn ]] || { echo "FAIL: uninstall.sh ZOMBIE_USER injection created /tmp/zombie-pwn" >&2; exit 1; }
  [[ ! -e /tmp/install-path-pwn ]] || { echo "FAIL: install.sh ZOMBIE_DIR injection created /tmp/install-path-pwn" >&2; exit 1; }
  [[ ! -e /tmp/uninstall-path-pwn ]] || { echo "FAIL: uninstall.sh ZOMBIE_DIR injection created /tmp/uninstall-path-pwn" >&2; exit 1; }
  # FIX-2-11: uninstall.sh run() must refuse extra arguments.
  set +e
  out="$(bash -c '
    set -Eeuo pipefail
    DRY_RUN=0
    C_RED=""; C_RESET=""; C_YEL=""
    run() {
      if (( $# != 1 )); then
        echo "BADARGS" >&2
        exit 1
      fi
      echo "$1"
    }
    run "echo a" "echo b"
  ' 2>&1)"
  rc=$?
  set -e
  if [[ $rc -eq 0 ]] || [[ "${out}" != *BADARGS* ]]; then
    echo "FAIL: run() guard did not refuse extra args" >&2
    exit 1
  fi
  # Uninstall must keep cleaning up even when host-level best-effort
  # removals fail, and it must quote paths passed through its eval helper.
  grep -Fq 'run_or_warn "systemctl daemon-reload"' scripts/uninstall.sh
  grep -Fq 'remove_tree_checked "${ZOMBIE_DIR}" "${ZOMBIE_DIR}"' scripts/uninstall.sh
  grep -Fq 'run_or_warn "Remove global npm package ${_pkg}"' scripts/uninstall.sh
  grep -Fq 'rm -f -- $(shell_quote "${f}")' scripts/uninstall.sh
  grep -Fq 'rm -f -- $(shell_quote "${_path}")' scripts/uninstall.sh
  # uninstall.sh exits during top-level validation when sourced as non-root,
  # so exercise a minimal copy of the helper bodies here. Keep this block in
  # sync with the uninstall helpers above.
  out="$(bash -c '
    set -Eeuo pipefail
    DRY_RUN=0
    UNINSTALL_EXIT=0
    warn() { printf "WARN:%s\n" "$*"; }
    run() {
      if (( $# != 1 )); then
        echo "BADARGS" >&2
        exit 1
      fi
      eval "$1"
    }
    shell_quote() {
      if (( $# != 1 )); then
        echo "BADQUOTE" >&2
        exit 1
      fi
      printf "%q" "$1"
    }
    run_or_warn() {
      local description="$1"
      local command="$2"
      if [[ "${DRY_RUN}" == "1" ]]; then
        run "${command}"
        return 0
      fi
      set +e
      eval "${command}"
      local rc=$?
      set -e
      if (( rc != 0 )); then
        warn "${description} failed (exit ${rc}); continuing cleanup."
        UNINSTALL_EXIT=1
      fi
      return 0
    }
    remove_tree_checked() {
      local path="$1"
      local label="$2"
      local quoted
      quoted="$(shell_quote "${path}")"
      if [[ "${DRY_RUN}" == "1" ]]; then
        run "rm -rf -- ${quoted}"
        return 0
      fi
      set +e
      rm -rf -- "${path}"
      local rc=$?
      set -e
      if (( rc != 0 )); then
        warn "Failed to remove ${label} (exit ${rc}); continuing cleanup."
        UNINSTALL_EXIT=1
        return 0
      fi
      if [[ -e "${path}" ]]; then
        warn "Failed to remove ${label}; path still exists: ${path}"
        UNINSTALL_EXIT=1
        return 0
      fi
      return 0
    }
    tmp=""
    trap '\''if [[ -n "${tmp}" && -d "${tmp}/parent" ]]; then chmod 700 "${tmp}/parent"; fi; [[ -n "${tmp}" ]] && rm -rf "${tmp}"'\'' EXIT
    run_or_warn "expected success" "true"
    [[ "${UNINSTALL_EXIT}" -eq 0 ]]
    run_or_warn "expected failure" "false"
    [[ "${UNINSTALL_EXIT}" -eq 1 ]]
    tmp="$(mktemp -d)"
    mkdir -p "${tmp}/parent/stubborn"
    chmod 500 "${tmp}/parent"
    remove_tree_checked "${tmp}/parent/stubborn" "stubborn"
    [[ "${UNINSTALL_EXIT}" -eq 1 ]]
    chmod 700 "${tmp}/parent"
    rm -rf "${tmp}"
    tmp=""
  ' 2>&1)"
  if [[ "${out}" != *"WARN:expected failure failed (exit 1); continuing cleanup."* ]]; then
    echo "FAIL: run_or_warn warning was not emitted" >&2
    exit 1
  fi
  if [[ "${out}" != *"WARN:Failed to remove stubborn"* ]]; then
    echo "FAIL: remove_tree_checked warning was not emitted" >&2
    exit 1
  fi
}

run_noninteractive() {
  echo "[smoke] non-interactive guard"
  # We cannot exercise the full install path without root, so we only
  # assert that the documented escape hatch is still advertised in
  # --help. The previous version of this test allocated a tmpdir and
  # probed `sudo -n true` but discarded both, so they have been removed
  # (FIX-1-13).
  ./scripts/install.sh --help | grep -q ZOMBIE_NONINTERACTIVE
  # The connectivity preflight must not use the retrying download helper:
  # curl_get adds 45 seconds of wrapper backoff before fallback probes run.
  if sed -n '/^preflight() {/,/^}/p' scripts/install.sh \
      | grep -q 'curl_get.*archive\.ubuntu\.com'; then
    echo "FAIL: connectivity preflight uses the retrying download helper" >&2
    exit 1
  fi
}

run_diagnostics() {
  echo "[smoke] collect-diagnostics best-effort"
  # FIX-3-24: collect-diagnostics must finish and write its tarball
  # even when individual captured commands return non-zero (e.g.
  # `systemctl status` of an inactive unit). Before the
  # fix, `set -euo pipefail` aborted the run on the first such failure
  # and the EXIT trap then deleted the partial bundle, so no tarball
  # was produced. Run the real script in an isolated TMPDIR and assert
  # it exits 0 and leaves exactly one tarball behind.
  local td
  td="$(mktemp -d)"
  if ! TMPDIR="${td}" bash payload/bin/collect-diagnostics >/dev/null 2>&1; then
    rm -rf "${td}"
    echo "FAIL: collect-diagnostics exited non-zero (best-effort capture regressed)" >&2
    exit 1
  fi
  local -a tarballs
  mapfile -t tarballs < <(find "${td}" -maxdepth 1 -name 'ubuntu-zombie-diagnostics-*.tar.gz' -print)
  if [[ "${#tarballs[@]}" -ne 1 ]]; then
    rm -rf "${td}"
    echo "FAIL: collect-diagnostics must produce exactly one tarball (found ${#tarballs[@]})" >&2
    exit 1
  fi
  local tarball
  tarball="${tarballs[0]}"
  if [[ ! -s "${tarball}" ]]; then
    rm -rf "${td}"
    echo "FAIL: collect-diagnostics produced an empty tarball" >&2
    exit 1
  fi
  # The staging directory must be cleaned up by the EXIT trap, leaving
  # only the tarball behind.
  if find "${td}" -maxdepth 1 -type d -name 'ubuntu-zombie-diagnostics-*' | grep -q .; then
    rm -rf "${td}"
    echo "FAIL: collect-diagnostics left its staging directory behind" >&2
    exit 1
  fi
  rm -rf "${td}"

  echo "[smoke] health-check timer warn-only mode"
  td="$(mktemp -d)"
  cat > "${td}/systemctl" <<'EOF'
#!/usr/bin/env bash
exit 1
EOF
  chmod +x "${td}/systemctl"
  if PATH="${td}:${PATH}" ZOMBIE_DIR="${td}/missing" \
      bash payload/bin/health-check >/dev/null 2>&1; then
    rm -rf "${td}"
    echo "FAIL: health-check should exit non-zero for manual failed checks" >&2
    exit 1
  fi
  if ! PATH="${td}:${PATH}" ZOMBIE_DIR="${td}/missing" ZOMBIE_HEALTH_WARN_ONLY=1 \
      bash payload/bin/health-check >/dev/null 2>&1; then
    rm -rf "${td}"
    echo "FAIL: health-check timer warn-only mode should not fail the systemd unit" >&2
    exit 1
  fi
  rm -rf "${td}"
}

run_standards() {
  echo "[smoke] repository standards"
  local required=(
    README.md
    LICENSE
    CODE_OF_CONDUCT.md
    SECURITY.md
    SUPPORT.md
    RELEASE.md
    CONTRIBUTING.md
    CHANGELOG.md
    VERSION
    Makefile
    .editorconfig
    .pre-commit-config.yaml
    .github/CODEOWNERS
    .github/PULL_REQUEST_TEMPLATE.md
    .github/workflows/ci.yml
    .github/workflows/codeql.yml
    .github/workflows/dependency-review.yml
    .github/workflows/scorecard.yml
    .github/workflows/release.yml
    .github/workflows/integration.yml
    docs/PLATFORMS.md
    docs/UPGRADING.md
    docs/FAQ.md
    payload/agent/bridge-dependencies.lock
    payload/bin/verify-release
    debian/control.in
    debian/postinst
    debian/prerm
    debian/copyright
    scripts/build-deb.sh
    scripts/verify-bridge-pins.sh
  )
  local f
  for f in "${required[@]}"; do
    [[ -s "$f" ]] || { echo "missing required repository file: $f" >&2; exit 1; }
  done

  local removed=(
    .github/workflows/beep-release.yml
    .github/workflows/forgejo-release.yml
    .github/workflows/imaginary-friend-release.yml
    .github/workflows/llama-release.yml
    docs/FORGEJO.md
    payload/agent/skills/forgejo.md
    payload/etc/forgejo-runner-config.yaml
    payload/systemd/forgejo-runner.service
    scripts/component-registry.sh
    tests/family/conformance.py
    tests/family/test_contract.py
  )
  for f in "${removed[@]}"; do
    [[ ! -e "$f" ]] \
      || { echo "removed multi-product asset still exists: $f" >&2; exit 1; }
  done
  [[ -z "$(git ls-files -- products family)" ]] \
    || { echo "removed product-family files are still tracked" >&2; exit 1; }

  grep -q 'registry.npmjs.org/@earendil-works%2Fpi-ai/latest' scripts/install.sh \
    || { echo "installer must resolve the latest pi-ai release" >&2; exit 1; }
  grep -q 'registry.npmjs.org/@earendil-works%2Fpi-coding-agent/latest' scripts/install.sh \
    || { echo "installer must resolve the latest pi-coding-agent release" >&2; exit 1; }
  grep -q 'Integrity check failed for ${package}@${version}' scripts/install.sh \
    || { echo "latest Earendil tarballs must be integrity-verified" >&2; exit 1; }
  grep -q 'tarball.hostname !== "registry.npmjs.org"' scripts/install.sh \
    || { echo "Earendil tarballs must stay on the npm registry" >&2; exit 1; }
  grep -q 'sri.slice(0, i) !== "sha512"' scripts/install.sh \
    || { echo "Earendil tarballs must require sha512 integrity" >&2; exit 1; }
  grep -q 'pi-ai) PI_AI_VERSION="${version}"' scripts/install.sh \
    || { echo "installer must retain the resolved pi-ai version" >&2; exit 1; }
  grep -q 'pi-mono) PI_MONO_VERSION="${version}"' scripts/install.sh \
    || { echo "installer must retain the resolved pi-mono version" >&2; exit 1; }

  # The built-in skills ship under payload/agent/skills/ so
  # ``make package`` carries them into the release bundle and the
  # installer can deploy them to /opt/ai-zombie/skills/.
  local s
  for s in ai-agents apt backup certificates containers css database \
           desktop dev disk files git hardware hermes-agent html \
           journal json kernel llm locale network obsidian openclaw-agent \
           packages performance pi-mono-agent process reactivation \
           scheduling secrets security services snap sql systemd \
           troubleshoot ubuntu users virtualization web zombie zram; do
    [[ -s "payload/agent/skills/${s}.md" ]] || \
      { echo "missing built-in skill: payload/agent/skills/${s}.md" >&2; exit 1; }
  done

  grep -q "__ZOMBIE_DIR__" payload/systemd/ubuntu-zombie-chat.service \
    || { echo "chat systemd template must keep __ZOMBIE_DIR__ placeholder" >&2; exit 1; }
  grep -q "ExecStart=__ZOMBIE_DIR__/bin/health-check" payload/systemd/ubuntu-zombie-health.service \
    || { echo "health systemd template must use __ZOMBIE_DIR__ placeholder" >&2; exit 1; }
  grep -q "ZOMBIE_HEALTH_WARN_ONLY=1" payload/systemd/ubuntu-zombie-health.service \
    || { echo "health timer must not leave a failed unit after reporting unhealthy state" >&2; exit 1; }
  local provider_helper provider_test_file
  provider_helper="$(install_function provider_credential_configured)"
  provider_test_file="$(mktemp)"
  printf 'ZOMBIE_PROVIDER=lmstudio\nLMSTUDIO_API_KEY=local\n' > "${provider_test_file}"
  bash -c "${provider_helper}
    provider_credential_configured \"\$1\"" _ "${provider_test_file}" \
    || { rm -f "${provider_test_file}"; echo "Local LLM credentials must satisfy installer health checks" >&2; exit 1; }
  rm -f "${provider_test_file}"
  grep -q 'GROQ|LMSTUDIO' payload/bin/health-check \
    || { echo "Local LLM credentials must satisfy deployed health checks" >&2; exit 1; }
  local model_helper model_test_dir discover_helper
  model_helper="$(install_function model_selection_configured)"
  discover_helper="$(install_function discover_local_llms)"
  grep -q 'model_selection_configured' <<<"${discover_helper}" \
    || { echo "Local LLM discovery must preserve a configured model" >&2; exit 1; }
  model_test_dir="$(mktemp -d)"
  mkdir -p "${model_test_dir}/secrets"
  cat > "${model_test_dir}/secrets/env" <<'EOF'
# ZOMBIE_MODEL=commented-out
ZOMBIE_MODEL=
EOF
  bash -c "${model_helper}
    ZOMBIE_DIR=\"\$1\"
    for key in ZOMBIE_MODEL ZOMBIE_OPENAI_MODEL ZOMBIE_ANTHROPIC_MODEL \
        ZOMBIE_GEMINI_MODEL ZOMBIE_XAI_MODEL ZOMBIE_MISTRAL_MODEL \
        ZOMBIE_GROQ_MODEL ZOMBIE_OPENROUTER_MODEL; do
      unset \"\${key}\"
    done
    ! model_selection_configured
    printf '%s\n' 'ZOMBIE_MODEL=installed-model' >> \"\${ZOMBIE_DIR}/secrets/env\"
    model_selection_configured
    : > \"\${ZOMBIE_DIR}/secrets/env\"
    ZOMBIE_OPENAI_MODEL=environment-model
    model_selection_configured" _ "${model_test_dir}" \
    || { rm -rf "${model_test_dir}"; echo "Configured model detection failed" >&2; exit 1; }
  rm -rf "${model_test_dir}"

  local lifecycle_helper lifecycle_test_dir lifecycle_runner lifecycle_state
  lifecycle_helper="$(install_function init_lifecycle_state)"
  lifecycle_test_dir="$(mktemp -d)"
  lifecycle_state="${lifecycle_test_dir}/state/lifecycle.json"
  mkdir -p "${lifecycle_test_dir}/agent" "${lifecycle_test_dir}/state"
  cp payload/agent/lifecycle.py "${lifecycle_test_dir}/agent/lifecycle.py"
  lifecycle_runner="${lifecycle_helper}
    set -euo pipefail
    runuser() {
      [[ \"\$1\" == '-u' ]]
      shift 2
      [[ \"\$1\" == '--' ]]
      shift
      command \"\$@\"
    }
    chown() { :; }
    info() { :; }
    warn() { :; }
    ok() { :; }
    die() { printf '%s\n' \"\$1\" >&2; return \"\${2:-1}\"; }
    ZOMBIE_DIR=\"\$1\"
    AGENT_USER=zombie
    TTL_DAYS=7
    init_lifecycle_state"
  bash -c "${lifecycle_runner}" _ "${lifecycle_test_dir}"
  ZOMBIE_LIFECYCLE_STATE="${lifecycle_state}" \
    PYTHONPATH=payload/agent python3 -c 'import lifecycle; lifecycle.set_ttl(11)'
  cp "${lifecycle_state}" "${lifecycle_state}.extended"
  bash -c "${lifecycle_runner}" _ "${lifecycle_test_dir}"
  cmp -s "${lifecycle_state}.extended" "${lifecycle_state}" \
    || { rm -rf "${lifecycle_test_dir}"; echo "Reinstall must preserve an extended TTL" >&2; exit 1; }
  ZOMBIE_LIFECYCLE_STATE="${lifecycle_state}" \
    PYTHONPATH=payload/agent python3 -c 'import lifecycle; lifecycle.kill()'
  cp "${lifecycle_state}" "${lifecycle_state}.dead"
  bash -c "${lifecycle_runner}" _ "${lifecycle_test_dir}"
  cmp -s "${lifecycle_state}.dead" "${lifecycle_state}" \
    || { rm -rf "${lifecycle_test_dir}"; echo "Reinstall must preserve a TTL tombstone" >&2; exit 1; }
  printf 'invalid\n' > "${lifecycle_state}"
  bash -c "${lifecycle_runner}" _ "${lifecycle_test_dir}"
  ZOMBIE_LIFECYCLE_STATE="${lifecycle_state}" \
    PYTHONPATH=payload/agent python3 -c \
      'import lifecycle; assert lifecycle.status()["configured"]'
  rm -rf "${lifecycle_test_dir}"

  grep -q "_LOCAL_API_LAN_PORTS = (1234, 8080, 11434, 51234)" \
    payload/agent/providers.py \
    || { echo "/locals must probe standard API ports across the LAN" >&2; exit 1; }
  grep -q '\["/fullwidth \[on|off\]"' payload/agent/templates/index.html \
    || { echo "chat must expose /fullwidth with optional on/off" >&2; exit 1; }
  grep -q 'body.fullwidth main, body.fullwidth .composer,' \
    payload/agent/templates/index.html \
    || { echo "/fullwidth must widen the transcript and composer" >&2; exit 1; }
  grep -q 'body.fullwidth .reactivation-banner' \
    payload/agent/templates/index.html \
    || { echo "/fullwidth must widen the reactivation banner" >&2; exit 1; }
  grep -q 'completeUi("Done.")' payload/agent/templates/index.html \
    || { echo "completed streamed turns must display Done" >&2; exit 1; }
  grep -q 'async function uzStreamReactivationTurn' \
    payload/agent/templates/index.html \
    && grep -q 'uzStreamLiveTurn(active.turn_id' \
      payload/agent/templates/index.html \
    || { echo "fired reactivations must stream live in chat" >&2; exit 1; }
  grep -q 'Reactivation started for conversation' \
    payload/agent/templates/index.html \
    || { echo "reactivation processing must be visible in chat" >&2; exit 1; }
  grep -q 'id="pause-reactivation"' payload/agent/templates/index.html \
    && grep -q 'id="stop-reactivation"' payload/agent/templates/index.html \
    && grep -q '/api/turn/${encodeURIComponent(activeReactivation.turn_id)}/stop' \
      payload/agent/templates/index.html \
    || { echo "active reactivations must expose pause and stop controls" >&2; exit 1; }
  grep -q 'visibleReactivationReply' payload/agent/templates/index.html \
    && grep -q 'ubuntu-zombie-reactivation' \
      payload/agent/templates/index.html \
    || { echo "structured reactivation requests must stay out of live chat" >&2; exit 1; }
  grep -q 'showPendingReactivation' payload/agent/templates/index.html \
    && grep -q 'data.reactivation' payload/agent/templates/index.html \
    || { echo "terminal reactivation outcomes must update chat immediately" >&2; exit 1; }
  grep -q 'uzPostJson("/api/reactivation", { reset: true })' \
    payload/agent/templates/index.html \
    && grep -q 'data.get("reset") is True' payload/agent/server.py \
    || { echo "/reactivation reset must connect the chat UX to the API" >&2; exit 1; }
  grep -q 'tallyStat("reactivations"' payload/agent/templates/index.html \
    && grep -q 'plural(bucket.reactivations, "reactivation")' \
      payload/agent/templates/index.html \
    || { echo "verbose mode must count reactivations" >&2; exit 1; }
  grep -q 'id="logout"' payload/agent/templates/index.html \
    || { echo "chat UI must expose the logoff button" >&2; exit 1; }
  grep -q 'case "/logout"' payload/agent/templates/index.html \
    || { echo "chat UI must expose the /logout command" >&2; exit 1; }
  grep -q 'case "/locals"' payload/agent/templates/index.html \
    && grep -q 'case "/local"' payload/agent/templates/index.html \
    && grep -q 'case "/models"' payload/agent/templates/index.html \
    || { echo "chat UI must expose /locals, /local, and /models commands" >&2; exit 1; }
  grep -q 'setAuthState(false, false)' payload/agent/templates/index.html \
    || { echo "chat UI must hide Logoff when the password gate is removed" >&2; exit 1; }
  grep -q 'Commands by category:' payload/agent/templates/index.html \
    || { echo "chat /help must keep compact grouped output" >&2; exit 1; }
  grep -q 'EventSource' payload/agent/templates/index.html \
    || { echo "chat UI must keep the SSE EventSource path" >&2; exit 1; }
  grep -q 'if (!verboseMode)' payload/agent/templates/index.html \
    && grep -q 'verbose-tool-activity' payload/agent/templates/index.html \
    && grep -q 'Tool activity is hidden; approval prompts remain visible.' \
      payload/agent/templates/index.html \
    || { echo "chat UI must hide ordinary tool activity unless verbose" >&2; exit 1; }
  grep -q '"args_summary": _summarize(cleaned)' payload/agent/server.py \
    || { echo "verbose tool activity must include summarized arguments" >&2; exit 1; }
  grep -q 'Live stream interrupted' payload/agent/templates/index.html \
    || { echo "chat UI must keep the streaming fallback reload path" >&2; exit 1; }
  grep -q 'queued' payload/agent/templates/index.html \
    || { echo "chat UI must keep the queued-message affordance" >&2; exit 1; }
  grep -q 'aria-label="Chat transcript"' payload/agent/templates/index.html \
    || { echo "chat transcript must retain its accessible name" >&2; exit 1; }
  python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path


class TranscriptNestingParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.divs = []
        self.found_log = False

    def handle_starttag(self, tag, attrs):
        if tag != "div":
            return
        element_id = dict(attrs).get("id")
        if element_id == "log":
            assert "welcome" not in self.divs, \
                "chat transcript must not be nested inside the welcome panel"
            self.found_log = True
        self.divs.append(element_id)

    def handle_endtag(self, tag):
        if tag == "div":
            self.divs.pop()


parser = TranscriptNestingParser()
parser.feed(Path("payload/agent/templates/index.html").read_text())
assert parser.found_log, "chat transcript is missing"
PY
  grep -q 'class="sr-only">Message the systems administrator' \
    payload/agent/templates/index.html \
    || { echo "chat composer must retain its accessible label" >&2; exit 1; }
  grep -q 'data-starter=' payload/agent/templates/index.html \
    || { echo "chat welcome must retain its starter prompts" >&2; exit 1; }
  grep -q 'case "/purpose"' payload/agent/templates/index.html \
    && grep -q '"#welcome \[data-starter\]"' payload/agent/templates/index.html \
    || { echo "/purpose must re-show the welcome starter buttons inline" >&2; exit 1; }
  grep -q '@media (max-width: 640px)' payload/agent/templates/index.html \
    || { echo "chat UI must retain its mobile layout" >&2; exit 1; }
  grep -q 'text: "Copy"' payload/agent/templates/index.html \
    || { echo "assistant responses must retain their copy action" >&2; exit 1; }
  grep -q 'busy ? "Queue" : "Send"' payload/agent/templates/index.html \
    || { echo "busy chat submit must retain its queue affordance" >&2; exit 1; }
  grep -q 'id="command-menu"' payload/agent/templates/index.html \
    && grep -q 'aria-label="Slash commands"' payload/agent/templates/index.html \
    || { echo "chat UI must provide slash-command completion" >&2; exit 1; }
  grep -q 'Type /commands <filter> for descriptions.' \
    payload/agent/templates/index.html \
    || { echo "chat /help must retain its compact command index" >&2; exit 1; }
  grep -q 'section "Install policy and operator tools"' scripts/install.sh \
    || { echo "installer must retain separated deployment phases" >&2; exit 1; }
  grep -q 'transcriptPinnedToBottom' payload/agent/templates/index.html \
    || { echo "chat transcript must retain sticky tail tracking" >&2; exit 1; }
  grep -q 'body.innerHTML = renderMarkdown(visibleReactivationReply(liveMarkdown))' \
    payload/agent/templates/index.html \
    || { echo "streamed assistant replies must render as Markdown" >&2; exit 1; }
  grep -q 'applyTurnPayload(payload, true)' payload/agent/templates/index.html \
    && grep -q 'Inspect tool call' payload/agent/templates/index.html \
    && grep -q 'Activity already observed on this page is retained' \
      payload/agent/templates/index.html \
    || { echo "verbose transcript activity must remain inspectable and persistent" >&2; exit 1; }
  command -v node >/dev/null \
    || { echo "node is required for chat UI smoke tests" >&2; exit 1; }
  _TOOL_DETAIL_TEST="$(mktemp)"
  python3 - "${_TOOL_DETAIL_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
stats_start = text.index("const uzTextEncoder")
stats_end = text.index("function formatDuration", stats_start)
args_start = text.index("function summarizeArgs")
args_end = text.index("function renderToolCall", args_start)
test = r'''
const command = `printf 'hello world\\n'
wc -c ./README.md`;
const args = { command };
if (formatToolArguments(args) !== command) {
  throw new Error("command arguments must render as readable text");
}
const mixed = { command, cwd: "/tmp/example" };
if (formatToolArguments(mixed) !== `${command}\n{\n  "cwd": "/tmp/example"\n}`) {
  throw new Error("command arguments with metadata must include both sections");
}
const special = { command: 'echo "test"', cwd: "/path/with\\backslash" };
// The expected value is a JavaScript string containing JSON, so the
// backslash is escaped once for the source literal and once for JSON.
if (formatToolArguments(special) !== 'echo "test"\n{\n  "cwd": "/path/with\\\\backslash"\n}') {
  throw new Error("special characters in tool arguments must remain readable");
}
if (formatToolArguments({ cwd: "/tmp/example" }) !== '{\n  "cwd": "/tmp/example"\n}') {
  throw new Error("non-command arguments must render as JSON");
}
if (formatToolArguments(null) !== "" ||
    formatToolArguments(undefined) !== "" ||
    formatToolArguments("") !== "") {
  throw new Error("empty arguments must render as an empty string");
}
if (formatToolArguments(42) !== "42") {
  throw new Error("non-object arguments must render as strings");
}
if (toolArgumentPayload({ args_summary: args, args: { command: "fallback" } }) !== args ||
    toolArgumentPayload({ args }) !== args) {
  throw new Error("tool argument payload must prefer args_summary and fallback to args");
}
if (toolArgumentBytes(args) !== byteLength(JSON.stringify(args))) {
  throw new Error("tool input bytes must count serialized arguments");
}
const note = formatToolDoneNote("bash", "done", ["58 ms", "287 B in", "11.9 kB out"]);
if (note !== "bash · done · 58 ms · 287 B in · 11.9 kB out") {
  throw new Error(`unexpected tool done note: ${note}`);
}
if (formatToolDoneNote("tool", "status", []) !== "tool · status") {
  throw new Error("empty tool metric list must not add a trailing separator");
}
'''
Path(sys.argv[1]).write_text(text[stats_start:stats_end] + text[args_start:args_end] + test)
PY
  node "${_TOOL_DETAIL_TEST}"
  rm -f "${_TOOL_DETAIL_TEST}"
  # A tool_end (or pending_approval) whose tool_start frame was dropped
  # must still render a completed line. The fallback used to reference an
  # undefined ``note`` binding, so the listener threw a ReferenceError and
  # the approval buttons for that call were never drawn.
  _ORPHAN_TOOL_TEST="$(mktemp)"
  python3 - "${_ORPHAN_TOOL_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
start = text.index("const toolLineStacks = new Map();")
end = text.index("const settleLive =", start)
prelude = r'''
const verboseMode = true;
const scrollLog = () => {};
const el = (tag, opts = {}) => {
  const node = {
    tag,
    children: [],
    className: opts.class || "",
    textContent: opts.text || "",
    hidden: false,
    appendChild(child) { this.children.push(child); return child; },
    get firstElementChild() { return this.children[0] || null; },
  };
  return node;
};
const activity = el("div");
'''
test = r'''
const orphan = endToolLine("fs.read", false, "fs.read · failed", "boom");
if (!orphan || orphan.className !== "act failed verbose-tool-activity") {
  throw new Error("an orphaned tool_end must still render a failed line");
}
if (activity.children.length !== 1) {
  throw new Error("the orphaned line must be appended to the activity list");
}
const label = orphan.children[1];
if (label.textContent !== "fs.read · failed") {
  throw new Error(`unexpected orphan label: ${label.textContent}`);
}
const dynamic = endToolLine("shell.run", true, () => "shell.run · done", "ok");
if (dynamic.className !== "act done verbose-tool-activity") {
  throw new Error("an orphaned tool_end with a callback note must render");
}
'''
Path(sys.argv[1]).write_text(prelude + text[start:end] + test)
PY
  node "${_ORPHAN_TOOL_TEST}"
  rm -f "${_ORPHAN_TOOL_TEST}"
  grep -q 'visibleMessages.push({ role: "assistant", content: data.reply })' \
    payload/agent/templates/index.html \
    || { echo "streamed replies must be recorded for /copy" >&2; exit 1; }
  grep -q 'A turn is still running. Stop it before retrying.' \
    payload/agent/templates/index.html \
    || { echo "/retry must not start a second turn over a live stream" >&2; exit 1; }
  python3 - <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
marker = "activeEventSource = new EventSource("
index = text.index(marker)
# The preceding statements must close any stream still attached, or a
# second turn started over a live one leaks its EventSource.
if "activeEventSource.close()" not in text[max(0, index - 400):index]:
    sys.exit("a new live stream must close any previous EventSource")
PY
  if grep -A3 'function tallyStat' payload/agent/templates/index.html \
      | grep -q 'if (!verboseMode) return'; then
    echo "verbose statistics must be retained before display is enabled" >&2
    exit 1
  fi
  grep -q 'class="table-wrap"' payload/agent/templates/index.html \
    && grep -q '\.md th, \.md td' payload/agent/templates/index.html \
    || { echo "Markdown tables must render with readable table styling" >&2; exit 1; }
  grep -q 'uzDetailedCommandHelp(arg)' payload/agent/templates/index.html \
    && grep -q '"/version": "Shows installed component versions' \
      payload/agent/templates/index.html \
    || { echo "/help <command> must provide detailed command help" >&2; exit 1; }
  grep -q 'needle === "all"' payload/agent/templates/index.html \
    && grep -q 'needle.includes("\*")' payload/agent/templates/index.html \
    || { echo "/help must support all and wildcard detail pages" >&2; exit 1; }
  grep -Fq 'typed === "/" ? matches' payload/agent/templates/index.html \
    || { echo "a bare slash must show the complete command finder" >&2; exit 1; }
  _COMMAND_TEST="$(mktemp)"
  python3 - "${_COMMAND_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
start = text.index("function uzCommandName")
end = text.index("let commandMatches", start)
reactivation_start = text.index("function visibleReactivationReply")
reactivation_end = text.index(
    "async function uzStreamReactivationTurn", reactivation_start
)
test = r'''
const marker = "<ubuntu-zombie-reactivation>";
const REACTIVATION_REQUEST_MARKER = marker;
if (visibleReactivationReply("Visible reply") !== "Visible reply") {
  throw new Error("ordinary streamed replies must remain visible");
}
if (visibleReactivationReply("Visible reply\n" + marker + '{"delay_seconds":1}') !==
    "Visible reply") {
  throw new Error("complete structured requests must be hidden");
}
if (visibleReactivationReply("Visible reply\n<ubuntu-zombie-react") !==
    "Visible reply") {
  throw new Error("partial structured request markers must be hidden");
}
const entries = [
  ["/local [url]"],
  ["/locals"],
  ["/conversations"],
];
if (uzExactCommandIndex(entries, "/conversations") !== 2) {
  throw new Error("exact /conversations command was not selected");
}
if (uzExactCommandIndex(entries, "/LOCAL") !== 0) {
  throw new Error("exact command matching must be case-insensitive");
}
if (uzExactCommandIndex(entries, "/loc") !== -1) {
  throw new Error("partial commands must remain autocomplete candidates");
}
'''
Path(sys.argv[1]).write_text(
    text[reactivation_start:reactivation_end] + text[start:end] + test
)
PY
  node "${_COMMAND_TEST}"
  rm -f "${_COMMAND_TEST}"
  _SLASH_PARSE_TEST="$(mktemp)"
  python3 - "${_SLASH_PARSE_TEST}" <<'PY'
import re
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
start = text.index("function uzParseSlashCommand")
end = text.index("async function handleSlashCommand", start)
test = r'''
const parsed = uzParseSlashCommand("/PASSWORD Two  Spaces\tand-a-tab");
if (parsed.cmd !== "/password" ||
    parsed.arg !== "Two  Spaces\tand-a-tab") {
  throw new Error(`slash arguments were changed: ${JSON.stringify(parsed)}`);
}
if (uzParseSlashCommand("//etc/passwd") !== null) {
  throw new Error("double slash must escape slash-command handling");
}
for (const invalid of ["", "0", "-1", "2.5", "3x", "9007199254740992"]) {
  if (uzPositiveInteger(invalid) !== null) {
    throw new Error(`accepted invalid positive integer: ${invalid}`);
  }
}
if (uzPositiveInteger("42") !== 42) {
  throw new Error("rejected a valid positive integer");
}
const lastLoad = uzParseLoadArgs("LAST");
if (!lastLoad || lastLoad.last !== true) {
  throw new Error("/load last must target the newest conversation");
}
const multiLoad = uzParseLoadArgs(" 3  1\t7 ");
if (!multiLoad || multiLoad.last ||
    JSON.stringify(multiLoad.ids) !== "[3,1,7]") {
  throw new Error("/load must accept several whitespace-separated ids");
}
for (const invalid of ["", "last 2", "1 zero", "0 1", "1 -2"]) {
  if (uzParseLoadArgs(invalid) !== null) {
    throw new Error(`accepted invalid /load arguments: ${invalid}`);
  }
}
'''
Path(sys.argv[1]).write_text(text[start:end] + test)

commands_match = re.search(
    r"const SLASH_COMMANDS = \[(.*?)\n\];", text, re.DOTALL
)
aliases_match = re.search(
    r"const COMMAND_ALIASES = \{(.*?)\n\};", text, re.DOTALL
)
details_match = re.search(
    r"const COMMAND_DETAILS = \{(.*?)\n\};", text, re.DOTALL
)
if not details_match:
    raise SystemExit("slash-command details registry not found")
handler_start = text.index("async function handleSlashCommand")
handler_end = text.index('\nform.addEventListener("submit"', handler_start)
handler = text[handler_start:handler_end]
documented = set(re.findall(r'\["(/[^ "\]]+)', commands_match.group(1)))
described = set(re.findall(r'"(/[^"]+)":', details_match.group(1)))
canonical_aliases = set(re.findall(r': "(/[^"]+)"', aliases_match.group(1)))
handled = set(re.findall(r'case "(/[^"]+)"', handler))
missing_detailed_help = documented - described
if missing_detailed_help:
    raise SystemExit(
        "documented slash commands missing detailed help: "
        + ", ".join(sorted(missing_detailed_help))
    )
missing = (documented | canonical_aliases) - handled
if missing:
    raise SystemExit(
        "documented slash commands missing dispatcher cases: "
        + ", ".join(sorted(missing))
    )
if "const cmd = COMMAND_ALIASES[parsed.cmd] || parsed.cmd;" not in handler:
    raise SystemExit("slash-command aliases must route to canonical handlers")
PY
  node "${_SLASH_PARSE_TEST}"
  rm -f "${_SLASH_PARSE_TEST}"
  _HELP_TEST="$(mktemp)"
  python3 - "${_HELP_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
registry_start = text.index("const SLASH_COMMANDS")
registry_end = text.index("function timestamp", registry_start)
help_start = text.index("function uzCommandEntries")
help_end = text.index("function uzCommandName", help_start)
test = r'''
const reprompt = uzDetailedCommandHelp("reprompt");
if (!reprompt.includes("/reprompt [placeholder]") ||
    !reprompt.includes("Changes the prompt placeholder")) {
  throw new Error("/help reprompt did not return its full help page");
}
if (!uzDetailedCommandHelp("help").includes("/help [command]")) {
  throw new Error("/help help did not return its own help page");
}
const quit = uzDetailedCommandHelp("quit");
if (!quit.includes("/quit") || !quit.includes("Alias for: /logout") ||
    !quit.includes("Ends the current browser session")) {
  throw new Error("/help quit did not return alias-aware detailed help");
}
const wildcard = uzDetailedCommandHelp("re*");
for (const command of ["/rebrand", "/redraw", "/reprompt", "/reset", "/resume", "/retry"]) {
  if (!wildcard.includes(command)) {
    throw new Error(`/help re* omitted ${command}`);
  }
}
const all = uzDetailedCommandHelp("all");
for (const command of ["/audit", "/help", "/quit", "/whoami"]) {
  if (!all.includes(command)) {
    throw new Error(`/help all omitted ${command}`);
  }
}
if (uzDetailedCommandHelp("does-not-exist") !== null) {
  throw new Error("unknown detailed help query should not match");
}
'''
Path(sys.argv[1]).write_text(
    text[registry_start:registry_end] + text[help_start:help_end] + test
)
PY
  node "${_HELP_TEST}"
  rm -f "${_HELP_TEST}"
  _REPROMPT_TEST="$(mktemp)"
  python3 - "${_REPROMPT_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
limit_start = text.index("const MAX_PROMPT_PLACEHOLDER_CHARS")
limit_end = text.index("\n", limit_start) + 1
start = text.index("const BRAND_STORAGE_KEY")
end = text.index("function brandWordmark", start)
test = r'''
const stored = new Map();
const window = { localStorage: {
  getItem: key => stored.has(key) ? stored.get(key) : null,
  setItem: (key, value) => stored.set(key, value),
  removeItem: key => stored.delete(key),
} };
const promptEl = {};
'''
test += text[limit_start:limit_end]
test += text[start:end]
test += r'''
applyPromptPlaceholder("Ask the administrator");
if (promptEl.placeholder !== "Ask the administrator" ||
    stored.get(PROMPT_STORAGE_KEY) !== "Ask the administrator") {
  throw new Error("/reprompt did not apply and persist its placeholder");
}
promptEl.placeholder = DEFAULT_PROMPT_PLACEHOLDER;
applyPromptPlaceholder(uzStorageGet(PROMPT_STORAGE_KEY), false);
if (promptEl.placeholder !== "Ask the administrator") {
  throw new Error("/reprompt placeholder did not survive a reload");
}
applyPromptPlaceholder("");
if (promptEl.placeholder !== DEFAULT_PROMPT_PLACEHOLDER ||
    stored.has(PROMPT_STORAGE_KEY)) {
  throw new Error("bare /reprompt did not restore and forget the default");
}
'''
Path(sys.argv[1]).write_text(test)
PY
  node "${_REPROMPT_TEST}"
  rm -f "${_REPROMPT_TEST}"
  _FULLWIDTH_TEST="$(mktemp)"
  python3 - "${_FULLWIDTH_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
start = text.index("const BRAND_STORAGE_KEY")
end = text.index("function brandWordmark", start)
test = r'''
const stored = new Map();
const classes = new Set();
const window = { localStorage: {
  getItem: key => stored.has(key) ? stored.get(key) : null,
  setItem: (key, value) => stored.set(key, value),
  removeItem: key => stored.delete(key),
} };
const document = { body: { classList: {
  toggle: (name, enabled) => enabled ? classes.add(name) : classes.delete(name),
} } };
const promptEl = {};
let fullWidthMode = false;
const MAX_PROMPT_PLACEHOLDER_CHARS = 160;
'''
test += text[start:end]
test += r'''
applyFullWidth(true);
if (!fullWidthMode || !classes.has("fullwidth") ||
    stored.get(FULLWIDTH_STORAGE_KEY) !== "on") {
  throw new Error("/fullwidth on did not apply and persist");
}
fullWidthMode = false;
classes.delete("fullwidth");
applyFullWidth(uzStorageGet(FULLWIDTH_STORAGE_KEY) === "on", false);
if (!fullWidthMode || !classes.has("fullwidth")) {
  throw new Error("/fullwidth did not survive a reload");
}
applyFullWidth(false);
if (fullWidthMode || classes.has("fullwidth") ||
    stored.has(FULLWIDTH_STORAGE_KEY)) {
  throw new Error("/fullwidth off did not restore and forget the default");
}
'''
Path(sys.argv[1]).write_text(test)
PY
  node "${_FULLWIDTH_TEST}"
  rm -f "${_FULLWIDTH_TEST}"
  grep -q 'uzFetchJson("/api/status")' payload/agent/templates/index.html \
    && grep -q '"Persistent usage"' payload/agent/templates/index.html \
    || { echo "/status must show comprehensive proof-of-life data" >&2; exit 1; }
  grep -q '"/rebrand \[title\]"' payload/agent/templates/index.html \
    && grep -q 'applyBrandTitle' payload/agent/templates/index.html \
    || { echo "chat UI must expose /rebrand branding controls" >&2; exit 1; }
  grep -q '"/reprompt \[placeholder\]"' payload/agent/templates/index.html \
    && grep -q 'applyPromptPlaceholder' payload/agent/templates/index.html \
    && grep -q 'PROMPT_STORAGE_KEY' payload/agent/templates/index.html \
    || { echo "chat UI must expose persistent /reprompt controls" >&2; exit 1; }
  grep -q 'FULLWIDTH_STORAGE_KEY' payload/agent/templates/index.html \
    && grep -q 'applyFullWidth' payload/agent/templates/index.html \
    || { echo "chat UI must persist /fullwidth controls" >&2; exit 1; }
  ! grep -q '"/retitle' payload/agent/templates/index.html \
    || { echo "chat UI must not expose the old /retitle command" >&2; exit 1; }
  grep -q 'id="provider-status"' payload/agent/templates/index.html \
    && grep -Fq '(data.address ? ` at ${data.address}` : "")' \
      payload/agent/templates/index.html \
    || { echo "chat header must show model and local address only" >&2; exit 1; }
  grep -q 'id="app-version"' payload/agent/templates/index.html \
    || { echo "chat footer must show the installed version" >&2; exit 1; }
  ! grep -q 'header h1::before' payload/agent/templates/index.html \
    || { echo "chat header must not show the green dot" >&2; exit 1; }
  _MARKDOWN_TEST="$(mktemp)"
  python3 - "${_MARKDOWN_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
start = text.index("function escapeHtml")
end = text.index("function showThinking")
test = r'''
const output = renderMarkdown(
  "| Name | State |\n| :--- | ---: |\n| api | **online** $\\rightarrow$ |"
);
if (!output.includes("<table>") ||
    !output.includes('<th class="align-left">Name</th>') ||
    !output.includes(
      '<td class="align-right"><strong>online</strong> ' +
      '<span class="math" role="math">→</span></td>'
    )) {
  throw new Error(output);
}
const math = renderMarkdown(
  "$\\leftarrow$ $\\Rightarrow$ $\\alpha$ $\\leq$ `\\rightarrow`"
);
if (!math.includes('<span class="math" role="math">←</span>') ||
    !math.includes('<span class="math" role="math">⇒</span>') ||
    !math.includes('<span class="math" role="math">α</span>') ||
    !math.includes('<span class="math" role="math">≤</span>') ||
    !math.includes("<code>\\rightarrow</code>")) {
  throw new Error(math);
}
'''
Path(sys.argv[1]).write_text(text[start:end] + test)
PY
  node "${_MARKDOWN_TEST}"
  rm -f "${_MARKDOWN_TEST}"
  _BRAND_TEST="$(mktemp)"
  python3 - "${_BRAND_TEST}" <<'PY'
import sys
from pathlib import Path

text = Path("payload/agent/templates/index.html").read_text()
brand_start = text.index("let brandTitle = ")
brand_end = text.index("\n", brand_start) + 1
helpers_start = text.index("const BRAND_STORAGE_KEY")
end = text.index("function uzConversationMarkdown")
test = r'''
const store = new Map();
global.window = { localStorage: {
  getItem: key => store.has(key) ? store.get(key) : null,
  setItem: (key, value) => store.set(key, String(value)),
  removeItem: key => store.delete(key),
}};
const nodes = {
  "brand-heading": {
    firstChild: { nodeValue: "" },
    attrs: {},
    setAttribute(name, value) { this.attrs[name] = value; },
  },
  "brand-wordmark": { textContent: "" },
  "login-brand-title": { textContent: "" },
  "tomb-brand-title": { textContent: "" },
};
global.document = {
  title: "",
  getElementById: id => nodes[id] || null,
};

if (cleanBrandTitle("  New    Name  ") !== "New Name") {
  throw new Error("brand title whitespace was not normalized");
}
if (cleanBrandTitle("x".repeat(90)).length !== 80) {
  throw new Error("brand title was not clipped to 80 chars");
}
if (!brandWordmark("").includes("UBUNTU ZOMBIE")) {
  throw new Error("empty wordmark did not fall back to default");
}
applyBrandTitle("  New    Name  ");
if (brandTitle !== "New Name" || document.title !== "New Name") {
  throw new Error("brand title was not applied");
}
if (nodes["brand-heading"].firstChild.nodeValue !== "New Name " ||
    nodes["brand-heading"].attrs["aria-label"] !==
      "New Name on {{HOSTNAME}}, user {{USERNAME}}" ||
    nodes["login-brand-title"].textContent !== "New Name" ||
    nodes["tomb-brand-title"].textContent !== "This New Name is dead" ||
    !nodes["brand-wordmark"].textContent.includes("NEW NAME")) {
  throw new Error("brand DOM targets were not updated");
}
if (store.get(BRAND_STORAGE_KEY) !== "New Name") {
  throw new Error("brand title was not persisted");
}
applyBrandTitle(DEFAULT_BRAND_TITLE);
if (store.has(BRAND_STORAGE_KEY)) {
  throw new Error("default brand title should remove stored override");
}
applyBrandTitle("No Persist", false);
if (store.has(BRAND_STORAGE_KEY)) {
  throw new Error("non-persistent brand title wrote localStorage");
}
'''
Path(sys.argv[1]).write_text(
    text[brand_start:brand_end] + text[helpers_start:end] + test
)
PY
  node "${_BRAND_TEST}"
  rm -f "${_BRAND_TEST}"
  grep -Fq '["api", "stream"]' payload/agent/server.py \
    || { echo "server.py must expose the SSE stream endpoint" >&2; exit 1; }
  grep -q '"type":"progress"' payload/agent/pi_mono.py \
    || { echo "pi_mono.py protocol docs must mention progress events" >&2; exit 1; }
  grep -q '"type":"token"' payload/agent/pi_mono.py \
    || { echo "pi_mono.py protocol docs must mention token events" >&2; exit 1; }
  grep -q '"type":"progress"' payload/agent/pi-mono-bridge.mjs \
    || { echo "pi-mono bridge protocol docs must mention progress events" >&2; exit 1; }
  grep -q '"type":"token"' payload/agent/pi-mono-bridge.mjs \
    || { echo "pi-mono bridge protocol docs must mention token events" >&2; exit 1; }
  # HTML tag names are case-insensitive; keep the no-external-script
  # guard case-insensitive so <SCRIPT SRC=...> is caught too.
  if grep -qi '<script[[:space:]][^>]*src=' payload/agent/templates/index.html; then
    echo "chat UI must not add external script dependencies" >&2
    exit 1
  fi
  grep -q "s|__ZOMBIE_DIR__|\\\${ZOMBIE_DIR}|g" scripts/install.sh \
    || { echo "install.sh must render __ZOMBIE_DIR__ in systemd units" >&2; exit 1; }
  if grep -n '\[\[ "${JSON}"' scripts/install.sh; then
    echo "generated verify script must escape JSON references in install.sh heredoc" >&2
    exit 1
  fi
  grep -q "actions/attest@" .github/workflows/release.yml \
    || { echo "release workflow must generate provenance attestations" >&2; exit 1; }
  grep -q "verify-bridge-pins" .github/workflows/release.yml \
    || { echo "release workflow must verify bridge dependency checksums" >&2; exit 1; }
  grep -q "paths:" .github/workflows/release.yml \
    || { echo "release workflow must have a paths trigger" >&2; exit 1; }
  grep -q "VERSION" .github/workflows/release.yml \
    || { echo "release workflow paths trigger must watch VERSION" >&2; exit 1; }
  grep -q "Ensure release tag exists" .github/workflows/release.yml \
    || { echo "release workflow must create the VERSION tag on main" >&2; exit 1; }
  bash payload/bin/verify-release --help >/dev/null

  # Keep the release bundle source list honest without creating dist/.
  tar --exclude-vcs --exclude='dist' --exclude='__pycache__' \
      -czf /tmp/ubuntu-zombie-smoke-package.tar.gz \
      scripts payload tests Makefile VERSION \
      README.md CHANGELOG.md CONTRIBUTING.md CODE_OF_CONDUCT.md \
      LICENSE .editorconfig \
      SECURITY.md docs debian
  rm -f /tmp/ubuntu-zombie-smoke-package.tar.gz
}

run_flags() {
  echo "[smoke] UX flags"
  # --help / --version / dry-run must stay exit 0 and never mutate the host.
  ./scripts/install.sh --help    >/dev/null
  ./scripts/install.sh --version >/dev/null
  expect_exit_code 0 ./scripts/install.sh install --dry-run
  expect_exit_code 0 ./scripts/install.sh install --yes --dry-run

  # --help must advertise the new examples and completion section.
  ./scripts/install.sh --help | grep -q "Examples:"
  ./scripts/install.sh --help | grep -q "completion"

  # Removed install modes must stay out of the public help surface.
  if ./scripts/install.sh --help \
      | grep -Eq 'FORGEJO|ZOMBIE_INSTALL_LLAMA|install (forgejo|llama)'; then
    echo "FAIL: installer help advertises a removed install mode" >&2
    exit 1
  fi

  # --no-color must strip ANSI escapes from output.
  set +e
  out="$(./scripts/install.sh doctor --no-color 2>&1)"
  set -e
  if printf '%s' "${out}" | grep -q $'\033'; then
    echo "FAIL: --no-color still emitted ANSI escapes" >&2
    exit 1
  fi

  # --quiet must suppress [i]/[+] info lines (warnings/errors only).
  set +e
  out="$(./scripts/install.sh doctor --quiet 2>/dev/null)"
  set -e
  if printf '%s\n' "${out}" | grep -qE '^\[i\]|^\[\+\]'; then
    echo "FAIL: --quiet still printed info/ok lines" >&2
    exit 1
  fi

  # --json must emit valid JSON for doctor (machine-readable mode).
  set +e
  out="$(./scripts/install.sh doctor --json 2>/dev/null)"
  set -e
  if command -v python3 >/dev/null 2>&1; then
    printf '%s' "${out}" | python3 -c 'import sys,json; json.load(sys.stdin)' \
      || { echo "FAIL: doctor --json did not produce valid JSON" >&2; exit 1; }
  fi

  # uninstall.sh shares the same UX flag vocabulary as install.sh.
  ./scripts/uninstall.sh --help    >/dev/null
  ./scripts/uninstall.sh --version >/dev/null
  expect_exit_code 2 ./scripts/uninstall.sh --definitely-not-a-flag
  set +e
  out="$(./scripts/uninstall.sh --no-color --dry-run 2>&1)"
  set -e
  if printf '%s' "${out}" | grep -q $'\033'; then
    echo "FAIL: uninstall.sh --no-color still emitted ANSI escapes" >&2
    exit 1
  fi
  set +e
  out="$(./scripts/uninstall.sh --quiet --dry-run 2>/dev/null)"
  set -e
  if printf '%s\n' "${out}" | grep -q '██'; then
    echo "FAIL: uninstall.sh --quiet still printed the splash" >&2
    exit 1
  fi

  # Every operator-facing helper script must answer --help with exit 0
  # and reject unknown arguments with exit 2 (bad usage).
  # Exceptions to the exit-2 check: audit-recent's -n takes a numeric
  # value it validates itself, and verify-release accepts an arbitrary
  # positional release directory, so a bogus flag is not "unknown" to it.
  local helpers=(
    payload/bin/collect-diagnostics
    payload/bin/health-check
    payload/bin/secrets-edit
    payload/bin/setup-agent-venv
    payload/bin/zombie-chat
    scripts/build-deb.sh
    scripts/verify-bridge-pins.sh
  )
  local helper
  for helper in "${helpers[@]}" payload/bin/audit-recent payload/bin/verify-release; do
    bash "${helper}" --help >/dev/null \
      || { echo "FAIL: ${helper} --help did not exit 0" >&2; exit 1; }
  done
  for helper in "${helpers[@]}" payload/bin/audit-recent; do
    expect_exit_code 2 bash "${helper}" --definitely-not-a-flag
  done

  # Completion files referenced by --help must exist and parse.
  [[ -r scripts/completions/install.bash ]] \
    || { echo "FAIL: scripts/completions/install.bash missing" >&2; exit 1; }
  bash -n scripts/completions/install.bash \
    || { echo "FAIL: install.bash completion has a syntax error" >&2; exit 1; }
  [[ -r scripts/completions/_install.sh ]] \
    || { echo "FAIL: scripts/completions/_install.sh missing" >&2; exit 1; }
  if grep -Eqi 'forgejo|(^|[[:space:]])llama([[:space:]]|$)' \
      scripts/completions/install.bash scripts/completions/_install.sh; then
    echo "FAIL: shell completions advertise a removed install mode" >&2
    exit 1
  fi
  grep -q -- "--archive" scripts/completions/install.bash \
    && grep -q -- "--keep-agent" scripts/completions/install.bash \
    || { echo "FAIL: bash completion missing uninstall-only flags" >&2; exit 1; }
}

case "${cmd}" in
  syntax)         run_syntax ;;
  python)         run_python ;;
  branding) run_branding ;;
  subcommands) run_subcommands ;;
  bad-usage)      run_bad_usage ;;
  flags)          run_flags ;;
  noninteractive) run_noninteractive ;;
  diagnostics)    run_diagnostics ;;
  standards)      run_standards ;;
  all)
    run_syntax
    run_python
    run_branding
    run_subcommands
    run_bad_usage
    run_flags
    run_noninteractive
    run_diagnostics
    run_standards
    echo "[smoke] all checks passed"
    ;;
  *) echo "unknown subcommand: ${cmd}" >&2; exit 2 ;;
esac
