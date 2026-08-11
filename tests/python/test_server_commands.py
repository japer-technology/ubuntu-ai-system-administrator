"""Tests for slash-command support data exposed by ``server.py``."""

from __future__ import annotations

import importlib
import json


class _FakeRFile:
    def read(self, *_args: object, **_kwargs: object) -> bytes:
        return b""

    def readline(self, *_args: object, **_kwargs: object) -> bytes:
        return b""


class _Recorder:
    def __init__(self, app, path: str) -> None:
        self.app = app
        self.path = path
        self.rfile = _FakeRFile()
        self.headers = {}
        self.status = None
        self.body = b""

    def send_response(self, code: int, message: object = None) -> None:  # noqa: ARG002
        self.status = code

    def send_header(self, *_args, **_kwargs) -> None:
        return

    def end_headers(self) -> None:
        return

    def send_error(self, code, *_args, **_kwargs) -> None:
        self.status = int(code)

    class _W:
        def __init__(self, outer: "_Recorder") -> None:
            self._outer = outer

        def write(self, data: bytes) -> None:
            self._outer.body += data

    @property
    def wfile(self) -> "_Recorder._W":
        return _Recorder._W(self)


def _get(server_mod, app, path: str) -> tuple[int, dict]:
    handler = type("_TestHandler", (_Recorder, server_mod.Handler), {})
    record = handler(app, path)
    record.do_GET()
    body = json.loads(record.body.decode("utf-8")) if record.body else {}
    return record.status, body


def test_whoami_is_provider_independent(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("ZOMBIE_HISTORY_DB", str(tmp_path / "conversations.db"))
    monkeypatch.setenv("ZOMBIE_AUDIT_LOG", str(tmp_path / "audit.log"))
    monkeypatch.setenv("ZOMBIE_PROVIDER", "bogus")

    import history as history_mod
    import server as server_mod

    importlib.reload(history_mod)
    server_mod = importlib.reload(server_mod)
    app = server_mod.App()
    try:
        whoami = app.whoami_info()
        assert whoami["agent_user"]
        assert whoami["hostname"]
        assert whoami["chat_url"].startswith("http://127.0.0.1:")
        assert whoami["loopback_only"] is True

        profile = app.profile_info()
        assert profile["zombie_dir"] == "/opt/ai-zombie"
        assert profile["history_db"] == str(tmp_path / "conversations.db")

        status, body = _get(server_mod, app, "/api/whoami")
        assert status == 200
        assert body == whoami
    finally:
        app.history.close()
