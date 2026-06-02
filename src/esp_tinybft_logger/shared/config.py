from dataclasses import dataclass


@dataclass(frozen=True)
class AppConfig:
    port: str
    baud: int = 115200
    csv_path: str | None = None
    ntp_host: str = "pool.ntp.org"
    timezone: str = "Asia/Bangkok"
    no_ntp: bool = False
