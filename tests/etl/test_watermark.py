"""
Tests para etl/watermark.py.
No usan datos de negocio — solo la tabla etl_watermarks en comercial_desn_db.
"""
from datetime import datetime

import pytest

from etl.watermark import clear_watermark, get_watermark, set_watermark

TABLA = "d_facturas_test_wm"  # nombre ficticio, no debe existir en TABLES


@pytest.fixture(autouse=True)
def _limpiar(engine_destino):
    """Borra cualquier watermark residual del nombre de prueba antes y después."""
    from sqlalchemy import text
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks WHERE tabla = :t"), {"t": TABLA})
    yield
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks WHERE tabla = :t"), {"t": TABLA})


# ── 1 ──────────────────────────────────────────────────────────────────────
def test_get_watermark_sin_registro_retorna_none(engine_destino):
    assert get_watermark(engine_destino, TABLA) is None


# ── 2 ──────────────────────────────────────────────────────────────────────
def test_get_watermark_con_registro_retorna_datetime(engine_destino):
    ts = datetime(2025, 3, 15, 10, 30, 0)
    set_watermark(engine_destino, TABLA, ts)
    assert get_watermark(engine_destino, TABLA) == ts


# ── 3 ──────────────────────────────────────────────────────────────────────
def test_set_watermark_primera_vez_crea_fila(engine_destino):
    from sqlalchemy import text
    ts = datetime(2025, 1, 1)
    set_watermark(engine_destino, TABLA, ts)
    with engine_destino.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM etl_watermarks WHERE tabla = :t"), {"t": TABLA}
        ).scalar()
    assert count == 1


# ── 4 ──────────────────────────────────────────────────────────────────────
def test_set_watermark_segunda_vez_no_duplica(engine_destino):
    from sqlalchemy import text
    ts1 = datetime(2025, 1, 1)
    ts2 = datetime(2025, 6, 1)
    set_watermark(engine_destino, TABLA, ts1)
    set_watermark(engine_destino, TABLA, ts2)

    with engine_destino.connect() as conn:
        count = conn.execute(
            text("SELECT COUNT(*) FROM etl_watermarks WHERE tabla = :t"), {"t": TABLA}
        ).scalar()
    assert count == 1
    assert get_watermark(engine_destino, TABLA) == ts2


# ── 5 ──────────────────────────────────────────────────────────────────────
def test_clear_watermark_con_registro_deja_none(engine_destino):
    set_watermark(engine_destino, TABLA, datetime(2025, 1, 1))
    clear_watermark(engine_destino, TABLA)
    assert get_watermark(engine_destino, TABLA) is None


# ── 6 ──────────────────────────────────────────────────────────────────────
def test_clear_watermark_sin_registro_no_lanza(engine_destino):
    clear_watermark(engine_destino, TABLA)  # no debe lanzar


# ── 7 ──────────────────────────────────────────────────────────────────────
def test_ensure_table_crea_tabla_si_no_existe(engine_destino):
    """
    La tabla etl_watermarks debe existir después de llamar a cualquier función
    del módulo, incluso en una BD recién creada.
    """
    from sqlalchemy import text, inspect
    inspector = inspect(engine_destino)
    # si get_watermark no lanza, la tabla fue creada exitosamente
    result = get_watermark(engine_destino, TABLA)
    assert result is None
    assert "etl_watermarks" in inspector.get_table_names()
