# ESP-TinyBFT Power Consumption Client Logger

Serial logger client for the [ESP-TinyBFT](https://github.com/CAMT-Web3-Club/ESP-TinyBFT-Power-Consumption) counter application.

Reads serial output from an ESP device running the TinyBFT consensus counter benchmark, parses log lines, computes real-time metrics (success rate, RTT, ops/min, uptime), and writes structured CSV data for post-processing with tools like Polars.

## Quick start

```bash
uv run src/main.py
```

Prompts for serial port and baud rate, then starts logging. Ctrl+C to exit.

## Usage

### Interactive (prompts for missing arguments)

```bash
uv run src/main.py
```

### All arguments provided

```bash
uv run src/main.py \
  --port /dev/ttyACM0 \
  --baud 115200 \
  --csv my_data.csv \
  --timezone Asia/Bangkok
```

### Options

| Argument | Default | Description |
|----------|---------|-------------|
| `--port` | prompt | Serial port (e.g. `/dev/ttyACM0`) |
| `--baud` | prompt | Baud rate |
| `--csv` | auto-generated | CSV output file path |
| `--no-csv` | — | Disable CSV logging |
| `--ntp-host` | `pool.ntp.org` | NTP server hostname |
| `--timezone` | `Asia/Bangkok` | Timezone |
| `--no-ntp` | — | Skip NTP sync |

CSV logging is enabled by default. If neither `--csv` nor `--no-csv` is given, a file named `esp_log_<YYYYMMDD_HHMMSS>.csv` is created automatically.

### Output

Colored log lines stream in real time:

```
ESP-TinyBFT Logger — /dev/ttyACM0 @ 115200 — NTP: synced (+3.5ms) — TZ: Asia/Bangkok
Press Ctrl+C to exit
14:32:01 I counter: Client sending increment...
14:32:01 I counter: Client reply: value=42, status=0
 ═══ Counter: 42  Success: 95% (19/20)  RTT: 344ms (max 512ms)  Ops/min: 23  Warmup: done  Uptime: 2m 34s ═══
```

- **Counter lines** in cyan
- **Warnings** in yellow
- **Errors** in red
- **Stats summary** every 10 lines

## Development

### Requirements

- Python >= 3.14
- [uv](https://docs.astral.sh/uv/)

### Setup

```bash
uv sync
```

### Tests

```bash
uv run pytest tests/
```

### Type checking

```bash
uv run ty check src/
```

### Linting

```bash
uv run ruff check .
```

## Project structure

```
src/
├── main.py                          # Entry point
└── esp_tinybft_logger/
    ├── analysis/
    │   ├── engine.py                # Metrics computation
    │   └── stats.py                 # StatsSummary builder
    ├── ingest/
    │   ├── parser.py                # Log line parser
    │   └── reader.py                # Serial port reader
    ├── pipeline/
    │   ├── ntp.py                   # NTP time sync
    ├── presentation/
    │   ├── cli_printer.py           # Colored terminal output
    │   └── csv_writer.py            # CSV file writer
    └── shared/
        ├── config.py                # AppConfig dataclass
        └── models.py                # Data models
```

## License

MIT
