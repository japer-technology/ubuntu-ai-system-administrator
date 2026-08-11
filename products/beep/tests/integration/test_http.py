from __future__ import annotations

import http.client
import json
import os
import tempfile
import threading
import unittest
from pathlib import Path
from typing import Any
from unittest import mock

import lifecycle
import server


class StubApp:
    def __init__(self) -> None:
        self.messages: list[str] = []

    def login(self, password: str) -> dict[str, Any] | None:
        if password == "correct horse battery staple":
            return {"ok": True, "token": "session-token"}
        return None

    def logout(self, token: str | None) -> None:
        return

    def session_valid(self, token: str | None) -> bool:
        return True

    def post_message(
        self,
        conversation_id: int | None,
        prompt: str,
    ) -> dict[str, Any]:
        self.messages.append(prompt)
        return {"ok": True, "conversation_id": conversation_id or 1}

    def export_conversation(self, conversation_id: int) -> dict[str, Any]:
        if conversation_id != 1:
            raise KeyError
        return {
            "schema_version": 1,
            "product_id": "beep",
            "conversation": {"id": conversation_id},
            "messages": [],
            "events": [],
        }

    def delete_conversation(
        self,
        conversation_id: int,
        confirmation: str,
    ) -> dict[str, Any]:
        expected = f"DELETE CONVERSATION {conversation_id}"
        if confirmation != expected:
            return {"error": f"confirmation must be exactly {expected!r}"}
        return {"ok": True, "conversation_id": conversation_id}


class HTTPBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.lifecycle_path = Path(self.temporary.name) / "lifecycle.json"
        self.environment = mock.patch.dict(
            os.environ,
            {"BEEP_LIFECYCLE_STATE": str(self.lifecycle_path)},
        )
        self.environment.start()
        lifecycle.initialize(1)
        self.app = StubApp()
        self.httpd = server.ThreadingHTTPServer(
            ("127.0.0.1", 0),
            server.make_handler(self.app),
        )
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.httpd.server_port
        self.origin = f"http://127.0.0.1:{self.port}"

    def tearDown(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        self.thread.join(timeout=5)
        self.environment.stop()
        self.temporary.cleanup()

    def request(
        self,
        method: str,
        path: str,
        body: bytes = b"",
        *,
        headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any], http.client.HTTPMessage]:
        supplied = dict(headers or {})
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=5)
        connection.request(method, path, body=body, headers=supplied)
        response = connection.getresponse()
        payload = json.loads(response.read().decode("utf-8"))
        result = (response.status, payload, response.headers)
        connection.close()
        return result

    def json_post(
        self,
        path: str,
        value: bytes,
        *,
        origin: str | None = None,
        extra_headers: dict[str, str] | None = None,
    ) -> tuple[int, dict[str, Any], http.client.HTTPMessage]:
        headers = {
            "Content-Type": "application/json",
            "Origin": self.origin if origin is None else origin,
        }
        headers.update(extra_headers or {})
        return self.request("POST", path, value, headers=headers)

    def test_cross_origin_mutation_is_rejected(self) -> None:
        status, payload, _ = self.json_post(
            "/api/login",
            b'{"password":"correct horse battery staple"}',
            origin="https://attacker.invalid",
        )
        self.assertEqual(status, 403)
        self.assertIn("same origin", payload["error"])

    def test_invalid_host_is_rejected(self) -> None:
        status, payload, _ = self.request(
            "GET",
            "/api/session",
            headers={"Host": "attacker.invalid"},
        )
        self.assertEqual(status, 400)
        self.assertIn("loopback", payload["error"])

    def test_body_boundaries_and_strict_json(self) -> None:
        cases = (
            (
                {"Content-Type": "text/plain", "Origin": self.origin},
                b"{}",
                415,
            ),
            (
                {
                    "Content-Type": "application/json",
                    "Content-Length": "invalid",
                    "Origin": self.origin,
                },
                b"{}",
                400,
            ),
            (
                {
                    "Content-Type": "application/json",
                    "Content-Length": str(server.MAX_REQUEST_BYTES + 1),
                    "Origin": self.origin,
                },
                b"",
                413,
            ),
            (
                {"Content-Type": "application/json", "Origin": self.origin},
                b'{"password":"a","password":"b"}',
                400,
            ),
            (
                {"Content-Type": "application/json", "Origin": self.origin},
                b"[]",
                400,
            ),
        )
        for headers, body, expected in cases:
            with self.subTest(expected=expected, body=body):
                status, _, _ = self.request(
                    "POST",
                    "/api/login",
                    body,
                    headers=headers,
                )
                self.assertEqual(status, expected)

    def test_valid_login_sets_strict_cookie(self) -> None:
        status, payload, headers = self.json_post(
            "/api/login",
            b'{"password":"correct horse battery staple"}',
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])
        cookie = headers["Set-Cookie"]
        self.assertIn("HttpOnly", cookie)
        self.assertIn("SameSite=Strict", cookie)

    def test_malformed_message_fields_return_400(self) -> None:
        status, payload, _ = self.json_post(
            "/api/message",
            b'{"prompt":42}',
        )
        self.assertEqual(status, 400)
        self.assertEqual(payload["error"], "prompt must be a string")
        status, _, _ = self.json_post(
            "/api/message",
            b'{"prompt":"hello","unexpected":true}',
        )
        self.assertEqual(status, 400)

    def test_missing_lifecycle_state_blocks_mutation(self) -> None:
        self.lifecycle_path.unlink()
        status, payload, _ = self.json_post(
            "/api/message",
            b'{"prompt":"hello"}',
        )
        self.assertEqual(status, 410)
        self.assertTrue(payload["dead"])
        self.assertEqual(payload["dead_reason"], "state_missing")

    def test_conversation_export_and_explicit_deletion(self) -> None:
        status, payload, headers = self.request(
            "GET",
            "/api/conversation/1/export",
        )
        self.assertEqual(status, 200)
        self.assertEqual(payload["product_id"], "beep")
        self.assertIn("attachment", headers["Content-Disposition"])

        status, _, _ = self.json_post(
            "/api/conversation/1/delete",
            b'{"confirmation":"wrong"}',
        )
        self.assertEqual(status, 400)
        status, payload, _ = self.json_post(
            "/api/conversation/1/delete",
            b'{"confirmation":"DELETE CONVERSATION 1"}',
        )
        self.assertEqual(status, 200)
        self.assertTrue(payload["ok"])


if __name__ == "__main__":
    unittest.main()
