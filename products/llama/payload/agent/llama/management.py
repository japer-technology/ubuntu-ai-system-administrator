"""Independent, root-only lifecycle for the Llama infrastructure product."""

from __future__ import annotations

import argparse
import fcntl
import grp
import hashlib
import http.client
import io
import json
import os
import platform
import pwd
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, Iterator


PRODUCT_ID = "llama"
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
MUTATING = {
    "install",
    "repair",
    "backup",
    "update",
    "rollback",
    "suspend",
    "resume",
    "uninstall",
}
READ_ONLY = {"describe", "status", "verify", "doctor"}
CONFIGURATION_OPERATIONS = {"install", "repair", "update"}
CONFIGURATION_INPUTS = {"model_id", "context_size", "cpu_threads", "boot"}
OPERATION_INPUTS = {
    "describe": set(),
    "status": set(),
    "install": CONFIGURATION_INPUTS,
    "verify": set(),
    "doctor": set(),
    "repair": CONFIGURATION_INPUTS,
    "backup": {"backup_destination"},
    "update": CONFIGURATION_INPUTS,
    "rollback": set(),
    "suspend": set(),
    "resume": set(),
    "uninstall": set(),
}
KNOWN_ENV = {
    "LLAMA_SOURCE_ROOT",
    "LLAMA_NONINTERACTIVE",
    "LLAMA_MODEL_ID",
    "LLAMA_CONTEXT_SIZE",
    "LLAMA_CPU_THREADS",
    "LLAMA_BOOT",
    "LLAMA_PORT",
    "LLAMA_BACKUP_DESTINATION",
    "LLAMA_ARTIFACT_SHA256",
    "LLAMA_DISPOSABLE_VM_TEST",
}
CONFIG_KEYS = {
    "schema_version",
    "port",
    "model_id",
    "model_path",
    "context_size",
    "threads",
    "runtime_release",
    "runtime_dir",
}
DEFAULT_MODEL_ID = "smollm2-360m-instruct-q4_k_m"
DEFAULT_CONTEXT_SIZE = 2048
DEFAULT_BOOT = "enabled"
FIXED_PORT = 8080
DELETE_CONFIRMATION = "DELETE LLAMA STATE"
LEGACY_UNIT_SHA256 = "58d8fdb8f635e7c4aafd84a838d902a1b1595f353074ebbe20d46f1eafa870e7"
VERSION_PARTS = 6
MAX_DOWNLOAD_BYTES = 8 * 1024 * 1024 * 1024


class ManagementError(Exception):
    """A stable lifecycle failure suitable for machine-readable responses."""

    def __init__(
        self,
        exit_code: int,
        code: str,
        message: str,
        *,
        retryable: bool = False,
        recovery: list[str] | None = None,
    ) -> None:
        super().__init__(message)
        self.exit_code = exit_code
        self.code = code
        self.message = message
        self.retryable = retryable
        self.recovery = recovery or []


@dataclass(frozen=True)
class Paths:
    """Every host resource reserved by Llama."""

    install_root: Path = Path("/opt/llama.cpp")
    configuration_root: Path = Path("/etc/llama.cpp")
    state_root: Path = Path("/var/lib/llama.cpp")
    log_root: Path = Path("/var/log/llama.cpp")
    cache_root: Path = Path("/var/cache/llama.cpp")
    unit: Path = Path("/etc/systemd/system/llama-server.service")
    logrotate: Path = Path("/etc/logrotate.d/llama")
    entrypoint: Path = Path("/usr/local/sbin/llama-manage")
    manager: Path = Path("/usr/local/bin/llama-manager")
    lock: Path = Path("/run/lock/llama.lock")
    backup_root: Path = Path("/var/backups/llama.cpp")

    @property
    def marker(self) -> Path:
        return self.state_root / "installation.json"

    @property
    def transaction(self) -> Path:
        return self.state_root / ".installing.json"

    @property
    def retained(self) -> Path:
        return self.state_root / "retained.json"

    @property
    def retained_config(self) -> Path:
        return self.state_root / "retained-config.json"

    @property
    def suspended(self) -> Path:
        return self.state_root / "suspended.json"

    @property
    def rollback_root(self) -> Path:
        return self.install_root / "rollback"

    @property
    def rollback_metadata(self) -> Path:
        return self.rollback_root / "rollback.json"

    @property
    def product_root(self) -> Path:
        return self.install_root / "product"

    @property
    def versions(self) -> Path:
        return self.install_root / "versions"

    @property
    def current(self) -> Path:
        return self.install_root / "current"

    @property
    def config(self) -> Path:
        return self.configuration_root / "config.json"

    @property
    def descriptor(self) -> Path:
        return self.configuration_root / "PRODUCT.json"

    @property
    def models(self) -> Path:
        return self.state_root / "models"

    @property
    def runtime_state(self) -> Path:
        return self.state_root / "state"

    @property
    def audit(self) -> Path:
        return self.log_root / "audit.log"

    @property
    def log_ownership(self) -> Path:
        return self.log_root / "product-ownership"

    @property
    def receipt(self) -> Path:
        return self.log_root / "management-receipt.json"

    @property
    def receipts(self) -> Path:
        return self.log_root / "receipts"


@dataclass
class Invocation:
    operation: str
    correlation_id: str
    actor: str
    inputs: dict[str, Any]
    confirmation: str | None
    retain_state: bool | None
    dry_run: bool
    json_output: bool
    non_interactive: bool
    assume_yes: bool
    supplied_plan_digest: str | None


@dataclass(frozen=True)
class Configuration:
    model_id: str
    context_size: int
    cpu_threads: int
    boot: str
    runtime_release: str
    runtime_dir: Path
    model_path: Path

    def object(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "port": FIXED_PORT,
            "model_id": self.model_id,
            "model_path": str(self.model_path),
            "context_size": self.context_size,
            "threads": self.cpu_threads,
            "runtime_release": self.runtime_release,
            "runtime_dir": str(self.runtime_dir.parent.parent / "current"),
        }


@dataclass
class Result:
    operation: str
    correlation_id: str
    product_version: str
    instance_id: str | None
    phase: str
    status: str = "ok"
    changed: bool = False
    plan_digest: str | None = None
    requires_confirmation: bool = False
    required_inputs: list[dict[str, Any]] = field(default_factory=list)
    steps: list[dict[str, Any]] = field(default_factory=list)
    checks: list[dict[str, str]] = field(default_factory=list)
    receipt: dict[str, str] | None = None
    errors: list[dict[str, Any]] = field(default_factory=list)
    recovery: list[str] = field(default_factory=list)
    details: dict[str, Any] | None = None

    def object(self) -> dict[str, Any]:
        value: dict[str, Any] = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "product_version": self.product_version,
            "instance_id": self.instance_id,
            "operation": self.operation,
            "phase": self.phase,
            "correlation_id": self.correlation_id,
            "status": self.status,
            "changed": self.changed,
            "plan_digest": self.plan_digest,
            "requires_confirmation": self.requires_confirmation,
            "required_inputs": self.required_inputs,
            "steps": self.steps,
            "checks": self.checks,
            "receipt": self.receipt,
            "errors": self.errors,
            "recovery": self.recovery,
        }
        if self.details is not None:
            value["details"] = {"llama": self.details}
        return value


def utc_now() -> str:
    """Return an RFC 3339 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    """Encode canonical UTF-8 JSON."""
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise ManagementError(78, "INTEGRITY_READ_FAILED", f"Cannot hash {path}.") from exc
    return digest.hexdigest()


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ManagementError(65, "DUPLICATE_KEY", f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict[str, Any]:
    """Read one strict UTF-8 JSON object."""
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=strict_object,
        )
    except ManagementError:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ManagementError(65, "INVALID_JSON", f"Invalid JSON file: {path}") from exc
    if not isinstance(value, dict):
        raise ManagementError(65, "INVALID_JSON", f"{path} must contain one object.")
    return value


def validate_uuid(value: str, *, label: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except (ValueError, AttributeError) as exc:
        raise ManagementError(65, "INVALID_UUID", f"{label} must be a UUID.") from exc
    if str(parsed) != value:
        raise ManagementError(
            65, "INVALID_UUID", f"{label} must be a canonical lowercase UUID."
        )
    return value


def validate_version(value: str) -> str:
    parts = value.split(".")
    if (
        len(parts) != VERSION_PARTS
        or len(parts[0]) != 4
        or any(len(part) != 2 for part in parts[1:])
        or any(not part.isdigit() for part in parts)
    ):
        raise ManagementError(78, "INVALID_VERSION", "Product VERSION is invalid.")
    return value


def atomic_write(
    path: Path,
    content: bytes,
    *,
    mode: int,
    uid: int = 0,
    gid: int = 0,
) -> None:
    """Write a regular file atomically without following links."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    fd = os.open(temporary, flags, mode)
    try:
        view = memoryview(content)
        while view:
            written = os.write(fd, view)
            view = view[written:]
        os.fchmod(fd, mode)
        os.fchown(fd, uid, gid)
        os.fsync(fd)
    except BaseException:
        os.close(fd)
        temporary.unlink(missing_ok=True)
        raise
    else:
        os.close(fd)
    os.replace(temporary, path)
    directory_fd = os.open(path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except (OSError, RuntimeError, ValueError):
        return False
    return True


def _operation_phase(operation: str, *, dry_run: bool) -> str:
    if dry_run and operation in MUTATING:
        return "plan"
    return "read" if operation in READ_ONLY else "execute"


def _validate_redirect_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    test_url = (
        os.environ.get("LLAMA_DISPOSABLE_VM_TEST") == "1"
        and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "::1"}
    )
    host = parsed.hostname or ""
    approved = (
        host == "github.com"
        or host.endswith(".githubusercontent.com")
        or host == "huggingface.co"
        or host.endswith(".huggingface.co")
        or host.endswith(".hf.co")
        or host.endswith(".xethub.hf.co")
    )
    if not (test_url or (parsed.scheme == "https" and approved)):
        raise ManagementError(78, "UNSAFE_REDIRECT", "Asset redirect left approved hosts.")


class _SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        _validate_redirect_url(new_url)
        return super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )


class Manager:
    """Product lifecycle implementation."""

    def __init__(self, source_root: Path, paths: Paths | None = None) -> None:
        self.source_root = source_root.resolve()
        self.paths = paths or Paths()
        self.descriptor = read_json(self.source_root / "PRODUCT.json")
        self._validate_descriptor()
        try:
            version_text = (self.source_root / "VERSION").read_text(encoding="utf-8")
        except OSError as exc:
            raise ManagementError(66, "VERSION_MISSING", "Product VERSION is missing.") from exc
        self.version = validate_version(version_text.strip())
        self.build_catalog = self._build_catalog()
        self.model_catalog = self._model_catalog()

    def _validate_descriptor(self) -> None:
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
        if set(self.descriptor) != required:
            raise ManagementError(65, "INVALID_DESCRIPTOR", "PRODUCT.json fields are invalid.")
        expected = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "source_root": "products/llama",
            "version_file": "VERSION",
            "lifecycle_script": "scripts/manage.sh",
            "installed_entrypoint": str(self.paths.entrypoint),
            "install_root": str(self.paths.install_root),
            "configuration_root": str(self.paths.configuration_root),
            "state_root": str(self.paths.state_root),
            "log_root": str(self.paths.log_root),
            "ownership_marker": str(self.paths.marker),
            "environment_prefix": "LLAMA",
            "accounts": [
                {"name": "llama-cpp", "kind": "user"},
                {"name": "llama-cpp", "kind": "group"},
            ],
            "units": ["llama-server.service"],
            "ports": [{"address": "127.0.0.1", "port": 8080, "protocol": "tcp"}],
            "cookie_names": [],
            "operations": list(OPERATIONS),
        }
        for key, value in expected.items():
            if self.descriptor.get(key) != value:
                raise ManagementError(
                    65, "INVALID_DESCRIPTOR", f"PRODUCT.json has invalid {key}."
                )
        for key in ("display_name", "authority_summary"):
            if not isinstance(self.descriptor[key], str) or not self.descriptor[key].strip():
                raise ManagementError(
                    65, "INVALID_DESCRIPTOR", f"PRODUCT.json has invalid {key}."
                )

    def _build_catalog(self) -> dict[str, Any]:
        value = read_json(self.source_root / "payload/etc/llama-builds.json")
        if set(value) != {"schema_version", "release", "commit", "assets"}:
            raise ManagementError(65, "INVALID_CATALOGUE", "Build catalogue fields are invalid.")
        if value["schema_version"] != 1 or not isinstance(value["assets"], dict):
            raise ManagementError(65, "INVALID_CATALOGUE", "Build catalogue is invalid.")
        if not isinstance(value["release"], str) or not value["release"]:
            raise ManagementError(65, "INVALID_CATALOGUE", "Build release is invalid.")
        if (
            not isinstance(value["commit"], str)
            or len(value["commit"]) != 40
            or any(character not in "0123456789abcdef" for character in value["commit"])
        ):
            raise ManagementError(65, "INVALID_CATALOGUE", "Build commit is invalid.")
        for architecture, asset in value["assets"].items():
            if architecture not in {"amd64", "arm64"} or not isinstance(asset, dict):
                raise ManagementError(65, "INVALID_CATALOGUE", "Build architecture is invalid.")
            if set(asset) != {"url", "sha256", "archive_root"}:
                raise ManagementError(65, "INVALID_CATALOGUE", "Build asset fields are invalid.")
            self._validate_download_record(asset, allowed_kind="runtime")
            root = asset["archive_root"]
            if (
                not isinstance(root, str)
                or not root
                or root != PurePosixPath(root).name
            ):
                raise ManagementError(65, "INVALID_CATALOGUE", "Archive root is invalid.")
        return value

    def _model_catalog(self) -> dict[str, Any]:
        value = read_json(self.source_root / "payload/etc/llama-models.json")
        if set(value) != {"schema_version", "models"}:
            raise ManagementError(65, "INVALID_CATALOGUE", "Model catalogue fields are invalid.")
        if value["schema_version"] != 1 or not isinstance(value["models"], list):
            raise ManagementError(65, "INVALID_CATALOGUE", "Model catalogue is invalid.")
        identifiers: set[str] = set()
        for model in value["models"]:
            required = {
                "id",
                "name",
                "filename",
                "url",
                "sha256",
                "size_bytes",
                "license",
                "context_size",
            }
            if not isinstance(model, dict) or set(model) != required:
                raise ManagementError(65, "INVALID_CATALOGUE", "Model fields are invalid.")
            identifier = model["id"]
            if not isinstance(identifier, str) or not identifier or identifier in identifiers:
                raise ManagementError(65, "INVALID_CATALOGUE", "Model identifier is invalid.")
            identifiers.add(identifier)
            if model["filename"] != PurePosixPath(str(model["filename"])).name:
                raise ManagementError(65, "INVALID_CATALOGUE", "Model filename is invalid.")
            if (
                isinstance(model["size_bytes"], bool)
                or not isinstance(model["size_bytes"], int)
                or not 1 <= model["size_bytes"] <= MAX_DOWNLOAD_BYTES
            ):
                raise ManagementError(65, "INVALID_CATALOGUE", "Model size is invalid.")
            if (
                isinstance(model["context_size"], bool)
                or not isinstance(model["context_size"], int)
                or model["context_size"] < 512
            ):
                raise ManagementError(65, "INVALID_CATALOGUE", "Model context is invalid.")
            self._validate_download_record(model, allowed_kind="model")
        if not identifiers:
            raise ManagementError(65, "INVALID_CATALOGUE", "Model catalogue is empty.")
        return value

    @staticmethod
    def _validate_download_record(value: dict[str, Any], *, allowed_kind: str) -> None:
        digest = value.get("sha256")
        if (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ManagementError(65, "INVALID_CATALOGUE", "Download digest is invalid.")
        url = value.get("url")
        if not isinstance(url, str):
            raise ManagementError(65, "INVALID_CATALOGUE", "Download URL is invalid.")
        parsed = urllib.parse.urlsplit(url)
        test_url = (
            os.environ.get("LLAMA_DISPOSABLE_VM_TEST") == "1"
            and parsed.scheme == "http"
            and parsed.hostname in {"127.0.0.1", "::1"}
        )
        expected_host = (
            parsed.hostname == "github.com"
            if allowed_kind == "runtime"
            else parsed.hostname == "huggingface.co"
        )
        if (
            parsed.username is not None
            or parsed.password is not None
            or parsed.fragment
            or not parsed.path
            or not (test_url or (parsed.scheme == "https" and expected_host))
        ):
            raise ManagementError(65, "INVALID_CATALOGUE", "Download URL is not approved.")

    @staticmethod
    def _architecture() -> str:
        machine = platform.machine().lower()
        if machine in {"x86_64", "amd64"}:
            return "amd64"
        if machine in {"aarch64", "arm64"}:
            return "arm64"
        raise ManagementError(
            69,
            "UNSUPPORTED_ARCHITECTURE",
            f"No approved Llama runtime exists for architecture {machine}.",
        )

    def _model(self, identifier: str) -> dict[str, Any]:
        for model in self.model_catalog["models"]:
            if model["id"] == identifier:
                return model
        raise ManagementError(
            78,
            "MODEL_NOT_APPROVED",
            "LLAMA_MODEL_ID is not present in the approved model catalogue.",
        )

    def _existing_config(self) -> dict[str, Any] | None:
        path = self.paths.config
        if not path.exists() and self.paths.retained_config.exists():
            path = self.paths.retained_config
        if not path.exists():
            return None
        value = read_json(path)
        if set(value) != CONFIG_KEYS or value.get("schema_version") != 1:
            raise ManagementError(65, "INVALID_CONFIGURATION", "Llama configuration is invalid.")
        if value.get("port") != FIXED_PORT:
            raise ManagementError(78, "UNSAFE_CONFIGURATION", "Llama port must remain 8080.")
        return value

    @staticmethod
    def _integer(value: Any, *, name: str) -> int:
        if isinstance(value, bool):
            raise ManagementError(78, "INVALID_CONFIGURATION", f"{name} must be an integer.")
        try:
            converted = int(value)
        except (TypeError, ValueError) as exc:
            raise ManagementError(
                78, "INVALID_CONFIGURATION", f"{name} must be an integer."
            ) from exc
        if str(value).strip() != str(converted):
            raise ManagementError(78, "INVALID_CONFIGURATION", f"{name} must be an integer.")
        return converted

    def configuration(self, invocation: Invocation) -> Configuration:
        existing = self._existing_config()
        inputs = invocation.inputs

        def selected(input_name: str, env_name: str, existing_name: str, default: Any) -> Any:
            if input_name in inputs:
                return inputs[input_name]
            if env_name in os.environ and os.environ[env_name] != "":
                return os.environ[env_name]
            if existing is not None:
                return existing[existing_name]
            return default

        model_id = selected("model_id", "LLAMA_MODEL_ID", "model_id", DEFAULT_MODEL_ID)
        if not isinstance(model_id, str):
            raise ManagementError(78, "INVALID_CONFIGURATION", "model_id must be a string.")
        model = self._model(model_id)
        context_size = self._integer(
            selected(
                "context_size",
                "LLAMA_CONTEXT_SIZE",
                "context_size",
                DEFAULT_CONTEXT_SIZE,
            ),
            name="context_size",
        )
        if not 512 <= context_size <= model["context_size"]:
            raise ManagementError(
                78,
                "INVALID_CONFIGURATION",
                f"context_size must be between 512 and {model['context_size']}.",
            )
        default_threads = max(1, os.cpu_count() or 1)
        cpu_threads = self._integer(
            selected("cpu_threads", "LLAMA_CPU_THREADS", "threads", default_threads),
            name="cpu_threads",
        )
        if not 1 <= cpu_threads <= 1024:
            raise ManagementError(
                78, "INVALID_CONFIGURATION", "cpu_threads must be between 1 and 1024."
            )
        if "boot" in inputs:
            boot = inputs["boot"]
        elif os.environ.get("LLAMA_BOOT"):
            boot = os.environ["LLAMA_BOOT"]
        elif existing is not None:
            boot = (
                "enabled"
                if self._service_enabled() == "enabled"
                else "disabled"
            )
        else:
            boot = DEFAULT_BOOT
        if boot not in {"enabled", "disabled"}:
            raise ManagementError(
                78, "INVALID_CONFIGURATION", "boot must be enabled or disabled."
            )
        port = os.environ.get("LLAMA_PORT", str(FIXED_PORT))
        if port != str(FIXED_PORT):
            raise ManagementError(
                78, "INVALID_CONFIGURATION", "LLAMA_PORT is fixed at 8080."
            )
        architecture = self._architecture()
        runtime_release = self.build_catalog["release"]
        runtime_dir = self.paths.versions / f"{runtime_release}-{architecture}"
        model_path = self.paths.models / model["filename"]
        return Configuration(
            model_id,
            context_size,
            cpu_threads,
            str(boot),
            runtime_release,
            runtime_dir,
            model_path,
        )

    def _request(self, path: Path, operation: str) -> dict[str, Any]:
        if not path.is_absolute():
            raise ManagementError(65, "UNSAFE_REQUEST", "Request path must be absolute.")
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise ManagementError(66, "REQUEST_MISSING", "Request file does not exist.") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise ManagementError(
                73,
                "UNSAFE_REQUEST",
                "Request file must be a root-owned regular file without group or other access.",
            )
        value = read_json(path)
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
        if not required.issubset(value) or set(value) - allowed:
            raise ManagementError(65, "INVALID_REQUEST", "Request fields are invalid.")
        if (
            value["schema_version"] != 1
            or value["product_id"] != PRODUCT_ID
            or value["operation"] != operation
        ):
            raise ManagementError(65, "INVALID_REQUEST", "Request identity is invalid.")
        validate_uuid(value["correlation_id"], label="correlation_id")
        if value["requested_by"] not in {"operator", "ubuntu-zombie", "beep"}:
            raise ManagementError(65, "INVALID_REQUEST", "requested_by is invalid.")
        if not isinstance(value["inputs"], dict):
            raise ManagementError(65, "INVALID_REQUEST", "inputs must be an object.")
        if value["confirmation"] is not None and not isinstance(
            value["confirmation"], str
        ):
            raise ManagementError(65, "INVALID_REQUEST", "confirmation is invalid.")
        if operation == "uninstall":
            if not isinstance(value.get("retain_state"), bool):
                raise ManagementError(
                    65, "INVALID_REQUEST", "uninstall requires retain_state."
                )
        elif "retain_state" in value:
            raise ManagementError(
                65, "INVALID_REQUEST", "retain_state is accepted only for uninstall."
            )
        return value

    def invocation(self, args: argparse.Namespace) -> Invocation:
        unknown_environment = sorted(
            name
            for name in os.environ
            if name.startswith("LLAMA_") and name not in KNOWN_ENV
        )
        if unknown_environment:
            raise ManagementError(
                65,
                "UNKNOWN_ENVIRONMENT",
                f"Unknown Llama environment variable: {unknown_environment[0]}",
            )
        request: dict[str, Any] | None = None
        if args.request_file is not None:
            request = self._request(args.request_file, args.operation)
        correlation_id = (
            request["correlation_id"]
            if request is not None
            else args.correlation_id or str(uuid.uuid4())
        )
        validate_uuid(correlation_id, label="correlation_id")
        actor = request["requested_by"] if request is not None else "operator"
        inputs = dict(request["inputs"]) if request is not None else {}
        unknown_inputs = set(inputs) - OPERATION_INPUTS[args.operation]
        if unknown_inputs:
            raise ManagementError(
                65,
                "UNKNOWN_INPUT",
                f"Unknown input for {args.operation}: {sorted(unknown_inputs)[0]}",
            )
        confirmation = request["confirmation"] if request is not None else args.confirmation
        retain_state: bool | None = None
        if args.operation == "uninstall":
            if request is not None:
                retain_state = request["retain_state"]
            elif args.purge:
                retain_state = False
            else:
                retain_state = True
        non_interactive = bool(
            args.non_interactive or os.environ.get("LLAMA_NONINTERACTIVE") == "1"
        )
        return Invocation(
            args.operation,
            correlation_id,
            actor,
            inputs,
            confirmation,
            retain_state,
            args.dry_run,
            args.json,
            non_interactive,
            args.yes,
            args.plan_digest,
        )

    def load_marker(self, *, required: bool = False) -> dict[str, Any] | None:
        if not self.paths.marker.exists():
            if required:
                raise ManagementError(
                    66,
                    "INSTALLATION_MISSING",
                    "Llama is not installed with a valid ownership marker.",
                )
            return None
        try:
            metadata = self.paths.marker.lstat()
        except OSError as exc:
            raise ManagementError(73, "UNSAFE_MARKER", "Cannot inspect Llama marker.") from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o644
        ):
            raise ManagementError(
                73, "UNSAFE_MARKER", "Llama ownership marker metadata is invalid."
            )
        value = read_json(self.paths.marker)
        required_fields = {
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
        if set(value) != required_fields:
            raise ManagementError(65, "INVALID_MARKER", "Llama marker fields are invalid.")
        if (
            value["schema_version"] != 1
            or value["product_id"] != PRODUCT_ID
            or value["install_root"] != str(self.paths.install_root)
            or value["lifecycle_entrypoint"] != str(self.paths.entrypoint)
        ):
            raise ManagementError(73, "UNSAFE_MARKER", "Llama marker identity is invalid.")
        validate_uuid(value["instance_id"], label="marker instance_id")
        validate_version(value["version"])
        if not isinstance(value["source_revision"], str) or not value["source_revision"]:
            raise ManagementError(65, "INVALID_MARKER", "Marker revision is invalid.")
        if value["artifact_sha256"] is not None and (
            not isinstance(value["artifact_sha256"], str)
            or len(value["artifact_sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in value["artifact_sha256"]
            )
        ):
            raise ManagementError(65, "INVALID_MARKER", "Marker artifact digest is invalid.")
        return value

    def instance_id(self) -> str | None:
        try:
            marker = self.load_marker()
        except ManagementError:
            return None
        return str(marker["instance_id"]) if marker is not None else None

    @staticmethod
    def check(
        identifier: str,
        passed: bool,
        summary: str,
        remediation: str = "",
        *,
        warning: bool = False,
    ) -> dict[str, str]:
        return {
            "id": identifier,
            "status": "pass" if passed else "warn" if warning else "fail",
            "summary": summary,
            "remediation": "" if passed else remediation,
        }

    @staticmethod
    def steps_for(operation: str) -> list[dict[str, Any]]:
        steps: dict[str, list[tuple[str, str]]] = {
            "install": [
                ("ownership", "Validate ownership, platform, port, and catalogues"),
                ("identity", "Converge the llama-cpp service identity and paths"),
                ("runtime", "Install the checksum-verified pinned llama.cpp runtime"),
                ("model", "Install the approved checksum-verified model"),
                ("configuration", "Deploy product management, configuration, and unit"),
                ("health", "Apply boot intent and verify the loopback service"),
                ("marker", "Write the product ownership marker after successful checks"),
            ],
            "repair": [
                ("ownership", "Validate the existing product ownership marker"),
                ("integrity", "Reassert product-owned files, permissions, and catalogues"),
                ("health", "Restore the declared service state and verify boundaries"),
            ],
            "backup": [
                ("ownership", "Validate the existing product ownership marker"),
                ("archive", "Create and verify a product-scoped configuration backup"),
            ],
            "update": [
                ("ownership", "Validate ownership and the candidate product release"),
                ("backup", "Create a verified pre-update backup and rollback snapshot"),
                ("switch", "Install verified assets and atomically switch the runtime"),
                ("health", "Verify the updated loopback service before committing"),
            ],
            "rollback": [
                ("ownership", "Validate ownership and the saved rollback snapshot"),
                ("restore", "Restore the previous product files, config, and runtime link"),
                ("health", "Verify the restored loopback service"),
            ],
            "suspend": [
                ("ownership", "Validate the existing product ownership marker"),
                ("service", "Stop useful operation while preserving product state"),
            ],
            "resume": [
                ("ownership", "Validate product integrity while suspended"),
                ("service", "Resume the service according to declared boot intent"),
            ],
            "uninstall": [
                ("ownership", "Validate ownership before removing any resource"),
                ("service", "Stop and remove the product-owned service"),
                ("files", "Remove product runtime and configuration only"),
                ("state", "Retain or delete model state exactly as requested"),
            ],
        }
        return [
            {"id": identifier, "summary": summary, "mutates": True}
            for identifier, summary in steps.get(operation, [])
        ]

    def plan_digest(
        self,
        invocation: Invocation,
        steps: list[dict[str, Any]],
        configuration: Configuration | None,
    ) -> str:
        marker = self.load_marker()
        plan_inputs: dict[str, Any] = {}
        if configuration is not None:
            plan_inputs = {
                "model_id": configuration.model_id,
                "context_size": configuration.context_size,
                "cpu_threads": configuration.cpu_threads,
                "boot": configuration.boot,
            }
        if invocation.operation == "backup":
            plan_inputs["backup_destination"] = str(
                self._backup_destination(invocation)
            )
        if invocation.operation == "uninstall":
            plan_inputs["retain_state"] = invocation.retain_state
        value = {
            "product_id": PRODUCT_ID,
            "version": self.version,
            "operation": invocation.operation,
            "instance_id": marker["instance_id"] if marker is not None else None,
            "inputs": plan_inputs,
            "steps": steps,
        }
        return sha256_bytes(canonical_json(value))

    @contextmanager
    def _lock(self) -> Iterator[None]:
        self.paths.lock.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.paths.lock,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        try:
            try:
                fcntl.flock(descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ManagementError(
                    75,
                    "TARGET_BUSY",
                    "Another Llama lifecycle operation is running.",
                    retryable=True,
                ) from exc
            yield
        finally:
            os.close(descriptor)

    def run(self, invocation: Invocation) -> tuple[Result, int]:
        phase = _operation_phase(invocation.operation, dry_run=invocation.dry_run)
        result = Result(
            invocation.operation,
            invocation.correlation_id,
            self.version,
            self.instance_id(),
            phase,
        )
        if invocation.operation == "describe":
            result.details = {"descriptor": self.descriptor}
            return result, 0
        if invocation.operation in {"status", "verify", "doctor"}:
            checks = self.verify_checks(probe_runtime=invocation.operation != "doctor")
            result.checks = checks
            failed = any(check["status"] == "fail" for check in checks)
            warned = any(check["status"] == "warn" for check in checks)
            result.status = "degraded" if failed or warned else "ok"
            result.details = self._status_details()
            if invocation.operation == "verify" and failed:
                return result, 1
            return result, 0

        configuration = (
            self.configuration(invocation)
            if invocation.operation in CONFIGURATION_OPERATIONS
            else None
        )
        steps = self.steps_for(invocation.operation)
        result.steps = steps
        result.plan_digest = self.plan_digest(invocation, steps, configuration)
        destructive = (
            invocation.operation == "uninstall" and invocation.retain_state is False
        )
        result.requires_confirmation = True
        if invocation.dry_run:
            if configuration is not None:
                result.details = {"runtime": configuration.runtime_release}
            if destructive:
                result.required_inputs = [{"name": "confirmation", "secret": False}]
            return result, 0
        if invocation.supplied_plan_digest is not None:
            if invocation.supplied_plan_digest != result.plan_digest:
                raise ManagementError(
                    78,
                    "PLAN_CHANGED",
                    "The supplied plan digest no longer matches current state and inputs.",
                )
        if destructive and invocation.confirmation != DELETE_CONFIRMATION:
            raise ManagementError(
                64,
                "DESTRUCTIVE_CONFIRMATION_REQUIRED",
                f"Complete removal requires confirmation: {DELETE_CONFIRMATION}",
            )
        if not invocation.assume_yes:
            if invocation.non_interactive:
                raise ManagementError(
                    64,
                    "CONFIRMATION_REQUIRED",
                    "A mutating non-interactive operation requires --yes.",
                )
            answer = input("Type YES to execute this Llama lifecycle plan: ")
            if answer != "YES":
                raise ManagementError(64, "CONFIRMATION_REQUIRED", "Operation cancelled.")
        if os.geteuid() != 0:
            raise ManagementError(
                73, "ROOT_REQUIRED", f"{invocation.operation} requires root."
            )
        event_id = str(uuid.uuid4())
        previous_version: str | None = None
        changed_resources: list[str] = []
        backup_path: str | None = None
        with self._lock():
            recomputed = self.plan_digest(invocation, steps, configuration)
            if recomputed != result.plan_digest:
                raise ManagementError(
                    78, "PLAN_CHANGED", "Host state changed while acquiring the product lock."
                )
            if invocation.operation == "install":
                changed_resources, previous_version = self._execute_install(
                    invocation, configuration, snapshot_on_change=True
                )
            elif invocation.operation == "repair":
                changed_resources, previous_version = self._execute_repair(
                    invocation, configuration
                )
            elif invocation.operation == "backup":
                changed_resources, previous_version, backup_path = self._execute_backup(
                    invocation
                )
            elif invocation.operation == "update":
                changed_resources, previous_version, backup_path = self._execute_update(
                    invocation, configuration
                )
            elif invocation.operation == "rollback":
                changed_resources, previous_version = self._execute_rollback(invocation)
            elif invocation.operation == "suspend":
                changed_resources, previous_version = self._execute_suspend()
            elif invocation.operation == "resume":
                changed_resources, previous_version = self._execute_resume()
            elif invocation.operation == "uninstall":
                changed_resources, previous_version = self._execute_uninstall(invocation)
            else:
                raise ManagementError(65, "UNKNOWN_OPERATION", "Unknown operation.")
            result.changed = bool(changed_resources)
            marker = self.load_marker()
            result.instance_id = (
                str(marker["instance_id"]) if marker is not None else result.instance_id
            )
            result.details = {}
            if backup_path is not None:
                result.details["backup"] = {"path": backup_path}
            receipt = self._write_receipt(
                result,
                previous_version=previous_version,
                changed_resources=changed_resources,
                event_id=event_id,
            )
            result.receipt = receipt
            self._append_audit(
                invocation,
                event_id=event_id,
                result_status=result.status,
                changed=result.changed,
                receipt_digest=receipt["digest"],
                instance_id=result.instance_id,
            )
        return result, 0

    def _status_details(self) -> dict[str, Any]:
        marker: dict[str, Any] | None
        try:
            marker = self.load_marker()
        except ManagementError:
            marker = None
        lifecycle = "missing"
        if marker is not None:
            lifecycle = "retained" if self.paths.retained.exists() else (
                "suspended" if self.paths.suspended.exists() else "active"
            )
        elif self._legacy_installation_valid():
            lifecycle = "legacy"
        config: dict[str, Any] = {}
        try:
            existing = self._existing_config()
            if existing is not None:
                config = {
                    "model_id": existing["model_id"],
                    "context_size": existing["context_size"],
                    "cpu_threads": existing["threads"],
                    "boot": self._service_enabled(),
                    "url": f"http://127.0.0.1:{FIXED_PORT}/v1",
                }
        except ManagementError:
            pass
        return {
            "lifecycle": lifecycle,
            "installed_version": marker["version"] if marker is not None else None,
            "configuration": config,
        }

    def verify_checks(self, *, probe_runtime: bool = True) -> list[dict[str, str]]:
        checks: list[dict[str, str]] = []
        try:
            marker = self.load_marker(required=True)
        except ManagementError as exc:
            checks.append(
                self.check(
                    "ownership_marker",
                    False,
                    exc.message,
                    "Run the product install, or restore its valid ownership marker.",
                )
            )
            return checks

        checks.append(self.check("ownership_marker", True, "Ownership marker is valid."))
        checks.append(
            self.check(
                "log_ownership",
                self._log_ownership_valid(),
                "Retained audit evidence has a protected ownership marker.",
                "Restore the product-owned log marker.",
            )
        )
        retained = self.paths.retained.exists()
        suspended = self.paths.suspended.exists()
        if retained:
            checks.append(
                self.check(
                    "retained_state",
                    False,
                    "Product runtime is removed and model state is retained.",
                    "Run install to restore the product or purge retained state.",
                    warning=True,
                )
            )
            return checks
        expected_files = (
            (self.paths.descriptor, 0o644, "descriptor"),
            (self.paths.config, 0o644, "configuration"),
            (self.paths.entrypoint, 0o755, "lifecycle_entrypoint"),
            (self.paths.manager, 0o755, "runtime_manager"),
            (self.paths.unit, 0o644, "systemd_unit"),
            (self.paths.logrotate, 0o644, "log_rotation"),
        )
        for path, mode, identifier in expected_files:
            valid = self._root_file(path, mode)
            checks.append(
                self.check(
                    identifier,
                    valid,
                    f"{path} is present with protected ownership and mode.",
                    "Run llama-manage repair after reconciling unsafe ownership.",
                )
            )
        account_valid = self._account_valid()
        checks.append(
            self.check(
                "service_identity",
                account_valid,
                "The llama-cpp account has the declared restricted identity.",
                "Reconcile the llama-cpp account before running repair.",
            )
        )
        config: dict[str, Any] | None = None
        try:
            config = self._existing_config()
            if config is None:
                raise ManagementError(66, "CONFIGURATION_MISSING", "Config is missing.")
            configuration_valid = self._configuration_paths_valid(config)
        except ManagementError:
            configuration_valid = False
        checks.append(
            self.check(
                "configuration_boundary",
                configuration_valid,
                "Configuration fixes the loopback listener and product-owned paths.",
                "Restore the product-owned configuration with repair.",
            )
        )
        runtime_valid = False
        model_valid = False
        if config is not None and configuration_valid:
            runtime_path = Path(config["runtime_dir"])
            runtime_valid = self._runtime_valid(runtime_path)
            try:
                model_record = self._model(str(config["model_id"]))
                model_path = Path(config["model_path"])
                model_valid = (
                    model_path.is_file()
                    and model_path.stat().st_size == model_record["size_bytes"]
                    and sha256_file(model_path) == model_record["sha256"]
                )
            except (ManagementError, OSError):
                model_valid = False
        checks.append(
            self.check(
                "runtime_integrity",
                runtime_valid,
                "Pinned llama.cpp runtime tree passes its checksum manifest.",
                "Run repair to restore the pinned runtime.",
            )
        )
        checks.append(
            self.check(
                "model_integrity",
                model_valid,
                "Approved model size and checksum are valid.",
                "Run repair to restore the approved model.",
            )
        )
        drop_in_root = self.paths.unit.with_name(f"{self.paths.unit.name}.d")
        drop_ins = list(drop_in_root.iterdir()) if drop_in_root.is_dir() else []
        checks.append(
            self.check(
                "systemd_drop_ins",
                not drop_ins,
                "The Llama unit has no unmanaged systemd drop-ins.",
                "Remove or reconcile unmanaged llama-server.service drop-ins.",
            )
        )
        active = self._service_active()
        if suspended:
            checks.append(
                self.check(
                    "suspension",
                    not active,
                    "Suspended Llama service is stopped.",
                    "Stop llama-server.service before repairing suspension state.",
                )
            )
        elif config is not None and self._service_enabled() == "enabled":
            checks.append(
                self.check(
                    "service_active",
                    active,
                    "Llama service is active.",
                    "Run llama-manage repair or inspect journalctl -u llama-server.",
                )
            )
        else:
            checks.append(
                self.check(
                    "service_active",
                    active,
                    "Llama service is intentionally not enabled at boot.",
                    "Run llama-manage resume to start it when needed.",
                    warning=not active,
                )
            )
        if probe_runtime and active:
            healthy = self._health()
            checks.append(
                self.check(
                    "loopback_health",
                    healthy,
                    "Llama health endpoint responds on 127.0.0.1:8080.",
                    "Inspect journalctl -u llama-server and run repair.",
                )
            )
        if marker["version"] != self.version:
            checks.append(
                self.check(
                    "source_version",
                    False,
                    "Invoked source and installed product versions differ.",
                    "Use update to switch versions; repair does not cross versions.",
                    warning=True,
                )
            )
        return checks

    def _post_install_checks(
        self, configuration: Configuration, *, probe_runtime: bool
    ) -> list[dict[str, str]]:
        existing = self._existing_config()
        checks = [
            self.check(
                "descriptor",
                self._root_file(self.paths.descriptor, 0o644),
                "Installed descriptor is protected.",
                "Restore the product descriptor.",
            ),
            self.check(
                "log_ownership",
                self._log_ownership_valid(),
                "Retained audit evidence has a protected ownership marker.",
                "Restore the product-owned log marker.",
            ),
            self.check(
                "configuration",
                self._root_file(self.paths.config, 0o644)
                and existing is not None
                and self._configuration_paths_valid(existing),
                "Configuration retains the declared loopback boundary.",
                "Restore the product configuration.",
            ),
            self.check(
                "lifecycle_entrypoint",
                self._root_file(self.paths.entrypoint, 0o755),
                "Lifecycle entrypoint is protected.",
                "Restore the lifecycle entrypoint.",
            ),
            self.check(
                "runtime_manager",
                self._root_file(self.paths.manager, 0o755),
                "Runtime manager is protected.",
                "Restore llama-manager.",
            ),
            self.check(
                "systemd_unit",
                self._root_file(self.paths.unit, 0o644),
                "Systemd unit is protected.",
                "Restore llama-server.service.",
            ),
            self.check(
                "service_identity",
                self._account_valid(),
                "The llama-cpp identity matches its declaration.",
                "Reconcile the llama-cpp account.",
            ),
            self.check(
                "runtime_integrity",
                self._runtime_valid(configuration.runtime_dir),
                "Pinned runtime integrity is valid.",
                "Restore the pinned runtime.",
            ),
        ]
        model = self._model(configuration.model_id)
        model_valid = (
            configuration.model_path.is_file()
            and configuration.model_path.stat().st_size == model["size_bytes"]
            and sha256_file(configuration.model_path) == model["sha256"]
        )
        checks.append(
            self.check(
                "model_integrity",
                model_valid,
                "Approved model integrity is valid.",
                "Restore the approved model.",
            )
        )
        if configuration.boot == "enabled" and not self.paths.suspended.exists():
            checks.append(
                self.check(
                    "service_enabled",
                    self._service_enabled() == "enabled",
                    "Llama service is enabled at boot.",
                    "Enable llama-server.service.",
                )
            )
            checks.append(
                self.check(
                    "service_active",
                    self._service_active(),
                    "Llama service is active.",
                    "Inspect llama-server.service.",
                )
            )
            if probe_runtime:
                checks.append(
                    self.check(
                        "loopback_health",
                        self._health(),
                        "Loopback health endpoint responds.",
                        "Inspect llama-server.service.",
                    )
                )
        elif configuration.boot == "disabled" and not self.paths.suspended.exists():
            checks.extend(
                (
                    self.check(
                        "service_disabled",
                        self._service_enabled() != "enabled",
                        "Llama service is disabled at boot.",
                        "Disable llama-server.service.",
                    ),
                    self.check(
                        "service_stopped",
                        not self._service_active(),
                        "Llama service is stopped.",
                        "Stop llama-server.service.",
                    ),
                )
            )
        return checks

    @staticmethod
    def _root_file(path: Path, mode: int) -> bool:
        try:
            metadata = path.lstat()
        except OSError:
            return False
        return (
            stat.S_ISREG(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            and metadata.st_uid == 0
            and metadata.st_gid == 0
            and stat.S_IMODE(metadata.st_mode) == mode
        )

    def _account_valid(self) -> bool:
        try:
            account = pwd.getpwnam("llama-cpp")
            group = grp.getgrnam("llama-cpp")
        except KeyError:
            return False
        if (
            account.pw_gid != group.gr_gid
            or account.pw_dir != str(self.paths.state_root)
            or account.pw_shell not in {"/usr/sbin/nologin", "/bin/false"}
        ):
            return False
        supplementary = {
            item.gr_name for item in grp.getgrall() if "llama-cpp" in item.gr_mem
        }
        return not supplementary

    @staticmethod
    def _directory_matches(path: Path, mode: int, uid: int, gid: int) -> bool:
        try:
            metadata = path.lstat()
        except OSError:
            return False
        return (
            stat.S_ISDIR(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            and metadata.st_uid == uid
            and metadata.st_gid == gid
            and stat.S_IMODE(metadata.st_mode) == mode
        )

    def _legacy_directories_valid(self) -> bool:
        try:
            account = pwd.getpwnam("llama-cpp")
            group = grp.getgrnam("llama-cpp")
        except KeyError:
            return False
        expected = (
            (self.paths.install_root, 0o755, 0, 0),
            (self.paths.versions, 0o755, 0, 0),
            (self.paths.configuration_root, 0o755, 0, 0),
            (self.paths.state_root, 0o755, 0, 0),
            (self.paths.models, 0o750, account.pw_uid, group.gr_gid),
            (self.paths.runtime_state, 0o750, account.pw_uid, group.gr_gid),
            (self.paths.log_root, 0o750, account.pw_uid, group.gr_gid),
            (self.paths.cache_root, 0o755, 0, 0),
        )
        return all(
            self._directory_matches(path, mode, uid, gid)
            for path, mode, uid, gid in expected
        )

    def _configuration_paths_valid(self, value: dict[str, Any]) -> bool:
        if set(value) != CONFIG_KEYS or value["schema_version"] != 1:
            return False
        if value["port"] != FIXED_PORT:
            return False
        runtime = Path(str(value["runtime_dir"]))
        model = Path(str(value["model_path"]))
        if runtime != self.paths.current:
            return False
        if not model.is_absolute() or not _is_relative_to(model, self.paths.models):
            return False
        if not isinstance(value["model_id"], str):
            return False
        try:
            model_record = self._model(value["model_id"])
        except ManagementError:
            return False
        return (
            model.name == model_record["filename"]
            and isinstance(value["context_size"], int)
            and not isinstance(value["context_size"], bool)
            and 512 <= value["context_size"] <= model_record["context_size"]
            and isinstance(value["threads"], int)
            and not isinstance(value["threads"], bool)
            and 1 <= value["threads"] <= 1024
            and value["runtime_release"] == self.build_catalog["release"]
        )

    def _runtime_valid(self, runtime: Path) -> bool:
        manifest = runtime / ".tree-sha256"
        if not (runtime.is_dir() and (runtime / "llama-server").is_file()):
            return False
        if not os.access(runtime / "llama-server", os.X_OK) or not manifest.is_file():
            return False
        try:
            expected: dict[str, str] = {}
            for line in manifest.read_text(encoding="utf-8").splitlines():
                digest, separator, name = line.partition("  ")
                if (
                    not separator
                    or len(digest) != 64
                    or any(character not in "0123456789abcdef" for character in digest)
                ):
                    return False
                relative = Path(name)
                if relative.is_absolute() or ".." in relative.parts or name in expected:
                    return False
                expected[name] = digest
            actual = {
                path.relative_to(runtime).as_posix(): sha256_file(path)
                for path in sorted(runtime.rglob("*"))
                if path.is_file() and not path.is_symlink() and path != manifest
            }
        except (OSError, UnicodeError, ManagementError):
            return False
        return bool(expected) and actual == expected

    def _service_active(self) -> bool:
        result = self._run(
            ["systemctl", "is-active", "--quiet", "llama-server.service"],
            check=False,
            timeout=15,
        )
        return result.returncode == 0

    def _service_enabled(self) -> str:
        result = self._run(
            ["systemctl", "is-enabled", "llama-server.service"],
            check=False,
            timeout=15,
        )
        return result.stdout.strip() if result.returncode == 0 else "disabled"

    def _stop_service(self, *, disable: bool) -> bool:
        """Stop the service and verify the requested systemd post-condition."""
        was_active = self._service_active()
        was_enabled = disable and self._service_enabled() == "enabled"
        if not was_active and not was_enabled:
            return False
        command = (
            ["systemctl", "disable", "--now", "llama-server.service"]
            if disable
            else ["systemctl", "stop", "llama-server.service"]
        )
        self._run(command, check=False)
        active = self._service_active()
        enabled = disable and self._service_enabled() == "enabled"
        if active or enabled:
            raise ManagementError(
                1,
                "SERVICE_STOP_FAILED",
                "llama-server.service did not reach the requested stopped state.",
                recovery=["Inspect systemctl status llama-server.service."],
            )
        return True

    @staticmethod
    def _health() -> bool:
        connection = http.client.HTTPConnection("127.0.0.1", FIXED_PORT, timeout=2)
        try:
            connection.request("GET", "/health", headers={"Accept": "application/json"})
            response = connection.getresponse()
            response.read(1024)
            return 200 <= response.status < 300
        except (OSError, http.client.HTTPException):
            return False
        finally:
            connection.close()

    @staticmethod
    def _run(
        command: list[str],
        *,
        check: bool = True,
        timeout: int = 120,
    ) -> subprocess.CompletedProcess[str]:
        try:
            return subprocess.run(
                command,
                check=check,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
        except FileNotFoundError as exc:
            raise ManagementError(
                69, "DEPENDENCY_MISSING", f"Required command is unavailable: {command[0]}"
            ) from exc
        except subprocess.TimeoutExpired as exc:
            raise ManagementError(
                75,
                "COMMAND_TIMEOUT",
                f"Timed out running required command: {command[0]}",
                retryable=True,
            ) from exc
        except subprocess.CalledProcessError as exc:
            detail = (exc.stderr or "").strip().splitlines()
            suffix = f": {detail[-1]}" if detail else ""
            raise ManagementError(
                1, "COMMAND_FAILED", f"Required command failed: {command[0]}{suffix}"
            ) from exc

    def _platform_preflight(self) -> None:
        os_release = Path("/etc/os-release")
        try:
            fields = {}
            for line in os_release.read_text(encoding="utf-8").splitlines():
                key, separator, raw = line.partition("=")
                if separator:
                    fields[key] = raw.strip().strip('"')
        except OSError as exc:
            raise ManagementError(69, "UNSUPPORTED_PLATFORM", "Cannot identify this host.") from exc
        if fields.get("ID") != "ubuntu" or fields.get("VERSION_ID") not in {
            "22.04",
            "24.04",
        }:
            raise ManagementError(
                69,
                "UNSUPPORTED_PLATFORM",
                "Llama supports Ubuntu 22.04 and 24.04 LTS only.",
            )
        self._architecture()

    def _port_preflight(self) -> None:
        if self._service_active():
            return
        candidate = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            candidate.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            candidate.bind(("127.0.0.1", FIXED_PORT))
        except OSError as exc:
            raise ManagementError(
                73,
                "PORT_CONFLICT",
                "Port 8080 is already used by a service not proven to be Llama.",
            ) from exc
        finally:
            candidate.close()

    @staticmethod
    def _legacy_marker(path: Path) -> bool:
        try:
            metadata = path.lstat()
            value = path.read_text(encoding="utf-8")
        except (OSError, UnicodeError):
            return False
        return (
            stat.S_ISREG(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            and metadata.st_uid == 0
            and metadata.st_gid == 0
            and stat.S_IMODE(metadata.st_mode) == 0o644
            and value == "component=llama\nformat=1\n"
        )

    def _legacy_installation_valid(self) -> bool:
        markers = (
            self.paths.configuration_root / "managed-by-ubuntu-zombie",
            self.paths.state_root / "managed-by-ubuntu-zombie",
        )
        if not all(self._legacy_marker(path) for path in markers):
            return False
        try:
            config = self._existing_config()
            unit_digest = sha256_file(self.paths.unit)
            build_content = (
                self.source_root / "payload/etc/llama-builds.json"
            ).read_bytes()
            model_content = (
                self.source_root / "payload/etc/llama-models.json"
            ).read_bytes()
        except ManagementError:
            return False
        except OSError:
            return False
        if config is None or not self._configuration_paths_valid(config):
            return False
        model = self._model(str(config["model_id"]))
        model_path = Path(str(config["model_path"]))
        try:
            model_valid = (
                model_path.is_file()
                and model_path.stat().st_size == model["size_bytes"]
                and sha256_file(model_path) == model["sha256"]
            )
        except (OSError, ManagementError):
            return False
        return (
            model_valid
            and self._account_valid()
            and self._legacy_directories_valid()
            and self._root_file(self.paths.manager, 0o755)
            and self._root_file(self.paths.unit, 0o644)
            and unit_digest == LEGACY_UNIT_SHA256
            and self._file_matches(
                self.paths.configuration_root / "builds.json",
                build_content,
                0o644,
                0,
                0,
            )
            and self._file_matches(
                self.paths.configuration_root / "models.json",
                model_content,
                0o644,
                0,
                0,
            )
            and self.paths.current.is_symlink()
            and self._runtime_valid(self.paths.current.resolve())
            and not self.paths.entrypoint.exists()
            and not self.paths.logrotate.exists()
        )

    def _log_ownership_valid(self) -> bool:
        try:
            metadata = self.paths.log_root.lstat()
        except OSError:
            return False
        content = b"product_id=llama\nformat=1\n"
        return (
            stat.S_ISDIR(metadata.st_mode)
            and not stat.S_ISLNK(metadata.st_mode)
            and metadata.st_uid == 0
            and stat.S_IMODE(metadata.st_mode) == 0o750
            and self._file_matches(self.paths.log_ownership, content, 0o600, 0, 0)
        )

    def _transaction_instance(self) -> str | None:
        if not self.paths.transaction.exists():
            return None
        try:
            metadata = self.paths.transaction.lstat()
            value = read_json(self.paths.transaction)
        except (OSError, ManagementError):
            return None
        if (
            not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o600
            or set(value) != {"schema_version", "product_id", "instance_id"}
            or value["schema_version"] != 1
            or value["product_id"] != PRODUCT_ID
        ):
            return None
        try:
            return validate_uuid(value["instance_id"], label="transaction instance_id")
        except ManagementError:
            return None

    def _collision_preflight(self) -> tuple[dict[str, Any] | None, str | None]:
        marker = self.load_marker()
        if marker is not None:
            return marker, None
        transaction = self._transaction_instance()
        if transaction is not None:
            return None, transaction
        if self._legacy_installation_valid():
            return None, str(uuid.uuid4())
        resources = (
            self.paths.install_root,
            self.paths.configuration_root,
            self.paths.state_root,
            self.paths.log_root,
            self.paths.cache_root,
            self.paths.unit,
            self.paths.logrotate,
            self.paths.entrypoint,
            self.paths.manager,
        )
        occupied_paths = [
            path for path in resources if path.exists() or path.is_symlink()
        ]
        if self.paths.log_root in occupied_paths and self._log_ownership_valid():
            occupied_paths.remove(self.paths.log_root)
        occupied = [str(path) for path in occupied_paths]
        try:
            pwd.getpwnam("llama-cpp")
        except KeyError:
            pass
        else:
            occupied.append("account:llama-cpp")
        if occupied:
            raise ManagementError(
                73,
                "UNSAFE_COLLISION",
                f"Refusing to adopt unmanaged Llama resource: {occupied[0]}",
            )
        return None, str(uuid.uuid4())

    @staticmethod
    def _ensure_directory(
        path: Path, mode: int, uid: int, gid: int, changed: list[str]
    ) -> None:
        if path.is_symlink():
            raise ManagementError(73, "UNSAFE_COLLISION", f"Directory is a symlink: {path}")
        created = not path.exists()
        path.mkdir(parents=True, exist_ok=True)
        metadata = path.stat()
        if not stat.S_ISDIR(metadata.st_mode):
            raise ManagementError(73, "UNSAFE_COLLISION", f"Path is not a directory: {path}")
        if (
            created
            or stat.S_IMODE(metadata.st_mode) != mode
            or metadata.st_uid != uid
            or metadata.st_gid != gid
        ):
            os.chown(path, uid, gid)
            os.chmod(path, mode)
            changed.append(str(path))

    def _ensure_transaction(self, instance_id: str, changed: list[str]) -> None:
        value = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "instance_id": instance_id,
        }
        content = canonical_json(value) + b"\n"
        if not self._file_matches(self.paths.transaction, content, 0o600, 0, 0):
            atomic_write(self.paths.transaction, content, mode=0o600)
            changed.append(str(self.paths.transaction))

    def _ensure_log_ownership(self, changed: list[str]) -> None:
        content = b"product_id=llama\nformat=1\n"
        if not self._file_matches(self.paths.log_ownership, content, 0o600, 0, 0):
            atomic_write(self.paths.log_ownership, content, mode=0o600)
            changed.append(str(self.paths.log_ownership))

    @staticmethod
    def _file_matches(
        path: Path, content: bytes, mode: int, uid: int, gid: int
    ) -> bool:
        try:
            metadata = path.lstat()
            return (
                stat.S_ISREG(metadata.st_mode)
                and not stat.S_ISLNK(metadata.st_mode)
                and metadata.st_uid == uid
                and metadata.st_gid == gid
                and stat.S_IMODE(metadata.st_mode) == mode
                and path.read_bytes() == content
            )
        except OSError:
            return False

    def _install_file(
        self,
        source: Path,
        destination: Path,
        mode: int,
        changed: list[str],
        *,
        uid: int = 0,
        gid: int = 0,
    ) -> None:
        try:
            content = source.read_bytes()
        except OSError as exc:
            raise ManagementError(66, "SOURCE_MISSING", f"Source asset is missing: {source}") from exc
        if not self._file_matches(destination, content, mode, uid, gid):
            atomic_write(destination, content, mode=mode, uid=uid, gid=gid)
            changed.append(str(destination))

    def _ensure_account(self, changed: list[str]) -> tuple[int, int]:
        try:
            account = pwd.getpwnam("llama-cpp")
        except KeyError:
            self._run(
                [
                    "adduser",
                    "--system",
                    "--group",
                    "--home",
                    str(self.paths.state_root),
                    "--no-create-home",
                    "llama-cpp",
                ]
            )
            changed.append("account:llama-cpp")
            account = pwd.getpwnam("llama-cpp")
        try:
            group = grp.getgrnam("llama-cpp")
        except KeyError as exc:
            raise ManagementError(
                73, "UNSAFE_COLLISION", "llama-cpp exists without its declared group."
            ) from exc
        if not self._account_valid():
            raise ManagementError(
                73,
                "UNSAFE_COLLISION",
                "The existing llama-cpp account does not match the declared identity.",
            )
        return account.pw_uid, group.gr_gid

    def _source_revision(self) -> str:
        digest = hashlib.sha256()
        for path in self._deployment_files(self.source_root):
            relative = path.relative_to(self.source_root).as_posix()
            digest.update(relative.encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
        return f"source-tree-sha256:{digest.hexdigest()}"

    def _product_tree_matches(self) -> bool:
        if not self.paths.product_root.is_dir():
            return False
        installed_version = self.paths.product_root / "VERSION"
        try:
            return (
                installed_version.read_text(encoding="utf-8").strip() == self.version
                and self._tree_digest(self.paths.product_root)
                == self._deployment_digest(self.source_root)
            )
        except OSError:
            return False

    @staticmethod
    def _deployment_files(root: Path) -> list[Path]:
        paths = [root / "PRODUCT.json", root / "VERSION"]
        for relative in ("scripts", "payload"):
            directory = root / relative
            if directory.is_dir():
                paths.extend(
                    path
                    for path in directory.rglob("*")
                    if path.is_file()
                    and "__pycache__" not in path.parts
                    and path.suffix != ".pyc"
                )
        return sorted(paths)

    def _deployment_digest(self, root: Path) -> str:
        digest = hashlib.sha256()
        for path in self._deployment_files(root):
            relative = path.relative_to(root).as_posix()
            digest.update(relative.encode("utf-8") + b"\0")
            digest.update(path.read_bytes())
        return digest.hexdigest()

    def _tree_digest(self, root: Path) -> str:
        return self._deployment_digest(root)

    @staticmethod
    def _protect_tree(root: Path) -> None:
        for path in sorted(root.rglob("*"), reverse=True):
            if path.is_symlink():
                raise ManagementError(73, "UNSAFE_SOURCE", "Product tree contains a symlink.")
            if path.is_file():
                executable = path.name in {"manage.sh", "llama-manager"}
                os.chmod(path, 0o755 if executable else 0o644)
                os.chown(path, 0, 0)
            elif path.is_dir():
                os.chmod(path, 0o755)
                os.chown(path, 0, 0)
        os.chmod(root, 0o755)
        os.chown(root, 0, 0)

    def _deploy_product(self, changed: list[str]) -> None:
        if self._product_tree_matches():
            return
        stage = Path(tempfile.mkdtemp(prefix=".product-stage.", dir=self.paths.install_root))
        try:
            for relative in ("PRODUCT.json", "VERSION"):
                shutil.copy2(self.source_root / relative, stage / relative)
            ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "dist")
            shutil.copytree(
                self.source_root / "scripts", stage / "scripts", ignore=ignore
            )
            shutil.copytree(
                self.source_root / "payload", stage / "payload", ignore=ignore
            )
            self._protect_tree(stage)
            old = self.paths.install_root / f".product-old.{uuid.uuid4().hex}"
            if self.paths.product_root.exists():
                os.replace(self.paths.product_root, old)
            os.replace(stage, self.paths.product_root)
            if old.exists():
                shutil.rmtree(old)
            changed.append(str(self.paths.product_root))
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def _download_verified(
        self,
        url: str,
        expected_digest: str,
        destination: Path,
        *,
        expected_size: int | None = None,
    ) -> None:
        if destination.is_file():
            try:
                size_valid = expected_size is None or destination.stat().st_size == expected_size
            except OSError:
                size_valid = False
            if size_valid and sha256_file(destination) == expected_digest:
                return
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_name(f".{destination.name}.{uuid.uuid4().hex}.part")
        request = urllib.request.Request(
            url, headers={"User-Agent": "ubuntu-zombie-llama/1"}
        )
        opener = urllib.request.build_opener(_SafeRedirectHandler())
        digest = hashlib.sha256()
        total = 0
        try:
            with opener.open(request, timeout=60) as response:
                self._validate_redirect(response.geturl())
                with temporary.open("xb") as output:
                    while True:
                        chunk = response.read(1024 * 1024)
                        if not chunk:
                            break
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise ManagementError(
                                78, "DOWNLOAD_TOO_LARGE", "Downloaded asset exceeded its limit."
                            )
                        output.write(chunk)
                        digest.update(chunk)
                    output.flush()
                    os.fsync(output.fileno())
            if expected_size is not None and total != expected_size:
                raise ManagementError(78, "SIZE_MISMATCH", "Downloaded asset size is invalid.")
            if digest.hexdigest() != expected_digest:
                raise ManagementError(
                    78, "CHECKSUM_MISMATCH", "Downloaded asset checksum is invalid."
                )
            os.chmod(temporary, 0o640)
            os.chown(temporary, 0, 0)
            os.replace(temporary, destination)
        except ManagementError:
            temporary.unlink(missing_ok=True)
            raise
        except (OSError, urllib.error.URLError) as exc:
            temporary.unlink(missing_ok=True)
            raise ManagementError(
                75, "DOWNLOAD_FAILED", "Could not download a pinned Llama asset.", retryable=True
            ) from exc

    @staticmethod
    def _validate_redirect(url: str) -> None:
        _validate_redirect_url(url)

    @staticmethod
    def _safe_archive_member(member: tarfile.TarInfo) -> bool:
        path = PurePosixPath(member.name)
        if path.is_absolute() or ".." in path.parts or "\x00" in member.name:
            return False
        if member.isdev() or member.isfifo():
            return False
        if member.issym() or member.islnk():
            target = PurePosixPath(member.linkname)
            if target.is_absolute() or "\x00" in member.linkname:
                return False
            resolved: list[str] = []
            base = path.parent if member.issym() else PurePosixPath()
            for part in (base / target).parts:
                if part in {"", "."}:
                    continue
                if part == "..":
                    if not resolved:
                        return False
                    resolved.pop()
                else:
                    resolved.append(part)
        return True

    def _extract_runtime(
        self, archive: Path, archive_root: str, destination: Path
    ) -> None:
        stage = Path(tempfile.mkdtemp(prefix=".runtime-stage.", dir=self.paths.versions))
        try:
            try:
                with tarfile.open(archive, "r:gz") as bundle:
                    members = bundle.getmembers()
                    if not members or not all(
                        self._safe_archive_member(member) for member in members
                    ):
                        raise ManagementError(
                            78, "UNSAFE_ARCHIVE", "Pinned runtime archive is unsafe."
                        )
                    bundle.extractall(stage)
            except (OSError, tarfile.TarError) as exc:
                raise ManagementError(
                    78, "INVALID_ARCHIVE", "Pinned runtime archive is invalid."
                ) from exc
            extracted = stage / archive_root
            for binary in ("llama-server", "llama-cli", "llama-bench"):
                path = extracted / binary
                if not path.is_file() or not os.access(path, os.X_OK):
                    raise ManagementError(
                        78, "INVALID_ARCHIVE", f"Pinned runtime is missing {binary}."
                    )
            for path in stage.rglob("*"):
                if path.is_symlink():
                    try:
                        path.resolve(strict=True).relative_to(stage.resolve())
                    except (OSError, ValueError) as exc:
                        raise ManagementError(
                            78, "UNSAFE_ARCHIVE", "Runtime symlink escapes its archive."
                        ) from exc
            manifest_lines = []
            for path in sorted(extracted.rglob("*")):
                if path.is_file() and not path.is_symlink():
                    relative = path.relative_to(extracted).as_posix()
                    manifest_lines.append(f"{sha256_file(path)}  {relative}\n")
            atomic_write(
                extracted / ".tree-sha256",
                "".join(manifest_lines).encode("utf-8"),
                mode=0o444,
            )
            for path in sorted(extracted.rglob("*"), reverse=True):
                if path.is_symlink():
                    continue
                os.chown(path, 0, 0)
                if path.is_file():
                    os.chmod(path, stat.S_IMODE(path.stat().st_mode) & ~0o222)
                elif path.is_dir():
                    os.chmod(path, 0o555)
            os.chown(extracted, 0, 0)
            os.chmod(extracted, 0o555)
            if destination.exists():
                shutil.rmtree(destination)
            os.replace(extracted, destination)
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def _install_runtime(
        self, configuration: Configuration, changed: list[str]
    ) -> None:
        if self._runtime_valid(configuration.runtime_dir):
            self._switch_runtime(configuration.runtime_dir, changed)
            return
        architecture = self._architecture()
        asset = self.build_catalog["assets"][architecture]
        archive = (
            self.paths.cache_root
            / f"{configuration.runtime_release}-{architecture}.tar.gz"
        )
        self._download_verified(asset["url"], asset["sha256"], archive)
        self._extract_runtime(
            archive, asset["archive_root"], configuration.runtime_dir
        )
        changed.append(str(configuration.runtime_dir))
        self._switch_runtime(configuration.runtime_dir, changed)

    def _switch_runtime(self, runtime: Path, changed: list[str]) -> None:
        try:
            if self.paths.current.is_symlink() and self.paths.current.resolve() == runtime:
                return
        except OSError:
            pass
        if self.paths.current.exists() and not self.paths.current.is_symlink():
            raise ManagementError(
                73, "UNSAFE_COLLISION", f"Runtime link is not a symlink: {self.paths.current}"
            )
        temporary = self.paths.install_root / f".current.{uuid.uuid4().hex}"
        temporary.symlink_to(runtime)
        os.replace(temporary, self.paths.current)
        changed.append(str(self.paths.current))

    def _install_model(
        self, configuration: Configuration, uid: int, gid: int, changed: list[str]
    ) -> None:
        model = self._model(configuration.model_id)
        valid = False
        if configuration.model_path.is_file():
            try:
                valid = (
                    configuration.model_path.stat().st_size == model["size_bytes"]
                    and sha256_file(configuration.model_path) == model["sha256"]
                )
            except OSError:
                valid = False
        if not valid:
            self._download_verified(
                model["url"],
                model["sha256"],
                configuration.model_path,
                expected_size=model["size_bytes"],
            )
            changed.append(str(configuration.model_path))
        metadata = configuration.model_path.stat()
        if (
            metadata.st_uid != uid
            or metadata.st_gid != gid
            or stat.S_IMODE(metadata.st_mode) != 0o640
        ):
            os.chown(configuration.model_path, uid, gid)
            os.chmod(configuration.model_path, 0o640)
            if str(configuration.model_path) not in changed:
                changed.append(str(configuration.model_path))

    def _deploy_configuration(
        self, configuration: Configuration, changed: list[str]
    ) -> None:
        source_payload = self.source_root / "payload"
        self._install_file(
            self.source_root / "PRODUCT.json",
            self.paths.descriptor,
            0o644,
            changed,
        )
        self._install_file(
            self.source_root / "scripts/manage.sh",
            self.paths.entrypoint,
            0o755,
            changed,
        )
        self._install_file(
            source_payload / "bin/llama-manager",
            self.paths.manager,
            0o755,
            changed,
        )
        self._install_file(
            source_payload / "etc/llama-builds.json",
            self.paths.configuration_root / "builds.json",
            0o644,
            changed,
        )
        self._install_file(
            source_payload / "etc/llama-models.json",
            self.paths.configuration_root / "models.json",
            0o644,
            changed,
        )
        self._install_file(
            source_payload / "systemd/llama-server.service",
            self.paths.unit,
            0o644,
            changed,
        )
        self._install_file(
            source_payload / "logrotate/llama",
            self.paths.logrotate,
            0o644,
            changed,
        )
        content = json.dumps(configuration.object(), indent=2, sort_keys=True).encode() + b"\n"
        if not self._file_matches(self.paths.config, content, 0o644, 0, 0):
            atomic_write(self.paths.config, content, mode=0o644)
            changed.append(str(self.paths.config))

    def _apply_service_state(
        self,
        configuration: Configuration,
        changed: list[str],
        *,
        verify_health: bool,
        restart_required: bool,
    ) -> None:
        self._run(["systemctl", "daemon-reload"])
        if self.paths.suspended.exists():
            if self._stop_service(disable=False):
                changed.append("llama-server.service:stopped")
            return
        if configuration.boot == "enabled":
            enabled = self._service_enabled() == "enabled"
            active = self._service_active()
            if not enabled:
                self._run(["systemctl", "enable", "llama-server.service"])
                changed.append("llama-server.service:enabled")
            if not active:
                self._run(["systemctl", "start", "llama-server.service"])
                changed.append("llama-server.service:active")
            elif restart_required:
                self._run(["systemctl", "restart", "llama-server.service"])
                changed.append("llama-server.service:restarted")
            if verify_health:
                for _ in range(60):
                    if self._health():
                        break
                    time.sleep(1)
                else:
                    raise ManagementError(
                        1,
                        "HEALTH_FAILED",
                        "llama-server did not become healthy on 127.0.0.1:8080.",
                        recovery=["Inspect journalctl -u llama-server.service."],
                    )
        elif self._stop_service(disable=True):
            changed.append("llama-server.service:disabled-stopped")

    def _write_marker(
        self,
        instance_id: str,
        *,
        installed_at: str,
        changed: list[str],
    ) -> None:
        artifact = os.environ.get("LLAMA_ARTIFACT_SHA256")
        if artifact is not None and (
            len(artifact) != 64
            or any(character not in "0123456789abcdef" for character in artifact)
        ):
            raise ManagementError(78, "INVALID_ARTIFACT_DIGEST", "Artifact digest is invalid.")
        value = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "instance_id": instance_id,
            "version": self.version,
            "source_revision": (
                f"artifact-sha256:{artifact}" if artifact else self._source_revision()
            ),
            "installed_at": installed_at,
            "install_root": str(self.paths.install_root),
            "lifecycle_entrypoint": str(self.paths.entrypoint),
            "artifact_sha256": artifact,
        }
        content = canonical_json(value) + b"\n"
        if not self._file_matches(self.paths.marker, content, 0o644, 0, 0):
            atomic_write(self.paths.marker, content, mode=0o644)
            changed.append(str(self.paths.marker))

    def _snapshot_for_rollback(self, marker: dict[str, Any]) -> None:
        if self.paths.rollback_metadata.is_file():
            try:
                current = read_json(self.paths.rollback_metadata)
                if current.get("from_version") == marker["version"]:
                    return
            except ManagementError:
                pass
        stage = Path(
            tempfile.mkdtemp(prefix=".rollback-stage.", dir=self.paths.install_root)
        )
        try:
            if self.paths.product_root.is_dir():
                shutil.copytree(self.paths.product_root, stage / "product")
            if self.paths.configuration_root.is_dir():
                shutil.copytree(self.paths.configuration_root, stage / "configuration")
            for source, name in (
                (self.paths.unit, "llama-server.service"),
                (self.paths.logrotate, "logrotate"),
                (self.paths.entrypoint, "llama-manage"),
                (self.paths.manager, "llama-manager"),
                (self.paths.marker, "installation.json"),
            ):
                if source.is_file():
                    shutil.copy2(source, stage / name)
            current_target = (
                str(self.paths.current.resolve()) if self.paths.current.is_symlink() else None
            )
            metadata = {
                "schema_version": 1,
                "product_id": PRODUCT_ID,
                "from_version": marker["version"],
                "runtime_target": current_target,
                "created_at": utc_now(),
                "boot": (
                    "enabled"
                    if self._service_enabled() == "enabled"
                    else "disabled"
                ),
                "suspended": self.paths.suspended.exists(),
            }
            (stage / "rollback.json").write_bytes(canonical_json(metadata) + b"\n")
            self._protect_tree(stage)
            old = self.paths.install_root / f".rollback-old.{uuid.uuid4().hex}"
            if self.paths.rollback_root.exists():
                os.replace(self.paths.rollback_root, old)
            os.replace(stage, self.paths.rollback_root)
            if old.exists():
                shutil.rmtree(old)
        finally:
            if stage.exists():
                shutil.rmtree(stage)

    def _execute_install(
        self,
        invocation: Invocation,
        configuration: Configuration | None,
        *,
        snapshot_on_change: bool,
    ) -> tuple[list[str], str | None]:
        if configuration is None:
            raise ManagementError(78, "INVALID_CONFIGURATION", "Configuration is required.")
        self._platform_preflight()
        marker, pending_instance = self._collision_preflight()
        self._port_preflight()
        previous_version = str(marker["version"]) if marker is not None else None
        if marker is not None and marker["version"] != self.version and snapshot_on_change:
            self._snapshot_for_rollback(marker)
        instance_id = (
            str(marker["instance_id"])
            if marker is not None
            else pending_instance or str(uuid.uuid4())
        )
        installed_at = (
            str(marker["installed_at"]) if marker is not None else utc_now()
        )
        changed: list[str] = []
        self._ensure_directory(self.paths.install_root, 0o755, 0, 0, changed)
        self._ensure_directory(self.paths.versions, 0o755, 0, 0, changed)
        self._ensure_directory(self.paths.configuration_root, 0o755, 0, 0, changed)
        self._ensure_directory(self.paths.state_root, 0o755, 0, 0, changed)
        self._ensure_directory(self.paths.cache_root, 0o755, 0, 0, changed)
        if marker is None:
            self._ensure_transaction(instance_id, changed)
        service_uid, service_gid = self._ensure_account(changed)
        self._ensure_directory(
            self.paths.models, 0o750, service_uid, service_gid, changed
        )
        self._ensure_directory(
            self.paths.runtime_state, 0o750, service_uid, service_gid, changed
        )
        self._ensure_directory(
            self.paths.log_root, 0o750, 0, service_gid, changed
        )
        self._ensure_directory(self.paths.receipts, 0o750, 0, service_gid, changed)
        self._ensure_log_ownership(changed)
        self._deploy_product(changed)
        self._install_runtime(configuration, changed)
        self._install_model(configuration, service_uid, service_gid, changed)
        before_service_files = len(changed)
        self._deploy_configuration(configuration, changed)
        live_resources = {
            str(configuration.runtime_dir),
            str(configuration.model_path),
            str(self.paths.current),
            str(self.paths.config),
            str(self.paths.manager),
            str(self.paths.unit),
        }
        self._apply_service_state(
            configuration,
            changed,
            verify_health=configuration.boot == "enabled",
            restart_required=any(item in live_resources for item in changed),
        )
        if len(changed) == before_service_files and configuration.boot == "enabled":
            if not self._health():
                raise ManagementError(1, "HEALTH_FAILED", "Llama health check failed.")
        required_checks = self._post_install_checks(
            configuration, probe_runtime=configuration.boot == "enabled"
        )
        failures = [check for check in required_checks if check["status"] == "fail"]
        if failures:
            raise ManagementError(
                78,
                "BOUNDARY_CHECK_FAILED",
                f"Post-install check failed: {failures[0]['id']}",
            )
        self._write_marker(instance_id, installed_at=installed_at, changed=changed)
        for path in (
            self.paths.configuration_root / "managed-by-ubuntu-zombie",
            self.paths.state_root / "managed-by-ubuntu-zombie",
            self.paths.transaction,
            self.paths.retained,
            self.paths.retained_config,
        ):
            if path.exists():
                path.unlink()
                changed.append(str(path))
        return list(dict.fromkeys(changed)), previous_version

    def _execute_repair(
        self, invocation: Invocation, configuration: Configuration | None
    ) -> tuple[list[str], str | None]:
        marker = self.load_marker(required=True)
        if marker["version"] != self.version:
            raise ManagementError(
                78,
                "VERSION_MISMATCH",
                "Repair cannot change product versions; use update.",
            )
        return self._execute_install(
            invocation, configuration, snapshot_on_change=False
        )

    def _backup_destination(self, invocation: Invocation) -> Path:
        value = invocation.inputs.get(
            "backup_destination",
            os.environ.get("LLAMA_BACKUP_DESTINATION", str(self.paths.backup_root)),
        )
        if not isinstance(value, str):
            raise ManagementError(
                78, "INVALID_BACKUP_DESTINATION", "Backup destination must be a path."
            )
        destination = Path(value)
        if not destination.is_absolute() or ".." in destination.parts:
            raise ManagementError(
                78,
                "INVALID_BACKUP_DESTINATION",
                "Backup destination must be a canonical absolute path.",
            )
        for root in (
            self.paths.install_root,
            self.paths.configuration_root,
            self.paths.state_root,
            self.paths.log_root,
            self.paths.cache_root,
        ):
            if destination == root or _is_relative_to(destination, root):
                raise ManagementError(
                    78,
                    "INVALID_BACKUP_DESTINATION",
                    "Backup destination must be outside product-owned roots.",
                )
        return destination

    def _create_backup(self, destination: Path, marker: dict[str, Any]) -> Path:
        existed = destination.exists()
        if destination.is_symlink():
            raise ManagementError(
                73, "UNSAFE_BACKUP_DESTINATION", "Backup destination is a symlink."
            )
        destination.mkdir(parents=True, exist_ok=True)
        metadata = destination.lstat()
        if (
            not stat.S_ISDIR(metadata.st_mode)
            or (existed and metadata.st_uid != 0)
            or (existed and stat.S_IMODE(metadata.st_mode) & 0o077)
        ):
            raise ManagementError(
                73,
                "UNSAFE_BACKUP_DESTINATION",
                "Existing backup destination must be root-owned and private.",
            )
        if not existed:
            os.chown(destination, 0, 0)
            os.chmod(destination, 0o700)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = destination / f"llama-backup-{marker['version']}-{timestamp}.tar.gz"
        if archive.exists():
            raise ManagementError(73, "BACKUP_EXISTS", f"Backup already exists: {archive}")
        temporary = archive.with_name(f".{archive.name}.{uuid.uuid4().hex}.tmp")
        manifest = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "version": marker["version"],
            "instance_id": marker["instance_id"],
            "created_at": utc_now(),
            "models_included": False,
        }
        try:
            with tarfile.open(temporary, "x:gz") as bundle:
                data = canonical_json(manifest) + b"\n"
                info = tarfile.TarInfo("llama-backup/manifest.json")
                info.size = len(data)
                info.mode = 0o600
                info.mtime = int(time.time())
                bundle.addfile(info, fileobj=io.BytesIO(data))
                if self.paths.configuration_root.is_dir():
                    bundle.add(
                        self.paths.configuration_root,
                        arcname="llama-backup/configuration",
                        recursive=True,
                    )
                for path in (
                    self.paths.marker,
                    self.paths.suspended,
                    self.paths.retained,
                ):
                    if path.is_file():
                        bundle.add(path, arcname=f"llama-backup/state/{path.name}")
            os.chown(temporary, 0, 0)
            os.chmod(temporary, 0o600)
            with tarfile.open(temporary, "r:gz") as bundle:
                members = bundle.getmembers()
                if not members or not all(
                    self._safe_archive_member(member) for member in members
                ):
                    raise ManagementError(78, "BACKUP_VERIFY_FAILED", "Backup is unsafe.")
            os.replace(temporary, archive)
            digest = sha256_file(archive)
            atomic_write(
                archive.with_suffix(archive.suffix + ".sha256"),
                f"{digest}  {archive.name}\n".encode(),
                mode=0o600,
            )
            return archive
        finally:
            temporary.unlink(missing_ok=True)

    def _execute_backup(
        self, invocation: Invocation
    ) -> tuple[list[str], str | None, str]:
        marker = self.load_marker(required=True)
        archive = self._create_backup(self._backup_destination(invocation), marker)
        return (
            [str(archive), str(archive.with_suffix(archive.suffix + ".sha256"))],
            str(marker["version"]),
            str(archive),
        )

    def _execute_update(
        self, invocation: Invocation, configuration: Configuration | None
    ) -> tuple[list[str], str | None, str]:
        marker = self.load_marker(required=True)
        if tuple(map(int, self.version.split("."))) < tuple(
            map(int, str(marker["version"]).split("."))
        ):
            raise ManagementError(
                78, "DOWNGRADE_REQUIRES_ROLLBACK", "Update cannot install an older version."
            )
        archive = self._create_backup(self.paths.backup_root, marker)
        self._snapshot_for_rollback(marker)
        changed, previous = self._execute_install(
            invocation, configuration, snapshot_on_change=False
        )
        return changed + [str(archive)], previous, str(archive)

    def _execute_rollback(
        self, _invocation: Invocation
    ) -> tuple[list[str], str | None]:
        marker = self.load_marker(required=True)
        if not self.paths.rollback_metadata.is_file():
            raise ManagementError(66, "ROLLBACK_MISSING", "No rollback snapshot is available.")
        metadata = read_json(self.paths.rollback_metadata)
        if (
            set(metadata)
            != {
                "schema_version",
                "product_id",
                "from_version",
                "runtime_target",
                "created_at",
                "boot",
                "suspended",
            }
            or metadata["schema_version"] != 1
            or metadata["product_id"] != PRODUCT_ID
            or metadata["boot"] not in {"enabled", "disabled"}
            or not isinstance(metadata["suspended"], bool)
        ):
            raise ManagementError(65, "INVALID_ROLLBACK", "Rollback metadata is invalid.")
        runtime_target = metadata["runtime_target"]
        if not isinstance(runtime_target, str):
            raise ManagementError(65, "INVALID_ROLLBACK", "Rollback runtime is invalid.")
        runtime = Path(runtime_target)
        if not _is_relative_to(runtime, self.paths.versions) or not self._runtime_valid(runtime):
            raise ManagementError(78, "INVALID_ROLLBACK", "Rollback runtime is unavailable.")
        required = (
            self.paths.rollback_root / "product",
            self.paths.rollback_root / "configuration",
            self.paths.rollback_root / "installation.json",
        )
        if not all(path.exists() for path in required):
            raise ManagementError(78, "INVALID_ROLLBACK", "Rollback snapshot is incomplete.")
        self._stop_service(disable=True)
        changed: list[str] = []
        restored_product = self.paths.rollback_root / "product"
        current_product = self.paths.install_root / f".product-current.{uuid.uuid4().hex}"
        os.replace(self.paths.product_root, current_product)
        shutil.copytree(restored_product, self.paths.product_root)
        shutil.rmtree(current_product)
        changed.append(str(self.paths.product_root))
        if self.paths.configuration_root.exists():
            shutil.rmtree(self.paths.configuration_root)
        shutil.copytree(
            self.paths.rollback_root / "configuration",
            self.paths.configuration_root,
        )
        self._protect_tree(self.paths.configuration_root)
        for source, destination, mode in (
            (self.paths.rollback_root / "llama-manage", self.paths.entrypoint, 0o755),
            (self.paths.rollback_root / "llama-manager", self.paths.manager, 0o755),
            (self.paths.rollback_root / "llama-server.service", self.paths.unit, 0o644),
            (self.paths.rollback_root / "logrotate", self.paths.logrotate, 0o644),
            (self.paths.rollback_root / "installation.json", self.paths.marker, 0o644),
        ):
            if source.is_file():
                atomic_write(destination, source.read_bytes(), mode=mode)
                changed.append(str(destination))
        self._switch_runtime(runtime, changed)
        self._run(["systemctl", "daemon-reload"])
        config = self._existing_config()
        if config is None:
            raise ManagementError(78, "INVALID_ROLLBACK", "Restored config is missing.")
        restored = Configuration(
            str(config["model_id"]),
            int(config["context_size"]),
            int(config["threads"]),
            str(metadata["boot"]),
            str(config["runtime_release"]),
            runtime,
            Path(str(config["model_path"])),
        )
        if metadata["suspended"]:
            content = canonical_json(
                {
                    "schema_version": 1,
                    "product_id": PRODUCT_ID,
                    "suspended_at": utc_now(),
                }
            ) + b"\n"
            atomic_write(self.paths.suspended, content, mode=0o644)
        else:
            self.paths.suspended.unlink(missing_ok=True)
        self._apply_service_state(
            restored,
            changed,
            verify_health=not bool(metadata["suspended"])
            and restored.boot == "enabled",
            restart_required=True,
        )
        self.load_marker(required=True)
        shutil.rmtree(self.paths.rollback_root)
        changed.append(str(self.paths.rollback_root))
        return changed, str(marker["version"])

    def _execute_suspend(self) -> tuple[list[str], str | None]:
        marker = self.load_marker(required=True)
        changed: list[str] = []
        if self._stop_service(disable=False):
            changed.append("llama-server.service:stopped")
        if not self.paths.suspended.exists():
            content = canonical_json(
                {
                    "schema_version": 1,
                    "product_id": PRODUCT_ID,
                    "suspended_at": utc_now(),
                }
            ) + b"\n"
            atomic_write(self.paths.suspended, content, mode=0o644)
            changed.append(str(self.paths.suspended))
        return changed, str(marker["version"])

    def _execute_resume(self) -> tuple[list[str], str | None]:
        marker = self.load_marker(required=True)
        if self.paths.retained.exists():
            raise ManagementError(66, "RUNTIME_REMOVED", "Install Llama before resuming it.")
        checks = self.verify_checks(probe_runtime=False)
        failures = [
            check
            for check in checks
            if check["status"] == "fail" and check["id"] != "suspension"
        ]
        if failures:
            raise ManagementError(
                78, "BOUNDARY_CHECK_FAILED", f"Cannot resume: {failures[0]['id']}"
            )
        changed: list[str] = []
        if self.paths.suspended.exists():
            self.paths.suspended.unlink()
            changed.append(str(self.paths.suspended))
        config = self._existing_config()
        if config is None:
            raise ManagementError(66, "CONFIGURATION_MISSING", "Llama config is missing.")
        if config["runtime_release"] != self.build_catalog["release"]:
            raise ManagementError(78, "VERSION_MISMATCH", "Installed catalogues do not match.")
        if not self._service_active():
            self._run(["systemctl", "start", "llama-server.service"])
            changed.append("llama-server.service:active")
        for _ in range(60):
            if self._health():
                break
            time.sleep(1)
        else:
            self._run(["systemctl", "stop", "llama-server.service"], check=False)
            raise ManagementError(1, "HEALTH_FAILED", "Llama failed its resume health gate.")
        return changed, str(marker["version"])

    @staticmethod
    def _remove_owned_tree(path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(metadata.st_mode):
            raise ManagementError(73, "UNSAFE_REMOVAL", f"Refusing to remove unsafe path: {path}")
        shutil.rmtree(path)

    @staticmethod
    def _remove_owned_file(path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise ManagementError(73, "UNSAFE_REMOVAL", f"Refusing to remove unsafe file: {path}")
        if metadata.st_uid != 0:
            raise ManagementError(73, "UNSAFE_REMOVAL", f"Refusing to remove unowned file: {path}")
        path.unlink()

    def _execute_uninstall(
        self, invocation: Invocation
    ) -> tuple[list[str], str | None]:
        marker = self.load_marker()
        legacy = marker is None and self._legacy_installation_valid()
        if marker is None and not legacy:
            raise ManagementError(
                73,
                "OWNERSHIP_REQUIRED",
                "Llama is not installed with a valid product or legacy ownership marker.",
            )
        changed: list[str] = []
        if marker is None:
            instance_id = str(uuid.uuid4())
            self._write_marker(instance_id, installed_at=utc_now(), changed=changed)
            marker = self.load_marker(required=True)
        version = str(marker["version"])
        try:
            service_gid = grp.getgrnam("llama-cpp").gr_gid
        except KeyError:
            service_gid = 0
        self._ensure_directory(self.paths.log_root, 0o750, 0, service_gid, changed)
        self._ensure_log_ownership(changed)
        retained_config_content = (
            self.paths.config.read_bytes()
            if invocation.retain_state and self.paths.config.is_file()
            else None
        )
        self._stop_service(disable=True)
        for path in (
            self.paths.unit,
            self.paths.logrotate,
            self.paths.entrypoint,
            self.paths.manager,
        ):
            if path.exists():
                self._remove_owned_file(path)
                changed.append(str(path))
        self._run(["systemctl", "daemon-reload"], check=False)
        for path in (
            self.paths.configuration_root,
            self.paths.install_root,
            self.paths.cache_root,
        ):
            if path.exists():
                self._remove_owned_tree(path)
                changed.append(str(path))
        legacy_state_marker = self.paths.state_root / "managed-by-ubuntu-zombie"
        if legacy_state_marker.exists():
            self._remove_owned_file(legacy_state_marker)
            changed.append(str(legacy_state_marker))
        if invocation.retain_state:
            if retained_config_content is not None:
                atomic_write(
                    self.paths.retained_config,
                    retained_config_content,
                    mode=0o600,
                )
                changed.append(str(self.paths.retained_config))
            content = canonical_json(
                {
                    "schema_version": 1,
                    "product_id": PRODUCT_ID,
                    "retained_at": utc_now(),
                }
            ) + b"\n"
            atomic_write(self.paths.retained, content, mode=0o600)
            changed.append(str(self.paths.retained))
        else:
            self._remove_owned_tree(self.paths.state_root)
            changed.append(str(self.paths.state_root))
            try:
                pwd.getpwnam("llama-cpp")
            except KeyError:
                pass
            else:
                result = self._run(["userdel", "llama-cpp"], check=False)
                if result.returncode != 0:
                    raise ManagementError(
                        73, "ACCOUNT_REMOVAL_FAILED", "Could not remove llama-cpp."
                    )
                changed.append("account:llama-cpp")
            try:
                grp.getgrnam("llama-cpp")
            except KeyError:
                pass
            else:
                result = self._run(["groupdel", "llama-cpp"], check=False)
                if result.returncode != 0:
                    raise ManagementError(
                        73, "ACCOUNT_REMOVAL_FAILED", "Could not remove the llama-cpp group."
                    )
        return changed, version

    def _write_receipt(
        self,
        result: Result,
        *,
        previous_version: str | None,
        changed_resources: list[str],
        event_id: str,
    ) -> dict[str, str]:
        try:
            service_gid = grp.getgrnam("llama-cpp").gr_gid
        except KeyError:
            service_gid = 0
        self._ensure_directory(self.paths.log_root, 0o750, 0, service_gid, [])
        self._ensure_directory(self.paths.receipts, 0o750, 0, service_gid, [])
        marker = self.load_marker()
        receipt_value = {
            "schema_version": 1,
            "response": result.object(),
            "installed_version": marker["version"] if marker is not None else None,
            "previous_version": previous_version,
            "changed_resources": sorted(set(changed_resources)),
            "audit_event_id": event_id,
        }
        content = canonical_json(receipt_value) + b"\n"
        historical = self.paths.receipts / f"{result.correlation_id}.json"
        atomic_write(historical, content, mode=0o640, gid=service_gid)
        atomic_write(self.paths.receipt, content, mode=0o640, gid=service_gid)
        return {"path": str(self.paths.receipt), "digest": sha256_bytes(content)}

    def _append_audit(
        self,
        invocation: Invocation,
        *,
        event_id: str,
        result_status: str,
        changed: bool,
        receipt_digest: str | None,
        instance_id: str | None,
    ) -> None:
        try:
            service_gid = grp.getgrnam("llama-cpp").gr_gid
        except KeyError:
            service_gid = 0
        event = {
            "timestamp": utc_now(),
            "event_id": event_id,
            "correlation_id": invocation.correlation_id,
            "product_id": PRODUCT_ID,
            "instance_id": instance_id,
            "operation": invocation.operation,
            "phase": _operation_phase(invocation.operation, dry_run=invocation.dry_run),
            "actor": invocation.actor,
            "decision": "denied" if result_status == "blocked" else "allowed",
            "result": result_status,
            "changed": changed,
            "receipt_digest": receipt_digest,
        }
        self.paths.audit.parent.mkdir(parents=True, exist_ok=True)
        flags = (
            os.O_WRONLY
            | os.O_APPEND
            | os.O_CREAT
            | getattr(os, "O_NOFOLLOW", 0)
        )
        descriptor = os.open(self.paths.audit, flags, 0o640)
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ManagementError(73, "UNSAFE_AUDIT", "Audit path is not regular.")
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            os.fchmod(descriptor, 0o640)
            os.fchown(descriptor, 0, service_gid)
            os.write(descriptor, canonical_json(event) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def audit_failure(self, invocation: Invocation, error: Exception) -> None:
        if os.geteuid() != 0 or not self.paths.log_root.exists():
            return
        status = "blocked" if isinstance(error, ManagementError) else "failed"
        try:
            self._append_audit(
                invocation,
                event_id=str(uuid.uuid4()),
                result_status=status,
                changed=False,
                receipt_digest=None,
                instance_id=self.instance_id(),
            )
        except (OSError, ManagementError):
            pass


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="llama-manage")
    parser.add_argument("operation", choices=OPERATIONS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--non-interactive", action="store_true")
    parser.add_argument("--request-file", type=Path)
    parser.add_argument("--correlation-id")
    parser.add_argument("--plan-digest")
    parser.add_argument("--yes", action="store_true")
    parser.add_argument("--purge", action="store_true")
    parser.add_argument("--confirmation")
    return parser


def _print_result(result: Result, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.object(), sort_keys=True, separators=(",", ":")))
        return
    if result.phase == "plan":
        print("Llama component:")
        print(
            f"  Runtime:        llama.cpp "
            f"{result.details.get('runtime', '') if result.details else ''}".rstrip()
        )
        print("  API:            http://127.0.0.1:8080/v1 (loopback only)")
        print("  Manager:        /usr/local/bin/llama-manager")
        print("  Data:           /var/lib/llama.cpp")
        print("  Zombie impact:  none; this is an independent product")
        print(f"  Plan digest:    {result.plan_digest}")
        for step in result.steps:
            print(f"  - {step['summary']}")
        return
    print(f"Llama {result.operation}: {result.status}")
    if result.details is not None:
        lifecycle = result.details.get("lifecycle")
        if lifecycle is not None:
            print(f"Lifecycle: {lifecycle}")
    for check in result.checks:
        glyph = "[ok]" if check["status"] == "pass" else "[!]" if check["status"] == "warn" else "[x]"
        print(f"{glyph} {check['summary']}")
    for error in result.errors:
        print(f"[x] {error['message']}", file=sys.stderr)


def _failure_result(
    manager: Manager,
    invocation: Invocation,
    error: Exception,
) -> tuple[Result, int]:
    if isinstance(error, ManagementError):
        exit_code = error.exit_code
        code = error.code
        message = error.message
        retryable = error.retryable
        recovery = error.recovery
        status = "blocked" if exit_code in {64, 65, 66, 69, 73, 75, 78} else "failed"
    else:
        exit_code = 1
        code = "OPERATION_FAILED"
        message = "The Llama lifecycle operation failed unexpectedly."
        retryable = False
        recovery = ["Inspect the product audit log and retry after correcting the host."]
        status = "failed"
    result = Result(
        invocation.operation,
        invocation.correlation_id,
        manager.version,
        manager.instance_id(),
        _operation_phase(invocation.operation, dry_run=invocation.dry_run),
        status=status,
        errors=[{"code": code, "message": message, "retryable": retryable}],
        recovery=recovery,
    )
    manager.audit_failure(invocation, error)
    return result, exit_code


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    parser = _parser()
    args = parser.parse_args(argv)
    source_root = Path(
        os.environ.get("LLAMA_SOURCE_ROOT", Path(__file__).resolve().parents[3])
    )
    try:
        manager = Manager(source_root)
    except ManagementError as exc:
        print(f"llama-manage: {exc.message}", file=sys.stderr)
        return exc.exit_code
    try:
        invocation = manager.invocation(args)
    except ManagementError as exc:
        correlation = args.correlation_id or str(uuid.uuid4())
        try:
            validate_uuid(correlation, label="correlation_id")
        except ManagementError:
            correlation = str(uuid.uuid4())
        invocation = Invocation(
            args.operation,
            correlation,
            "operator",
            {},
            None,
            None,
            args.dry_run,
            args.json,
            args.non_interactive,
            args.yes,
            args.plan_digest,
        )
        result, exit_code = _failure_result(manager, invocation, exc)
        _print_result(result, as_json=args.json)
        return exit_code
    try:
        result, exit_code = manager.run(invocation)
    except Exception as exc:
        result, exit_code = _failure_result(manager, invocation, exc)
    _print_result(result, as_json=invocation.json_output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
