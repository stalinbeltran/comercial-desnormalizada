"""
Tests para etl/pipeline.py.
Mezcla de ejecución real (con BDs vacías) y mocks del extractor.
"""
import logging
from datetime import datetime, timedelta

import pytest

from etl import pipeline
from etl.watermark import get_watermark
from tests.etl.helpers.db_etl_helpers import (
    contar_filas, leer_campo, truncar_tablas_destino,
)

_TODAS = ["d_inventario", "d_movimientos_inventario",
          "d_facturas", "d_facturas_detalle", "d_ordenes_compra"]


@pytest.fixture(autouse=True)
def _estado_limpio(engine_destino):
    """Watermarks limpios y tablas destino truncadas antes/después de cada test."""
    from sqlalchemy import text
    truncar_tablas_destino(engine_destino, _TODAS)
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))
    yield
    truncar_tablas_destino(engine_destino, _TODAS)
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))


# ── 1 ──────────────────────────────────────────────────────────────────────
def test_run_sin_args_ejecuta_cinco_tablas():
    results = pipeline.run()
    assert len(results) == 5
    nombres = {r["tabla"] for r in results}
    assert nombres == set(_TODAS)


# ── 2 ──────────────────────────────────────────────────────────────────────
def test_run_tabla_unica_retorna_un_resultado():
    results = pipeline.run(tables=["d_facturas"])
    assert len(results) == 1
    assert results[0]["tabla"] == "d_facturas"


# ── 3 ──────────────────────────────────────────────────────────────────────
def test_run_tabla_inexistente_retorna_lista_vacia(caplog):
    with caplog.at_level(logging.WARNING, logger="etl.pipeline"):
        results = pipeline.run(tables=["tabla_que_no_existe"])
    assert results == []
    assert any("coincide" in m.lower() or "tabla_que_no_existe" in m
               for m in caplog.messages)


# ── 4 ──────────────────────────────────────────────────────────────────────
def test_full_refresh_trunca_tabla_destino(engine_destino):
    from sqlalchemy import text
    # pre-cargar una fila en destino
    with engine_destino.begin() as conn:
        conn.execute(text("""
            INSERT INTO d_ordenes_compra
                (id_orden_orig, id_proveedor, proveedor, fecha_emision,
                 estado, total)
            VALUES (99999, 9000, 'Test', '2025-01-01', 'pendiente', 1)
        """))
    pipeline.run(tables=["d_ordenes_compra"], full_refresh=True)
    # El full-refresh trunca el destino → la fila pre-cargada debe haber desaparecido
    assert leer_campo(engine_destino, "d_ordenes_compra",
                      "id_orden_orig", 99999, "id_orden_orig") is None


# ── 5 ──────────────────────────────────────────────────────────────────────
def test_full_refresh_borra_watermark(engine_destino):
    from sqlalchemy import text
    from etl.watermark import set_watermark
    set_watermark(engine_destino, "d_ordenes_compra", datetime(2025, 1, 1))
    pipeline.run(tables=["d_ordenes_compra"], full_refresh=True)
    # después del full-refresh el watermark se re-crea con el timestamp de esta ejecución
    wm = get_watermark(engine_destino, "d_ordenes_compra")
    assert wm is not None
    assert wm >= datetime(2025, 1, 1)


# ── 6 ──────────────────────────────────────────────────────────────────────
def test_watermark_guardado_dentro_de_ventana_de_ejecucion(engine_destino):
    before = datetime.now() - timedelta(seconds=1)
    pipeline.run(tables=["d_ordenes_compra"])
    after = datetime.now() + timedelta(seconds=1)
    wm = get_watermark(engine_destino, "d_ordenes_compra")
    assert wm is not None
    assert before <= wm <= after


# ── 7 ──────────────────────────────────────────────────────────────────────
def test_extractor_error_no_aborta_otras_tablas():
    cfg = next(c for c in pipeline.TABLES if c.dest_table == "d_ordenes_compra")
    original = cfg.extractor

    def _roto(engine, watermark, chunksize):
        raise RuntimeError("fallo simulado en extractor")
        yield  # pragma: no cover

    cfg.extractor = _roto
    try:
        results = pipeline.run(tables=["d_inventario", "d_ordenes_compra"])
    finally:
        cfg.extractor = original

    nombres = {r["tabla"] for r in results}
    assert "d_inventario" in nombres
    assert "d_ordenes_compra" in nombres


# ── 8 ──────────────────────────────────────────────────────────────────────
def test_resultado_error_tiene_campo_error_poblado():
    cfg = next(c for c in pipeline.TABLES if c.dest_table == "d_ordenes_compra")
    original = cfg.extractor

    def _roto(engine, watermark, chunksize):
        raise RuntimeError("error esperado en test")
        yield  # pragma: no cover

    cfg.extractor = _roto
    try:
        results = pipeline.run(tables=["d_ordenes_compra"])
    finally:
        cfg.extractor = original

    assert results[0]["error"] is not None
    assert "error esperado" in results[0]["error"]


# ── 9 ──────────────────────────────────────────────────────────────────────
def test_stats_son_numeros_validos():
    results = pipeline.run(tables=["d_ordenes_compra"])
    r = results[0]
    assert isinstance(r["leidas"], int)    and r["leidas"]   >= 0
    assert isinstance(r["rowcount"], int)  and r["rowcount"] >= 0
    assert isinstance(r["chunks"], int)    and r["chunks"]   >= 0
    assert isinstance(r["segundos"], float) and r["segundos"] >= 0
