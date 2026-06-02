from collections.abc import AsyncGenerator

from esp_tinybft_logger.analysis.engine import MetricsEngine
from esp_tinybft_logger.ingest.parser import (
    event_type,
    extract_status,
    extract_value,
    parse_line,
)
from esp_tinybft_logger.pipeline.ntp import NTPClient
from esp_tinybft_logger.presentation.cli_printer import CliPrinter
from esp_tinybft_logger.presentation.csv_writer import CsvWriter
from esp_tinybft_logger.shared.models import CounterEvent


async def process_lines(
    raw_lines: AsyncGenerator[str],
    printer: CliPrinter,
    metrics: MetricsEngine,
    ntp: NTPClient,
    csv_writer: CsvWriter | None,
) -> None:
    async for raw in raw_lines:
        if not raw:
            continue

        match raw:
            case "SERIAL_DISCONNECTED":
                printer.set_connected(False)
                printer.print_disconnected()
                continue
            case _:
                printer.set_connected(True)
                parsed = parse_line(raw)

        if parsed is None:
            continue

        ts = ntp.now_iso()
        is_counter = parsed.tag == "counter"

        printer.print_log(parsed, ts, is_counter)
        printer.update_esp_ticks(parsed.esp_ticks)

        if is_counter:
            event = CounterEvent(
                ntp_timestamp=ts,
                level=parsed.level,
                tag=parsed.tag,
                event_type=event_type(parsed.message),
                message=parsed.message,
                counter_value=extract_value(parsed.message),
                status=extract_status(parsed.message),
                raw_line=parsed.raw_line,
            )
        else:
            event = CounterEvent(
                ntp_timestamp=ts,
                level=parsed.level,
                tag=parsed.tag,
                event_type="",
                message=parsed.message,
                raw_line=parsed.raw_line,
            )

        metrics.process(event)
        printer.update_stats(metrics.stats())

        processed_event = metrics.last_processed_event or event

        if csv_writer is not None:
            csv_writer.write(processed_event)

        if printer.line_count % 10 == 0:
            printer.print_stats_summary()
