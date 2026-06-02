import re

from esp_tinybft_logger.shared.models import ParsedLog

_PATTERN = re.compile(r"^(I|W|E|D)\s*\((\d+)\)\s*(\w+):\s*(.*)$")
_VALUE_RE = re.compile(r"value=(-?\d+)")
_STATUS_RE = re.compile(r"status=(-?\d+)")


def parse_line(raw: str) -> ParsedLog | None:
    stripped = raw.strip()
    if m := _PATTERN.match(stripped):
        level, ticks, tag, msg = m.groups()
        return ParsedLog(
            level=level,
            esp_ticks=int(ticks),
            tag=tag,
            message=msg,
            raw_line=raw,
        )
    return None


def event_type(message: str) -> str:
    msg_lower = message.lower()
    match msg_lower:
        case _ if "sending increment" in msg_lower:
            return "increment"
        case _ if "reply: value=" in msg_lower:
            return "reply"
        case _ if "timed out" in msg_lower or "failed" in msg_lower:
            return "timeout"
        case _:
            return ""


def extract_value(message: str) -> int | None:
    if m := _VALUE_RE.search(message):
        return int(m.group(1))
    return None


def extract_status(message: str) -> int | None:
    if m := _STATUS_RE.search(message):
        return int(m.group(1))
    return None
