from esp_tinybft_logger.pipeline.ntp import NTPClient


class TestNTPClientSync:
    def test_sync_unreachable_host(self) -> None:
        client = NTPClient(host="127.0.0.1")
        result = client.sync()
        assert result is False
        assert client.synced is False

    def test_unsynced_now_iso_uses_bangkok(self) -> None:
        client = NTPClient()
        ts = client.now_iso()
        assert ts.endswith("+07:00")

    def test_now_iso_with_utc_timezone(self) -> None:
        from zoneinfo import ZoneInfo

        client = NTPClient(tz=ZoneInfo("UTC"))
        ts = client.now_iso()
        assert ts.endswith("+00:00")

    def test_default_host(self) -> None:
        client = NTPClient()
        assert client._host == "pool.ntp.org"


class TestNTPClientTime:
    def test_offset_applied(self) -> None:
        client = NTPClient()
        client._synced = True
        client._offset = 0.0
        ts1 = client.now_iso()
        client._offset = 60.0
        ts2 = client.now_iso()
        assert ts1 != ts2

    def test_synced_property(self) -> None:
        client = NTPClient()
        assert client.synced is False
        client._synced = True
        assert client.synced is True


class TestNTPOffsetMs:
    def test_offset_ms_zero_when_not_synced(self) -> None:
        client = NTPClient()
        assert client.offset_ms == 0.0

    def test_offset_ms_converts_seconds_to_ms(self) -> None:
        client = NTPClient()
        client._synced = True
        client._offset = 0.0035
        assert client.offset_ms == 3.5

    def test_offset_ms_negative(self) -> None:
        client = NTPClient()
        client._synced = True
        client._offset = -0.002
        assert client.offset_ms == -2.0
