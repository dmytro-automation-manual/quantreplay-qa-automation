import psycopg
from psycopg.rows import dict_row

from framework import config


class DbClient:
    """Read-only access to the simulator database (schema `sim`, created by Liquibase)."""

    def __init__(self):
        self.conn = psycopg.connect(host=config.DB_HOST, port=config.DB_PORT, dbname=config.DB_NAME,
                                    user=config.DB_USER, password=config.DB_PASSWORD,
                                    row_factory=dict_row, autocommit=True)

    def query(self, sql: str, params: tuple = ()) -> list[dict]:
        with self.conn.cursor() as cur:
            cur.execute(sql, params)
            return cur.fetchall()

    def close(self):
        self.conn.close()
