import polars as pl
import pytest

from esp_tinybft_logger.shared.models import CounterEvent, ParsedLog


@pytest.fixture
def sample_parsed_increment() -> ParsedLog:
    return ParsedLog(
        level="I",
        esp_ticks=12345,
        tag="counter",
        message="Client sending increment...",
        raw_line="I (12345) counter: Client sending increment...",
    )


@pytest.fixture
def sample_parsed_reply() -> ParsedLog:
    return ParsedLog(
        level="I",
        esp_ticks=12800,
        tag="counter",
        message="Client reply: value=42, status=0",
        raw_line="I (12800) counter: Client reply: value=42, status=0",
    )


@pytest.fixture
def sample_parsed_timeout() -> ParsedLog:
    return ParsedLog(
        level="W",
        esp_ticks=35000,
        tag="counter",
        message="Request failed or timed out.",
        raw_line="W (35000) counter: Request failed or timed out.",
    )


@pytest.fixture
def sample_parsed_non_counter() -> ParsedLog:
    return ParsedLog(
        level="W",
        esp_ticks=5000,
        tag="tbft_replica",
        message="view-change timeout in view 3 (keys=7/7)",
        raw_line="W (5000) tbft_replica: view-change timeout in view 3 (keys=7/7)",
    )


@pytest.fixture
def sample_event_increment() -> CounterEvent:
    return CounterEvent(
        ntp_timestamp="2026-06-01T14:32:01.123+00:00",
        level="I",
        tag="counter",
        event_type="increment",
        message="Client sending increment...",
        raw_line="I (12345) counter: Client sending increment...",
    )


@pytest.fixture
def sample_event_reply() -> CounterEvent:
    return CounterEvent(
        ntp_timestamp="2026-06-01T14:32:01.467+00:00",
        level="I",
        tag="counter",
        event_type="reply",
        message="Client reply: value=42, status=0",
        counter_value=42,
        status=0,
        rtt_ms=344.0,
        raw_line="I (12800) counter: Client reply: value=42, status=0",
    )


@pytest.fixture
def sample_event_timeout() -> CounterEvent:
    return CounterEvent(
        ntp_timestamp="2026-06-01T14:32:30.030+00:00",
        level="W",
        tag="counter",
        event_type="timeout",
        message="Request failed or timed out.",
        raw_line="W (35000) counter: Request failed or timed out.",
    )


@pytest.fixture
def sample_events_df() -> pl.DataFrame:
    return pl.DataFrame(
        [
            {
                "ntp_timestamp": "2026-06-01T14:32:01.123+00:00",
                "level": "I",
                "tag": "counter",
                "event_type": "increment",
                "message": "Client sending increment...",
                "counter_value": None,
                "status": None,
                "rtt_ms": None,
                "raw_line": "I (1) counter: Client sending increment...",
            },
            {
                "ntp_timestamp": "2026-06-01T14:32:01.467+00:00",
                "level": "I",
                "tag": "counter",
                "event_type": "reply",
                "message": "Client reply: value=1, status=0",
                "counter_value": 1,
                "status": 0,
                "rtt_ms": 344.0,
                "raw_line": "I (2) counter: Client reply: value=1, status=0",
            },
            {
                "ntp_timestamp": "2026-06-01T14:32:31.901+00:00",
                "level": "I",
                "tag": "counter",
                "event_type": "increment",
                "message": "Client sending increment...",
                "counter_value": None,
                "status": None,
                "rtt_ms": None,
                "raw_line": "I (3) counter: Client sending increment...",
            },
            {
                "ntp_timestamp": "2026-06-01T14:32:32.289+00:00",
                "level": "I",
                "tag": "counter",
                "event_type": "reply",
                "message": "Client reply: value=2, status=0",
                "counter_value": 2,
                "status": 0,
                "rtt_ms": 388.0,
                "raw_line": "I (4) counter: Client reply: value=2, status=0",
            },
            {
                "ntp_timestamp": "2026-06-01T14:33:02.512+00:00",
                "level": "I",
                "tag": "counter",
                "event_type": "increment",
                "message": "Client sending increment...",
                "counter_value": None,
                "status": None,
                "rtt_ms": None,
                "raw_line": "I (5) counter: Client sending increment...",
            },
            {
                "ntp_timestamp": "2026-06-01T14:33:33.030+00:00",
                "level": "W",
                "tag": "counter",
                "event_type": "timeout",
                "message": "Request failed or timed out.",
                "counter_value": None,
                "status": None,
                "rtt_ms": None,
                "raw_line": "W (6) counter: Request failed or timed out.",
            },
        ]
    )
