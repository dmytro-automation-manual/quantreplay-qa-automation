import os

FIX_HOST = os.getenv("FIX_HOST", "localhost")
FIX_PORT = int(os.getenv("FIX_PORT", "9051"))
FIX_SENDER = os.getenv("FIX_SENDER", "CLIENT_XETRA")
FIX_TARGET = os.getenv("FIX_TARGET", "SIM_XETRA")
FIX_TIMEOUT = float(os.getenv("FIX_TIMEOUT", "5"))

REST_URL = os.getenv("REST_URL", "http://localhost:9050")

VENUE = os.getenv("VENUE", "XETRA")
SYMBOL = os.getenv("SYMBOL", "VOW")

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", "15432"))
DB_NAME = os.getenv("DB_NAME", "simdb")
DB_USER = os.getenv("DB_USER", "sim")          # simulator's application user (market_simulator.xml)
DB_PASSWORD = os.getenv("DB_PASSWORD", "sim")
