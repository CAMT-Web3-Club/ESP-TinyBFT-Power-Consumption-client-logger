import asyncio
from collections.abc import AsyncGenerator

import serial


async def read_serial(port: str, baud: int) -> AsyncGenerator[str]:
    loop = asyncio.get_running_loop()
    while True:
        try:
            with serial.Serial(port, baud, timeout=1) as ser:
                while True:
                    raw = await loop.run_in_executor(None, ser.readline)
                    yield raw.decode(errors="replace").strip()
        except (serial.SerialException, OSError):
            yield "SERIAL_DISCONNECTED"
            await asyncio.sleep(2)
