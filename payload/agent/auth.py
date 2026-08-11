"""Password gate for the Ubuntu Zombie chat UI.

The chat service binds to ``127.0.0.1`` only, but on a shared desktop
*every* local user can reach ``http://127.0.0.1:7878``. A password gate
keeps the root-capable administrator behind a shared secret. The
installer asks for the password (default ``braaaains``) and
stores only a salted PBKDF2 hash in ``secrets/env`` as
``ZOMBIE_ADMIN_PASSWORD_HASH`` — the plaintext is never written to disk.

The gate is *opt-in by configuration*: when ``ZOMBIE_ADMIN_PASSWORD_HASH``
is unset (e.g. in tests, or a deliberately open install), ``auth_required``
returns ``False`` and every request is allowed. When it is set, the
server requires a valid login before serving any privileged endpoint.

Hash format (single line, ``$``-separated)::

    pbkdf2_sha256$<iterations>$<salt-hex>$<derived-key-hex>
"""
from __future__ import annotations

import hashlib
import hmac
import os
import secrets

HASH_ENV = "ZOMBIE_ADMIN_PASSWORD_HASH"
DEFAULT_PASSWORD = "braaaains"

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
    if algo != _ALGO:
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
    """True when a password hash is configured (the gate is active)."""
    return configured_hash() is not None


def check_password(password: str) -> bool:
    """Validate ``password``; allow everything when the gate is disabled."""
    stored = configured_hash()
    if stored is None:
        return True
    return verify_password(password, stored)


def new_session_token() -> str:
    """Return an unguessable opaque session token."""
    return secrets.token_urlsafe(32)


def main(argv: list[str] | None = None) -> int:
    """CLI used by the installer to compute a hash without exposing the
    plaintext on the process command line (read from stdin by default)."""
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description="Compute the Ubuntu Zombie admin password hash."
    )
    parser.add_argument(
        "--password",
        help="Password to hash. If omitted, read a single line from stdin.",
    )
    args = parser.parse_args(argv)
    password = args.password
    if password is None:
        password = sys.stdin.readline().rstrip("\n")
    if not password:
        password = DEFAULT_PASSWORD
    sys.stdout.write(hash_password(password) + "\n")
    return 0


if __name__ == "__main__":  # pragma: no cover
    import sys

    sys.exit(main())
