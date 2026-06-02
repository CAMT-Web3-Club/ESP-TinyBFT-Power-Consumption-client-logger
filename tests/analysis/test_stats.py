import polars as pl
import pytest

from esp_tinybft_logger.analysis.stats import build_summary
from esp_tinybft_logger.shared.models import StatsSummary


class TestBuildSummary:
    def test_empty_df(self) -> None:
        df = pl.DataFrame()
        result = build_summary(df, warmup_done=False, warmup_skipped=3, uptime_seconds=60)
        assert isinstance(result, StatsSummary)
        assert result.warmup_timeouts_skipped == 3
        assert result.warmup_done is False
        assert result.success_rate_pct == 0.0

    def test_normal_df(self, sample_events_df: pl.DataFrame) -> None:
        result = build_summary(
            sample_events_df, warmup_done=True, warmup_skipped=0, uptime_seconds=120
        )
        assert result.total_increments == 3
        assert result.total_replies == 2
        assert result.total_timeouts == 1
        assert result.counter_value == 2
        assert result.success_rate_pct == pytest.approx(66.7, abs=0.1)
        assert result.avg_rtt_ms == 366.0
        assert result.max_rtt_ms == 388.0
        assert result.ops_per_minute == 1.0

    def test_all_replies_no_timeouts(self) -> None:
        df = pl.DataFrame(
            [
                {"event_type": "increment", "rtt_ms": 100.0, "counter_value": 1},
                {"event_type": "reply", "rtt_ms": 100.0, "counter_value": 1},
                {"event_type": "increment", "rtt_ms": None, "counter_value": None},
                {"event_type": "reply", "rtt_ms": 200.0, "counter_value": 2},
            ]
        )
        result = build_summary(df, warmup_done=True, warmup_skipped=0, uptime_seconds=60)
        assert result.success_rate_pct == 100.0
        assert result.total_timeouts == 0

    def test_all_timeouts(self) -> None:
        df = pl.DataFrame(
            [
                {"event_type": "increment", "rtt_ms": None, "counter_value": None},
                {"event_type": "timeout", "rtt_ms": None, "counter_value": None},
            ]
        )
        result = build_summary(df, warmup_done=True, warmup_skipped=0, uptime_seconds=60)
        assert result.success_rate_pct == 0.0
        assert result.total_replies == 0  # type: ignore[attr-defined]

    def test_warmup_flags_propagated(self, sample_events_df: pl.DataFrame) -> None:
        result = build_summary(
            sample_events_df, warmup_done=True, warmup_skipped=7, uptime_seconds=3600
        )
        assert result.warmup_done is True
        assert result.warmup_timeouts_skipped == 7
        assert result.uptime_seconds == 3600
