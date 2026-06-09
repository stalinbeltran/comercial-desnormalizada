"""
Tests para etl/loaders/upsert.py.
Solo BD destino — usa d_ordenes_compra como tabla de prueba.
"""
from pathlib import Path

import pandas as pd
import pytest
from sqlalchemy import text

from etl.loaders.upsert import upsert, upsert_chunk_safe

_TABLA = "d_ordenes_compra"
_UNIQUE = ["id_orden_orig"]


def _fila(id_orig: int = 9001, proveedor: str = "Acme ETL",
          total: float = 100.0, **extra) -> dict:
    base = {
        "id_orden_orig": id_orig, "id_proveedor": 9000,
        "proveedor": proveedor, "fecha_emision": "2025-01-10",
        "estado": "pendiente", "total": total,
        "created_at": "2025-01-10 00:00:00",
        "updated_at": "2025-01-10 00:00:00",
        "deleted_at": None,
    }
    base.update(extra)
    return base


@pytest.fixture(autouse=True)
def _truncar(engine_destino):
    with engine_destino.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {_TABLA}"))
    yield
    with engine_destino.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {_TABLA}"))


# ── 1 ──────────────────────────────────────────────────────────────────────
def test_upsert_dataframe_vacio_retorna_cero(engine_destino):
    rc = upsert(pd.DataFrame(), _TABLA, engine_destino, _UNIQUE)
    assert rc == 0


# ── 2 ──────────────────────────────────────────────────────────────────────
def test_upsert_inserta_filas_nuevas(engine_destino):
    df = pd.DataFrame([_fila(9001), _fila(9002)])
    upsert(df, _TABLA, engine_destino, _UNIQUE)
    with engine_destino.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {_TABLA}")).scalar()
    assert count == 2


# ── 3 ──────────────────────────────────────────────────────────────────────
def test_upsert_actualiza_fila_existente(engine_destino):
    df1 = pd.DataFrame([_fila(9001, total=100.0)])
    df2 = pd.DataFrame([_fila(9001, total=999.99)])
    upsert(df1, _TABLA, engine_destino, _UNIQUE)
    upsert(df2, _TABLA, engine_destino, _UNIQUE)
    with engine_destino.connect() as conn:
        total = conn.execute(
            text(f"SELECT total FROM {_TABLA} WHERE id_orden_orig = 9001")
        ).scalar()
    assert float(total) == pytest.approx(999.99)


# ── 4 ──────────────────────────────────────────────────────────────────────
def test_upsert_no_duplica_en_segunda_ejecucion(engine_destino):
    df = pd.DataFrame([_fila(9001)])
    upsert(df, _TABLA, engine_destino, _UNIQUE)
    upsert(df, _TABLA, engine_destino, _UNIQUE)
    with engine_destino.connect() as conn:
        count = conn.execute(text(f"SELECT COUNT(*) FROM {_TABLA}")).scalar()
    assert count == 1


# ── 5 ──────────────────────────────────────────────────────────────────────
def test_upsert_none_en_col_nullable_inserta_null(engine_destino):
    df = pd.DataFrame([_fila(9001, deleted_at=None)])
    upsert(df, _TABLA, engine_destino, _UNIQUE)
    with engine_destino.connect() as conn:
        val = conn.execute(
            text(f"SELECT deleted_at FROM {_TABLA} WHERE id_orden_orig = 9001")
        ).scalar()
    assert val is None


# ── 6 ──────────────────────────────────────────────────────────────────────
def test_upsert_chunk_safe_ante_excepcion_no_relanza(engine_destino):
    df = pd.DataFrame([_fila(9001)])
    # tabla inválida provoca error en MySQL
    rc = upsert_chunk_safe(df, "tabla_que_no_existe", engine_destino, _UNIQUE,
                           chunk_index=1)
    assert rc == 0


# ── 7 ──────────────────────────────────────────────────────────────────────
def test_upsert_chunk_safe_crea_dead_letter(engine_destino, tmp_path, monkeypatch):
    from etl.loaders import upsert as upsert_mod
    monkeypatch.setattr(upsert_mod, "_DEAD_LETTERS", tmp_path)

    df = pd.DataFrame([_fila(9001)])
    upsert_chunk_safe(df, "tabla_inexistente", engine_destino, _UNIQUE, chunk_index=7)

    csvs = list(tmp_path.glob("*.csv"))
    assert len(csvs) == 1
    nombre = csvs[0].name
    assert "tabla_inexistente" in nombre
    assert "0007" in nombre  # chunk_index formateado con 4 dígitos
