"""In-process pub/sub feeding the WebSocket. publish() is safe to call from worker threads."""

from __future__ import annotations

import asyncio
import contextlib
from typing import Any

Event = dict[str, Any]


class EventBus:
    def __init__(self) -> None:
        self._loop: asyncio.AbstractEventLoop | None = None
        self._subs: set[asyncio.Queue[Event]] = set()

    def bind_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def subscribe(self) -> asyncio.Queue[Event]:
        q: asyncio.Queue[Event] = asyncio.Queue(maxsize=1000)
        self._subs.add(q)
        return q

    def unsubscribe(self, q: asyncio.Queue[Event]) -> None:
        self._subs.discard(q)

    def publish(self, event: Event) -> None:
        if self._loop is None or self._loop.is_closed():
            return
        for q in list(self._subs):
            self._loop.call_soon_threadsafe(self._offer, q, event)

    @staticmethod
    def _offer(q: asyncio.Queue[Event], event: Event) -> None:
        # A stalled client must not grow memory forever; progress events are superseded anyway.
        with contextlib.suppress(asyncio.QueueFull):
            q.put_nowait(event)
