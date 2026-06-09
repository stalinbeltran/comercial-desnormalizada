import logging
import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from sqlalchemy import text

logger = logging.getLogger(__name__)

_DEAD_LETTERS = Path(__file__).parent.parent / "dead_letters"


def _rows_for_mysql(df: pd.DataFrame) -> list[dict]:
    """Convierte pandas.Timestamp → datetime nativo; mysql.connector no acepta Timestamp."""
    rows = []
    for record in df.to_dict(orient="records"):
        rows.append({
            k: (v.to_pydatetime() if isinstance(v, pd.Timestamp) else v)
            for k, v in record.items()
        })
    return rows


def upsert(df: pd.DataFrame, tabla: str, engine, unique_cols: list[str]) -> int:
    """INSERT … ON DUPLICATE KEY UPDATE. Devuelve rowcount de MySQL."""
    if df.empty:
        return 0

    cols         = list(df.columns)
    placeholders = ", ".join(f":{c}" for c in cols)
    update_set   = ", ".join(f"{c}=VALUES({c})" for c in cols if c not in unique_cols)
    sql = (
        f"INSERT INTO {tabla} ({', '.join(cols)}) "
        f"VALUES ({placeholders}) "
        f"ON DUPLICATE KEY UPDATE {update_set}"
    )
    rows = _rows_for_mysql(df)

    with engine.begin() as conn:
        result = conn.execute(text(sql), rows)

    return result.rowcount


def upsert_chunk_safe(
    df: pd.DataFrame,
    tabla: str,
    engine,
    unique_cols: list[str],
    chunk_index: int,
) -> int:
    """Ejecuta upsert; ante error guarda el chunk en dead_letters y retorna 0."""
    try:
        return upsert(df, tabla, engine, unique_cols)
    except Exception as exc:
        logger.error(
            "Error en chunk %d de %s: %s — guardando en dead_letters",
            chunk_index, tabla, exc,
        )
        _save_dead_letter(df, tabla, chunk_index)
        return 0


def _save_dead_letter(df: pd.DataFrame, tabla: str, chunk_index: int) -> None:
    _DEAD_LETTERS.mkdir(parents=True, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = _DEAD_LETTERS / f"{tabla}_{ts}_chunk{chunk_index:04d}.csv"
    df.to_csv(path, index=False)
    logger.warning("Dead letter guardado: %s", path)
