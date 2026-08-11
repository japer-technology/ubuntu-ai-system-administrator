"""Closed tool registry for the pi-mono runtime.

The chat service runs an explicit, code-controlled tool surface
instead of parsing and approving free-form shell. Every ``pi-mono``
tool call is dispatched through this module:

* :data:`TOOL_REGISTRY` lists the only tools the chat service will ever
  execute. Adding a tool requires a code release — skills cannot
  expand the tool surface.
* :func:`validate_args` runs a minimal, dependency-free schema check.
  Rejections are recorded as ``tool_call_rejected_schema`` audit events
  by the server before any side effects.
* :func:`dispatch` runs the registered shim. Shims wrap existing
  Beep helpers (``runner.run``, ``Path.read_text`` etc.) so
  the rest of the codebase keeps its existing invariants.

The shapes intentionally avoid pulling in jsonschema or pydantic;
operators install Beep on stock Ubuntu and the agent venv
should not gain third-party deps just to gate a dozen calls.
"""
from __future__ import annotations

import ipaddress
import os
import shlex
import socket
import subprocess
import urllib.error
import urllib.request
import json
from pathlib import Path
from typing import Any, Callable

from runner import run as run_command  # noqa: E402


# ---------------------------------------------------------------------------
# Schema validation (tiny, dependency-free)
# ---------------------------------------------------------------------------

class SchemaError(ValueError):
    """Raised when a tool call's ``args`` violate the registered schema."""


_PY_TO_JSON = {
    str: "string",
    int: "integer",
    float: "number",
    bool: "boolean",
    list: "array",
    dict: "object",
}


def _check_field(name: str, value: Any, spec: dict[str, Any]) -> None:
    expected = spec.get("type")
    if expected is None:
        return
    if expected == "string" and not isinstance(value, str):
        raise SchemaError(f"{name}: expected string, got {type(value).__name__}")
    if expected == "integer" and (
        isinstance(value, bool) or not isinstance(value, int)
    ):
        # ``bool`` is a subclass of ``int`` in Python; reject it explicitly so
        # callers cannot smuggle ``True``/``False`` into integer fields such
        # as ``shell.run`` ``timeout`` (which would otherwise be coerced to
        # ``0`` and immediately fire ``TimeoutExpired``).
        raise SchemaError(f"{name}: expected integer, got {type(value).__name__}")
    if expected == "number" and (
        isinstance(value, bool) or not isinstance(value, (int, float))
    ):
        raise SchemaError(f"{name}: expected number, got {type(value).__name__}")
    if expected == "boolean" and not isinstance(value, bool):
        raise SchemaError(f"{name}: expected boolean, got {type(value).__name__}")
    if expected == "array":
        if not isinstance(value, list):
            raise SchemaError(f"{name}: expected array, got {type(value).__name__}")
        items = spec.get("items")
        if isinstance(items, dict):
            for i, item in enumerate(value):
                _check_field(f"{name}[{i}]", item, items)
    if expected == "object":
        if not isinstance(value, dict):
            raise SchemaError(f"{name}: expected object, got {type(value).__name__}")
    enum = spec.get("enum")
    if enum is not None and value not in enum:
        raise SchemaError(f"{name}: value {value!r} not in {enum!r}")


def validate_args(name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    """Return a sanitized ``args`` dict or raise :class:`SchemaError`."""
    spec = TOOL_REGISTRY.get(name)
    if spec is None:
        raise SchemaError(f"unknown tool: {name!r}")
    args = dict(args or {})
    schema = spec.get("schema", {})
    required = schema.get("required", ())
    properties = schema.get("properties", {})
    additional = schema.get("additionalProperties", False)
    for key in required:
        if key not in args:
            raise SchemaError(f"{name}: missing required field {key!r}")
    for key, value in args.items():
        if key not in properties:
            if additional:
                continue
            raise SchemaError(f"{name}: unexpected field {key!r}")
        _check_field(key, value, properties[key])
    return args


# ---------------------------------------------------------------------------
# Path allow-list helpers
# ---------------------------------------------------------------------------

def _state_dir() -> Path:
    return Path("/var/lib/beep/runtime")


def _read_allowed_prefixes() -> tuple[Path, ...]:
    return (
        _state_dir(),
        Path("/etc"),
        Path("/var/log"),
        Path("/proc"),
        Path("/sys"),
        Path("/usr/share"),
        # Ubuntu ships several canonical inspection files under /etc as
        # symlinks into these read-only distro/runtime trees
        # (``/etc/os-release`` -> ``/usr/lib/os-release``,
        # ``/etc/localtime`` -> ``/usr/share/zoneinfo/...``,
        # ``/etc/resolv.conf`` -> ``/run/systemd/resolve/...``). The
        # allow-list is checked against the *resolved* path, so these
        # roots must be listed or the most common read-only lookups fail.
        Path("/usr/lib"),
        Path("/run/systemd"),
    )


def _write_allowed_prefixes() -> tuple[Path, ...]:
    return (_state_dir(), Path("/tmp"))


def _denied_read(resolved: Path) -> bool:
    """Reject reads that would hand process secrets back to the model.

    ``/proc`` is on the read allow-list (inspection files such as
    ``/proc/meminfo``), but ``/proc/<pid>/environ`` exposes the chat
    service's own environment — including provider API keys loaded from
    the secrets file. ``fs.read`` is auto-approved ``read_only``, so this
    has to be blocked here rather than at the policy gate.
    """
    parts = resolved.parts
    return (
        len(parts) >= 4
        and parts[1] == "proc"
        and parts[3] == "environ"
    )


def _resolve_within(target: Path, roots: tuple[Path, ...]) -> Path | None:
    """Return the symlink-resolved path when it lives under ``roots``.

    Callers must operate on the *returned* path: performing I/O on the
    unresolved path would re-traverse the symlinks that were just
    validated, so a link swapped after the check could escape the
    allow-list.
    """
    try:
        resolved = target.expanduser().resolve()
    except OSError:
        return None
    for root in roots:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except (OSError, ValueError):
            continue
    return None


def _within(target: Path, roots: tuple[Path, ...]) -> bool:
    return _resolve_within(target, roots) is not None


# ---------------------------------------------------------------------------
# Tool shims
# ---------------------------------------------------------------------------

def _valid_pkg_name(name: str) -> bool:
    # A leading ``-`` would be parsed as an option by apt-get/dpkg even
    # after ``shlex.quote`` (quoting stops shell metacharacters, not
    # option parsing), so reject it in addition to the ``--`` guard the
    # callers pass.
    if not name or name.startswith("-"):
        return False
    return name.replace("-", "").replace("+", "").replace(".", "").isalnum()


def _valid_unit_name(unit: str) -> bool:
    if not unit or unit.startswith("-"):
        return False
    return all(c.isalnum() or c in "._@-" for c in unit)


def _shim_shell_run(args: dict[str, Any]) -> dict[str, Any]:
    argv = args.get("argv")
    if isinstance(argv, list) and argv:
        command = " ".join(shlex.quote(str(a)) for a in argv)
    else:
        command = str(args.get("command", ""))
    if not command.strip():
        raise SchemaError("shell.run: argv or command must be non-empty")
    timeout = int(args.get("timeout") or 0) or None
    cwd = args.get("cwd")
    if cwd is not None:
        cwd_path = _resolve_within(
            Path(str(cwd)).expanduser(), _write_allowed_prefixes())
        if cwd_path is None:
            raise SchemaError(f"shell.run: cwd {cwd!r} outside writable allow-list")
        cwd = str(cwd_path)
    kwargs: dict[str, Any] = {}
    if timeout:
        kwargs["timeout"] = timeout
    if cwd:
        kwargs["cwd"] = cwd
    res = run_command(command, **kwargs)
    return {
        "exit_code": res.exit_code,
        "stdout": res.stdout,
        "stderr": res.stderr,
        "duration_ms": res.duration_ms,
        "follow_up": res.follow_up,
    }


def _shim_fs_read(args: dict[str, Any]) -> dict[str, Any]:
    raw = Path(str(args["path"])).expanduser()
    path = _resolve_within(raw, _read_allowed_prefixes())
    if path is None:
        raise SchemaError(f"fs.read: {raw} outside readable allow-list")
    if _denied_read(path):
        raise SchemaError(f"fs.read: {raw} is denied (process environment)")
    max_bytes = int(args.get("max_bytes") or 65536)
    data = path.read_bytes()
    truncated = len(data) > max_bytes
    body = data[:max_bytes].decode("utf-8", errors="replace")
    return {"path": str(path), "content": body, "bytes": len(data),
            "truncated": truncated}


def _shim_fs_list(args: dict[str, Any]) -> dict[str, Any]:
    raw = Path(str(args["path"])).expanduser()
    path = _resolve_within(raw, _read_allowed_prefixes())
    if path is None:
        raise SchemaError(f"fs.list: {raw} outside readable allow-list")
    if not path.is_dir():
        raise SchemaError(f"fs.list: {path} is not a directory")
    max_entries = int(args.get("max_entries") or 1000)
    if max_entries < 1:
        raise SchemaError("fs.list: max_entries must be positive")
    entries: list[dict[str, Any]] = []
    names = sorted(p.name for p in path.iterdir())
    truncated = len(names) > max_entries
    for name in names[:max_entries]:
        child = path / name
        try:
            st = child.lstat()
        except OSError:
            continue
        if child.is_symlink():
            kind = "symlink"
        elif child.is_dir():
            kind = "dir"
        elif child.is_file():
            kind = "file"
        else:
            kind = "other"
        entries.append({"name": name, "type": kind, "bytes": st.st_size})
    return {"path": str(path), "entries": entries, "count": len(names),
            "truncated": truncated}


def _shim_fs_write(args: dict[str, Any]) -> dict[str, Any]:
    raw = Path(str(args["path"])).expanduser()
    path = _resolve_within(raw, _write_allowed_prefixes())
    if path is None:
        raise SchemaError(f"fs.write: {raw} outside writable allow-list")
    content = str(args["content"])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return {"path": str(path), "bytes": len(content.encode("utf-8"))}


def _shim_pkg_query(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args["name"])
    if not _valid_pkg_name(name):
        raise SchemaError(f"pkg.query: invalid package name {name!r}")
    res = run_command(
        f"dpkg -s -- {shlex.quote(name)} 2>&1 "
        f"|| apt-cache policy -- {shlex.quote(name)}"
    )
    return {"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr}


def _shim_pkg_install(args: dict[str, Any]) -> dict[str, Any]:
    names = args.get("names") or []
    if not isinstance(names, list) or not names:
        raise SchemaError("pkg.install: names must be a non-empty array")
    for n in names:
        if not isinstance(n, str) or not _valid_pkg_name(n):
            raise SchemaError(f"pkg.install: invalid package name {n!r}")
    cmd = "sudo apt-get install -y -- " + " ".join(shlex.quote(n) for n in names)
    res = run_command(cmd)
    return {"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr,
            "duration_ms": res.duration_ms}


def _shim_svc_status(args: dict[str, Any]) -> dict[str, Any]:
    unit = str(args["unit"])
    if not _valid_unit_name(unit):
        raise SchemaError(f"svc.status: invalid unit {unit!r}")
    res = run_command(
        f"systemctl status --no-pager -- {shlex.quote(unit)} "
        f"|| systemctl is-active -- {shlex.quote(unit)}"
    )
    return {"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr}


def _shim_svc_control(args: dict[str, Any]) -> dict[str, Any]:
    action = str(args["action"])
    if action not in {"start", "stop", "restart", "reload", "enable", "disable"}:
        raise SchemaError(f"svc.control: invalid action {action!r}")
    unit = str(args["unit"])
    if not _valid_unit_name(unit):
        raise SchemaError(f"svc.control: invalid unit {unit!r}")
    res = run_command(f"sudo systemctl {action} -- {shlex.quote(unit)}")
    return {"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr}


def _shim_net_status(args: dict[str, Any]) -> dict[str, Any]:
    target = str(args.get("target") or "all")
    if target == "ip":
        cmd = "ip -brief addr"
    else:
        cmd = "ip -brief addr; ss -ltn"
    res = run_command(cmd)
    return {"exit_code": res.exit_code, "stdout": res.stdout, "stderr": res.stderr}


def _skills_dirs() -> list[Path]:
    dirs = [
        Path("/opt/beep/skills"),
        Path("/etc/beep/skills.d"),
    ]
    # Honour ``BEEP_SKILLS_DIR`` only when it is a non-empty value. An
    # empty string would otherwise become ``Path("")``/``Path(".")`` and
    # silently add the chat service's working directory to the skills
    # search path, bypassing the root-owned trees above.
    extra = os.environ.get("BEEP_SKILLS_DIR", "").strip()
    if extra:
        dirs.append(Path(extra))
    return dirs


def _shim_skill_list(_args: dict[str, Any]) -> dict[str, Any]:
    skills: list[dict[str, str]] = []
    for d in _skills_dirs():
        if not d or not d.is_dir():
            continue
        for path in sorted(d.glob("*.md")):
            skills.append({"name": path.stem, "path": str(path)})
    return {"skills": skills}


def _shim_skill_load(args: dict[str, Any]) -> dict[str, Any]:
    name = str(args["name"])
    if not name.replace("-", "").replace("_", "").isalnum():
        raise SchemaError(f"skill.load: invalid skill name {name!r}")
    for d in _skills_dirs():
        if not d or not d.is_dir():
            continue
        candidate = d / f"{name}.md"
        if candidate.is_file():
            return {"name": name, "path": str(candidate),
                    "content": candidate.read_text(encoding="utf-8", errors="replace")}
    raise SchemaError(f"skill.load: skill {name!r} not found")


# ---------------------------------------------------------------------------
# Read-only web access
# ---------------------------------------------------------------------------

# Byte caps for ``web.fetch``. The default keeps a page cheap in context;
# the maximum stops a large download from filling the transcript.
WEB_FETCH_DEFAULT_BYTES = 64 * 1024
WEB_FETCH_MAX_BYTES = 1024 * 1024
WEB_FETCH_TIMEOUT_SECONDS = 20
WEB_FETCH_MAX_REDIRECTS = 5
WEB_FETCH_USER_AGENT = "beep/web.fetch (+read-only)"


def _assert_public_url(url: str) -> str:
    """Validate ``url`` for outbound read-only fetching.

    Rejects anything that is not plain ``http``/``https``, URLs carrying
    embedded credentials, and hosts that resolve to a non-global address.
    The last check is the SSRF guard: without it ``web.fetch`` — which is
    ``read_only`` and therefore auto-approved — could read the loopback
    chat service, LAN devices, or a cloud metadata endpoint such as
    ``169.254.169.254``. DNS is re-resolved by the HTTP client after this
    check, so a hostile resolver can still rebind; the guard is a
    meaningful barrier, not a proof.
    """
    from urllib.parse import urlsplit

    try:
        parts = urlsplit(url)
    except ValueError as exc:
        raise SchemaError(f"web.fetch: invalid URL: {exc}") from exc
    if parts.scheme not in ("http", "https"):
        raise SchemaError(
            f"web.fetch: only http/https URLs are allowed, got {parts.scheme!r}"
        )
    if parts.username or parts.password:
        raise SchemaError("web.fetch: URLs with embedded credentials are refused")
    host = parts.hostname
    if not host:
        raise SchemaError("web.fetch: URL has no host")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    try:
        infos = socket.getaddrinfo(host, port, proto=socket.IPPROTO_TCP)
    except (OSError, ValueError) as exc:
        raise SchemaError(f"web.fetch: cannot resolve {host!r}: {exc}") from exc
    for info in infos:
        address = info[4][0]
        try:
            ip = ipaddress.ip_address(address)
        except ValueError:
            raise SchemaError(f"web.fetch: unusable address for {host!r}")
        if not ip.is_global:
            raise SchemaError(
                f"web.fetch: {host!r} resolves to the non-public address "
                f"{address}; local and private targets are refused"
            )
    return url


class _GuardedRedirectHandler(urllib.request.HTTPRedirectHandler):
    """Re-validate every redirect target against :func:`_assert_public_url`."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        _assert_public_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _shim_web_fetch(args: dict[str, Any]) -> dict[str, Any]:
    url = _assert_public_url(str(args["url"]))
    method = str(args.get("method") or "GET").upper()
    if method not in ("GET", "HEAD"):
        raise SchemaError(f"web.fetch: method {method!r} is not allowed")
    max_bytes = int(args.get("max_bytes") or WEB_FETCH_DEFAULT_BYTES)
    if max_bytes <= 0:
        raise SchemaError("web.fetch: max_bytes must be positive")
    max_bytes = min(max_bytes, WEB_FETCH_MAX_BYTES)

    request = urllib.request.Request(
        url,
        method=method,
        headers={"User-Agent": WEB_FETCH_USER_AGENT, "Accept": "*/*"},
    )
    opener = urllib.request.build_opener(_GuardedRedirectHandler)
    opener.addheaders = []
    try:
        with opener.open(request, timeout=WEB_FETCH_TIMEOUT_SECONDS) as response:
            status = int(getattr(response, "status", 0) or 0)
            final_url = response.geturl()
            content_type = response.headers.get("Content-Type", "")
            raw = b"" if method == "HEAD" else response.read(max_bytes + 1)
    except urllib.error.HTTPError as exc:
        # An error status is an answer, not a tool failure: report it so
        # the model can say "that page returned 404" instead of retrying.
        body = exc.read(max_bytes + 1) if exc.fp is not None else b""
        truncated = len(body) > max_bytes
        return {
            "url": url,
            "final_url": exc.url or url,
            "status": int(exc.code),
            "content_type": exc.headers.get("Content-Type", "") if exc.headers else "",
            "bytes": len(body[:max_bytes]),
            "truncated": truncated,
            "body": body[:max_bytes].decode("utf-8", errors="replace"),
        }
    except (urllib.error.URLError, OSError, ValueError) as exc:
        raise SchemaError(f"web.fetch: request failed: {exc}") from exc

    truncated = len(raw) > max_bytes
    body = raw[:max_bytes]
    return {
        "url": url,
        "final_url": final_url,
        "status": status,
        "content_type": content_type,
        "bytes": len(body),
        "truncated": truncated,
        "body": body.decode("utf-8", errors="replace"),
    }


def _shim_timer_reactivation(_args: dict[str, Any]) -> dict[str, Any]:
    raise SchemaError(
        "timer.reactivation requires an active conversation runtime"
    )


def _agent_cli(arguments: list[str], *, timeout: int) -> dict[str, Any]:
    """Invoke Beep's fixed family CLI and return its bounded JSON response."""

    if isinstance(timeout, bool) or not 1 <= timeout <= 3600:
        raise SchemaError("agent tool timeout must be between 1 and 3600 seconds")
    command = [
        "sudo",
        "-n",
        "/opt/beep/bin/beep-agents",
        "--json",
        *arguments,
    ]
    try:
        completed = subprocess.run(
            command,
            check=False,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            env={
                "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
                "HOME": "/var/lib/beep",
                "LANG": "C.UTF-8",
            },
        )
    except subprocess.TimeoutExpired as exc:
        raise SchemaError("agent manager timed out") from exc
    if len(completed.stdout) > 2 * 1024 * 1024:
        raise SchemaError("agent manager response exceeded its size limit")
    try:
        value = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise SchemaError("agent manager returned an invalid response") from exc
    if not isinstance(value, dict):
        raise SchemaError("agent manager response must be an object")
    if completed.returncode != 0:
        value["manager_exit_code"] = completed.returncode
    return value


def _agent_timeout(args: dict[str, Any], default: int) -> int:
    value = args.get("timeout", default)
    if isinstance(value, bool) or not isinstance(value, int):
        raise SchemaError("agent tool timeout must be an integer")
    return value


def _shim_agent_list(args: dict[str, Any]) -> dict[str, Any]:
    return _agent_cli(["list"], timeout=_agent_timeout(args, 60))


def _shim_agent_status(args: dict[str, Any]) -> dict[str, Any]:
    return _agent_cli(
        ["status", str(args["product_id"])],
        timeout=_agent_timeout(args, 60),
    )


def _shim_agent_plan(args: dict[str, Any]) -> dict[str, Any]:
    command = [
        "plan",
        str(args["product_id"]),
        str(args["operation"]),
    ]
    if "retain_state" in args:
        command.extend(["--retain-state", "yes" if args["retain_state"] else "no"])
    return _agent_cli(command, timeout=_agent_timeout(args, 1800))


def _shim_agent_manage(args: dict[str, Any]) -> dict[str, Any]:
    command = [
        "manage",
        str(args["product_id"]),
        str(args["operation"]),
        "--correlation-id",
        str(args["correlation_id"]),
        "--plan-digest",
        str(args["plan_digest"]),
    ]
    if "retain_state" in args:
        command.extend(["--retain-state", "yes" if args["retain_state"] else "no"])
    if "confirmation" in args:
        command.extend(["--confirmation", str(args["confirmation"])])
    return _agent_cli(command, timeout=_agent_timeout(args, 1800))


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

ToolShim = Callable[[dict[str, Any]], dict[str, Any]]


def _t(*, classification: str, schema: dict[str, Any], shim: ToolShim,
       description: str) -> dict[str, Any]:
    return {"classification": classification, "schema": schema, "shim": shim,
            "description": description}


TOOL_REGISTRY: dict[str, dict[str, Any]] = {
    "shell.run": _t(
        classification="system_change",  # actual class computed per-argv in classify_tool
        description="Run a shell command through the existing runner.",
        schema={
            "type": "object",
            "properties": {
                "argv": {"type": "array", "items": {"type": "string"}},
                "command": {"type": "string"},
                "cwd": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": [],
            "additionalProperties": False,
        },
        shim=_shim_shell_run,
    ),
    "fs.read": _t(
        classification="read_only",
        description="Read a UTF-8 text file within the readable allow-list.",
        schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_bytes": {"type": "integer"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        shim=_shim_fs_read,
    ),
    "fs.list": _t(
        classification="read_only",
        description="List directory entries within the readable allow-list.",
        schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "max_entries": {"type": "integer"},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
        shim=_shim_fs_list,
    ),
    "fs.write": _t(
        classification="user_change",
        description="Write text content to a path within the writable allow-list.",
        schema={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
        shim=_shim_fs_write,
    ),
    "pkg.query": _t(
        classification="read_only",
        description="Query installed package metadata via dpkg/apt-cache.",
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        shim=_shim_pkg_query,
    ),
    "pkg.install": _t(
        classification="system_change",
        description="Install Debian packages via apt-get.",
        schema={
            "type": "object",
            "properties": {"names": {"type": "array", "items": {"type": "string"}}},
            "required": ["names"],
            "additionalProperties": False,
        },
        shim=_shim_pkg_install,
    ),
    "svc.status": _t(
        classification="read_only",
        description="Inspect a systemd unit (status / is-active).",
        schema={
            "type": "object",
            "properties": {"unit": {"type": "string"}},
            "required": ["unit"],
            "additionalProperties": False,
        },
        shim=_shim_svc_status,
    ),
    "svc.control": _t(
        classification="system_change",
        description="Start/stop/restart/reload/enable/disable a systemd unit.",
        schema={
            "type": "object",
            "properties": {
                "unit": {"type": "string"},
                "action": {
                    "type": "string",
                    "enum": ["start", "stop", "restart", "reload", "enable", "disable"],
                },
            },
            "required": ["unit", "action"],
            "additionalProperties": False,
        },
        shim=_shim_svc_control,
    ),
    "net.status": _t(
        classification="read_only",
        description="Read-only interface and listening-port inspection.",
        schema={
            "type": "object",
            "properties": {
                "target": {"type": "string", "enum": ["all", "ip"]},
            },
            "required": [],
            "additionalProperties": False,
        },
        shim=_shim_net_status,
    ),
    "skill.list": _t(
        classification="read_only",
        description="Enumerate available skills from /opt/beep/skills and /etc/beep/skills.d.",
        schema={"type": "object", "properties": {}, "required": [],
                "additionalProperties": False},
        shim=_shim_skill_list,
    ),
    "skill.load": _t(
        classification="read_only",
        description="Read the markdown body of a skill by name.",
        schema={
            "type": "object",
            "properties": {"name": {"type": "string"}},
            "required": ["name"],
            "additionalProperties": False,
        },
        shim=_shim_skill_load,
    ),
    "web.fetch": _t(
        classification="read_only",
        description=(
            "Fetch a public http/https URL read-only and return its status "
            "and a truncated body."
        ),
        schema={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "method": {"type": "string", "enum": ["GET", "HEAD"]},
                "max_bytes": {"type": "integer"},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        shim=_shim_web_fetch,
    ),
    "timer.reactivation": _t(
        classification="chat_schedule",
        description=(
            "Schedule one bounded, visible continuation in the current conversation."
        ),
        schema={
            "type": "object",
            "properties": {
                "delay_seconds": {"type": "integer"},
                "prompt": {"type": "string"},
                "reason": {"type": "string"},
                "replace_existing": {"type": "boolean"},
            },
            "required": ["delay_seconds", "prompt"],
            "additionalProperties": False,
        },
        shim=_shim_timer_reactivation,
    ),
    "agent.list": _t(
        classification="read_only",
        description="List releases admitted to Beep's validated family catalogue.",
        schema={
            "type": "object",
            "properties": {"timeout": {"type": "integer"}},
            "required": [],
            "additionalProperties": False,
        },
        shim=_shim_agent_list,
    ),
    "agent.status": _t(
        classification="read_only",
        description="Read one admitted product's validated lifecycle status.",
        schema={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "enum": [
                        "imaginary-friend",
                        "curriculum-flame",
                        "eric",
                        "llama",
                    ],
                },
                "timeout": {"type": "integer"},
            },
            "required": ["product_id"],
            "additionalProperties": False,
        },
        shim=_shim_agent_status,
    ),
    "agent.plan": _t(
        classification="read_only",
        description="Render one admitted target's dry-run lifecycle plan.",
        schema={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "enum": [
                        "imaginary-friend",
                        "curriculum-flame",
                        "eric",
                        "llama",
                    ],
                },
                "operation": {
                    "type": "string",
                    "enum": [
                        "install",
                        "repair",
                        "backup",
                        "update",
                        "rollback",
                        "suspend",
                        "resume",
                        "uninstall",
                    ],
                },
                "retain_state": {"type": "boolean"},
                "timeout": {"type": "integer"},
            },
            "required": ["product_id", "operation"],
            "additionalProperties": False,
        },
        shim=_shim_agent_plan,
    ),
    "agent.manage": _t(
        classification="system_change",
        description="Execute one exact approved target lifecycle plan.",
        schema={
            "type": "object",
            "properties": {
                "product_id": {
                    "type": "string",
                    "enum": [
                        "imaginary-friend",
                        "curriculum-flame",
                        "eric",
                        "llama",
                    ],
                },
                "operation": {
                    "type": "string",
                    "enum": [
                        "install",
                        "repair",
                        "backup",
                        "update",
                        "rollback",
                        "suspend",
                        "resume",
                        "uninstall",
                    ],
                },
                "correlation_id": {"type": "string"},
                "plan_digest": {"type": "string"},
                "retain_state": {"type": "boolean"},
                "confirmation": {"type": "string"},
                "timeout": {"type": "integer"},
            },
            "required": [
                "product_id",
                "operation",
                "correlation_id",
                "plan_digest",
            ],
            "additionalProperties": False,
        },
        shim=_shim_agent_manage,
    ),
}


def tool_names() -> tuple[str, ...]:
    return tuple(TOOL_REGISTRY.keys())


def dispatch(name: str, args: dict[str, Any] | None) -> dict[str, Any]:
    """Validate and execute a tool. Raises :class:`SchemaError` on bad input."""
    cleaned = validate_args(name, args)
    spec = TOOL_REGISTRY[name]
    return spec["shim"](cleaned)


# Silence unused-import warnings when imported by smoke tests that
# never call subprocess directly.
_ = subprocess
