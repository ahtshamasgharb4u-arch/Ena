"""Mock TTS server for testing.

Implements the contract:
  POST /v1/synthesize
    body: {ssml: str, idempotency_key: str, voice: str}
    200 → {audio_url: str}
    202 → {audio_url: str}   (cached/duplicate idempotency key)
    429 → {retry_after: int}  (rate limited)
    4xx → terminal client error
    5xx / timeout → retryable

This is an ASGI app that can be run with ``uvicorn`` or used as a
test fixture via ``httpx.ASGITransport``.
"""

from __future__ import annotations

import hashlib
import json
import random
from typing import Optional

from pydantic import BaseModel


class SynthesizeRequest(BaseModel):
    ssml: str
    idempotency_key: str
    voice: str = "default"


class MockTTSServer:
    """A mock TTS server that can simulate all response codes.

    Usage as a test fixture::

        from reminder_service.mock_server import MockTTSServer
        server = MockTTSServer()
        server.set_mode("ok")  # returns 200

    The server tracks seen idempotency keys to simulate caching (202).
    """

    def __init__(self):
        self._seen_keys: set[str] = set()
        self._mode: str = "ok"  # ok | cached | rate_limit | client_error | server_error
        self._retry_after: int = 5
        self._requests: list[dict] = []

    def set_mode(self, mode: str, retry_after: int = 5) -> None:
        """Set the response mode for the next request.

        Modes:
            - "ok": returns 200
            - "cached": returns 202 (simulates duplicate idempotency key)
            - "rate_limit": returns 429
            - "client_error": returns 422
            - "server_error": returns 503
        """
        self._mode = mode
        self._retry_after = retry_after

    def reset(self) -> None:
        self._seen_keys.clear()
        self._mode = "ok"
        self._requests.clear()

    @property
    def request_count(self) -> int:
        return len(self._requests)

    async def handle(self, scope, receive, send) -> None:
        """ASGI application handler."""
        assert scope["type"] == "http"

        body_bytes = b""
        more_body = True
        while more_body:
            message = await receive()
            body_bytes += message.get("body", b"")
            more_body = message.get("more_body", False)

        try:
            req_data = json.loads(body_bytes)
            request = SynthesizeRequest(**req_data)
        except (json.JSONDecodeError, Exception):
            await self._send_response(send, 400, {"error": "invalid request"})
            return

        self._requests.append(req_data)

        if self._mode == "rate_limit":
            await self._send_response(send, 429, {"retry_after": self._retry_after})
            return

        if self._mode == "client_error":
            await self._send_response(send, 422, {"error": "invalid voice parameter"})
            return

        if self._mode == "server_error":
            await self._send_response(send, 503, {"error": "service unavailable"})
            return

        # Check for duplicate idempotency key
        if request.idempotency_key in self._seen_keys or self._mode == "cached":
            self._seen_keys.add(request.idempotency_key)
            await self._send_response(
                send,
                202,
                {
                    "audio_url": f"https://tts.example.com/audio/{hashlib.md5(request.idempotency_key.encode()).hexdigest()}.mp3"
                },
            )
            return

        self._seen_keys.add(request.idempotency_key)
        audio_id = hashlib.md5(request.idempotency_key.encode()).hexdigest()
        await self._send_response(
            send,
            200,
            {"audio_url": f"https://tts.example.com/audio/{audio_id}.mp3"},
        )

    async def _send_response(self, send, status_code: int, body: dict) -> None:
        body_bytes = json.dumps(body).encode("utf-8")
        await send(
            {
                "type": "http.response.start",
                "status": status_code,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body_bytes)).encode()),
                ],
            }
        )
        await send(
            {
                "type": "http.response.body",
                "body": body_bytes,
            }
        )
