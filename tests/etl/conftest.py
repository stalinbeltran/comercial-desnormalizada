"""
Fixtures compartidas para el test suite del ETL.
Usa las mismas BDs de desarrollo (comercial_db / comercial_desn_db).
Los seeds usan IDs ≥ 9000 para no colisionar con los 901-9xx del conftest principal.
"""
import sys
from pathlib import Path

# Garantiza que la raíz del proyecto esté en sys.path al colectar estos tests
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import os
import pytest
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

from tests.etl.helpers.db_etl_helpers import (
    delete_maestros, insert_maestros, truncar_tablas_destino,
)

load_dotenv()

# UNIQUE KEY constraints requeridas por el upsert del ETL
_UNIQUE_KEYS = [
    ("d_inventario",            "uk_inv_prod_pres_bod", "id_producto, id_presentacion, id_bodega"),
    ("d_movimientos_inventario","uk_mov_orig",           "id_movimiento_orig"),
    ("d_facturas",              "uk_fac_orig",           "id_factura_orig"),
    ("d_facturas_detalle",      "uk_det_orig",           "id_detalle_orig"),
    ("d_ordenes_compra",        "uk_oc_orig",            "id_orden_orig"),
]

_ALL_DEST_TABLES = [
    "d_inventario", "d_movimientos_inventario",
    "d_facturas", "d_facturas_detalle", "d_ordenes_compra",
]


# ---------------------------------------------------------------------------
# Engines (session-scoped: caros de crear)
# ---------------------------------------------------------------------------

def _engine(user_var, pass_var, host_var, port_var, name_var):
    url = (
        f"mysql+mysqlconnector://{os.environ[user_var]}:{os.environ[pass_var]}"
        f"@{os.environ[host_var]}:{os.environ[port_var]}/{os.environ[name_var]}"
        "?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True, pool_recycle=3600)


@pytest.fixture(scope="session")
def engine_origen():
    eng = _engine("DB_USER", "DB_PASSWORD", "DB_HOST", "DB_PORT", "DB_NAME")
    yield eng
    eng.dispose()


@pytest.fixture(scope="session")
def engine_destino():
    eng = _engine("DB_DESN_USER", "DB_DESN_PASSWORD",
                  "DB_DESN_HOST", "DB_DESN_PORT", "DB_DESN_NAME")
    yield eng
    eng.dispose()


# ---------------------------------------------------------------------------
# Migración de UNIQUE KEYs (una sola vez por sesión)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def apply_unique_keys(engine_destino):
    with engine_destino.begin() as conn:
        for tabla, key, cols in _UNIQUE_KEYS:
            try:
                conn.execute(text(
                    f"ALTER TABLE {tabla} ADD CONSTRAINT {key} UNIQUE KEY ({cols})"
                ))
            except Exception as e:
                if "Duplicate key name" not in str(e) and "1061" not in str(e):
                    raise


# ---------------------------------------------------------------------------
# Maestros reutilizables (session-scoped: se insertan una vez y se borran al final)
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def seed_maestros(engine_origen):
    insert_maestros(engine_origen)
    yield
    delete_maestros(engine_origen)


# ---------------------------------------------------------------------------
# Limpieza de watermarks (function-scoped: se solicita por cada test que lo necesite)
# ---------------------------------------------------------------------------

@pytest.fixture
def limpiar_watermarks(engine_destino):
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))
    yield
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))


# ---------------------------------------------------------------------------
# Limpieza de tablas destino (function-scoped)
# ---------------------------------------------------------------------------

@pytest.fixture
def truncar_destino(engine_destino):
    """Factory: truncar_destino(["d_facturas", "d_ordenes_compra"])"""
    tablas_usadas = []

    def _truncar(tablas: list):
        tablas_usadas.extend(tablas)
        truncar_tablas_destino(engine_destino, tablas)

    yield _truncar

    if tablas_usadas:
        truncar_tablas_destino(engine_destino, list(set(tablas_usadas)))


@pytest.fixture
def truncar_todo_destino(engine_destino):
    """Trunca todas las tablas d_* y limpia watermarks antes/después del test."""
    truncar_tablas_destino(engine_destino, _ALL_DEST_TABLES)
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))
    yield
    truncar_tablas_destino(engine_destino, _ALL_DEST_TABLES)
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))
