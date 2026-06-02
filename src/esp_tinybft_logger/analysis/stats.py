import polars as pl

from esp_tinybft_logger.shared.models import StatsSummary


def build_summary(
    df: pl.DataFrame,
    warmup_done: bool,
    warmup_skipped: int,
    uptime_seconds: int,
) -> StatsSummary:
    if df.is_empty():
        return StatsSummary(
            warmup_timeouts_skipped=warmup_skipped,
            warmup_done=warmup_done,
            uptime_seconds=uptime_seconds,
        )

    increments = df.filter(pl.col("event_type") == "increment")
    replies = df.filter(pl.col("event_type") == "reply")
    timeouts = df.filter(pl.col("event_type") == "timeout")

    total = replies.height + timeouts.height
    rate = (replies.height / total * 100) if total > 0 else 100.0

    rtts = replies["rtt_ms"].drop_nulls()

    counter_vals = replies["counter_value"].drop_nulls()

    elapsed_minutes = max(uptime_seconds / 60, 1)

    if rtts.len() > 0:
        rtt_mean = round(float(rtts.mean()), 1)  # ty: ignore
        rtt_max = round(float(rtts.max()), 1)  # ty: ignore
    else:
        rtt_mean = 0.0
        rtt_max = 0.0

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
    )
