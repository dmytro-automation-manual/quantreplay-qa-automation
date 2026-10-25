"""Environment-driven settings. The only place that reads environment variables.

Layer rule: imports nothing from the framework. Other layers never import this module;
the composition root (tests/conftest.py) reads the settings and passes plain values down.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FixSettings:
    host: str = os.getenv("FIX_HOST", "localhost")
    port: int = int(os.getenv("FIX_PORT", "9051"))
    sender_comp_id: str = os.getenv("FIX_SENDER", "CLIENT_XETRA")
    target_comp_id: str = os.getenv("FIX_TARGET", "SIM_XETRA")
    timeout: float = float(os.getenv("FIX_TIMEOUT", "5"))
    heartbeat: int = int(os.getenv("FIX_HEARTBEAT", "30"))


@dataclass(frozen=True)
class RestSettings:
    base_url: str = os.getenv("REST_URL", "http://localhost:9050/api")
    timeout: float = float(os.getenv("REST_TIMEOUT", "5"))


@dataclass(frozen=True)
class DbSettings:
    host: str = os.getenv("DB_HOST", "localhost")
    port: int = int(os.getenv("DB_PORT", "15432"))
    name: str = os.getenv("DB_NAME", "simdb")
    user: str = os.getenv("DB_USER", "sim")          # simulator's application user (read access to schema sim)
    password: str = os.getenv("DB_PASSWORD", "sim")


@dataclass(frozen=True)
class Settings:
    venue_id: str = os.getenv("VENUE", "XETRA")
    startup_timeout: float = float(os.getenv("SIM_STARTUP_TIMEOUT", "60"))
    fix: FixSettings = FixSettings()
    rest: RestSettings = RestSettings()
    db: DbSettings = DbSettings()
