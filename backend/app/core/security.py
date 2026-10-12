"""Only this machine may talk to the backend (N10).

Binding to 127.0.0.1 keeps the LAN out, but a web page in the user's browser could still reach
localhost via DNS rebinding or cross-site requests. So: the Host header must be ours, and any
Origin header present must be ours too.
"""

from __future__ import annotations

import json

from starlette.types import ASGIApp, Receive, Scope, Send

from app.core.config import Settings
from app.messages import message


class LocalOnlyMiddleware:
    def __init__(self, app: ASGIApp, settings: Settings):
        self.app = app
        self.hosts = settings.allowed_hosts
        self.origins = settings.allowed_origins

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] in ("http", "websocket"):
            headers = {k.decode("latin-1"): v.decode("latin-1") for k, v in scope["headers"]}
            origin = headers.get("origin")
            if headers.get("host") not in self.hosts or (origin and origin not in self.origins):
                await self._reject(scope, send)
                return
        await self.app(scope, receive, send)

    @staticmethod
    async def _reject(scope: Scope, send: Send) -> None:
        if scope["type"] == "websocket":
            await send({"type": "websocket.close", "code": 1008})
            return
        body = json.dumps(
            {"code": "forbidden_host", "message_vi": message("forbidden_host"), "detail": ""},
            ensure_ascii=False,
        ).encode()
        await send(
            {
                "type": "http.response.start",
                "status": 403,
                "headers": [(b"content-type", b"application/json; charset=utf-8")],
            }
        )
        await send({"type": "http.response.body", "body": body})
