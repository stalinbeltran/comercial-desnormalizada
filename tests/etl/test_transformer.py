"""
Tests para etl/transformers/common.py.
Sin BD — puro pandas.
"""
import logging

import numpy as np
import pandas as pd
import pytest

from etl.transformers.common import clean

# Columnas required usadas en la mayoría de tests
REQ = ["id_producto", "id_presentacion", "id_bodega"]


def _df(**kwargs) -> pd.DataFrame:
    """Construye un DataFrame de una fila con las columnas dadas."""
    base = {"id_producto": 1, "id_presentacion": 1, "id_bodega": 1}
    base.update(kwargs)
    return pd.DataFrame([base])


# ── 1 ──────────────────────────────────────────────────────────────────────
def test_decimal_string_convertido_a_float():
    df = _df(stock_actual="1.5")
    result = clean(df, required=REQ)
    assert result["stock_actual"].iloc[0] == pytest.approx(1.5)


# ── 2 ──────────────────────────────────────────────────────────────────────
def test_decimal_none_convertido_a_cero():
    df = _df(stock_actual=None)
    result = clean(df, required=REQ)
    assert result["stock_actual"].iloc[0] == 0.0


# ── 3 ──────────────────────────────────────────────────────────────────────
def test_decimal_no_parseable_convertido_a_cero():
    df = _df(stock_actual="abc")
    result = clean(df, required=REQ)
    assert result["stock_actual"].iloc[0] == 0.0


# ── 4 ──────────────────────────────────────────────────────────────────────
def test_datetime_string_iso_convertido():
    df = _df(created_at="2025-06-01 10:00:00")
    result = clean(df, required=REQ)
    assert pd.api.types.is_datetime64_any_dtype(result["created_at"])


# ── 5 ──────────────────────────────────────────────────────────────────────
def test_date_columna_queda_como_date():
    df = _df(fecha_emision="2025-06-01")
    result = clean(df, required=REQ)
    val = result["fecha_emision"].iloc[0]
    # debe ser datetime.date, no Timestamp
    import datetime
    assert isinstance(val, datetime.date) and not isinstance(val, pd.Timestamp)


# ── 6 ──────────────────────────────────────────────────────────────────────
def test_nan_convertido_a_none():
    df = _df(observacion=float("nan"))
    result = clean(df, required=REQ)
    assert result["observacion"].iloc[0] is None


# ── 7 ──────────────────────────────────────────────────────────────────────
def test_fila_con_required_nulo_descartada():
    df = pd.DataFrame([
        {"id_producto": 1, "id_presentacion": 1, "id_bodega": 1},
        {"id_producto": None, "id_presentacion": 1, "id_bodega": 1},
    ])
    result = clean(df, required=REQ)
    assert len(result) == 1
    assert result["id_producto"].iloc[0] == 1


# ── 8 ──────────────────────────────────────────────────────────────────────
def test_fila_con_nulo_en_col_opcional_conservada():
    df = pd.DataFrame([
        {"id_producto": 1, "id_presentacion": 1, "id_bodega": 1, "observacion": None},
    ])
    result = clean(df, required=REQ)
    assert len(result) == 1


# ── 9 ──────────────────────────────────────────────────────────────────────
def test_dataframe_entrada_no_mutado():
    df = _df(stock_actual="abc", created_at="2025-01-01 00:00:00")
    original = df.copy()
    clean(df, required=REQ)
    pd.testing.assert_frame_equal(df, original)


# ── 10 ─────────────────────────────────────────────────────────────────────
def test_warning_loggeado_al_descartar_filas(caplog):
    df = pd.DataFrame([
        {"id_producto": 1,    "id_presentacion": 1, "id_bodega": 1},
        {"id_producto": None, "id_presentacion": 1, "id_bodega": 1},
        {"id_producto": None, "id_presentacion": 2, "id_bodega": 1},
    ])
    with caplog.at_level(logging.WARNING, logger="etl.transformers.common"):
        clean(df, required=REQ)
    assert any("2" in msg for msg in caplog.messages), \
        "Se esperaba un WARNING indicando cuántas filas fueron descartadas"
