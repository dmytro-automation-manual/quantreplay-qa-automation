"""Environment-driven settings. The only place that reads environment variables.

Layer rule: imports nothing from the framework. Other layers never import this module;
the composition root (tests/conftest.py) reads the settings and passes plain values down.
Ports and CompIDs belong to each venue and are in test_data/markets.py.
"""
import os
from dataclasses import dataclass


@dataclass(frozen=True)
class FixSettings:
    host: str = os.getenv("FIX_HOST", "localhost")
    timeout: float = float(os.getenv("FIX_TIMEOUT", "5"))
    heartbeat: int = int(os.getenv("FIX_HEARTBEAT", "30"))


@dataclass(frozen=True)
class RestSettings:
    host: str = os.getenv("REST_HOST", "localhost")
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
    startup_timeout: float = float(os.getenv("SIM_STARTUP_TIMEOUT", "60"))
    fix: FixSettings = FixSettings()
    rest: RestSettings = RestSettings()
    db: DbSettings = DbSettings()
