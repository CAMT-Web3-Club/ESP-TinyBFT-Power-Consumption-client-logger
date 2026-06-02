import os
import tempfile

from esp_tinybft_logger.presentation.csv_writer import CsvWriter
from esp_tinybft_logger.shared.models import CounterEvent

_SAMPLE = CounterEvent(
    ntp_timestamp="2026-06-01T14:32:01.467+00:00",
    level="I",
    tag="counter",
    event_type="reply",
    message="Client reply: value=42, status=0",
    counter_value=42,
    status=0,
    rtt_ms=344.0,
    raw_line="I (12800) counter: Client reply: value=42, status=0",
)


class TestCsvWriter:
    def test_creates_file_with_header(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=True) as tmp:
            path = tmp.name

        try:
            with CsvWriter(path) as writer:
                writer.write(_SAMPLE)

            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 2
            assert lines[0].startswith("ntp_timestamp")
            assert "42" in lines[1]
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_appends_rows(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=True) as tmp:
            path = tmp.name

        try:
            with CsvWriter(path) as writer:
                writer.write(_SAMPLE)
                writer.write(_SAMPLE)

            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 3
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_header_only_once(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=True) as tmp:
            path = tmp.name

        try:
            with CsvWriter(path) as writer:
                writer.write(_SAMPLE)

            with CsvWriter(path) as writer2:
                writer2.write(_SAMPLE)

            with open(path) as f:
                lines = f.readlines()
            assert len(lines) == 3
            assert lines[0].startswith("ntp_timestamp")
            assert not lines[1].startswith("ntp_timestamp")
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_double_exit_safe(self) -> None:
        with tempfile.NamedTemporaryFile(mode="r", suffix=".csv", delete=True) as tmp:
            path = tmp.name

        try:
            with CsvWriter(path) as writer:
                writer.write(_SAMPLE)
            writer.__exit__(None, None, None)
        finally:
            if os.path.exists(path):
                os.unlink(path)
