import asyncio

import pytest

from esp_tinybft_logger.pipeline.stream import EventStream
from esp_tinybft_logger.shared.models import CounterEvent


def _make_event(index: int) -> CounterEvent:
    return CounterEvent(
        ntp_timestamp=f"2026-06-01T14:00:0{index}.000+00:00",
        level="I",
        tag="counter",
        event_type="increment",
        message=f"Client sending increment #{index}...",
        raw_line=f"I (0) counter: increment #{index}",
    )


class TestEventStreamPublishSubscribe:
    @pytest.mark.asyncio
    async def test_single_subscriber_receives_all(self) -> None:
        stream = EventStream()
        received: list[CounterEvent] = []

        async def collect() -> None:
            async for event in stream.subscribe():
                received.append(event)
                if len(received) >= 3:
                    break

        task = asyncio.create_task(collect())
        await asyncio.sleep(0.01)
        await stream.publish(_make_event(1))
        await stream.publish(_make_event(2))
        await stream.publish(_make_event(3))
        await task
        assert len(received) == 3
        assert received[0].counter_value is None

    @pytest.mark.asyncio
    async def test_multi_subscriber(self) -> None:
        stream = EventStream()
        r1: list[CounterEvent] = []
        r2: list[CounterEvent] = []

        async def collect(receiver: list[CounterEvent]) -> None:
            async for event in stream.subscribe():
                receiver.append(event)
                if len(receiver) >= 2:
                    break

        t1 = asyncio.create_task(collect(r1))
        t2 = asyncio.create_task(collect(r2))
        await asyncio.sleep(0.01)
        await stream.publish(_make_event(1))
        await stream.publish(_make_event(2))
        await t1
        await t2
        assert len(r1) == 2
        assert len(r2) == 2

    @pytest.mark.asyncio
    async def test_no_subscribers_no_error(self) -> None:
        stream = EventStream()
        await stream.publish(_make_event(1))

    @pytest.mark.asyncio
    async def test_subscribe_returns_async_generator(self) -> None:
        stream = EventStream()
        gen = stream.subscribe()
        assert gen is not None
