"""Typed failures exposed by the Friend HTTP and lifecycle boundaries."""

from __future__ import annotations


class FriendError(Exception):
    """A safe, expected failure with a stable public code."""

    def __init__(self, code: str, message: str, *, status: int = 400) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


class AuthenticationError(FriendError):
    def __init__(self, message: str = "Authentication required.") -> None:
        super().__init__("AUTHENTICATION_REQUIRED", message, status=401)


class AuthorizationError(FriendError):
    def __init__(self, message: str = "The requested action is not allowed.") -> None:
        super().__init__("ACTION_DENIED", message, status=403)


class ConflictError(FriendError):
    def __init__(self, message: str) -> None:
        super().__init__("CONFLICT", message, status=409)


class NotFoundError(FriendError):
    def __init__(self, message: str) -> None:
        super().__init__("NOT_FOUND", message, status=404)


class ValidationError(FriendError):
    def __init__(self, message: str) -> None:
        super().__init__("INVALID_REQUEST", message, status=400)

