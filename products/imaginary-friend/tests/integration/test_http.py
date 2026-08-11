from __future__ import annotations

import http.client
import json
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "fixtures"))

from openai_fixture import Fixture  # noqa: E402

from friend.application import Config, FriendApplication
from friend.auth import hash_password
from friend.database import Database
from friend.server import FriendHTTPServer


class HTTPTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        root = Path(self.temporary.name)
        self.workspace = root / "workspace"
        self.workspace.mkdir()
        self.workspace.chmod(0o2770)
        key = root / "session.key"
        key.write_bytes(b"s" * 32)
        database = Database(root / "friend.db")
        self.model = Fixture()
        self.model.__enter__()
        database.initialize(
            password_hash=hash_password("initial owner password"),
            model_base_url=self.model.base_url,
            model="fixture-friend",
            history_retention_days=30,
            audit_retention_days=90,
        )
        details = self.workspace.stat()
        self.workspace_id = database.register_workspace(
            canonical_root=str(self.workspace),
            root_device=details.st_dev,
            root_inode=details.st_ino,
        )
        with mock.patch("friend.application.grp.getgrnam") as share_group:
            share_group.return_value.gr_gid = self.workspace.stat().st_gid
            app = FriendApplication(
                Config(
                    owner_user="owner",
                    port=6767,
                    database_path=root / "friend.db",
                    audit_path=root / "audit.log",
                    signing_key_path=key,
                    allowed_workspaces=(self.workspace,),
                )
            )
        self.server = FriendHTTPServer(("127.0.0.1", 0), app)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.origin = f"http://127.0.0.1:{self.port}"
        self.cookie = ""
        self.csrf = ""

    def tearDown(self) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)
        self.model.__exit__(None, None, None)
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        body: dict[str, Any] | None = None,
        *,
        origin: str | None = None,
    ) -> tuple[int, dict[str, Any], list[tuple[str, str]]]:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        headers = {
            "Host": f"127.0.0.1:{self.port}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"
            headers["Origin"] = self.origin if origin is None else origin
        if self.cookie:
            headers["Cookie"] = self.cookie
        if self.csrf and method not in {"GET", "HEAD"}:
            headers["X-Friend-CSRF"] = self.csrf
        payload = None if body is None else json.dumps(body)
        connection.request(method, path, body=payload, headers=headers)
        response = connection.getresponse()
        raw = response.read()
        response_headers = response.getheaders()
        connection.close()
        return response.status, json.loads(raw), response_headers

    def login(self) -> None:
        status, value, headers = self.request(
            "POST", "/api/login", {"password": "initial owner password"}
        )
        self.assertEqual(status, 200)
        self.csrf = value["csrf_token"]
        cookie = next(value for name, value in headers if name.lower() == "set-cookie")
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)
        self.assertNotIn("Domain=", cookie)
        self.cookie = cookie.split(";", 1)[0]

    def test_authenticated_chat_workspace_and_export_routes(self) -> None:
        self.login()
        status, written, _ = self.request(
            "PUT",
            f"/api/workspaces/{self.workspace_id}/write",
            {
                "path": "note.txt",
                "content": "workspace text",
                "expected_sha256": None,
                "confirmation": None,
            },
        )
        self.assertEqual(status, 200)
        self.assertTrue(written["created"])
        status, read, _ = self.request(
            "GET",
            f"/api/workspaces/{self.workspace_id}/read?path=note.txt",
        )
        self.assertEqual(status, 200)
        self.assertEqual(read["content"], "workspace text")
        status, chat, _ = self.request(
            "POST",
            "/api/chat",
            {
                "message": "hello",
                "conversation_id": None,
                "selected_files": [
                    {"workspace_id": self.workspace_id, "path": "note.txt"}
                ],
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(chat["message"], "A private fixture reply.")
        status, exported, _ = self.request("GET", "/api/conversations/export")
        self.assertEqual(status, 200)
        serialized = json.dumps(exported)
        self.assertNotIn("token_digest", serialized)
        self.assertNotIn("workspace text", serialized)

    def test_same_origin_and_csrf_are_required(self) -> None:
        status, _, _ = self.request(
            "POST",
            "/api/login",
            {"password": "initial owner password"},
            origin="http://attacker.invalid",
        )
        self.assertEqual(status, 403)
        self.login()
        saved = self.csrf
        self.csrf = ""
        status, _, _ = self.request("POST", "/api/logout", {})
        self.assertEqual(status, 403)
        self.csrf = saved
        status, _, _ = self.request("POST", "/api/logout", {})
        self.assertEqual(status, 200)

    def test_host_header_is_pinned_to_loopback_origin(self) -> None:
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request("GET", "/healthz", headers={"Host": "attacker.invalid"})
        response = connection.getresponse()
        self.assertEqual(response.status, 400)
        response.read()
        connection.close()

    def test_server_socket_supports_prompt_service_restarts(self) -> None:
        self.assertTrue(FriendHTTPServer.allow_reuse_address)


if __name__ == "__main__":
    unittest.main()
