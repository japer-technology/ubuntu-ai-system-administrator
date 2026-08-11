"""Hermetic loopback OpenAI-compatible model fixture."""

from __future__ import annotations

import argparse
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any


class Handler(BaseHTTPRequestHandler):
    protocol_version = "HTTP/1.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, value: Any, status: int = 200) -> None:
        payload = json.dumps(value, separators=(",", ":")).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def do_GET(self) -> None:
        if self.path == "/v1/models":
            self._json({"data": [{"id": "fixture-friend"}]})
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._json({"error": "not found"}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            value = json.loads(self.rfile.read(length).decode("utf-8"))
            messages = value["messages"]
            prompt = str(messages[-1]["content"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            self._json({"error": "bad request"}, 400)
            return
        reply = "OK" if prompt == "Reply with OK." else "A private fixture reply."
        self._json(
            {
                "id": "fixture-completion",
                "choices": [
                    {
                        "index": 0,
                        "message": {"role": "assistant", "content": reply},
                    }
                ],
            }
        )


class Fixture:
    def __init__(self, port: int = 0) -> None:
        self.server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)

    @property
    def port(self) -> int:
        return int(self.server.server_port)

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1"

    def __enter__(self) -> "Fixture":
        self.thread.start()
        return self

    def __exit__(self, *_args: object) -> None:
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=18080)
    args = parser.parse_args()
    fixture = Fixture(args.port)
    fixture.thread.start()

    def stop(_signum: int, _frame: Any) -> None:
        threading.Thread(target=fixture.server.shutdown, daemon=True).start()

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    fixture.thread.join()
    fixture.server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
