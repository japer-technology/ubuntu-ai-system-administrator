"""Closed capability decisions for Friend's deliberately small authority."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Capability(str, Enum):
    CONVERSATION = "conversation"
    WORKSPACE_READ = "workspace.read"
    WORKSPACE_CHANGE = "workspace.change"
    PRODUCT_ADMIN = "product.admin"


@dataclass(frozen=True)
class Decision:
    capability: str
    allowed: bool
    reason: str
    requires_confirmation: bool = False


_ABSENT_PREFIXES = (
    "shell",
    "host.",
    "package.",
    "service.",
    "network.",
    "account.",
    "sibling.",
    "sudo",
)


def decide(
    capability: str,
    *,
    authenticated_owner: bool,
    destructive: bool = False,
    confirmation_matches: bool = False,
) -> Decision:
    """Fail closed for every capability outside the fixed registry."""
    if any(capability == prefix or capability.startswith(prefix) for prefix in _ABSENT_PREFIXES):
        return Decision(capability, False, "Host and sibling capabilities are absent.")
    try:
        known = Capability(capability)
    except ValueError:
        return Decision(capability, False, "Unknown capabilities are denied.")
    if not authenticated_owner:
        return Decision(capability, False, "An authenticated Friend owner is required.")
    if known is Capability.WORKSPACE_CHANGE and destructive and not confirmation_matches:
        return Decision(
            capability,
            False,
            "The canonical relative path must be confirmed.",
            requires_confirmation=True,
        )
    return Decision(capability, True, "Allowed inside the installed Friend boundary.")
