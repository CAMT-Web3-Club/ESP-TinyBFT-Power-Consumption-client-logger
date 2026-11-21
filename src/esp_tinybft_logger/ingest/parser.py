import re

from esp_tinybft_logger.shared.models import ParsedLog

_PATTERN = re.compile(r"^(I|W|E|D)\s*\((\d+)\)\s*(\w+):\s*(.*)$")
_VALUE_RE = re.compile(r"value=(-?\d+)")
_STATUS_RE = re.compile(r"status=(-?\d+)")
_KV_RE = re.compile(r"(\w+)=(\S+)")


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
        # Current firmware: one CLIENT_STATS line after every request (WARN
        # level) and one BANNER line at boot.  Checked first: "fail=" in a
        # CLIENT_STATS line must not be taken for a timeout.
        case _ if msg_lower.startswith("client_stats "):
            return "stats"
        case _ if msg_lower.startswith("banner "):
            return "banner"
        # Older firmware (devlope/v0.2.9): INFO lines around each request.
        case _ if "sending increment" in msg_lower:
            return "increment"
        case _ if "reply: value=" in msg_lower:
            return "reply"
        # The older client's only failure line.  Not any "failed": transport
        # warnings such as "tx to ... failed: frame 1/1 not acknowledged"
        # are not request failures.
        case _ if "request failed or timed out" in msg_lower:
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


def extract_kv(message: str) -> dict[str, str]:
    """key=value pairs of a CLIENT_STATS or BANNER line."""
    return dict(_KV_RE.findall(message))


def kv_int(kv: dict[str, str], key: str) -> int | None:
    try:
        return int(kv[key])
    except KeyError, ValueError:
        return None
