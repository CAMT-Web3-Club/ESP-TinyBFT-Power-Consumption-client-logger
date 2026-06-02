from unittest.mock import patch

from esp_tinybft_logger.presentation.cli_printer import CliPrinter
from esp_tinybft_logger.shared.models import ParsedLog, StatsSummary


def _make_log(tag: str = "counter", message: str = "test") -> ParsedLog:
    return ParsedLog(
        level="I",
        esp_ticks=5000,
        tag=tag,
        message=message,
        raw_line=f"I (5000) {tag}: {message}",
    )


class TestCliPrinterInit:
    def test_starts_connected(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        assert p._connected is True

    def test_starts_line_count_zero(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        assert p.line_count == 0

    def test_starts_empty_stats(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        assert p._stats.counter_value == 0


class TestCliPrinterLog:
    def test_print_log_increments_line_count(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        with patch.object(p._console, "print"):
            p.print_log(_make_log(), "2026-06-01T14:00:00.000+07:00", False)
        assert p.line_count == 1

    def test_print_log_counter_style(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        with patch.object(p._console, "print") as mock_print:
            p.print_log(_make_log(), "2026-06-01T14:00:00.000+07:00", True)
        assert mock_print.called
        style = mock_print.call_args[1]["style"]
        assert "cyan" in style or "bold" in style


class TestCliPrinterUpdates:
    def test_set_connected(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        p.set_connected(False)
        assert p._connected is False
        p.set_connected(True)
        assert p._connected is True

    def test_update_stats(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        stats = StatsSummary(counter_value=42)
        p.update_stats(stats)
        assert p._stats.counter_value == 42

    def test_update_esp_ticks(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        p.update_esp_ticks(12345)
        assert p._esp_ticks == 12345


class TestCliPrinterOutput:
    def test_print_startup(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, True, 3.5, "Asia/Bangkok")
        with patch.object(p._console, "print") as mock_print:
            p.print_startup()
        assert mock_print.call_count == 2

    def test_print_shutdown(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        with patch.object(p._console, "print") as mock_print:
            p.print_shutdown()
        assert mock_print.called

    def test_print_disconnected(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "Asia/Bangkok")
        with patch.object(p._console, "print") as mock_print:
            p.print_disconnected()
        assert mock_print.called

    def test_print_stats_summary(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, True, 3.5, "Asia/Bangkok")
        p.update_stats(StatsSummary(counter_value=42, total_replies=50, total_timeouts=2))
        with patch.object(p._console, "print") as mock_print:
            p.print_stats_summary()
        assert mock_print.called

    def test_print_startup_without_ntp(self) -> None:
        p = CliPrinter("/dev/ttyUSB0", 115200, False, None, "UTC")
        with patch.object(p._console, "print") as mock_print:
            p.print_startup()
        assert mock_print.called
