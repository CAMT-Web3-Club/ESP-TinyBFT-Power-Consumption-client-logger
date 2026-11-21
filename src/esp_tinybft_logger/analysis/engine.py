import time
from datetime import datetime

import polars as pl

from esp_tinybft_logger.analysis.stats import DeviceTotals, build_summary
from esp_tinybft_logger.ingest.parser import extract_kv, kv_int
from esp_tinybft_logger.shared.models import CounterEvent, StatsSummary

# Column types of CounterEvent.model_dump().  Without them polars infers the
# schema from the first 100 rows: a run that opens with minutes of transport
# warnings gets rtt_ms (and ok/fail/...) as Null, and the first measured
# value then fails with "could not append value ... of type: f64".
EVENT_SCHEMA: dict[str, type[pl.DataType]] = {
    "ntp_timestamp": pl.String,
    "level": pl.String,
    "tag": pl.String,
    "event_type": pl.String,
    "message": pl.String,
    "counter_value": pl.Int64,
    "status": pl.Int64,
    "rtt_ms": pl.Float64,
    "ok": pl.Int64,
    "fail": pl.Int64,
    "missed": pl.Int64,
    "preset": pl.String,
    "load": pl.String,
    "raw_line": pl.String,
}


def _parse_iso(ts: str) -> float:
    return datetime.fromisoformat(ts).timestamp()


class MetricsEngine:
    """Metrics from the client's serial output.

    Two sources, whichever the firmware prints:
    - current firmware: CLIENT_STATS after every request (the board's own
      counters ok/fail/missed and its measured latency last_ms) and BANNER
      at boot (preset=, load=);
    - older firmware: "Client sending increment..." / "Client reply: ..." /
      "Request failed or timed out." INFO lines, timed on the host.
    """

    def __init__(self) -> None:
        self._events: list[dict[str, object]] = []
        self._warmup_done = False
        self._warmup_skipped = 0
        self._last_inc_ts: str | None = None
        self._start = time.monotonic()
        self._last_processed_event: CounterEvent | None = None
        # CLIENT_STATS counters restart at 0 when the client reboots: keep the
        # totals of earlier boots in _base and the current boot's in _cur.
        self._device = False
        self._base = DeviceTotals()
        self._cur = DeviceTotals()
        self._preset: str | None = None
        self._load: str | None = None

    def process(self, event: CounterEvent) -> bool:
        match event.event_type:
            case "timeout" if not self._warmup_done:
                self._warmup_skipped += 1
                self._last_processed_event = event
                return False
            case "increment":
                self._last_inc_ts = event.ntp_timestamp
            case "reply":
                if not self._warmup_done:
                    self._warmup_done = True
                if self._last_inc_ts is not None:
                    rtt = (_parse_iso(event.ntp_timestamp) - _parse_iso(self._last_inc_ts)) * 1000
                    event = event.model_copy(update={"rtt_ms": round(rtt, 1)})
            case "banner":
                self._new_boot()
                self._preset = event.preset or self._preset
                self._load = event.load or self._load
            case "stats":
                event = self._device_stats(event)

        self._last_processed_event = event
        self._events.append(event.model_dump())
        return True

    def _new_boot(self) -> None:
        self._base = self._base + self._cur
        self._cur = DeviceTotals()

    def _device_stats(self, event: CounterEvent) -> CounterEvent:
        self._device = True
        now = DeviceTotals(ok=event.ok or 0, fail=event.fail or 0, missed=event.missed or 0)
        if now.ok < self._cur.ok or now.fail < self._cur.fail:
            self._new_boot()  # rebooted without a BANNER on this port
        new_success = now.ok > self._cur.ok
        self._cur = now
        if now.ok > 0:
            self._warmup_done = True
        # The board's own latency of the request that just succeeded.  The
        # first success after boot waits for the whole cluster to come up, so
        # it is left out of RTT, as tools/analyze.py in the firmware does.
        last_ms = kv_int(extract_kv(event.message), "last_ms")
        rtt = float(last_ms) if new_success and now.ok > 1 and last_ms is not None else None
        return event.model_copy(update={"rtt_ms": rtt, "preset": self._preset, "load": self._load})

    def stats(self) -> StatsSummary:
        uptime = int(time.monotonic() - self._start)
        df: pl.DataFrame = pl.DataFrame(self._events, schema=EVENT_SCHEMA)
        device = self._base + self._cur if self._device else None
        return build_summary(
            df,
            self._warmup_done,
            self._warmup_skipped,
            uptime,
            device=device,
            preset=self._preset,
            load=self._load,
        )

    @property
    def warmup_done(self) -> bool:
        return self._warmup_done

    @property
    def last_processed_event(self) -> CounterEvent | None:
        return self._last_processed_event
