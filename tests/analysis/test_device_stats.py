"""Current firmware: CLIENT_STATS and BANNER lines (WARN level).

The lines below are copied from a client log of the board runs
(esp-tinybft fix/develop/v0.2.9, preset en1, 10 s load).
"""

import os
import tempfile
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest

from esp_tinybft_logger.analysis.engine import MetricsEngine
from esp_tinybft_logger.ingest.parser import event_type, extract_kv, kv_int, parse_line
from esp_tinybft_logger.pipeline.ntp import NTPClient
from esp_tinybft_logger.pipeline.processor import process_lines
from esp_tinybft_logger.presentation.cli_printer import CliPrinter
from esp_tinybft_logger.presentation.csv_writer import CsvWriter

_BANNER = (
    "W (356) counter: BANNER preset=en1 load=p10 req_interval_ms=10000 role=client "
    "role_from=list id=7 transport=espnow if=sta rate=0 retries=3 txp_dbm=8"
)
_STATS = [
    "W (12246) counter: CLIENT_STATS ok=1 fail=0 missed=0 last_ms=6965 min_ms=6965 "
    "avg_ms=6965 max_ms=6965",
    "W (17327) counter: CLIENT_STATS ok=2 fail=0 missed=0 last_ms=1698 min_ms=1698 "
    "avg_ms=4331 max_ms=6965",
    "W (27139) counter: CLIENT_STATS ok=3 fail=0 missed=0 last_ms=1697 min_ms=1697 "
    "avg_ms=3453 max_ms=6965",
]
# A failed request: last_ms is the failed attempt, not a success.
_STATS_FAIL = (
    "W (57181) counter: CLIENT_STATS ok=3 fail=1 missed=1 last_ms=20012 min_ms=1697 "
    "avg_ms=3453 max_ms=6965"
)


async def _lines(*lines: str) -> AsyncGenerator[str]:
    for line in lines:
        yield line


async def _run(*lines: str, csv_path: str | None = None) -> MetricsEngine:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    metrics = MetricsEngine()
    with patch.object(printer._console, "print"):
        if csv_path is None:
            await process_lines(_lines(*lines), printer, metrics, NTPClient("127.0.0.1"), None)
        else:
            with CsvWriter(csv_path) as w:
                await process_lines(_lines(*lines), printer, metrics, NTPClient("127.0.0.1"), w)
    return metrics


class TestParser:
    def test_stats_event(self) -> None:
        parsed = parse_line(_STATS[0])
        assert parsed is not None
        assert parsed.level == "W"
        assert parsed.tag == "counter"
        assert event_type(parsed.message) == "stats"

    def test_stats_with_fail_is_not_timeout(self) -> None:
        parsed = parse_line(_STATS_FAIL)
        assert parsed is not None
        assert event_type(parsed.message) == "stats"

    def test_banner_event(self) -> None:
        parsed = parse_line(_BANNER)
        assert parsed is not None
        assert event_type(parsed.message) == "banner"

    def test_extract_kv(self) -> None:
        parsed = parse_line(_STATS[1])
        assert parsed is not None
        kv = extract_kv(parsed.message)
        assert kv_int(kv, "ok") == 2
        assert kv_int(kv, "last_ms") == 1698
        assert kv_int(kv, "nothing") is None

    def test_wifi_lines_are_not_timeouts(self) -> None:
        for line in (
            "W (13021) counter: WiFi disconnected (attempt 1) reason=201 rssi=-71 "
            "t_ms=13021, reconnecting...",
            "W (2801) counter: WiFi associated ch=6 rssi=-58 bssid=aa:bb:cc:dd:ee:ff "
            "after 0 retries",
            "W (3305) counter: WiFi got IP t_ms=3305 after 0 retries",
        ):
            parsed = parse_line(line)
            assert parsed is not None
            assert event_type(parsed.message) == ""

    def test_old_lines_unchanged(self) -> None:
        assert event_type("Client sending increment...") == "increment"
        assert event_type("Client reply: value=42, status=0") == "reply"
        assert event_type("Request failed or timed out.") == "timeout"


class TestDeviceMetrics:
    @pytest.mark.asyncio
    async def test_counts_and_rtt(self) -> None:
        stats = (await _run(_BANNER, *_STATS)).stats()
        assert stats.source == "device"
        assert stats.total_replies == 3
        assert stats.total_timeouts == 0
        assert stats.success_rate_pct == 100.0
        # Every success counts, the first one after boot (6965 ms) included.
        assert stats.avg_rtt_ms == round((6965 + 1698 + 1697) / 3, 1)
        assert stats.max_rtt_ms == 6965.0
        assert stats.first_ok_boot_s == 12.246
        assert stats.warmup_timeouts == 0
        assert stats.preset == "en1"
        assert stats.load == "p10"
        assert stats.warmup_done is True

    @pytest.mark.asyncio
    async def test_failure_counted_without_rtt(self) -> None:
        stats = (await _run(_BANNER, *_STATS, _STATS_FAIL)).stats()
        assert stats.total_replies == 3
        assert stats.total_timeouts == 1
        assert stats.total_missed == 1
        assert stats.success_rate_pct == 75.0
        assert stats.max_rtt_ms == 6965.0  # 20012 ms of the failure is not an RTT

    @pytest.mark.asyncio
    async def test_client_reboot_keeps_totals(self) -> None:
        # Second BANNER: the client rebooted and its counters start again.
        stats = (await _run(_BANNER, *_STATS, _BANNER, *_STATS[:2])).stats()
        assert stats.total_replies == 5

    @pytest.mark.asyncio
    async def test_wifi_lines_change_nothing(self) -> None:
        wifi = (
            "W (13021) counter: WiFi disconnected (attempt 1) reason=204 rssi=-80 "
            "t_ms=13021, reconnecting..."
        )
        stats = (await _run(_BANNER, wifi, *_STATS, wifi)).stats()
        assert stats.total_replies == 3
        assert stats.total_timeouts == 0
        assert stats.warmup_timeouts == 0

    @pytest.mark.asyncio
    async def test_reboot_without_banner(self) -> None:
        stats = (await _run(*_STATS, _STATS[0])).stats()
        assert stats.total_replies == 4

    @pytest.mark.asyncio
    async def test_csv_has_device_columns(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "out.csv")
            await _run(_BANNER, *_STATS, csv_path=path)
            with open(path) as f:
                header, *rows = f.read().splitlines()
        assert header.split(",")[:13] == [
            "ntp_timestamp", "level", "tag", "event_type", "message", "counter_value",
            "status", "rtt_ms", "ok", "fail", "missed", "preset", "load",
        ]  # fmt: skip
        last = rows[-1]
        assert ",stats," in last
        assert ",1697.0,3,0,0,en1,p10," in last


class TestWarmup:
    """The board run of 2026-11-21: 9 failures while the replicas came up."""

    @pytest.mark.asyncio
    async def test_failures_before_first_success_are_counted(self) -> None:
        fails = [
            f"W ({20000 * i}) counter: CLIENT_STATS ok=0 fail={i} missed=0 last_ms=20780 "
            "min_ms=0 avg_ms=0 max_ms=0"
            for i in range(1, 10)
        ]
        transport = (
            "W (1234) tbft_espnow: tx to 88:56:a6:5b:f2:f0 failed: frame 1/1 not acknowledged"
        )
        ok = [
            "W (199000) counter: CLIENT_STATS ok=1 fail=9 missed=0 last_ms=18879 "
            "min_ms=18879 avg_ms=18879 max_ms=18879",
            "W (214000) counter: CLIENT_STATS ok=2 fail=9 missed=0 last_ms=14360 "
            "min_ms=14360 avg_ms=16619 max_ms=18879",
        ]
        stats = (await _run(_BANNER, transport, *fails, transport, *ok)).stats()
        assert stats.total_replies == 2
        assert stats.total_timeouts == 9
        assert stats.success_rate_pct == round(2 / 11 * 100, 1)
        assert stats.warmup_timeouts == 9
        assert stats.first_ok_boot_s == 199.0
        assert stats.avg_rtt_ms == round((18879 + 14360) / 2, 1)

    def test_transport_failure_is_not_a_request_failure(self) -> None:
        assert event_type("tx to 88:56:a6:5b:f2:f0 failed: frame 1/1 not acknowledged") != "timeout"
