"""Database transport. Knows nothing about the simulator schema: SQL in, rows (dicts) out."""
import logging

import psycopg
from psycopg.rows import dict_row

log = logging.getLogger("db")


class DbClient:
    def __init__(self, host: str, port: int, dbname: str, user: str, password: str):
        self._conn = psycopg.connect(host=host, port=port, dbname=dbname, user=user, password=password,
                                     row_factory=dict_row, autocommit=True)

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        log.info("SQL %s %s", " ".join(sql.split()), params or "")
        with self._conn.cursor() as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()
        log.info("rows: %d", len(rows))
        return rows

    def close(self) -> None:
        self._conn.close()
