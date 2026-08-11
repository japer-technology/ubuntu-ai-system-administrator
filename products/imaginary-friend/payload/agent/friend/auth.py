"""Product-specific scrypt passwords and opaque session credentials."""

from __future__ import annotations

import hashlib
import hmac
import secrets

ALGORITHM = "scrypt"
SCRYPT_N = 16_384
SCRYPT_R = 8
SCRYPT_P = 1
SALT_BYTES = 16
DERIVED_BYTES = 32
MAX_PASSWORD_BYTES = 1_024


def _password_bytes(password: str) -> bytes:
    if not isinstance(password, str):
        raise TypeError("password must be text")
    try:
        encoded = password.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ValueError("password must be valid UTF-8") from exc
    if not encoded:
        raise ValueError("password must not be empty")
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ValueError("password is too long")
    return encoded


def hash_password(password: str, *, salt: bytes | None = None) -> str:
    """Return the fixed first-release scrypt record for ``password``."""
    encoded = _password_bytes(password)
    actual_salt = salt if salt is not None else secrets.token_bytes(SALT_BYTES)
    if len(actual_salt) != SALT_BYTES:
        raise ValueError("scrypt salt must be exactly 16 bytes")
    digest = hashlib.scrypt(
        encoded,
        salt=actual_salt,
        n=SCRYPT_N,
        r=SCRYPT_R,
        p=SCRYPT_P,
        dklen=DERIVED_BYTES,
    )
    return (
        f"{ALGORITHM}${SCRYPT_N}${SCRYPT_R}${SCRYPT_P}$"
        f"{actual_salt.hex()}${digest.hex()}"
    )


def valid_password_record(record: str) -> bool:
    """Return whether ``record`` has the exact supported algorithm and shape."""
    try:
        algorithm, n_text, r_text, p_text, salt_hex, digest_hex = record.split("$")
        salt = bytes.fromhex(salt_hex)
        digest = bytes.fromhex(digest_hex)
        values = (int(n_text), int(r_text), int(p_text))
    except (AttributeError, TypeError, ValueError):
        return False
    return (
        algorithm == ALGORITHM
        and values == (SCRYPT_N, SCRYPT_R, SCRYPT_P)
        and len(salt) == SALT_BYTES
        and len(digest) == DERIVED_BYTES
    )


def verify_password(password: str, record: str) -> bool:
    """Perform a constant-time comparison against a supported scrypt record."""
    if not valid_password_record(record):
        return False
    try:
        _, _, _, _, salt_hex, expected_hex = record.split("$")
        candidate = hashlib.scrypt(
            _password_bytes(password),
            salt=bytes.fromhex(salt_hex),
            n=SCRYPT_N,
            r=SCRYPT_R,
            p=SCRYPT_P,
            dklen=DERIVED_BYTES,
        )
    except (TypeError, ValueError):
        return False
    return hmac.compare_digest(candidate, bytes.fromhex(expected_hex))


def new_session_token() -> str:
    """Return a high-entropy opaque cookie value."""
    return secrets.token_urlsafe(32)


def new_csrf_token() -> str:
    """Return a separate token bound to one authenticated session."""
    return secrets.token_urlsafe(32)


def token_digest(token: str, signing_key: bytes) -> str:
    """Return a keyed digest suitable for persistent session lookup."""
    if len(signing_key) < 32:
        raise ValueError("session signing key must contain at least 32 bytes")
    return hmac.new(signing_key, token.encode("utf-8"), hashlib.sha256).hexdigest()


def new_signing_key() -> bytes:
    """Return independent signing material for this Friend installation."""
    return secrets.token_bytes(32)
