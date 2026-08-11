"""Audit log round-trip tests mirroring ``tests/smoke.sh python``."""

from __future__ import annotations

import json
from pathlib import Path


def _read_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def test_default_mode_redacts_and_carries_metadata(tmp_path, monkeypatch) -> None:
    audit_path = tmp_path / "audit.log"
    monkeypatch.setenv("ZOMBIE_AUDIT_LOG", str(audit_path))

    # Force a re-import so the module picks up the patched env var.
    import importlib

    import audit as audit_mod

    importlib.reload(audit_mod)

    audit_mod.log_event("prompt", prompt="hello sk-abcdefghijklmnop world")
    audit_mod.log_tool_call(
        tool="shell.run",
        classification="read_only",
        decision="executed",
        stdout="line1\nAPI_KEY=secretsesame\nline2",
        stderr="boom",
        exit_code=0,
        duration_ms=12,
    )

    entries = _read_jsonl(audit_path)
    assert len(entries) == 2

    for entry in entries:
        assert "pid" in entry
        assert "ts_utc" in entry
        flat = json.dumps(entry)
        assert "secretsesame" not in flat
        assert "sk-abcdefghijklmnop" not in flat

    tool_entry = entries[1]
    assert "stdout_preview" not in tool_entry
    assert "stderr_preview" not in tool_entry


def test_verbose_mode_attaches_redacted_previews(tmp_path, monkeypatch) -> None:
    audit_path = tmp_path / "audit.log"
    monkeypatch.setenv("ZOMBIE_AUDIT_LOG", str(audit_path))
    monkeypatch.setenv("ZOMBIE_AUDIT_VERBOSE", "1")

    import importlib

    import audit as audit_mod

    importlib.reload(audit_mod)

    audit_mod.log_tool_call(
        tool="shell.run",
        classification="read_only",
        decision="executed",
        stdout="visible\nAPI_KEY=secretsesame\nbye",
        stderr="ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQ secret",
        exit_code=0,
        duration_ms=8,
    )

    entry = _read_jsonl(audit_path)[0]
    assert "stdout_preview" in entry
    assert "stderr_preview" in entry
    flat = json.dumps(entry)
    assert "secretsesame" not in flat
    assert "AAAAB3NzaC1yc2EAAAADAQABAAABAQ" not in flat
