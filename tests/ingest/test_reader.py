import asyncio
from unittest.mock import MagicMock, patch

import pytest
import serial

from esp_tinybft_logger.ingest.reader import read_serial


class TestReadSerial:
    @pytest.mark.asyncio
    async def test_yields_empty_on_timeout(self) -> None:
        with patch("serial.Serial") as mock_serial:
            mock_ser = MagicMock()
            mock_ser.readline.return_value = b""
            mock_serial.return_value.__enter__.return_value = mock_ser

            gen = read_serial("/dev/null", 115200)
            result = await asyncio.wait_for(anext(gen), timeout=2)
            assert result == ""

    @pytest.mark.asyncio
    async def test_yields_line_on_data(self) -> None:
        with patch("serial.Serial") as mock_serial:
            mock_ser = MagicMock()
            mock_ser.readline.return_value = b"some data\n"
            mock_serial.return_value.__enter__.return_value = mock_ser

            gen = read_serial("/dev/null", 115200)
            result = await asyncio.wait_for(anext(gen), timeout=2)
            assert result == "some data"

    @pytest.mark.asyncio
    async def test_yields_disconnected_on_serial_error(self) -> None:
        with patch("serial.Serial") as mock_serial:
            mock_serial.side_effect = serial.SerialException("port not found")

            gen = read_serial("/dev/null", 115200)
            result = await asyncio.wait_for(anext(gen), timeout=2)
            assert result == "SERIAL_DISCONNECTED"
