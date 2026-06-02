from rich.console import Console
from rich.text import Text

from esp_tinybft_logger.shared.models import ParsedLog, StatsSummary

_COUNTER_COLOR = "cyan bold"
_WARN_COLOR = "yellow"
_ERROR_COLOR = "red"
_DIM_COLOR = "dim white"
_GREEN_COLOR = "green"
_RED_COLOR = "red"

_STATS_INTERVAL = 10


class CliPrinter:
    def __init__(
        self,
        port: str,
        baud: int,
        ntp_synced: bool,
        ntp_offset_ms: float | None,
        timezone: str,
    ) -> None:
        self._console = Console()
        self._line_count = 0
        self._stats = StatsSummary()
        self._esp_ticks = 0
        self._connected = True
        self._port = port
        self._baud = baud
        self._ntp_synced = ntp_synced
        self._ntp_offset_ms = ntp_offset_ms
        self._timezone = timezone

    def _get_style(self, level: str, is_counter: bool) -> str:
        if is_counter:
            return _COUNTER_COLOR
        match level:
            case "W":
                return _WARN_COLOR
            case "E":
                return _ERROR_COLOR
            case _:
                return _DIM_COLOR

    def print_log(self, parsed: ParsedLog, ntp_ts: str, is_counter: bool) -> None:
        ts_short = ntp_ts.split("T")[1].split(".")[0] if "T" in ntp_ts else ntp_ts
        style = self._get_style(parsed.level, is_counter)
        self._console.print(
            f"{ts_short} {parsed.level} {parsed.tag}: {parsed.message}", style=style
        )
        self._line_count += 1

    def print_stats_summary(self) -> None:
        s = self._stats
        total = s.total_replies + s.total_timeouts
        success_style = _GREEN_COLOR if s.success_rate_pct >= 90 else _WARN_COLOR
        warmup_style = _GREEN_COLOR if s.warmup_done else _WARN_COLOR

        text = Text()
        text.append(" ═══ ", style=_DIM_COLOR)
        text.append(f"Counter: {s.counter_value}", style=_COUNTER_COLOR)
        text.append(
            f"  Success: {s.success_rate_pct}% ({s.total_replies}/{total})",
            style=success_style,
        )
        text.append(f"  RTT: {s.avg_rtt_ms}ms (max {s.max_rtt_ms}ms)", style=_DIM_COLOR)
        text.append(f"  Ops/min: {s.ops_per_minute}", style=_DIM_COLOR)
        text.append(f"  Warmup: {'done' if s.warmup_done else 'pending'}", style=warmup_style)
        text.append(f"  Uptime: {_fmt_uptime(s.uptime_seconds)}", style=_DIM_COLOR)
        text.append(" ═══", style=_DIM_COLOR)
        self._console.print(text)

    def print_disconnected(self) -> None:
        self._console.print("[red]SERIAL DISCONNECTED[/red]")

    def print_startup(self) -> None:
        ntp = "synced" if self._ntp_synced else "local clock"
        offset = ""
        if self._ntp_synced and self._ntp_offset_ms is not None:
            sign = "+" if self._ntp_offset_ms >= 0 else ""
            offset = f" ({sign}{self._ntp_offset_ms}ms)"
        self._console.print(
            f"ESP-TinyBFT Logger — {self._port} @ {self._baud}"
            f" — NTP: {ntp}{offset} — TZ: {self._timezone}",
            style="bold",
        )
        self._console.print("Press Ctrl+C to exit", style="dim")

    def print_shutdown(self) -> None:
        self._console.print("\nShutting down...", style=_DIM_COLOR)

    def set_connected(self, connected: bool) -> None:
        self._connected = connected

    def update_stats(self, stats: StatsSummary) -> None:
        self._stats = stats

    def update_esp_ticks(self, ticks: int) -> None:
        self._esp_ticks = ticks

    @property
    def line_count(self) -> int:
        return self._line_count


def _fmt_uptime(seconds: int) -> str:
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h > 0:
        return f"{h}h {m:02d}m {s:02d}s"
    if m > 0:
        return f"{m}m {s:02d}s"
    return f"{s}s"
