"""Independent, root-only lifecycle for the Forgejo infrastructure product."""

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
import re
import secrets
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
from pathlib import Path
from typing import Any, Callable, Iterator


PRODUCT_ID = "forgejo"
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
CONFIGURATION_INPUTS = {
    "admin_user",
    "admin_email",
    "database_name",
    "database_user",
    "admin_password_file",
    "database_password_file",
    "upstream_version",
    "boot",
}
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
SECRET_INPUTS = {"admin_password_file", "database_password_file"}
KNOWN_ENV = {
    "FORGEJO_SOURCE_ROOT",
    "FORGEJO_NONINTERACTIVE",
    "FORGEJO_ADMIN_USER",
    "FORGEJO_ADMIN_EMAIL",
    "FORGEJO_DB_NAME",
    "FORGEJO_DB_USER",
    "FORGEJO_ADMIN_PASSWORD_FILE",
    "FORGEJO_DB_PASSWORD_FILE",
    "FORGEJO_VERSION",
    "FORGEJO_BOOT",
    "FORGEJO_HTTP_PORT",
    "FORGEJO_BACKUP_DESTINATION",
    "FORGEJO_ARTIFACT_SHA256",
    "FORGEJO_CONFIRM_ADOPTION",
    "FORGEJO_CONFIRM_DATABASE_REUSE",
    "FORGEJO_MIGRATION_MANIFEST",
    "FORGEJO_DISPOSABLE_VM_TEST",
    "FORGEJO_TEST_RELEASE_BASE",
}
FIXED_PORT = 3000
DELETE_CONFIRMATION = "DELETE FORGEJO STATE"
ADOPT_CONFIRMATION = "ADOPT FORGEJO"
DEFAULT_ADMIN_USER = "forgejo-admin"
DEFAULT_ADMIN_EMAIL = "forgejo-admin@localhost.localdomain"
DEFAULT_DATABASE_NAME = "forgejo"
DEFAULT_DATABASE_USER = "forgejo"
DEFAULT_UPSTREAM_VERSION = "latest"
DEFAULT_BOOT = "enabled"
VERSION_PARTS = 6
MAX_DOWNLOAD_BYTES = 512 * 1024 * 1024
RELEASE_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+(?:-[A-Za-z0-9.]+)?$")
NAME_RE = re.compile(r"^[a-z](?:[a-z0-9_-]{0,38}[a-z0-9])?$")
HOST_RE = re.compile(
    r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?"
    r"(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*$"
)
ALLOWED_RELEASE_HOSTS = {
    "data.forgejo.org",
    "code.forgejo.org",
    "codeberg.org",
}
MARKER_FIELDS = {
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
PREVIOUS_MARKER_FIELDS = {
    "schema_version",
    "product_id",
    "instance_id",
    "version",
    "source_revision",
    "installed_at",
    "updated_at",
}


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
    """Every host resource reserved or managed by Forgejo."""

    install_root: Path = Path("/opt/forgejo")
    configuration_root: Path = Path("/etc/forgejo")
    state_root: Path = Path("/var/lib/forgejo")
    log_root: Path = Path("/var/log/forgejo")
    cache_root: Path = Path("/var/cache/forgejo")
    unit: Path = Path("/etc/systemd/system/forgejo.service")
    logrotate: Path = Path("/etc/logrotate.d/forgejo-product")
    entrypoint: Path = Path("/usr/local/sbin/forgejo-manage")
    binary: Path = Path("/usr/local/bin/forgejo")
    lock: Path = Path("/run/lock/forgejo-product.lock")
    backup_root: Path = Path("/var/backups/forgejo")
    caddyfile: Path = Path("/etc/caddy/Caddyfile")
    legacy_caddy: Path = Path("/etc/caddy/conf.d/forgejo.caddy")
    avahi_service: Path = Path("/etc/avahi/services/forgejo.service")
    caddy_ca: Path = Path(
        "/var/lib/caddy/.local/share/caddy/pki/authorities/local/root.crt"
    )
    trusted_ca: Path = Path(
        "/usr/local/share/ca-certificates/forgejo-local-ca.crt"
    )
    migration_manifest: Path | None = None

    @property
    def marker(self) -> Path:
        return self.state_root / "installation.json"

    @property
    def transaction(self) -> Path:
        return self.state_root / ".product-installing.json"

    @property
    def retained(self) -> Path:
        return self.state_root / ".product-retained.json"

    @property
    def suspended(self) -> Path:
        return self.state_root / ".product-suspended.json"

    @property
    def product_root(self) -> Path:
        return self.install_root / "product"

    @property
    def rollback_root(self) -> Path:
        return self.install_root / "rollback"

    @property
    def rollback_metadata(self) -> Path:
        return self.rollback_root / "rollback.json"

    @property
    def app_ini(self) -> Path:
        return self.configuration_root / "app.ini"

    @property
    def descriptor(self) -> Path:
        return self.configuration_root / "PRODUCT.json"

    @property
    def binary_metadata(self) -> Path:
        return self.configuration_root / "binary.json"

    @property
    def bootstrap_password(self) -> Path:
        return self.configuration_root / "bootstrap-admin-password"

    @property
    def exported_ca(self) -> Path:
        return self.configuration_root / "caddy-local-ca.crt"

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
    admin_user: str
    admin_email: str
    database_name: str
    database_user: str
    upstream_version: str
    boot: str
    host: str

    @property
    def root_url(self) -> str:
        return f"https://{self.host}/"

    def public_object(self) -> dict[str, str | int]:
        return {
            "admin_user": self.admin_user,
            "admin_email": self.admin_email,
            "database_name": self.database_name,
            "database_user": self.database_user,
            "upstream_version": self.upstream_version,
            "boot": self.boot,
            "host": self.host,
            "root_url": self.root_url,
            "http_address": "127.0.0.1",
            "http_port": FIXED_PORT,
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
            value["details"] = {"forgejo": self.details}
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
        raise ManagementError(
            78, "INTEGRITY_READ_FAILED", f"Cannot hash {path}."
        ) from exc
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
        raise ManagementError(
            65, "INVALID_JSON", f"Invalid JSON file: {path}"
        ) from exc
    if not isinstance(value, dict):
        raise ManagementError(
            65, "INVALID_JSON", f"{path} must contain one object."
        )
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
    descriptor = os.open(temporary, flags, mode)
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fchmod(descriptor, mode)
        os.fchown(descriptor, uid, gid)
        os.fsync(descriptor)
    except BaseException:
        os.close(descriptor)
        temporary.unlink(missing_ok=True)
        raise
    else:
        os.close(descriptor)
        os.replace(temporary, path)


def is_relative_to(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
    except ValueError:
        return False
    return True


def operation_phase(operation: str, *, dry_run: bool) -> str:
    if operation in READ_ONLY:
        return "read"
    return "plan" if dry_run else "execute"


def parse_ini(path: Path) -> dict[str, dict[str, str]]:
    sections: dict[str, dict[str, str]] = {}
    current = ""
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeError) as exc:
        raise ManagementError(
            65, "INVALID_CONFIGURATION", "Forgejo app.ini cannot be read."
        ) from exc
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith((";", "#")):
            continue
        if line.startswith("[") and line.endswith("]"):
            current = line[1:-1].strip().lower()
            if not current:
                raise ManagementError(
                    65, "INVALID_CONFIGURATION", "Forgejo app.ini has an empty section."
                )
            sections.setdefault(current, {})
            continue
        key, separator, value = line.partition("=")
        if not separator or not current:
            continue
        normalized = key.strip().upper()
        if normalized in sections[current]:
            raise ManagementError(
                65,
                "INVALID_CONFIGURATION",
                f"Forgejo app.ini contains duplicate {current}.{normalized}.",
            )
        sections[current][normalized] = value.strip()
    return sections


def secure_secret_file(path: Path) -> str:
    if not path.is_absolute():
        raise ManagementError(
            65, "INVALID_SECRET", "Secret input paths must be absolute."
        )
    try:
        metadata = path.lstat()
    except OSError as exc:
        raise ManagementError(
            66, "SECRET_MISSING", "A required secret input file is missing."
        ) from exc
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_ISLNK(metadata.st_mode)
        or metadata.st_uid != 0
        or stat.S_IMODE(metadata.st_mode) & 0o077
        or metadata.st_size > 1024
    ):
        raise ManagementError(
            73,
            "UNSAFE_SECRET",
            "Secret input files must be root-owned private regular files.",
        )
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ManagementError(
            65, "INVALID_SECRET", "A secret input file is unreadable."
        ) from exc
    if value.endswith("\n"):
        value = value[:-1]
    if (
        "\n" in value
        or "\r" in value
        or not 8 <= len(value) <= 256
        or not value.isprintable()
    ):
        raise ManagementError(
            65,
            "INVALID_SECRET",
            "Forgejo passwords must contain 8 through 256 printable characters.",
        )
    return value


class SafeRedirectHandler(urllib.request.HTTPRedirectHandler):
    def redirect_request(
        self,
        request: urllib.request.Request,
        file_pointer: Any,
        code: int,
        message: str,
        headers: Any,
        new_url: str,
    ) -> urllib.request.Request | None:
        validate_release_url(new_url)
        return super().redirect_request(
            request, file_pointer, code, message, headers, new_url
        )


def validate_release_url(url: str) -> None:
    parsed = urllib.parse.urlsplit(url)
    local_test = (
        os.environ.get("FORGEJO_DISPOSABLE_VM_TEST") == "1"
        and parsed.scheme == "http"
        and parsed.hostname in {"127.0.0.1", "::1"}
    )
    approved_host = parsed.hostname in ALLOWED_RELEASE_HOSTS
    if (
        parsed.username is not None
        or parsed.password is not None
        or parsed.fragment
        or not parsed.path
        or not (local_test or (parsed.scheme == "https" and approved_host))
    ):
        raise ManagementError(
            78, "UNAPPROVED_DOWNLOAD", "Forgejo release URL is not approved."
        )


class Manager:
    """Product lifecycle implementation."""

    def __init__(self, source_root: Path, paths: Paths | None = None) -> None:
        self.source_root = source_root.resolve()
        if paths is None:
            manifest_value = os.environ.get("FORGEJO_MIGRATION_MANIFEST")
            migration_manifest = Path(manifest_value) if manifest_value else None
            if migration_manifest is not None and (
                not migration_manifest.is_absolute()
                or ".." in migration_manifest.parts
            ):
                raise ManagementError(
                    65,
                    "INVALID_MIGRATION_MANIFEST",
                    "FORGEJO_MIGRATION_MANIFEST must be a canonical absolute path.",
                )
            paths = Paths(migration_manifest=migration_manifest)
        self.paths = paths
        self.descriptor = read_json(self.source_root / "PRODUCT.json")
        self._validate_descriptor()
        try:
            version_text = (self.source_root / "VERSION").read_text(encoding="utf-8")
        except OSError as exc:
            raise ManagementError(
                66, "VERSION_MISSING", "Product VERSION is missing."
            ) from exc
        self.version = validate_version(version_text.strip())

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
            raise ManagementError(
                65, "INVALID_DESCRIPTOR", "PRODUCT.json fields are invalid."
            )
        expected = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "source_root": "products/forgejo",
            "version_file": "VERSION",
            "lifecycle_script": "scripts/manage.sh",
            "installed_entrypoint": str(self.paths.entrypoint),
            "install_root": str(self.paths.install_root),
            "configuration_root": str(self.paths.configuration_root),
            "state_root": str(self.paths.state_root),
            "log_root": str(self.paths.log_root),
            "ownership_marker": str(self.paths.marker),
            "environment_prefix": "FORGEJO",
            "accounts": [
                {"name": "git", "kind": "user"},
                {"name": "git", "kind": "group"},
            ],
            "units": ["forgejo.service"],
            "ports": [
                {"address": "127.0.0.1", "port": FIXED_PORT, "protocol": "tcp"}
            ],
            "cookie_names": ["forgejo_session", "forgejo_remember"],
            "operations": list(OPERATIONS),
        }
        for key, value in expected.items():
            if self.descriptor.get(key) != value:
                raise ManagementError(
                    65, "INVALID_DESCRIPTOR", f"PRODUCT.json has invalid {key}."
                )
        for key in ("display_name", "authority_summary"):
            if (
                not isinstance(self.descriptor[key], str)
                or not self.descriptor[key].strip()
            ):
                raise ManagementError(
                    65, "INVALID_DESCRIPTOR", f"PRODUCT.json has invalid {key}."
                )

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
            f"Forgejo releases do not support architecture {machine}.",
        )

    @staticmethod
    def _host() -> str:
        result = socket.gethostname().split(".", 1)[0].strip().lower()
        result = f"{result.removesuffix('.local')}.local"
        if not HOST_RE.fullmatch(result):
            raise ManagementError(
                78, "INVALID_HOSTNAME", "The host name cannot form a safe .local name."
            )
        return result

    def _binary_record(self) -> dict[str, Any] | None:
        if not self.paths.binary_metadata.exists():
            return None
        value = read_json(self.paths.binary_metadata)
        if (
            set(value) != {"schema_version", "version", "sha256", "source_url"}
            or value["schema_version"] != 1
            or not isinstance(value["version"], str)
            or not RELEASE_RE.fullmatch(value["version"])
            or not isinstance(value["sha256"], str)
            or len(value["sha256"]) != 64
            or any(character not in "0123456789abcdef" for character in value["sha256"])
            or not isinstance(value["source_url"], str)
        ):
            raise ManagementError(
                65, "INVALID_CONFIGURATION", "Forgejo binary metadata is invalid."
            )
        return value

    def _existing_public_config(self) -> dict[str, str] | None:
        if not self.paths.app_ini.exists():
            return None
        sections = parse_ini(self.paths.app_ini)
        database = sections.get("database", {})
        server = sections.get("server", {})
        service = sections.get("service", {})
        result = {
            "database_name": database.get("NAME", ""),
            "database_user": database.get("USER", ""),
            "host": server.get("DOMAIN", ""),
            "root_url": server.get("ROOT_URL", ""),
            "http_address": server.get("HTTP_ADDR", ""),
            "http_port": server.get("HTTP_PORT", ""),
            "registration": service.get("DISABLE_REGISTRATION", ""),
        }
        return result

    @staticmethod
    def _validate_name(value: Any, *, label: str) -> str:
        if not isinstance(value, str) or not NAME_RE.fullmatch(value):
            raise ManagementError(
                78,
                "INVALID_CONFIGURATION",
                f"{label} must be a conservative lowercase identifier.",
            )
        return value

    @staticmethod
    def _validate_email(value: Any) -> str:
        if (
            not isinstance(value, str)
            or len(value) > 254
            or re.fullmatch(r"[A-Za-z0-9._+-]+@[A-Za-z0-9.-]+", value) is None
        ):
            raise ManagementError(
                78, "INVALID_CONFIGURATION", "admin_email is invalid."
            )
        return value

    @staticmethod
    def _validate_upstream_version(value: str) -> str:
        if value != DEFAULT_UPSTREAM_VERSION and not RELEASE_RE.fullmatch(value):
            raise ManagementError(
                78,
                "INVALID_CONFIGURATION",
                "upstream_version must be latest or a Forgejo release.",
            )
        return value

    @staticmethod
    def _prompt(message: str, *, as_json: bool) -> str:
        destination = sys.stderr if as_json else sys.stdout
        print(message, end="", file=destination, flush=True)
        try:
            return input()
        except (EOFError, KeyboardInterrupt) as exc:
            raise ManagementError(
                64,
                "INTERACTIVE_INPUT_REQUIRED",
                "Interactive installation was cancelled.",
            ) from exc

    def _prepare_interactive_install(
        self,
        args: argparse.Namespace,
        inputs: dict[str, Any],
        *,
        request_supplied: bool,
        non_interactive: bool,
    ) -> None:
        if (
            args.operation != "install"
            or request_supplied
            or args.yes
            or args.dry_run
            or non_interactive
            or not sys.stdin.isatty()
            or self.paths.marker.exists()
            or self.paths.app_ini.exists()
        ):
            return

        destination = sys.stderr if args.json else sys.stdout
        print("Forgejo interactive installer", file=destination)
        print(
            "Press Enter to accept each value shown in brackets.",
            file=destination,
        )

        def prompt_value(
            name: str,
            label: str,
            default: str,
            validator: Callable[[str], str],
        ) -> None:
            if name in inputs:
                return
            while True:
                answer = self._prompt(
                    f"{label} [{default}]: ",
                    as_json=args.json,
                ).strip()
                try:
                    inputs[name] = validator(answer or default)
                    return
                except ManagementError as exc:
                    print(f"  {exc.message}", file=sys.stderr)

        prompt_value(
            "admin_user",
            "Administrator username",
            DEFAULT_ADMIN_USER,
            lambda value: self._validate_name(value, label="admin_user"),
        )
        prompt_value(
            "admin_email",
            "Administrator email",
            DEFAULT_ADMIN_EMAIL,
            self._validate_email,
        )
        prompt_value(
            "database_name",
            "PostgreSQL database name",
            DEFAULT_DATABASE_NAME,
            lambda value: self._validate_name(value, label="database_name"),
        )
        prompt_value(
            "database_user",
            "PostgreSQL role name",
            DEFAULT_DATABASE_USER,
            lambda value: self._validate_name(value, label="database_user"),
        )
        prompt_value(
            "upstream_version",
            "Forgejo version",
            DEFAULT_UPSTREAM_VERSION,
            self._validate_upstream_version,
        )
        if "boot" not in inputs:
            while True:
                answer = self._prompt(
                    "Start Forgejo automatically at boot? [Y/n]: ",
                    as_json=args.json,
                ).strip().lower()
                if answer in {"", "y", "yes"}:
                    inputs["boot"] = "enabled"
                    break
                if answer in {"n", "no"}:
                    inputs["boot"] = "disabled"
                    break
                print("  Answer yes or no.", file=sys.stderr)
        print(
            "Secure database and initial administrator credentials will be "
            "generated automatically.",
            file=destination,
        )

    def configuration(self, invocation: Invocation) -> Configuration:
        existing = self._existing_public_config()
        record = self._binary_record()
        inputs = invocation.inputs

        def selected(
            input_name: str,
            env_name: str,
            existing_name: str,
            default: str,
        ) -> str:
            value: Any
            if input_name in inputs:
                value = inputs[input_name]
            elif os.environ.get(env_name):
                value = os.environ[env_name]
            elif existing is not None and existing.get(existing_name):
                value = existing[existing_name]
            else:
                value = default
            if not isinstance(value, str):
                raise ManagementError(
                    78, "INVALID_CONFIGURATION", f"{input_name} must be a string."
                )
            return value

        admin_user = self._validate_name(
            selected(
                "admin_user",
                "FORGEJO_ADMIN_USER",
                "",
                DEFAULT_ADMIN_USER,
            ),
            label="admin_user",
        )
        admin_email = self._validate_email(
            selected(
                "admin_email",
                "FORGEJO_ADMIN_EMAIL",
                "",
                DEFAULT_ADMIN_EMAIL,
            )
        )
        database_name = self._validate_name(
            selected(
                "database_name",
                "FORGEJO_DB_NAME",
                "database_name",
                DEFAULT_DATABASE_NAME,
            ),
            label="database_name",
        )
        database_user = self._validate_name(
            selected(
                "database_user",
                "FORGEJO_DB_USER",
                "database_user",
                DEFAULT_DATABASE_USER,
            ),
            label="database_user",
        )
        upstream_version = self._validate_upstream_version(
            selected(
                "upstream_version",
                "FORGEJO_VERSION",
                "",
                (
                    str(record["version"])
                    if record is not None
                    else DEFAULT_UPSTREAM_VERSION
                ),
            )
        )
        if "boot" in inputs:
            boot = inputs["boot"]
        elif os.environ.get("FORGEJO_BOOT"):
            boot = os.environ["FORGEJO_BOOT"]
        elif self.paths.marker.exists():
            boot = "enabled" if self._service_enabled() == "enabled" else "disabled"
        else:
            boot = DEFAULT_BOOT
        if boot not in {"enabled", "disabled"}:
            raise ManagementError(
                78, "INVALID_CONFIGURATION", "boot must be enabled or disabled."
            )
        if os.environ.get("FORGEJO_HTTP_PORT", str(FIXED_PORT)) != str(FIXED_PORT):
            raise ManagementError(
                78,
                "INVALID_CONFIGURATION",
                f"FORGEJO_HTTP_PORT is fixed at {FIXED_PORT}.",
            )
        for input_name in SECRET_INPUTS:
            value = inputs.get(input_name)
            if value is not None:
                if not isinstance(value, str):
                    raise ManagementError(
                        65, "INVALID_SECRET", f"{input_name} must be a path."
                    )
                secure_secret_file(Path(value))
        return Configuration(
            admin_user,
            admin_email,
            database_name,
            database_user,
            upstream_version,
            str(boot),
            (
                existing["host"]
                if existing is not None
                and HOST_RE.fullmatch(existing.get("host", ""))
                else self._host()
            ),
        )

    def _request(self, path: Path, operation: str) -> dict[str, Any]:
        if not path.is_absolute():
            raise ManagementError(
                65, "UNSAFE_REQUEST", "Request path must be absolute."
            )
        try:
            metadata = path.lstat()
        except OSError as exc:
            raise ManagementError(
                66, "REQUEST_MISSING", "Request file does not exist."
            ) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != 0
            or stat.S_IMODE(metadata.st_mode) & 0o077
        ):
            raise ManagementError(
                73,
                "UNSAFE_REQUEST",
                "Request file must be a root-owned private regular file.",
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
            raise ManagementError(
                65, "INVALID_REQUEST", "Request fields are invalid."
            )
        if (
            value["schema_version"] != 1
            or value["product_id"] != PRODUCT_ID
            or value["operation"] != operation
        ):
            raise ManagementError(
                65, "INVALID_REQUEST", "Request identity is invalid."
            )
        validate_uuid(value["correlation_id"], label="correlation_id")
        if value["requested_by"] not in {"operator", "beep"}:
            raise ManagementError(
                65, "INVALID_REQUEST", "requested_by is invalid."
            )
        if not isinstance(value["inputs"], dict):
            raise ManagementError(
                65, "INVALID_REQUEST", "inputs must be an object."
            )
        if value["confirmation"] is not None and not isinstance(
            value["confirmation"], str
        ):
            raise ManagementError(
                65, "INVALID_REQUEST", "confirmation is invalid."
            )
        if operation == "uninstall":
            if not isinstance(value.get("retain_state"), bool):
                raise ManagementError(
                    65, "INVALID_REQUEST", "uninstall requires retain_state."
                )
        elif "retain_state" in value:
            raise ManagementError(
                65,
                "INVALID_REQUEST",
                "retain_state is accepted only for uninstall.",
            )
        return value

    @staticmethod
    def _environment_inputs(operation: str) -> dict[str, str]:
        if operation not in CONFIGURATION_OPERATIONS:
            return {}
        mapping = {
            "FORGEJO_ADMIN_USER": "admin_user",
            "FORGEJO_ADMIN_EMAIL": "admin_email",
            "FORGEJO_DB_NAME": "database_name",
            "FORGEJO_DB_USER": "database_user",
            "FORGEJO_ADMIN_PASSWORD_FILE": "admin_password_file",
            "FORGEJO_DB_PASSWORD_FILE": "database_password_file",
            "FORGEJO_VERSION": "upstream_version",
            "FORGEJO_BOOT": "boot",
        }
        return {
            destination: os.environ[source]
            for source, destination in mapping.items()
            if os.environ.get(source)
        }

    def invocation(self, args: argparse.Namespace) -> Invocation:
        unknown_environment = sorted(
            name
            for name in os.environ
            if name.startswith("FORGEJO_") and name not in KNOWN_ENV
        )
        if unknown_environment:
            raise ManagementError(
                65,
                "UNKNOWN_ENVIRONMENT",
                f"Unknown Forgejo environment variable: {unknown_environment[0]}",
            )
        if os.environ.get("FORGEJO_TEST_RELEASE_BASE") and not Path(
            "/run/forgejo/tests-enabled"
        ).is_file():
            raise ManagementError(
                64,
                "TEST_OVERRIDE_FORBIDDEN",
                "FORGEJO_TEST_RELEASE_BASE is available only in guarded tests.",
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
        if request is None:
            inputs.update(self._environment_inputs(args.operation))
        unknown_inputs = set(inputs) - OPERATION_INPUTS[args.operation]
        if unknown_inputs:
            raise ManagementError(
                65,
                "UNKNOWN_INPUT",
                f"Unknown input for {args.operation}: {sorted(unknown_inputs)[0]}",
            )
        non_interactive = bool(
            args.non_interactive
            or os.environ.get("FORGEJO_NONINTERACTIVE") == "1"
        )
        self._prepare_interactive_install(
            args,
            inputs,
            request_supplied=request is not None,
            non_interactive=non_interactive,
        )
        confirmation = (
            request["confirmation"] if request is not None else args.confirmation
        )
        retain_state: bool | None = None
        if args.operation == "uninstall":
            if request is not None:
                retain_state = request["retain_state"]
            else:
                retain_state = not args.purge
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
                    "Forgejo is not installed with a valid ownership marker.",
                )
            return None
        try:
            metadata = self.paths.marker.lstat()
        except OSError as exc:
            raise ManagementError(
                73, "UNSAFE_MARKER", "Cannot inspect the Forgejo marker."
            ) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o644
        ):
            raise ManagementError(
                73, "UNSAFE_MARKER", "Forgejo ownership marker metadata is invalid."
            )
        value = read_json(self.paths.marker)
        if set(value) == PREVIOUS_MARKER_FIELDS:
            if not isinstance(value["updated_at"], str) or not value["updated_at"]:
                raise ManagementError(
                    65,
                    "INVALID_MARKER",
                    "Previous Forgejo marker metadata is invalid.",
                )
            value = {
                key: item
                for key, item in value.items()
                if key != "updated_at"
            }
            value["install_root"] = str(self.paths.install_root)
            value["lifecycle_entrypoint"] = str(self.paths.entrypoint)
            value["artifact_sha256"] = None
        elif set(value) != MARKER_FIELDS:
            raise ManagementError(
                65, "INVALID_MARKER", "Forgejo marker fields are invalid."
            )
        if (
            value["schema_version"] != 1
            or value["product_id"] != PRODUCT_ID
            or value["install_root"] != str(self.paths.install_root)
            or value["lifecycle_entrypoint"] != str(self.paths.entrypoint)
        ):
            raise ManagementError(
                73, "UNSAFE_MARKER", "Forgejo marker identity is invalid."
            )
        validate_uuid(value["instance_id"], label="marker instance_id")
        validate_version(value["version"])
        if not isinstance(value["installed_at"], str) or not value["installed_at"]:
            raise ManagementError(
                65, "INVALID_MARKER", "Marker installation time is invalid."
            )
        if not isinstance(value["source_revision"], str) or not value[
            "source_revision"
        ]:
            raise ManagementError(
                65, "INVALID_MARKER", "Marker revision is invalid."
            )
        artifact = value["artifact_sha256"]
        if artifact is not None and (
            not isinstance(artifact, str)
            or len(artifact) != 64
            or any(character not in "0123456789abcdef" for character in artifact)
        ):
            raise ManagementError(
                65, "INVALID_MARKER", "Marker artifact digest is invalid."
            )
        return value

    def _migrate_previous_marker(self) -> bool:
        if not self.paths.marker.exists():
            return False
        normalized = self.load_marker(required=True)
        value = read_json(self.paths.marker)
        if set(value) != PREVIOUS_MARKER_FIELDS:
            return False
        atomic_write(
            self.paths.marker,
            canonical_json(normalized) + b"\n",
            mode=0o644,
        )
        return True

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
                ("ownership", "Validate product ownership and host boundaries"),
                ("packages", "Converge PostgreSQL, Caddy, Avahi, and git prerequisites"),
                ("binary", "Install a checksum-verified Forgejo release"),
                ("database", "Converge the PostgreSQL role and database"),
                ("configuration", "Preserve secrets and deploy the loopback configuration"),
                ("network", "Configure Caddy HTTPS, local CA trust, and Avahi"),
                ("health", "Migrate and verify the complete HTTPS service path"),
                ("marker", "Write ownership only after successful boundary checks"),
            ],
            "repair": [
                ("ownership", "Validate the product ownership marker"),
                ("configuration", "Reassert protected files and shared-edge fragments"),
                ("health", "Restore the declared service state and verify boundaries"),
            ],
            "backup": [
                ("ownership", "Validate the product ownership marker"),
                ("archive", "Create and verify a database, configuration, and repository backup"),
            ],
            "update": [
                ("ownership", "Validate ownership and the candidate product release"),
                ("backup", "Create a pre-update backup and rollback snapshot"),
                ("migrate", "Install the candidate binary, configuration, and database migration"),
                ("health", "Verify the loopback and HTTPS endpoints"),
            ],
            "rollback": [
                ("ownership", "Validate ownership and the saved rollback snapshot"),
                ("restore", "Restore the prior product, binary, configuration, and database"),
                ("health", "Verify the restored service and dependent runner"),
            ],
            "suspend": [
                ("ownership", "Validate the product ownership marker"),
                ("service", "Stop Forgejo and its co-located dependent runner"),
            ],
            "resume": [
                ("ownership", "Validate product integrity while suspended"),
                ("service", "Resume Forgejo and the previously active runner"),
            ],
            "uninstall": [
                ("ownership", "Validate ownership before removing any resource"),
                ("dependency", "Require the co-located runner to be removed first"),
                ("service", "Remove the product-owned service and network edge"),
                ("state", "Retain or explicitly purge repositories, secrets, and database"),
            ],
        }
        return [
            {"id": identifier, "summary": summary, "mutates": True}
            for identifier, summary in steps.get(operation, [])
        ]

    def _backup_destination(self, invocation: Invocation) -> Path:
        value = invocation.inputs.get(
            "backup_destination",
            os.environ.get("FORGEJO_BACKUP_DESTINATION", str(self.paths.backup_root)),
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
            if destination == root or is_relative_to(destination, root):
                raise ManagementError(
                    78,
                    "INVALID_BACKUP_DESTINATION",
                    "Backup destination must be outside product-owned roots.",
                )
        return destination

    def plan_digest(
        self,
        invocation: Invocation,
        steps: list[dict[str, Any]],
        configuration: Configuration | None,
    ) -> str:
        marker = self.load_marker()
        plan_inputs: dict[str, Any] = {}
        if configuration is not None:
            plan_inputs = configuration.public_object()
            for name in SECRET_INPUTS:
                value = invocation.inputs.get(name)
                if isinstance(value, str):
                    plan_inputs[name] = sha256_bytes(Path(value).read_bytes())
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
                    "Another Forgejo lifecycle operation is running.",
                    retryable=True,
                ) from exc
            yield
        finally:
            os.close(descriptor)

    def run(self, invocation: Invocation) -> tuple[Result, int]:
        result = Result(
            invocation.operation,
            invocation.correlation_id,
            self.version,
            self.instance_id(),
            operation_phase(invocation.operation, dry_run=invocation.dry_run),
        )
        if invocation.operation == "describe":
            result.details = {"descriptor": self.descriptor}
            return result, 0
        if invocation.operation in {"status", "verify", "doctor"}:
            checks = self.verify_checks(probe=invocation.operation != "doctor")
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
        if configuration is not None:
            result.details = {
                "configuration": configuration.public_object(),
            }
        destructive = (
            invocation.operation == "uninstall" and invocation.retain_state is False
        )
        result.requires_confirmation = True
        if invocation.dry_run:
            if destructive:
                result.required_inputs = [
                    {"name": "confirmation", "secret": False}
                ]
            return result, 0
        if invocation.supplied_plan_digest is not None and (
            invocation.supplied_plan_digest != result.plan_digest
        ):
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
            print_plan(
                result,
                configuration=(
                    configuration.public_object()
                    if configuration is not None
                    else None
                ),
                file=sys.stderr if invocation.json_output else sys.stdout,
            )
            answer = self._prompt(
                "Apply this plan? [y/N]: ",
                as_json=invocation.json_output,
            ).strip().lower()
            if answer not in {"y", "yes"}:
                raise ManagementError(
                    64, "CONFIRMATION_REQUIRED", "Operation cancelled."
                )
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
                    78,
                    "PLAN_CHANGED",
                    "Host state changed while acquiring the product lock.",
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
                (
                    changed_resources,
                    previous_version,
                    backup_path,
                ) = self._execute_backup(invocation)
            elif invocation.operation == "update":
                (
                    changed_resources,
                    previous_version,
                    backup_path,
                ) = self._execute_update(invocation, configuration)
            elif invocation.operation == "rollback":
                changed_resources, previous_version = self._execute_rollback()
            elif invocation.operation == "suspend":
                changed_resources, previous_version = self._execute_suspend()
            elif invocation.operation == "resume":
                changed_resources, previous_version = self._execute_resume()
            elif invocation.operation == "uninstall":
                changed_resources, previous_version = self._execute_uninstall(
                    invocation
                )
            else:
                raise ManagementError(
                    65, "UNKNOWN_OPERATION", "Unknown operation."
                )
            if self._migrate_previous_marker():
                changed_resources.append(str(self.paths.marker))
            result.changed = bool(changed_resources)
            marker = self.load_marker()
            result.instance_id = (
                str(marker["instance_id"]) if marker is not None else result.instance_id
            )
            result.details = (
                {"configuration": configuration.public_object()}
                if configuration is not None
                else {}
            )
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
                if self.paths.retained.exists():
                    lifecycle = "retained"
                elif self.paths.suspended.exists():
                    lifecycle = "suspended"
                else:
                    lifecycle = "active"
            elif self._legacy_installation_valid():
                lifecycle = "legacy"
            configuration: dict[str, Any] = {}
            try:
                public = self._existing_public_config()
                record = self._binary_record()
                if public is not None:
                    configuration = {
                        "url": public["root_url"],
                        "backend": f"http://127.0.0.1:{FIXED_PORT}/",
                        "database_name": public["database_name"],
                        "database_user": public["database_user"],
                        "upstream_version": (
                            record["version"] if record is not None else None
                        ),
                        "boot": self._service_enabled(),
                        "runner_present": self._runner_present(),
                    }
            except ManagementError:
                pass
            return {
                "lifecycle": lifecycle,
                "installed_version": marker["version"] if marker is not None else None,
                "configuration": configuration,
            }

    def verify_checks(self, *, probe: bool = True) -> list[dict[str, str]]:
            checks: list[dict[str, str]] = []
            try:
                marker = self.load_marker(required=True)
            except ManagementError as exc:
                checks.append(
                    self.check(
                        "ownership_marker",
                        False,
                        exc.message,
                        "Run forgejo-manage install to adopt or install Forgejo.",
                    )
                )
                if self._legacy_installation_valid():
                    checks.append(
                        self.check(
                            "legacy_installation",
                            False,
                            "A valid legacy Forgejo installation can be adopted.",
                            f"Run forgejo-manage install --confirmation '{ADOPT_CONFIRMATION}' --yes.",
                            warning=True,
                        )
                    )
                return checks
            checks.append(self.check("ownership_marker", True, "Ownership marker is valid."))
            checks.append(
                self.check(
                    "log_ownership",
                    self._log_ownership_valid(),
                    "Lifecycle audit storage has protected ownership.",
                    "Restore /var/log/forgejo/product-ownership.",
                )
            )
            if self.paths.retained.exists():
                checks.append(
                    self.check(
                        "retained_state",
                        False,
                        "Forgejo runtime is removed while repositories and secrets are retained.",
                        "Run forgejo-manage install to restore service.",
                        warning=True,
                    )
                )
                return checks
            expected_files = (
                (self.paths.descriptor, 0o644, 0, 0, "descriptor"),
                (self.paths.entrypoint, 0o755, 0, 0, "lifecycle_entrypoint"),
                (self.paths.binary, 0o755, 0, 0, "binary"),
                (self.paths.binary_metadata, 0o644, 0, 0, "binary_metadata"),
                (self.paths.unit, 0o644, 0, 0, "systemd_unit"),
                (self.paths.logrotate, 0o644, 0, 0, "log_rotation"),
                (self.paths.app_ini, 0o640, 0, self._git_gid(), "configuration"),
                (self.paths.avahi_service, 0o644, 0, 0, "avahi_service"),
                (self.paths.exported_ca, 0o644, 0, 0, "exported_ca"),
                (self.paths.trusted_ca, 0o644, 0, 0, "trusted_ca"),
            )
            for path, mode, uid, gid, identifier in expected_files:
                checks.append(
                    self.check(
                        identifier,
                        self._file_metadata_matches(path, mode, uid, gid),
                        f"{path} is present with protected ownership.",
                        "Run forgejo-manage repair after reconciling unsafe ownership.",
                    )
                )
            checks.append(
                self.check(
                    "service_identity",
                    self._account_valid(),
                    "The git service account matches the declared identity.",
                    "Reconcile the git account before repair.",
                )
            )
            configuration_valid = False
            recovery_valid = False
            try:
                configuration_valid = self._configuration_boundary_valid()
                recovery_valid = self._configuration_has_recovery_material()
            except ManagementError:
                pass
            checks.append(
                self.check(
                    "configuration_boundary",
                    configuration_valid,
                    "Forgejo is fixed to the loopback backend and HTTPS public URL.",
                    "Recover app.ini or run forgejo-manage repair.",
                )
            )
            checks.append(
                self.check(
                    "configuration_recovery",
                    recovery_valid,
                    "Database and encryption recovery material is present.",
                    "Recover the original app.ini from a protected backup.",
                )
            )
            binary_valid = False
            try:
                record = self._binary_record()
                binary_valid = (
                    record is not None
                    and self.paths.binary.is_file()
                    and sha256_file(self.paths.binary) == record["sha256"]
                )
            except (ManagementError, OSError):
                pass
            checks.append(
                self.check(
                    "binary_integrity",
                    binary_valid,
                    "Forgejo binary matches its recorded upstream checksum.",
                    "Run forgejo-manage repair to restore the verified binary.",
                )
            )
            checks.append(
                self.check(
                    "postgresql",
                    self._service_active_named("postgresql.service"),
                    "PostgreSQL is active.",
                    "Start PostgreSQL and inspect its journal.",
                )
            )
            checks.append(
                self.check(
                    "database",
                    self._database_resources_exist(),
                    "The declared Forgejo database and role exist.",
                    "Restore the PostgreSQL backup before repair.",
                )
            )
            checks.append(
                self.check(
                    "caddy_route",
                    self._caddy_route_valid(),
                    "Caddy has one exact internal-TLS Forgejo route.",
                    "Run forgejo-manage repair after reconciling the Caddyfile.",
                )
            )
            checks.append(
                self.check(
                    "caddy_configuration",
                    self._caddy_configuration_valid(),
                    "The active Caddy configuration validates.",
                    "Validate /etc/caddy/Caddyfile before repair.",
                )
            )
            checks.append(
                self.check(
                    "local_ca",
                    self._local_ca_current(),
                    "Exported and trusted Caddy local CA copies are current.",
                    "Run forgejo-manage repair to re-export local CA trust.",
                )
            )
            drop_ins = self._unit_drop_ins("forgejo.service")
            checks.append(
                self.check(
                    "systemd_drop_ins",
                    not drop_ins,
                    "Forgejo has no unmanaged systemd drop-ins.",
                    "Remove or reconcile unmanaged forgejo.service drop-ins.",
                )
            )
            suspended = self.paths.suspended.exists()
            active = self._service_active()
            enabled = self._service_enabled() == "enabled"
            if suspended:
                suspension_valid = True
                try:
                    self._load_suspension()
                except ManagementError:
                    suspension_valid = False
                checks.append(
                    self.check(
                        "suspension_metadata",
                        suspension_valid,
                        "Forgejo suspension intent is protected and valid.",
                        "Recover or remove invalid suspension metadata before resume.",
                    )
                )
                checks.append(
                    self.check(
                        "suspension",
                        (
                            not active
                            and not enabled
                            and not self._runner_active()
                            and (
                                not self._runner_present()
                                or self._service_enabled_named(
                                    "forgejo-runner.service"
                                )
                                != "enabled"
                            )
                        ),
                        "Forgejo and its dependent runner are stopped and "
                        "disabled while suspended.",
                        "Stop and disable both services before repairing "
                        "suspension state.",
                    )
                )
            else:
                checks.append(
                    self.check(
                        "service_enabled",
                        enabled,
                        "Forgejo is enabled at boot.",
                        "Run forgejo-manage repair or set FORGEJO_BOOT=disabled.",
                        warning=not enabled,
                    )
                )
                checks.append(
                    self.check(
                        "service_active",
                        active,
                        "Forgejo is active.",
                        "Inspect journalctl -u forgejo.service.",
                        warning=not enabled and not active,
                    )
                )
                if probe and active:
                    checks.append(
                        self.check(
                            "loopback_health",
                            self._health(),
                            "The loopback health endpoint responds.",
                            "Inspect Forgejo and PostgreSQL journals.",
                        )
                    )
                    checks.append(
                        self.check(
                            "https_health",
                            self._https_health(),
                            "The Caddy HTTPS health endpoint validates against the local CA.",
                            "Inspect Caddy, CA trust, Avahi, and Forgejo.",
                        )
                    )
            if self._runner_present():
                if not suspended:
                    checks.append(
                        self.check(
                            "runner_dependency",
                            active and self._runner_active(),
                            "The co-located runner is active only with healthy Forgejo.",
                            "Repair Forgejo, then repair forgejo-runner.",
                        )
                    )
                checks.append(
                    self.check(
                        "runner_same_host_boundary",
                        self._runner_same_host_config_valid(),
                        "Runner jobs use host networking, fixed name resolution, and trusted CA injection.",
                        "Re-run the forgejo-runner compatibility install.",
                    )
                )
            if marker["version"] != self.version:
                checks.append(
                    self.check(
                        "source_version",
                        False,
                        "Invoked source and installed product versions differ.",
                        "Use update to switch product versions.",
                        warning=True,
                    )
                )
            return checks

    @staticmethod
    def _file_metadata_matches(
            path: Path, mode: int, uid: int, gid: int
    ) -> bool:
            try:
                metadata = path.lstat()
            except OSError:
                return False
            return (
                stat.S_ISREG(metadata.st_mode)
                and not stat.S_ISLNK(metadata.st_mode)
                and metadata.st_uid == uid
                and metadata.st_gid == gid
                and stat.S_IMODE(metadata.st_mode) == mode
            )

    @staticmethod
    def _directory_matches(
            path: Path, mode: int, uid: int, gid: int
    ) -> bool:
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

    @staticmethod
    def _run(
            command: list[str],
            *,
            check: bool = True,
            timeout: int = 180,
            input_text: str | None = None,
            environment: dict[str, str] | None = None,
            stdin: Any | None = None,
            stdout: Any | None = None,
    ) -> subprocess.CompletedProcess[str]:
            if input_text is not None and stdin is not None:
                raise ManagementError(
                    70,
                    "INTERNAL_ERROR",
                    "A command cannot use both text and file input.",
                )
            try:
                return subprocess.run(
                    command,
                    check=check,
                    text=True,
                    input=input_text,
                    stdin=stdin,
                    stdout=subprocess.PIPE if stdout is None else stdout,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env=environment,
                )
            except FileNotFoundError as exc:
                raise ManagementError(
                    69,
                    "DEPENDENCY_MISSING",
                    f"Required command is unavailable: {command[0]}",
                ) from exc
            except subprocess.TimeoutExpired as exc:
                raise ManagementError(
                    75,
                    "COMMAND_TIMEOUT",
                    f"Timed out running required command: {command[0]}",
                    retryable=True,
                ) from exc
            except subprocess.CalledProcessError as exc:
                raise ManagementError(
                    1,
                    "COMMAND_FAILED",
                    f"Required command failed: {command[0]}",
                ) from exc

    def _run_as(
            self,
            user: str,
            command: list[str],
            *,
            check: bool = True,
            timeout: int = 180,
            input_text: str | None = None,
            stdin: Any | None = None,
            stdout: Any | None = None,
    ) -> subprocess.CompletedProcess[str]:
            return self._run(
                ["runuser", "-u", user, "--", *command],
                check=check,
                timeout=timeout,
                input_text=input_text,
                stdin=stdin,
                stdout=stdout,
            )

    def _platform_preflight(self) -> None:
            try:
                fields = {}
                for line in Path("/etc/os-release").read_text(
                    encoding="utf-8"
                ).splitlines():
                    key, separator, raw = line.partition("=")
                    if separator:
                        fields[key] = raw.strip().strip('"')
            except OSError as exc:
                raise ManagementError(
                    69, "UNSUPPORTED_PLATFORM", "Cannot identify this host."
                ) from exc
            if fields.get("ID") != "ubuntu" or fields.get("VERSION_ID") not in {
                "22.04",
                "24.04",
            }:
                raise ManagementError(
                    69,
                    "UNSUPPORTED_PLATFORM",
                    "Forgejo supports Ubuntu 22.04 and 24.04 LTS only.",
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
                    f"127.0.0.1:{FIXED_PORT} is already in use by another service.",
                ) from exc
            finally:
                candidate.close()

    def _service_active_named(self, unit: str) -> bool:
            result = self._run(
                ["systemctl", "is-active", "--quiet", unit],
                check=False,
                timeout=15,
            )
            return result.returncode == 0

    def _service_active(self) -> bool:
            return self._service_active_named("forgejo.service")

    def _service_enabled_named(self, unit: str) -> str:
            result = self._run(
                ["systemctl", "is-enabled", unit],
                check=False,
                timeout=15,
            )
            return result.stdout.strip() if result.returncode == 0 else "disabled"

    def _service_enabled(self) -> str:
            return self._service_enabled_named("forgejo.service")

    def _runner_present(self) -> bool:
            return any(
                (
                    Path("/etc/systemd/system/forgejo-runner.service").exists(),
                    Path("/usr/local/bin/forgejo-runner").exists(),
                    Path("/var/lib/forgejo-runner/.runner").exists(),
                )
            )

    def _runner_active(self) -> bool:
            return self._service_active_named("forgejo-runner.service")

    def _stop_services(self) -> bool:
            runner_was_active = self._runner_active()
            if runner_was_active:
                self._run(
                    ["systemctl", "stop", "forgejo-runner.service"], check=False
                )
                if self._runner_active():
                    raise ManagementError(
                        1,
                        "RUNNER_STOP_FAILED",
                        "forgejo-runner.service did not stop before Forgejo mutation.",
                    )
            if self._service_active():
                self._run(["systemctl", "stop", "forgejo.service"], check=False)
                if self._service_active():
                    raise ManagementError(
                        1,
                        "SERVICE_STOP_FAILED",
                        "forgejo.service did not reach the stopped state.",
                    )
            return runner_was_active

    def _enforce_suspension(self) -> None:
            self._stop_services()
            self._run(
                ["systemctl", "disable", "forgejo.service"],
                check=False,
            )
            if self._runner_present():
                self._run(
                    ["systemctl", "disable", "forgejo-runner.service"],
                    check=False,
                )

    def _restore_after_failed_mutation(
            self,
            *,
            server_was_active: bool,
            runner_was_active: bool,
            was_suspended: bool,
    ) -> None:
            if was_suspended:
                try:
                    self._enforce_suspension()
                except ManagementError:
                    pass
                return
            if (
                not server_was_active
                or not self.paths.unit.is_file()
            ):
                return
            try:
                self._run(
                    ["systemctl", "start", "forgejo.service"],
                    check=False,
                )
                if (
                    runner_was_active
                    and self._health()
                    and self._https_health()
                ):
                    self._run(
                        ["systemctl", "start", "forgejo-runner.service"],
                        check=False,
                    )
            except ManagementError:
                return

    def _restore_runner(self, runner_was_active: bool) -> None:
            if not runner_was_active:
                return
            if not self._health() or not self._https_health():
                raise ManagementError(
                    1,
                    "RUNNER_DEPENDENCY_UNHEALTHY",
                    "The runner was not restarted because the complete Forgejo "
                    "HTTPS path is unhealthy.",
                )
            self._run(["systemctl", "start", "forgejo-runner.service"])
            for _ in range(30):
                if self._runner_active():
                    return
                time.sleep(1)
            raise ManagementError(
                1,
                "RUNNER_START_FAILED",
                "The previously active Forgejo runner did not restart.",
            )

    @staticmethod
    def _health() -> bool:
            connection = http.client.HTTPConnection(
                "127.0.0.1", FIXED_PORT, timeout=3
            )
            try:
                connection.request(
                    "GET", "/api/healthz", headers={"Accept": "application/json"}
                )
                response = connection.getresponse()
                response.read(4096)
                return 200 <= response.status < 300
            except (OSError, http.client.HTTPException):
                return False
            finally:
                connection.close()

    def _https_health(self) -> bool:
            if not self.paths.exported_ca.is_file():
                return False
            host = self._configured_host()
            if not host:
                return False
            result = self._run(
                [
                    "curl",
                    "-fsS",
                    "--max-time",
                    "5",
                    "--output",
                    "/dev/null",
                    "--cacert",
                    str(self.paths.exported_ca),
                    "--resolve",
                    f"{host}:443:127.0.0.1",
                    f"https://{host}/api/healthz",
                ],
                check=False,
                timeout=10,
            )
            return result.returncode == 0

    @staticmethod
    def _unit_drop_ins(unit: str) -> list[Path]:
            root = Path("/etc/systemd/system") / f"{unit}.d"
            return sorted(root.glob("*.conf")) if root.is_dir() else []

    def _git_gid(self) -> int:
            try:
                return grp.getgrnam("git").gr_gid
            except KeyError:
                return 0

    def _account_valid(self) -> bool:
            try:
                account = pwd.getpwnam("git")
                group = grp.getgrnam("git")
            except KeyError:
                return False
            supplementary = {
                item.gr_name for item in grp.getgrall() if "git" in item.gr_mem
            }
            return (
                account.pw_gid == group.gr_gid
                and account.pw_dir == str(self.paths.state_root)
                and account.pw_shell == "/bin/bash"
                and not supplementary
            )

    def _configured_host(self) -> str:
            try:
                value = self._existing_public_config()
            except ManagementError:
                return ""
            if value is None:
                return ""
            host = value["host"]
            return host if HOST_RE.fullmatch(host) else ""

    def _configuration_has_recovery_material(self) -> bool:
            sections = parse_ini(self.paths.app_ini)
            database = sections.get("database", {})
            security = sections.get("security", {})
            oauth2 = sections.get("oauth2", {})
            server = sections.get("server", {})
            jwt = re.compile(r"^[A-Za-z0-9_-]{43}$")
            return (
                bool(database.get("PASSWD"))
                and bool(security.get("SECRET_KEY"))
                and bool(security.get("INTERNAL_TOKEN"))
                and jwt.fullmatch(oauth2.get("JWT_SECRET", "")) is not None
                and jwt.fullmatch(server.get("LFS_JWT_SECRET", "")) is not None
            )

    def _configuration_boundary_valid(self) -> bool:
            sections = parse_ini(self.paths.app_ini)
            database = sections.get("database", {})
            server = sections.get("server", {})
            service = sections.get("service", {})
            actions = sections.get("actions", {})
            session = sections.get("session", {})
            security = sections.get("security", {})
            repository = sections.get("repository", {})
            lfs = sections.get("lfs", {})
            host = server.get("DOMAIN", "")
            return (
                database.get("DB_TYPE") == "postgres"
                and database.get("HOST") == "127.0.0.1:5432"
                and NAME_RE.fullmatch(database.get("NAME", "")) is not None
                and NAME_RE.fullmatch(database.get("USER", "")) is not None
                and server.get("HTTP_ADDR") == "127.0.0.1"
                and server.get("HTTP_PORT") == str(FIXED_PORT)
                and HOST_RE.fullmatch(host) is not None
                and server.get("ROOT_URL") == f"https://{host}/"
                and server.get("LOCAL_ROOT_URL")
                == f"http://127.0.0.1:{FIXED_PORT}/"
                and server.get("LFS_START_SERVER", "").lower() == "true"
                and repository.get("ROOT")
                == "/var/lib/forgejo/data/forgejo-repositories"
                and lfs.get("PATH") == "/var/lib/forgejo/data/lfs"
                and service.get("DISABLE_REGISTRATION", "").lower() == "true"
                and actions.get("ENABLED", "").lower() == "true"
                and session.get("COOKIE_NAME") == "forgejo_session"
                and session.get("COOKIE_SECURE", "").lower() == "true"
                and security.get("INSTALL_LOCK", "").lower() == "true"
                and security.get("COOKIE_REMEMBER_NAME") == "forgejo_remember"
            )

    def _database_resources_exist(self) -> bool:
            try:
                sections = parse_ini(self.paths.app_ini)
            except ManagementError:
                return False
            database = sections.get("database", {})
            name = database.get("NAME", "")
            user = database.get("USER", "")
            if not NAME_RE.fullmatch(name) or not NAME_RE.fullmatch(user):
                return False
            role = self._run_as(
                "postgres",
                [
                    "psql",
                    "-tAc",
                    f"SELECT 1 FROM pg_roles WHERE rolname = '{user}'",
                ],
                check=False,
            )
            db = self._run_as(
                "postgres",
                [
                    "psql",
                    "-tAc",
                    f"SELECT 1 FROM pg_database WHERE datname = '{name}'",
                ],
                check=False,
            )
            return role.stdout.strip() == "1" and db.stdout.strip() == "1"

    def _caddy_route_valid(self) -> bool:
            if not self.paths.caddyfile.is_file():
                return False
            host = self._configured_host()
            if not host:
                return False
            begin = "# BEGIN forgejo-manage Forgejo"
            end = "# END forgejo-manage Forgejo"
            try:
                lines = self.paths.caddyfile.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                return False
            managed = False
            begin_count = 0
            end_count = 0
            body: list[str] = []
            for line in lines:
                if line == begin:
                    begin_count += 1
                    managed = True
                    continue
                if line == end:
                    end_count += 1
                    managed = False
                    continue
                if managed:
                    body.append(line.strip())
            return (
                begin_count == 1
                and end_count == 1
                and not managed
                and body.count(f"https://{host} {{") == 1
                and body.count("tls internal") == 1
                and body.count(f"reverse_proxy 127.0.0.1:{FIXED_PORT}") == 1
            )

    def _caddy_configuration_valid(self) -> bool:
            if not self.paths.caddyfile.is_file():
                return False
            result = self._run(
                [
                    "caddy",
                    "validate",
                    "--config",
                    str(self.paths.caddyfile),
                    "--adapter",
                    "caddyfile",
                ],
                check=False,
                timeout=30,
            )
            return result.returncode == 0

    def _local_ca_current(self) -> bool:
            try:
                digest = sha256_file(self.paths.caddy_ca)
                return (
                    sha256_file(self.paths.exported_ca) == digest
                    and sha256_file(self.paths.trusted_ca) == digest
                )
            except ManagementError:
                return False

    def _runner_same_host_config_valid(self) -> bool:
            path = Path("/var/lib/forgejo-runner/config.yaml")
            try:
                value = path.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return False
            host = self._configured_host()
            required = (
                "  network: host",
                "  privileged: false",
                "  valid_volumes: []",
                '  docker_host: "-"',
                "    SSL_CERT_FILE: /etc/ssl/certs/ca-certificates.crt",
                "    NODE_EXTRA_CA_CERTS: /etc/ssl/certs/ca-certificates.crt",
                "--volume /etc/ssl/certs/ca-certificates.crt:"
                "/etc/ssl/certs/ca-certificates.crt:ro",
                f"--add-host {host}:127.0.0.1",
            )
            return bool(host) and all(item in value for item in required)

    def _legacy_manifest_valid(self) -> bool:
            path = self.paths.migration_manifest
            if path is None:
                return False
            try:
                metadata = path.lstat()
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeError):
                return False
            if (
                not stat.S_ISREG(metadata.st_mode)
                or stat.S_ISLNK(metadata.st_mode)
                or metadata.st_uid != 0
                or metadata.st_gid != 0
                or stat.S_IMODE(metadata.st_mode) != 0o644
            ):
                return False
            values: dict[str, str] = {}
            for line in lines:
                key, separator, value = line.partition("=")
                if (
                    not separator
                    or not re.fullmatch(r"[a-z_]+", key)
                    or key in values
                ):
                    return False
                values[key] = value
            fixed_fields = {
                "format",
                "component",
                "converged_utc",
                "component_version",
                "suboptions",
            }
            version_fields = set(values) - fixed_fields
            return (
                fixed_fields.issubset(values)
                and len(values) == len(fixed_fields) + 1
                and len(version_fields) == 1
                and re.fullmatch(
                    r"[a-z][a-z0-9]*(?:_[a-z0-9]+)*_version",
                    next(iter(version_fields)),
                )
                is not None
                and values["format"] == "1"
                and values["component"] == PRODUCT_ID
            )

    def _legacy_installation_valid(self) -> bool:
            if not self._legacy_manifest_valid():
                return False
            if not (
                self.paths.binary.is_file()
                and os.access(self.paths.binary, os.X_OK)
                and self.paths.unit.is_file()
                and self.paths.app_ini.is_file()
                and self._account_valid()
                and self._legacy_configuration_valid()
                and not self._unit_drop_ins("forgejo.service")
            ):
                return False
            try:
                unit = self.paths.unit.read_text(encoding="utf-8")
            except (OSError, UnicodeError):
                return False
            return (
                "User=git" in unit
                and "ExecStart=/usr/local/bin/forgejo web "
                "--config /etc/forgejo/app.ini" in unit
                and "NoNewPrivileges=true" in unit
                and "ReadWritePaths=/var/lib/forgejo" in unit
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
                or stat.S_ISLNK(metadata.st_mode)
                or metadata.st_uid != 0
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

    def _collision_preflight(
            self, invocation: Invocation
    ) -> tuple[dict[str, Any] | None, str, bool]:
            marker = self.load_marker()
            if marker is not None:
                return marker, str(marker["instance_id"]), False
            transaction = self._transaction_instance()
            if transaction is not None:
                return None, transaction, False
            if self._legacy_installation_valid():
                approved = (
                    invocation.confirmation == ADOPT_CONFIRMATION
                    or os.environ.get("FORGEJO_CONFIRM_ADOPTION") == "YES"
                )
                if not approved:
                    raise ManagementError(
                        64,
                        "ADOPTION_CONFIRMATION_REQUIRED",
                        f"Legacy adoption requires confirmation: {ADOPT_CONFIRMATION}",
                    )
                return None, str(uuid.uuid4()), True
            product_paths = (
                self.paths.install_root,
                self.paths.configuration_root,
                self.paths.state_root,
                self.paths.log_root,
                self.paths.cache_root,
                self.paths.backup_root,
                self.paths.unit,
                self.paths.logrotate,
                self.paths.entrypoint,
                self.paths.binary,
                self.paths.avahi_service,
                self.paths.trusted_ca,
                self.paths.legacy_caddy,
            )
            occupied = [path for path in product_paths if path.exists() or path.is_symlink()]
            caddy_owned = False
            if self.paths.caddyfile.is_file():
                try:
                    caddy_owned = any(
                        marker in self.paths.caddyfile.read_text(encoding="utf-8")
                        for marker in (
                            "# BEGIN forgejo-manage Forgejo",
                            "# BEGIN install.sh Forgejo",
                        )
                    )
                except (OSError, UnicodeError):
                    caddy_owned = True
            if caddy_owned:
                occupied.append(self.paths.caddyfile)
            try:
                pwd.getpwnam("git")
            except KeyError:
                pass
            else:
                occupied.append(Path("account:git"))
            if occupied:
                raise ManagementError(
                    73,
                    "UNSAFE_COLLISION",
                    f"Refusing to adopt unmanaged Forgejo resource: {occupied[0]}",
                )
            return None, str(uuid.uuid4()), False

    @staticmethod
    def _ensure_directory(
            path: Path, mode: int, uid: int, gid: int, changed: list[str]
    ) -> None:
            if path.is_symlink():
                raise ManagementError(
                    73, "UNSAFE_COLLISION", f"Directory is a symlink: {path}"
                )
            created = not path.exists()
            path.mkdir(parents=True, exist_ok=True)
            metadata = path.stat()
            if not stat.S_ISDIR(metadata.st_mode):
                raise ManagementError(
                    73, "UNSAFE_COLLISION", f"Path is not a directory: {path}"
                )
            if (
                created
                or stat.S_IMODE(metadata.st_mode) != mode
                or metadata.st_uid != uid
                or metadata.st_gid != gid
            ):
                os.chown(path, uid, gid)
                os.chmod(path, mode)
                changed.append(str(path))

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
                raise ManagementError(
                    66, "SOURCE_MISSING", f"Source asset is missing: {source}"
                ) from exc
            if not self._file_matches(destination, content, mode, uid, gid):
                atomic_write(destination, content, mode=mode, uid=uid, gid=gid)
                changed.append(str(destination))

    def _ensure_transaction(self, instance_id: str, changed: list[str]) -> None:
            content = canonical_json(
                {
                    "schema_version": 1,
                    "product_id": PRODUCT_ID,
                    "instance_id": instance_id,
                }
            ) + b"\n"
            if not self._file_matches(self.paths.transaction, content, 0o600, 0, 0):
                atomic_write(self.paths.transaction, content, mode=0o600)
                changed.append(str(self.paths.transaction))

    def _log_ownership_valid(self) -> bool:
            return self._file_matches(
                self.paths.log_ownership,
                b"product_id=forgejo\nformat=1\n",
                0o600,
                0,
                0,
            )

    def _ensure_log_ownership(self, changed: list[str]) -> None:
            content = b"product_id=forgejo\nformat=1\n"
            if not self._file_matches(self.paths.log_ownership, content, 0o600, 0, 0):
                atomic_write(self.paths.log_ownership, content, mode=0o600)
                changed.append(str(self.paths.log_ownership))

    def _ensure_account(self, changed: list[str]) -> tuple[int, int]:
            try:
                pwd.getpwnam("git")
            except KeyError:
                self._run(
                    [
                        "adduser",
                        "--system",
                        "--group",
                        "--home",
                        str(self.paths.state_root),
                        "--shell",
                        "/bin/bash",
                        "--gecos",
                        "Forgejo git service",
                        "git",
                    ]
                )
                changed.append("account:git")
            if not self._account_valid():
                raise ManagementError(
                    73,
                    "UNSAFE_COLLISION",
                    "The existing git account does not match the declared identity.",
                )
            account = pwd.getpwnam("git")
            group = grp.getgrnam("git")
            return account.pw_uid, group.gr_gid

    def _source_revision(self) -> str:
            digest = hashlib.sha256()
            for path in self._deployment_files(self.source_root):
                relative = path.relative_to(self.source_root).as_posix()
                digest.update(relative.encode("utf-8") + b"\0")
                digest.update(path.read_bytes())
            return f"source-tree-sha256:{digest.hexdigest()}"

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

    def _product_tree_matches(self) -> bool:
            try:
                return (
                    self.paths.product_root.is_dir()
                    and (self.paths.product_root / "VERSION")
                    .read_text(encoding="utf-8")
                    .strip()
                    == self.version
                    and self._deployment_digest(self.paths.product_root)
                    == self._deployment_digest(self.source_root)
                )
            except OSError:
                return False

    @staticmethod
    def _protect_tree(root: Path) -> None:
            for path in sorted(root.rglob("*"), reverse=True):
                if path.is_symlink():
                    raise ManagementError(
                        73, "UNSAFE_SOURCE", "Product tree contains a symlink."
                    )
                if path.is_file():
                    os.chmod(path, 0o755 if path.name == "manage.sh" else 0o644)
                    os.chown(path, 0, 0)
                elif path.is_dir():
                    os.chmod(path, 0o755)
                    os.chown(path, 0, 0)
            os.chmod(root, 0o755)
            os.chown(root, 0, 0)

    def _deploy_product(self, changed: list[str]) -> None:
            if self._product_tree_matches():
                return
            stage = Path(
                tempfile.mkdtemp(prefix=".product-stage.", dir=self.paths.install_root)
            )
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

    @staticmethod
    def _read_bounded_url(url: str, *, limit: int) -> bytes:
            validate_release_url(url)
            request = urllib.request.Request(
                url, headers={"User-Agent": "forgejo-installer/1"}
            )
            opener = urllib.request.build_opener(SafeRedirectHandler())
            try:
                with opener.open(request, timeout=60) as response:
                    validate_release_url(response.geturl())
                    value = response.read(limit + 1)
            except (OSError, urllib.error.URLError) as exc:
                raise ManagementError(
                    75,
                    "DOWNLOAD_FAILED",
                    "Could not download Forgejo release metadata.",
                    retryable=True,
                ) from exc
            if len(value) > limit:
                raise ManagementError(
                    78, "DOWNLOAD_TOO_LARGE", "Forgejo download exceeded its limit."
                )
            return value

    def _resolve_latest_release(self) -> str:
            test_base = os.environ.get("FORGEJO_TEST_RELEASE_BASE")
            urls = (
                [f"{test_base.rstrip('/')}/latest.json"]
                if test_base
                else [
                    f"{origin}/api/v1/repos/forgejo/forgejo/releases/latest"
                    for origin in (
                        "https://data.forgejo.org",
                        "https://code.forgejo.org",
                        "https://codeberg.org",
                    )
                ]
            )
            for url in urls:
                try:
                    value = json.loads(
                        self._read_bounded_url(url, limit=1024 * 1024),
                        object_pairs_hook=strict_object,
                    )
                    tag = str(value.get("tag_name") or value.get("name") or "")
                    tag = tag.removeprefix("v")
                    if RELEASE_RE.fullmatch(tag):
                        return tag
                except (ManagementError, UnicodeError, json.JSONDecodeError):
                    continue
            raise ManagementError(
                66,
                "RELEASE_RESOLUTION_FAILED",
                "Could not resolve the latest Forgejo release; pin FORGEJO_VERSION.",
                retryable=True,
            )

    def _download_verified_binary(
            self, version: str, architecture: str
    ) -> tuple[Path, str, str]:
            asset = f"forgejo-{version}-linux-{architecture}"
            test_base = os.environ.get("FORGEJO_TEST_RELEASE_BASE")
            bases = (
                [test_base.rstrip("/")]
                if test_base
                else [
                    f"https://code.forgejo.org/forgejo/forgejo/releases/download/v{version}",
                    f"https://codeberg.org/forgejo/forgejo/releases/download/v{version}",
                ]
            )
            for base in bases:
                url = f"{base}/{asset}"
                try:
                    checksum = (
                        self._read_bounded_url(f"{url}.sha256", limit=4096)
                        .decode("ascii")
                        .split()[0]
                    )
                    if len(checksum) != 64 or any(
                        character not in "0123456789abcdef"
                        for character in checksum
                    ):
                        continue
                    destination = self.paths.cache_root / asset
                    if (
                        destination.is_file()
                        and sha256_file(destination) == checksum
                    ):
                        return destination, checksum, url
                    payload = self._read_bounded_url(url, limit=MAX_DOWNLOAD_BYTES)
                    if hashlib.sha256(payload).hexdigest() != checksum:
                        raise ManagementError(
                            78,
                            "CHECKSUM_MISMATCH",
                            "Forgejo binary does not match its published checksum.",
                        )
                    atomic_write(destination, payload, mode=0o755)
                    return destination, checksum, url
                except (ManagementError, UnicodeError, IndexError):
                    continue
            raise ManagementError(
                66,
                "RELEASE_DOWNLOAD_FAILED",
                f"Could not download a verified Forgejo {version} binary.",
                retryable=True,
            )

    def _install_binary(
            self, requested_version: str, changed: list[str]
    ) -> str:
            version = (
                self._resolve_latest_release()
                if requested_version == "latest"
                else requested_version
            )
            record = self._binary_record()
            if (
                record is not None
                and record["version"] == version
                and self.paths.binary.is_file()
                and sha256_file(self.paths.binary) == record["sha256"]
            ):
                return version
            source, digest, url = self._download_verified_binary(
                version, self._architecture()
            )
            atomic_write(self.paths.binary, source.read_bytes(), mode=0o755)
            changed.append(str(self.paths.binary))
            content = (
                json.dumps(
                    {
                        "schema_version": 1,
                        "version": version,
                        "sha256": digest,
                        "source_url": url,
                    },
                    indent=2,
                    sort_keys=True,
                ).encode("utf-8")
                + b"\n"
            )
            atomic_write(self.paths.binary_metadata, content, mode=0o644)
            changed.append(str(self.paths.binary_metadata))
            return version

    def _install_packages(self, changed: list[str]) -> None:
        packages = (
            "ca-certificates",
            "curl",
            "git",
            "git-lfs",
            "postgresql",
            "postgresql-contrib",
            "openssl",
            "caddy",
            "avahi-daemon",
            "libnss-mdns",
        )
        missing = []
        for package in packages:
            result = self._run(
                ["dpkg-query", "-W", "-f=${db:Status-Abbrev}", package],
                check=False,
                timeout=15,
            )
            if result.returncode != 0 or not result.stdout.startswith("ii "):
                missing.append(package)
        if not missing:
            return
        environment = dict(os.environ)
        environment["DEBIAN_FRONTEND"] = "noninteractive"
        self._run(
            ["apt-get", "update"],
            timeout=600,
            environment=environment,
        )
        self._run(
            [
                "apt-get",
                "install",
                "-y",
                "--no-install-recommends",
                *missing,
            ],
            timeout=1200,
            environment=environment,
        )
        changed.extend(f"package:{package}" for package in missing)

    def _ensure_layout(
        self, uid: int, gid: int, changed: list[str]
    ) -> None:
        for path, mode, owner, group in (
            (self.paths.install_root, 0o755, 0, 0),
            (self.paths.configuration_root, 0o750, 0, gid),
            (self.paths.state_root, 0o750, uid, gid),
            (self.paths.log_root, 0o750, 0, 0),
            (self.paths.receipts, 0o700, 0, 0),
            (self.paths.backup_root, 0o700, 0, 0),
            (self.paths.cache_root, 0o700, 0, 0),
        ):
            self._ensure_directory(path, mode, owner, group, changed)

    @staticmethod
    def _password_safe_for_ini(value: str) -> bool:
        return (
            re.fullmatch(
                r"[A-Za-z0-9._~!@$%^&*()+={}:,?/\-]{8,256}",
                value,
            )
            is not None
        )

    def _secret_input(
        self, invocation: Invocation, input_name: str
    ) -> str | None:
        value = invocation.inputs.get(input_name)
        if value is None:
            return None
        if not isinstance(value, str):
            raise ManagementError(
                65, "INVALID_SECRET", f"{input_name} must be a file path."
            )
        return secure_secret_file(Path(value))

    def _database_state(
        self, configuration: Configuration
    ) -> tuple[bool, bool]:
        user = configuration.database_user
        name = configuration.database_name
        role = self._run_as(
            "postgres",
            [
                "psql",
                "-tAc",
                f"SELECT 1 FROM pg_roles WHERE rolname = '{user}'",
            ],
            check=False,
        )
        database = self._run_as(
            "postgres",
            [
                "psql",
                "-tAc",
                f"SELECT 1 FROM pg_database WHERE datname = '{name}'",
            ],
            check=False,
        )
        return role.stdout.strip() == "1", database.stdout.strip() == "1"

    def _existing_database_password(
        self, configuration: Configuration
    ) -> str | None:
        if not self.paths.app_ini.is_file():
            return None
        if not self._configuration_has_recovery_material():
            return None
        sections = parse_ini(self.paths.app_ini)
        database = sections["database"]
        if (
            database.get("NAME") != configuration.database_name
            or database.get("USER") != configuration.database_user
        ):
            raise ManagementError(
                73,
                "DATABASE_IDENTITY_CONFLICT",
                "Existing app.ini names a different PostgreSQL database or role.",
            )
        return database.get("PASSWD")

    def _configure_database(
        self,
        invocation: Invocation,
        configuration: Configuration,
        changed: list[str],
    ) -> str:
        self._run(["systemctl", "enable", "--now", "postgresql.service"])
        if not self._service_active_named("postgresql.service"):
            raise ManagementError(
                1,
                "POSTGRESQL_UNHEALTHY",
                "PostgreSQL did not become active.",
            )
        role_exists, database_exists = self._database_state(configuration)
        existing_password = self._existing_database_password(configuration)
        supplied_password = self._secret_input(
            invocation, "database_password_file"
        )
        if (role_exists or database_exists) and existing_password is None:
            raise ManagementError(
                73,
                "UNSAFE_DATABASE_COLLISION",
                "An existing Forgejo database or role lacks recoverable managed configuration.",
            )
        password = supplied_password or existing_password or secrets.token_hex(24)
        if not self._password_safe_for_ini(password):
            raise ManagementError(
                65,
                "INVALID_SECRET",
                "The database password contains characters unsafe for app.ini.",
            )
        escaped = password.replace("'", "''")
        role = configuration.database_user
        sql = (
            "DO $$\n"
            "BEGIN\n"
            f"  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN\n"
            f'    CREATE ROLE "{role}" LOGIN PASSWORD \'{escaped}\';\n'
            "  ELSE\n"
            f'    ALTER ROLE "{role}" WITH LOGIN PASSWORD \'{escaped}\';\n'
            "  END IF;\n"
            "END\n"
            "$$;\n"
        )
        self._run_as(
            "postgres",
            ["psql", "-v", "ON_ERROR_STOP=1"],
            input_text=sql,
        )
        if not role_exists:
            changed.append(f"postgresql-role:{role}")
        if not database_exists:
            self._run_as(
                "postgres",
                [
                    "createdb",
                    "-O",
                    configuration.database_user,
                    configuration.database_name,
                ],
            )
            changed.append(f"postgresql-database:{configuration.database_name}")
        return password

    @staticmethod
    def _generated_jwt_secret() -> str:
        value = secrets.token_urlsafe(32)
        if len(value) != 43:
            raise ManagementError(
                70, "SECRET_GENERATION_FAILED", "Could not generate a JWT secret."
            )
        return value

    def _configuration_secrets(self) -> dict[str, str]:
        if not self.paths.app_ini.is_file():
            return {}
        try:
            sections = parse_ini(self.paths.app_ini)
        except ManagementError:
            return {}
        return {
            "secret_key": sections.get("security", {}).get("SECRET_KEY", ""),
            "internal_token": sections.get("security", {}).get(
                "INTERNAL_TOKEN", ""
            ),
            "oauth_jwt": sections.get("oauth2", {}).get("JWT_SECRET", ""),
            "lfs_jwt": sections.get("server", {}).get("LFS_JWT_SECRET", ""),
        }

    def _render_app_ini(
        self,
        configuration: Configuration,
        database_password: str,
    ) -> bytes:
        previous = self._configuration_secrets()
        secret_key = previous.get("secret_key") or secrets.token_hex(32)
        internal_token = previous.get("internal_token") or secrets.token_hex(32)
        oauth_jwt = previous.get("oauth_jwt")
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", oauth_jwt or "") is None:
            oauth_jwt = self._generated_jwt_secret()
        lfs_jwt = previous.get("lfs_jwt")
        if re.fullmatch(r"[A-Za-z0-9_-]{43}", lfs_jwt or "") is None:
            lfs_jwt = self._generated_jwt_secret()
        value = f"""; Managed by forgejo-manage.
; Recovery requires this file and the PostgreSQL backup.
APP_NAME = Forgejo
RUN_USER = git
WORK_PATH = /var/lib/forgejo

[database]
DB_TYPE = postgres
HOST = 127.0.0.1:5432
NAME = {configuration.database_name}
USER = {configuration.database_user}
PASSWD = {database_password}

[server]
HTTP_ADDR = 127.0.0.1
HTTP_PORT = {FIXED_PORT}
DOMAIN = {configuration.host}
ROOT_URL = https://{configuration.host}/
LOCAL_ROOT_URL = http://127.0.0.1:{FIXED_PORT}/
LFS_START_SERVER = true
LFS_JWT_SECRET = {lfs_jwt}

[repository]
ROOT = /var/lib/forgejo/data/forgejo-repositories

[lfs]
PATH = /var/lib/forgejo/data/lfs

[security]
INSTALL_LOCK = true
SECRET_KEY = {secret_key}
INTERNAL_TOKEN = {internal_token}
COOKIE_REMEMBER_NAME = forgejo_remember

[oauth2]
JWT_SECRET = {oauth_jwt}

[session]
COOKIE_NAME = forgejo_session
COOKIE_SECURE = true

[service]
DISABLE_REGISTRATION = true

[actions]
ENABLED = true
"""
        return value.encode("utf-8")

    def _write_configuration(
        self,
        configuration: Configuration,
        database_password: str,
        gid: int,
        changed: list[str],
    ) -> None:
        content = self._render_app_ini(configuration, database_password)
        if not self._file_matches(
            self.paths.app_ini, content, 0o640, 0, gid
        ):
            atomic_write(
                self.paths.app_ini,
                content,
                mode=0o640,
                uid=0,
                gid=gid,
            )
            changed.append(str(self.paths.app_ini))

    def _install_assets(self, changed: list[str]) -> None:
        assets = self.paths.product_root / "payload"
        self._install_file(
            self.paths.product_root / "PRODUCT.json",
            self.paths.descriptor,
            0o644,
            changed,
        )
        self._install_file(
            self.paths.product_root / "scripts" / "manage.sh",
            self.paths.entrypoint,
            0o755,
            changed,
        )
        self._install_file(
            assets / "systemd" / "forgejo.service",
            self.paths.unit,
            0o644,
            changed,
        )
        self._install_file(
            assets / "logrotate" / "forgejo",
            self.paths.logrotate,
            0o644,
            changed,
        )

    def _migrate_database(self, gid: int) -> None:
        os.chmod(self.paths.app_ini, 0o660)
        try:
            self._run_as(
                "git",
                [
                    str(self.paths.binary),
                    "migrate",
                    "--config",
                    str(self.paths.app_ini),
                    "--work-path",
                    str(self.paths.state_root),
                ],
                timeout=600,
            )
        finally:
            os.chown(self.paths.configuration_root, 0, gid)
            os.chown(self.paths.app_ini, 0, gid)
            os.chmod(self.paths.configuration_root, 0o750)
            os.chmod(self.paths.app_ini, 0o640)

    def _admin_exists(self, username: str) -> bool:
        result = self._run_as(
            "git",
            [
                str(self.paths.binary),
                "admin",
                "user",
                "list",
                "--admin",
                "--config",
                str(self.paths.app_ini),
                "--work-path",
                str(self.paths.state_root),
            ],
            check=False,
            timeout=60,
        )
        if result.returncode != 0:
            return False
        return any(
            len(fields) > 1 and fields[1] == username
            for line in result.stdout.splitlines()
            if (fields := line.split())
        )

    def _ensure_admin(
        self,
        invocation: Invocation,
        configuration: Configuration,
        changed: list[str],
    ) -> None:
        if self._admin_exists(configuration.admin_user):
            return
        supplied = self._secret_input(invocation, "admin_password_file")
        password = supplied or secrets.token_urlsafe(18)
        command = [
            str(self.paths.binary),
            "admin",
            "user",
            "create",
            "--config",
            str(self.paths.app_ini),
            "--work-path",
            str(self.paths.state_root),
            "--admin",
            "--username",
            configuration.admin_user,
            "--email",
            configuration.admin_email,
            "--password",
            password,
        ]
        if supplied is None:
            command.append("--must-change-password")
        self._run_as("git", command, timeout=60)
        changed.append(f"forgejo-admin:{configuration.admin_user}")
        if supplied is None:
            content = (
                f"username={configuration.admin_user}\n"
                f"credential={password}\n"
                "must_change_password=true\n"
            ).encode("utf-8")
            atomic_write(self.paths.bootstrap_password, content, mode=0o600)
            changed.append(str(self.paths.bootstrap_password))

    @staticmethod
    def _managed_caddy_markers() -> tuple[tuple[str, str], ...]:
        return (
            (
                "# BEGIN forgejo-manage Forgejo",
                "# END forgejo-manage Forgejo",
            ),
            (
                "# BEGIN install.sh Forgejo",
                "# END install.sh Forgejo",
            ),
        )

    def _without_managed_caddy_blocks(self, content: str) -> str:
        markers = self._managed_caddy_markers()
        for begin, end in markers:
            if content.splitlines().count(begin) != content.splitlines().count(end):
                raise ManagementError(
                    73,
                    "CADDY_OWNERSHIP_AMBIGUOUS",
                    "Caddyfile contains an incomplete managed Forgejo block.",
                )
            if content.splitlines().count(begin) > 1:
                raise ManagementError(
                    73,
                    "CADDY_OWNERSHIP_AMBIGUOUS",
                    "Caddyfile contains duplicate managed Forgejo blocks.",
                )
        output: list[str] = []
        active_end = ""
        marker_lines = {
            marker
            for pair in markers
            for marker in pair
        }
        for line in content.splitlines():
            if active_end:
                if line == active_end:
                    active_end = ""
                elif line in marker_lines:
                    raise ManagementError(
                        73,
                        "CADDY_OWNERSHIP_AMBIGUOUS",
                        "Caddyfile contains overlapping managed Forgejo blocks.",
                    )
                continue
            matched = False
            for begin, end in markers:
                if line == begin:
                    active_end = end
                    matched = True
                    break
                if line == end:
                    raise ManagementError(
                        73,
                        "CADDY_OWNERSHIP_AMBIGUOUS",
                        "Caddyfile contains a misplaced managed Forgejo marker.",
                    )
            if not matched:
                output.append(line)
        if active_end:
            raise ManagementError(
                73,
                "CADDY_OWNERSHIP_AMBIGUOUS",
                "Caddyfile contains an incomplete managed Forgejo block.",
            )
        return "\n".join(output).rstrip()

    @staticmethod
    def _packaged_caddy_default(content: str) -> bool:
        lines = [
            line.strip()
            for line in content.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        ]
        return lines == [
            ":80 {",
            "root * /usr/share/caddy",
            "file_server",
            "}",
        ]

    def _render_caddyfile(self, host: str) -> bytes:
        if self.paths.caddyfile.is_symlink():
            raise ManagementError(
                73,
                "CADDY_OWNERSHIP_AMBIGUOUS",
                "The shared Caddyfile must not be a symlink.",
            )
        try:
            current = self.paths.caddyfile.read_text(encoding="utf-8")
        except FileNotFoundError:
            current = ""
        except (OSError, UnicodeError) as exc:
            raise ManagementError(
                73, "CADDY_UNREADABLE", "Cannot safely read the Caddyfile."
            ) from exc
        base = self._without_managed_caddy_blocks(current)
        if self._packaged_caddy_default(base):
            base = ""
        block = (
            "# BEGIN forgejo-manage Forgejo\n"
            "# Forgejo stays on loopback; Caddy is the LAN TLS boundary.\n"
            f"https://{host} {{\n"
            "\ttls internal\n"
            f"\treverse_proxy 127.0.0.1:{FIXED_PORT}\n"
            "}\n"
            "# END forgejo-manage Forgejo\n"
        )
        return ((base + "\n\n") if base else "") .encode("utf-8") + block.encode(
            "utf-8"
        )

    def _configure_caddy(self, host: str, changed: list[str]) -> None:
        content = self._render_caddyfile(host)
        self.paths.caddyfile.parent.mkdir(parents=True, exist_ok=True)
        stage = self.paths.caddyfile.with_name(
            f".Caddyfile.{uuid.uuid4().hex}.stage"
        )
        atomic_write(stage, content, mode=0o644)
        try:
            result = self._run(
                [
                    "caddy",
                    "validate",
                    "--config",
                    str(stage),
                    "--adapter",
                    "caddyfile",
                ],
                check=False,
                timeout=30,
            )
            if result.returncode != 0:
                raise ManagementError(
                    78,
                    "CADDY_VALIDATION_FAILED",
                    "The staged Forgejo Caddy configuration is invalid.",
                )
            if not self._file_matches(
                self.paths.caddyfile, content, 0o644, 0, 0
            ):
                os.replace(stage, self.paths.caddyfile)
                os.chown(self.paths.caddyfile, 0, 0)
                os.chmod(self.paths.caddyfile, 0o644)
                changed.append(str(self.paths.caddyfile))
            else:
                stage.unlink(missing_ok=True)
        finally:
            stage.unlink(missing_ok=True)

    @staticmethod
    def _avahi_content() -> bytes:
        return b"""<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">Forgejo on %h</name>
  <service>
    <type>_https._tcp</type>
    <port>443</port>
  </service>
</service-group>
"""

    def _configure_network_services(self, changed: list[str]) -> None:
        content = self._avahi_content()
        if not self._file_matches(
            self.paths.avahi_service, content, 0o644, 0, 0
        ):
            atomic_write(self.paths.avahi_service, content, mode=0o644)
            changed.append(str(self.paths.avahi_service))
        self._run(["systemctl", "enable", "--now", "avahi-daemon.service"])
        self._run(["systemctl", "enable", "--now", "caddy.service"])
        self._run(["systemctl", "reload-or-restart", "caddy.service"])
        self._run(["systemctl", "reload-or-restart", "avahi-daemon.service"])

    def _export_local_ca(self, changed: list[str]) -> None:
        for _ in range(30):
            if self.paths.caddy_ca.is_file():
                break
            time.sleep(1)
        else:
            raise ManagementError(
                1,
                "CADDY_CA_MISSING",
                "Caddy did not create its local CA certificate.",
            )
        content = self.paths.caddy_ca.read_bytes()
        trust_changed = False
        for path in (self.paths.exported_ca, self.paths.trusted_ca):
            if not self._file_matches(path, content, 0o644, 0, 0):
                atomic_write(path, content, mode=0o644)
                changed.append(str(path))
                if path == self.paths.trusted_ca:
                    trust_changed = True
        if trust_changed:
            self._run(["update-ca-certificates"], timeout=120)

    def _wait_healthy(self) -> None:
        for _ in range(30):
            if self._health():
                return
            time.sleep(2)
        self._run(
            ["systemctl", "disable", "--now", "forgejo.service"],
            check=False,
        )
        raise ManagementError(
            1,
            "FORGEJO_UNHEALTHY",
            "Forgejo did not become healthy and was stopped.",
        )

    def _wait_https_healthy(self) -> None:
        for _ in range(15):
            if self._https_health():
                return
            time.sleep(2)
        raise ManagementError(
            1,
            "HTTPS_UNHEALTHY",
            "Forgejo is healthy on loopback but its Caddy HTTPS endpoint is not.",
        )

    def _activate_service(
        self, configuration: Configuration, changed: list[str]
    ) -> None:
        self._run(["systemctl", "daemon-reload"])
        if configuration.boot == "enabled":
            self._run(["systemctl", "enable", "forgejo.service"])
        else:
            self._run(["systemctl", "disable", "forgejo.service"], check=False)
        self._run(["systemctl", "restart", "forgejo.service"])
        self._wait_healthy()
        self._configure_network_services(changed)
        self._export_local_ca(changed)
        self._wait_https_healthy()

    def _installed_binary_version(self) -> str | None:
        if not self.paths.binary.is_file():
            return None
        result = self._run(
            [str(self.paths.binary), "--version"],
            check=False,
            timeout=15,
        )
        match = re.search(r"\bversion\s+v?([0-9]+\.[0-9]+\.[0-9]+)\b", result.stdout)
        return match.group(1) if result.returncode == 0 and match else None

    def _write_marker(
        self,
        instance_id: str,
        *,
        existing: dict[str, Any] | None,
        changed: list[str],
    ) -> None:
        artifact = os.environ.get("FORGEJO_ARTIFACT_SHA256") or None
        if artifact is not None and (
            len(artifact) != 64
            or any(character not in "0123456789abcdef" for character in artifact)
        ):
            raise ManagementError(
                78,
                "INVALID_ARTIFACT_DIGEST",
                "Forgejo artifact digest is invalid.",
            )
        installed_at = (
            str(existing["installed_at"])
            if existing is not None
            else utc_now()
        )
        preserve_artifact = (
            artifact is None
            and existing is not None
            and existing["artifact_sha256"] is not None
            and existing["version"] == self.version
            and self.source_root
            == self.paths.product_root.resolve(strict=False)
        )
        if preserve_artifact:
            artifact = str(existing["artifact_sha256"])
            source_revision = str(existing["source_revision"])
        else:
            source_revision = (
                f"artifact-sha256:{artifact}"
                if artifact is not None
                else self._source_revision()
            )
        value = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "instance_id": instance_id,
            "version": self.version,
            "source_revision": source_revision,
            "installed_at": installed_at,
            "install_root": str(self.paths.install_root),
            "lifecycle_entrypoint": str(self.paths.entrypoint),
            "artifact_sha256": artifact,
        }
        content = canonical_json(value) + b"\n"
        if not self._file_matches(self.paths.marker, content, 0o644, 0, 0):
            atomic_write(self.paths.marker, content, mode=0o644)
            changed.append(str(self.paths.marker))

    def _legacy_configuration_valid(self) -> bool:
        try:
            sections = parse_ini(self.paths.app_ini)
        except ManagementError:
            return False
        database = sections.get("database", {})
        server = sections.get("server", {})
        return (
            database.get("DB_TYPE") == "postgres"
            and database.get("HOST") == "127.0.0.1:5432"
            and NAME_RE.fullmatch(database.get("NAME", "")) is not None
            and NAME_RE.fullmatch(database.get("USER", "")) is not None
            and server.get("HTTP_ADDR") == "127.0.0.1"
            and server.get("HTTP_PORT") == str(FIXED_PORT)
            and server.get("ROOT_URL", "").startswith("https://")
            and self._configuration_has_recovery_material()
        )

    def _execute_install(
        self,
        invocation: Invocation,
        configuration: Configuration | None,
        *,
        snapshot_on_change: bool,
    ) -> tuple[list[str], str | None]:
        if configuration is None:
            raise ManagementError(
                70, "INTERNAL_ERROR", "Install configuration is unavailable."
            )
        self._platform_preflight()
        existing, instance_id, adopting = self._collision_preflight(invocation)
        previous_version = (
            str(existing["version"]) if existing is not None else None
        )
        if adopting and not self._legacy_configuration_valid():
            raise ManagementError(
                73,
                "UNSAFE_LEGACY_INSTALLATION",
                "Legacy Forgejo configuration is not safe to adopt.",
            )
        self._port_preflight()
        changed: list[str] = []
        self._install_packages(changed)
        if snapshot_on_change and existing is not None and (
            existing["version"] != self.version
        ):
            self._create_backup("pre-install")
        server_was_active = self._service_active()
        runner_was_active = self._stop_services()
        was_suspended = self.paths.suspended.exists()
        try:
            uid, gid = self._ensure_account(changed)
            self._ensure_layout(uid, gid, changed)
            self._ensure_transaction(instance_id, changed)
            self._ensure_log_ownership(changed)
            self._deploy_product(changed)
            self._install_assets(changed)
            requested_version = configuration.upstream_version
            if adopting and requested_version == "latest":
                requested_version = self._installed_binary_version() or "latest"
            self._install_binary(requested_version, changed)
            database_password = self._configure_database(
                invocation, configuration, changed
            )
            self._write_configuration(
                configuration, database_password, gid, changed
            )
            self._configure_caddy(configuration.host, changed)
            self._migrate_database(gid)
            self._ensure_admin(invocation, configuration, changed)
            self._activate_service(configuration, changed)
            if was_suspended:
                self._enforce_suspension()
            else:
                self._restore_runner(runner_was_active)
            self.paths.retained.unlink(missing_ok=True)
            self._write_marker(
                instance_id, existing=existing, changed=changed
            )
            self.paths.transaction.unlink(missing_ok=True)
            if adopting:
                if self.paths.migration_manifest is None:
                    raise ManagementError(
                        70,
                        "INTERNAL_ERROR",
                        "Migration manifest disappeared during adoption.",
                    )
                self.paths.migration_manifest.unlink(missing_ok=True)
                changed.append(str(self.paths.migration_manifest))
            return changed, previous_version
        except BaseException:
            self._restore_after_failed_mutation(
                server_was_active=server_was_active,
                runner_was_active=runner_was_active,
                was_suspended=was_suspended,
            )
            raise

    def _execute_repair(
        self,
        invocation: Invocation,
        configuration: Configuration | None,
    ) -> tuple[list[str], str | None]:
        self.load_marker(required=True)
        return self._execute_install(
            invocation, configuration, snapshot_on_change=False
        )

    def _backup_destination(self, invocation: Invocation) -> Path:
        value = invocation.inputs.get(
            "backup_destination",
            os.environ.get(
                "FORGEJO_BACKUP_DESTINATION", str(self.paths.backup_root)
            ),
        )
        if not isinstance(value, str):
            raise ManagementError(
                78,
                "INVALID_BACKUP_DESTINATION",
                "Backup destination must be a path.",
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
            if destination != self.paths.backup_root and (
                destination == root or is_relative_to(destination, root)
            ):
                raise ManagementError(
                    78,
                    "INVALID_BACKUP_DESTINATION",
                    "Backup destination must be outside mutable product roots.",
                )
        return destination

    @staticmethod
    def _safe_archive_member(member: tarfile.TarInfo) -> bool:
        path = Path(member.name)
        return (
            not path.is_absolute()
            and ".." not in path.parts
            and member.name.startswith("forgejo-backup/")
            and (member.isdir() or member.isreg())
            and not member.issym()
            and not member.islnk()
            and not member.isdev()
        )

    @staticmethod
    def _assert_backup_tree_safe(path: Path) -> None:
        if not path.exists():
            return
        for candidate in (path, *path.rglob("*")):
            metadata = candidate.lstat()
            if stat.S_ISLNK(metadata.st_mode) or not (
                stat.S_ISDIR(metadata.st_mode)
                or stat.S_ISREG(metadata.st_mode)
            ):
                raise ManagementError(
                    73,
                    "UNSAFE_BACKUP_SOURCE",
                    f"Backup source contains an unsupported object: {candidate}",
                )

    def _create_backup(
        self, label: str, destination: Path | None = None
    ) -> Path:
        marker = self.load_marker(required=True)
        destination = destination or self.paths.backup_root
        existed = destination.exists()
        if destination.is_symlink():
            raise ManagementError(
                73,
                "UNSAFE_BACKUP_DESTINATION",
                "Backup destination is a symlink.",
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
        os.chown(destination, 0, 0)
        os.chmod(destination, 0o700)
        sections = parse_ini(self.paths.app_ini)
        database = sections.get("database", {})
        name = database.get("NAME", "")
        user = database.get("USER", "")
        if not NAME_RE.fullmatch(name) or not NAME_RE.fullmatch(user):
            raise ManagementError(
                65,
                "INVALID_CONFIGURATION",
                "Cannot identify the Forgejo database for backup.",
            )
        for source in (
            self.paths.configuration_root,
            self.paths.state_root,
            self.paths.product_root,
            self.paths.binary,
            self.paths.unit,
            self.paths.entrypoint,
            self.paths.logrotate,
        ):
            self._assert_backup_tree_safe(source)
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        archive = destination / (
            f"forgejo-{label}-{timestamp}-{uuid.uuid4().hex[:8]}.tar.gz"
        )
        temporary = archive.with_name(f".{archive.name}.tmp")
        workspace = Path(
            tempfile.mkdtemp(prefix=".forgejo-backup.", dir=destination)
        )
        dump = workspace / "database.dump"
        try:
            with dump.open("xb") as output:
                self._run_as(
                    "postgres",
                    ["pg_dump", "--format=custom", name],
                    timeout=1800,
                    stdout=output,
                )
            os.chown(dump, 0, 0)
            os.chmod(dump, 0o600)
            record = self._binary_record()
            manifest = {
                "schema_version": 1,
                "product_id": PRODUCT_ID,
                "product_version": marker["version"],
                "instance_id": marker["instance_id"],
                "created_at": utc_now(),
                "database_name": name,
                "database_user": user,
                "binary_version": (
                    record["version"] if record is not None else None
                ),
                "boot": self._service_enabled(),
                "suspended": self.paths.suspended.exists(),
            }
            with tarfile.open(temporary, "x:gz") as bundle:
                manifest_data = canonical_json(manifest) + b"\n"
                info = tarfile.TarInfo("forgejo-backup/manifest.json")
                info.size = len(manifest_data)
                info.mode = 0o600
                info.mtime = int(time.time())
                bundle.addfile(info, fileobj=io.BytesIO(manifest_data))
                bundle.add(
                    dump,
                    arcname="forgejo-backup/database.dump",
                    recursive=False,
                )
                for source, target in (
                    (self.paths.configuration_root, "configuration"),
                    (self.paths.state_root, "state"),
                    (self.paths.product_root, "product"),
                    (self.paths.binary, "runtime/forgejo"),
                    (self.paths.unit, "runtime/forgejo.service"),
                    (self.paths.entrypoint, "runtime/forgejo-manage"),
                    (self.paths.logrotate, "runtime/logrotate"),
                ):
                    if source.exists():
                        bundle.add(
                            source,
                            arcname=f"forgejo-backup/{target}",
                            recursive=True,
                        )
            os.chown(temporary, 0, 0)
            os.chmod(temporary, 0o600)
            with tarfile.open(temporary, "r:gz") as bundle:
                members = bundle.getmembers()
                if not members or not all(
                    self._safe_archive_member(member) for member in members
                ):
                    raise ManagementError(
                        78,
                        "BACKUP_VERIFY_FAILED",
                        "Backup archive contains an unsafe member.",
                    )
            os.replace(temporary, archive)
            digest = sha256_file(archive)
            checksum = archive.with_suffix(archive.suffix + ".sha256")
            atomic_write(
                checksum,
                f"{digest}  {archive.name}\n".encode("ascii"),
                mode=0o600,
            )
            return archive
        finally:
            temporary.unlink(missing_ok=True)
            shutil.rmtree(workspace, ignore_errors=True)

    def _coordinated_backup(
        self, label: str, destination: Path | None = None
    ) -> Path:
        server_was_active = self._service_active()
        runner_was_active = self._stop_services()

        def restore_services() -> None:
            self._run(["systemctl", "start", "forgejo.service"])
            self._wait_healthy()
            self._wait_https_healthy()
            self._restore_runner(runner_was_active)

        try:
            archive = self._create_backup(label, destination)
        except BaseException as backup_error:
            if server_was_active and not self.paths.suspended.exists():
                try:
                    restore_services()
                except BaseException as restore_error:
                    if isinstance(backup_error, ManagementError):
                        backup_error.recovery.extend(
                            [
                                "Forgejo service restoration also failed after "
                                "the backup error.",
                                "Keep Forgejo and its runner stopped; inspect "
                                "their service journals before retrying.",
                            ]
                        )
                    else:
                        backup_error = ManagementError(
                            1,
                            "BACKUP_AND_RESTORE_FAILED",
                            "Backup and Forgejo service restoration both failed.",
                            recovery=[
                                "Keep Forgejo and its runner stopped; inspect "
                                "the PostgreSQL, Forgejo, and Caddy journals.",
                            ],
                        )
                    raise backup_error from restore_error
            raise
        if server_was_active and not self.paths.suspended.exists():
            try:
                restore_services()
            except BaseException as exc:
                raise ManagementError(
                    1,
                    "BACKUP_RESTORE_FAILED",
                    f"Backup completed at {archive}, but Forgejo service "
                    "restoration failed.",
                    recovery=[
                        f"Preserve the completed backup at {archive}.",
                        "Inspect the Forgejo, Caddy, and runner service journals.",
                    ],
                ) from exc
        return archive

    def _snapshot_for_rollback(
        self, archive: Path, marker: dict[str, Any]
    ) -> None:
        self.paths.rollback_root.mkdir(parents=True, exist_ok=True)
        os.chown(self.paths.rollback_root, 0, 0)
        os.chmod(self.paths.rollback_root, 0o700)
        value = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "from_version": marker["version"],
            "archive": str(archive),
            "archive_sha256": sha256_file(archive),
            "created_at": utc_now(),
        }
        atomic_write(
            self.paths.rollback_metadata,
            json.dumps(value, indent=2, sort_keys=True).encode("utf-8")
            + b"\n",
            mode=0o600,
        )

    def _execute_backup(
        self, invocation: Invocation
    ) -> tuple[list[str], str | None, str]:
        marker = self.load_marker(required=True)
        archive = self._coordinated_backup(
            "manual", self._backup_destination(invocation)
        )
        checksum = archive.with_suffix(archive.suffix + ".sha256")
        return [str(archive), str(checksum)], str(marker["version"]), str(
            archive
        )

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
        return tuple(
            int(part) for part in value.split("-", 1)[0].split(".")
        )

    def _execute_update(
        self,
        invocation: Invocation,
        configuration: Configuration | None,
    ) -> tuple[list[str], str | None, str]:
        marker = self.load_marker(required=True)
        if self._version_tuple(self.version) < self._version_tuple(
            str(marker["version"])
        ):
            raise ManagementError(
                78,
                "DOWNGRADE_REQUIRES_ROLLBACK",
                "Update cannot install an older product version.",
            )
        if configuration is None:
            raise ManagementError(
                70, "INTERNAL_ERROR", "Update configuration is unavailable."
            )
        current_binary = self._binary_record()
        if (
            current_binary is not None
            and configuration.upstream_version != "latest"
            and self._version_tuple(configuration.upstream_version)
            < self._version_tuple(str(current_binary["version"]))
        ):
            raise ManagementError(
                78,
                "UPSTREAM_DOWNGRADE_REQUIRES_ROLLBACK",
                "Update cannot install an older Forgejo release.",
            )
        archive = self._coordinated_backup("pre-update")
        self._snapshot_for_rollback(archive, marker)
        changed, previous = self._execute_install(
            invocation, configuration, snapshot_on_change=False
        )
        return changed + [str(archive)], previous, str(archive)

    def _validate_rollback_archive(
        self,
        metadata: dict[str, Any],
        current: dict[str, Any],
    ) -> tuple[Path, dict[str, Any]]:
        expected = {
            "schema_version",
            "product_id",
            "from_version",
            "archive",
            "archive_sha256",
            "created_at",
        }
        if (
            set(metadata) != expected
            or metadata["schema_version"] != 1
            or metadata["product_id"] != PRODUCT_ID
            or not isinstance(metadata["archive"], str)
            or not isinstance(metadata["archive_sha256"], str)
            or len(metadata["archive_sha256"]) != 64
            or any(
                character not in "0123456789abcdef"
                for character in metadata["archive_sha256"]
            )
            or not isinstance(metadata["from_version"], str)
            or not isinstance(metadata["created_at"], str)
            or not metadata["created_at"]
        ):
            raise ManagementError(
                65, "INVALID_ROLLBACK", "Rollback metadata is invalid."
            )
        try:
            validate_version(metadata["from_version"])
        except ManagementError as exc:
            raise ManagementError(
                65,
                "INVALID_ROLLBACK",
                "Rollback metadata version is invalid.",
            ) from exc
        archive = Path(metadata["archive"])
        if (
            not archive.is_absolute()
            or not archive.is_file()
            or archive.is_symlink()
            or sha256_file(archive) != metadata["archive_sha256"]
        ):
            raise ManagementError(
                78,
                "INVALID_ROLLBACK",
                "Rollback backup is missing or has changed.",
            )
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                members = bundle.getmembers()
                if not members or not all(
                    self._safe_archive_member(member) for member in members
                ):
                    raise ManagementError(
                        78,
                        "INVALID_ROLLBACK",
                        "Rollback archive contains an unsafe member.",
                    )
                manifest_file = bundle.extractfile(
                    "forgejo-backup/manifest.json"
                )
                if manifest_file is None:
                    raise ManagementError(
                        78,
                        "INVALID_ROLLBACK",
                        "Rollback manifest is missing.",
                    )
                manifest = json.loads(
                    manifest_file.read(),
                    object_pairs_hook=strict_object,
                )
        except (OSError, tarfile.TarError, json.JSONDecodeError) as exc:
            raise ManagementError(
                78,
                "INVALID_ROLLBACK",
                "Rollback archive cannot be read.",
            ) from exc
        manifest_fields = {
            "schema_version",
            "product_id",
            "product_version",
            "instance_id",
            "created_at",
            "database_name",
            "database_user",
            "binary_version",
            "boot",
            "suspended",
        }
        if (
            not isinstance(manifest, dict)
            or set(manifest) != manifest_fields
            or manifest["schema_version"] != 1
            or manifest["product_id"] != PRODUCT_ID
            or manifest["product_version"] != metadata["from_version"]
            or manifest["instance_id"] != current["instance_id"]
            or not isinstance(manifest["created_at"], str)
            or not manifest["created_at"]
            or not NAME_RE.fullmatch(str(manifest["database_name"]))
            or not NAME_RE.fullmatch(str(manifest["database_user"]))
            or (
                manifest["binary_version"] is not None
                and (
                    not isinstance(manifest["binary_version"], str)
                    or RELEASE_RE.fullmatch(manifest["binary_version"]) is None
                )
            )
            or manifest["boot"] not in {"enabled", "disabled"}
            or not isinstance(manifest["suspended"], bool)
        ):
            raise ManagementError(
                78,
                "INVALID_ROLLBACK",
                "Rollback manifest is invalid.",
            )
        return archive, manifest

    @staticmethod
    def _remove_owned_tree(path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISDIR(
            metadata.st_mode
        ):
            raise ManagementError(
                73,
                "UNSAFE_REMOVAL",
                f"Refusing to remove unsafe directory: {path}",
            )
        shutil.rmtree(path)

    @staticmethod
    def _remove_owned_file(path: Path) -> None:
        try:
            metadata = path.lstat()
        except FileNotFoundError:
            return
        if (
            stat.S_ISLNK(metadata.st_mode)
            or not stat.S_ISREG(metadata.st_mode)
            or metadata.st_uid != 0
        ):
            raise ManagementError(
                73,
                "UNSAFE_REMOVAL",
                f"Refusing to remove unsafe file: {path}",
            )
        path.unlink()

    def _restore_database(
        self, extracted: Path, configuration_path: Path
    ) -> None:
        sections = parse_ini(configuration_path)
        database = sections.get("database", {})
        name = database.get("NAME", "")
        user = database.get("USER", "")
        credential = database.get("PASSWD", "")
        if (
            not NAME_RE.fullmatch(name)
            or not NAME_RE.fullmatch(user)
            or not self._password_safe_for_ini(credential)
        ):
            raise ManagementError(
                78,
                "INVALID_ROLLBACK",
                "Rollback database configuration is invalid.",
            )
        escaped = credential.replace("'", "''")
        sql = (
            "DO $$\n"
            "BEGIN\n"
            f"  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{user}') THEN\n"
            f'    CREATE ROLE "{user}" LOGIN PASSWORD \'{escaped}\';\n'
            "  ELSE\n"
            f'    ALTER ROLE "{user}" WITH LOGIN PASSWORD \'{escaped}\';\n'
            "  END IF;\n"
            "END\n"
            "$$;\n"
        )
        self._run_as(
            "postgres",
            ["psql", "-v", "ON_ERROR_STOP=1"],
            input_text=sql,
        )
        self._run_as(
            "postgres", ["dropdb", "--if-exists", "--force", name]
        )
        self._run_as("postgres", ["createdb", "-O", user, name])
        with (extracted / "database.dump").open("rb") as source:
            self._run_as(
                "postgres",
                [
                    "pg_restore",
                    "--exit-on-error",
                    "--no-owner",
                    "--role",
                    user,
                    "--dbname",
                    name,
                ],
                timeout=1800,
                stdin=source,
            )

    def _execute_rollback(self) -> tuple[list[str], str | None]:
        current = self.load_marker(required=True)
        if not self.paths.rollback_metadata.is_file():
            raise ManagementError(
                66,
                "ROLLBACK_MISSING",
                "No Forgejo rollback snapshot is available.",
            )
        rollback_metadata = self.paths.rollback_metadata.lstat()
        if (
            not stat.S_ISREG(rollback_metadata.st_mode)
            or stat.S_ISLNK(rollback_metadata.st_mode)
            or rollback_metadata.st_uid != 0
            or rollback_metadata.st_gid != 0
            or stat.S_IMODE(rollback_metadata.st_mode) != 0o600
        ):
            raise ManagementError(
                73,
                "UNSAFE_ROLLBACK",
                "Rollback metadata ownership is invalid.",
            )
        metadata = read_json(self.paths.rollback_metadata)
        archive, manifest = self._validate_rollback_archive(metadata, current)
        pre_rollback = self._coordinated_backup("pre-rollback")
        runner_was_active = self._stop_services()
        workspace = Path(
            tempfile.mkdtemp(prefix=".forgejo-rollback.", dir="/var/tmp")
        )
        os.chmod(workspace, 0o700)
        try:
            with tarfile.open(archive, "r:gz") as bundle:
                bundle.extractall(workspace)
            extracted = workspace / "forgejo-backup"
            required = (
                extracted / "configuration" / "app.ini",
                extracted / "state" / "installation.json",
                extracted / "product" / "PRODUCT.json",
                extracted / "runtime" / "forgejo",
                extracted / "database.dump",
            )
            if not all(path.exists() for path in required):
                raise ManagementError(
                    78,
                    "INVALID_ROLLBACK",
                    "Rollback archive is incomplete.",
                )
            self._restore_database(
                extracted, extracted / "configuration" / "app.ini"
            )
            for destination in (
                self.paths.configuration_root,
                self.paths.state_root,
                self.paths.product_root,
            ):
                self._remove_owned_tree(destination)
            self.paths.install_root.mkdir(parents=True, exist_ok=True)
            shutil.copytree(
                extracted / "configuration",
                self.paths.configuration_root,
                copy_function=shutil.copy2,
            )
            shutil.copytree(
                extracted / "state",
                self.paths.state_root,
                copy_function=shutil.copy2,
            )
            shutil.copytree(
                extracted / "product",
                self.paths.product_root,
                copy_function=shutil.copy2,
            )
            self._protect_tree(self.paths.product_root)
            atomic_write(
                self.paths.binary,
                (extracted / "runtime" / "forgejo").read_bytes(),
                mode=0o755,
            )
            changed = [
                str(self.paths.configuration_root),
                str(self.paths.state_root),
                str(self.paths.product_root),
                str(self.paths.binary),
            ]
            self._install_assets(changed)
            gid = grp.getgrnam("git").gr_gid
            uid = pwd.getpwnam("git").pw_uid
            for path in self.paths.state_root.rglob("*"):
                os.chown(path, uid, gid)
            os.chown(self.paths.state_root, uid, gid)
            for path, mode in (
                (self.paths.marker, 0o644),
                (self.paths.suspended, 0o600),
                (self.paths.retained, 0o600),
            ):
                if path.is_file():
                    os.chown(path, 0, 0)
                    os.chmod(path, mode)
            self.paths.transaction.unlink(missing_ok=True)
            os.chown(self.paths.configuration_root, 0, gid)
            os.chmod(self.paths.configuration_root, 0o750)
            os.chown(self.paths.app_ini, 0, gid)
            os.chmod(self.paths.app_ini, 0o640)
            public = self._existing_public_config()
            if public is None or not HOST_RE.fullmatch(public["host"]):
                raise ManagementError(
                    78,
                    "INVALID_ROLLBACK",
                    "Rollback public URL is invalid.",
                )
            self._configure_caddy(public["host"], changed)
            self._run(["systemctl", "daemon-reload"])
            if manifest["boot"] == "enabled":
                self._run(["systemctl", "enable", "forgejo.service"])
            else:
                self._run(
                    ["systemctl", "disable", "forgejo.service"], check=False
                )
            if manifest["suspended"]:
                self._run(
                    ["systemctl", "stop", "forgejo.service"], check=False
                )
            else:
                self._run(["systemctl", "start", "forgejo.service"])
                self._wait_healthy()
                self._configure_network_services(changed)
                self._export_local_ca(changed)
                self._wait_https_healthy()
                self._restore_runner(runner_was_active)
            self.load_marker(required=True)
            self._snapshot_for_rollback(pre_rollback, current)
            return changed + [str(pre_rollback)], str(current["version"])
        finally:
            shutil.rmtree(workspace, ignore_errors=True)

    def _load_suspension(self) -> dict[str, Any]:
        try:
            metadata = self.paths.suspended.lstat()
        except OSError as exc:
            raise ManagementError(
                66,
                "SUSPENSION_MISSING",
                "Forgejo suspension metadata is missing.",
            ) from exc
        if (
            not stat.S_ISREG(metadata.st_mode)
            or stat.S_ISLNK(metadata.st_mode)
            or metadata.st_uid != 0
            or metadata.st_gid != 0
            or stat.S_IMODE(metadata.st_mode) != 0o600
        ):
            raise ManagementError(
                73,
                "UNSAFE_SUSPENSION",
                "Forgejo suspension metadata ownership is invalid.",
            )
        value = read_json(self.paths.suspended)
        expected = {
            "schema_version",
            "product_id",
            "suspended_at",
            "server_was_active",
            "runner_was_active",
            "boot",
            "runner_boot",
        }
        if (
            set(value) != expected
            or value["schema_version"] != 1
            or value["product_id"] != PRODUCT_ID
            or not isinstance(value["suspended_at"], str)
            or not value["suspended_at"]
            or not isinstance(value["server_was_active"], bool)
            or not isinstance(value["runner_was_active"], bool)
            or value["runner_was_active"] and not value["server_was_active"]
            or value["boot"] not in {"enabled", "disabled"}
            or value["runner_boot"] not in {"enabled", "disabled"}
        ):
            raise ManagementError(
                65,
                "INVALID_SUSPENSION",
                "Forgejo suspension metadata is invalid.",
            )
        return value

    def _execute_suspend(self) -> tuple[list[str], str | None]:
        marker = self.load_marker(required=True)
        if self.paths.retained.exists():
            raise ManagementError(
                69,
                "RUNTIME_RETAINED",
                "A retained Forgejo installation cannot be suspended.",
            )
        if self.paths.suspended.exists():
            self._load_suspension()
            changed: list[str] = []
            if self._runner_active() or self._service_active():
                self._stop_services()
                changed.append("forgejo.service:stopped")
            if self._service_enabled() == "enabled":
                self._run(
                    ["systemctl", "disable", "forgejo.service"],
                    check=False,
                )
                changed.append("forgejo.service:disabled")
            if (
                self._runner_present()
                and self._service_enabled_named("forgejo-runner.service")
                == "enabled"
            ):
                self._run(
                    ["systemctl", "disable", "forgejo-runner.service"],
                    check=False,
                )
                changed.append("forgejo-runner.service:disabled")
            return changed, str(marker["version"])
        server_was_active = self._service_active()
        runner_was_active = self._runner_active()
        if runner_was_active and not server_was_active:
            raise ManagementError(
                73,
                "RUNNER_DEPENDENCY_INVALID",
                "The active Forgejo runner has no active Forgejo dependency.",
            )
        runner_present = self._runner_present()
        boot = (
            "enabled" if self._service_enabled() == "enabled" else "disabled"
        )
        runner_boot = (
            "enabled"
            if runner_present
            and self._service_enabled_named("forgejo-runner.service") == "enabled"
            else "disabled"
        )
        self._stop_services()
        self._run(
            ["systemctl", "disable", "forgejo.service"], check=False
        )
        if runner_present:
            self._run(
                ["systemctl", "disable", "forgejo-runner.service"],
                check=False,
            )
        value = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "suspended_at": utc_now(),
            "server_was_active": server_was_active,
            "runner_was_active": runner_was_active,
            "boot": boot,
            "runner_boot": runner_boot,
        }
        atomic_write(
            self.paths.suspended,
            canonical_json(value) + b"\n",
            mode=0o600,
        )
        return [str(self.paths.suspended), "forgejo.service:stopped"], str(
            marker["version"]
        )

    def _execute_resume(self) -> tuple[list[str], str | None]:
        marker = self.load_marker(required=True)
        if (
            not self.paths.suspended.exists()
            and not self.paths.suspended.is_symlink()
        ):
            return [], str(marker["version"])
        value = self._load_suspension()
        failures = [
            check
            for check in self.verify_checks(probe=False)
            if check["status"] == "fail"
        ]
        if failures:
            raise ManagementError(
                78,
                "BOUNDARY_CHECK_FAILED",
                f"Cannot resume Forgejo: {failures[0]['id']}.",
            )
        runner_present = self._runner_present()
        if value["runner_was_active"] and not runner_present:
            raise ManagementError(
                66,
                "DEPENDENT_RUNNER_MISSING",
                "The previously active Forgejo runner is missing.",
            )
        try:
            if value["boot"] == "enabled":
                self._run(["systemctl", "enable", "forgejo.service"])
            else:
                self._run(
                    ["systemctl", "disable", "forgejo.service"],
                    check=False,
                )
            if runner_present:
                runner_action = (
                    "enable"
                    if value["runner_boot"] == "enabled"
                    else "disable"
                )
                self._run(
                    [
                        "systemctl",
                        runner_action,
                        "forgejo-runner.service",
                    ],
                    check=runner_action == "enable",
                )
            if value["server_was_active"]:
                self._run(["systemctl", "start", "forgejo.service"])
                self._wait_healthy()
                self._wait_https_healthy()
            if value["runner_was_active"]:
                self._restore_runner(True)
        except BaseException:
            self._stop_services()
            self._run(
                ["systemctl", "disable", "forgejo.service"],
                check=False,
            )
            if runner_present:
                self._run(
                    ["systemctl", "disable", "forgejo-runner.service"],
                    check=False,
                )
            raise
        self.paths.suspended.unlink()
        return [str(self.paths.suspended), "forgejo.service:restored"], str(
            marker["version"]
        )

    def _remove_caddy_route(self, changed: list[str]) -> None:
        if self.paths.caddyfile.is_symlink():
            raise ManagementError(
                73,
                "CADDY_OWNERSHIP_AMBIGUOUS",
                "The shared Caddyfile must not be a symlink.",
            )
        if self.paths.caddyfile.is_file():
            current = self.paths.caddyfile.read_text(encoding="utf-8")
            content = self._without_managed_caddy_blocks(current)
            rendered = (content + ("\n" if content else "")).encode("utf-8")
            if not self._file_matches(
                self.paths.caddyfile, rendered, 0o644, 0, 0
            ):
                atomic_write(self.paths.caddyfile, rendered, mode=0o644)
                changed.append(str(self.paths.caddyfile))
        if self.paths.legacy_caddy.exists() or self.paths.legacy_caddy.is_symlink():
            self._remove_owned_file(self.paths.legacy_caddy)
            changed.append(str(self.paths.legacy_caddy))
        if self._service_active_named("caddy.service"):
            self._run(
                ["systemctl", "reload-or-restart", "caddy.service"],
                check=False,
            )

    def _drop_database(self) -> list[str]:
        if not self.paths.app_ini.is_file():
            raise ManagementError(
                73,
                "UNSAFE_DATABASE_REMOVAL",
                "Cannot purge Forgejo without its protected database configuration.",
            )
        sections = parse_ini(self.paths.app_ini)
        database = sections.get("database", {})
        name = database.get("NAME", "")
        user = database.get("USER", "")
        if not NAME_RE.fullmatch(name) or not NAME_RE.fullmatch(user):
            raise ManagementError(
                73,
                "UNSAFE_DATABASE_REMOVAL",
                "Cannot safely identify the Forgejo database and role.",
            )
        self._run_as(
            "postgres",
            ["dropdb", "--if-exists", "--force", name],
            timeout=180,
        )
        self._run_as(
            "postgres", ["dropuser", "--if-exists", user], timeout=60
        )
        return [f"postgresql-database:{name}", f"postgresql-role:{user}"]

    def _execute_uninstall(
        self, invocation: Invocation
    ) -> tuple[list[str], str | None]:
        marker = self.load_marker()
        legacy = marker is None and self._legacy_installation_valid()
        if marker is None and not legacy:
            raise ManagementError(
                73,
                "OWNERSHIP_REQUIRED",
                "Forgejo lacks a valid product or legacy ownership marker.",
            )
        if self._runner_present():
            raise ManagementError(
                69,
                "DEPENDENT_RUNNER_INSTALLED",
                "Remove forgejo-runner before uninstalling Forgejo.",
                recovery=[
                    "Run the root compatibility uninstaller for forgejo-runner first."
                ],
            )
        previous = str(marker["version"]) if marker is not None else None
        changed: list[str] = []
        if legacy:
            self._write_marker(
                str(uuid.uuid4()),
                existing=None,
                changed=changed,
            )
            marker = self.load_marker(required=True)
            previous = str(marker["version"])
            self._ensure_directory(
                self.paths.log_root,
                0o750,
                0,
                0,
                changed,
            )
            self._ensure_log_ownership(changed)
        self._stop_services()
        self._run(
            ["systemctl", "disable", "forgejo.service"], check=False
        )
        purge = invocation.retain_state is False
        if purge:
            changed.extend(self._drop_database())
        self._remove_caddy_route(changed)
        for path in (
            self.paths.avahi_service,
            self.paths.unit,
            self.paths.logrotate,
            self.paths.entrypoint,
            self.paths.binary,
            self.paths.trusted_ca,
        ):
            if path.exists() or path.is_symlink():
                self._remove_owned_file(path)
                changed.append(str(path))
        self._run(["systemctl", "daemon-reload"], check=False)
        if self.paths.trusted_ca.exists() is False:
            self._run(["update-ca-certificates"], check=False, timeout=120)
        if self._service_active_named("avahi-daemon.service"):
            self._run(
                ["systemctl", "reload-or-restart", "avahi-daemon.service"],
                check=False,
            )
        for path in (self.paths.install_root, self.paths.cache_root):
            if path.exists() or path.is_symlink():
                self._remove_owned_tree(path)
                changed.append(str(path))
        if purge:
            for path in (
                self.paths.configuration_root,
                self.paths.state_root,
                self.paths.backup_root,
            ):
                if path.exists() or path.is_symlink():
                    self._remove_owned_tree(path)
                    changed.append(str(path))
            try:
                pwd.getpwnam("git")
            except KeyError:
                pass
            else:
                result = self._run(["userdel", "git"], check=False)
                if result.returncode != 0:
                    raise ManagementError(
                        73,
                        "ACCOUNT_REMOVAL_FAILED",
                        "Could not remove the git service account.",
                    )
                changed.append("account:git")
        else:
            content = canonical_json(
                {
                    "schema_version": 1,
                    "product_id": PRODUCT_ID,
                    "retained_at": utc_now(),
                }
            ) + b"\n"
            atomic_write(self.paths.retained, content, mode=0o600)
            for path in (
                self.paths.descriptor,
                self.paths.binary_metadata,
                self.paths.exported_ca,
            ):
                if path.exists() or path.is_symlink():
                    self._remove_owned_file(path)
            changed.append(str(self.paths.retained))
        if self.paths.migration_manifest is not None:
            self.paths.migration_manifest.unlink(missing_ok=True)
        return changed, previous

    def _write_receipt(
        self,
        result: Result,
        *,
        previous_version: str | None,
        changed_resources: list[str],
        event_id: str,
    ) -> dict[str, str]:
        try:
            gid = grp.getgrnam("git").gr_gid
        except KeyError:
            gid = 0
        self._ensure_directory(self.paths.log_root, 0o750, 0, 0, [])
        self._ensure_directory(self.paths.receipts, 0o700, 0, 0, [])
        marker = self.load_marker()
        value = {
            "schema_version": 1,
            "response": result.object(),
            "installed_version": (
                marker["version"] if marker is not None else None
            ),
            "previous_version": previous_version,
            "changed_resources": sorted(set(changed_resources)),
            "audit_event_id": event_id,
        }
        content = canonical_json(value) + b"\n"
        historical = self.paths.receipts / f"{result.correlation_id}.json"
        atomic_write(historical, content, mode=0o640, gid=gid)
        atomic_write(self.paths.receipt, content, mode=0o640, gid=gid)
        return {
            "path": str(self.paths.receipt),
            "digest": sha256_bytes(content),
        }

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
            gid = grp.getgrnam("git").gr_gid
        except KeyError:
            gid = 0
        event = {
            "timestamp": utc_now(),
            "event_id": event_id,
            "correlation_id": invocation.correlation_id,
            "product_id": PRODUCT_ID,
            "instance_id": instance_id,
            "operation": invocation.operation,
            "phase": operation_phase(
                invocation.operation, dry_run=invocation.dry_run
            ),
            "actor": invocation.actor,
            "decision": (
                "denied" if result_status == "blocked" else "allowed"
            ),
            "result": result_status,
            "changed": changed,
            "receipt_digest": receipt_digest,
        }
        self.paths.audit.parent.mkdir(parents=True, exist_ok=True)
        descriptor = os.open(
            self.paths.audit,
            os.O_WRONLY
            | os.O_APPEND
            | os.O_CREAT
            | getattr(os, "O_NOFOLLOW", 0),
            0o640,
        )
        try:
            metadata = os.fstat(descriptor)
            if not stat.S_ISREG(metadata.st_mode):
                raise ManagementError(
                    73, "UNSAFE_AUDIT", "Audit path is not a regular file."
                )
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            os.fchmod(descriptor, 0o640)
            os.fchown(descriptor, 0, gid)
            os.write(descriptor, canonical_json(event) + b"\n")
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def audit_failure(
        self, invocation: Invocation, error: Exception
    ) -> None:
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


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
        prog="forgejo-manage",
        description="Install and manage a private Forgejo server.",
    )
    value.add_argument("operation", choices=OPERATIONS, help="lifecycle operation")
    value.add_argument(
        "--dry-run",
        action="store_true",
        help="render a plan without making changes",
    )
    value.add_argument(
        "--json",
        action="store_true",
        help="write one machine-readable response object",
    )
    value.add_argument(
        "--non-interactive",
        action="store_true",
        help="never prompt; missing approval exits 64",
    )
    value.add_argument(
        "--request-file",
        type=Path,
        help="read a root-owned lifecycle request",
    )
    value.add_argument("--correlation-id", help="use the supplied request UUID")
    value.add_argument(
        "--plan-digest",
        help="require the current plan to match this digest",
    )
    value.add_argument(
        "--yes",
        action="store_true",
        help="approve a non-destructive plan without prompting",
    )
    value.add_argument(
        "--purge",
        action="store_true",
        help="delete retained state during uninstall",
    )
    value.add_argument(
        "--confirmation",
        help="supply an exact destructive or migration confirmation",
    )
    return value


def print_plan(
    result: Result,
    *,
    configuration: dict[str, Any] | None,
    file: Any = None,
) -> None:
    def field(label: str, value: Any) -> None:
        print(f"  {label + ':':<18}{value}", file=file)

    print("Forgejo product lifecycle plan:", file=file)
    field("Operation", result.operation)
    if configuration is not None:
        field("Public URL", configuration["root_url"])
        field(
            "Administrator",
            f"{configuration['admin_user']} ({configuration['admin_email']})",
        )
        field(
            "PostgreSQL",
            f"{configuration['database_name']} "
            f"(role {configuration['database_user']})",
        )
        field("Forgejo version", configuration["upstream_version"])
        field("Start at boot", configuration["boot"])
    field("Backend", "http://127.0.0.1:3000 (loopback only)")
    field("State", "/var/lib/forgejo")
    field("Digest", result.plan_digest)
    for index, step in enumerate(result.steps, 1):
        print(f"  {index}. {step['summary']}", file=file)
    if result.operation == "install":
        print(
            "  Generated credentials, when needed: "
            "/etc/forgejo/bootstrap-admin-password",
            file=file,
        )


def print_result(result: Result, *, as_json: bool) -> None:
    if as_json:
        print(
            json.dumps(
                result.object(), sort_keys=True, separators=(",", ":")
            )
        )
        return
    if result.phase == "plan":
        configuration = None
        if result.details is not None:
            candidate = result.details.get("configuration")
            if isinstance(candidate, dict):
                configuration = candidate
        print_plan(result, configuration=configuration)
        return
    print(f"Forgejo {result.operation}: {result.status}")
    configuration = None
    if result.details is not None:
        candidate = result.details.get("configuration")
        if isinstance(candidate, dict):
            configuration = candidate
    if configuration is not None:
        print(f"URL: {configuration['root_url']}")
        print(f"Administrator: {configuration['admin_user']}")
        if result.operation == "install":
            print(
                "Generated initial credentials (when applicable): "
                "/etc/forgejo/bootstrap-admin-password"
            )
    if result.details is not None and result.details.get("lifecycle"):
        print(f"Lifecycle: {result.details['lifecycle']}")
    for check in result.checks:
        glyph = (
            "[ok]"
            if check["status"] == "pass"
            else "[!]"
            if check["status"] == "warn"
            else "[x]"
        )
        print(f"{glyph} {check['summary']}")
    for error in result.errors:
        print(f"[x] {error['message']}", file=sys.stderr)


def failure_result(
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
        status = (
            "blocked"
            if exit_code in {64, 65, 66, 69, 73, 75, 78}
            else "failed"
        )
    else:
        exit_code = 1
        code = "OPERATION_FAILED"
        message = "The Forgejo lifecycle operation failed unexpectedly."
        retryable = False
        recovery = [
            "Inspect /var/log/forgejo/audit.log and the service journals."
        ]
        status = "failed"
    result = Result(
        invocation.operation,
        invocation.correlation_id,
        manager.version,
        manager.instance_id(),
        operation_phase(invocation.operation, dry_run=invocation.dry_run),
        status=status,
        errors=[
            {"code": code, "message": message, "retryable": retryable}
        ],
        recovery=recovery,
    )
    manager.audit_failure(invocation, error)
    return result, exit_code


def main(argv: list[str] | None = None) -> int:
    """Run the Forgejo lifecycle CLI."""
    arguments = parser().parse_args(argv)
    source_root = Path(
        os.environ.get(
            "FORGEJO_SOURCE_ROOT", Path(__file__).resolve().parents[3]
        )
    )
    try:
        manager = Manager(source_root)
    except ManagementError as exc:
        print(f"forgejo-manage: {exc.message}", file=sys.stderr)
        return exc.exit_code
    try:
        invocation = manager.invocation(arguments)
    except ManagementError as exc:
        correlation = arguments.correlation_id or str(uuid.uuid4())
        try:
            validate_uuid(correlation, label="correlation_id")
        except ManagementError:
            correlation = str(uuid.uuid4())
        invocation = Invocation(
            arguments.operation,
            correlation,
            "operator",
            {},
            None,
            None,
            arguments.dry_run,
            arguments.json,
            arguments.non_interactive,
            arguments.yes,
            arguments.plan_digest,
        )
        result, exit_code = failure_result(manager, invocation, exc)
        print_result(result, as_json=arguments.json)
        return exit_code
    try:
        result, exit_code = manager.run(invocation)
    except Exception as exc:
        result, exit_code = failure_result(manager, invocation, exc)
    print_result(result, as_json=invocation.json_output)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
