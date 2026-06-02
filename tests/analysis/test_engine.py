from esp_tinybft_logger.analysis.engine import MetricsEngine
from esp_tinybft_logger.shared.models import CounterEvent

_EVENT_TIMEOUT = CounterEvent(
    ntp_timestamp="2026-06-01T14:30:00.000+00:00",
    level="W",
    tag="counter",
    event_type="timeout",
    message="Request failed or timed out.",
    raw_line="W (100) counter: Request failed or timed out.",
)

_EVENT_INCREMENT = CounterEvent(
    ntp_timestamp="2026-06-01T14:30:01.000+00:00",
    level="I",
    tag="counter",
    event_type="increment",
    message="Client sending increment...",
    raw_line="I (200) counter: Client sending increment...",
)

_EVENT_REPLY = CounterEvent(
    ntp_timestamp="2026-06-01T14:30:01.350+00:00",
    level="I",
    tag="counter",
    event_type="reply",
    message="Client reply: value=1, status=0",
    counter_value=1,
    status=0,
    raw_line="I (300) counter: Client reply: value=1, status=0",
)


class TestMetricsEngineWarmup:
    def test_skips_timeouts_during_warmup(self) -> None:
        engine = MetricsEngine()
        assert engine.warmup_done is False
        accepted = engine.process(_EVENT_TIMEOUT)
        assert accepted is False
        assert engine.warmup_done is False
        stats = engine.stats()
        assert stats.warmup_timeouts_skipped == 1
        assert stats.total_timeouts == 0

    def test_warmup_ends_on_first_reply(self) -> None:
        engine = MetricsEngine()
        engine.process(_EVENT_TIMEOUT)
        engine.process(_EVENT_TIMEOUT)
        engine.process(_EVENT_INCREMENT)
        accepted = engine.process(_EVENT_REPLY)
        assert accepted is True
        assert engine.warmup_done is True
        stats = engine.stats()
        assert stats.warmup_timeouts_skipped == 2

    def test_timeouts_counted_after_warmup(self) -> None:
        engine = MetricsEngine()
        engine.process(_EVENT_INCREMENT)
        engine.process(_EVENT_REPLY)
        assert engine.warmup_done is True
        engine.process(_EVENT_TIMEOUT)
        stats = engine.stats()
        assert stats.total_timeouts == 1
        assert stats.warmup_timeouts_skipped == 0


class TestMetricsEngineRTT:
    def test_rtt_computed_on_reply(self) -> None:
        engine = MetricsEngine()
        engine.process(_EVENT_INCREMENT)
        engine.process(_EVENT_REPLY)
        stats = engine.stats()
        assert stats.warmup_done is True
        assert stats.avg_rtt_ms == 350.0

    def test_no_rtt_without_prior_increment(self) -> None:
        engine = MetricsEngine()
        engine.process(_EVENT_REPLY)
        stats = engine.stats()
        assert stats.warmup_done is True


class TestMetricsEngineStats:
    def test_stats_returns_summary(self) -> None:
        engine = MetricsEngine()
        engine.process(
            CounterEvent(
                ntp_timestamp="2026-06-01T14:00:00.000+00:00",
                level="I",
                tag="counter",
                event_type="increment",
                message="inc",
                raw_line="I (1) counter: inc",
            )
        )
        engine.process(
            CounterEvent(
                ntp_timestamp="2026-06-01T14:00:00.350+00:00",
                level="I",
                tag="counter",
                event_type="reply",
                message="rep val=5",
                counter_value=5,
                status=0,
                raw_line="I (2) counter: rep",
            )
        )
        stats = engine.stats()
        assert stats.counter_value == 5
        assert stats.total_replies == 1
        assert stats.success_rate_pct == 100.0
        assert stats.warmup_done is True


class TestNonCounterEvents:
    def test_non_counter_passes_through_engine(self) -> None:
        engine = MetricsEngine()
        engine.process(_EVENT_INCREMENT)
        engine.process(_EVENT_REPLY)
        assert engine.warmup_done is True
        accepted = engine.process(
            CounterEvent(
                ntp_timestamp="2026-06-01T14:01:00.000+00:00",
                level="W",
                tag="tbft_replica",
                event_type="",
                message="view-change timeout",
                raw_line="W (5) tbft_replica: view-change timeout",
            )
        )
        assert accepted is True

    def test_non_counter_does_not_affect_counter_stats(self) -> None:
        engine = MetricsEngine()
        engine.process(_EVENT_INCREMENT)
        engine.process(_EVENT_REPLY)
        engine.process(
            CounterEvent(
                ntp_timestamp="2026-06-01T14:01:00.000+00:00",
                level="W",
                tag="tbft_udp",
                event_type="",
                message="send timeout",
                raw_line="W (5) tbft_udp: send timeout",
            )
        )
        stats = engine.stats()
        assert stats.counter_value == 1
        assert stats.total_replies == 1
        assert stats.total_timeouts == 0
