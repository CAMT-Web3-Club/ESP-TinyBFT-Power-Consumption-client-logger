# ESP-TinyBFT Power Consumption Client Logger

Serial logger client for the [ESP-TinyBFT](https://github.com/CAMT-Web3-Club/esp-tinybft) counter application.

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
 ═══ Counter: 42  Success: 95% (19/20)  RTT: 344ms (max 512ms)  Ops/min: 23  Warm-up: first OK 41s after boot  Uptime: 2m 34s ═══
```

### Firmware versions

The logger reads either format the counter client prints:

- **Current firmware** (esp-tinybft `fix/develop/v0.2.9` and later, log level
  WARN): one `CLIENT_STATS ok=… fail=… missed=… last_ms=…` line after every
  request and a `BANNER preset=… load=…` line at boot. Success, failures and
  missed slots are the board's own counters (totals are kept across a client
  reboot), and RTT is the board's `last_ms` of every new success. A run lasts
  from power-on until the batteries are empty, so nothing is left out: the
  requests that fail while the cluster comes up count like the rest, and the
  first success after boot is in RTT. The summary reports the warm-up instead
  (`Warm-up: first OK 3m 19s after boot, 9 failed before`).
  The client may stay powered between runs while only the replicas run on
  batteries. Then start the logger when the batteries go in: if its first
  `CLIENT_STATS` line comes without a `BANNER` before it, the client was
  already running, its counters so far are taken as the baseline and the run
  is counted from the logger's start (`first OK … after start`; the request of
  that first line is not counted, as it cannot be told whether it succeeded).
  If the client boots while the logger runs, the run is counted from that boot.
  Firmware that adds `value=` to `CLIENT_STATS` (the counter in the last
  accepted reply, -1 before the first) shows `Counter:` again, and
  `Agreed, no reply: N` when the counter jumped by more than the client's
  successes: the replicas executed those requests, but the client did not get
  f+1 matching replies and counted them as failures. `executed` is counted
  from the run's first success to the latest one. The summary shows `OK:` instead of
  `Counter:` (CLIENT_STATS has no counter value), plus preset/load and missed
  slots; the CSV gets the columns `ok`, `fail`, `missed`, `preset`, `load`.
- **Older firmware** (`devlope/v0.2.9`, log level INFO): the
  `Client sending increment...`, `Client reply: value=…` and
  `Request failed or timed out.` lines, with RTT timed on the host.

Start a new CSV file for each run: appending to a CSV written by an older
version of the logger mixes two column layouts.

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
