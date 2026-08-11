"""Closed, catalogue-pinned family manager for Beep.

The manager never contains or reimplements another product's installer. It
validates Beep's own release catalogue, verifies one listed target artifact,
and invokes only that target's declared lifecycle entry point with an argument
array and a common request file.
"""

from __future__ import annotations

import argparse
import fcntl
import grp
import hashlib
import json
import os
import pwd
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Iterator


PRODUCTS = (
    "imaginary-friend",
    "curriculum-flame",
    "eric",
    "llama",
    "beep",
)
MANAGEABLE_PRODUCTS = tuple(product for product in PRODUCTS if product != "beep")
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
MUTATING_OPERATIONS = {
    "install",
    "repair",
    "backup",
    "update",
    "rollback",
    "suspend",
    "resume",
    "uninstall",
}
RELEASE_OPERATIONS = {"install", "update"}
VERSION_PATTERN = re.compile(r"^\d{4}(?:\.\d{2}){5}$")
DIGEST_PATTERN = re.compile(r"^sha256:[0-9a-f]{64}$")
HEX_DIGEST_PATTERN = re.compile(r"^[0-9a-f]{64}$")
UUID_PATTERN = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-"
    r"[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
)
MAX_ASSET_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_FILES = 20_000
MAX_ARCHIVE_BYTES = 2 * 1024 * 1024 * 1024
MAX_RESPONSE_BYTES = 2 * 1024 * 1024
DEFAULT_TIMEOUT = 1800
OIDC_ISSUER = "https://token.actions.githubusercontent.com"
REPOSITORY = "japer-technology/beep"
RELEASE_PREFIX = f"https://github.com/{REPOSITORY}/releases/download/"

DESCRIPTOR_FIELDS = {
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
RESPONSE_FIELDS = {
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
INVENTORY_ENTRY_FIELDS = {
    "instance_id",
    "installed_version",
    "available_version",
    "descriptor_digest",
    "marker_digest",
    "lifecycle_status",
    "health_status",
    "last_correlation_id",
    "last_operation",
    "last_result",
    "receipt_path",
    "receipt_digest",
    "last_checked_at",
}
SECRET_WORDS = ("secret", "password", "credential", "token", "api_key", "private_key")

DEFAULT_DESCRIPTOR_PATHS = {
    "imaginary-friend": Path("/etc/imaginary-friend/PRODUCT.json"),
    "curriculum-flame": Path("/etc/curriculum-flame/PRODUCT.json"),
    "eric": Path("/etc/eric/PRODUCT.json"),
    "llama": Path("/etc/llama.cpp/PRODUCT.json"),
}
EXPECTED_ENTRYPOINTS = {
    "imaginary-friend": "/usr/local/sbin/friend-manage",
    "curriculum-flame": "/usr/local/sbin/flame-manage",
    "eric": "/usr/local/sbin/eric-manage",
    "llama": "/usr/local/sbin/llama-manage",
}


class FamilyError(Exception):
    """Stable manager failure suitable for CLI and structured tool output."""

    def __init__(self, exit_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.code = code
        self.message = message


@dataclass(frozen=True)
class FamilyPaths:
    """Every durable resource owned by Beep's family manager."""

    catalog: Path = Path("/etc/beep/agents/catalog.json")
    inventory: Path = Path("/var/lib/beep/agents/inventory.json")
    audit: Path = Path("/var/log/beep/audit.jsonl")
    lock: Path = Path("/run/lock/beep-agents.lock")
    releases: Path = Path("/run/beep-agent-releases")


def utc_now() -> str:
    """Return a canonical second-precision UTC timestamp."""

    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
        "+00:00", "Z"
    )


def canonical_json(value: Any) -> bytes:
    """Return deterministic compact UTF-8 JSON."""

    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    """Return a family-contract digest."""

    return "sha256:" + hashlib.sha256(value).hexdigest()


def _no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise FamilyError(65, "DUPLICATE_JSON_KEY", f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def load_json(path: Path, *, label: str) -> dict[str, Any]:
    """Load one strict UTF-8 JSON object from a regular non-symlink file."""

    if not path.is_file() or path.is_symlink():
        raise FamilyError(66, f"{label.upper()}_MISSING", f"{label} is missing.")
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_no_duplicates
        )
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise FamilyError(65, f"INVALID_{label.upper()}", f"{label} is invalid.") from exc
    if not isinstance(value, dict):
        raise FamilyError(65, f"INVALID_{label.upper()}", f"{label} must be an object.")
    return value


def _exact_fields(
    value: dict[str, Any],
    expected: set[str],
    *,
    label: str,
    optional: set[str] | None = None,
) -> None:
    optional = optional or set()
    missing = expected - value.keys()
    unknown = value.keys() - expected - optional
    if missing or unknown:
        raise FamilyError(
            65,
            f"INVALID_{label.upper()}",
            f"{label} fields are invalid.",
        )


def _canonical_uuid(value: Any, *, label: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if not isinstance(value, str) or not UUID_PATTERN.fullmatch(value):
        raise FamilyError(65, "INVALID_UUID", f"{label} must be a canonical UUID.")
    try:
        if str(uuid.UUID(value)) != value:
            raise ValueError
    except ValueError as exc:
        raise FamilyError(65, "INVALID_UUID", f"{label} must be a canonical UUID.") from exc


def _timestamp(value: Any, *, label: str) -> None:
    if not isinstance(value, str) or not value.endswith("Z"):
        raise FamilyError(65, "INVALID_TIMESTAMP", f"{label} must be UTC RFC 3339.")
    try:
        datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError as exc:
        raise FamilyError(65, "INVALID_TIMESTAMP", f"{label} is invalid.") from exc


def _absolute(value: Any, *, label: str) -> Path:
    if (
        not isinstance(value, str)
        or not value.startswith("/")
        or "\x00" in value
        or "\r" in value
        or "\n" in value
        or ".." in Path(value).parts
    ):
        raise FamilyError(65, "INVALID_PATH", f"{label} must be canonical and absolute.")
    path = Path(value)
    if str(path) != value:
        raise FamilyError(65, "INVALID_PATH", f"{label} must be canonical and absolute.")
    return path


def _under(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _assert_protected_file(
    path: Path,
    *,
    mode: int,
    root_owned: bool,
    label: str,
) -> os.stat_result:
    if not path.is_file() or path.is_symlink():
        raise FamilyError(66, f"{label.upper()}_MISSING", f"{label} is missing.")
    try:
        metadata = path.stat(follow_symlinks=False)
    except OSError as exc:
        raise FamilyError(66, f"{label.upper()}_MISSING", f"{label} is unreadable.") from exc
    if not stat.S_ISREG(metadata.st_mode) or stat.S_IMODE(metadata.st_mode) != mode:
        raise FamilyError(73, f"UNSAFE_{label.upper()}", f"{label} permissions are unsafe.")
    if root_owned and (metadata.st_uid != 0 or metadata.st_gid != 0):
        raise FamilyError(73, f"UNSAFE_{label.upper()}", f"{label} must be root-owned.")
    return metadata


def validate_descriptor(value: dict[str, Any], product_id: str) -> dict[str, Any]:
    """Validate a target descriptor and its separation from Beep."""

    _exact_fields(value, DESCRIPTOR_FIELDS, label="descriptor")
    if value["schema_version"] != 1 or value["product_id"] != product_id:
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Descriptor identity is invalid.")
    if product_id not in MANAGEABLE_PRODUCTS:
        raise FamilyError(65, "SELF_MANAGEMENT_DENIED", "Beep never manages itself.")
    if (
        value["source_root"] != f"products/{product_id}"
        or value["version_file"] != "VERSION"
        or value["lifecycle_script"] != "scripts/manage.sh"
        or value["installed_entrypoint"] != EXPECTED_ENTRYPOINTS[product_id]
        or value["operations"] != list(OPERATIONS)
    ):
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Descriptor lifecycle is invalid.")
    if not isinstance(value["display_name"], str) or not value["display_name"].strip():
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Descriptor display name is invalid.")
    if not isinstance(value["authority_summary"], str) or not value[
        "authority_summary"
    ].strip():
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Descriptor authority is invalid.")

    paths = {
        name: _absolute(value[name], label=name)
        for name in (
            "installed_entrypoint",
            "install_root",
            "configuration_root",
            "state_root",
            "log_root",
            "ownership_marker",
        )
    }
    if paths["ownership_marker"] != paths["state_root"] / "installation.json":
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Ownership marker is outside state.")
    beep_roots = (
        Path("/opt/beep"),
        Path("/etc/beep"),
        Path("/var/lib/beep"),
        Path("/var/log/beep"),
    )
    if any(
        path == root or _under(path, root)
        for path in paths.values()
        for root in beep_roots
    ):
        raise FamilyError(65, "BEEP_BOUNDARY_VIOLATION", "Target claims a Beep resource.")
    if value["environment_prefix"] == "BEEP":
        raise FamilyError(65, "BEEP_BOUNDARY_VIOLATION", "Target claims Beep environment.")

    accounts = value["accounts"]
    if not isinstance(accounts, list) or not accounts:
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Target accounts are invalid.")
    seen_accounts: set[tuple[str, str]] = set()
    for account in accounts:
        if not isinstance(account, dict) or set(account) != {"name", "kind"}:
            raise FamilyError(65, "INVALID_DESCRIPTOR", "Target account is invalid.")
        item = (account["name"], account["kind"])
        if (
            not isinstance(item[0], str)
            or not re.fullmatch(r"[a-z_][a-z0-9_-]{0,31}", item[0])
            or item[1] not in {"user", "group"}
            or item in seen_accounts
            or item[0] == "beep"
        ):
            raise FamilyError(65, "BEEP_BOUNDARY_VIOLATION", "Target account is unsafe.")
        seen_accounts.add(item)

    units = value["units"]
    if not isinstance(units, list) or len(units) != len(set(units)):
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Target units are invalid.")
    for unit in units:
        if (
            not isinstance(unit, str)
            or not re.fullmatch(r"[a-z0-9][a-z0-9@_.-]*\.(?:service|socket|timer)", unit)
            or unit.startswith("beep-")
        ):
            raise FamilyError(65, "BEEP_BOUNDARY_VIOLATION", "Target unit is unsafe.")

    ports = value["ports"]
    if not isinstance(ports, list):
        raise FamilyError(65, "INVALID_DESCRIPTOR", "Target ports are invalid.")
    port_rows: set[tuple[str, int, str]] = set()
    for port in ports:
        if not isinstance(port, dict) or set(port) != {"address", "port", "protocol"}:
            raise FamilyError(65, "INVALID_DESCRIPTOR", "Target port is invalid.")
        row = (port["address"], port["port"], port["protocol"])
        if (
            row[0] not in {"127.0.0.1", "::1"}
            or isinstance(row[1], bool)
            or not isinstance(row[1], int)
            or not 1 <= row[1] <= 65535
            or row[2] not in {"tcp", "udp"}
            or row in port_rows
            or row[1] == 58989
        ):
            raise FamilyError(65, "BEEP_BOUNDARY_VIOLATION", "Target port is unsafe.")
        port_rows.add(row)

    cookies = value["cookie_names"]
    if (
        not isinstance(cookies, list)
        or len(cookies) != len(set(cookies))
        or "beep_session" in cookies
    ):
        raise FamilyError(65, "BEEP_BOUNDARY_VIOLATION", "Target cookie is unsafe.")
    return value


def validate_marker(
    value: dict[str, Any],
    descriptor: dict[str, Any],
) -> dict[str, Any]:
    """Validate the target's ownership marker against its descriptor."""

    fields = {
        "schema_version",
        "product_id",
        "instance_id",
        "version",
        "source_revision",
        "installed_at",
        "install_root",
        "lifecycle_entrypoint",
        "artifact_sha256",
    }
    _exact_fields(value, fields, label="marker")
    if (
        value["schema_version"] != 1
        or value["product_id"] != descriptor["product_id"]
        or value["install_root"] != descriptor["install_root"]
        or value["lifecycle_entrypoint"] != descriptor["installed_entrypoint"]
        or not VERSION_PATTERN.fullmatch(str(value["version"]))
        or not isinstance(value["source_revision"], str)
        or not value["source_revision"]
    ):
        raise FamilyError(65, "INVALID_MARKER", "Target marker is invalid.")
    _canonical_uuid(value["instance_id"], label="instance_id")
    _timestamp(value["installed_at"], label="installed_at")
    artifact_digest = value["artifact_sha256"]
    if artifact_digest is not None and not HEX_DIGEST_PATTERN.fullmatch(
        str(artifact_digest)
    ):
        raise FamilyError(65, "INVALID_MARKER", "Target artifact digest is invalid.")
    return value


def validate_response(
    value: dict[str, Any],
    *,
    product_id: str,
    operation: str,
    correlation_id: str,
    dry_run: bool,
    plan_digest: str | None,
) -> dict[str, Any]:
    """Validate a target's common response before trusting any field."""

    _exact_fields(value, RESPONSE_FIELDS, label="response", optional={"details"})
    if (
        value["schema_version"] != 1
        or value["product_id"] != product_id
        or value["operation"] != operation
        or value["correlation_id"] != correlation_id
        or not VERSION_PATTERN.fullmatch(str(value["product_version"]))
        or value["status"]
        not in {"ok", "degraded", "blocked", "unsupported", "failed"}
        or not isinstance(value["changed"], bool)
        or not isinstance(value["requires_confirmation"], bool)
    ):
        raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target response is invalid.")
    _canonical_uuid(value["instance_id"], label="instance_id", nullable=True)
    _canonical_uuid(value["correlation_id"], label="correlation_id")
    expected_phase = "plan" if dry_run else (
        "execute" if operation in MUTATING_OPERATIONS else "read"
    )
    if value["phase"] != expected_phase or (dry_run and value["changed"]):
        raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target response phase is invalid.")
    returned_digest = value["plan_digest"]
    if returned_digest is not None and not DIGEST_PATTERN.fullmatch(
        str(returned_digest)
    ):
        raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target plan digest is invalid.")
    if dry_run and returned_digest is None:
        raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target omitted the plan digest.")
    if plan_digest is not None and returned_digest != plan_digest:
        raise FamilyError(78, "PLAN_DIGEST_MISMATCH", "Target plan digest changed.")
    for field in ("required_inputs", "steps", "checks", "errors", "recovery"):
        if not isinstance(value[field], list):
            raise FamilyError(65, "INVALID_TARGET_RESPONSE", f"Target {field} is invalid.")
    if "details" in value and not isinstance(value["details"], dict):
        raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target details are invalid.")
    receipt = value["receipt"]
    if receipt is not None:
        if (
            not isinstance(receipt, dict)
            or set(receipt) != {"path", "digest"}
            or not DIGEST_PATTERN.fullmatch(str(receipt["digest"]))
        ):
            raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target receipt is invalid.")
        _absolute(receipt["path"], label="receipt")
    return value


def _validate_asset(
    value: Any,
    *,
    tag: str,
    label: str,
) -> dict[str, str]:
    if not isinstance(value, dict) or set(value) != {"name", "url", "sha256"}:
        raise FamilyError(65, "INVALID_CATALOG", f"Catalog {label} is invalid.")
    name, url, digest = value["name"], value["url"], value["sha256"]
    if (
        not isinstance(name, str)
        or not name
        or "/" in name
        or name in {".", ".."}
        or not isinstance(url, str)
        or url != f"{RELEASE_PREFIX}{tag}/{name}"
        or not HEX_DIGEST_PATTERN.fullmatch(str(digest))
    ):
        raise FamilyError(65, "INVALID_CATALOG", f"Catalog {label} is invalid.")
    return {"name": name, "url": url, "sha256": digest}


def validate_catalog(value: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Validate and index Beep's installed release catalogue."""

    _exact_fields(
        value,
        {"schema_version", "repository", "generated_at", "products"},
        label="catalog",
    )
    if value["schema_version"] != 1 or value["repository"] != REPOSITORY:
        raise FamilyError(65, "INVALID_CATALOG", "Catalog identity is invalid.")
    _timestamp(value["generated_at"], label="generated_at")
    if not isinstance(value["products"], list):
        raise FamilyError(65, "INVALID_CATALOG", "Catalog products are invalid.")
    indexed: dict[str, dict[str, Any]] = {}
    for row in value["products"]:
        fields = {
            "product_id",
            "descriptor",
            "version",
            "tag",
            "artifact",
            "sbom",
            "provenance",
            "signature_bundle",
            "certificate_identity",
        }
        if not isinstance(row, dict):
            raise FamilyError(65, "INVALID_CATALOG", "Catalog product is invalid.")
        _exact_fields(row, fields, label="catalog_product")
        product_id = row["product_id"]
        version = row["version"]
        tag = row["tag"]
        if (
            product_id not in MANAGEABLE_PRODUCTS
            or product_id in indexed
            or row["descriptor"] != f"products/{product_id}/PRODUCT.json"
            or not VERSION_PATTERN.fullmatch(str(version))
            or tag != f"{product_id}-v{version}"
            or not isinstance(row["certificate_identity"], str)
            or not row["certificate_identity"].startswith(
                f"https://github.com/{REPOSITORY}/.github/workflows/"
            )
        ):
            raise FamilyError(65, "INVALID_CATALOG", "Catalog product identity is invalid.")
        normalized = dict(row)
        asset_names: set[str] = set()
        for label in ("artifact", "sbom", "provenance", "signature_bundle"):
            asset = _validate_asset(row[label], tag=tag, label=label)
            if asset["name"] in asset_names:
                raise FamilyError(65, "INVALID_CATALOG", "Catalog asset names collide.")
            asset_names.add(asset["name"])
            normalized[label] = asset
        indexed[product_id] = normalized
    return indexed


def validate_inventory(value: dict[str, Any]) -> dict[str, Any]:
    """Validate Beep's secret-free manager inventory."""

    _exact_fields(
        value,
        {"schema_version", "generated_at", "products"},
        label="inventory",
    )
    if value["schema_version"] != 1 or not isinstance(value["products"], dict):
        raise FamilyError(65, "INVALID_INVENTORY", "Inventory is invalid.")
    _timestamp(value["generated_at"], label="generated_at")
    for product_id, row in value["products"].items():
        if product_id not in MANAGEABLE_PRODUCTS or not isinstance(row, dict):
            raise FamilyError(65, "INVALID_INVENTORY", "Inventory product is invalid.")
        _exact_fields(row, INVENTORY_ENTRY_FIELDS, label="inventory_entry")
        _canonical_uuid(row["instance_id"], label="instance_id")
        _canonical_uuid(row["last_correlation_id"], label="last_correlation_id")
        _timestamp(row["last_checked_at"], label="last_checked_at")
        if (
            not isinstance(row["installed_version"], str)
            or not isinstance(row["available_version"], str)
            or not DIGEST_PATTERN.fullmatch(str(row["descriptor_digest"]))
            or not DIGEST_PATTERN.fullmatch(str(row["marker_digest"]))
            or row["lifecycle_status"]
            not in {"active", "suspended", "retained", "unknown"}
            or row["health_status"] not in {"ok", "degraded", "failed", "unknown"}
            or not isinstance(row["last_operation"], str)
            or not isinstance(row["last_result"], str)
            or not isinstance(row["receipt_path"], str)
            or not row["receipt_path"].startswith("/")
            or not DIGEST_PATTERN.fullmatch(str(row["receipt_digest"]))
        ):
            raise FamilyError(65, "INVALID_INVENTORY", "Inventory entry is invalid.")
        encoded = canonical_json(row).lower()
        if any(word.encode() in encoded for word in SECRET_WORDS):
            raise FamilyError(65, "INVALID_INVENTORY", "Inventory contains private fields.")
    return value


def _atomic_json(path: Path, value: dict[str, Any], *, mode: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        os.fchmod(descriptor, mode)
        content = canonical_json(value) + b"\n"
        os.write(descriptor, content)
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = -1
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


class _ReleaseRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Permit redirects only between GitHub-controlled HTTPS hosts."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        parsed = urllib.parse.urlsplit(newurl)
        hostname = (parsed.hostname or "").lower()
        if (
            parsed.scheme != "https"
            or parsed.username is not None
            or parsed.password is not None
            or not (
                hostname == "github.com"
                or hostname.endswith(".githubusercontent.com")
            )
        ):
            raise urllib.error.HTTPError(
                newurl, 403, "unsafe release redirect", headers, fp
            )
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class FamilyManager:
    """Validate, plan, and execute one exact external product lifecycle."""

    def __init__(
        self,
        paths: FamilyPaths = FamilyPaths(),
        *,
        descriptor_paths: dict[str, Path] | None = None,
        enforce_system_ownership: bool = True,
        signature_verifier: Callable[[Path, Path, str], None] | None = None,
    ) -> None:
        self.paths = paths
        self.descriptor_paths = descriptor_paths or DEFAULT_DESCRIPTOR_PATHS
        self.enforce_system_ownership = enforce_system_ownership
        self.signature_verifier = signature_verifier or self._verify_signature

    def catalog(self) -> dict[str, dict[str, Any]]:
        return validate_catalog(load_json(self.paths.catalog, label="catalog"))

    def inventory(self) -> dict[str, Any]:
        if not self.paths.inventory.exists():
            return {"schema_version": 1, "generated_at": utc_now(), "products": {}}
        return validate_inventory(load_json(self.paths.inventory, label="inventory"))

    def list_products(self) -> dict[str, Any]:
        catalog = self.catalog()
        inventory = self.inventory()
        return {
            "schema_version": 1,
            "manager": "beep",
            "operation": "list",
            "products": [
                {
                    "product_id": product_id,
                    "available_version": entry["version"],
                    "installed": product_id in inventory["products"],
                    "inventory": inventory["products"].get(product_id),
                }
                for product_id, entry in sorted(catalog.items())
            ],
        }

    def status(self, product_id: str, *, timeout: int = 60) -> dict[str, Any]:
        catalog = self.catalog()
        entry = self._target_entry(catalog, product_id)
        descriptor = self._installed_descriptor(product_id, required=False)
        if descriptor is None:
            return {
                "schema_version": 1,
                "manager": "beep",
                "operation": "status",
                "product_id": product_id,
                "available_version": entry["version"],
                "installed": False,
                "target": None,
            }
        with self._manager_lock():
            marker, _ = self._installed_marker(descriptor)
            correlation_id = str(uuid.uuid4())
            response = self._invoke(
                Path(descriptor["installed_entrypoint"]),
                product_id=product_id,
                operation="status",
                correlation_id=correlation_id,
                inputs={},
                confirmation=None,
                retain_state=None,
                dry_run=False,
                plan_digest=None,
                timeout=timeout,
                environment_prefix=descriptor["environment_prefix"],
                artifact_sha256=None,
            )
            self._record_outcome(entry, descriptor, marker, response)
            self._audit(response, actor="beep")
        return {
            "schema_version": 1,
            "manager": "beep",
            "operation": "status",
            "product_id": product_id,
            "available_version": entry["version"],
            "installed": True,
            "target": response,
        }

    def prepare(self, product_id: str) -> dict[str, Any]:
        """Download and verify one admitted release for later read-only planning."""

        catalog = self.catalog()
        entry = self._target_entry(catalog, product_id)
        correlation_id = str(uuid.uuid4())
        with self._manager_lock():
            self._ensure_cache_directory(self.paths.releases)
            product_root = self.paths.releases / product_id
            self._ensure_cache_directory(product_root)
            with tempfile.TemporaryDirectory(
                prefix=".prepare-", dir=product_root
            ) as directory:
                work = Path(directory)
                assets_root = work / "assets"
                assets_root.mkdir(mode=0o700)
                assets = self._download_assets(entry, assets_root)
                self.signature_verifier(
                    assets["artifact"],
                    assets["signature_bundle"],
                    entry["certificate_identity"],
                )
                release_root = work / "release"
                self._extract_release(entry, assets["artifact"], release_root)
                manifest = {
                    "schema_version": 1,
                    "product_id": product_id,
                    "version": entry["version"],
                    "catalog_entry_digest": sha256_bytes(canonical_json(entry)),
                    "prepared_at": utc_now(),
                    "assets": {
                        label: {
                            "name": entry[label]["name"],
                            "sha256": entry[label]["sha256"],
                        }
                        for label in (
                            "artifact",
                            "sbom",
                            "provenance",
                            "signature_bundle",
                        )
                    },
                }
                _atomic_json(work / "manifest.json", manifest, mode=0o600)
                destination = product_root / entry["version"]
                if destination.is_symlink():
                    raise FamilyError(
                        73, "UNSAFE_RELEASE_CACHE", "Prepared release is a symlink."
                    )
                if destination.exists():
                    self._assert_safe_cache_tree(destination)
                    shutil.rmtree(destination)
                os.replace(work, destination)
            self._audit(
                {
                    "correlation_id": correlation_id,
                    "product_id": product_id,
                    "instance_id": None,
                    "operation": "prepare",
                    "phase": "execute",
                    "status": "ok",
                    "changed": True,
                    "receipt": None,
                },
                actor="operator",
            )
            return {
                "schema_version": 1,
                "manager": "beep",
                "operation": "prepare",
                "product_id": product_id,
                "version": entry["version"],
                "correlation_id": correlation_id,
                "status": "ok",
                "prepared_path": str(destination),
            }

    def plan(
        self,
        product_id: str,
        operation: str,
        *,
        correlation_id: str | None = None,
        inputs: dict[str, Any] | None = None,
        confirmation: str | None = None,
        retain_state: bool | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        if operation not in MUTATING_OPERATIONS:
            raise FamilyError(
                2, "INVALID_OPERATION", "Plans are available for mutating operations only."
            )
        correlation_id = correlation_id or str(uuid.uuid4())
        _canonical_uuid(correlation_id, label="correlation_id")
        inputs = self._safe_inputs(inputs or {})
        catalog = self.catalog()
        entry = self._target_entry(catalog, product_id)
        with self._target_lifecycle(entry, operation) as (
            entrypoint,
            descriptor,
            artifact_digest,
        ):
            response = self._invoke(
                entrypoint,
                product_id=product_id,
                operation=operation,
                correlation_id=correlation_id,
                inputs=inputs,
                confirmation=confirmation,
                retain_state=retain_state,
                dry_run=True,
                plan_digest=None,
                timeout=timeout,
                environment_prefix=descriptor["environment_prefix"],
                artifact_sha256=artifact_digest,
            )
        return response

    def manage(
        self,
        product_id: str,
        operation: str,
        *,
        correlation_id: str,
        plan_digest: str,
        inputs: dict[str, Any] | None = None,
        confirmation: str | None = None,
        retain_state: bool | None = None,
        timeout: int = DEFAULT_TIMEOUT,
    ) -> dict[str, Any]:
        if operation not in MUTATING_OPERATIONS:
            raise FamilyError(65, "MUTATION_REQUIRED", "agent.manage accepts mutations only.")
        _canonical_uuid(correlation_id, label="correlation_id")
        if not DIGEST_PATTERN.fullmatch(plan_digest):
            raise FamilyError(65, "INVALID_PLAN_DIGEST", "Plan digest is invalid.")
        inputs = self._safe_inputs(inputs or {})
        catalog = self.catalog()
        entry = self._target_entry(catalog, product_id)
        with self._manager_lock():
            with self._target_lifecycle(entry, operation) as (
                entrypoint,
                descriptor,
                artifact_digest,
            ):
                response = self._invoke(
                    entrypoint,
                    product_id=product_id,
                    operation=operation,
                    correlation_id=correlation_id,
                    inputs=inputs,
                    confirmation=confirmation,
                    retain_state=retain_state,
                    dry_run=False,
                    plan_digest=plan_digest,
                    timeout=timeout,
                    environment_prefix=descriptor["environment_prefix"],
                    artifact_sha256=artifact_digest,
                )
            try:
                marker: dict[str, Any] | None = None
                if operation != "uninstall" and response["status"] == "ok":
                    installed = self._installed_descriptor(product_id, required=True)
                    if installed != descriptor:
                        raise FamilyError(
                            78,
                            "DESCRIPTOR_MISMATCH",
                            "Installed target descriptor differs from verified release.",
                        )
                    marker, _ = self._installed_marker(installed)
                    self._verify_receipt(response, installed)
                    self._record_outcome(entry, installed, marker, response)
                elif operation == "uninstall" and response["status"] == "ok":
                    self._record_uninstall(entry, descriptor, response, retain_state)
                self._audit(response, actor="beep")
            except FamilyError:
                self._audit_manager_failure(response)
                raise
            except Exception as exc:
                self._audit_manager_failure(response)
                raise FamilyError(
                    1,
                    "MANAGER_RECORD_FAILED",
                    "The target returned, but Beep could not verify or record the outcome.",
                ) from exc
        return response

    def read_inputs(self, path: Path | None) -> dict[str, Any]:
        if path is None:
            return {}
        if not path.is_absolute():
            raise FamilyError(65, "INVALID_INPUTS_FILE", "Inputs file must be absolute.")
        _assert_protected_file(
            path,
            mode=0o600,
            root_owned=self.enforce_system_ownership,
            label="inputs_file",
        )
        value = load_json(path, label="inputs")
        return self._safe_inputs(value)

    @staticmethod
    def _safe_inputs(value: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(value, dict):
            raise FamilyError(65, "INVALID_INPUTS", "Target inputs must be an object.")
        encoded = canonical_json(value)
        if len(encoded) > 64 * 1024:
            raise FamilyError(65, "INVALID_INPUTS", "Target inputs are too large.")

        def inspect(item: Any, key: str = "") -> None:
            lowered = key.lower()
            if any(word in lowered for word in SECRET_WORDS) and not lowered.endswith(
                "_file"
            ):
                raise FamilyError(
                    65,
                    "RAW_SECRET_INPUT_DENIED",
                    "Private inputs must use protected *_file references.",
                )
            if isinstance(item, dict):
                for nested_key, nested_value in item.items():
                    if not isinstance(nested_key, str):
                        raise FamilyError(65, "INVALID_INPUTS", "Input keys must be strings.")
                    inspect(nested_value, nested_key)
            elif isinstance(item, list):
                for nested_value in item:
                    inspect(nested_value, key)
            elif item is not None and not isinstance(item, (str, int, float, bool)):
                raise FamilyError(65, "INVALID_INPUTS", "Input value is invalid.")
            if lowered.endswith("_file"):
                _absolute(item, label=key)

        inspect(value)
        return value

    def _target_entry(
        self, catalog: dict[str, dict[str, Any]], product_id: str
    ) -> dict[str, Any]:
        if product_id == "beep":
            raise FamilyError(65, "SELF_MANAGEMENT_DENIED", "Beep never manages itself.")
        if product_id not in catalog:
            raise FamilyError(66, "PRODUCT_NOT_ADMITTED", "Product is not in the catalogue.")
        return catalog[product_id]

    @contextmanager
    def _target_lifecycle(
        self,
        entry: dict[str, Any],
        operation: str,
    ) -> Iterator[tuple[Path, dict[str, Any], str | None]]:
        product_id = entry["product_id"]
        if operation not in RELEASE_OPERATIONS:
            descriptor = self._installed_descriptor(product_id, required=True)
            self._installed_marker(descriptor)
            entrypoint = Path(descriptor["installed_entrypoint"])
            _assert_protected_file(
                entrypoint,
                mode=0o755,
                root_owned=self.enforce_system_ownership,
                label="target_entrypoint",
            )
            yield entrypoint, descriptor, None
            return
        with self._prepared_lifecycle(entry) as prepared:
            yield prepared

    @contextmanager
    def _prepared_lifecycle(
        self,
        entry: dict[str, Any],
    ) -> Iterator[tuple[Path, dict[str, Any], str]]:
        prepared = self.paths.releases / entry["product_id"] / entry["version"]
        if not prepared.is_dir() or prepared.is_symlink():
            raise FamilyError(
                69,
                "RELEASE_NOT_PREPARED",
                "Run `sudo /opt/beep/bin/beep-agents --json prepare "
                f"{entry['product_id']}` before planning this release.",
            )
        self._assert_safe_cache_tree(prepared)
        manifest = load_json(prepared / "manifest.json", label="prepared_manifest")
        expected_assets = {
            label: {
                "name": entry[label]["name"],
                "sha256": entry[label]["sha256"],
            }
            for label in ("artifact", "sbom", "provenance", "signature_bundle")
        }
        if (
            set(manifest)
            != {
                "schema_version",
                "product_id",
                "version",
                "catalog_entry_digest",
                "prepared_at",
                "assets",
            }
            or manifest["schema_version"] != 1
            or manifest["product_id"] != entry["product_id"]
            or manifest["version"] != entry["version"]
            or manifest["catalog_entry_digest"]
            != sha256_bytes(canonical_json(entry))
            or manifest["assets"] != expected_assets
        ):
            raise FamilyError(78, "PREPARED_RELEASE_INVALID", "Prepared release is invalid.")
        _timestamp(manifest["prepared_at"], label="prepared_at")
        assets_root = prepared / "assets"
        for label, expected in expected_assets.items():
            asset = assets_root / expected["name"]
            if not asset.is_file() or asset.is_symlink():
                raise FamilyError(
                    78, "PREPARED_RELEASE_INVALID", "Prepared release asset is missing."
                )
            digest = hashlib.sha256()
            with asset.open("rb") as handle:
                for block in iter(lambda: handle.read(1024 * 1024), b""):
                    digest.update(block)
            if digest.hexdigest() != expected["sha256"]:
                raise FamilyError(
                    78, "PREPARED_RELEASE_INVALID", "Prepared release asset changed."
                )
        extracted = prepared / "release"
        descriptor = self._validate_release_tree(entry, extracted)
        entrypoint = extracted / descriptor["source_root"] / descriptor[
            "lifecycle_script"
        ]
        if not entrypoint.is_file() or entrypoint.is_symlink():
            raise FamilyError(78, "RELEASE_INCOMPLETE", "Release lifecycle is missing.")
        yield entrypoint, descriptor, entry["artifact"]["sha256"]

    def _ensure_cache_directory(self, path: Path) -> None:
        if path.exists() or path.is_symlink():
            if not path.is_dir() or path.is_symlink():
                raise FamilyError(
                    73, "UNSAFE_RELEASE_CACHE", "Release cache is unsafe."
                )
            metadata = path.stat(follow_symlinks=False)
            if self.enforce_system_ownership and (
                metadata.st_uid != 0 or metadata.st_gid != 0
            ):
                raise FamilyError(
                    73, "UNSAFE_RELEASE_CACHE", "Release cache must be root-owned."
                )
        else:
            path.mkdir(mode=0o700)
        os.chmod(path, 0o700)

    def _assert_safe_cache_tree(self, root: Path) -> None:
        if not root.is_dir() or root.is_symlink():
            raise FamilyError(73, "UNSAFE_RELEASE_CACHE", "Release cache is unsafe.")
        for path in (root, *root.rglob("*")):
            if path.is_symlink():
                raise FamilyError(
                    73, "UNSAFE_RELEASE_CACHE", "Release cache contains a symlink."
                )
            metadata = path.stat(follow_symlinks=False)
            if self.enforce_system_ownership and (
                metadata.st_uid != 0 or metadata.st_gid != 0
            ):
                raise FamilyError(
                    73, "UNSAFE_RELEASE_CACHE", "Release cache is not root-owned."
                )
            if stat.S_IMODE(metadata.st_mode) & 0o022:
                raise FamilyError(
                    73, "UNSAFE_RELEASE_CACHE", "Release cache is writable by others."
                )

    def _download_assets(
        self, entry: dict[str, Any], destination: Path
    ) -> dict[str, Path]:
        opener = urllib.request.build_opener(_ReleaseRedirectHandler)
        result: dict[str, Path] = {}
        for label in ("artifact", "sbom", "provenance", "signature_bundle"):
            asset = entry[label]
            target = destination / asset["name"]
            request = urllib.request.Request(
                asset["url"], headers={"User-Agent": "beep-agents/1"}
            )
            digest = hashlib.sha256()
            written = 0
            try:
                with opener.open(request, timeout=60) as response, target.open("xb") as out:
                    while True:
                        block = response.read(1024 * 1024)
                        if not block:
                            break
                        written += len(block)
                        if written > MAX_ASSET_BYTES:
                            raise FamilyError(
                                78, "ASSET_TOO_LARGE", "Release asset exceeds the size limit."
                            )
                        digest.update(block)
                        out.write(block)
            except FamilyError:
                raise
            except (OSError, urllib.error.URLError) as exc:
                raise FamilyError(
                    75, "ASSET_DOWNLOAD_FAILED", "Could not download a release asset."
                ) from exc
            if digest.hexdigest() != asset["sha256"]:
                raise FamilyError(
                    78, "ASSET_DIGEST_MISMATCH", "Release asset digest did not match."
                )
            os.chmod(target, 0o600)
            result[label] = target
        return result

    @staticmethod
    def _verify_signature(artifact: Path, bundle: Path, identity: str) -> None:
        cosign = shutil.which("cosign")
        if not cosign:
            raise FamilyError(
                69,
                "COSIGN_MISSING",
                "cosign is required to verify a managed product release.",
            )
        completed = subprocess.run(
            [
                cosign,
                "verify-blob",
                "--offline",
                "--bundle",
                str(bundle),
                "--certificate-identity",
                identity,
                "--certificate-oidc-issuer",
                OIDC_ISSUER,
                str(artifact),
            ],
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=120,
            env={
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "HOME": "/var/empty",
                "LANG": "C.UTF-8",
            },
        )
        if completed.returncode != 0:
            raise FamilyError(
                78, "SIGNATURE_VERIFICATION_FAILED", "Release signature is invalid."
            )

    def _extract_release(
        self,
        entry: dict[str, Any],
        archive: Path,
        destination: Path,
    ) -> dict[str, Any]:
        product_root = PurePosixPath("products") / entry["product_id"]
        allowed_roots = {PurePosixPath("products"), PurePosixPath("family")}
        total_size = 0
        file_count = 0
        try:
            with tarfile.open(archive, "r:gz") as source:
                members = source.getmembers()
                seen_paths: set[PurePosixPath] = set()
                for member in members:
                    path = PurePosixPath(member.name)
                    if (
                        not member.name
                        or path.is_absolute()
                        or ".." in path.parts
                        or member.issym()
                        or member.islnk()
                        or member.isdev()
                        or member.isfifo()
                        or (not member.isfile() and not member.isdir())
                        or path in seen_paths
                    ):
                        raise FamilyError(
                            78, "UNSAFE_RELEASE", "Release contains an unsafe archive member."
                        )
                    seen_paths.add(path)
                    if path in {
                        PurePosixPath("products"),
                        PurePosixPath("family"),
                    }:
                        pass
                    elif path == PurePosixPath("LICENSE"):
                        pass
                    elif not path.parts or PurePosixPath(path.parts[0]) not in allowed_roots:
                        raise FamilyError(
                            78, "UNSAFE_RELEASE", "Release contains an unexpected root."
                        )
                    elif path.parts[0] == "products" and not (
                        path == product_root or product_root in path.parents
                    ):
                        raise FamilyError(
                            78,
                            "SIBLING_PAYLOAD_REJECTED",
                            "Release bundles another product.",
                        )
                    elif path.parts[0] == "family" and (
                        len(path.parts) < 2 or path.parts[1] != "schemas"
                    ):
                        raise FamilyError(
                            78, "UNSAFE_RELEASE", "Release family data is unexpected."
                        )
                    if member.isfile():
                        file_count += 1
                        total_size += member.size
                    if (
                        file_count > MAX_ARCHIVE_FILES
                        or total_size > MAX_ARCHIVE_BYTES
                        or member.size > MAX_ASSET_BYTES
                    ):
                        raise FamilyError(
                            78, "RELEASE_TOO_LARGE", "Release exceeds extraction limits."
                        )
                destination.mkdir(mode=0o700)
                for member in members:
                    relative = PurePosixPath(member.name)
                    target = destination.joinpath(*relative.parts)
                    if member.isdir():
                        target.mkdir(parents=True, exist_ok=True, mode=0o755)
                        os.chmod(target, 0o755)
                        continue
                    target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                    extracted = source.extractfile(member)
                    if extracted is None:
                        raise FamilyError(
                            78, "INVALID_RELEASE", "Release file cannot be extracted."
                        )
                    with extracted, target.open("xb") as output:
                        shutil.copyfileobj(extracted, output, length=1024 * 1024)
                    os.chmod(target, 0o755 if member.mode & 0o111 else 0o644)
        except FamilyError:
            raise
        except (OSError, tarfile.TarError) as exc:
            raise FamilyError(78, "INVALID_RELEASE", "Release archive is invalid.") from exc
        return self._validate_release_tree(entry, destination)

    @staticmethod
    def _validate_release_tree(
        entry: dict[str, Any], destination: Path
    ) -> dict[str, Any]:
        descriptor_path = destination / entry["descriptor"]
        descriptor = validate_descriptor(
            load_json(descriptor_path, label="descriptor"), entry["product_id"]
        )
        version_path = destination / descriptor["source_root"] / descriptor["version_file"]
        if (
            not version_path.is_file()
            or version_path.is_symlink()
            or version_path.read_text(encoding="utf-8").strip() != entry["version"]
        ):
            raise FamilyError(78, "VERSION_MISMATCH", "Release version does not match.")
        return descriptor

    def _installed_descriptor(
        self, product_id: str, *, required: bool
    ) -> dict[str, Any] | None:
        path = self.descriptor_paths.get(product_id)
        if path is None:
            raise FamilyError(65, "UNKNOWN_PRODUCT", "Product descriptor path is unknown.")
        if not path.exists():
            if required:
                raise FamilyError(66, "TARGET_NOT_INSTALLED", "Target is not installed.")
            return None
        _assert_protected_file(
            path,
            mode=0o644,
            root_owned=self.enforce_system_ownership,
            label="descriptor",
        )
        return validate_descriptor(load_json(path, label="descriptor"), product_id)

    def _installed_marker(
        self, descriptor: dict[str, Any]
    ) -> tuple[dict[str, Any], str]:
        path = Path(descriptor["ownership_marker"])
        _assert_protected_file(
            path,
            mode=0o644,
            root_owned=self.enforce_system_ownership,
            label="marker",
        )
        content = path.read_bytes()
        marker = validate_marker(load_json(path, label="marker"), descriptor)
        return marker, sha256_bytes(content)

    def _invoke(
        self,
        entrypoint: Path,
        *,
        product_id: str,
        operation: str,
        correlation_id: str,
        inputs: dict[str, Any],
        confirmation: str | None,
        retain_state: bool | None,
        dry_run: bool,
        plan_digest: str | None,
        timeout: int,
        environment_prefix: str,
        artifact_sha256: str | None,
    ) -> dict[str, Any]:
        if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 3600:
            raise FamilyError(65, "INVALID_TIMEOUT", "Timeout must be 1..3600 seconds.")
        if operation == "uninstall" and not isinstance(retain_state, bool):
            raise FamilyError(
                64, "RETAIN_STATE_REQUIRED", "Uninstall requires an explicit retain_state."
            )
        if operation != "uninstall" and retain_state is not None:
            raise FamilyError(
                65, "INVALID_RETAIN_STATE", "retain_state applies only to uninstall."
            )
        request: dict[str, Any] = {
            "schema_version": 1,
            "product_id": product_id,
            "operation": operation,
            "correlation_id": correlation_id,
            "requested_by": "beep",
            "inputs": inputs,
            "confirmation": confirmation,
        }
        if operation == "uninstall":
            request["retain_state"] = retain_state
        with tempfile.TemporaryDirectory(prefix="beep-request-") as directory:
            request_path = Path(directory) / "request.json"
            request_path.write_bytes(canonical_json(request) + b"\n")
            os.chmod(request_path, 0o600)
            arguments = [
                str(entrypoint),
                operation,
                "--json",
                "--non-interactive",
                "--request-file",
                str(request_path),
            ]
            if dry_run:
                arguments.append("--dry-run")
            if plan_digest is not None:
                arguments.extend(["--plan-digest", plan_digest])
                arguments.append("--yes")
            with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
                try:
                    environment = {
                        "PATH": (
                            "/usr/local/sbin:/usr/local/bin:/usr/sbin:"
                            "/usr/bin:/sbin:/bin"
                        ),
                        "HOME": "/root",
                        "LANG": "C.UTF-8",
                    }
                    if artifact_sha256 is not None:
                        environment[f"{environment_prefix}_ARTIFACT_SHA256"] = (
                            artifact_sha256
                        )
                    completed = subprocess.run(
                        arguments,
                        check=False,
                        stdin=subprocess.DEVNULL,
                        stdout=stdout,
                        stderr=stderr,
                        timeout=timeout,
                        env=environment,
                    )
                except subprocess.TimeoutExpired as exc:
                    raise FamilyError(75, "TARGET_TIMEOUT", "Target lifecycle timed out.") from exc
                stdout.seek(0)
                raw = stdout.read(MAX_RESPONSE_BYTES + 1)
                stderr.seek(0)
                error = stderr.read(16 * 1024).decode("utf-8", errors="replace").strip()
        if len(raw) > MAX_RESPONSE_BYTES:
            raise FamilyError(65, "TARGET_RESPONSE_TOO_LARGE", "Target response is too large.")
        try:
            response = json.loads(raw.decode("utf-8"), object_pairs_hook=_no_duplicates)
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise FamilyError(
                65,
                "INVALID_TARGET_RESPONSE",
                "Target did not return one valid JSON response.",
            ) from exc
        if not isinstance(response, dict):
            raise FamilyError(65, "INVALID_TARGET_RESPONSE", "Target response is not an object.")
        validated = validate_response(
            response,
            product_id=product_id,
            operation=operation,
            correlation_id=correlation_id,
            dry_run=dry_run,
            plan_digest=plan_digest,
        )
        if completed.returncode != 0 and validated["status"] not in {
            "blocked",
            "unsupported",
            "failed",
        }:
            raise FamilyError(
                1,
                "TARGET_EXIT_MISMATCH",
                "Target exit status disagreed with its response.",
            )
        if completed.returncode == 0 and validated["status"] in {"blocked", "failed"}:
            raise FamilyError(
                1,
                "TARGET_EXIT_MISMATCH",
                "Target reported failure with a successful exit status.",
            )
        if completed.returncode not in {0, 1, 2, 64, 65, 66, 69, 73, 75, 78}:
            raise FamilyError(
                1,
                "TARGET_EXIT_INVALID",
                f"Target returned an unsupported exit status{': ' + error if error else '.'}",
            )
        return validated

    def _verify_receipt(
        self, response: dict[str, Any], descriptor: dict[str, Any]
    ) -> None:
        receipt = response["receipt"]
        if not isinstance(receipt, dict):
            raise FamilyError(78, "RECEIPT_MISSING", "Target mutation omitted its receipt.")
        path = Path(receipt["path"])
        expected = Path(descriptor["log_root"]) / "management-receipt.json"
        if path != expected:
            raise FamilyError(78, "RECEIPT_PATH_MISMATCH", "Target receipt path is invalid.")
        _assert_protected_file(
            path,
            mode=0o640,
            root_owned=self.enforce_system_ownership,
            label="receipt",
        )
        if sha256_bytes(path.read_bytes()) != receipt["digest"]:
            raise FamilyError(78, "RECEIPT_DIGEST_MISMATCH", "Target receipt digest is invalid.")

    def _record_outcome(
        self,
        catalog_entry: dict[str, Any],
        descriptor: dict[str, Any],
        marker: dict[str, Any],
        response: dict[str, Any],
    ) -> None:
        inventory = self.inventory()
        marker_path = Path(descriptor["ownership_marker"])
        receipt = response["receipt"]
        previous = inventory["products"].get(catalog_entry["product_id"], {})
        receipt_path = (
            receipt["path"]
            if isinstance(receipt, dict)
            else previous.get(
                "receipt_path",
                str(Path(descriptor["log_root"]) / "management-receipt.json"),
            )
        )
        receipt_digest = (
            receipt["digest"]
            if isinstance(receipt, dict)
            else previous.get("receipt_digest")
        )
        if receipt_digest is None:
            receipt_file = Path(receipt_path)
            if not receipt_file.is_file() or receipt_file.is_symlink():
                raise FamilyError(78, "RECEIPT_MISSING", "Target receipt is unavailable.")
            receipt_digest = sha256_bytes(receipt_file.read_bytes())
        lifecycle_status = (
            "suspended"
            if response["operation"] == "suspend"
            else "active"
        )
        health_status = {
            "ok": "ok",
            "degraded": "degraded",
            "blocked": "failed",
            "unsupported": "unknown",
            "failed": "failed",
        }[response["status"]]
        descriptor_path = self.descriptor_paths[catalog_entry["product_id"]]
        inventory["products"][catalog_entry["product_id"]] = {
            "instance_id": marker["instance_id"],
            "installed_version": marker["version"],
            "available_version": catalog_entry["version"],
            "descriptor_digest": sha256_bytes(descriptor_path.read_bytes()),
            "marker_digest": sha256_bytes(marker_path.read_bytes()),
            "lifecycle_status": lifecycle_status,
            "health_status": health_status,
            "last_correlation_id": response["correlation_id"],
            "last_operation": response["operation"],
            "last_result": response["status"],
            "receipt_path": receipt_path,
            "receipt_digest": receipt_digest,
            "last_checked_at": utc_now(),
        }
        inventory["generated_at"] = utc_now()
        validate_inventory(inventory)
        _atomic_json(self.paths.inventory, inventory, mode=0o600)

    def _record_uninstall(
        self,
        catalog_entry: dict[str, Any],
        descriptor: dict[str, Any],
        response: dict[str, Any],
        retain_state: bool | None,
    ) -> None:
        inventory = self.inventory()
        if not retain_state:
            inventory["products"].pop(catalog_entry["product_id"], None)
        else:
            previous = inventory["products"].get(catalog_entry["product_id"])
            if previous is None:
                raise FamilyError(
                    78, "INVENTORY_MISSING", "Retained uninstall lacks prior inventory."
                )
            previous.update(
                {
                    "available_version": catalog_entry["version"],
                    "lifecycle_status": "retained",
                    "health_status": "unknown",
                    "last_correlation_id": response["correlation_id"],
                    "last_operation": "uninstall",
                    "last_result": response["status"],
                    "last_checked_at": utc_now(),
                }
            )
        inventory["generated_at"] = utc_now()
        validate_inventory(inventory)
        _atomic_json(self.paths.inventory, inventory, mode=0o600)

    def _audit(self, response: dict[str, Any], *, actor: str) -> None:
        event = {
            "timestamp": utc_now(),
            "event_id": str(uuid.uuid4()),
            "correlation_id": response["correlation_id"],
            "product_id": response["product_id"],
            "instance_id": response["instance_id"],
            "operation": response["operation"],
            "phase": response["phase"],
            "actor": actor,
            "decision": "denied" if response["status"] == "blocked" else "allowed",
            "result": response["status"],
            "changed": response["changed"],
            "receipt_digest": (
                response["receipt"]["digest"]
                if isinstance(response["receipt"], dict)
                else None
            ),
            "manager": "beep",
        }
        self.paths.audit.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.paths.audit,
            os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW,
            0o640,
        )
        try:
            try:
                account = pwd.getpwnam("beep")
                group = grp.getgrnam("beep")
            except KeyError:
                pass
            else:
                os.fchown(descriptor, account.pw_uid, group.gr_gid)
            os.fchmod(descriptor, 0o640)
            os.write(descriptor, canonical_json(event) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def _audit_manager_failure(self, response: dict[str, Any]) -> None:
        failure = dict(response)
        failure["status"] = "failed"
        try:
            self._audit(failure, actor="beep")
        except OSError:
            pass

    @contextmanager
    def _manager_lock(self) -> Iterator[None]:
        self.paths.lock.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.paths.lock,
            os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW,
            0o600,
        )
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise FamilyError(75, "MANAGER_BUSY", "Beep family manager is busy.") from exc
            yield
        finally:
            os.close(descriptor)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="beep-agents")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list")
    status = subparsers.add_parser("status")
    status.add_argument("product_id", choices=MANAGEABLE_PRODUCTS)
    prepare = subparsers.add_parser("prepare")
    prepare.add_argument("product_id", choices=MANAGEABLE_PRODUCTS)

    def target_arguments(value: argparse.ArgumentParser, *, execute: bool) -> None:
        value.add_argument("product_id", choices=MANAGEABLE_PRODUCTS)
        value.add_argument("operation", choices=MUTATING_OPERATIONS)
        value.add_argument("--correlation-id")
        value.add_argument("--inputs-file", type=Path)
        value.add_argument("--confirmation")
        value.add_argument(
            "--retain-state",
            choices=("yes", "no"),
        )
        value.add_argument("--timeout", type=int, default=DEFAULT_TIMEOUT)
        if execute:
            value.add_argument("--plan-digest", required=True)

    target_arguments(subparsers.add_parser("plan"), execute=False)
    target_arguments(subparsers.add_parser("manage"), execute=True)
    parser.add_argument("--json", action="store_true")
    return parser


def _error_result(error: FamilyError) -> dict[str, Any]:
    return {
        "schema_version": 1,
        "manager": "beep",
        "status": "blocked"
        if error.exit_code in {64, 65, 66, 69, 73, 75, 78}
        else "failed",
        "errors": [{"code": error.code, "message": error.message}],
    }


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if os.geteuid() != 0:
        result = _error_result(
            FamilyError(73, "ROOT_REQUIRED", "beep-agents must run as root.")
        )
        print(json.dumps(result, sort_keys=True))
        return 73
    manager = FamilyManager()
    try:
        if args.command == "list":
            result = manager.list_products()
        elif args.command == "status":
            result = manager.status(args.product_id)
        elif args.command == "prepare":
            result = manager.prepare(args.product_id)
        else:
            inputs = manager.read_inputs(args.inputs_file)
            retain_state = (
                None
                if args.retain_state is None
                else args.retain_state == "yes"
            )
            if args.command == "plan":
                result = manager.plan(
                    args.product_id,
                    args.operation,
                    correlation_id=args.correlation_id,
                    inputs=inputs,
                    confirmation=args.confirmation,
                    retain_state=retain_state,
                    timeout=args.timeout,
                )
            else:
                if args.correlation_id is None:
                    raise FamilyError(
                        64,
                        "CORRELATION_ID_REQUIRED",
                        "manage requires --correlation-id from the approved plan.",
                    )
                result = manager.manage(
                    args.product_id,
                    args.operation,
                    correlation_id=args.correlation_id,
                    plan_digest=args.plan_digest,
                    inputs=inputs,
                    confirmation=args.confirmation,
                    retain_state=retain_state,
                    timeout=args.timeout,
                )
    except FamilyError as error:
        result = _error_result(error)
        print(json.dumps(result, sort_keys=True))
        return error.exit_code
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
