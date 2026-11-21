from pydantic import BaseModel


class ParsedLog(BaseModel):
    model_config = {"frozen": True}

    level: str
    esp_ticks: int
    tag: str
    message: str
    raw_line: str


class CounterEvent(BaseModel):
    model_config = {"frozen": True}

    ntp_timestamp: str
    level: str
    tag: str
    event_type: str
    message: str
    counter_value: int | None = None
    status: int | None = None
    rtt_ms: float | None = None
    # From CLIENT_STATS (counters of the current client boot) and BANNER.
    ok: int | None = None
    fail: int | None = None
    missed: int | None = None
    preset: str | None = None
    load: str | None = None
    raw_line: str


class StatsSummary(BaseModel):
    counter_value: int = 0
    total_increments: int = 0
    total_replies: int = 0
    total_timeouts: int = 0
    total_missed: int = 0
    preset: str | None = None
    load: str | None = None
    source: str = "log"
    # Warm-up: everything before the first successful request is counted
    # like the rest of the run; these fields only describe it.
    warmup_timeouts: int = 0
    # When the run's first success came, in seconds from first_ok_from:
    # "boot" (the client booted while logging) or "start" (of the logger).
    first_ok_s: float | None = None
    first_ok_from: str | None = None
    success_rate_pct: float = 0.0
    avg_rtt_ms: float = 0.0
    max_rtt_ms: float = 0.0
    ops_per_minute: float = 0.0
    uptime_seconds: int = 0
    ntp_synced: bool = False
    warmup_done: bool = False
