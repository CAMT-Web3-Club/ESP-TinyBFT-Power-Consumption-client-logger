import argparse
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from rich.console import Console
from rich.prompt import IntPrompt, Prompt

from esp_tinybft_logger.analysis.engine import MetricsEngine
from esp_tinybft_logger.ingest.reader import read_serial
from esp_tinybft_logger.pipeline.ntp import NTPClient
from esp_tinybft_logger.pipeline.processor import process_lines
from esp_tinybft_logger.presentation.cli_printer import CliPrinter
from esp_tinybft_logger.presentation.csv_writer import CsvWriter
from esp_tinybft_logger.shared.config import AppConfig


def _parse_args() -> AppConfig:
    ap = argparse.ArgumentParser(description="ESP-TinyBFT Counter Serial Logger")
    ap.add_argument("--port", default=None, help="Serial port (e.g. /dev/ttyUSB0)")
    ap.add_argument("--baud", type=int, default=None, help="Baud rate")
    ap.add_argument("--csv", dest="csv_path", default=None, help="CSV output file path")
    ap.add_argument("--no-csv", action="store_true", help="Disable CSV logging")
    ap.add_argument("--ntp-host", default="pool.ntp.org", help="NTP server hostname")
    ap.add_argument("--timezone", default="Asia/Bangkok", help="Timezone (e.g. Asia/Bangkok)")
    ap.add_argument("--no-ntp", action="store_true", help="Skip NTP sync")
    args = ap.parse_args()

    console = Console()

    if args.port is None:
        args.port = Prompt.ask("Serial port", console=console, default="/dev/ttyACM0")

    if args.baud is None:
        args.baud = IntPrompt.ask("Baud rate", console=console, default=115200)

    if args.csv_path is None and not args.no_csv:
        args.csv_path = f"esp_log_{datetime.now():%Y%m%d_%H%M%S}.csv"
        console.print(f"CSV logging to [bold]{args.csv_path}[/bold]", style="dim")

    kwargs = {k: v for k, v in vars(args).items() if k != "no_csv"}
    return AppConfig(**kwargs)


async def main() -> None:
    cfg = _parse_args()
    tz = ZoneInfo(cfg.timezone)

    ntp = NTPClient(cfg.ntp_host, tz)
    ntp_synced = not cfg.no_ntp and ntp.sync()
    ntp_offset = ntp.offset_ms if ntp_synced else None

    metrics = MetricsEngine()
    printer = CliPrinter(cfg.port, cfg.baud, ntp_synced, ntp_offset, cfg.timezone)

    csv_ctx: CsvWriter | None = None
    csv_writer: CsvWriter | None = None

    if cfg.csv_path:
        csv_ctx = CsvWriter(cfg.csv_path)
        csv_writer = csv_ctx.__enter__()

    printer.print_startup()

    try:
        await process_lines(read_serial(cfg.port, cfg.baud), printer, metrics, ntp, csv_writer)
    except (KeyboardInterrupt, asyncio.CancelledError):
        printer.print_shutdown()
    finally:
        if csv_ctx is not None:
            csv_ctx.__exit__(None, None, None)


if __name__ == "__main__":
    asyncio.run(main())
