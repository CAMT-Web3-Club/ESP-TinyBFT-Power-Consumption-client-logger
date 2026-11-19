from dataclasses import dataclass

import polars as pl

from esp_tinybft_logger.shared.models import StatsSummary


@dataclass(frozen=True)
class DeviceTotals:
    """Request counters the client firmware prints in CLIENT_STATS."""

    ok: int = 0
    fail: int = 0
    missed: int = 0

    def __add__(self, other: DeviceTotals) -> DeviceTotals:
        return DeviceTotals(
            ok=self.ok + other.ok,
            fail=self.fail + other.fail,
            missed=self.missed + other.missed,
        )


def _rtt(values: pl.Series) -> tuple[float, float]:
    rtts = values.drop_nulls()
    if rtts.len() == 0:
        return 0.0, 0.0
    return round(float(rtts.mean()), 1), round(float(rtts.max()), 1)  # ty: ignore


def build_summary(
    df: pl.DataFrame,
    warmup_done: bool,
    warmup_skipped: int,
    uptime_seconds: int,
    device: DeviceTotals | None = None,
    preset: str | None = None,
    load: str | None = None,
) -> StatsSummary:
    if df.is_empty():
        return StatsSummary(
            warmup_timeouts_skipped=warmup_skipped,
            warmup_done=warmup_done,
            uptime_seconds=uptime_seconds,
            preset=preset,
            load=load,
        )

    elapsed_minutes = max(uptime_seconds / 60, 1)

    if device is not None:
        # Current firmware: the board's own counters and latencies.  Success
        # is ok / (ok + fail); missed slots (10 s load only) are latency, not
        # loss, and are reported apart.
        sent = device.ok + device.fail
        rtt_mean, rtt_max = _rtt(df.filter(pl.col("event_type") == "stats")["rtt_ms"])
        return StatsSummary(
            counter_value=device.ok,
            total_increments=sent,
            total_replies=device.ok,
            total_timeouts=device.fail,
            total_missed=device.missed,
            warmup_timeouts_skipped=warmup_skipped,
            success_rate_pct=round(device.ok / sent * 100, 1) if sent > 0 else 100.0,
            avg_rtt_ms=rtt_mean,
            max_rtt_ms=rtt_max,
            ops_per_minute=round(device.ok / elapsed_minutes, 2),
            uptime_seconds=uptime_seconds,
            warmup_done=warmup_done,
            preset=preset,
            load=load,
            source="device",
        )

    increments = df.filter(pl.col("event_type") == "increment")
    replies = df.filter(pl.col("event_type") == "reply")
    timeouts = df.filter(pl.col("event_type") == "timeout")

    total = replies.height + timeouts.height
    rate = (replies.height / total * 100) if total > 0 else 100.0

    rtts = replies["rtt_ms"]

    counter_vals = replies["counter_value"].drop_nulls()

    rtt_mean, rtt_max = _rtt(rtts)

    counter_value: int = counter_vals.max() if counter_vals.len() > 0 else 0  # ty: ignore

    return StatsSummary(
        counter_value=counter_value,
        total_increments=increments.height,
        total_replies=replies.height,
        total_timeouts=timeouts.height,
        warmup_timeouts_skipped=warmup_skipped,
        success_rate_pct=round(rate, 1),
        avg_rtt_ms=rtt_mean,
        max_rtt_ms=rtt_max,
        ops_per_minute=round(replies.height / elapsed_minutes, 2),
        uptime_seconds=uptime_seconds,
        warmup_done=warmup_done,
        preset=preset,
        load=load,
    )
