"""Time-to-live (TTL) kill switch for Ubuntu AI System Administrator.

Ubuntu AI System Administrator is a privileged, root-capable
account. To bound the window in which it can act, a fresh install is
given a *Time to Live*: a future moment after which the AI System Administrator is
permanently disabled. Two events trip the kill switch:

* the TTL elapses (``status`` notices ``now >= expires_at``); or
* the operator runs ``/ttl --die`` (or ``lifecycle.py die``).

Once tripped, the state is a tombstone: the ``dead`` flag is written to
disk and never cleared at runtime, so a restart of the chat service
cannot reactivate the AI System Administrator. Routine reinstalls preserve the tombstone;
only an explicit ``initialize`` call resets the lifecycle.

State lives in a small JSON file
(``$AI_SYS_ADMIN_DIR/state/lifecycle.json`` by default, overridable with
``AI_SYS_ADMIN_LIFECYCLE_STATE``)::

    {
      "created_at": 1700000000.0,
      "expires_at": 1700259200.0,
      "dead": false,
      "dead_reason": null,
      "dead_at": null
    }

The ``/ttl N`` chat command extends the Time to Live by ``N`` days from
the current expiry (or from now, whichever is later), so issuing
``/ttl 5`` while four days remain leaves nine days on the clock.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

_INSTALL_ROOT = Path(os.environ.get("AI_SYS_ADMIN_DIR", "/opt/ai-system-administrator"))
STATE_PATH = Path(os.environ.get(
    "AI_SYS_ADMIN_LIFECYCLE_STATE",
    str(_INSTALL_ROOT / "state" / "lifecycle.json"),
))

DAY_SECONDS = 86_400
DEFAULT_TTL_SECONDS = 7 * DAY_SECONDS
_DURATION_UNITS = {
    "s": 1,
    "sec": 1,
    "second": 1,
    "m": 60,
    "min": 60,
    "minute": 60,
    "h": 3_600,
    "hr": 3_600,
    "hour": 3_600,
    "d": DAY_SECONDS,
    "day": DAY_SECONDS,
    "w": 7 * DAY_SECONDS,
    "week": 7 * DAY_SECONDS,
    "mo": 30 * DAY_SECONDS,
    "month": 30 * DAY_SECONDS,
    "y": 365 * DAY_SECONDS,
    "yr": 365 * DAY_SECONDS,
    "year": 365 * DAY_SECONDS,
}


def _now() -> float:
    return time.time()


def _state_path() -> Path:
    # Re-read the env var each call so tests can point at a temp file.
    return Path(
        os.environ.get("AI_SYS_ADMIN_LIFECYCLE_STATE", str(STATE_PATH))
    )


def _load_raw() -> dict[str, Any]:
    try:
        data = json.loads(_state_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_raw(data: dict[str, Any]) -> None:
    path = _state_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)
    # The lifecycle file is not a secret, but keep it owner-only so a
    # non-privileged local user cannot edit the expiry to keep the AI
    # System Administrator active past its TTL.
    try:
        os.chmod(path, 0o600)
    except OSError:  # pragma: no cover - best effort on odd filesystems
        pass


def format_remaining(seconds: float) -> str:
    """Render a duration as ``D days H hours M minutes S seconds``.

    Negative inputs clamp to zero. Units are always present (even when
    zero) so the countdown reads consistently, and each unit is
    singularised when its value is exactly one.
    """
    total = int(max(0, seconds))
    days, rem = divmod(total, DAY_SECONDS)
    hours, rem = divmod(rem, 3_600)
    minutes, secs = divmod(rem, 60)
    parts = [
        (days, "day"),
        (hours, "hour"),
        (minutes, "minute"),
        (secs, "second"),
    ]
    return " ".join(
        f"{value} {unit if value == 1 else unit + 's'}" for value, unit in parts
    )


def parse_duration(text: str, *, default_seconds: float | None = None) -> float:
    """Parse a human duration such as ``14 days`` or ``2 years 3 months``.

    Singular/plural units are accepted. Months and years are fixed
    operator-facing approximations: 30 and 365 days respectively.
    """
    value = " ".join(text.replace(",", " ").split())
    if not value:
        if default_seconds is None:
            raise ValueError("duration is required")
        if default_seconds <= 0:
            raise ValueError("duration must be greater than zero")
        return float(default_seconds)
    tokens = value.split(" ")
    if len(tokens) == 1:
        try:
            days = float(tokens[0])
        except ValueError as exc:
            raise ValueError("duration must be '<number> <unit>' pairs") from exc
        if days <= 0:
            raise ValueError("duration must be greater than zero")
        return days * DAY_SECONDS
    if len(tokens) % 2:
        raise ValueError("duration must be '<number> <unit>' pairs")
    total = 0.0
    for idx in range(0, len(tokens), 2):
        raw_amount = tokens[idx]
        raw_unit = tokens[idx + 1].lower()
        try:
            amount = float(raw_amount)
        except ValueError as exc:
            raise ValueError(f"bad duration amount: {raw_amount}") from exc
        stripped = raw_unit[:-1] if raw_unit.endswith("s") else raw_unit
        # Prefer the plural-stripped form, but fall back to the raw
        # token so the bare unit "s" (seconds) is not stripped to "".
        seconds = _DURATION_UNITS.get(stripped)
        if seconds is None:
            seconds = _DURATION_UNITS.get(raw_unit)
        if seconds is None:
            raise ValueError(f"bad duration unit: {raw_unit}")
        total += amount * seconds
    if total <= 0:
        raise ValueError("duration must be greater than zero")
    return total


def _mark_dead(reason: str, data: dict[str, Any] | None = None) -> dict[str, Any]:
    if data is None:
        data = _load_raw()
    if not data.get("dead"):
        data["dead"] = True
        data["dead_reason"] = reason
        data["dead_at"] = _now()
        _save_raw(data)
    return data


def status() -> dict[str, Any]:
    """Return the current lifecycle status, tripping the kill switch on expiry.

    This is the single read path the chat service consults before doing
    anything privileged. If the TTL has elapsed it writes the tombstone
    *before* returning so the ``dead`` decision is durable.
    """
    data = _load_raw()
    dead = bool(data.get("dead"))
    expires_at = data.get("expires_at")
    created_at = data.get("created_at")
    reason = data.get("dead_reason")
    configured = dead or isinstance(expires_at, (int, float))
    now = _now()

    if not dead and isinstance(expires_at, (int, float)) and now >= expires_at:
        _mark_dead("expired", data)
        dead = True
        reason = "expired"

    remaining = 0.0
    if not dead and isinstance(expires_at, (int, float)):
        remaining = max(0.0, expires_at - now)

    return {
        "alive": not dead,
        "dead": dead,
        "dead_reason": reason,
        "dead_at": data.get("dead_at"),
        "configured": configured,
        "created_at": created_at,
        "expires_at": expires_at if isinstance(expires_at, (int, float)) else None,
        "remaining_seconds": int(remaining),
        "remaining_human": "0 seconds" if dead else format_remaining(remaining),
    }


def set_ttl(days: float) -> dict[str, Any]:
    """Extend the Time to Live by ``days`` days and return the new status.

    The extension is measured from the later of *now* or the current
    expiry, so it never shortens an existing countdown. A disabled administrator
    cannot be revived: the returned status keeps ``dead`` true and the
    expiry is left untouched.
    """
    return set_ttl_seconds(days * DAY_SECONDS)


def set_ttl_seconds(seconds: float) -> dict[str, Any]:
    """Extend the Time to Live by ``seconds`` and return the new status."""
    if seconds <= 0:
        raise ValueError("duration must be greater than zero")
    current = status()
    if current["dead"]:
        return current
    data = _load_raw()
    now = _now()
    base = data.get("expires_at")
    if not isinstance(base, (int, float)) or base < now:
        base = now
    data["expires_at"] = base + seconds
    data.setdefault("created_at", now)
    data.setdefault("dead", False)
    _save_raw(data)
    return status()


def reset_ttl_seconds(seconds: float = DEFAULT_TTL_SECONDS) -> dict[str, Any]:
    """Reset the Time to Live to ``seconds`` from now."""
    if seconds <= 0:
        raise ValueError("duration must be greater than zero")
    current = status()
    if current["dead"]:
        return current
    data = _load_raw()
    now = _now()
    data["expires_at"] = now + seconds
    data.setdefault("created_at", now)
    data.setdefault("dead", False)
    _save_raw(data)
    return status()


def kill(reason: str = "killed") -> dict[str, Any]:
    """Trip the kill switch immediately and permanently."""
    _mark_dead(reason)
    return status()


def initialize(days: float) -> dict[str, Any]:
    """Create (or reset) the lifecycle state with a fresh ``days``-day TTL.

    Called by the installer only when no valid lifecycle state exists.
    This is the only path that clears a tombstone.
    """
    if days <= 0:
        raise ValueError("days must be greater than zero")
    now = _now()
    _save_raw(
        {
            "created_at": now,
            "expires_at": now + days * DAY_SECONDS,
            "dead": False,
            "dead_reason": None,
            "dead_at": None,
        }
    )
    return status()


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(
        description="Manage the Ubuntu AI System Administrator time-to-live kill switch."
    )
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init", help="Create/reset state with a fresh TTL.")
    p_init.add_argument("--days", type=float, required=True)

    p_set = sub.add_parser("set", help="Extend the TTL by N days.")
    p_set.add_argument("--days", type=float, required=True)

    sub.add_parser("die", help="Permanently disable the AI System Administrator now.")
    sub.add_parser("status", help="Print the current lifecycle status.")

    args = parser.parse_args(argv)
    try:
        if args.cmd == "init":
            result = initialize(args.days)
        elif args.cmd == "set":
            result = set_ttl(args.days)
        elif args.cmd == "die":
            result = kill()
        else:
            result = status()
    except ValueError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - parser.error raises SystemExit

    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
