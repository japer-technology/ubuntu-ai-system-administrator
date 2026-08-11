"""Standard-library checks for the shared family data contract."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

OPERATIONS = (
    "describe",
    "status",
    "install",
    "verify",
    "doctor",
    "repair",
    "backup",
    "update",
    "rollback",
    "suspend",
    "resume",
    "uninstall",
)
BEEP_OPERATIONS = (*OPERATIONS[:-1], "kill", OPERATIONS[-1])
PRODUCTS = (
    "imaginary-friend",
    "curriculum-flame",
    "eric",
    "forgejo",
    "llama",
    "beep",
)
VERSION_PATTERN = re.compile(r"^\d{4}(?:\.\d{2}){5}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")


class ContractError(ValueError):
    """Raised when data does not satisfy a family contract."""


def _object_no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractError(f"duplicate key: {key}")
        result[key] = value
    return result


def load_json_strict(path: Path) -> dict[str, Any]:
    """Load one UTF-8 JSON object while rejecting duplicate keys."""
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_object_no_duplicates,
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractError(f"invalid JSON in {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise ContractError(f"{path} must contain one JSON object")
    return value


def _exact_keys(value: dict[str, Any], required: set[str], *, label: str) -> None:
    missing = required - value.keys()
    unknown = value.keys() - required
    if missing:
        raise ContractError(f"{label} missing keys: {sorted(missing)}")
    if unknown:
        raise ContractError(f"{label} unknown keys: {sorted(unknown)}")


def _uuid(value: Any, *, label: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str):
        raise ContractError(f"{label} must be a UUID string")
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ContractError(f"{label} must be a UUID") from exc
    if str(parsed) != value:
        raise ContractError(f"{label} must be a canonical lowercase UUID")


def _absolute(path: Any, *, label: str) -> None:
    if (
        not isinstance(path, str)
        or not path.startswith("/")
        or "\x00" in path
        or "\n" in path
        or ".." in Path(path).parts
    ):
        raise ContractError(f"{label} must be a canonical absolute path")


def validate_product(value: dict[str, Any]) -> None:
    """Validate the stable fields and namespace relationships in PRODUCT.json."""
    required = {
        "schema_version",
        "product_id",
        "display_name",
        "authority_summary",
        "source_root",
        "version_file",
        "lifecycle_script",
        "installed_entrypoint",
        "install_root",
        "configuration_root",
        "state_root",
        "log_root",
        "ownership_marker",
        "environment_prefix",
        "accounts",
        "units",
        "ports",
        "cookie_names",
        "operations",
    }
    _exact_keys(value, required, label="product descriptor")
    if value["schema_version"] != 1:
        raise ContractError("product schema_version must be 1")
    product_id = value["product_id"]
    if product_id not in PRODUCTS:
        raise ContractError("unknown product_id")
    if value["source_root"] != f"products/{product_id}":
        raise ContractError("source_root does not match product_id")
    if value["version_file"] != "VERSION":
        raise ContractError("version_file must be VERSION")
    if value["lifecycle_script"] != "scripts/manage.sh":
        raise ContractError("lifecycle_script must be scripts/manage.sh")
    for field in (
        "installed_entrypoint",
        "install_root",
        "configuration_root",
        "state_root",
        "log_root",
        "ownership_marker",
    ):
        _absolute(value[field], label=field)
    if value["ownership_marker"] != f"{value['state_root']}/installation.json":
        raise ContractError("ownership_marker must be below state_root")
    if not isinstance(value["display_name"], str) or not value["display_name"].strip():
        raise ContractError("display_name must be non-empty")
    if (
        not isinstance(value["authority_summary"], str)
        or not value["authority_summary"].strip()
    ):
        raise ContractError("authority_summary must be non-empty")
    expected_operations = BEEP_OPERATIONS if product_id == "beep" else OPERATIONS
    if value["operations"] != list(expected_operations):
        raise ContractError("operations must use the complete stable order")
    if not isinstance(value["accounts"], list) or not value["accounts"]:
        raise ContractError("accounts must be a non-empty array")
    identities: set[tuple[str, str]] = set()
    for account in value["accounts"]:
        if not isinstance(account, dict):
            raise ContractError("account entries must be objects")
        _exact_keys(account, {"name", "kind"}, label="account")
        if account["kind"] not in {"user", "group"}:
            raise ContractError("invalid account kind")
        identity = (account["name"], account["kind"])
        if identity in identities:
            raise ContractError("duplicate account")
        identities.add(identity)
    if not isinstance(value["units"], list) or len(value["units"]) != len(
        set(value["units"])
    ):
        raise ContractError("units must be a unique array")
    if not isinstance(value["ports"], list):
        raise ContractError("ports must be an array")
    for port in value["ports"]:
        if set(port) != {"address", "port", "protocol"}:
            raise ContractError("invalid port entry")
        if port["address"] not in {"127.0.0.1", "::1"}:
            raise ContractError("product listeners must be loopback")
        if not isinstance(port["port"], int) or not 1 <= port["port"] <= 65535:
            raise ContractError("invalid port number")
    cookies = value["cookie_names"]
    if not isinstance(cookies, list) or len(cookies) != len(set(cookies)):
        raise ContractError("cookie_names must be a unique array")


def validate_request(
    value: dict[str, Any], *, product_id: str, operation: str
) -> None:
    """Validate a common request before product-specific input checks."""
    allowed = {
        "schema_version",
        "product_id",
        "operation",
        "correlation_id",
        "requested_by",
        "inputs",
        "confirmation",
        "retain_state",
    }
    required = allowed - {"retain_state"}
    missing = required - value.keys()
    unknown = value.keys() - allowed
    if missing or unknown:
        raise ContractError(
            f"request keys invalid; missing={sorted(missing)}, unknown={sorted(unknown)}"
        )
    if value["schema_version"] != 1 or value["product_id"] != product_id:
        raise ContractError("request identity mismatch")
    expected_operations = BEEP_OPERATIONS if product_id == "beep" else OPERATIONS
    if value["operation"] != operation or operation not in expected_operations:
        raise ContractError("request operation mismatch")
    _uuid(value["correlation_id"], label="correlation_id")
    if value["requested_by"] not in {"operator", "ubuntu-zombie", "beep"}:
        raise ContractError("invalid requested_by")
    if not isinstance(value["inputs"], dict):
        raise ContractError("inputs must be an object")
    if value["confirmation"] is not None and not isinstance(
        value["confirmation"], str
    ):
        raise ContractError("confirmation must be a string or null")
    if operation == "uninstall" and not isinstance(value.get("retain_state"), bool):
        raise ContractError("uninstall requires boolean retain_state")
    if operation != "uninstall" and "retain_state" in value:
        raise ContractError("retain_state is accepted only for uninstall")


def validate_response(value: dict[str, Any]) -> None:
    """Validate the common response envelope without third-party packages."""
    required = {
        "schema_version",
        "product_id",
        "product_version",
        "instance_id",
        "operation",
        "phase",
        "correlation_id",
        "status",
        "changed",
        "plan_digest",
        "requires_confirmation",
        "required_inputs",
        "steps",
        "checks",
        "receipt",
        "errors",
        "recovery",
    }
    missing = required - value.keys()
    unknown = value.keys() - (required | {"details"})
    if missing:
        raise ContractError(f"response missing keys: {sorted(missing)}")
    if unknown:
        raise ContractError(f"response unknown keys: {sorted(unknown)}")
    if "details" in value and not isinstance(value["details"], dict):
        raise ContractError("response details must be an object")
    if value["schema_version"] != 1 or value["product_id"] not in PRODUCTS:
        raise ContractError("invalid response identity")
    if not VERSION_PATTERN.fullmatch(str(value["product_version"])):
        raise ContractError("invalid product_version")
    _uuid(value["instance_id"], label="instance_id", nullable=True)
    _uuid(value["correlation_id"], label="correlation_id")
    expected_operations = (
        BEEP_OPERATIONS if value["product_id"] == "beep" else OPERATIONS
    )
    if value["operation"] not in expected_operations:
        raise ContractError("invalid response operation")
    if value["phase"] not in {"read", "plan", "execute"}:
        raise ContractError("invalid response phase")
    if value["status"] not in {
        "ok",
        "degraded",
        "blocked",
        "unsupported",
        "failed",
    }:
        raise ContractError("invalid response status")
    if not isinstance(value["changed"], bool):
        raise ContractError("changed must be boolean")
    if value["phase"] in {"read", "plan"} and value["changed"]:
        raise ContractError("read and plan responses cannot report changes")
    digest = value["plan_digest"]
    if digest is not None and not DIGEST_PATTERN.fullmatch(str(digest)):
        raise ContractError("invalid plan digest")
    if not isinstance(value["requires_confirmation"], bool):
        raise ContractError("requires_confirmation must be boolean")
    for name in ("required_inputs", "steps", "checks", "errors", "recovery"):
        if not isinstance(value[name], list):
            raise ContractError(f"{name} must be an array")
    receipt = value["receipt"]
    if receipt is not None:
        if set(receipt) != {"path", "digest"}:
            raise ContractError("invalid receipt")
        _absolute(receipt["path"], label="receipt path")
        if not DIGEST_PATTERN.fullmatch(str(receipt["digest"])):
            raise ContractError("invalid receipt digest")
