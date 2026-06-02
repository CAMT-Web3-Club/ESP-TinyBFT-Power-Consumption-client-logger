import time
from datetime import datetime

import polars as pl

from esp_tinybft_logger.analysis.stats import build_summary
from esp_tinybft_logger.shared.models import CounterEvent, StatsSummary


def _parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


class MetricsEngine:
    def __init__(self) -> None:
        self._events: list[dict[str, object]] = []
        self._warmup_done = False
        self._warmup_skipped = 0
        self._last_inc_ts: str | None = None
        self._start = time.monotonic()

    def process(self, event: CounterEvent) -> bool:
        match event.event_type:
            case "timeout" if not self._warmup_done:
                self._warmup_skipped += 1
                return False
            case "increment":
                self._last_inc_ts = event.ntp_timestamp
            case "reply":
                if not self._warmup_done:
                    self._warmup_done = True
                if self._last_inc_ts is not None:
                    rtt = (_parse_iso(event.ntp_timestamp) - _parse_iso(self._last_inc_ts)) * 1000
                    event = event.model_copy(update={"rtt_ms": round(rtt, 1)})

        self._events.append(event.model_dump())
        return True

    def stats(self) -> StatsSummary:
        uptime = int(time.monotonic() - self._start)
        df: pl.DataFrame = pl.DataFrame(self._events)
        summary = build_summary(df, self._warmup_done, self._warmup_skipped, uptime)
        return summary

    @property
    def warmup_done(self) -> bool:
        return self._warmup_done
