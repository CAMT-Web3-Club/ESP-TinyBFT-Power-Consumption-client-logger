import pytest

from esp_tinybft_logger.ingest.parser import (
    event_type,
    extract_status,
    extract_value,
    parse_line,
)


class TestParseLine:
    def test_valid_increment(self) -> None:
        raw = "I (12345) counter: Client sending increment..."
        result = parse_line(raw)
        assert result is not None
        assert result.level == "I"
        assert result.esp_ticks == 12345
        assert result.tag == "counter"
        assert result.message == "Client sending increment..."
        assert result.raw_line == raw

    def test_valid_warning(self) -> None:
        raw = "W (35000) tbft_replica: view-change timeout"
        result = parse_line(raw)
        assert result is not None
        assert result.level == "W"
        assert result.tag == "tbft_replica"

    def test_valid_error(self) -> None:
        raw = "E (100) tbft_node: transport init failed"
        result = parse_line(raw)
        assert result is not None
        assert result.level == "E"

    def test_valid_debug(self) -> None:
        raw = "D (999) tbft_udp: some debug message"
        result = parse_line(raw)
        assert result is not None
        assert result.level == "D"

    def test_no_space_before_parens(self) -> None:
        raw = "I(5000)counter:message"
        result = parse_line(raw)
        assert result is not None
        assert result.level == "I"
        assert result.esp_ticks == 5000
        assert result.tag == "counter"
        assert result.message == "message"

    def test_empty_string(self) -> None:
        assert parse_line("") is None

    def test_garbage(self) -> None:
        assert parse_line("garbage text here") is None

    def test_missing_ticks(self) -> None:
        assert parse_line("I counter: no ticks") is None

    def test_whitespace_only(self) -> None:
        assert parse_line("   ") is None
        assert parse_line("\n") is None


class TestEventType:
    @pytest.mark.parametrize(
        ("msg", "expected"),
        [
            ("Client sending increment...", "increment"),
            ("client sending increment...", "increment"),
            ("Client reply: value=42, status=0", "reply"),
            ("client reply: value=1, status=0", "reply"),
            ("Request failed or timed out.", "timeout"),
            ("request failed or timed out.", "timeout"),
            ("some random log message", ""),
            ("", ""),
        ],
    )
    def test_event_type(self, msg: str, expected: str) -> None:
        assert event_type(msg) == expected


class TestExtractValue:
    def test_extract_positive(self) -> None:
        assert extract_value("Client reply: value=42, status=0") == 42

    def test_extract_zero(self) -> None:
        assert extract_value("Client reply: value=0, status=0") == 0

    def test_extract_negative(self) -> None:
        assert extract_value("Client reply: value=-5, status=1") == -5

    def test_no_value(self) -> None:
        assert extract_value("Client sending increment...") is None

    def test_empty(self) -> None:
        assert extract_value("") is None


class TestExtractStatus:
    def test_extract_zero(self) -> None:
        assert extract_status("Client reply: value=42, status=0") == 0

    def test_extract_nonzero(self) -> None:
        assert extract_status("Client reply: value=0, status=-1") == -1

    def test_no_status(self) -> None:
        assert extract_status("Client sending increment...") is None
