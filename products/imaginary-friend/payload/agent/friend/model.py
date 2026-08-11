"""Bounded OpenAI-compatible client restricted to a loopback endpoint."""

from __future__ import annotations

import http.client
import ipaddress
import json
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

from .errors import ValidationError

MAX_RESPONSE_BYTES = 2 * 1_048_576
MAX_CONTEXT_MESSAGES = 100
MAX_MESSAGE_CHARS = 100_000


@dataclass(frozen=True)
class Endpoint:
    host: str
    port: int
    base_path: str


def validate_model_base_url(value: str) -> Endpoint:
    """Accept plain HTTP only when every destination is loopback."""
    if not isinstance(value, str) or not value.strip():
        raise ValidationError("Model endpoint must not be empty.")
    try:
        parsed = urlsplit(value)
        port = parsed.port or 80
    except ValueError as exc:
        raise ValidationError("Model endpoint is not a valid URL.") from exc
    if parsed.scheme != "http":
        raise ValidationError("First-release model endpoints must use loopback HTTP.")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValidationError("Model endpoint must not contain credentials or a query.")
    host = (parsed.hostname or "").lower()
    if not host:
        raise ValidationError("Model endpoint requires a loopback host.")
    if host == "localhost":
        try:
            addresses = {
                item[4][0]
                for item in socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
            }
        except OSError as exc:
            raise ValidationError("localhost could not be resolved.") from exc
        if not addresses or any(
            not ipaddress.ip_address(address).is_loopback for address in addresses
        ):
            raise ValidationError("localhost resolved outside loopback.")
    else:
        try:
            address = ipaddress.ip_address(host)
        except ValueError as exc:
            raise ValidationError(
                "Model endpoint host must be localhost or a loopback address."
            ) from exc
        if not address.is_loopback:
            raise ValidationError("Model endpoint must stay on loopback.")
    if not 1 <= port <= 65535:
        raise ValidationError("Model endpoint port is invalid.")
    path = parsed.path.rstrip("/")
    if not path:
        path = "/v1"
    if not path.startswith("/") or ".." in path.split("/"):
        raise ValidationError("Model endpoint path is invalid.")
    return Endpoint(host=host, port=port, base_path=path)


def validate_model_id(value: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or len(value) > 256
        or any(ord(character) < 32 for character in value)
    ):
        raise ValidationError("Model ID must be non-empty text.")
    return value.strip()


class ModelClient:
    """Make only model-list and text-completion requests without redirects."""

    def __init__(self, base_url: str, model: str, *, timeout: float = 15) -> None:
        self.endpoint = validate_model_base_url(base_url)
        self.model = validate_model_id(model)
        self.timeout = timeout

    def _request(
        self, method: str, path: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        body = None
        headers = {"Accept": "application/json", "Connection": "close"}
        if payload is not None:
            body = json.dumps(
                payload, ensure_ascii=False, separators=(",", ":")
            ).encode("utf-8")
            headers["Content-Type"] = "application/json"
        connection = http.client.HTTPConnection(
            self.endpoint.host, self.endpoint.port, timeout=self.timeout
        )
        try:
            connection.request(method, path, body=body, headers=headers)
            response = connection.getresponse()
            if response.status < 200 or response.status >= 300:
                response.read(min(MAX_RESPONSE_BYTES, 64 * 1024))
                raise ValidationError(
                    f"Local model endpoint returned HTTP {response.status}."
                )
            length = response.getheader("Content-Length")
            if length is not None:
                try:
                    if int(length) > MAX_RESPONSE_BYTES:
                        raise ValidationError("Local model response is too large.")
                except ValueError as exc:
                    raise ValidationError(
                        "Local model returned an invalid Content-Length."
                    ) from exc
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            if len(raw) > MAX_RESPONSE_BYTES:
                raise ValidationError("Local model response is too large.")
        except (OSError, http.client.HTTPException) as exc:
            raise ValidationError("Local model endpoint is unavailable.") from exc
        finally:
            connection.close()
        try:
            value = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValidationError("Local model returned invalid JSON.") from exc
        if not isinstance(value, dict):
            raise ValidationError("Local model response must be a JSON object.")
        return value

    def models(self) -> list[str]:
        value = self._request("GET", f"{self.endpoint.base_path}/models")
        records = value.get("data")
        if not isinstance(records, list):
            raise ValidationError("Local model list has an invalid shape.")
        result: list[str] = []
        for record in records:
            if isinstance(record, dict) and isinstance(record.get("id"), str):
                result.append(record["id"])
        if not result:
            raise ValidationError("Local model endpoint returned no model IDs.")
        return result

    def complete(
        self,
        messages: list[dict[str, str]],
        *,
        max_tokens: int = 1_024,
        temperature: float = 0.7,
    ) -> str:
        if not 1 <= len(messages) <= MAX_CONTEXT_MESSAGES:
            raise ValidationError("Conversation context is empty or too long.")
        safe_messages: list[dict[str, str]] = []
        for item in messages:
            if set(item) != {"role", "content"}:
                raise ValidationError("Model message shape is invalid.")
            role = item["role"]
            content = item["content"]
            if role not in {"system", "user", "assistant"}:
                raise ValidationError("Model message role is invalid.")
            if not isinstance(content, str) or len(content) > MAX_MESSAGE_CHARS:
                raise ValidationError("Model message content is invalid.")
            safe_messages.append({"role": role, "content": content})
        if (
            isinstance(max_tokens, bool)
            or not isinstance(max_tokens, int)
            or not 1 <= max_tokens <= 4096
        ):
            raise ValidationError("max_tokens is outside the supported range.")
        value = self._request(
            "POST",
            f"{self.endpoint.base_path}/chat/completions",
            {
                "model": self.model,
                "messages": safe_messages,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "stream": False,
            },
        )
        choices = value.get("choices")
        if not isinstance(choices, list) or not choices:
            raise ValidationError("Local model completion has no choices.")
        first = choices[0]
        if not isinstance(first, dict):
            raise ValidationError("Local model completion choice is invalid.")
        message = first.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise ValidationError("Local model completion content is invalid.")
        content = message["content"].strip()
        if not content:
            raise ValidationError("Local model returned an empty response.")
        if len(content) > MAX_MESSAGE_CHARS:
            raise ValidationError("Local model completion content is too large.")
        return content

    def probe(self) -> dict[str, Any]:
        models = self.models()
        if self.model not in models:
            raise ValidationError("Configured model is not present in the model list.")
        result = self.complete(
            [{"role": "user", "content": "Reply with OK."}],
            max_tokens=4,
            temperature=0,
        )
        return {"model": self.model, "models": len(models), "completion": bool(result)}
