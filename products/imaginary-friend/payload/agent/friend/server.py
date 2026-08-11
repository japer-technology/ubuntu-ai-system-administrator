"""Loopback-only HTTP surface for the authenticated Friend owner."""

from __future__ import annotations

import argparse
import json
import secrets
import signal
import sys
from http import HTTPStatus
from http.cookies import SimpleCookie
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any, cast
from urllib.parse import parse_qs, urlsplit

from . import COOKIE_NAME, SESSION_LIFETIME_SECONDS
from .application import FriendApplication, load_config
from .errors import AuthenticationError, FriendError, NotFoundError, ValidationError

MAX_REQUEST_BYTES = 1_048_576
STATIC_PATH = Path(__file__).with_name("static") / "index.html"


class FriendHTTPServer(ThreadingHTTPServer):
    daemon_threads = True
    allow_reuse_address = True

    def __init__(
        self, address: tuple[str, int], application: FriendApplication
    ) -> None:
        super().__init__(address, FriendHandler)
        self.application = application


class FriendHandler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"
    server_version = "ImaginaryFriend"
    sys_version = ""

    @property
    def app(self) -> FriendApplication:
        return cast(FriendHTTPServer, self.server).application

    def version_string(self) -> str:
        return "ImaginaryFriend"

    def log_message(self, format: str, *args: Any) -> None:
        # The default log includes attacker-controlled paths. Operational
        # events use the structured, redacted product audit instead.
        return

    def _host(self) -> str:
        host = self.headers.get("Host", "")
        port = cast(FriendHTTPServer, self.server).server_port
        allowed = {f"127.0.0.1:{port}", f"localhost:{port}"}
        if host not in allowed:
            raise ValidationError("Host header is not the Friend loopback origin.")
        return host

    def _same_origin(self) -> None:
        host = self._host()
        origin = self.headers.get("Origin")
        if origin != f"http://{host}":
            raise FriendError(
                "ORIGIN_DENIED",
                "State-changing requests require the Friend same origin.",
                status=403,
            )

    def _cookie_token(self) -> str:
        raw = self.headers.get("Cookie", "")
        cookie = SimpleCookie()
        try:
            cookie.load(raw)
        except Exception as exc:
            raise AuthenticationError() from exc
        morsel = cookie.get(COOKIE_NAME)
        return morsel.value if morsel is not None else ""

    def _require_session(self) -> str:
        token = self._cookie_token()
        self.app.require_session(token)
        return token

    def _require_mutation(self) -> str:
        self._same_origin()
        token = self._cookie_token()
        self.app.require_csrf(token, self.headers.get("X-Friend-CSRF", ""))
        return token

    def _body(self) -> dict[str, Any]:
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip()
        if content_type != "application/json":
            raise ValidationError("Request Content-Type must be application/json.")
        if self.headers.get("Transfer-Encoding"):
            raise ValidationError("Chunked request bodies are not accepted.")
        try:
            length = int(self.headers.get("Content-Length", ""))
        except ValueError as exc:
            raise ValidationError("Request Content-Length is invalid.") from exc
        if length <= 0 or length > MAX_REQUEST_BYTES:
            raise ValidationError("Request body is empty or too large.")
        raw = self.rfile.read(length)
        if len(raw) != length:
            raise ValidationError("Request body was incomplete.")
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Request body is not valid UTF-8 JSON.") from exc
        if not isinstance(value, dict):
            raise ValidationError("Request body must be one JSON object.")
        return value

    @staticmethod
    def _only(value: dict[str, Any], allowed: set[str]) -> None:
        unknown = set(value) - allowed
        if unknown:
            raise ValidationError(f"Unknown request field: {sorted(unknown)[0]}")

    def _send_headers(
        self,
        status: int,
        length: int,
        *,
        content_type: str = "application/json; charset=utf-8",
        extra: dict[str, str] | None = None,
        csp_nonce: str | None = None,
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(length))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        if csp_nonce:
            self.send_header(
                "Content-Security-Policy",
                "default-src 'none'; "
                f"script-src 'nonce-{csp_nonce}'; "
                "style-src 'unsafe-inline'; "
                "img-src 'self' data:; connect-src 'self'; "
                "base-uri 'none'; form-action 'self'; frame-ancestors 'none'",
            )
        else:
            self.send_header("Content-Security-Policy", "default-src 'none'")
        for name, value in (extra or {}).items():
            self.send_header(name, value)
        self.end_headers()

    def _json(
        self,
        value: Any,
        *,
        status: int = 200,
        extra: dict[str, str] | None = None,
    ) -> None:
        payload = json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        self._send_headers(status, len(payload), extra=extra)
        self.wfile.write(payload)

    def _error(self, error: Exception) -> None:
        if isinstance(error, FriendError):
            status = error.status
            code = error.code
            message = error.message
        else:
            status = 500
            code = "INTERNAL_ERROR"
            message = "Imaginary Friend could not complete the request."
        self._json(
            {"error": {"code": code, "message": message}},
            status=status,
        )

    @staticmethod
    def _cookie_header(token: str, *, expire: bool = False) -> str:
        if expire:
            return (
                f"{COOKIE_NAME}=; Path=/; HttpOnly; SameSite=Strict; "
                "Max-Age=0"
            )
        return (
            f"{COOKIE_NAME}={token}; Path=/; HttpOnly; SameSite=Strict; "
            f"Max-Age={SESSION_LIFETIME_SECONDS}"
        )

    def _serve_index(self) -> None:
        nonce = secrets.token_urlsafe(18)
        try:
            html = STATIC_PATH.read_text(encoding="utf-8").replace(
                "__CSP_NONCE__", nonce
            )
        except OSError:
            raise NotFoundError("Friend web interface is unavailable.") from None
        payload = html.encode("utf-8")
        self._send_headers(
            200,
            len(payload),
            content_type="text/html; charset=utf-8",
            csp_nonce=nonce,
        )
        self.wfile.write(payload)

    def do_GET(self) -> None:
        try:
            self._dispatch_get()
        except Exception as exc:
            self._error(exc)

    def _dispatch_get(self) -> None:
        self._host()
        parsed = urlsplit(self.path)
        path = parsed.path
        if path == "/":
            self._serve_index()
            return
        if path == "/healthz":
            self._json({"ok": True, "product_id": "imaginary-friend"})
            return
        token = self._require_session()
        if path == "/api/session":
            csrf = self.app.refresh_csrf(token)
            self._json(
                {
                    "authenticated": True,
                    "owner_user": self.app.config.owner_user,
                    "csrf_token": csrf,
                }
            )
            return
        if path == "/api/conversations":
            self._json({"conversations": self.app.conversations()})
            return
        if path == "/api/conversations/export":
            self._json(self.app.export())
            return
        if path.startswith("/api/conversations/"):
            conversation_id = path.removeprefix("/api/conversations/")
            self._json(self.app.conversation(conversation_id))
            return
        if path == "/api/workspaces":
            self._json({"workspaces": self.app.list_workspaces()})
            return
        if path == "/api/workspace-events":
            self._json({"events": self.app.workspace_events()})
            return
        if path == "/api/settings":
            self._json(self.app.database.settings())
            return
        if path == "/api/health":
            self._json(self.app.health())
            return
        workspace = self._workspace_route(path)
        if workspace is not None:
            workspace_id, action = workspace
            query = parse_qs(parsed.query, keep_blank_values=True)
            relative = query.get("path", ["."])[0]
            if set(query) - {"path"}:
                raise ValidationError("Unknown workspace query parameter.")
            if action == "list":
                self._json(self.app.list_directory(workspace_id, relative))
                return
            if action == "read":
                self._json(self.app.read_file(workspace_id, relative))
                return
        raise NotFoundError("Route does not exist.")

    def do_POST(self) -> None:
        try:
            self._dispatch_post()
        except Exception as exc:
            self._error(exc)

    def _dispatch_post(self) -> None:
        self._host()
        path = urlsplit(self.path).path
        if path == "/api/login":
            self._same_origin()
            body = self._body()
            self._only(body, {"password"})
            if not isinstance(body.get("password"), str):
                raise ValidationError("password must be text.")
            login = self.app.login(body["password"])
            self._json(
                {
                    "authenticated": True,
                    "csrf_token": login["csrf_token"],
                    "expires_at": login["expires_at"],
                },
                extra={"Set-Cookie": self._cookie_header(login["session_token"])},
            )
            return
        token = self._require_mutation()
        body = self._body()
        if path == "/api/logout":
            self._only(body, set())
            self.app.logout(token)
            self._json(
                {"ok": True},
                extra={"Set-Cookie": self._cookie_header("", expire=True)},
            )
            return
        if path == "/api/chat":
            self._only(body, {"message", "conversation_id", "selected_files"})
            self._json(
                self.app.chat(
                    body.get("message"),
                    conversation_id=body.get("conversation_id"),
                    selected_files=body.get("selected_files"),
                )
            )
            return
        if path == "/api/password":
            self._only(body, {"current_password", "new_password"})
            current = body.get("current_password")
            new = body.get("new_password")
            if not isinstance(current, str) or not isinstance(new, str):
                raise ValidationError("Password values must be text.")
            self.app.rotate_password(current, new)
            self._json(
                {"ok": True, "sessions_revoked": True},
                extra={"Set-Cookie": self._cookie_header("", expire=True)},
            )
            return
        if path == "/api/sessions/revoke":
            self._only(body, set())
            self.app.revoke_all_sessions()
            self._json(
                {"ok": True},
                extra={"Set-Cookie": self._cookie_header("", expire=True)},
            )
            return
        if path == "/api/suspend":
            self._only(body, {"confirmation"})
            if body.get("confirmation") != "SUSPEND IMAGINARY FRIEND":
                raise ValidationError(
                    "Suspension requires confirmation: SUSPEND IMAGINARY FRIEND"
                )
            self.app.suspend()
            self._json(
                {"ok": True, "suspended": True},
                extra={"Set-Cookie": self._cookie_header("", expire=True)},
            )
            return
        workspace = self._workspace_route(path)
        if workspace is not None:
            workspace_id, action = workspace
            if action == "mkdir":
                self._only(body, {"path"})
                self._json(
                    self.app.make_directory(workspace_id, body.get("path")),
                    status=201,
                )
                return
            if action == "move":
                self._only(body, {"source", "destination", "confirmation"})
                self._json(
                    self.app.move_path(
                        workspace_id,
                        body.get("source"),
                        body.get("destination"),
                        confirmation=body.get("confirmation"),
                    )
                )
                return
        raise NotFoundError("Route does not exist.")

    def do_PUT(self) -> None:
        try:
            self._host()
            self._require_mutation()
            path = urlsplit(self.path).path
            body = self._body()
            workspace = self._workspace_route(path)
            if workspace is None or workspace[1] != "write":
                raise NotFoundError("Route does not exist.")
            self._only(body, {"path", "content", "expected_sha256", "confirmation"})
            self._json(
                self.app.write_file(
                    workspace[0],
                    body.get("path"),
                    body.get("content"),
                    expected_sha256=body.get("expected_sha256"),
                    confirmation=body.get("confirmation"),
                )
            )
        except Exception as exc:
            self._error(exc)

    def do_PATCH(self) -> None:
        try:
            self._host()
            self._require_mutation()
            path = urlsplit(self.path).path
            body = self._body()
            if path == "/api/settings":
                self._json(self.app.update_settings(body))
                return
            workspace = self._workspace_route(path)
            if workspace is not None and workspace[1] == "state":
                self._only(body, {"enabled"})
                self.app.set_workspace_enabled(workspace[0], body.get("enabled"))
                self._json({"ok": True, "enabled": body.get("enabled")})
                return
            raise NotFoundError("Route does not exist.")
        except Exception as exc:
            self._error(exc)

    def do_DELETE(self) -> None:
        try:
            self._host()
            self._require_mutation()
            path = urlsplit(self.path).path
            body = self._body()
            if path.startswith("/api/conversations/"):
                self._only(body, set())
                conversation_id = path.removeprefix("/api/conversations/")
                self.app.delete_conversation(conversation_id)
                self._json({"ok": True})
                return
            workspace = self._workspace_route(path)
            if workspace is not None and workspace[1] == "path":
                self._only(body, {"path", "confirmation"})
                self._json(
                    self.app.delete_path(
                        workspace[0],
                        body.get("path"),
                        confirmation=body.get("confirmation"),
                    )
                )
                return
            raise NotFoundError("Route does not exist.")
        except Exception as exc:
            self._error(exc)

    @staticmethod
    def _workspace_route(path: str) -> tuple[str, str] | None:
        prefix = "/api/workspaces/"
        if not path.startswith(prefix):
            return None
        parts = path[len(prefix) :].split("/")
        if len(parts) != 2 or not all(parts):
            return None
        if parts[1] not in {"list", "read", "write", "mkdir", "move", "path", "state"}:
            return None
        return parts[0], parts[1]


def serve(application: FriendApplication, *, port: int) -> None:
    server = FriendHTTPServer(("127.0.0.1", port), application)

    def stop(_signum: int, _frame: Any) -> None:
        # shutdown() must run outside the serve_forever thread.
        import threading

        threading.Thread(target=server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    server.serve_forever(poll_interval=0.25)
    server.server_close()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Imaginary Friend loopback service")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("/etc/imaginary-friend/config.json"),
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="validate configuration and state, then exit",
    )
    args = parser.parse_args(argv)
    try:
        config = load_config(args.config)
        application = FriendApplication(config)
        if args.check:
            application.health(probe_model=False)
            return 0
        serve(application, port=config.port)
    except FriendError as exc:
        print(f"{exc.code}: {exc.message}", file=sys.stderr)
        return 78
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
