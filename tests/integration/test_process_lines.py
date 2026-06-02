import os
import tempfile
from collections.abc import AsyncGenerator
from unittest.mock import patch

import pytest

from esp_tinybft_logger.analysis.engine import MetricsEngine
from esp_tinybft_logger.pipeline.ntp import NTPClient
from esp_tinybft_logger.pipeline.processor import process_lines
from esp_tinybft_logger.presentation.cli_printer import CliPrinter
from esp_tinybft_logger.presentation.csv_writer import CsvWriter


async def _lines(*lines: str) -> AsyncGenerator[str]:
    for line in lines:
        yield line


async def _empty() -> AsyncGenerator[str]:
    if False:
        yield  # pragma: no cover


@pytest.mark.asyncio
async def test_empty_input_no_output() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    with patch.object(printer._console, "print") as mock_print:
        await process_lines(_empty(), printer, MetricsEngine(), NTPClient(host="127.0.0.1"), None)
    assert mock_print.call_count == 0
    assert printer.line_count == 0


@pytest.mark.asyncio
async def test_empty_lines_skipped() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    with patch.object(printer._console, "print") as mock_print:
        await process_lines(
            _lines("", ""), printer, MetricsEngine(), NTPClient(host="127.0.0.1"), None
        )
    assert mock_print.call_count == 0


@pytest.mark.asyncio
async def test_single_counter_increment() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    ntp = NTPClient(host="127.0.0.1")
    metrics = MetricsEngine()
    line = "I (1000) counter: Client sending increment..."

    with (
        patch.object(printer._console, "print"),
    ):
        await process_lines(_lines(line), printer, metrics, ntp, None)

    assert printer.line_count == 1


@pytest.mark.asyncio
async def test_increment_then_reply_updates_metrics() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    ntp = NTPClient(host="127.0.0.1")
    metrics = MetricsEngine()
    inc = "I (1000) counter: Client sending increment..."
    reply = "I (1100) counter: Client reply: value=42, status=0"

    with patch.object(printer._console, "print"):
        await process_lines(_lines(inc, reply), printer, metrics, ntp, None)

    s = metrics.stats()
    assert printer.line_count == 2
    assert s.total_increments == 1
    assert s.total_replies == 1
    assert s.counter_value == 42


@pytest.mark.asyncio
async def test_non_counter_event() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    ntp = NTPClient(host="127.0.0.1")
    metrics = MetricsEngine()
    line = "W (5000) tbft_replica: view-change timeout in view 3 (keys=7/7)"

    with patch.object(printer._console, "print"):
        await process_lines(_lines(line), printer, metrics, ntp, None)

    assert printer.line_count == 1
    assert metrics.stats().total_increments == 0


@pytest.mark.asyncio
async def test_serial_disconnected() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    metrics = MetricsEngine()
    ntp = NTPClient(host="127.0.0.1")

    with (
        patch.object(printer._console, "print"),
    ):
        await process_lines(_lines("SERIAL_DISCONNECTED"), printer, metrics, ntp, None)

    assert printer._connected is False


@pytest.mark.asyncio
async def test_malformed_line_skipped() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    metrics = MetricsEngine()
    ntp = NTPClient(host="127.0.0.1")

    with (
        patch.object(printer._console, "print") as mock_print,
    ):
        await process_lines(_lines("garbage text here"), printer, metrics, ntp, None)

    assert mock_print.call_count == 0
    assert printer.line_count == 0


@pytest.mark.asyncio
async def test_stats_summary_at_interval() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    metrics = MetricsEngine()
    ntp = NTPClient(host="127.0.0.1")
    line = "I (1000) counter: Client sending increment..."

    with (
        patch.object(printer, "print_stats_summary") as mock_stats,
        patch.object(printer._console, "print"),
    ):
        await process_lines(_lines(*([line] * 12)), printer, metrics, ntp, None)

    # Stats should print at line 10 (1st call) but not at 12
    assert mock_stats.call_count == 1
    assert printer.line_count == 12


@pytest.mark.asyncio
async def test_stats_summary_at_20_lines() -> None:
    printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
    metrics = MetricsEngine()
    ntp = NTPClient(host="127.0.0.1")
    line = "I (1000) counter: Client sending increment..."

    with (
        patch.object(printer, "print_stats_summary") as mock_stats,
        patch.object(printer._console, "print"),
    ):
        await process_lines(_lines(*([line] * 22)), printer, metrics, ntp, None)

    # Stats should print at line 10 and line 20
    assert mock_stats.call_count == 2
    assert printer.line_count == 22


@pytest.mark.asyncio
async def test_with_csv_writer() -> None:
    import csv

    with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=True) as tmp:
        path = tmp.name

    try:
        printer = CliPrinter("/dev/null", 115200, False, None, "UTC")
        metrics = MetricsEngine()
        ntp = NTPClient(host="127.0.0.1")
        inc = "I (1000) counter: Client sending increment..."
        reply = "I (1100) counter: Client reply: value=42, status=0"

        with (
            patch.object(printer._console, "print"),
        ):
            with CsvWriter(path) as writer:
                await process_lines(_lines(inc, reply), printer, metrics, ntp, writer)

        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            rows = list(reader)

        assert len(rows) == 2  # 2 events
        # First row is increment (should not have counter_value, status, or rtt_ms)
        assert rows[0]["event_type"] == "increment"
        assert rows[0]["rtt_ms"] == ""

        # Second row is reply
        assert rows[1]["event_type"] == "reply"
        assert rows[1]["counter_value"] == "42"
        assert rows[1]["status"] == "0"
        # RTT should be populated (either 0.0 or a real duration)
        assert rows[1]["rtt_ms"] != ""
        assert float(rows[1]["rtt_ms"]) >= 0.0

        assert printer.line_count == 2
    finally:
        if os.path.exists(path):
            os.unlink(path)
