from datetime import datetime
from sqlalchemy import text

_CREATE = """
CREATE TABLE IF NOT EXISTS etl_watermarks (
    tabla      VARCHAR(100) PRIMARY KEY,
    last_run   DATETIME     NOT NULL,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
"""

_GET = "SELECT last_run FROM etl_watermarks WHERE tabla = :t"

_UPSERT = """
INSERT INTO etl_watermarks (tabla, last_run) VALUES (:t, :ts)
ON DUPLICATE KEY UPDATE last_run = :ts
"""

_DELETE = "DELETE FROM etl_watermarks WHERE tabla = :t"


def _ensure_table(conn) -> None:
    conn.execute(text(_CREATE))


def get_watermark(engine, tabla: str) -> datetime | None:
    with engine.connect() as conn:
        _ensure_table(conn)
        conn.commit()
        row = conn.execute(text(_GET), {"t": tabla}).fetchone()
    return row[0] if row else None


def set_watermark(engine, tabla: str, ts: datetime) -> None:
    with engine.begin() as conn:
        _ensure_table(conn)
        conn.execute(text(_UPSERT), {"t": tabla, "ts": ts})


def clear_watermark(engine, tabla: str) -> None:
    with engine.begin() as conn:
        conn.execute(text(_DELETE), {"t": tabla})
