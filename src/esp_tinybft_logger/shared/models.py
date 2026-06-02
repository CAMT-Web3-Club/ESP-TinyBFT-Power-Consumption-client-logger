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
    raw_line: str


class StatsSummary(BaseModel):
    counter_value: int = 0
    total_increments: int = 0
    total_replies: int = 0
    total_timeouts: int = 0
    warmup_timeouts_skipped: int = 0
    success_rate_pct: float = 0.0
    avg_rtt_ms: float = 0.0
    max_rtt_ms: float = 0.0
    ops_per_minute: float = 0.0
    uptime_seconds: int = 0
    ntp_synced: bool = False
    warmup_done: bool = False
