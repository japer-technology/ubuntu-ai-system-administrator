"""Password gate for the Beep chat UI.

The chat service binds to ``127.0.0.1`` only, but on a shared desktop
*every* local user can reach ``http://127.0.0.1:58989``. A password gate
keeps the root-capable administrator behind a product-specific shared
secret. The installer requires a protected password input and stores only
a salted PBKDF2 hash as ``BEEP_ADMIN_PASSWORD_HASH``.

An installed Beep always configures the gate. An unset hash is supported
only by isolated source tests; it is never an installed operating mode.

Hash format (single line, ``$``-separated)::

    pbkdf2_sha256$<iterations>$<salt-hex>$<derived-key-hex>
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets
import stat
import time
from pathlib import Path

HASH_ENV = "BEEP_ADMIN_PASSWORD_HASH"
SESSION_KEY_ENV = "BEEP_SESSION_KEY_FILE"
DEFAULT_SESSION_KEY = "/etc/beep/secrets/session.key"
SESSION_MAX_AGE_SECONDS = 12 * 60 * 60

_ALGO = "pbkdf2_sha256"
_ITERATIONS = 200_000
_SALT_BYTES = 16


def hash_password(
    password: str, *, salt: str | None = None, iterations: int = _ITERATIONS
) -> str:
    """Return a PBKDF2-SHA256 hash string for ``password``."""
    if salt is None:
        salt = secrets.token_hex(_SALT_BYTES)
    derived = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), bytes.fromhex(salt), iterations
    )
    return f"{_ALGO}${iterations}${salt}${derived.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check of ``password`` against a stored hash string."""
    try:
        algo, iterations, salt, digest = stored.split("$", 3)
    except (ValueError, AttributeError):
        return False
    if (
        algo != _ALGO
        or not iterations.isascii()
        or not iterations.isdigit()
        or len(iterations) > 7
        or not 100_000 <= int(iterations) <= 2_000_000
        or len(salt) != _SALT_BYTES * 2
        or len(digest) != hashlib.sha256().digest_size * 2
    ):
        return False
    try:
        candidate = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt), int(iterations)
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(candidate.hex(), digest)


def configured_hash() -> str | None:
    """Return the configured admin password hash, or ``None`` if unset."""
    value = (os.environ.get(HASH_ENV) or "").strip()
    return value or None


def auth_required() -> bool:
    """Installed Beep always requires authentication."""

    return True


def check_password(password: str) -> bool:
    """Validate ``password`` and fail closed when configuration is absent."""
    stored = configured_hash()
    if stored is None:
        return False
    return verify_password(password, stored)


def valid_password_hash(stored: str | None) -> bool:
    """Return whether ``stored`` has Beep's bounded PBKDF2 format."""

    return bool(stored) and _hash_fields_valid(stored)


def _hash_fields_valid(stored: str) -> bool:
    try:
        algo, iterations, salt, digest = stored.split("$", 3)
        bytes.fromhex(salt)
        bytes.fromhex(digest)
    except (AttributeError, TypeError, ValueError):
        return False
    return (
        algo == _ALGO
        and iterations.isascii()
        and iterations.isdigit()
        and len(iterations) <= 7
        and 100_000 <= int(iterations) <= 2_000_000
        and len(salt) == _SALT_BYTES * 2
        and len(digest) == hashlib.sha256().digest_size * 2
    )


def new_session_token() -> str:
    """Return an authenticated, expiring Beep-only session token."""
    issued = str(int(time.time()))
    nonce = secrets.token_urlsafe(24)
    payload = f"{issued}.{nonce}"
    signature = hmac.new(_session_key(), payload.encode(), hashlib.sha256).hexdigest()
    return f"{payload}.{signature}"


def verify_session_token(token: str) -> bool:
    """Validate a token signature and its fixed 12-hour lifetime."""
    try:
        issued_text, nonce, signature = token.split(".", 2)
        issued = int(issued_text)
    except (AttributeError, TypeError, ValueError):
        return False
    if (
        not nonce
        or len(token) > 512
        or len(nonce) > 128
        or issued > int(time.time()) + 60
    ):
        return False
    if int(time.time()) - issued > SESSION_MAX_AGE_SECONDS:
        return False
    payload = f"{issued_text}.{nonce}"
    expected = hmac.new(_session_key(), payload.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def _session_key() -> bytes:
    path = Path(os.environ.get(SESSION_KEY_ENV, DEFAULT_SESSION_KEY))
    try:
        value = path.read_bytes().strip()
    except OSError:
        value = b""
    if not 32 <= len(value) <= 4096:
        if os.environ.get("BEEP_TEST_ALLOW_EPHEMERAL_SESSION_KEY") == "1":
            return _TEST_SESSION_KEY
        raise RuntimeError("Beep session key is missing or too short")
    return value


def validate_configuration() -> None:
    """Fail closed unless installed authentication material is protected."""

    if not _hash_fields_valid(configured_hash() or ""):
        raise RuntimeError("Beep admin password hash is missing or invalid")
    path = Path(os.environ.get(SESSION_KEY_ENV, DEFAULT_SESSION_KEY))
    try:
        metadata = path.lstat()
        value = path.read_bytes().strip()
    except OSError as exc:
        raise RuntimeError("Beep session key is missing") from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.geteuid()
        or not 32 <= len(value) <= 4096
    ):
        raise RuntimeError("Beep session key is not safely configured")


_TEST_SESSION_KEY = secrets.token_bytes(48)


def main(argv: list[str] | None = None) -> int:
    """CLI used by the installer to compute a hash without exposing the
    plaintext on the process command line (read from stdin by default)."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Compute the Beep admin password hash."
    )
    parser.parse_args(argv)
    password = sys.stdin.readline().rstrip("\n")
    if not password:
        parser.error("a non-empty Beep password is required")
    sys.stdout.write(hash_password(password) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
