"""pytest fixtures shared across tests/python/.

The Python agent code lives under ``payload/agent/`` (not a real package).
Adding that directory to ``sys.path`` once here lets every test ``import
policy``, ``import tools``, etc. without per-test boilerplate.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
AGENT_DIR = ROOT / "payload" / "agent"
POLICY_FILE = ROOT / "payload" / "etc" / "policy.yaml"

sys.path.insert(0, str(AGENT_DIR))


@pytest.fixture(autouse=True)
def _zombie_policy_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Point the policy loader at the in-tree YAML so tests don't need
    /etc/ubuntu-zombie/policy.yaml on the filesystem.
    """
    monkeypatch.setenv("ZOMBIE_POLICY", str(POLICY_FILE))
    # Ensure no stale audit log path leaks from a previous test.
    monkeypatch.delenv("ZOMBIE_AUDIT_LOG", raising=False)
    monkeypatch.delenv("ZOMBIE_AUDIT_VERBOSE", raising=False)


@pytest.fixture
def policy_module():
    """Return the live ``policy`` module."""
    import policy  # noqa: WPS433 (intentional late import)

    return policy


@pytest.fixture
def tools_module():
    """Return the live ``tools`` module."""
    import tools  # noqa: WPS433

    return tools
