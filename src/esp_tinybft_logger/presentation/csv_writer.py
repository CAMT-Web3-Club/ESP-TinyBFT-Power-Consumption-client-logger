import csv
import os
from types import TracebackType
from typing import TextIO

from esp_tinybft_logger.shared.models import CounterEvent

_HEADER = [
    "ntp_timestamp",
    "level",
    "tag",
    "event_type",
    "message",
    "counter_value",
    "status",
    "rtt_ms",
    "raw_line",
]


class CsvWriter:
    def __init__(self, path: str) -> None:
        self._path = path
        self._file: TextIO | None = None
        self._writer: csv.DictWriter | None = None
        self._header_written = os.path.exists(path)

    def __enter__(self) -> CsvWriter:
        self._file = open(self._path, "a", newline="")
        self._writer = csv.DictWriter(self._file, fieldnames=_HEADER)
        if not self._header_written:
            self._writer.writeheader()
            self._header_written = True
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        if self._file is not None:
            self._file.close()
            self._file = None
            self._writer = None

    def write(self, event: CounterEvent) -> None:
        row = event.model_dump()
        if self._writer is not None and self._file is not None:
            self._writer.writerow(row)
            self._file.flush()
