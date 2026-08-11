"""Root logrotate helper for the owner-configured audit retention window."""

from __future__ import annotations

import os
import sqlite3
import stat
import time
from pathlib import Path
from urllib.parse import quote

DATABASE_PATH = Path("/var/lib/imaginary-friend/friend.db")
LOG_ROOT = Path("/var/log/imaginary-friend")


def _retention_days(database_path: Path) -> int:
    details = database_path.lstat()
    if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
        raise ValueError("Friend database is not one regular file.")
    uri = f"file:{quote(str(database_path), safe='/')}?mode=ro"
    connection = sqlite3.connect(uri, uri=True, timeout=5)
    try:
        row = connection.execute(
            "SELECT audit_retention_days FROM settings WHERE singleton = 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None or isinstance(row[0], bool):
        raise ValueError("Friend audit retention setting is missing.")
    days = int(row[0])
    if not 30 <= days <= 3650:
        raise ValueError("Friend audit retention setting is invalid.")
    return days


def prune_rotated_audit(
    database_path: Path = DATABASE_PATH,
    log_root: Path = LOG_ROOT,
    *,
    now: float | None = None,
) -> list[Path]:
    """Remove only expired, regular ``audit.log.*`` rotation files."""
    root_details = log_root.lstat()
    if not stat.S_ISDIR(root_details.st_mode) or stat.S_ISLNK(root_details.st_mode):
        raise ValueError("Friend log root is not a real directory.")
    cutoff = (time.time() if now is None else now) - _retention_days(
        database_path
    ) * 86_400
    removed: list[Path] = []
    for path in log_root.iterdir():
        if not path.name.startswith("audit.log."):
            continue
        details = path.lstat()
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_nlink != 1
            or stat.S_IMODE(details.st_mode) & 0o022
        ):
            raise ValueError(f"Unsafe Friend audit rotation: {path.name}")
        if details.st_mtime < cutoff:
            path.unlink()
            removed.append(path)
    return removed


def main() -> int:
    if os.geteuid() != 0:
        raise SystemExit("Friend audit retention must run as root.")
    prune_rotated_audit()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
