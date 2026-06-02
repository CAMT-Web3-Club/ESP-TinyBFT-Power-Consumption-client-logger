---
name: python-standard
description: >
  Python 3.14t coding standards for this project. VSA project structure,
  strict full type hints, functional-first design with OOP fallback.
  Covers modern syntax (match/case, type unions, type aliases, deferred
  annotations), asyncio patterns, pydantic frozen models, ruff linting,
  ty type checking, uv package manager. Use ONLY when writing, editing,
  or reviewing Python code in this repo.
---

# Python Standard — 3.14t (free-threaded)

## 1. Python Version

- **3.14t** — free-threaded, no-GIL. Officially supported (PEP 703, PEP 779).
- 5–10 % single-thread performance penalty over GIL build. Worth it for parallelism.
- Pin with `uv python pin 3.14t`.
- `requires-python = ">=3.14"` in `pyproject.toml`.

## 2. Syntax Requirements

### Union types (3.10+)

```python
# ✅
def parse(raw: str) -> ParsedLog | None: ...
field: int | None = None

# ❌
from typing import Optional
field: Optional[int] = None
```

### Type aliases (3.12+)

```python
# ✅ type keyword
type FilterFn = Callable[[CounterEvent], bool]
type EventQueue = asyncio.Queue[CounterEvent]

# ❌ bare assignment — does not declare a type alias
FilterFn = Callable[[CounterEvent], bool]
```

### Deferred annotations (PEP 649/749 — 3.14 default)

Annotations are deferred by default. No `from __future__ import annotations` needed.
Forward references work naturally without string quoting.

```python
# ✅ Works in 3.14 — no strings, no future import
class EventStream:
    _subscribers: list[asyncio.Queue[CounterEvent]] = []

# If runtime evaluation is needed:
from annotationlib import get_annotations, Format
annotations = get_annotations(cls, format=Format.VALUE)
```

### Match/case with guards (3.10+)

Prefer over if-elif chains or method dispatch for branching.

```python
match event_type:
    case "timeout" if not warmup: ...
    case "increment": ...
    case "reply": ...
    case _: ...
```

### Walrus operator (3.8+)

```python
if parsed := parse_line(raw):
    process(parsed)
```

### Override decorator (3.12+)

```python
from typing import override

class SerialReader(Thread):
    @override
    def run(self) -> None: ...
```

### Bracketless except (PEP 758 — 3.14)

```python
try:
    connect()
except TimeoutError, ConnectionRefusedError:
    retry()
```

### Generator type hints

```python
from collections.abc import AsyncGenerator, Generator

def lines() -> Generator[str, None, None]: ...
async def events() -> AsyncGenerator[CounterEvent, None]: ...
```

## 3. Type Hints — Strict & Complete

Every function, method, parameter, and return type **must** be fully annotated.
No `Any`. No bare generics (`list` → `list[str]`).

```python
# ✅
def process(events: dict[str, CounterEvent], limit: int) -> list[StatsSummary]: ...
async def read_serial(port: str, baud: int) -> AsyncGenerator[str, None]: ...

# ❌
def process(events, limit): ...
def foo(x: list) -> dict: ...
```

## 4. Design Principles

1. **Pure functions first.** Same input → same output. No hidden side effects.
   No mutation of shared state. Compose through pipelines.

2. **Data as immutable values.** Use `frozen=True` Pydantic models.
   Thread-safe by construction.

3. **Errors as exceptions.** This is Python — exceptions are idiomatic.
   Do not force Rust-style `Result` types.

4. **Classes for state, not behavior.** Only use classes when a piece of shared
   mutable state needs to live across operations. No inheritance unless forced
   by stdlib. No public setters. `__init__` initializes fields only — no side effects.

5. **Compose, do not nest.** Prefer chaining transformations through generators /
   comprehensions over deeply nested loops.

6. **No comments.** Code is self-documenting through types, naming, and structure.
   Add comments only if the user explicitly asks.

### Composition example

```python
# ✅ Pipeline — each step is a pure(ish) function
def enrich_logs(
    lines: AsyncGenerator[str, None],
    ntp: NTPClient,
) -> AsyncGenerator[CounterEvent, None]:
    async for raw in lines:
        if parsed := parse_line(raw):
            yield enrich(parsed, ntp.now_iso())

# ❌ Deep nesting with side effects
def handle(self):
    for raw in self._lines:
        if raw:
            parsed = parse(raw)
            if parsed and parsed.tag == "counter":
                self._events.append(parsed)
                self._write_file(parsed)
                self._display.render(parsed)
```

## 5. VSA Project Structure

Organize by **business capability** (what the app does), not by technical layer
(what a file is).

```
src/
  esp_tinybft_logger/
    __init__.py
    shared/                  # Cross-cutting — used by all slices
      __init__.py
      models.py              # Pydantic: ParsedLog, CounterEvent, StatsSummary
      config.py              # AppConfig, CLI args model
    ingest/                  # Slice: data from serial into system
      __init__.py
      reader.py              # Async serial reader
      parser.py              # ESP-IDF log line parser
    pipeline/                # Slice: transform & enrich stream
      __init__.py
      stream.py              # EventStream — async fan-out
      ntp.py                 # NTP timestamp enricher
    analysis/                # Slice: metrics computation
      __init__.py
      engine.py              # MetricsEngine — polars + warmup gate
      stats.py               # Pure functions: build StatsSummary
    presentation/            # Slice: output
      __init__.py
      dashboard.py           # Rich Layout TUI
      csv_writer.py          # CSV append writer
  main.py                    # Entry point — wires slices
```

### Rules

- Slices import only from `shared/` — never from other slices.
- `main.py` is the **only** place slices are wired together.
- No slice knows about how upstream/downstream slices work.

## 6. Async Patterns

- `asyncio` everywhere. Threading-only for blocking I/O (serial `readline()`).
- `asyncio.TaskGroup` for spawning concurrent tasks (3.11+).
- `asyncio.Queue` for producer/consumer channels.
- Blocking I/O via `loop.run_in_executor()`.

```python
async def main() -> None:
    async with asyncio.TaskGroup() as tg:
        tg.create_task(consumer_a())
        tg.create_task(consumer_b())
        async for item in producer():
            await process(item)
```

## 7. Pydantic Models

```python
from pydantic import BaseModel

class ParsedLog(BaseModel):
    model_config = {"frozen": True}
    level: str
    esp_ticks: int
    tag: str
    message: str
    raw_line: str

class CounterEvent(BaseModel):
    model_config = {"frozen": True}
    ntp_timestamp: str
    level: str
    tag: str
    event_type: str
    message: str
    counter_value: int | None = None
    status: int | None = None
    rtt_ms: float | None = None
    raw_line: str
```

- Always `frozen=True` — immutable, thread-safe.
- Union syntax (`int | None`), never `Optional[int]`.
- Serialize with `.model_dump()`, copy with `.model_copy(update={...})`.

## 8. Package Manager — uv

```bash
uv add <pkg>        # runtime dep → pyproject.toml
uv add --dev <pkg>  # dev dep → [project.optional-dependencies]
uv run <tool>       # run in venv
uv sync             # sync env from lockfile
uv python pin 3.14t
```

## 9. Lint & Format — Ruff

```bash
uv run ruff check .      # lint
uv run ruff format .     # format
```

`pyproject.toml`:
```toml
[tool.ruff]
line-length = 100
target-version = "py314"

[tool.ruff.lint]
select = [
    "E",        # pycodestyle errors
    "F",        # pyflakes
    "W",        # pycodestyle warnings
    "I",        # isort import ordering
    "N",        # pep8-naming
    "UP",       # pyupgrade modern syntax
    "ANN001",   # missing function parameter annotations
    "ANN201",   # missing function return type annotations
]
```

Run before committing or completing any task.

## 10. Type Checking — Ty

```bash
uv run ty check .        # type check
```

Run after ruff. Zero errors allowed.

## 11. Naming

| Category   | Style        | Example              |
|------------|-------------|----------------------|
| Module     | snake_case   | `serial_reader.py`   |
| Package    | lowercase    | `esp_tinybft_logger` |
| Class      | PascalCase   | `MetricsEngine`      |
| Function   | snake_case   | `parse_line()`       |
| Variable   | snake_case   | `warmup_done`        |
| Constant   | UPPER        | `_PATTERN`           |
| Private    | `_` prefix   | `_warmup_skipped`    |

## 12. Import Order

Stdlib → third-party → local. One blank line between groups.

```python
import asyncio
from collections.abc import AsyncGenerator
from functools import partial

import polars as pl
from pydantic import BaseModel

from esp_tinybft_logger.shared.models import ParsedLog
```
