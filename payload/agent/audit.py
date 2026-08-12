"""Audit logging for Ubuntu AI System Administrator.

Every prompt, proposed action, approval decision, command, exit code,
and verification result is appended as one JSON object per line to
``/var/log/ubuntu-ai-system-administrator/audit.log``. Secrets are redacted before
write: the redactor matches token-shaped substrings and also scrubs
the values of a fixed set of sensitive environment variables and the
secrets-file path. Tool dispatches are recorded as structured
``tool_call`` events that include classification, decision, exit
code, duration, and SHA-256 digests of stdout/stderr.

Two environment variables tune verbosity (off by default, opt-in for
testing and debugging):

``AI_SYS_ADMIN_AUDIT_VERBOSE=1``
    Adds redacted ``stdout_preview`` / ``stderr_preview`` snippets to
    ``tool_call`` entries (capped to ``AI_SYS_ADMIN_AUDIT_PREVIEW_BYTES``,
    default 2048 bytes each). The SHA-256 digests still ship so the
    integrity contract is unchanged. The preview goes through the same
    secret redactor as every other field.

``AI_SYS_ADMIN_AUDIT_PREVIEW_BYTES=N``
    Override the per-stream preview cap (only honoured when
    ``AI_SYS_ADMIN_AUDIT_VERBOSE=1``). Hard ceiling is 16 KiB to keep the
    log bounded.

Every audit entry also carries ``ts_utc`` (ISO-8601 UTC) and ``pid``
so a tester can correlate lines across processes and journalctl
without parsing the local-time ``ts`` field.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import threading
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Mapping

AUDIT_PATH = Path(os.environ.get("AI_SYS_ADMIN_AUDIT_LOG", "/var/log/ubuntu-ai-system-administrator/audit.log"))

# Hard ceiling on preview length even when ``AI_SYS_ADMIN_AUDIT_PREVIEW_BYTES``
# is set higher — keeps the log bounded and matches the per-stream cap
# already enforced by ``runner.py``.
_MAX_PREVIEW_BYTES = 16_384
_DEFAULT_PREVIEW_BYTES = 2_048


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}


def _verbose() -> bool:
    """Re-read the env var each call so tests can flip the flag mid-run."""
    return _truthy(os.environ.get("AI_SYS_ADMIN_AUDIT_VERBOSE"))


def _preview_cap() -> int:
    raw = os.environ.get("AI_SYS_ADMIN_AUDIT_PREVIEW_BYTES")
    if not raw:
        return _DEFAULT_PREVIEW_BYTES
    try:
        n = int(raw)
    except ValueError:
        return _DEFAULT_PREVIEW_BYTES
    if n <= 0:
        return 0
    return min(n, _MAX_PREVIEW_BYTES)


def _preview(text: str, cap: int) -> str:
    """Trim ``text`` to ``cap`` bytes (UTF-8) with a truncation marker."""
    if cap <= 0 or not text:
        return ""
    encoded = text.encode("utf-8", "replace")
    if len(encoded) <= cap:
        return text
    truncated = encoded[:cap].decode("utf-8", "replace")
    return truncated + f"\n…[truncated {len(encoded) - cap} bytes]"

# Sensitive env-var names whose values must never appear in the audit
# log even outside their token-shaped substrings (e.g. an operator
# pasted a short token that does not match the ``sk-...`` pattern).
_SENSITIVE_ENV_NAMES = (
    "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY",
    "XAI_API_KEY", "OPENROUTER_API_KEY", "MISTRAL_API_KEY",
    "GROQ_API_KEY",
    "AI_SYS_ADMIN_SECRETS",
)


def _secrets_path_redactors() -> tuple[tuple[re.Pattern[str], str], ...]:
    install_root = Path(os.environ.get("AI_SYS_ADMIN_DIR", "/opt/ai-system-administrator"))
    paths = {
        os.environ.get("AI_SYS_ADMIN_SECRETS")
        or str(install_root / "secrets" / "env")
    }
    out: list[tuple[re.Pattern[str], str]] = []
    for p in paths:
        if not p:
            continue
        out.append((re.compile(re.escape(p)), "***SECRETS_PATH***"))
    return tuple(out)


def _sensitive_env_redactors() -> tuple[tuple[re.Pattern[str], str], ...]:
    return tuple(
        (re.compile(rf"\b{name}\s*[:=]\s*\S+"), f"{name}=***REDACTED***")
        for name in _SENSITIVE_ENV_NAMES
    )


# Token-shaped strings: provider keys, base64 blobs, ssh keys, etc.
_REDACTORS: tuple[tuple[re.Pattern[str], str], ...] = (
    # Order matters: the generic ``sk-`` pattern also matches
    # ``sk-ant-...`` keys, so the Anthropic-specific rule has to run
    # first or it would never fire.
    (re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}"), "sk-ant-***REDACTED***"),
    (re.compile(r"sk-[A-Za-z0-9_-]{12,}"), "sk-***REDACTED***"),
    (re.compile(r"tskey-[A-Za-z0-9_-]{12,}"), "tskey-***REDACTED***"),
    (re.compile(r"ssh-(rsa|ed25519|dss)\s+[A-Za-z0-9+/=]{20,}"), "ssh-*** REDACTED ***"),
    # FIX-3-11: capture the separator (``:`` or ``=``) so the
    # redacted line preserves the original syntax — otherwise
    # ``Authorization: ...`` gets rewritten to ``Authorization=...``
    # and audit-log greps for ``Authorization: Bearer`` find nothing.
    (re.compile(r"(?i)(api[_-]?key|token|password|secret)(\s*[:=]\s*)\S+"),
     r"\1\2***REDACTED***"),
    (re.compile(r"-----BEGIN [A-Z ]+PRIVATE KEY-----[\s\S]+?-----END [A-Z ]+PRIVATE KEY-----"),
     "***REDACTED PRIVATE KEY***"),
) + _sensitive_env_redactors() + _secrets_path_redactors()

_LOCK = threading.Lock()


def redact(value: Any) -> Any:
    """Redact token-shaped substrings from ``value`` recursively."""
    if isinstance(value, str):
        out = value
        for pattern, replacement in _REDACTORS:
            out = pattern.sub(replacement, out)
        return out
    if isinstance(value, Mapping):
        return {k: redact(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [redact(v) for v in value]
    return value


def _ensure_log() -> None:
    AUDIT_PATH.parent.mkdir(parents=True, exist_ok=True)
    if not AUDIT_PATH.exists():
        AUDIT_PATH.touch(mode=0o640)
    # FIX-3-15: ``Path.touch(mode=...)`` is masked by the process
    # umask, so a fresh file under a stock ``umask 022`` ends up at
    # 0o620 (group-writable but not readable). Force the intended mode
    # explicitly. Ownership is the operator's job (systemd ``User=``).
    try:
        os.chmod(AUDIT_PATH, 0o640)
    except OSError:
        # The log may be owned by another user (post-rotate). The
        # write below will fail with a clearer error if it really is
        # unwritable; do not raise from the permission tweak itself.
        pass


def log_event(event_type: str, **fields: Any) -> str:
    """Append one audit entry. Returns the entry's ``id``."""
    entry_id = uuid.uuid4().hex
    now = time.time()
    entry: dict[str, Any] = {
        "id": entry_id,
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S%z", time.localtime(now)),
        # FIX: always emit a UTC timestamp alongside the local-time
        # ``ts`` so testers correlating audit lines with journalctl
        # (UTC) do not have to do timezone math in their heads.
        "ts_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now)),
        # FIX: ``pid`` is cheap and lets a tester join audit lines
        # with ``journalctl _PID=...`` output for the chat service.
        "pid": os.getpid(),
        "type": event_type,
    }
    entry.update(redact(fields))
    line = json.dumps(entry, ensure_ascii=False, separators=(",", ":"))
    with _LOCK:
        _ensure_log()
        with AUDIT_PATH.open("a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    return entry_id


def log_tool_call(
    *,
    tool: str,
    classification: str,
    decision: str,
    args_summary: Mapping[str, Any] | None = None,
    exit_code: int | None = None,
    duration_ms: int | None = None,
    stdout: str | None = None,
    stderr: str | None = None,
    error: str | None = None,
    **extra: Any,
) -> str:
    """Append a ``tool_call`` audit entry.

    Stdout/stderr are recorded as length + SHA-256 digest so the audit
    log stays bounded and never persists tool output verbatim (per the
    Phase 2 plan §6 risk register, R5/R6).

    When ``AI_SYS_ADMIN_AUDIT_VERBOSE=1`` is set, a redacted preview of each
    stream (capped at ``AI_SYS_ADMIN_AUDIT_PREVIEW_BYTES``, default 2048) is
    additionally captured as ``stdout_preview`` / ``stderr_preview``.
    The digests still ship unchanged. Verbose mode is intended for
    pre-release testing and operator debugging; leave it off in
    production deployments where the audit log is the long-lived
    forensic trail.
    """
    fields: dict[str, Any] = {
        "tool": tool,
        "classification": classification,
        "decision": decision,
    }
    if args_summary is not None:
        fields["args"] = dict(args_summary)
    if exit_code is not None:
        fields["exit_code"] = exit_code
    if duration_ms is not None:
        fields["duration_ms"] = duration_ms
    if error is not None:
        fields["error"] = error
    verbose = _verbose()
    cap = _preview_cap() if verbose else 0
    if stdout is not None:
        fields["stdout_sha256"] = hashlib.sha256(stdout.encode("utf-8", "replace")).hexdigest()
        fields["stdout_bytes"] = len(stdout.encode("utf-8", "replace"))
        if verbose and cap > 0:
            # Redact before truncating: truncating first can split a
            # token at the byte cap so the remaining fragment is too
            # short for the redaction patterns to match, leaking a
            # partial secret into the preview.
            fields["stdout_preview"] = _preview(redact(stdout), cap)
    if stderr is not None:
        fields["stderr_sha256"] = hashlib.sha256(stderr.encode("utf-8", "replace")).hexdigest()
        fields["stderr_bytes"] = len(stderr.encode("utf-8", "replace"))
        if verbose and cap > 0:
            fields["stderr_preview"] = _preview(redact(stderr), cap)
    fields.update(extra)
    return log_event("tool_call", **fields)


def tail(n: int = 25) -> list[dict[str, Any]]:
    """Return up to ``n`` most recent audit entries as parsed dicts."""
    if not AUDIT_PATH.exists():
        return []
    # FIX-3-18: stream the file through a bounded ``deque`` rather than
    # slurping the whole thing into memory. The audit log can be tens
    # of MB on a busy machine and ``/api/audit`` hits this on every
    # page load.
    with AUDIT_PATH.open("r", encoding="utf-8", errors="replace") as fh:
        lines = list(deque(fh, maxlen=max(n, 0)))
    out: list[dict[str, Any]] = []
    for raw in lines:
        raw = raw.strip()
        if not raw:
            continue
        try:
            out.append(json.loads(raw))
        except json.JSONDecodeError:
            continue
    return out
