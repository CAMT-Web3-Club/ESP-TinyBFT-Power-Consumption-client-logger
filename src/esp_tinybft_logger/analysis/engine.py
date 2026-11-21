import re
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


_BOOT_MS_RE = re.compile(r"^[IWED]\s*\((\d+)\)")


def _boot_ms(raw_line: str) -> int | None:
    """Milliseconds since the board booted, from the ESP-IDF log prefix."""
    m = _BOOT_MS_RE.match(raw_line.strip())
    return int(m.group(1)) if m else None


class MetricsEngine:
    """Metrics from the client's serial output.

    A run lasts from power-on until the batteries are empty, and all of it is
    data: requests that fail while the cluster comes up count like any
    other, and every success has its latency.  The warm-up (failures before
    the first success, and when that success came) is reported, not removed.

    The client may stay powered between runs while the replicas run on
    batteries.  When the first CLIENT_STATS arrives without a BANNER before
    it, the client was already running: its counters so far belong to
    earlier runs, so they become the baseline and the run is counted from
    the logger's start (start the logger when the batteries go in).  The
    request of that first line is not counted: it cannot be told whether it
    succeeded.  When the client boots while the logger runs, the run is
    counted from that boot.

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
        self._warmup_timeouts = 0
        self._first_ok_s: float | None = None
        self._first_ok_from: str | None = None  # "boot" or "start"
        self._seen_banner = False
        self._t0: str | None = None  # host time of the first line
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
        if self._t0 is None:
            self._t0 = event.ntp_timestamp
        match event.event_type:
            case "timeout" if not self._warmup_done:
                self._warmup_timeouts += 1
            case "increment":
                self._last_inc_ts = event.ntp_timestamp
            case "reply":
                if not self._warmup_done:
                    self._warmup_done = True
                    self._first_ok_at(event)
                if self._last_inc_ts is not None:
                    rtt = (_parse_iso(event.ntp_timestamp) - _parse_iso(self._last_inc_ts)) * 1000
                    event = event.model_copy(update={"rtt_ms": round(rtt, 1)})
            case "banner":
                self._seen_banner = True
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

    def _first_ok_at(self, event: CounterEvent) -> None:
        """Record when the run's first success came: board uptime if the
        client booted in this session, else time since the logger started."""
        boot_ms = _boot_ms(event.raw_line)
        if self._seen_banner and boot_ms is not None:
            self._first_ok_s, self._first_ok_from = boot_ms / 1000, "boot"
        elif self._t0 is not None:
            secs = _parse_iso(event.ntp_timestamp) - _parse_iso(self._t0)
            self._first_ok_s, self._first_ok_from = round(secs, 1), "start"

    def _device_stats(self, event: CounterEvent) -> CounterEvent:
        now = DeviceTotals(ok=event.ok or 0, fail=event.fail or 0, missed=event.missed or 0)
        if not self._device and not self._seen_banner:
            # Already running when the logger started: earlier runs' counts
            # are the baseline (see the class docstring).
            self._base = DeviceTotals(ok=-now.ok, fail=-now.fail, missed=-now.missed)
            self._cur = now
        self._device = True
        if now.ok < self._cur.ok or now.fail < self._cur.fail:
            self._new_boot()  # rebooted without a BANNER on this port
        new_success = now.ok > self._cur.ok
        self._cur = now
        run = self._base + self._cur
        if run.ok > 0 and not self._warmup_done:
            self._warmup_done = True
            self._warmup_timeouts = run.fail
            self._first_ok_at(event)
        # The board's own latency of the request that just succeeded, the
        # first one after boot included: it is part of the run.
        last_ms = kv_int(extract_kv(event.message), "last_ms")
        rtt = float(last_ms) if new_success and last_ms is not None else None
        return event.model_copy(update={"rtt_ms": rtt, "preset": self._preset, "load": self._load})

    def stats(self) -> StatsSummary:
        uptime = int(time.monotonic() - self._start)
        df: pl.DataFrame = pl.DataFrame(self._events, schema=EVENT_SCHEMA)
        device = self._base + self._cur if self._device else None
        return build_summary(
            df,
            self._warmup_done,
            self._warmup_timeouts,
            uptime,
            device=device,
            preset=self._preset,
            load=self._load,
            first_ok_s=self._first_ok_s,
            first_ok_from=self._first_ok_from,
        )

    @property
    def warmup_done(self) -> bool:
        return self._warmup_done

    @property
    def last_processed_event(self) -> CounterEvent | None:
        return self._last_processed_event
