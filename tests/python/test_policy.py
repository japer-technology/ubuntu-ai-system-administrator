"""Regression tests for ``payload/agent/policy.py``.

These mirror the inline Python block in ``tests/smoke.sh python`` but
read better in failure output and run individually via ``pytest -k``.
"""

from __future__ import annotations

import pytest


CLASSIFICATION_CASES = {
    "grep needle file > out": "user_change",
    "cat <<EOF > /tmp/out\nhello\nEOF": "user_change",
    "cat <<EOF\nhello\nEOF": "read_only",
    "cat script.sh | bash": "system_change",
    "cat data | sudo tee /etc/example": "system_change",
    "cat data | tee /dev/stderr": "read_only",
    "grep needle file 2>&1 >/dev/null": "read_only",
    "find /tmp -name x -delete": "destructive",
    "LC_ALL=C ls /etc": "read_only",
    "FOO=bar apt-get install pkg": "system_change",
    "sudo apt install foo": "system_change",
    "sudo -u zombie ls /tmp": "read_only",
    "sudo -E systemctl restart cron": "system_change",
    'rm -rf "/tmp/some file"': "destructive",
    # Unknown commands hit the fail-closed default.
    "foozle --bar": "destructive",
    "sudo foozle --bar": "destructive",
    "echo a && echo b": "destructive",
}


@pytest.mark.parametrize(("command", "want"), list(CLASSIFICATION_CASES.items()))
def test_classify_matches_expected(policy_module, command: str, want: str) -> None:
    p = policy_module.load_policy()
    got = p.classify(command)
    assert got == want, f"classify({command!r}) = {got!r}, want {want!r}"


def test_sudo_allow_list_invariants(policy_module) -> None:
    p = policy_module.load_policy()
    assert "apt" in p.sudo_allow_list
    assert "foozle" not in p.sudo_allow_list


def test_fail_closed_default(policy_module) -> None:
    p = policy_module.load_policy()
    assert p.default_class == "destructive"
    assert p.requires_approval(p.classify("foozle --bar"))


def test_extract_commands_removed() -> None:
    """The legacy fenced-bash extraction path must stay gone."""
    import server

    assert not hasattr(server, "extract_commands")


def test_tool_registry_is_closed(tools_module) -> None:
    expected = {
        "shell.run", "fs.read", "fs.list", "fs.write",
        "pkg.query", "pkg.install",
        "svc.status", "svc.control",
        "net.status",
        "skill.list", "skill.load",
    }
    assert set(tools_module.tool_names()) == expected


@pytest.mark.parametrize(
    ("tool", "args", "want"),
    [
        ("fs.read", {"path": "/etc/os-release"}, "read_only"),
        ("fs.list", {"path": "/etc"}, "read_only"),
        ("pkg.install", {"names": ["curl"]}, "system_change"),
        ("svc.control", {"unit": "cron", "action": "restart"}, "system_change"),
        ("shell.run", {"argv": ["ls", "-la"]}, "read_only"),
        ("shell.run", {"command": "sudo apt-get install -y curl"}, "system_change"),
    ],
)
def test_classify_tool(policy_module, tool, args, want) -> None:
    p = policy_module.load_policy()
    assert p.classify_tool(tool, args) == want


def test_unknown_tool_requires_approval(policy_module) -> None:
    p = policy_module.load_policy()
    assert p.requires_approval(p.classify_tool("totally.unknown", {}))


def test_schema_validation_rejects_bad_args(tools_module) -> None:
    with pytest.raises(tools_module.SchemaError):
        tools_module.validate_args("fs.read", {"path": 12})
