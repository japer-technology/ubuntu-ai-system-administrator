"""Root-only lifecycle implementation shared by source and installed entrypoints."""

from __future__ import annotations

import argparse
import fcntl
import getpass
import grp
import hashlib
import http.client
import json
import os
import platform
import pwd
import secrets
import shutil
import socket
import stat
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import venv
from contextlib import contextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

from .audit import redact
from .auth import MAX_PASSWORD_BYTES, hash_password, new_signing_key
from .database import Database
from .errors import FriendError, ValidationError
from .model import ModelClient, validate_model_base_url, validate_model_id
from .workspace import validate_nominated_root

PRODUCT_ID = "imaginary-friend"
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
KNOWN_ENV = {
    "FRIEND_NONINTERACTIVE",
    "FRIEND_OWNER_USER",
    "FRIEND_OWNER_PASSWORD_FILE",
    "FRIEND_MODEL_BASE_URL",
    "FRIEND_MODEL",
    "FRIEND_WORKSPACES_FILE",
    "FRIEND_HISTORY_RETENTION_DAYS",
    "FRIEND_AUDIT_RETENTION_DAYS",
}
CONFIGURATION_INPUT_KEYS = {
    "owner_user",
    "owner_password_file",
    "model_base_url",
    "model",
    "workspaces_file",
    "history_retention_days",
    "audit_retention_days",
}
OPERATION_INPUT_KEYS = {
    "describe": set(),
    "status": set(),
    "install": CONFIGURATION_INPUT_KEYS,
    "verify": set(),
    "doctor": set(),
    "repair": CONFIGURATION_INPUT_KEYS,
    "backup": {"backup_destination"},
    "update": CONFIGURATION_INPUT_KEYS,
    "rollback": set(),
    "suspend": set(),
    "resume": set(),
    "uninstall": set(),
}
CONFIGURATION_OPERATIONS = {"install", "repair", "update"}
SECRET_INPUTS = {"owner_password_file"}
DEFAULT_MODEL_BASE_URL = "http://127.0.0.1:8080/v1"
DEFAULT_WORKSPACE = Path("/srv/imaginary-friend/workspace")
DELETE_CONFIRMATION = "DELETE IMAGINARY FRIEND STATE"
VERSION_PATTERN_PARTS = 6


def _operation_phase(operation: str, *, dry_run: bool) -> str:
    if dry_run and operation in MUTATING:
        return "plan"
    if operation in READ_ONLY:
        return "read"
    return "execute"


@dataclass(frozen=True)
class Paths:
    install_root: Path = Path("/opt/imaginary-friend")
    configuration_root: Path = Path("/etc/imaginary-friend")
    state_root: Path = Path("/var/lib/imaginary-friend")
    log_root: Path = Path("/var/log/imaginary-friend")
    workspace_parent: Path = Path("/srv/imaginary-friend")
    unit: Path = Path("/etc/systemd/system/imaginary-friend-chat.service")
    logrotate: Path = Path("/etc/logrotate.d/imaginary-friend")
    entrypoint: Path = Path("/usr/local/sbin/friend-manage")
    diagnostics: Path = Path("/usr/local/bin/friend-diagnostics")
    lock: Path = Path("/run/lock/imaginary-friend.lock")
    rollback_root: Path = Path("/opt/.imaginary-friend-rollback")

    @property
    def marker(self) -> Path:
        return self.state_root / "installation.json"

    @property
    def transaction(self) -> Path:
        return self.state_root / ".installing.json"

    @property
    def database(self) -> Path:
        return self.state_root / "friend.db"

    @property
    def recovery(self) -> Path:
        return self.state_root / "recovery"

    @property
    def operation_recovery(self) -> Path:
        return self.state_root / ".operation-recovery"

    @property
    def audit(self) -> Path:
        return self.log_root / "audit.log"

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
    generated_password: str | None = None
    password: str | None = None
    workspaces: list[Path] = field(default_factory=list)
    request_supplied: bool = False


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
    checks: list[dict[str, Any]] = field(default_factory=list)
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
            value["details"] = {"imaginary_friend": redact(self.details)}
        return value


class ManagementError(Exception):
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


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def canonical_json(value: Any) -> bytes:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    value: dict[str, Any] = {}
    for key, item in pairs:
        if key in value:
            raise ManagementError(65, "DUPLICATE_KEY", f"Duplicate JSON key: {key}")
        value[key] = item
    return value


def read_json(path: Path) -> dict[str, Any]:
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
        len(parts) != VERSION_PATTERN_PARTS
        or any(len(part) not in {2, 4} for part in parts)
        or len(parts[0]) != 4
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
    except Exception:
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


def check_secure_file(path: Path, *, missing_code: int = 66) -> os.stat_result:
    try:
        details = path.lstat()
    except FileNotFoundError as exc:
        raise ManagementError(
            missing_code, "INPUT_FILE_MISSING", f"Required file does not exist: {path}"
        ) from exc
    if (
        not stat.S_ISREG(details.st_mode)
        or details.st_nlink != 1
        or details.st_uid != 0
        or stat.S_IMODE(details.st_mode) & 0o077
    ):
        raise ManagementError(
            65,
            "UNSAFE_INPUT_FILE",
            f"Input file must be root-owned, regular, non-symlink, and mode 0600: {path}",
        )
    return details


def read_secret_file(path: Path) -> str:
    details = check_secure_file(path)
    if details.st_size > MAX_PASSWORD_BYTES + 2:
        raise ManagementError(65, "INVALID_SECRET", "Owner password file is too large.")
    try:
        value = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise ManagementError(65, "INVALID_SECRET", "Owner password file is unreadable.") from exc
    if value.endswith("\n"):
        value = value[:-1]
    return validate_owner_password(value)


def validate_owner_password(value: str) -> str:
    if "\r" in value or "\n" in value:
        raise ManagementError(
            65, "INVALID_SECRET", "Owner password must contain exactly one line."
        )
    try:
        encoded = value.encode("utf-8")
    except UnicodeEncodeError as exc:
        raise ManagementError(
            65, "INVALID_SECRET", "Owner password must be valid UTF-8."
        ) from exc
    if len(encoded) > MAX_PASSWORD_BYTES:
        raise ManagementError(65, "INVALID_SECRET", "Owner password file is too large.")
    if len(value) < 12:
        raise ManagementError(
            65, "INVALID_SECRET", "Owner password must be at least 12 characters."
        )
    return value


class Manager:
    def __init__(self, source_root: Path, paths: Paths = Paths()) -> None:
        self.source_root = source_root
        self.paths = paths
        self._transient_runtime: Path | None = None
        self._rollback_switch_active = False
        self.descriptor_path = source_root / "PRODUCT.json"
        self.version_path = source_root / "VERSION"
        self.descriptor = read_json(self.descriptor_path)
        self._validate_descriptor()
        try:
            self.version = validate_version(
                self.version_path.read_text(encoding="utf-8").strip()
            )
        except OSError as exc:
            raise ManagementError(66, "VERSION_MISSING", "Product VERSION is missing.") from exc

    def _validate_descriptor(self) -> None:
        exact = {
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
        if set(self.descriptor) != exact:
            raise ManagementError(
                78, "INVALID_DESCRIPTOR", "PRODUCT.json fields do not match schema v1."
            )
        expected = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "source_root": "products/imaginary-friend",
            "version_file": "VERSION",
            "lifecycle_script": "scripts/manage.sh",
            "installed_entrypoint": str(self.paths.entrypoint),
            "install_root": str(self.paths.install_root),
            "configuration_root": str(self.paths.configuration_root),
            "state_root": str(self.paths.state_root),
            "log_root": str(self.paths.log_root),
            "ownership_marker": str(self.paths.marker),
            "environment_prefix": "FRIEND",
            "operations": list(OPERATIONS),
        }
        for key, value in expected.items():
            if self.descriptor.get(key) != value:
                raise ManagementError(
                    78, "INVALID_DESCRIPTOR", f"PRODUCT.json has invalid {key}."
                )
        if self.descriptor.get("cookie_names") != ["imaginary_friend_session"]:
            raise ManagementError(
                78, "INVALID_DESCRIPTOR", "Friend cookie namespace is invalid."
            )
        if self.descriptor.get("ports") != [
            {"address": "127.0.0.1", "port": 6767, "protocol": "tcp"}
        ]:
            raise ManagementError(
                78, "INVALID_DESCRIPTOR", "Friend listener namespace is invalid."
            )

    def source_asset(self, relative: str) -> Path:
        payload = self.source_root / "payload" / relative
        if payload.exists():
            return payload
        installed = self.source_root / relative
        if installed.exists():
            return installed
        raise ManagementError(
            66, "SOURCE_ASSET_MISSING", f"Product source asset is missing: {relative}"
        )

    def _request(self, path: Path, operation: str) -> dict[str, Any]:
        check_secure_file(path)
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
        missing = required - value.keys()
        unknown = value.keys() - allowed
        if missing or unknown:
            raise ManagementError(
                65,
                "INVALID_REQUEST",
                f"Request fields invalid; missing={sorted(missing)}, unknown={sorted(unknown)}.",
            )
        if value["schema_version"] != 1 or value["product_id"] != PRODUCT_ID:
            raise ManagementError(65, "REQUEST_MISMATCH", "Request product identity is invalid.")
        if value["operation"] != operation:
            raise ManagementError(65, "REQUEST_MISMATCH", "Request operation does not match.")
        validate_uuid(value["correlation_id"], label="request correlation_id")
        if value["requested_by"] != "operator":
            raise ManagementError(65, "INVALID_REQUEST", "requested_by is invalid.")
        if not isinstance(value["inputs"], dict):
            raise ManagementError(65, "INVALID_REQUEST", "Request inputs must be an object.")
        input_unknown = set(value["inputs"]) - OPERATION_INPUT_KEYS[operation]
        if input_unknown:
            raise ManagementError(
                65,
                "UNKNOWN_INPUT",
                f"Input is not accepted for {operation}: {sorted(input_unknown)[0]}",
            )
        if not all(isinstance(key, str) for key in value["inputs"]):
            raise ManagementError(65, "INVALID_REQUEST", "Input keys must be strings.")
        if value["confirmation"] is not None and not isinstance(
            value["confirmation"], str
        ):
            raise ManagementError(65, "INVALID_REQUEST", "confirmation is invalid.")
        if operation == "uninstall":
            if not isinstance(value.get("retain_state"), bool):
                raise ManagementError(
                    65, "INVALID_REQUEST", "Uninstall requires boolean retain_state."
                )
        elif "retain_state" in value:
            raise ManagementError(
                65, "INVALID_REQUEST", "retain_state is valid only for uninstall."
            )
        return value

    @staticmethod
    def _environment_inputs() -> dict[str, Any]:
        unknown = sorted(
            key for key in os.environ if key.startswith("FRIEND_") and key not in KNOWN_ENV
        )
        if unknown:
            raise ManagementError(
                65, "UNKNOWN_INPUT", f"Unknown FRIEND_* input: {unknown[0]}"
            )
        mapping = {
            "FRIEND_OWNER_USER": "owner_user",
            "FRIEND_OWNER_PASSWORD_FILE": "owner_password_file",
            "FRIEND_MODEL_BASE_URL": "model_base_url",
            "FRIEND_MODEL": "model",
            "FRIEND_WORKSPACES_FILE": "workspaces_file",
            "FRIEND_HISTORY_RETENTION_DAYS": "history_retention_days",
            "FRIEND_AUDIT_RETENTION_DAYS": "audit_retention_days",
        }
        return {
            destination: os.environ[source]
            for source, destination in mapping.items()
            if source in os.environ and os.environ[source] != ""
        }

    def invocation(self, args: argparse.Namespace) -> Invocation:
        environment = self._environment_inputs()
        if args.operation not in CONFIGURATION_OPERATIONS:
            environment = {}
        env_noninteractive = os.environ.get("FRIEND_NONINTERACTIVE")
        if env_noninteractive not in {None, "", "0", "1"}:
            raise ManagementError(
                65,
                "INVALID_INPUT",
                "FRIEND_NONINTERACTIVE must be 0 or 1.",
            )
        non_interactive = args.non_interactive or env_noninteractive == "1"
        request: dict[str, Any] | None = None
        if args.request_file is not None:
            if not args.request_file.is_absolute():
                raise ManagementError(
                    2, "INVALID_USAGE", "--request-file must use an absolute path."
                )
            request = self._request(args.request_file, args.operation)
        inputs = dict(environment)
        if request is not None:
            inputs.update(request["inputs"])
        request_correlation = request["correlation_id"] if request else None
        if args.correlation_id and request_correlation:
            if args.correlation_id != request_correlation:
                raise ManagementError(
                    65, "REQUEST_MISMATCH", "Correlation IDs do not match."
                )
        correlation = args.correlation_id or request_correlation or str(uuid.uuid4())
        validate_uuid(correlation, label="correlation_id")
        actor = request["requested_by"] if request else "operator"
        invocation = Invocation(
            operation=args.operation,
            correlation_id=correlation,
            actor=actor,
            inputs=inputs,
            confirmation=request["confirmation"] if request else None,
            retain_state=request.get("retain_state") if request else None,
            dry_run=args.dry_run,
            json_output=args.json,
            non_interactive=non_interactive,
            assume_yes=args.yes,
            supplied_plan_digest=args.plan_digest,
            request_supplied=request is not None,
        )
        self._prepare_inputs(invocation)
        return invocation

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

    @staticmethod
    def _prompt_secret(message: str) -> str:
        try:
            return getpass.getpass(message)
        except (EOFError, KeyboardInterrupt) as exc:
            raise ManagementError(
                64,
                "INTERACTIVE_INPUT_REQUIRED",
                "Interactive installation was cancelled.",
            ) from exc

    def _prepare_inputs(self, invocation: Invocation) -> None:
        operation = invocation.operation
        if operation in {"install", "repair", "update", "resume"}:
            self._prepare_configuration_inputs(invocation)
        if operation == "backup":
            destination = invocation.inputs.get("backup_destination")
            if destination is None and not invocation.non_interactive:
                destination = self._prompt(
                    "Absolute backup destination directory: ",
                    as_json=invocation.json_output,
                ).strip()
                invocation.inputs["backup_destination"] = destination
            if not isinstance(destination, str) or not destination:
                raise ManagementError(
                    64,
                    "MISSING_INPUT",
                    "backup_destination is required for backup.",
                )
            self._validate_backup_destination(Path(destination), dry_run=invocation.dry_run)
        if operation == "uninstall":
            if invocation.retain_state is None:
                if invocation.non_interactive:
                    raise ManagementError(
                        64,
                        "MISSING_INPUT",
                        "Unattended uninstall requires retain_state in a request file.",
                    )
                answer = self._prompt(
                    "Retain protected Friend state? [Y/n]: ",
                    as_json=invocation.json_output,
                ).strip().lower()
                invocation.retain_state = answer not in {"n", "no"}
            if not invocation.retain_state:
                invocation.confirmation = invocation.confirmation or (
                    "" if invocation.non_interactive else self._prompt(
                        f"Type {DELETE_CONFIRMATION!r} to delete Friend state: ",
                        as_json=invocation.json_output,
                    )
                )
                if invocation.confirmation != DELETE_CONFIRMATION:
                    raise ManagementError(
                        64,
                        "CONFIRMATION_REQUIRED",
                        f"Complete uninstall requires: {DELETE_CONFIRMATION}",
                    )

    def _prepare_configuration_inputs(self, invocation: Invocation) -> None:
        existing = self._existing_settings()
        needs_install_inputs = invocation.operation == "install" and existing is None
        interactive_install = (
            needs_install_inputs
            and not invocation.non_interactive
            and not invocation.assume_yes
            and not invocation.request_supplied
        )
        destination = sys.stderr if invocation.json_output else sys.stdout
        if interactive_install:
            if not sys.stdin.isatty():
                raise ManagementError(
                    64,
                    "INTERACTIVE_INPUT_REQUIRED",
                    "Run the installer in a terminal or use --non-interactive with required inputs.",
                )
            print("Imaginary Friend interactive installer", file=destination)
            print(
                "Press Enter to accept each value shown in brackets.",
                file=destination,
            )
        owner = invocation.inputs.get("owner_user") or self._owner_from_config()
        if (
            needs_install_inputs
            and not interactive_install
            and not invocation.inputs.get("owner_user")
        ):
            raise ManagementError(
                64,
                "MISSING_INPUT",
                "owner_user is required for unattended installation.",
            )
        if owner is None and interactive_install:
            default_owner = os.environ.get("SUDO_USER", "")
            if not default_owner and os.geteuid() != 0:
                default_owner = pwd.getpwuid(os.geteuid()).pw_name
            while owner is None:
                suffix = f" [{default_owner}]" if default_owner else ""
                answer = self._prompt(
                    f"Human owner{suffix}: ",
                    as_json=invocation.json_output,
                ).strip()
                candidate = answer or default_owner
                try:
                    self._validate_owner(candidate)
                except ManagementError as exc:
                    print(f"  {exc.message}", file=destination)
                else:
                    owner = candidate
                    invocation.inputs["owner_user"] = owner
        if not owner and (needs_install_inputs or existing is None):
            raise ManagementError(
                64, "MISSING_INPUT", "owner_user is required for installation."
            )
        if owner:
            invocation.inputs["owner_user"] = owner
        password_file = invocation.inputs.get("owner_password_file")
        if password_file is not None:
            if not isinstance(password_file, str) or not Path(password_file).is_absolute():
                raise ManagementError(
                    65, "INVALID_INPUT", "owner_password_file must be absolute."
                )
            invocation.password = read_secret_file(Path(password_file))
        elif needs_install_inputs and not interactive_install:
            raise ManagementError(
                64,
                "MISSING_INPUT",
                "owner_password_file is required for unattended installation.",
            )
        elif existing is None:
            while invocation.password is None:
                first = self._prompt_secret(
                    "Owner password (leave empty to generate a strong password): "
                )
                if not first:
                    invocation.generated_password = secrets.token_urlsafe(24)
                    invocation.password = invocation.generated_password
                    break
                second = self._prompt_secret("Repeat owner password: ")
                if not secrets.compare_digest(first, second):
                    print("  Passwords did not match.", file=destination)
                    continue
                try:
                    invocation.password = validate_owner_password(first)
                except ManagementError as exc:
                    print(f"  {exc.message}", file=destination)
        model_url = invocation.inputs.get(
            "model_base_url",
            existing["model_base_url"] if existing else DEFAULT_MODEL_BASE_URL,
        )
        if interactive_install and "model_base_url" not in invocation.inputs:
            while True:
                answer = self._prompt(
                    f"Local model endpoint [{model_url}]: ",
                    as_json=invocation.json_output,
                ).strip()
                candidate = answer or str(model_url)
                try:
                    validate_model_base_url(candidate)
                except FriendError as exc:
                    print(f"  {exc.message}", file=destination)
                else:
                    model_url = candidate
                    break
        model = invocation.inputs.get("model", existing["model"] if existing else None)
        if (
            needs_install_inputs
            and not interactive_install
            and not invocation.inputs.get("model")
        ):
            raise ManagementError(
                64, "MISSING_INPUT", "model is required for unattended installation."
            )
        if model is None and existing is None and interactive_install:
            while model is None:
                answer = self._prompt(
                    "OpenAI-compatible local model ID: ",
                    as_json=invocation.json_output,
                ).strip()
                try:
                    validate_model_id(answer)
                except FriendError as exc:
                    print(f"  {exc.message}", file=destination)
                else:
                    model = answer
                    invocation.inputs["model"] = model
        if existing is None and not model:
            raise ManagementError(64, "MISSING_INPUT", "model is required for installation.")
        try:
            validate_model_base_url(str(model_url))
            validate_model_id(str(model))
        except FriendError as exc:
            raise ManagementError(65, exc.code, exc.message) from exc
        invocation.inputs["model_base_url"] = str(model_url)
        invocation.inputs["model"] = str(model)
        history = invocation.inputs.get(
            "history_retention_days",
            existing["history_retention_days"] if existing else 30,
        )
        audit = invocation.inputs.get(
            "audit_retention_days",
            existing["audit_retention_days"] if existing else 90,
        )
        if interactive_install and "history_retention_days" not in invocation.inputs:
            while True:
                answer = self._prompt(
                    f"Conversation history retention in days [{history}]: ",
                    as_json=invocation.json_output,
                ).strip()
                try:
                    history = self._bounded_integer(
                        answer or history,
                        "history_retention_days",
                        1,
                        365,
                    )
                except ManagementError as exc:
                    print(f"  {exc.message}", file=destination)
                else:
                    break
        if interactive_install and "audit_retention_days" not in invocation.inputs:
            while True:
                answer = self._prompt(
                    f"Operational audit retention in days [{audit}]: ",
                    as_json=invocation.json_output,
                ).strip()
                try:
                    audit = self._bounded_integer(
                        answer or audit,
                        "audit_retention_days",
                        30,
                        3650,
                    )
                except ManagementError as exc:
                    print(f"  {exc.message}", file=destination)
                else:
                    break
        history_value = self._bounded_integer(history, "history_retention_days", 1, 365)
        audit_value = self._bounded_integer(audit, "audit_retention_days", 30, 3650)
        invocation.inputs["history_retention_days"] = history_value
        invocation.inputs["audit_retention_days"] = audit_value
        invocation.workspaces = self._workspace_inputs(invocation.inputs.get("workspaces_file"))

    @staticmethod
    def _bounded_integer(value: Any, name: str, minimum: int, maximum: int) -> int:
        if isinstance(value, bool):
            raise ManagementError(65, "INVALID_INPUT", f"{name} must be an integer.")
        if isinstance(value, int):
            parsed = value
        elif isinstance(value, str) and value.isascii() and value.isdecimal():
            parsed = int(value)
        else:
            raise ManagementError(65, "INVALID_INPUT", f"{name} must be an integer.")
        if not minimum <= parsed <= maximum:
            raise ManagementError(
                65,
                "INVALID_INPUT",
                f"{name} must be between {minimum} and {maximum}.",
            )
        return parsed

    def _existing_settings(self) -> dict[str, Any] | None:
        if not self.paths.database.is_file():
            return None
        try:
            database = Database(self.paths.database)
            database.require_ready()
            return database.settings()
        except FriendError:
            return None

    def _workspace_inputs(self, file_value: Any) -> list[Path]:
        if file_value is None:
            if self.paths.database.is_file():
                try:
                    records = Database(self.paths.database).list_workspaces()
                    paths = [Path(record["canonical_root"]) for record in records]
                    if paths:
                        return paths
                except (FriendError, OSError):
                    pass
            return [DEFAULT_WORKSPACE]
        if not isinstance(file_value, str) or not Path(file_value).is_absolute():
            raise ManagementError(65, "INVALID_INPUT", "workspaces_file must be absolute.")
        path = Path(file_value)
        check_secure_file(path)
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise ManagementError(
                65, "INVALID_INPUT", "Workspace file must be a JSON array."
            ) from exc
        if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
            raise ManagementError(
                65, "INVALID_INPUT", "Workspace file must be an array of absolute paths."
            )
        paths = [DEFAULT_WORKSPACE, *(Path(item) for item in value)]
        unique: list[Path] = []
        for item in paths:
            if not item.is_absolute() or ".." in item.parts:
                raise ManagementError(
                    65, "INVALID_INPUT", "Workspace roots must be canonical absolute paths."
                )
            if item not in unique:
                unique.append(item)
        return unique

    def _validate_backup_destination(self, path: Path, *, dry_run: bool) -> None:
        if not path.is_absolute() or ".." in path.parts:
            raise ManagementError(
                65, "INVALID_INPUT", "Backup destination must be absolute and canonical."
            )
        if path == self.paths.state_root or self.paths.state_root in path.parents:
            raise ManagementError(
                73, "UNSAFE_DESTINATION", "Backup destination cannot be inside Friend state."
            )
        if any(
            path == workspace or workspace in path.parents
            for workspace in self._installed_workspace_paths()
        ):
            raise ManagementError(
                73,
                "UNSAFE_DESTINATION",
                "Backup destination cannot be inside a nominated workspace.",
            )
        try:
            details = path.lstat()
        except FileNotFoundError as exc:
            raise ManagementError(
                66, "DESTINATION_MISSING", "Backup destination directory does not exist."
            ) from exc
        if not stat.S_ISDIR(details.st_mode) or stat.S_ISLNK(details.st_mode):
            raise ManagementError(
                73, "UNSAFE_DESTINATION", "Backup destination must be a real directory."
            )
        if details.st_uid != 0 or stat.S_IMODE(details.st_mode) & 0o022:
            raise ManagementError(
                73,
                "UNSAFE_DESTINATION",
                "Backup destination must be root-owned and not group/other writable.",
            )

    def _installed_workspace_paths(self) -> list[Path]:
        if not self.paths.database.is_file():
            return []
        try:
            return [
                Path(record["canonical_root"])
                for record in Database(self.paths.database).list_workspaces()
            ]
        except (FriendError, OSError):
            return []

    def load_marker(self, *, required: bool = False) -> dict[str, Any] | None:
        if not self.paths.marker.exists():
            if required:
                raise ManagementError(
                    66, "INSTALLATION_MISSING", "Imaginary Friend is not installed."
                )
            return None
        try:
            details = self.paths.marker.lstat()
        except OSError as exc:
            raise ManagementError(78, "INVALID_MARKER", "Ownership marker is unreadable.") from exc
        if (
            not stat.S_ISREG(details.st_mode)
            or details.st_nlink != 1
            or details.st_uid != 0
            or details.st_gid != 0
            or stat.S_IMODE(details.st_mode) != 0o644
        ):
            raise ManagementError(
                78, "INVALID_MARKER", "Ownership marker type, owner, or mode is invalid."
            )
        marker = read_json(self.paths.marker)
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
        if set(marker) != required_fields:
            raise ManagementError(78, "INVALID_MARKER", "Ownership marker fields are invalid.")
        expected = {
            "schema_version": 1,
            "product_id": PRODUCT_ID,
            "install_root": str(self.paths.install_root),
            "lifecycle_entrypoint": str(self.paths.entrypoint),
        }
        if any(marker.get(key) != value for key, value in expected.items()):
            raise ManagementError(78, "INVALID_MARKER", "Ownership marker identity is invalid.")
        validate_uuid(marker.get("instance_id"), label="marker instance_id")
        validate_version(str(marker.get("version")))
        if (
            not isinstance(marker.get("source_revision"), str)
            or not marker["source_revision"]
            or len(marker["source_revision"]) > 256
        ):
            raise ManagementError(
                78, "INVALID_MARKER", "Marker source revision is invalid."
            )
        try:
            datetime.fromisoformat(str(marker.get("installed_at")).replace("Z", "+00:00"))
        except ValueError as exc:
            raise ManagementError(
                78, "INVALID_MARKER", "Marker installation time is invalid."
            ) from exc
        digest = marker.get("artifact_sha256")
        if digest is not None and (
            not isinstance(digest, str)
            or len(digest) != 64
            or any(character not in "0123456789abcdef" for character in digest)
        ):
            raise ManagementError(78, "INVALID_MARKER", "Marker artifact digest is invalid.")
        return marker

    def _transaction_instance(self) -> str | None:
        if not self.paths.transaction.is_file():
            return None
        check_secure_file(self.paths.transaction, missing_code=73)
        transaction = read_json(self.paths.transaction)
        if set(transaction) != {
            "schema_version",
            "product_id",
            "instance_id",
            "started_at",
        }:
            raise ManagementError(73, "UNSAFE_COLLISION", "Install transaction is invalid.")
        if transaction["schema_version"] != 1 or transaction["product_id"] != PRODUCT_ID:
            raise ManagementError(73, "UNSAFE_COLLISION", "Install transaction is invalid.")
        return validate_uuid(transaction["instance_id"], label="transaction instance_id")

    def instance_id(self) -> str | None:
        marker = self.load_marker()
        if marker is not None:
            return str(marker["instance_id"])
        return self._transaction_instance()

    @staticmethod
    def steps_for(operation: str) -> list[dict[str, Any]]:
        steps: dict[str, list[tuple[str, str, bool]]] = {
            "install": [
                ("preflight", "Validate platform, model, inputs, and collisions", False),
                ("ownership", "Create or validate the Friend transaction and identities", True),
                ("paths", "Converge protected product and nominated workspace paths", True),
                ("credentials", "Create or preserve authentication and session material", True),
                ("runtime", "Stage root-owned code, policy, service, and helpers", True),
                ("state", "Initialize or migrate Friend SQLite state", True),
                (
                    "service",
                    "Validate Friend and start its service unless suspension is preserved",
                    True,
                ),
                ("health", "Verify positive capabilities and structural denials", False),
                ("marker", "Atomically record ownership after health succeeds", True),
            ],
            "repair": [
                ("ownership", "Validate the Friend marker and declared resources", False),
                ("configuration", "Reassert only product-owned configuration and permissions", True),
                ("state", "Validate state and apply requested owner-only settings", True),
                ("service", "Reload and restart only the Friend service", True),
                ("health", "Run the complete Friend verification set", False),
            ],
            "backup": [
                ("ownership", "Validate the Friend ownership marker", False),
                ("snapshot", "Snapshot state without live sessions or workspace files", True),
                ("archive", "Write and verify a mode-0600 backup archive", True),
            ],
            "update": [
                ("preflight", "Validate source version, model, ownership, and sandbox", False),
                ("backup", "Preserve current code, configuration, and compatible state", True),
                ("stage", "Stage and validate the new independent Friend runtime", True),
                ("switch", "Atomically switch only Friend code and configuration", True),
                ("health", "Restart Friend and roll back automatically on failed health", True),
                ("marker", "Record the new version after health succeeds", True),
            ],
            "rollback": [
                ("ownership", "Validate current and previous Friend ownership", False),
                ("stop", "Stop only the Friend service", True),
                ("restore", "Restore previous Friend code and compatible state", True),
                ("health", "Validate and start the restored Friend release", True),
                ("marker", "Record the restored version", True),
            ],
            "suspend": [
                ("ownership", "Validate Friend state", False),
                ("sessions", "Revoke every Friend session and suspend capabilities", True),
                ("service", "Stop only the Friend service", True),
            ],
            "resume": [
                ("integrity", "Validate credentials, policy, workspace, sandbox, and model", False),
                ("state", "Clear Friend suspension", True),
                ("service", "Start only the Friend service and check health", True),
            ],
            "uninstall": [
                ("ownership", "Validate every resource against the Friend marker", False),
                ("service", "Stop, disable, and remove only the Friend unit", True),
                ("runtime", "Remove Friend executable code, commands, and configuration", True),
                ("identity", "Remove the non-login Friend service identity", True),
                ("state", "Retain or delete Friend state exactly as requested", True),
                ("workspace", "Leave every nominated workspace file untouched", False),
            ],
        }
        return [
            {"id": identifier, "summary": summary, "mutates": mutates}
            for identifier, summary, mutates in steps.get(operation, [])
        ]

    def _input_fingerprints(self, invocation: Invocation) -> dict[str, Any]:
        fingerprints: dict[str, Any] = {}
        for key in sorted(invocation.inputs):
            value = invocation.inputs[key]
            if key in SECRET_INPUTS and isinstance(value, str):
                path = Path(value)
                check_secure_file(path)
                fingerprints[key] = sha256_bytes(path.read_bytes())
            else:
                fingerprints[key] = sha256_bytes(canonical_json(value))
        if invocation.retain_state is not None:
            fingerprints["retain_state"] = sha256_bytes(
                canonical_json(invocation.retain_state)
            )
        return fingerprints

    @staticmethod
    def plan_configuration(invocation: Invocation) -> dict[str, Any]:
        return {
            "owner_user": invocation.inputs["owner_user"],
            "model_base_url": invocation.inputs["model_base_url"],
            "model": invocation.inputs["model"],
            "history_retention_days": invocation.inputs["history_retention_days"],
            "audit_retention_days": invocation.inputs["audit_retention_days"],
            "workspaces": [str(path) for path in invocation.workspaces],
        }

    def plan_digest(
        self, invocation: Invocation, steps: list[dict[str, Any]], instance_id: str | None
    ) -> str:
        value = {
            "product_id": PRODUCT_ID,
            "version": self.version,
            "operation": invocation.operation,
            "instance": instance_id,
            "inputs": self._input_fingerprints(invocation),
            "steps": steps,
        }
        return sha256_bytes(canonical_json(value))

    def _approve(self, invocation: Invocation, result: Result) -> None:
        if invocation.dry_run or invocation.operation not in MUTATING:
            return
        if invocation.assume_yes:
            return
        if invocation.non_interactive:
            raise ManagementError(
                64,
                "PLAN_APPROVAL_REQUIRED",
                "Unattended mutation requires --yes after reviewing the plan.",
            )
        destination = sys.stderr if invocation.json_output else sys.stdout
        configuration = None
        if result.details is not None:
            candidate = result.details.get("configuration")
            if isinstance(candidate, dict):
                configuration = candidate
        print_plan(result, configuration=configuration, file=destination)
        answer = self._prompt(
            "Apply this plan? [y/N]: ",
            as_json=invocation.json_output,
        ).strip().lower()
        if answer not in {"y", "yes"}:
            raise ManagementError(64, "PLAN_NOT_APPROVED", "Lifecycle plan was not approved.")

    @contextmanager
    def mutation_lock(self) -> Iterator[None]:
        self.paths.lock.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(
            self.paths.lock,
            os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0),
            0o600,
        )
        os.fchmod(fd, 0o600)
        try:
            try:
                fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc:
                raise ManagementError(
                    75,
                    "TARGET_BUSY",
                    "Another Imaginary Friend mutation is in progress.",
                    retryable=True,
                ) from exc
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def run(self, invocation: Invocation) -> tuple[Result, int]:
        instance_id = self.instance_id()
        phase = _operation_phase(
            invocation.operation,
            dry_run=invocation.dry_run,
        )
        result = Result(
            operation=invocation.operation,
            correlation_id=invocation.correlation_id,
            product_version=self.version,
            instance_id=instance_id,
            phase=phase,
            steps=self.steps_for(invocation.operation),
        )
        if invocation.operation == "describe":
            result.details = {"descriptor": self.descriptor}
            result.checks.append(
                self.check("descriptor", True, "Product descriptor is valid.")
            )
            self._audit_read(invocation, result)
            return result, 0
        if invocation.operation == "status":
            self._status(result)
            self._audit_read(invocation, result)
            return result, 0
        if invocation.operation in {"verify", "doctor"}:
            result.checks = self.verify_checks(probe_runtime=True)
            failed = any(item["status"] == "fail" for item in result.checks)
            result.status = "degraded" if failed else "ok"
            result.recovery = [
                item["remediation"]
                for item in result.checks
                if item["status"] != "pass" and item["remediation"]
            ]
            self._audit_read(invocation, result)
            if invocation.operation == "doctor":
                return result, 0
            return result, 1 if failed else 0
        if invocation.operation in {"install", "repair", "update", "resume"}:
            result.details = {
                "configuration": self.plan_configuration(invocation),
            }
        result.plan_digest = self.plan_digest(invocation, result.steps, instance_id)
        result.requires_confirmation = True
        if invocation.supplied_plan_digest is not None:
            supplied = invocation.supplied_plan_digest
            if supplied != result.plan_digest:
                raise ManagementError(
                    78,
                    "PLAN_CHANGED",
                    "Supplied plan digest does not match current state and inputs.",
                )
        if invocation.dry_run:
            result.checks = self.preflight_checks(invocation, network=False)
            result.status = (
                "blocked"
                if any(item["status"] == "fail" for item in result.checks)
                else "ok"
            )
            return result, 1 if result.status == "blocked" else 0
        if os.geteuid() != 0:
            raise ManagementError(
                73, "ROOT_REQUIRED", "Mutating Friend lifecycle operations require root."
            )
        self._approve(invocation, result)
        with self.mutation_lock():
            current_instance = self.instance_id()
            current_digest = self.plan_digest(invocation, result.steps, current_instance)
            if current_digest != result.plan_digest:
                raise ManagementError(
                    78, "PLAN_CHANGED", "Host state changed after plan review."
                )
            changed_resources, previous_version = self._execute(invocation, result)
            installed_marker = self.load_marker()
            result.instance_id = (
                str(installed_marker["instance_id"])
                if installed_marker is not None
                else current_instance
            )
            if installed_marker is not None:
                result.product_version = str(installed_marker["version"])
            result.changed = bool(changed_resources)
            result.details = {
                "changed_resources": changed_resources,
                "previous_version": previous_version,
            }
            self._write_receipt_and_audit(
                invocation,
                result,
                changed_resources=changed_resources,
                previous_version=previous_version,
            )
        if invocation.generated_password:
            destination = sys.stderr if invocation.json_output else sys.stdout
            print(
                "Generated Imaginary Friend owner password "
                f"(shown once): {invocation.generated_password}",
                file=destination,
            )
        return result, 0

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
            "status": "warn" if warning else "pass" if passed else "fail",
            "summary": summary,
            "remediation": remediation,
        }

    def _status(self, result: Result) -> None:
        marker = self.load_marker()
        if marker is None:
            result.status = "degraded"
            result.checks.append(
                self.check(
                    "installation",
                    False,
                    "Imaginary Friend is not installed.",
                    "Run friend-manage install after reviewing a dry-run.",
                )
            )
            result.details = {"lifecycle": "absent", "health": "unknown"}
            return
        installed = self.paths.install_root.is_dir() and self.paths.unit.is_file()
        suspended = False
        if self.paths.database.is_file():
            try:
                suspended = bool(Database(self.paths.database).settings()["suspended"])
            except FriendError:
                result.status = "degraded"
        lifecycle = "retained" if not installed else "suspended" if suspended else "active"
        checks = self.verify_checks(probe_runtime=False) if installed else []
        failed = any(item["status"] == "fail" for item in checks)
        result.status = "degraded" if failed or not installed else "ok"
        result.checks = checks
        result.details = {
            "lifecycle": lifecycle,
            "health": "degraded" if failed else "not_running" if not installed else "ok",
            "installed_version": marker["version"],
        }

    def preflight_checks(
        self, invocation: Invocation, *, network: bool
    ) -> list[dict[str, str]]:
        checks: list[dict[str, str]] = []
        if invocation.operation != "install":
            try:
                marker = self.load_marker(required=True)
            except ManagementError as exc:
                checks.append(
                    self.check(
                        "ownership_marker",
                        False,
                        exc.message,
                        "Install Friend or restore its valid ownership marker first.",
                    )
                )
            else:
                checks.append(
                    self.check(
                        "ownership_marker",
                        True,
                        "The Friend ownership marker is valid.",
                    )
                )
                if (
                    invocation.operation == "repair"
                    and marker["version"] != self.version
                ):
                    checks.append(
                        self.check(
                            "source_version",
                            False,
                            "Repair source does not match the installed version.",
                            "Use update for a newer source or the matching release for repair.",
                        )
                    )
                if (
                    invocation.operation == "rollback"
                    and not self.paths.rollback_root.is_dir()
                ):
                    checks.append(
                        self.check(
                            "rollback_runtime",
                            False,
                            "No previous Friend runtime is available.",
                            "Restore a verified backup or install a reviewed release.",
                        )
                    )
        if invocation.operation in {"install", "update", "resume"}:
            try:
                self._platform_preflight()
            except ManagementError as exc:
                checks.append(
                    self.check("platform", False, exc.message, *exc.recovery)
                    if exc.recovery
                    else self.check("platform", False, exc.message)
                )
            else:
                checks.append(self.check("platform", True, "Supported Ubuntu platform detected."))
        if invocation.operation == "install":
            try:
                self._validate_owner(str(invocation.inputs.get("owner_user", "")))
                self._collision_preflight()
                self._workspace_preflight(invocation.workspaces)
            except (ManagementError, FriendError) as exc:
                checks.append(
                    self.check(
                        "install_boundary",
                        False,
                        getattr(exc, "message", str(exc)),
                        "Resolve the collision or invalid workspace before installing.",
                    )
                )
            else:
                checks.append(
                    self.check(
                        "install_boundary",
                        True,
                        "Owner, namespace, and workspace checks passed.",
                    )
                )
        if invocation.operation in {"install", "update", "resume"}:
            if network:
                try:
                    self._probe_model(invocation)
                except ManagementError as exc:
                    checks.append(
                        self.check(
                            "model",
                            False,
                            exc.message,
                            "Start the configured loopback model and verify its model ID.",
                        )
                    )
                else:
                    checks.append(
                        self.check("model", True, "Local model list and completion probe passed.")
                    )
            else:
                checks.append(
                    self.check(
                        "model",
                        True,
                        "Model probe is deferred during a non-mutating dry-run.",
                        warning=True,
                    )
                )
        return checks

    def _platform_preflight(self) -> None:
        machine = platform.machine().lower()
        if machine not in {"x86_64", "amd64"}:
            raise ManagementError(
                69, "UNSUPPORTED_PLATFORM", "Imaginary Friend supports amd64 only."
            )
        try:
            values: dict[str, str] = {}
            for line in Path("/etc/os-release").read_text(encoding="utf-8").splitlines():
                if "=" in line:
                    key, value = line.split("=", 1)
                    values[key] = value.strip().strip('"')
        except OSError as exc:
            raise ManagementError(
                69, "UNSUPPORTED_PLATFORM", "Ubuntu release metadata is unavailable."
            ) from exc
        if values.get("ID") != "ubuntu" or values.get("VERSION_ID") not in {
            "22.04",
            "24.04",
        }:
            raise ManagementError(
                69,
                "UNSUPPORTED_PLATFORM",
                "Imaginary Friend supports Ubuntu Desktop 22.04 and 24.04 LTS.",
            )
        if sys.version_info[:2] not in {(3, 10), (3, 12)}:
            raise ManagementError(
                69,
                "UNSUPPORTED_PYTHON",
                "Imaginary Friend requires Python 3.10 or 3.12.",
            )
        required = ("systemctl", "useradd", "groupadd", "usermod", "runuser")
        missing = [name for name in required if shutil.which(name) is None]
        if missing:
            raise ManagementError(
                69,
                "DEPENDENCY_MISSING",
                f"Required local command is unavailable: {missing[0]}",
            )

    @staticmethod
    def _validate_owner(name: str) -> pwd.struct_passwd:
        if not name or name == "root":
            raise ManagementError(
                65, "INVALID_OWNER", "Owner must be an existing non-root local account."
            )
        try:
            record = pwd.getpwnam(name)
        except KeyError as exc:
            raise ManagementError(
                65, "INVALID_OWNER", "Owner must be an existing non-root local account."
            ) from exc
        if record.pw_uid == 0 or record.pw_name == "friend":
            raise ManagementError(
                65, "INVALID_OWNER", "Owner must be an existing non-root human account."
            )
        return record

    def _collision_preflight(self) -> None:
        marker = self.load_marker()
        transaction = self._transaction_instance()
        owned = marker is not None or transaction is not None
        reserved_paths = (
            self.paths.install_root,
            self.paths.configuration_root,
            self.paths.state_root,
            self.paths.log_root,
            self.paths.workspace_parent,
            self.paths.unit,
            self.paths.logrotate,
            self.paths.entrypoint,
            self.paths.diagnostics,
            self.paths.rollback_root,
        )
        if not owned:
            for name in ("friend",):
                try:
                    pwd.getpwnam(name)
                except KeyError:
                    pass
                else:
                    raise ManagementError(
                        73, "UNSAFE_COLLISION", f"Unowned account already exists: {name}"
                    )
            for name in ("friend", "friend-share"):
                try:
                    grp.getgrnam(name)
                except KeyError:
                    pass
                else:
                    raise ManagementError(
                        73, "UNSAFE_COLLISION", f"Unowned group already exists: {name}"
                    )
            for path in reserved_paths:
                if path.exists() or path.is_symlink():
                    raise ManagementError(
                        73, "UNSAFE_COLLISION", f"Unowned reserved path exists: {path}"
                    )
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
                try:
                    listener.bind(("127.0.0.1", 6767))
                except OSError as exc:
                    raise ManagementError(
                        73,
                        "UNSAFE_COLLISION",
                        "Loopback port 6767 is already in use.",
                    ) from exc
        else:
            for path in reserved_paths:
                if path.is_symlink():
                    raise ManagementError(
                        73, "UNSAFE_COLLISION", f"Reserved path is a symlink: {path}"
                    )

    def _workspace_preflight(self, workspaces: list[Path]) -> None:
        if not workspaces or workspaces[0] != DEFAULT_WORKSPACE:
            raise ManagementError(
                65, "INVALID_WORKSPACE", "Default Friend workspace must remain nominated."
            )
        try:
            share_gid = grp.getgrnam("friend-share").gr_gid
        except KeyError:
            share_gid = None
        for path in workspaces:
            if path.exists() or path.is_symlink():
                try:
                    details = validate_nominated_root(
                        path, allow_default=path == DEFAULT_WORKSPACE
                    )
                except FriendError as exc:
                    raise ManagementError(73, exc.code, exc.message) from exc
                if path != DEFAULT_WORKSPACE and (
                    share_gid is None
                    or details.st_gid != share_gid
                    or stat.S_IMODE(details.st_mode) & 0o070 != 0o070
                    or not details.st_mode & stat.S_ISGID
                ):
                    raise ManagementError(
                        73,
                        "UNSAFE_WORKSPACE",
                        "Existing additional roots must use friend-share with group rwx and setgid.",
                    )
            elif path.parent != self.paths.workspace_parent:
                raise ManagementError(
                    73,
                    "UNSAFE_WORKSPACE",
                    "New workspace roots must be direct children of /srv/imaginary-friend.",
                )

    @staticmethod
    def _probe_model(invocation: Invocation) -> None:
        try:
            ModelClient(
                str(invocation.inputs["model_base_url"]),
                str(invocation.inputs["model"]),
                timeout=10,
            ).probe()
        except FriendError as exc:
            raise ManagementError(69, "MODEL_UNAVAILABLE", exc.message, retryable=True) from exc

    def verify_checks(
        self, *, probe_runtime: bool, allow_transaction: bool = False
    ) -> list[dict[str, str]]:
        checks: list[dict[str, str]] = []
        try:
            marker = self.load_marker(required=True)
        except ManagementError as exc:
            transaction = (
                self._transaction_instance()
                if allow_transaction and exc.code == "INSTALLATION_MISSING"
                else None
            )
            if transaction is None:
                return [
                    self.check(
                        "ownership_marker",
                        False,
                        exc.message,
                        "Use a reviewed source checkout to repair or reinstall Friend.",
                    )
                ]
            checks.append(
                self.check(
                    "installation_transaction",
                    True,
                    "The clean install transaction is valid.",
                )
            )
        else:
            checks.append(self.check("ownership_marker", True, "Ownership marker is valid."))
        retained = not self.paths.install_root.exists()
        if retained:
            checks.append(
                self.check(
                    "retained_state",
                    True,
                    "Friend software is removed and protected state is retained.",
                    warning=True,
                )
            )
            return checks
        try:
            account = pwd.getpwnam("friend")
            primary = grp.getgrgid(account.pw_gid).gr_name
            groups = {
                group.gr_name
                for group in grp.getgrall()
                if "friend" in group.gr_mem or group.gr_gid == account.pw_gid
            }
            account_ok = (
                primary == "friend"
                and account.pw_shell in {"/usr/sbin/nologin", "/bin/false"}
                and account.pw_dir == str(self.paths.state_root)
                and groups == {"friend", "friend-share"}
            )
        except KeyError:
            account_ok = False
        checks.append(
            self.check(
                "service_identity",
                account_ok,
                "Friend has a non-login, non-privileged service identity."
                if account_ok
                else "Friend service identity or group boundary is invalid.",
                "Run friend-manage repair from the matching source release.",
            )
        )
        for identifier, path, expected_mode, uid in (
            ("install_root", self.paths.install_root, 0o755, 0),
            ("configuration_root", self.paths.configuration_root, 0o750, 0),
            ("state_root", self.paths.state_root, 0o750, 0),
            ("log_root", self.paths.log_root, 0o750, 0),
        ):
            try:
                details = path.lstat()
                passed = (
                    stat.S_ISDIR(details.st_mode)
                    and not stat.S_ISLNK(details.st_mode)
                    and stat.S_IMODE(details.st_mode) == expected_mode
                    and (uid is None or details.st_uid == uid)
                )
            except OSError:
                passed = False
            checks.append(
                self.check(
                    identifier,
                    passed,
                    f"{path} ownership and mode are valid."
                    if passed
                    else f"{path} ownership or mode is invalid.",
                    "Run friend-manage repair.",
                )
            )
        key = self.paths.configuration_root / "session.key"
        try:
            details = key.lstat()
            friend_gid = grp.getgrnam("friend").gr_gid
            key_ok = (
                stat.S_ISREG(details.st_mode)
                and details.st_nlink == 1
                and details.st_size == 32
                and details.st_uid == 0
                and details.st_gid == friend_gid
                and stat.S_IMODE(details.st_mode) == 0o640
            )
        except (OSError, KeyError):
            key_ok = False
        checks.append(
            self.check(
                "credentials",
                key_ok,
                "Independent Friend credential material is present."
                if key_ok
                else "Friend credential material is missing or exposed.",
                "Run friend-manage repair; rotate the owner password if exposure is suspected.",
            )
        )
        try:
            database = Database(self.paths.database)
            database.require_ready()
            friend = pwd.getpwnam("friend")
            database_details = self.paths.database.lstat()
            journal_path = self.paths.database.with_name(
                f"{self.paths.database.name}-journal"
            )
            journal_details = journal_path.lstat()
            db_ok = (
                database.integrity_check() == "ok"
                and stat.S_ISREG(database_details.st_mode)
                and database_details.st_nlink == 1
                and database_details.st_uid == friend.pw_uid
                and database_details.st_gid == friend.pw_gid
                and stat.S_IMODE(database_details.st_mode) == 0o600
                and stat.S_ISREG(journal_details.st_mode)
                and journal_details.st_nlink == 1
                and journal_details.st_uid == friend.pw_uid
                and journal_details.st_gid == friend.pw_gid
                and stat.S_IMODE(journal_details.st_mode) == 0o600
            )
        except (FriendError, OSError, KeyError):
            database = None
            db_ok = False
        checks.append(
            self.check(
                "database",
                db_ok,
                "Friend SQLite state is valid."
                if db_ok
                else "Friend SQLite state is invalid.",
                "Restore a verified Friend backup or run doctor for recovery guidance.",
            )
        )
        workspace_ok = True
        if database is not None:
            try:
                share_gid = grp.getgrnam("friend-share").gr_gid
                for record in database.list_workspaces():
                    details = validate_nominated_root(
                        Path(record["canonical_root"]),
                        allow_default=record["canonical_root"]
                        == str(DEFAULT_WORKSPACE),
                    )
                    if (
                        details.st_dev != int(record["root_device"])
                        or details.st_ino != int(record["root_inode"])
                        or details.st_gid != share_gid
                        or stat.S_IMODE(details.st_mode) & 0o070 != 0o070
                        or not details.st_mode & stat.S_ISGID
                    ):
                        workspace_ok = False
            except (FriendError, OSError, KeyError):
                workspace_ok = False
        else:
            workspace_ok = False
        checks.append(
            self.check(
                "workspaces",
                workspace_ok,
                "Nominated workspace roots retain their device and inode."
                if workspace_ok
                else "A nominated workspace is missing, moved, mounted, or replaced.",
                "Restore the original root or explicitly repair workspace nominations.",
            )
        )
        sandbox_ok = self._unit_has_required_sandbox()
        checks.append(
            self.check(
                "sandbox",
                sandbox_ok,
                "Friend systemd confinement contains all required controls."
                if sandbox_ok
                else "Friend systemd confinement is missing a required control.",
                "Run friend-manage repair and review the unit before resume.",
            )
        )
        runtime_ok = self._runtime_is_root_controlled(
            allow_transaction=allow_transaction
        )
        checks.append(
            self.check(
                "runtime_integrity",
                runtime_ok,
                "Friend runtime, descriptor, policy, and lifecycle files are root-controlled."
                if runtime_ok
                else "Friend executable or policy state is writable or inconsistent.",
                "Stop Friend and run friend-manage repair from the matching release.",
            )
        )
        suspended = bool(database.settings()["suspended"]) if database else False
        if probe_runtime and not suspended:
            active = self._systemctl_is_active()
            checks.append(
                self.check(
                    "service",
                    active,
                    "Friend service is active."
                    if active
                    else "Friend service is not active.",
                    "Run friend-manage doctor, then repair or resume.",
                )
            )
            healthy = active and self._service_health()
            checks.append(
                self.check(
                    "loopback_health",
                    healthy,
                    "Friend loopback health endpoint answered."
                    if healthy
                    else "Friend loopback health endpoint did not answer.",
                    "Inspect redacted diagnostics and the Friend service journal.",
                )
            )
            try:
                settings = database.settings() if database else {}
                ModelClient(
                    settings["model_base_url"], settings["model"], timeout=10
                ).probe()
                model_ok = True
            except (FriendError, OSError, KeyError):
                model_ok = False
            checks.append(
                self.check(
                    "model",
                    model_ok,
                    "Configured loopback model passed list and completion probes."
                    if model_ok
                    else "Configured loopback model is unavailable or missing.",
                    "Start the local model endpoint and confirm its configured model ID.",
                )
            )
        elif suspended:
            stopped = not self._systemctl_is_active()
            checks.append(
                self.check(
                    "suspension",
                    stopped,
                    "Friend is suspended and useful service is stopped."
                    if stopped
                    else "Friend is suspended but its service is still active.",
                    "Stop imaginary-friend-chat.service before treating suspension as complete.",
                    warning=stopped,
                )
            )
        return checks

    @staticmethod
    def _run(
            command: list[str],
            *,
            check: bool = True,
            timeout: int = 120,
    ) -> subprocess.CompletedProcess[str]:
            try:
                completed = subprocess.run(
                    command,
                    check=False,
                    text=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                    env={
                        "PATH": "/usr/sbin:/usr/bin:/sbin:/bin",
                        "LANG": "C.UTF-8",
                    },
                )
            except (OSError, subprocess.TimeoutExpired) as exc:
                raise ManagementError(
                    75 if isinstance(exc, subprocess.TimeoutExpired) else 69,
                    "COMMAND_FAILED",
                    f"Required local command failed: {command[0]}",
                    retryable=isinstance(exc, subprocess.TimeoutExpired),
                ) from exc
            if check and completed.returncode != 0:
                raise ManagementError(
                    1,
                    "COMMAND_FAILED",
                    f"Required local command failed: {command[0]}",
                )
            return completed

    def _systemctl_is_active(self) -> bool:
            if shutil.which("systemctl") is None:
                return False
            return (
                self._run(
                    ["systemctl", "is-active", "--quiet", "imaginary-friend-chat.service"],
                    check=False,
                    timeout=20,
                ).returncode
                == 0
            )

    @staticmethod
    def _service_health() -> bool:
            connection = http.client.HTTPConnection("127.0.0.1", 6767, timeout=5)
            try:
                connection.request(
                    "GET",
                    "/healthz",
                    headers={"Host": "127.0.0.1:6767", "Connection": "close"},
                )
                response = connection.getresponse()
                raw = response.read(4096)
                if response.status != 200:
                    return False
                value = json.loads(raw.decode("utf-8"))
                return value == {"ok": True, "product_id": PRODUCT_ID}
            except (OSError, ValueError, http.client.HTTPException):
                return False
            finally:
                connection.close()

    def _unit_has_required_sandbox(self) -> bool:
            try:
                text = self.paths.unit.read_text(encoding="utf-8")
            except OSError:
                return False
            required = (
                "User=friend",
                "Group=friend",
                "SupplementaryGroups=friend-share",
                "NoNewPrivileges=true",
                "PrivateTmp=true",
                "PrivateDevices=true",
                "ProtectSystem=strict",
                "ProtectHome=true",
                "ProtectKernelTunables=true",
                "ProtectKernelModules=true",
                "ProtectControlGroups=true",
                "CapabilityBoundingSet=",
                "AmbientCapabilities=",
                "IPAddressDeny=any",
                "IPAddressAllow=localhost",
                "RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6",
            )
            return all(item in text for item in required) and "__FRIEND_" not in text

    def _runtime_is_root_controlled(self, *, allow_transaction: bool = False) -> bool:
            try:
                installed_descriptor = read_json(
                    self.paths.configuration_root / "PRODUCT.json"
                )
                installed_version = (
                    self.paths.install_root / "VERSION"
                ).read_text(encoding="utf-8").strip()
                marker = self.load_marker()
                if marker is None:
                    if not allow_transaction or self._transaction_instance() is None:
                        return False
                    installed_marker_version = self.version
                else:
                    installed_marker_version = str(marker["version"])
                if (
                    installed_descriptor != self.descriptor
                    or installed_version != installed_marker_version
                ):
                    return False
                protected_files = (
                    self.paths.configuration_root / "PRODUCT.json",
                    self.paths.configuration_root / "config.json",
                    self.paths.configuration_root / "policy.json",
                    self.paths.unit,
                    self.paths.logrotate,
                    self.paths.entrypoint,
                    self.paths.diagnostics,
                )
                for path in protected_files:
                    details = path.lstat()
                    if (
                        not stat.S_ISREG(details.st_mode)
                        or details.st_nlink != 1
                        or details.st_uid != 0
                        or stat.S_IMODE(details.st_mode) & 0o022
                    ):
                        return False
                for directory, names, files in os.walk(
                    self.paths.install_root, followlinks=False
                ):
                    for name in [*names, *files]:
                        path = Path(directory) / name
                        details = path.lstat()
                        if details.st_uid != 0:
                            return False
                        if stat.S_ISLNK(details.st_mode):
                            target = path.resolve(strict=True)
                            target_details = target.stat()
                            if (
                                target_details.st_uid != 0
                                or stat.S_IMODE(target_details.st_mode) & 0o022
                            ):
                                return False
                        elif stat.S_IMODE(details.st_mode) & 0o022:
                            return False
            except (ManagementError, OSError, UnicodeError):
                return False
            return True

    def _ensure_transaction(self) -> str:
            marker = self.load_marker()
            if marker is not None:
                return str(marker["instance_id"])
            transaction_instance = self._transaction_instance()
            if transaction_instance is not None:
                return transaction_instance
            self.paths.state_root.mkdir(parents=True, mode=0o700)
            os.chown(self.paths.state_root, 0, 0)
            os.chmod(self.paths.state_root, 0o700)
            instance_id = str(uuid.uuid4())
            atomic_write(
                self.paths.transaction,
                canonical_json(
                    {
                        "schema_version": 1,
                        "product_id": PRODUCT_ID,
                        "instance_id": instance_id,
                        "started_at": utc_now(),
                    }
                )
                + b"\n",
                mode=0o600,
            )
            return instance_id

    def _ensure_accounts(self, owner_user: str) -> tuple[int, int]:
            try:
                friend_group = grp.getgrnam("friend")
            except KeyError:
                self._run(["groupadd", "--system", "friend"])
                friend_group = grp.getgrnam("friend")
            try:
                share_group = grp.getgrnam("friend-share")
            except KeyError:
                self._run(["groupadd", "--system", "friend-share"])
                share_group = grp.getgrnam("friend-share")
            try:
                account = pwd.getpwnam("friend")
            except KeyError:
                self._run(
                    [
                        "useradd",
                        "--system",
                        "--gid",
                        "friend",
                        "--groups",
                        "friend-share",
                        "--home-dir",
                        str(self.paths.state_root),
                        "--shell",
                        "/usr/sbin/nologin",
                        "--no-create-home",
                        "friend",
                    ]
                )
                account = pwd.getpwnam("friend")
            groups = {
                group.gr_name
                for group in grp.getgrall()
                if "friend" in group.gr_mem or group.gr_gid == account.pw_gid
            }
            if (
                account.pw_gid != friend_group.gr_gid
                or account.pw_shell not in {"/usr/sbin/nologin", "/bin/false"}
                or account.pw_dir != str(self.paths.state_root)
                or groups - {"friend", "friend-share"}
            ):
                raise ManagementError(
                    73,
                    "UNSAFE_COLLISION",
                    "Existing friend identity does not match the unprivileged contract.",
                )
            if "friend-share" not in groups:
                self._run(["usermod", "--append", "--groups", "friend-share", "friend"])
            self._validate_owner(owner_user)
            self._run(["usermod", "--append", "--groups", "friend-share", owner_user])
            return account.pw_uid, share_group.gr_gid

    @staticmethod
    def _ensure_directory(path: Path, mode: int, uid: int, gid: int) -> None:
            if path.exists() or path.is_symlink():
                details = path.lstat()
                if not stat.S_ISDIR(details.st_mode) or stat.S_ISLNK(details.st_mode):
                    raise ManagementError(
                        73, "UNSAFE_COLLISION", f"Expected a real directory: {path}"
                    )
            else:
                path.mkdir(parents=True, mode=mode)
            os.chown(path, uid, gid)
            os.chmod(path, mode)

    def _ensure_paths(
            self,
            *,
            friend_uid: int,
            friend_gid: int,
            share_gid: int,
            workspaces: list[Path],
    ) -> None:
            self._ensure_directory(self.paths.state_root, 0o750, 0, friend_gid)
            self._ensure_directory(self.paths.configuration_root, 0o750, 0, friend_gid)
            self._ensure_directory(self.paths.log_root, 0o750, 0, friend_gid)
            self._ensure_directory(self.paths.receipts, 0o750, 0, 0)
            self._ensure_directory(self.paths.recovery, 0o700, 0, 0)
            self._ensure_directory(self.paths.state_root / "exports", 0o700, friend_uid, friend_gid)
            self._ensure_directory(self.paths.workspace_parent, 0o755, 0, 0)
            for workspace in workspaces:
                if workspace.exists():
                    if workspace == DEFAULT_WORKSPACE:
                        os.chown(workspace, 0, share_gid)
                        os.chmod(workspace, 0o2770)
                    continue
                workspace.mkdir(mode=0o2770)
                os.chown(workspace, 0, share_gid)
                os.chmod(workspace, 0o2770)
            if not self.paths.audit.exists():
                atomic_write(
                    self.paths.audit,
                    b"",
                    mode=0o640,
                    uid=friend_uid,
                    gid=friend_gid,
                )
            else:
                details = self.paths.audit.lstat()
                if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                    raise ManagementError(73, "UNSAFE_COLLISION", "Audit log is not a regular file.")
                os.chown(self.paths.audit, friend_uid, friend_gid)
                os.chmod(self.paths.audit, 0o640)

    @staticmethod
    def _reject_source_links(root: Path) -> None:
            for directory, names, files in os.walk(root, followlinks=False):
                directory_path = Path(directory)
                for name in [*names, *files]:
                    candidate = directory_path / name
                    if candidate.is_symlink():
                        raise ManagementError(
                            78,
                            "INVALID_SOURCE",
                            f"Product source must not contain symlinks: {candidate}",
                        )

    @staticmethod
    def _copy_tree(source: Path, destination: Path) -> None:
            Manager._reject_source_links(source)
            shutil.copytree(
                source,
                destination,
                symlinks=False,
                ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "dist"),
            )

    @staticmethod
    def _root_own_tree(root: Path) -> None:
            for directory, names, files in os.walk(root, followlinks=False):
                os.chown(directory, 0, 0)
                os.chmod(directory, 0o755)
                for name in [*names, *files]:
                    path = Path(directory) / name
                    if path.is_symlink():
                        os.lchown(path, 0, 0)
                    else:
                        os.chown(path, 0, 0)
                        os.chmod(path, 0o755 if path.is_dir() else 0o644)

    def _switch_staged_runtime(
            self, stage: Path, *, preserve_rollback: bool
    ) -> str | None:
            previous_version: str | None = None
            self._transient_runtime = None
            self._rollback_switch_active = False
            if not self.paths.install_root.exists():
                os.rename(stage, self.paths.install_root)
                return None
            try:
                previous_version = (
                    self.paths.install_root / "VERSION"
                ).read_text(encoding="utf-8").strip()
            except OSError:
                previous_version = None
            if preserve_rollback:
                previous_runtime = self.paths.install_root.parent / (
                    f".imaginary-friend-previous-{uuid.uuid4().hex}"
                )
                os.rename(self.paths.install_root, previous_runtime)
                try:
                    os.rename(stage, self.paths.install_root)
                except Exception:
                    os.rename(previous_runtime, self.paths.install_root)
                    raise
                self._transient_runtime = previous_runtime
                return previous_version
            if self.paths.rollback_root.exists():
                details = self.paths.rollback_root.lstat()
                if (
                    not stat.S_ISDIR(details.st_mode)
                    or stat.S_ISLNK(details.st_mode)
                    or details.st_uid != 0
                ):
                    raise ManagementError(
                        73, "UNSAFE_COLLISION", "Rollback path is not product-controlled."
                    )
                shutil.rmtree(self.paths.rollback_root)
            os.rename(self.paths.install_root, self.paths.rollback_root)
            self._rollback_switch_active = True
            try:
                os.rename(stage, self.paths.install_root)
            except Exception:
                os.rename(self.paths.rollback_root, self.paths.install_root)
                self._rollback_switch_active = False
                raise
            return previous_version

    def _commit_runtime_switch(self) -> None:
            previous_runtime = self._transient_runtime
            if previous_runtime is None or not previous_runtime.exists():
                self._transient_runtime = None
                self._rollback_switch_active = False
                return
            discarded = previous_runtime.with_name(
                f".imaginary-friend-discarded-{uuid.uuid4().hex}"
            )
            os.rename(previous_runtime, discarded)
            self._transient_runtime = None
            self._rollback_switch_active = False
            try:
                shutil.rmtree(discarded)
            except OSError:
                pass

    def _stage_runtime(self, *, preserve_rollback: bool = False) -> str | None:
            parent = self.paths.install_root.parent
            stage = parent / f".imaginary-friend-stage-{uuid.uuid4().hex}"
            try:
                stage.mkdir(mode=0o755)
                for name in ("agent", "bin", "etc", "systemd", "logrotate"):
                    self._copy_tree(self.source_asset(name), stage / name)
                scripts_source = self.source_root / "scripts"
                if not scripts_source.is_dir():
                    scripts_source = self.paths.install_root / "scripts"
                self._copy_tree(scripts_source, stage / "scripts")
                shutil.copy2(self.descriptor_path, stage / "PRODUCT.json")
                shutil.copy2(self.version_path, stage / "VERSION")
                venv.EnvBuilder(with_pip=False, symlinks=True).create(stage / "venv")
                self._root_own_tree(stage)
                os.chmod(stage, 0o755)
                for executable in [*(stage / "bin").iterdir(), stage / "scripts" / "manage.sh"]:
                    os.chmod(executable, 0o755)
                previous_version = self._switch_staged_runtime(
                    stage,
                    preserve_rollback=preserve_rollback,
                )
            finally:
                if stage.exists():
                    shutil.rmtree(stage)
            return previous_version

    def _owner_from_config(self) -> str | None:
            config = self.paths.configuration_root / "config.json"
            if not config.is_file():
                return None
            try:
                value = read_json(config)
            except ManagementError:
                return None
            owner = value.get("owner_user")
            return owner if isinstance(owner, str) else None

    def _deploy_configuration(
            self,
            invocation: Invocation,
            *,
            owner_user: str,
            friend_gid: int,
            workspaces: list[Path],
    ) -> None:
            policy_source = self.paths.install_root / "etc" / "policy.json"
            atomic_write(
                self.paths.configuration_root / "policy.json",
                policy_source.read_bytes(),
                mode=0o644,
            )
            descriptor = canonical_json(self.descriptor) + b"\n"
            atomic_write(
                self.paths.configuration_root / "PRODUCT.json",
                descriptor,
                mode=0o644,
            )
            signing_key = self.paths.configuration_root / "session.key"
            if signing_key.exists():
                details = signing_key.lstat()
                if (
                    not stat.S_ISREG(details.st_mode)
                    or details.st_nlink != 1
                    or details.st_size != 32
                ):
                    raise ManagementError(
                        78, "INVALID_CREDENTIAL", "Session-signing key is invalid."
                    )
                os.chown(signing_key, 0, friend_gid)
                os.chmod(signing_key, 0o640)
            else:
                atomic_write(
                    signing_key,
                    new_signing_key(),
                    mode=0o640,
                    uid=0,
                    gid=friend_gid,
                )
            config = {
                "schema_version": 1,
                "product_id": PRODUCT_ID,
                "owner_user": owner_user,
                "port": 6767,
                "database_path": str(self.paths.database),
                "audit_path": str(self.paths.audit),
                "signing_key_path": str(signing_key),
                "allowed_workspaces": [str(path) for path in workspaces],
            }
            atomic_write(
                self.paths.configuration_root / "config.json",
                canonical_json(config) + b"\n",
                mode=0o644,
            )

    def _initialize_database(
            self,
            invocation: Invocation,
            *,
            friend_uid: int,
            friend_gid: int,
            workspaces: list[Path],
    ) -> Database:
            database_preexisting = self.paths.database.is_file()
            database = Database(self.paths.database)
            password = invocation.password or secrets.token_urlsafe(24)
            database.initialize(
                password_hash=hash_password(password),
                model_base_url=str(invocation.inputs["model_base_url"]),
                model=str(invocation.inputs["model"]),
                history_retention_days=int(invocation.inputs["history_retention_days"]),
                audit_retention_days=int(invocation.inputs["audit_retention_days"]),
            )
            database.update_settings(
                {
                    "model_base_url": str(invocation.inputs["model_base_url"]),
                    "model": str(invocation.inputs["model"]),
                    "history_retention_days": int(
                        invocation.inputs["history_retention_days"]
                    ),
                    "audit_retention_days": int(invocation.inputs["audit_retention_days"]),
                }
            )
            if self.paths.database.exists():
                os.chown(self.paths.database, friend_uid, friend_gid)
                os.chmod(self.paths.database, 0o600)
            journal = self.paths.database.with_name(
                f"{self.paths.database.name}-journal"
            )
            if not journal.exists():
                atomic_write(
                    journal,
                    b"",
                    mode=0o600,
                    uid=friend_uid,
                    gid=friend_gid,
                )
            else:
                details = journal.lstat()
                if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                    raise ManagementError(
                        73,
                        "UNSAFE_COLLISION",
                        "Friend SQLite journal is not a regular file.",
                    )
                os.chown(journal, friend_uid, friend_gid)
                os.chmod(journal, 0o600)
            if database_preexisting and "workspaces_file" not in invocation.inputs:
                return database
            selected = {str(path) for path in workspaces}
            for record in database.list_workspaces():
                if record["canonical_root"] not in selected:
                    database.set_workspace_enabled(str(record["id"]), False)
            for workspace in workspaces:
                details = workspace.lstat()
                database.register_workspace(
                    canonical_root=str(workspace),
                    root_device=details.st_dev,
                    root_inode=details.st_ino,
                )
            return database

    @staticmethod
    def _systemd_quote(path: Path) -> str:
            value = str(path)
            if any(ord(character) < 32 for character in value):
                raise ManagementError(65, "INVALID_WORKSPACE", "Workspace path is invalid.")
            escaped = value.replace("\\", "\\\\").replace('"', '\\"')
            return f'"{escaped}"'

    def _deploy_unit(self, workspaces: list[Path]) -> None:
            template = (
                self.paths.install_root / "systemd" / "imaginary-friend-chat.service"
            ).read_text(encoding="utf-8")
            lines = "\n".join(
                f"ReadWritePaths={self._systemd_quote(path)}" for path in workspaces
            )
            rendered = template.replace("__FRIEND_WORKSPACE_PATHS__", lines)
            if "__FRIEND_" in rendered:
                raise ManagementError(78, "INVALID_UNIT", "Service template is incomplete.")
            atomic_write(self.paths.unit, rendered.encode("utf-8"), mode=0o644)
            logrotate = (
                self.paths.install_root / "logrotate" / "imaginary-friend"
            ).read_bytes()
            atomic_write(self.paths.logrotate, logrotate, mode=0o644)
            atomic_write(
                self.paths.entrypoint,
                (self.paths.install_root / "scripts" / "manage.sh").read_bytes(),
                mode=0o755,
            )
            atomic_write(
                self.paths.diagnostics,
                (self.paths.install_root / "bin" / "friend-diagnostics").read_bytes(),
                mode=0o755,
            )

    def _execute(
            self, invocation: Invocation, result: Result
    ) -> tuple[list[str], str | None]:
            operation = invocation.operation
            if operation == "install":
                return self._execute_install(invocation)
            if operation == "repair":
                return self._execute_repair(invocation)
            if operation == "backup":
                return self._execute_backup(invocation)
            if operation == "update":
                return self._execute_update(invocation)
            if operation == "rollback":
                return self._execute_rollback(invocation)
            if operation == "suspend":
                return self._execute_suspend()
            if operation == "resume":
                return self._execute_resume(invocation)
            if operation == "uninstall":
                return self._execute_uninstall(invocation)
            raise ManagementError(2, "INVALID_USAGE", f"Unsupported operation: {operation}")

    def _execute_install(self, invocation: Invocation) -> tuple[list[str], str | None]:
            self._platform_preflight()
            owner = str(
                invocation.inputs.get("owner_user")
                or self._owner_from_config()
                or ""
            )
            self._validate_owner(owner)
            self._collision_preflight()
            self._workspace_preflight(invocation.workspaces)
            self._probe_model(invocation)
            marker = self.load_marker()
            if (
                marker is not None
                and marker["version"] != self.version
                and invocation.operation != "update"
            ):
                raise ManagementError(
                    78,
                    "VERSION_MISMATCH",
                    "Installed Friend version differs; use update or rollback.",
                )
            preserve_rollback = (
                marker is not None and marker["version"] == self.version
            )
            recovery_source: Path | None = None
            if marker is not None:
                recovery_source = (
                    self.paths.operation_recovery
                    if preserve_rollback
                    else self.paths.recovery
                )
                self._snapshot_state(recovery_source)
            runtime_switched = False
            previous_version: str | None = None
            try:
                instance_id = self._ensure_transaction()
                friend_uid, share_gid = self._ensure_accounts(owner)
                friend_gid = grp.getgrnam("friend").gr_gid
                self._ensure_paths(
                    friend_uid=friend_uid,
                    friend_gid=friend_gid,
                    share_gid=share_gid,
                    workspaces=invocation.workspaces,
                )
                previous_version = self._stage_runtime(
                    preserve_rollback=preserve_rollback
                )
                runtime_switched = True
                self._deploy_configuration(
                    invocation,
                    owner_user=owner,
                    friend_gid=friend_gid,
                    workspaces=invocation.workspaces,
                )
                database = self._initialize_database(
                    invocation,
                    friend_uid=friend_uid,
                    friend_gid=friend_gid,
                    workspaces=invocation.workspaces,
                )
                suspended = bool(database.settings()["suspended"])
                self._deploy_unit(invocation.workspaces)
                self._validate_runtime_as_friend()
                if suspended:
                    self._stop_service(disable=False)
                else:
                    self._start_service()
                    if not self._service_health():
                        raise ManagementError(
                            1,
                            "HEALTH_FAILED",
                            "Friend service did not pass its loopback health gate.",
                            recovery=[
                                "Run friend-manage doctor and inspect redacted diagnostics."
                            ],
                        )
                checks = self.verify_checks(
                    probe_runtime=not suspended,
                    allow_transaction=marker is None,
                )
                failed = [item for item in checks if item["status"] == "fail"]
                if failed:
                    raise ManagementError(
                        1,
                        "BOUNDARY_CHECK_FAILED",
                        f"Post-install boundary check failed: {failed[0]['id']}",
                    )
                self._write_marker(instance_id, previous=marker)
                self.load_marker(required=True)
                self.paths.transaction.unlink(missing_ok=True)
                self._commit_runtime_switch()
            except Exception:
                self._restore_failed_switch(
                    runtime_switched=runtime_switched,
                    recovery_source=recovery_source,
                )
                if marker is None and self.paths.marker.exists():
                    self.paths.marker.unlink(missing_ok=True)
                raise
            if recovery_source == self.paths.operation_recovery:
                try:
                    shutil.rmtree(recovery_source)
                except OSError:
                    pass
            return (
                [
                    "friend",
                    "friend-share",
                    str(self.paths.install_root),
                    str(self.paths.configuration_root),
                    str(self.paths.state_root),
                    str(self.paths.log_root),
                    *(str(path) for path in invocation.workspaces),
                    str(self.paths.unit),
                    str(self.paths.entrypoint),
                ],
                previous_version,
            )

    def _execute_repair(self, invocation: Invocation) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            if marker["version"] != self.version:
                raise ManagementError(
                    78,
                    "VERSION_MISMATCH",
                    "Repair source must match the installed version; use update for a new version.",
                )
            owner = str(
                invocation.inputs.get("owner_user")
                or self._owner_from_config()
                or ""
            )
            self._validate_owner(owner)
            self._workspace_preflight(invocation.workspaces)
            recovery_source = self.paths.operation_recovery
            self._snapshot_state(recovery_source)
            runtime_switched = False
            previous_version: str | None = None
            try:
                friend_uid, share_gid = self._ensure_accounts(owner)
                friend_gid = grp.getgrnam("friend").gr_gid
                self._ensure_paths(
                    friend_uid=friend_uid,
                    friend_gid=friend_gid,
                    share_gid=share_gid,
                    workspaces=invocation.workspaces,
                )
                previous_version = self._stage_runtime(preserve_rollback=True)
                runtime_switched = True
                self._deploy_configuration(
                    invocation,
                    owner_user=owner,
                    friend_gid=friend_gid,
                    workspaces=invocation.workspaces,
                )
                database = self._initialize_database(
                    invocation,
                    friend_uid=friend_uid,
                    friend_gid=friend_gid,
                    workspaces=invocation.workspaces,
                )
                if invocation.inputs.get("owner_password_file"):
                    if invocation.password is None:
                        raise ManagementError(
                            65, "INVALID_SECRET", "Password input is missing."
                        )
                    database.rotate_password(hash_password(invocation.password))
                self._deploy_unit(invocation.workspaces)
                self._validate_runtime_as_friend()
                if not database.settings()["suspended"]:
                    self._start_service()
                    if not self._service_health():
                        raise ManagementError(
                            1, "HEALTH_FAILED", "Repaired Friend service is unhealthy."
                        )
                checks = self.verify_checks(
                    probe_runtime=not database.settings()["suspended"]
                )
                failed = [item for item in checks if item["status"] == "fail"]
                if failed:
                    raise ManagementError(
                        1, "REPAIR_FAILED", f"Repair check failed: {failed[0]['id']}"
                    )
                self._commit_runtime_switch()
            except Exception:
                self._restore_failed_switch(
                    runtime_switched=runtime_switched,
                    recovery_source=recovery_source,
                )
                raise
            try:
                shutil.rmtree(recovery_source)
            except OSError:
                pass
            return (
                [
                    str(self.paths.install_root),
                    str(self.paths.configuration_root),
                    str(self.paths.state_root),
                    str(self.paths.unit),
                ],
                previous_version,
            )

    def _execute_backup(self, invocation: Invocation) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            destination = Path(str(invocation.inputs["backup_destination"]))
            self._validate_backup_destination(destination, dry_run=False)
            archive = self._create_backup(destination)
            return [str(archive)], str(marker["version"])

    def _execute_update(self, invocation: Invocation) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            installed_version = str(marker["version"])
            if self._version_tuple(self.version) < self._version_tuple(installed_version):
                raise ManagementError(
                    78, "VERSION_DOWNGRADE", "Use rollback for an older Friend version."
                )
            self._platform_preflight()
            self._probe_model(invocation)
            if self.version == installed_version:
                return [], installed_version
            resources, previous = self._execute_install(invocation)
            return resources, previous or installed_version

    def _execute_rollback(self, invocation: Invocation) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            current_version = str(marker["version"])
            if not self.paths.rollback_root.is_dir():
                raise ManagementError(
                    66, "ROLLBACK_UNAVAILABLE", "No previous Friend runtime is available."
                )
            rollback_version_path = self.paths.rollback_root / "VERSION"
            try:
                rollback_version = validate_version(
                    rollback_version_path.read_text(encoding="utf-8").strip()
                )
            except OSError as exc:
                raise ManagementError(
                    78, "ROLLBACK_INVALID", "Previous Friend runtime is incomplete."
                ) from exc
            current_snapshot = self.paths.state_root / (
                f".rollback-current-{uuid.uuid4().hex}"
            )
            self._snapshot_state(current_snapshot)
            swapped = False
            try:
                self._stop_service(disable=False)
                self._swap_runtime_trees()
                swapped = True
                self._restore_recovery_state()
                database = Database(self.paths.database)
                database.require_ready()
                workspaces = [
                    Path(record["canonical_root"]) for record in database.list_workspaces()
                ]
                self._deploy_unit(workspaces)
                self._validate_runtime_as_friend()
                if not database.settings()["suspended"]:
                    self._start_service()
                    if not self._service_health():
                        raise ManagementError(
                            1,
                            "ROLLBACK_HEALTH_FAILED",
                            "Restored Friend release is unhealthy.",
                        )
                self.version = rollback_version
                restored_marker = self.load_marker(required=True)
                if (
                    restored_marker["instance_id"] != marker["instance_id"]
                    or restored_marker["version"] != rollback_version
                ):
                    raise ManagementError(
                        78,
                        "ROLLBACK_INVALID",
                        "Recovery state does not match the previous Friend runtime.",
                    )
                self._rotate_recovery_snapshot(current_snapshot)
            except Exception:
                self._stop_service(disable=False)
                recovered_current = False
                try:
                    if swapped:
                        self._swap_runtime_trees()
                    if current_snapshot.is_dir():
                        self._restore_state(current_snapshot)
                    self.version = current_version
                    database = Database(self.paths.database)
                    database.require_ready()
                    workspaces = [
                        Path(record["canonical_root"])
                        for record in database.list_workspaces()
                    ]
                    self._deploy_unit(workspaces)
                    if not database.settings()["suspended"]:
                        self._start_service()
                    recovered_current = True
                except Exception:
                    pass
                if recovered_current and current_snapshot.is_dir():
                    shutil.rmtree(current_snapshot)
                raise
            return (
                [str(self.paths.install_root), str(self.paths.database), str(self.paths.unit)],
                current_version,
            )

    def _execute_suspend(self) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            database = Database(self.paths.database)
            database.require_ready()
            database.set_suspended(True)
            self._stop_service(disable=False)
            return [str(self.paths.database), "imaginary-friend-chat.service"], str(marker["version"])

    def _execute_resume(self, invocation: Invocation) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            if not self._unit_has_required_sandbox():
                raise ManagementError(
                    78, "SANDBOX_INVALID", "Friend sandbox must be repaired before resume."
                )
            database = Database(self.paths.database)
            database.require_ready()
            try:
                share_gid = grp.getgrnam("friend-share").gr_gid
            except KeyError as exc:
                raise ManagementError(
                    78,
                    "WORKSPACE_SHARING_INVALID",
                    "Friend workspace sharing group is unavailable.",
                ) from exc
            for record in database.list_workspaces():
                details = validate_nominated_root(
                    Path(record["canonical_root"]),
                    allow_default=record["canonical_root"] == str(DEFAULT_WORKSPACE),
                )
                if (
                    details.st_dev != int(record["root_device"])
                    or details.st_ino != int(record["root_inode"])
                    or details.st_gid != share_gid
                    or stat.S_IMODE(details.st_mode) & 0o070 != 0o070
                    or not details.st_mode & stat.S_ISGID
                ):
                    raise ManagementError(
                        78,
                        "WORKSPACE_CHANGED",
                        "A workspace changed or lost its sharing boundary after nomination.",
                    )
            self._probe_model(invocation)
            self._validate_runtime_as_friend()
            database.set_suspended(False)
            self._start_service()
            if not self._service_health():
                database.set_suspended(True)
                self._stop_service(disable=False)
                raise ManagementError(1, "HEALTH_FAILED", "Friend failed its resume health gate.")
            return [str(self.paths.database), "imaginary-friend-chat.service"], str(marker["version"])

    def _execute_uninstall(
            self, invocation: Invocation
    ) -> tuple[list[str], str | None]:
            marker = self.load_marker(required=True)
            version = str(marker["version"])
            if self.paths.database.is_file():
                database = Database(self.paths.database)
                database.require_ready()
                database.set_suspended(True)
            self._stop_service(disable=True)
            removed: list[str] = []
            for path in (
                self.paths.unit,
                self.paths.logrotate,
                self.paths.entrypoint,
                self.paths.diagnostics,
            ):
                if path.exists():
                    self._unlink_owned_file(path)
                    removed.append(str(path))
            if self.paths.install_root.exists():
                self._remove_owned_tree(self.paths.install_root)
                removed.append(str(self.paths.install_root))
            if self.paths.rollback_root.exists():
                self._remove_owned_tree(self.paths.rollback_root)
                removed.append(str(self.paths.rollback_root))
            if self.paths.configuration_root.exists():
                self._remove_owned_tree(self.paths.configuration_root)
                removed.append(str(self.paths.configuration_root))
            self._run(["systemctl", "daemon-reload"], check=False, timeout=30)
            try:
                pwd.getpwnam("friend")
            except KeyError:
                pass
            else:
                self._run(["userdel", "friend"])
                removed.append("friend")
            if invocation.retain_state:
                atomic_write(
                    self.paths.state_root / "retained.json",
                    canonical_json(
                        {
                            "schema_version": 1,
                            "product_id": PRODUCT_ID,
                            "retained_at": utc_now(),
                        }
                    )
                    + b"\n",
                    mode=0o600,
                )
                self._chown_tree(self.paths.state_root, 0, 0)
                os.chmod(self.paths.state_root, 0o700)
            else:
                self._remove_owned_tree(self.paths.state_root)
                removed.append(str(self.paths.state_root))
            if self.paths.audit.exists():
                os.chown(self.paths.audit, 0, 0)
                os.chmod(self.paths.audit, 0o640)
            try:
                grp.getgrnam("friend")
            except KeyError:
                pass
            else:
                self._run(["groupdel", "friend"], check=False)
            return removed, version

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, ...]:
            validate_version(value)
            return tuple(int(part) for part in value.split("."))

    def _validate_runtime_as_friend(self) -> None:
            command = [
                "runuser",
                "-u",
                "friend",
                "--",
                "/usr/bin/env",
                f"PYTHONPATH={self.paths.install_root / 'agent'}",
                str(self.paths.install_root / "venv" / "bin" / "python"),
                "-m",
                "friend.server",
                "--config",
                str(self.paths.configuration_root / "config.json"),
                "--check",
            ]
            self._run(command, timeout=60)

    def _start_service(self) -> None:
            self._run(["systemctl", "daemon-reload"], timeout=30)
            self._run(
                ["systemctl", "enable", "--now", "imaginary-friend-chat.service"],
                timeout=60,
            )
            deadline = time.monotonic() + 15
            while time.monotonic() < deadline:
                if self._systemctl_is_active() and self._service_health():
                    return
                time.sleep(0.25)
            raise ManagementError(
                75,
                "SERVICE_TIMEOUT",
                "Friend service did not become healthy in time.",
                retryable=True,
            )

    def _stop_service(self, *, disable: bool) -> None:
            if shutil.which("systemctl") is None:
                return
            command = ["systemctl", "disable", "--now"] if disable else ["systemctl", "stop"]
            command.append("imaginary-friend-chat.service")
            self._run(command, check=False, timeout=60)

    def _write_marker(
            self, instance_id: str, *, previous: dict[str, Any] | None
    ) -> None:
            artifact = os.environ.get("IMAGINARY_FRIEND_ARTIFACT_SHA256")
            if artifact is not None and (
                len(artifact) != 64
                or any(character not in "0123456789abcdef" for character in artifact)
            ):
                raise ManagementError(78, "INVALID_ARTIFACT_DIGEST", "Artifact digest is invalid.")
            marker = {
                "schema_version": 1,
                "product_id": PRODUCT_ID,
                "instance_id": instance_id,
                "version": self.version,
                "source_revision": self._source_revision(),
                "installed_at": previous["installed_at"] if previous else utc_now(),
                "install_root": str(self.paths.install_root),
                "lifecycle_entrypoint": str(self.paths.entrypoint),
                "artifact_sha256": artifact,
            }
            atomic_write(
                self.paths.marker,
                canonical_json(marker) + b"\n",
                mode=0o644,
            )

    def _source_revision(self) -> str:
            completed = self._run(
                ["git", "-C", str(self.source_root), "rev-parse", "HEAD"],
                check=False,
                timeout=10,
            ) if shutil.which("git") else None
            if completed is not None:
                revision = completed.stdout.strip()
                if len(revision) == 40 and all(
                    character in "0123456789abcdef" for character in revision
                ):
                    return revision
            digest = hashlib.sha256()
            for path in sorted(self.source_root.rglob("*")):
                if (
                    not path.is_file()
                    or "__pycache__" in path.parts
                    or "dist" in path.parts
                ):
                    continue
                digest.update(str(path.relative_to(self.source_root)).encode("utf-8"))
                digest.update(b"\0")
                digest.update(path.read_bytes())
                digest.update(b"\0")
            return f"source-tree-sha256:{digest.hexdigest()}"

    def _snapshot_state(self, destination: Path) -> None:
            if destination.exists() or destination.is_symlink():
                details = destination.lstat()
                if (
                    not stat.S_ISDIR(details.st_mode)
                    or stat.S_ISLNK(details.st_mode)
                    or details.st_uid != 0
                ):
                    raise ManagementError(
                        73,
                        "UNSAFE_COLLISION",
                        "Recovery snapshot path is not a root-owned directory.",
                    )
            else:
                destination.mkdir(parents=True, mode=0o700)
            os.chown(destination, 0, 0)
            os.chmod(destination, 0o700)
            for child in destination.iterdir():
                if child.is_dir() and not child.is_symlink():
                    shutil.rmtree(child)
                else:
                    child.unlink()
            if self.paths.database.is_file():
                snapshot = destination / "friend.db"
                Database(self.paths.database).backup_to(snapshot)
                os.chown(snapshot, 0, 0)
                os.chmod(snapshot, 0o600)
            if self.paths.configuration_root.is_dir():
                self._copy_tree(
                    self.paths.configuration_root,
                    destination / "configuration",
                )
                self._root_own_tree(destination / "configuration")
            if self.paths.marker.is_file():
                shutil.copy2(self.paths.marker, destination / "installation.json")
                os.chown(destination / "installation.json", 0, 0)
            atomic_write(
                destination / "snapshot.json",
                canonical_json(
                    {
                        "schema_version": 1,
                        "product_id": PRODUCT_ID,
                        "created_at": utc_now(),
                    }
                )
                + b"\n",
                mode=0o600,
            )

    def _restore_recovery_state(self) -> None:
            self._restore_state(self.paths.recovery)

    def _restore_state(self, source: Path) -> None:
            metadata_path = source / "snapshot.json"
            check_secure_file(metadata_path, missing_code=78)
            metadata = read_json(metadata_path)
            if set(metadata) != {"schema_version", "product_id", "created_at"} or (
                metadata["schema_version"] != 1
                or metadata["product_id"] != PRODUCT_ID
                or not isinstance(metadata["created_at"], str)
            ):
                raise ManagementError(
                    78, "RECOVERY_INVALID", "Recovery snapshot metadata is invalid."
                )
            friend_uid = pwd.getpwnam("friend").pw_uid
            friend_gid = grp.getgrnam("friend").gr_gid
            snapshot = source / "friend.db"
            if snapshot.is_file():
                check_secure_file(snapshot, missing_code=78)
                atomic_write(
                    self.paths.database,
                    snapshot.read_bytes(),
                    mode=0o600,
                    uid=friend_uid,
                    gid=friend_gid,
                )
                journal = self.paths.database.with_name(
                    f"{self.paths.database.name}-journal"
                )
                if journal.exists() or journal.is_symlink():
                    details = journal.lstat()
                    if (
                        not stat.S_ISREG(details.st_mode)
                        or details.st_nlink != 1
                        or details.st_uid not in {0, friend_uid}
                    ):
                        raise ManagementError(
                            73,
                            "RECOVERY_BLOCKED",
                            "Friend SQLite journal cannot be replaced safely.",
                        )
                    journal.unlink()
                atomic_write(
                    journal,
                    b"",
                    mode=0o600,
                    uid=friend_uid,
                    gid=friend_gid,
                )
            configuration = source / "configuration"
            if configuration.is_dir():
                if self.paths.configuration_root.exists():
                    self._remove_owned_tree(self.paths.configuration_root)
                self._copy_tree(configuration, self.paths.configuration_root)
                self._root_own_tree(self.paths.configuration_root)
                os.chmod(self.paths.configuration_root, 0o750)
                key = self.paths.configuration_root / "session.key"
                if key.exists():
                    os.chown(key, 0, friend_gid)
                    os.chmod(key, 0o640)
            marker = source / "installation.json"
            if marker.is_file():
                details = marker.lstat()
                if (
                    not stat.S_ISREG(details.st_mode)
                    or details.st_nlink != 1
                    or details.st_uid != 0
                ):
                    raise ManagementError(
                        78, "RECOVERY_INVALID", "Recovery marker is invalid."
                    )
                atomic_write(
                    self.paths.marker,
                    marker.read_bytes(),
                    mode=0o644,
                )
                self.load_marker(required=True)

    def _restore_failed_switch(
            self,
            *,
            runtime_switched: bool,
            recovery_source: Path | None = None,
    ) -> None:
            self._stop_service(disable=False)
            failed = self.paths.install_root.parent / f".imaginary-friend-failed-{uuid.uuid4().hex}"
            try:
                if runtime_switched and (
                    self._transient_runtime is not None
                    and self._transient_runtime.is_dir()
                ):
                    if self.paths.install_root.exists():
                        os.rename(self.paths.install_root, failed)
                    os.rename(self._transient_runtime, self.paths.install_root)
                    self._transient_runtime = None
                    if failed.exists():
                        shutil.rmtree(failed)
                elif (
                    runtime_switched
                    and self._rollback_switch_active
                    and self.paths.rollback_root.is_dir()
                ):
                    if self.paths.install_root.exists():
                        os.rename(self.paths.install_root, failed)
                    os.rename(self.paths.rollback_root, self.paths.install_root)
                    self._rollback_switch_active = False
                    if failed.exists():
                        shutil.rmtree(failed)
                snapshot_root = recovery_source or self.paths.recovery
                if (snapshot_root / "snapshot.json").is_file():
                    self._restore_state(snapshot_root)
                if (
                    self.paths.install_root.is_dir()
                    and self.paths.database.is_file()
                    and self.paths.configuration_root.is_dir()
                ):
                    database = Database(self.paths.database)
                    database.require_ready()
                    workspaces = [
                        Path(record["canonical_root"])
                        for record in database.list_workspaces()
                    ]
                    self._deploy_unit(workspaces)
                    if not database.settings()["suspended"]:
                        self._start_service()
                if (
                    recovery_source == self.paths.operation_recovery
                    and recovery_source.is_dir()
                ):
                    shutil.rmtree(recovery_source)
            except Exception:
                # Preserve both trees and recovery data for an explicit doctor run.
                return

    def _swap_runtime_trees(self) -> None:
            for path in (self.paths.install_root, self.paths.rollback_root):
                details = path.lstat()
                if (
                    not stat.S_ISDIR(details.st_mode)
                    or stat.S_ISLNK(details.st_mode)
                    or details.st_uid != 0
                ):
                    raise ManagementError(
                        73,
                        "OWNERSHIP_MISMATCH",
                        f"Runtime tree is not product-controlled: {path}",
                    )
            temporary = self.paths.install_root.parent / (
                f".imaginary-friend-swap-{uuid.uuid4().hex}"
            )
            os.rename(self.paths.install_root, temporary)
            try:
                os.rename(self.paths.rollback_root, self.paths.install_root)
                try:
                    os.rename(temporary, self.paths.rollback_root)
                except Exception:
                    os.rename(self.paths.install_root, self.paths.rollback_root)
                    os.rename(temporary, self.paths.install_root)
                    raise
            except Exception:
                if temporary.exists() and not self.paths.install_root.exists():
                    os.rename(temporary, self.paths.install_root)
                raise

    def _rotate_recovery_snapshot(self, replacement: Path) -> None:
            consumed = self.paths.state_root / (
                f".recovery-consumed-{uuid.uuid4().hex}"
            )
            os.rename(self.paths.recovery, consumed)
            try:
                os.rename(replacement, self.paths.recovery)
            except Exception:
                os.rename(consumed, self.paths.recovery)
                raise
            try:
                shutil.rmtree(consumed)
            except OSError:
                # The active rollback is already committed. Doctor can remove
                # this root-only stale snapshot without weakening recovery.
                pass

    def _create_backup(self, destination: Path) -> Path:
            timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            archive = destination / (
                f"imaginary-friend-backup-{timestamp}-{uuid.uuid4().hex[:8]}.tar.gz"
            )
            with tempfile.TemporaryDirectory(prefix="imaginary-friend-backup-") as temporary:
                root = Path(temporary)
                state = root / "state"
                configuration = root / "configuration"
                state.mkdir(mode=0o700)
                configuration.mkdir(mode=0o700)
                Database(self.paths.database).backup_to(state / "friend.db")
                for name in ("config.json", "session.key", "PRODUCT.json", "policy.json"):
                    source = self.paths.configuration_root / name
                    if source.is_file():
                        shutil.copy2(source, configuration / name)
                shutil.copy2(self.paths.marker, root / "installation.json")
                manifest = {
                    "schema_version": 1,
                    "product_id": PRODUCT_ID,
                    "created_at": utc_now(),
                    "version": self.load_marker(required=True)["version"],
                    "contains_workspace_files": False,
                    "sessions_revoked_in_snapshot": True,
                    "encrypted": False,
                }
                (root / "backup.json").write_bytes(canonical_json(manifest) + b"\n")
                flags = (
                    os.O_WRONLY
                    | os.O_CREAT
                    | os.O_EXCL
                    | getattr(os, "O_NOFOLLOW", 0)
                )
                fd = os.open(archive, flags, 0o600)
                try:
                    with os.fdopen(fd, "wb", closefd=False) as file_object:
                        with tarfile.open(fileobj=file_object, mode="w:gz") as bundle:
                            for name in (
                                "backup.json",
                                "installation.json",
                                "configuration",
                                "state",
                            ):
                                bundle.add(root / name, arcname=name, recursive=True)
                    os.fchmod(fd, 0o600)
                    os.fsync(fd)
                finally:
                    os.close(fd)
            try:
                with tarfile.open(archive, mode="r:gz") as bundle:
                    names = set(bundle.getnames())
            except (OSError, tarfile.TarError) as exc:
                archive.unlink(missing_ok=True)
                raise ManagementError(1, "BACKUP_INVALID", "Backup verification failed.") from exc
            if (
                "backup.json" not in names
                or "state/friend.db" not in names
                or any("workspace" in name.lower() for name in names)
            ):
                archive.unlink(missing_ok=True)
                raise ManagementError(1, "BACKUP_INVALID", "Backup contents are invalid.")
            os.chmod(archive, 0o600)
            return archive

    @staticmethod
    def _unlink_owned_file(path: Path) -> None:
            details = path.lstat()
            if (
                not stat.S_ISREG(details.st_mode)
                or details.st_nlink != 1
                or details.st_uid != 0
            ):
                raise ManagementError(
                    73, "OWNERSHIP_MISMATCH", f"Refusing to remove unowned path: {path}"
                )
            path.unlink()

    @staticmethod
    def _remove_owned_tree(path: Path) -> None:
            details = path.lstat()
            if (
                not stat.S_ISDIR(details.st_mode)
                or stat.S_ISLNK(details.st_mode)
                or details.st_uid != 0
            ):
                raise ManagementError(
                    73, "OWNERSHIP_MISMATCH", f"Refusing to remove unowned tree: {path}"
                )
            shutil.rmtree(path)

    @staticmethod
    def _chown_tree(path: Path, uid: int, gid: int) -> None:
            for directory, names, files in os.walk(path, followlinks=False):
                os.chown(directory, uid, gid)
                for name in [*names, *files]:
                    child = Path(directory) / name
                    if child.is_symlink():
                        os.lchown(child, uid, gid)
                    else:
                        os.chown(child, uid, gid)

    def _write_receipt_and_audit(
            self,
            invocation: Invocation,
            result: Result,
            *,
            changed_resources: list[str],
            previous_version: str | None,
    ) -> None:
            self.paths.log_root.mkdir(parents=True, exist_ok=True)
            self.paths.receipts.mkdir(parents=True, exist_ok=True)
            os.chown(self.paths.receipts, 0, 0)
            os.chmod(self.paths.receipts, 0o750)
            event_id = str(uuid.uuid4())
            response = result.object()
            response["receipt"] = None
            receipt = {
                "schema_version": 1,
                "response": response,
                "installed_version": (
                    self.load_marker()["version"] if self.load_marker() else None
                ),
                "previous_version": previous_version,
                "changed_resources": changed_resources,
                "audit_event_id": event_id,
            }
            content = canonical_json(receipt) + b"\n"
            historical = self.paths.receipts / f"{invocation.correlation_id}.json"
            atomic_write(historical, content, mode=0o640)
            atomic_write(self.paths.receipt, content, mode=0o640)
            digest = sha256_bytes(content)
            result.receipt = {"path": str(self.paths.receipt), "digest": digest}
            self._append_lifecycle_audit(
                event_id=event_id,
                correlation_id=invocation.correlation_id,
                instance_id=result.instance_id,
                operation=invocation.operation,
                phase="execute",
                actor=invocation.actor,
                decision="allowed",
                outcome=result.status,
                changed=result.changed,
                receipt_digest=digest,
            )

    def _append_lifecycle_audit(
            self,
            *,
            event_id: str,
            correlation_id: str,
            instance_id: str | None,
            operation: str,
            phase: str,
            actor: str,
            decision: str,
            outcome: str,
            changed: bool,
            receipt_digest: str | None,
            failure_type: str | None = None,
    ) -> None:
            if not self.paths.log_root.exists():
                return
            entry = {
                "timestamp": utc_now(),
                "event_id": event_id,
                "correlation_id": correlation_id,
                "product_id": PRODUCT_ID,
                "instance_id": instance_id,
                "operation": operation,
                "phase": phase,
                "actor": actor,
                "decision": decision,
                "result": outcome,
                "changed": changed,
                "receipt_digest": receipt_digest,
            }
            if failure_type is not None:
                entry["failure_type"] = failure_type
            line = canonical_json(entry) + b"\n"
            flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
            fd = os.open(self.paths.audit, flags, 0o640)
            try:
                details = os.fstat(fd)
                if not stat.S_ISREG(details.st_mode) or details.st_nlink != 1:
                    raise ManagementError(73, "AUDIT_INVALID", "Audit log is not a regular file.")
                os.write(fd, line)
                os.fsync(fd)
                os.fchmod(fd, 0o640)
            finally:
                os.close(fd)

    def _audit_read(self, invocation: Invocation, result: Result) -> None:
            if not self.paths.audit.exists():
                return
            self._append_lifecycle_audit(
                event_id=str(uuid.uuid4()),
                correlation_id=invocation.correlation_id,
                instance_id=result.instance_id,
                operation=invocation.operation,
                phase="read",
                actor=invocation.actor,
                decision="allowed",
                outcome=result.status,
                changed=False,
                receipt_digest=None,
            )

    def audit_denial(
            self, invocation: Invocation | None, error: ManagementError
    ) -> None:
            if invocation is None or not self.paths.audit.exists():
                return
            try:
                self._append_lifecycle_audit(
                    event_id=str(uuid.uuid4()),
                    correlation_id=invocation.correlation_id,
                    instance_id=self.instance_id(),
                    operation=invocation.operation,
                    phase=_operation_phase(
                        invocation.operation,
                        dry_run=invocation.dry_run,
                    ),
                    actor=invocation.actor,
                    decision="denied",
                    outcome="blocked" if error.exit_code != 1 else "failed",
                    changed=False,
                    receipt_digest=None,
                )
            except Exception:
                return

    def audit_failure(self, invocation: Invocation, error: Exception) -> None:
            if not self.paths.audit.exists():
                return
            try:
                self._append_lifecycle_audit(
                    event_id=str(uuid.uuid4()),
                    correlation_id=invocation.correlation_id,
                    instance_id=self.instance_id(),
                    operation=invocation.operation,
                    phase=_operation_phase(
                        invocation.operation,
                        dry_run=invocation.dry_run,
                    ),
                    actor=invocation.actor,
                    decision="allowed",
                    outcome="failed",
                    changed=False,
                    receipt_digest=None,
                    failure_type=type(error).__name__,
                )
            except Exception:
                return


def parser() -> argparse.ArgumentParser:
    value = argparse.ArgumentParser(
            prog="friend-manage",
            description="Imaginary Friend product-owned lifecycle interface",
    )
    value.add_argument("operation", choices=OPERATIONS)
    value.add_argument(
            "--dry-run",
            action="store_true",
            help="render a mutation plan without locks, writes, or network requests",
    )
    value.add_argument(
            "--json",
            action="store_true",
            help="write exactly one lifecycle response object to stdout",
    )
    value.add_argument(
            "--non-interactive",
            action="store_true",
            help="never prompt; missing required input exits 64",
    )
    value.add_argument("--request-file", type=Path)
    value.add_argument("--correlation-id")
    value.add_argument("--plan-digest")
    value.add_argument(
            "--yes",
            action="store_true",
            help="accept a reviewed non-destructive plan",
    )
    return value


def print_plan(
    result: Result,
    *,
    configuration: dict[str, Any] | None,
    file: Any = None,
) -> None:
    def field_value(label: str, value: Any) -> None:
        print(f"  {label + ':':<22}{value}", file=file)

    print("Imaginary Friend lifecycle plan:", file=file)
    field_value("Operation", result.operation)
    if configuration is not None:
        field_value("Human owner", configuration["owner_user"])
        field_value("Model endpoint", configuration["model_base_url"])
        field_value("Model ID", configuration["model"])
        field_value(
            "History retention",
            f"{configuration['history_retention_days']} days",
        )
        field_value(
            "Audit retention",
            f"{configuration['audit_retention_days']} days",
        )
        field_value("Workspaces", ", ".join(configuration["workspaces"]))
    field_value("Local URL", "http://127.0.0.1:6767/")
    field_value("State", "/var/lib/imaginary-friend")
    field_value("Digest", result.plan_digest)
    for index, step in enumerate(result.steps, 1):
        print(f"  {index}. {step['summary']}", file=file)
    if result.operation == "install":
        print(
            "  A generated owner password is shown once after installation.",
            file=file,
        )


def _print_result(result: Result, *, as_json: bool) -> None:
    value = result.object()
    if as_json:
        sys.stdout.write(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n")
        return
    if result.phase == "plan" and result.plan_digest:
        configuration = None
        if result.details is not None:
            candidate = result.details.get("configuration")
            if isinstance(candidate, dict):
                configuration = candidate
        print_plan(result, configuration=configuration)
        return
    print(
        f"{result.operation}: {result.status} "
        f"(version {result.product_version}, correlation {result.correlation_id})"
    )
    if result.plan_digest:
        print(f"Plan: {result.plan_digest}")
    for check in result.checks:
        print(f"[{check['status']}] {check['id']}: {check['summary']}")
    for error in result.errors:
        print(f"ERROR {error['code']}: {error['message']}", file=sys.stderr)
    for guidance in result.recovery:
        print(f"Recovery: {guidance}", file=sys.stderr)
    if result.receipt:
        print(f"Receipt: {result.receipt['path']} ({result.receipt['digest']})")
    if result.operation == "install" and result.status == "ok":
        print("Open: http://127.0.0.1:6767/")


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    source = Path(
            os.environ.get(
                "IMAGINARY_FRIEND_SOURCE_ROOT",
                Path(__file__).resolve().parents[3],
            )
    )
    manager: Manager | None = None
    invocation: Invocation | None = None
    try:
            manager = Manager(source)
            invocation = manager.invocation(args)
            result, exit_code = manager.run(invocation)
    except ManagementError as exc:
            version = manager.version if manager is not None else "0000.00.00.00.00.00"
            correlation = (
                invocation.correlation_id
                if invocation is not None
                else args.correlation_id
                if args.correlation_id
                else str(uuid.uuid4())
            )
            try:
                validate_uuid(correlation, label="correlation_id")
            except ManagementError:
                correlation = str(uuid.uuid4())
            phase = _operation_phase(args.operation, dry_run=args.dry_run)
            result = Result(
                operation=args.operation,
                correlation_id=correlation,
                product_version=version,
                instance_id=manager.instance_id() if manager is not None else None,
                phase=phase,
                status="failed" if exc.exit_code == 1 else "blocked",
                changed=False,
                steps=manager.steps_for(args.operation) if manager is not None else [],
                errors=[
                    {
                        "code": exc.code,
                        "message": str(redact(exc.message)),
                        "retryable": exc.retryable,
                    }
                ],
                recovery=[str(redact(item)) for item in exc.recovery],
            )
            if exc.code in {"MISSING_INPUT", "CONFIRMATION_REQUIRED"}:
                secret = "password" in exc.message.lower()
                result.required_inputs = [{"name": exc.message, "secret": secret}]
                result.requires_confirmation = exc.code == "CONFIRMATION_REQUIRED"
            if manager is not None:
                manager.audit_denial(invocation, exc)
            exit_code = exc.exit_code
    except Exception as exc:
            version = manager.version if manager is not None else "0000.00.00.00.00.00"
            correlation = (
                invocation.correlation_id
                if invocation is not None
                else args.correlation_id
                if args.correlation_id
                else str(uuid.uuid4())
            )
            try:
                validate_uuid(correlation, label="correlation_id")
            except ManagementError:
                correlation = str(uuid.uuid4())
            instance_id = None
            if manager is not None:
                try:
                    instance_id = manager.instance_id()
                except Exception:
                    pass
            result = Result(
                operation=args.operation,
                correlation_id=correlation,
                product_version=version,
                instance_id=instance_id,
                phase=_operation_phase(args.operation, dry_run=args.dry_run),
                status="failed",
                steps=manager.steps_for(args.operation) if manager is not None else [],
                errors=[
                    {
                        "code": getattr(exc, "code", "OPERATION_FAILED"),
                        "message": "Imaginary Friend lifecycle validation failed.",
                        "retryable": False,
                    }
                ],
            )
            if manager is not None and invocation is not None:
                manager.audit_failure(invocation, exc)
            exit_code = 1
    _print_result(result, as_json=args.json)
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
