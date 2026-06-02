from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import ntplib

_BANGKOK = ZoneInfo("Asia/Bangkok")


class NTPClient:
    def __init__(self, host: str = "pool.ntp.org", tz: ZoneInfo = _BANGKOK) -> None:
        self._host = host
        self._tz = tz
        self._offset: float = 0.0
        self._synced = False

    def sync(self) -> bool:
        try:
            client = ntplib.NTPClient()
            response = client.request(self._host, version=3)
            self._offset = response.tx_time - datetime.now(UTC).timestamp()
            self._synced = True
            return True
        except ntplib.NTPException, OSError:
            self._synced = False
            return False

    def now_iso(self) -> str:
        utc_now = datetime.fromtimestamp(datetime.now(UTC).timestamp() + self._offset, tz=UTC)
        return utc_now.astimezone(self._tz).isoformat()

    @property
    def synced(self) -> bool:
        return self._synced

    @property
    def offset_ms(self) -> float:
        return round(self._offset * 1000, 1)

    @property
    def tz(self) -> ZoneInfo:
        return self._tz
