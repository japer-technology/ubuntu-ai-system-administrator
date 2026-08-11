"""Python client for the ``pi-mono`` bridge.

The chat service drives the ``pi`` agent loop
(``@earendil-works/pi-coding-agent``) instead of parsing fenced-bash
proposals. ``pi`` runs as a Node subprocess wrapped by
``pi-mono-bridge.mjs`` and speaks a small line-delimited JSON protocol
over stdio so the Python server can mediate every tool call through
the closed registry in ``tools.py``.

Protocol (Python ↔ bridge, one JSON object per line):

* ``{"type":"start", "prompt": str, "system": str, "history": [...],
     "tools": [...], "settings_path": str, "log_path": str,
     "max_tool_calls": int, "idle_timeout_seconds": float,
     "provider": str, "model": str}`` —
  Python → bridge. ``provider`` (a pi-ai/``pi`` provider id such as
  ``openai`` or ``google``) and ``model`` are resolved from
  ``providers`` so the agent loop and chat surface select the same
  model; either may be ``""`` when no provider is configured, in which
  case the bridge omits the corresponding ``pi`` CLI flag.
* ``{"type":"tool_call", "id": str, "name": str, "args": {...}}`` —
  bridge → Python (one or more)
* ``{"type":"tool_result", "id": str, "ok": bool, "result"|"error":
     ...}`` — Python → bridge
* ``{"type":"final", "text": str}`` — bridge → Python (terminates)
* ``{"type":"error", "message": str}`` — bridge → Python (terminates)
* ``{"type":"progress", "kind": "tool_start"|"tool_end", "name": str,
     "id": str}`` — bridge → Python (optional live progress)
* ``{"type":"token", "delta": str}`` — bridge → Python (optional
  assistant text delta)

The bridge handles the actual ``pi --mode rpc`` (or ``--mode json``)
plumbing, including ``--no-builtin-tools`` and ``--tools <names>``
flags, system-prompt rendering, and per-turn session management.

For development and CI, ``ZOMBIE_PI_MONO_BRIDGE`` may point at any
executable that speaks this protocol — including the stub script
``tests/fixtures/stub-pi-mono.mjs`` used by ``smoke.sh``.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Iterable

import providers

HERE = Path(__file__).resolve().parent

DEFAULT_BRIDGE = HERE / "pi-mono-bridge.mjs"
DEFAULT_LOG_DIR = Path(os.environ.get(
    "ZOMBIE_PI_MONO_LOG_DIR", "/opt/ai-zombie/state/logs"))
DEFAULT_SETTINGS_PATH = Path(os.environ.get(
    "ZOMBIE_PI_MONO_SETTINGS", "/opt/ai-zombie/pi/settings.json"))

# Per-turn idle deadline (seconds). If the bridge produces no event for
# this long the turn is presumed wedged — a hung provider socket, a pi
# child stuck mid-stream, or a bridge that never emits ``final`` — and
# the subprocess is killed so the chat surfaces a clean error instead of
# hanging the operator's request forever. This is an *idle* deadline:
# every bridge event (and every operator-mediated tool result) resets it,
# so a generous value does not slow active turns. It is the innermost of
# three layered deadlines and the smallest, so it fires first with a
# clean error (Python < bridge ZOMBIE_PI_MONO_IDLE_TIMEOUT < client
# CLIENT_TURN_TIMEOUT_MS). ``0`` disables the watchdog.
DEFAULT_TURN_TIMEOUT = 86400.0


class BridgeError(RuntimeError):
    """Raised when the pi-mono bridge cannot be started or produces
    malformed output."""


def _bridge_argv() -> list[str]:
    explicit = os.environ.get("ZOMBIE_PI_MONO_BRIDGE")
    if explicit:
        # Allow either a bare script path or a full argv string.
        parts = explicit.split()
        if len(parts) == 1 and parts[0].endswith((".mjs", ".js", ".cjs")):
            return ["node", parts[0]]
        return parts
    node = shutil.which("node")
    if node is None:
        raise BridgeError(
            "Cannot run pi-mono: 'node' not on PATH. Install Node.js >=22 "
            "or set ZOMBIE_PI_MONO_BRIDGE to point at a stub."
        )
    if not DEFAULT_BRIDGE.exists():
        raise BridgeError(f"Bridge script missing: {DEFAULT_BRIDGE}")
    return [node, str(DEFAULT_BRIDGE)]


def _log_path() -> Path:
    DEFAULT_LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y%m%dT%H%M%S", time.localtime())
    return DEFAULT_LOG_DIR / f"pi-mono.{ts}.{os.getpid()}.log"


def _env_float(name: str, default: float) -> float:
    """Best-effort float from the environment; ``default`` on any error."""
    raw = os.environ.get(name)
    if raw is None or raw == "":
        return default
    try:
        return float(raw)
    except (TypeError, ValueError):
        return default


ToolCallback = Callable[[str, str, dict[str, Any]], dict[str, Any]]
"""Signature: callback(tool_call_id, tool_name, args) -> {"ok": bool,
"result"|"error": ...}."""


def run_turn(
    *,
    prompt: str,
    system_prompt: str,
    history: Iterable[dict[str, Any]],
    on_tool_call: ToolCallback,
    tool_names: Iterable[str],
    max_tool_calls: int = 1000,
    settings_path: Path | str | None = None,
    timeout: float | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
    cancel_event: threading.Event | None = None,
) -> dict[str, Any]:
    """Run one pi-mono turn.

    Returns ``{"final": str, "events": [...]}`` where ``events`` is the
    full list of bridge-emitted events (tool_call + tool_result echoes,
    in order).

    ``timeout`` is a per-turn *idle* deadline in seconds: if the bridge
    emits no event (and we are not waiting on an operator-mediated tool
    result) for ``timeout`` seconds, the subprocess is terminated and a
    :class:`BridgeError` is raised so the caller can report a clean
    error rather than blocking the operator forever. ``None`` falls back
    to ``ZOMBIE_PI_MONO_TIMEOUT`` then :data:`DEFAULT_TURN_TIMEOUT`; a
    non-positive value disables the watchdog.

    ``on_event`` receives optional ``token`` and ``progress`` bridge
    events as they arrive. The callback is best-effort: exceptions are
    swallowed so UI streaming can never break the turn.
    """
    argv = _bridge_argv()
    log = _log_path()
    settings = str(settings_path or DEFAULT_SETTINGS_PATH)
    env = dict(os.environ)
    env.setdefault("PI_MONO_LOG", str(log))

    if timeout is None:
        timeout = _env_float("ZOMBIE_PI_MONO_TIMEOUT", DEFAULT_TURN_TIMEOUT)

    # Single source of truth for model + auth. Resolve the active
    # provider from /opt/ai-zombie/secrets/env via the shared registry
    # in ``providers`` and pass the result to the bridge so the ``pi``
    # CLI selects the same model the chat banner advertises — rather
    # than falling back to pi's own default (``google``) or its native
    # ``~/.pi`` config. Resolution is best-effort: if nothing is
    # configured we leave the env untouched and let ``pi`` resolve
    # credentials itself (e.g. an OAuth subscription set up via
    # ``pi /login``), preserving existing behaviour.
    pi_provider = ""
    model_id = ""
    active_key_env = ""
    try:
        active = providers.provider_from_env()
    except providers.NoProviderConfigured:
        active = None
    if active is not None:
        pi_provider = active.pi_provider
        model_id = active.model
        active_key_env = active.key_env
        # Forward only the active provider's key; strip the others so
        # the ``pi`` CLI cannot authenticate against — or log — an
        # unrelated provider. Mirrors providers._bridge_env isolation.
        for key_env in providers.ALL_KEY_ENVS:
            if key_env != active_key_env:
                env.pop(key_env, None)

    start_msg = {
        "type": "start",
        "prompt": prompt,
        "system": system_prompt,
        "history": list(history),
        "tools": list(tool_names),
        "settings_path": settings,
        "log_path": str(log),
        "max_tool_calls": max_tool_calls,
        "idle_timeout_seconds": timeout,
        "provider": pi_provider,
        "model": model_id,
    }

    proc = subprocess.Popen(
        argv,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        text=True,
        bufsize=1,
    )
    assert proc.stdin is not None and proc.stdout is not None

    # Drain stderr concurrently into a bounded buffer. If it were left
    # unread until EOF (as ``proc.stderr.read()`` alone would do), a
    # chatty bridge could fill the OS pipe buffer, block on its own
    # stderr writes, and stall stdout — deadlocking the turn until the
    # idle watchdog kills it with a misleading timeout.
    stderr_chunks: list[str] = []
    stderr_len = 0

    def _drain_stderr() -> None:
        nonlocal stderr_len
        if proc.stderr is None:
            return
        try:
            for err_line in proc.stderr:
                if stderr_len < 65536:
                    stderr_chunks.append(err_line)
                    stderr_len += len(err_line)
        except (OSError, ValueError):
            pass

    stderr_thread = threading.Thread(
        target=_drain_stderr, name="pi-mono-stderr", daemon=True)
    stderr_thread.start()

    # Idle watchdog: if the bridge produces no event for ``timeout``
    # seconds the turn is presumed wedged and the subprocess is killed.
    # ``readline`` below then returns EOF and we raise a timeout-specific
    # error. ``last_activity`` is refreshed by the read loop after every
    # event (and after each operator-mediated tool result) so a long but
    # *active* turn — many tool calls — is never killed prematurely.
    timed_out = threading.Event()
    cancelled = threading.Event()
    stop_watchdog = threading.Event()
    # Set while a tool callback is running. The callback can block for a
    # long time waiting on the operator approval gate, and that wait is
    # activity, not idleness — refreshing ``last_activity`` only *after*
    # the callback returns would let the watchdog kill the bridge in the
    # middle of a pending approval.
    tool_in_flight = threading.Event()
    activity_lock = threading.Lock()
    last_activity = time.monotonic()

    def _touch() -> None:
        nonlocal last_activity
        with activity_lock:
            last_activity = time.monotonic()

    def _watchdog() -> None:
        while not stop_watchdog.wait(0.5):
            # An explicit operator stop wins if it races the idle deadline.
            if cancel_event is not None and cancel_event.is_set():
                cancelled.set()
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return
            # A non-positive timeout disables the idle deadline. The
            # watchdog still runs when an operator stop is possible, so
            # the check has to be repeated here and not only at start-up.
            if not timeout or timeout <= 0:
                continue
            if tool_in_flight.is_set():
                continue
            with activity_lock:
                idle = time.monotonic() - last_activity
            if idle >= timeout:
                timed_out.set()
                try:
                    proc.kill()
                except ProcessLookupError:
                    pass
                return

    watchdog: threading.Thread | None = None
    if (timeout and timeout > 0) or cancel_event is not None:
        watchdog = threading.Thread(
            target=_watchdog, name="pi-mono-watchdog", daemon=True)
        watchdog.start()

    events: list[dict[str, Any]] = []
    final_text = ""
    try:
        proc.stdin.write(json.dumps(start_msg, ensure_ascii=False) + "\n")
        proc.stdin.flush()

        calls_made = 0
        while True:
            line = proc.stdout.readline()
            if not line:
                if cancelled.is_set():
                    raise BridgeError("pi-mono turn was stopped by the operator")
                if timed_out.is_set():
                    raise BridgeError(
                        f"pi-mono turn timed out after {timeout:.0f}s of "
                        f"inactivity and was terminated. The model or "
                        f"provider stopped responding; try again or check "
                        f"the provider configuration."
                    )
                # Bridge exited; capture stderr for diagnostics.
                stderr_thread.join(timeout=2)
                err = "".join(stderr_chunks)
                raise BridgeError(
                    f"pi-mono bridge exited without 'final'. stderr:\n{err[-2000:]}"
                )
            _touch()
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError as exc:
                raise BridgeError(f"Malformed bridge event: {exc}: {line!r}") from exc
            kind = event.get("type")
            events.append(event)
            if kind in {"token", "progress"} and on_event is not None:
                try:
                    on_event(event)
                except Exception as exc:  # noqa: BLE001
                    print(
                        f"pi_mono on_event callback failed: {exc.__class__.__name__}: {exc}",
                        file=sys.stderr,
                    )
                    pass
            if kind == "tool_call":
                calls_made += 1
                if calls_made > max_tool_calls:
                    # Synthetic ``budget_exceeded`` observation so the
                    # model closes the turn instead of looping. Mirrors
                    # the elevated-budget enforcement in ``server.py``.
                    reply = {"type": "tool_result", "id": event.get("id"),
                             "ok": False,
                             "error": (f"budget_exceeded: per-turn tool-call "
                                       f"budget reached ({max_tool_calls}); "
                                       f"end the turn and summarise.")}
                else:
                    tool_in_flight.set()
                    try:
                        result = on_tool_call(
                            str(event.get("id") or uuid.uuid4().hex),
                            str(event.get("name") or ""),
                            dict(event.get("args") or {}),
                        )
                        if not isinstance(result, dict):
                            raise BridgeError(
                                "tool callback returned "
                                f"{type(result).__name__}, expected dict"
                            )
                    except Exception as exc:  # noqa: BLE001
                        result = {"ok": False, "error": f"{exc.__class__.__name__}: {exc}"}
                    finally:
                        tool_in_flight.clear()
                    reply = {"type": "tool_result", "id": event.get("id"), **result}
                # Executing a tool (or waiting on the operator gate) is
                # activity, not idleness — refresh the deadline before we
                # block again on the next bridge event.
                _touch()
                proc.stdin.write(json.dumps(reply, ensure_ascii=False) + "\n")
                proc.stdin.flush()
            elif kind == "final":
                final_text = str(event.get("text") or "")
                break
            elif kind == "error":
                raise BridgeError(str(event.get("message") or "bridge error"))
            else:
                # Unknown event type — record and continue. Bridges may
                # emit progress hints we do not yet interpret.
                continue
    finally:
        stop_watchdog.set()
        try:
            if proc.stdin:
                proc.stdin.close()
        except OSError:
            pass
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)
        if watchdog is not None:
            watchdog.join(timeout=2)
        stderr_thread.join(timeout=2)

    return {"final": final_text, "events": events, "log_path": str(log)}


def render_settings(*, tool_names_list: Iterable[str]) -> dict[str, Any]:
    """Return the structured pi-mono settings object the installer
    writes to ``/opt/ai-zombie/pi/settings.json``."""
    return {
        "mode": "rpc",
        "noBuiltinTools": True,
        "tools": list(tool_names_list),
    }


if __name__ == "__main__":  # pragma: no cover - manual smoke
    print(json.dumps({"bridge": _bridge_argv()}, indent=2))
    sys.exit(0)
