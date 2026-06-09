"""
Tests de integración end-to-end del ETL.
Ambas BDs con datos reales. Usa d_ordenes_compra por ser la tabla más simple
(menor cadena de dependencias FK). El CHUNK_SIZE se parchea a 3 para tests
de límite de chunk sin necesidad de insertar miles de filas.
"""
from datetime import datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import text

from etl import pipeline
from etl.watermark import get_watermark, set_watermark
from tests.etl.helpers.db_etl_helpers import (
    contar_filas, delete_ordenes_compra, insert_orden_compra, leer_campo,
    truncar_tablas_destino,
)

_DEST = "d_ordenes_compra"
_SMALL_CHUNK = 3


@pytest.fixture(autouse=True)
def _limpio(engine_origen, engine_destino, seed_maestros):
    """Limpia tablas y watermarks antes/después de cada test."""
    truncar_tablas_destino(engine_destino, [_DEST])
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks WHERE tabla = :t"),
                     {"t": _DEST})
    yield
    delete_ordenes_compra(engine_origen,
                          list(range(9001, 9020)))  # limpia todos los posibles seeds
    truncar_tablas_destino(engine_destino, [_DEST])
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks WHERE tabla = :t"),
                     {"t": _DEST})


def _run_oc(**kwargs):
    return pipeline.run(tables=[_DEST], **kwargs)


# ── 1 ──────────────────────────────────────────────────────────────────────
def test_bootstrap_filas_fuente_igualan_destino(engine_origen, engine_destino):
    # Watermark = ahora; seed con updated_at futuro → solo el seed se extrae
    set_watermark(engine_destino, _DEST, datetime.now())
    insert_orden_compra(engine_origen, 9001, updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")
    insert_orden_compra(engine_origen, 9002, updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")

    results = _run_oc()

    assert results[0]["error"] is None
    # Ambos seeds en dest (sin mezcla de datos reales gracias al watermark)
    dest_seed = contar_filas(engine_destino, f"{_DEST} WHERE id_orden_orig IN (9001, 9002)")
    assert dest_seed == 2


# ── 2 ──────────────────────────────────────────────────────────────────────
def test_segunda_ejecucion_sin_cambios_rowcount_cero(engine_origen):
    insert_orden_compra(engine_origen, 9001)
    _run_oc()
    results = _run_oc()
    # MySQL rowcount para ON DUPLICATE KEY sin cambio = 0
    assert results[0]["rowcount"] == 0


# ── 3 ──────────────────────────────────────────────────────────────────────
def test_modificacion_en_fuente_actualiza_destino(engine_origen, engine_destino):
    set_watermark(engine_destino, _DEST, datetime.now())
    insert_orden_compra(engine_origen, 9001, total=100.0,
                        updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")
    _run_oc()

    # modificar en fuente con updated_at definitivamente posterior al watermark actual
    with engine_origen.begin() as conn:
        conn.execute(text(
            "UPDATE ordenes_compra SET total = 999.99, "
            "updated_at = DATE_ADD(NOW(), INTERVAL 2 HOUR) WHERE id = 9001"
        ))

    _run_oc()

    total_dest = leer_campo(engine_destino, _DEST, "id_orden_orig", 9001, "total")
    assert float(total_dest) == pytest.approx(999.99)


# ── 4 ──────────────────────────────────────────────────────────────────────
def test_nuevo_registro_aparece_en_destino(engine_origen, engine_destino):
    set_watermark(engine_destino, _DEST, datetime.now())
    insert_orden_compra(engine_origen, 9001, updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")
    _run_oc()
    count_seed_antes = contar_filas(engine_destino,
                                    f"{_DEST} WHERE id_orden_orig IN (9001, 9002)")

    insert_orden_compra(engine_origen, 9002, updated_at="DATE_ADD(NOW(), INTERVAL 2 HOUR)")
    _run_oc()

    count_seed_despues = contar_filas(engine_destino,
                                      f"{_DEST} WHERE id_orden_orig IN (9001, 9002)")
    assert count_seed_despues == count_seed_antes + 1


# ── 5 ──────────────────────────────────────────────────────────────────────
def test_soft_delete_en_maestro_excluye_fila(engine_origen, engine_destino):
    """Si el proveedor (tercero) tiene deleted_at, la fila no debe aparecer en destino."""
    set_watermark(engine_destino, _DEST, datetime.now())
    insert_orden_compra(engine_origen, 9001, updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")
    with engine_origen.begin() as conn:
        conn.execute(text("UPDATE terceros SET deleted_at = NOW() WHERE id = 9000"))
    try:
        _run_oc()
        # Solo el seed era candidato; excluido por deleted_at → 0 filas del seed en dest
        filas = contar_filas(engine_destino, f"{_DEST} WHERE id_orden_orig = 9001")
        assert filas == 0
    finally:
        with engine_origen.begin() as conn:
            conn.execute(text("UPDATE terceros SET deleted_at = NULL WHERE id = 9000"))


# ── 6 ──────────────────────────────────────────────────────────────────────
def test_full_refresh_produce_mismo_resultado_que_bootstrap(engine_origen,
                                                             engine_destino):
    insert_orden_compra(engine_origen, 9001)
    insert_orden_compra(engine_origen, 9002)
    _run_oc()
    count_bootstrap = contar_filas(engine_destino, _DEST)

    _run_oc(full_refresh=True)

    assert contar_filas(engine_destino, _DEST) == count_bootstrap


# ── 7 ──────────────────────────────────────────────────────────────────────
def test_fuente_vacia_sin_error(engine_destino):
    # Watermark = ahora → datos pre-existentes excluidos; nada nuevo insertado
    set_watermark(engine_destino, _DEST, datetime.now())
    results = _run_oc()
    assert results[0]["error"] is None
    assert results[0]["leidas"] == 0


# ── 8 ──────────────────────────────────────────────────────────────────────
def test_exactamente_chunk_size_filas(engine_origen, engine_destino):
    # Watermark = ahora, seed con updated_at en el futuro → solo el seed pasa el filtro
    set_watermark(engine_destino, _DEST, datetime.now())
    for i in range(1, _SMALL_CHUNK + 1):
        insert_orden_compra(engine_origen, 9000 + i, numero=f"OC-ETL-{i:03d}",
                            updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")

    with patch("etl.pipeline.CHUNK_SIZE", _SMALL_CHUNK):
        results = _run_oc()

    assert results[0]["error"]   is None
    assert results[0]["chunks"]  == 1
    assert results[0]["leidas"]  == _SMALL_CHUNK
    assert contar_filas(engine_destino, _DEST) == _SMALL_CHUNK


# ── 9 ──────────────────────────────────────────────────────────────────────
def test_chunk_size_mas_uno_genera_dos_chunks(engine_origen, engine_destino):
    total = _SMALL_CHUNK + 1
    # Watermark = ahora, seed con updated_at en el futuro → solo el seed pasa el filtro
    set_watermark(engine_destino, _DEST, datetime.now())
    for i in range(1, total + 1):
        insert_orden_compra(engine_origen, 9000 + i, numero=f"OC-ETL-{i:03d}",
                            updated_at="DATE_ADD(NOW(), INTERVAL 1 HOUR)")

    with patch("etl.pipeline.CHUNK_SIZE", _SMALL_CHUNK):
        results = _run_oc()

    assert results[0]["error"]  is None
    assert results[0]["chunks"] == 2
    assert contar_filas(engine_destino, _DEST) == total


# ── 10 ─────────────────────────────────────────────────────────────────────
def test_razon_social_con_caracteres_especiales(engine_origen, engine_destino):
    with engine_origen.begin() as conn:
        conn.execute(text(
            "UPDATE terceros SET razon_social = 'Proveedor Ñ & \"Test\" SA' WHERE id = 9000"
        ))
    insert_orden_compra(engine_origen, 9001)
    try:
        _run_oc()
        proveedor = leer_campo(engine_destino, _DEST, "id_orden_orig", 9001, "proveedor")
        assert "Ñ" in proveedor
        assert "&" in proveedor
    finally:
        with engine_origen.begin() as conn:
            conn.execute(text(
                "UPDATE terceros SET razon_social = 'Proveedor ETL SA' WHERE id = 9000"
            ))


# ── 11 ─────────────────────────────────────────────────────────────────────
def test_decimal_maximo_sin_perdida_de_precision(engine_origen, engine_destino):
    total_exacto = 99999999999.9999  # cerca del límite DECIMAL(15,4)
    insert_orden_compra(engine_origen, 9001, total=total_exacto)
    _run_oc()
    total_dest = leer_campo(engine_destino, _DEST, "id_orden_orig", 9001, "total")
    assert float(total_dest) == pytest.approx(total_exacto, rel=1e-6)
