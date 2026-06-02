import asyncio
from collections.abc import AsyncGenerator

from esp_tinybft_logger.shared.models import CounterEvent


class EventStream:
    def __init__(self) -> None:
        self._subscribers: list[asyncio.Queue[CounterEvent]] = []

    async def publish(self, event: CounterEvent) -> None:
        for q in self._subscribers:
            q.put_nowait(event)

    def subscribe(self) -> AsyncGenerator[CounterEvent]:
        async def _gen() -> AsyncGenerator[CounterEvent]:
            q: asyncio.Queue[CounterEvent] = asyncio.Queue()
            self._subscribers.append(q)
            try:
                while True:
                    yield await q.get()
            finally:
                self._subscribers.remove(q)

        return _gen()
