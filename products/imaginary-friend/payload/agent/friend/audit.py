"""Append-only, content-minimising audit records for Imaginary Friend."""

from __future__ import annotations

import json
import os
import re
import stat
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

_TOKEN_PATTERNS = (
    re.compile(r"(?i)\b(password|token|secret|signing[_ -]?key)\s*[:=]\s*\S+"),
    re.compile(r"\bscrypt\$16384\$8\$1\$[0-9a-f]{32}\$[0-9a-f]{64}\b"),
    re.compile(r"\b[A-Za-z0-9_-]{43,86}\b"),
)
_SECRET_FIELD_NAMES = {
    "password",
    "password_hash",
    "owner_password",
    "session_token",
    "token_digest",
    "csrf_token",
    "csrf_digest",
    "signing_key",
    "session_signing_key",
    "provider_key",
}


def redact(value: Any, *, field_name: str = "") -> Any:
    """Redact credential-shaped values recursively before serialization."""
    if field_name.lower() in _SECRET_FIELD_NAMES:
        return "***REDACTED***"
    if isinstance(value, str):
        result = value
        for pattern in _TOKEN_PATTERNS:
            result = pattern.sub("***REDACTED***", result)
        return result
    if isinstance(value, Mapping):
        return {
            str(key): redact(item, field_name=str(key))
            for key, item in value.items()
        }
    if isinstance(value, (list, tuple)):
        return [redact(item) for item in value]
    return value


class AuditLogger:
    """Write one restricted JSON object per line without following symlinks."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._lock = threading.Lock()

    def _open(self) -> int:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | os.O_CLOEXEC
        flags |= getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o640)
        details = os.fstat(fd)
        if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
            os.close(fd)
            raise OSError("audit destination must be one regular file")
        os.fchmod(fd, 0o640)
        return fd

    def event(self, event_type: str, **fields: Any) -> str:
        """Append a redacted runtime event and return its UUID."""
        event_id = str(uuid.uuid4())
        entry: dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "event_id": event_id,
            "product_id": "imaginary-friend",
            "event_type": event_type,
        }
        entry.update(redact(fields))
        line = json.dumps(
            entry,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
        with self._lock:
            fd = self._open()
            try:
                os.write(fd, line)
                os.fsync(fd)
            finally:
                os.close(fd)
        return event_id

