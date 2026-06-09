"""
Tests para etl/extractors/*.py.
Verifican que las queries SQL retornen las columnas correctas y que el
filtro de watermark funcione. Requieren datos de seed en comercial_db.
"""
import pytest
from sqlalchemy import text

from etl.extractors import (facturas, facturas_detalle, inventario,
                             movimientos, ordenes_compra)
from tests.etl.helpers.db_etl_helpers import (
    delete_facturas, delete_inventario, delete_ordenes_compra,
    insert_factura, insert_inventario, insert_orden_compra,
)

# Columnas esperadas por tabla destino (excluye el AUTO_INCREMENT id)
_COLS_INVENTARIO = {
    "id_producto", "codigo_producto", "nombre_producto",
    "id_presentacion", "presentacion", "id_bodega", "bodega",
    "stock_actual", "stock_minimo", "stock_maximo",
    "created_at", "updated_at", "deleted_at",
}
_COLS_MOVIMIENTOS = {
    "id_movimiento_orig", "id_producto", "codigo_producto", "nombre_producto",
    "id_bodega", "bodega", "fecha", "tipo_movimiento",
    "cantidad", "cantidad_anterior", "cantidad_posterior", "costo_unitario",
    "tipo_referencia", "id_referencia", "observacion",
    "created_at", "updated_at", "deleted_at",
}
_COLS_FACTURAS = {
    "id_factura_orig", "numero_factura", "fecha_emision", "fecha_vencimiento",
    "id_sucursal", "sucursal", "id_cliente", "cliente",
    "subtotal", "descuento", "impuesto", "total", "saldo", "estado",
    "created_at", "updated_at", "deleted_at",
}
_COLS_FACTURAS_DETALLE = {
    "id_detalle_orig", "id_factura", "numero_factura", "fecha_emision",
    "id_sucursal", "estado_factura", "id_producto", "codigo_producto",
    "nombre_producto", "id_categoria", "categoria",
    "cantidad", "subtotal", "costo_unitario",
    "created_at", "updated_at", "deleted_at",
}
_COLS_ORDENES = {
    "id_orden_orig", "id_proveedor", "proveedor",
    "fecha_emision", "estado", "total",
    "created_at", "updated_at", "deleted_at",
}

_WM_PASADO  = "2000-01-01 00:00:00"
_WM_FUTURO  = "2099-12-31 23:59:59"


def _primer_chunk(extractor_fn, engine_origen, watermark=_WM_PASADO, chunksize=100):
    """Retorna el primer chunk — útil para verificar columnas."""
    chunks = list(extractor_fn(engine_origen, watermark, chunksize))
    return chunks[0] if chunks else None


def _todos_chunks(extractor_fn, engine_origen, watermark=_WM_PASADO, chunksize=100):
    """Concatena todos los chunks — necesario cuando el seed puede estar en cualquier chunk."""
    import pandas as pd
    frames = list(extractor_fn(engine_origen, watermark, chunksize))
    return pd.concat(frames, ignore_index=True) if frames else None


# ═══════════════════════════════════════════════════════════════════════════
# inventario
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seed_inv(engine_origen, seed_maestros):
    insert_inventario(engine_origen)
    yield
    delete_inventario(engine_origen)


def test_inventario_columnas_correctas(engine_origen, seed_inv):
    chunk = _primer_chunk(inventario.extract, engine_origen)
    assert chunk is not None
    assert set(chunk.columns) == _COLS_INVENTARIO


def test_inventario_alias_stock(engine_origen, seed_inv):
    chunk = _primer_chunk(inventario.extract, engine_origen)
    assert "stock_actual" in chunk.columns
    assert "stock_minimo" in chunk.columns
    assert "stock_maximo" in chunk.columns


def test_inventario_watermark_filtra(engine_origen, seed_inv):
    chunk = _primer_chunk(inventario.extract, engine_origen, watermark=_WM_FUTURO)
    assert chunk is None or len(chunk) == 0


def test_inventario_join_no_duplica(engine_origen, seed_inv):
    chunk = _primer_chunk(inventario.extract, engine_origen)
    filas_prod = chunk[chunk["id_producto"] == 9000]
    assert len(filas_prod) == 1


# ═══════════════════════════════════════════════════════════════════════════
# movimientos_inventario
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seed_mov(engine_origen, seed_maestros):
    with engine_origen.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO movimientos_inventario
                (id, id_producto, id_presentacion, id_bodega, tipo_movimiento,
                 cantidad, cantidad_anterior, cantidad_posterior, costo_unitario)
            VALUES (9000, 9000, 9000, 9000, 'entrada', 10, 0, 10, 5.50)
        """))
    yield
    with engine_origen.begin() as conn:
        conn.execute(text("DELETE FROM movimientos_inventario WHERE id = 9000"))


def test_movimientos_columnas_correctas(engine_origen, seed_mov):
    chunk = _primer_chunk(movimientos.extract, engine_origen)
    assert chunk is not None
    assert set(chunk.columns) == _COLS_MOVIMIENTOS


def test_movimientos_created_at_como_fecha(engine_origen, seed_mov):
    chunk = _primer_chunk(movimientos.extract, engine_origen)
    assert "fecha" in chunk.columns
    assert chunk[chunk["id_movimiento_orig"] == 9000]["fecha"].notna().all()


def test_movimientos_watermark_filtra(engine_origen, seed_mov):
    chunk = _primer_chunk(movimientos.extract, engine_origen, watermark=_WM_FUTURO)
    assert chunk is None or len(chunk) == 0


# ═══════════════════════════════════════════════════════════════════════════
# facturas
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seed_fac(engine_origen, seed_maestros):
    insert_factura(engine_origen, factura_id=9001)
    yield
    delete_facturas(engine_origen, [9001])


def test_facturas_columnas_correctas(engine_origen, seed_fac):
    chunk = _primer_chunk(facturas.extract, engine_origen)
    assert chunk is not None
    assert set(chunk.columns) == _COLS_FACTURAS


def test_facturas_alias_numero_factura(engine_origen, seed_fac):
    df = _todos_chunks(facturas.extract, engine_origen)
    fila = df[df["id_factura_orig"] == 9001]
    assert len(fila) == 1
    assert fila["numero_factura"].iloc[0] == "F-ETL-9001"


def test_facturas_razon_social_como_cliente(engine_origen, seed_fac):
    df = _todos_chunks(facturas.extract, engine_origen)
    fila = df[df["id_factura_orig"] == 9001]
    assert len(fila) == 1
    assert fila["cliente"].iloc[0] == "Proveedor ETL SA"


def test_facturas_watermark_filtra(engine_origen, seed_fac):
    chunk = _primer_chunk(facturas.extract, engine_origen, watermark=_WM_FUTURO)
    assert chunk is None or len(chunk[chunk["id_factura_orig"] == 9001]) == 0


# ═══════════════════════════════════════════════════════════════════════════
# facturas_detalle
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seed_det(engine_origen, seed_maestros):
    insert_factura(engine_origen, factura_id=9002, numero="F-ETL-002")
    with engine_origen.begin() as conn:
        conn.execute(text("""
            INSERT IGNORE INTO facturas_detalle
                (id, id_factura, id_producto, id_presentacion, id_bodega,
                 cantidad, precio_unitario, descuento, subtotal, costo_unitario)
            VALUES (9001, 9002, 9000, 9000, 9000, 2, 50, 0, 100, 40)
        """))
    yield
    with engine_origen.begin() as conn:
        conn.execute(text("DELETE FROM facturas_detalle WHERE id = 9001"))
    delete_facturas(engine_origen, [9002])


def test_facturas_detalle_columnas_correctas(engine_origen, seed_det):
    chunk = _primer_chunk(facturas_detalle.extract, engine_origen)
    assert chunk is not None
    assert set(chunk.columns) == _COLS_FACTURAS_DETALLE


def test_facturas_detalle_alias_numero_factura(engine_origen, seed_det):
    df = _todos_chunks(facturas_detalle.extract, engine_origen)
    fila = df[df["id_detalle_orig"] == 9001]
    assert len(fila) == 1
    assert fila["numero_factura"].iloc[0] == "F-ETL-002"


def test_facturas_detalle_sin_categoria_no_descartada(engine_origen, seed_maestros):
    """LEFT JOIN a categorias — producto sin categoría debe seguir apareciendo."""
    with engine_origen.begin() as conn:
        # producto temporal sin categoría (id_categoria = NULL)
        conn.execute(text("""
            INSERT IGNORE INTO productos (id, id_categoria, id_marca, id_unidad_medida,
                codigo, nombre, aplica_impuesto, porcentaje_impuesto, estado)
            VALUES (9001, NULL, 9000, 9000, 'ETL-NOCAT', 'Sin Cat ETL', 1, 0, 1)
        """))
        conn.execute(text("""
            INSERT IGNORE INTO productos_presentaciones (id, id_producto, nombre,
                factor_conversion, estado)
            VALUES (9001, 9001, 'Unidad', 1, 1)
        """))
        conn.execute(text("""
            INSERT IGNORE INTO facturas (id, id_sucursal, id_cliente, numero,
                fecha_emision, estado, subtotal, descuento, impuesto, total, saldo)
            VALUES (9003, 9000, 9000, 'F-ETL-003', '2025-02-01',
                    'pendiente', 50, 0, 6, 56, 56)
        """))
        conn.execute(text("""
            INSERT IGNORE INTO facturas_detalle (id, id_factura, id_producto,
                id_presentacion, id_bodega, cantidad, precio_unitario,
                descuento, subtotal, costo_unitario)
            VALUES (9002, 9003, 9001, 9001, 9000, 1, 50, 0, 50, 40)
        """))
    try:
        df = _todos_chunks(facturas_detalle.extract, engine_origen)
        fila = df[df["id_detalle_orig"] == 9002]
        assert len(fila) == 1
        assert fila["categoria"].iloc[0] is None or fila["categoria"].isna().iloc[0]
    finally:
        with engine_origen.begin() as conn:
            conn.execute(text("DELETE FROM facturas_detalle WHERE id IN (9002)"))
            conn.execute(text("DELETE FROM facturas WHERE id = 9003"))
            conn.execute(text("DELETE FROM productos_presentaciones WHERE id = 9001"))
            conn.execute(text("DELETE FROM productos WHERE id = 9001"))


# ═══════════════════════════════════════════════════════════════════════════
# ordenes_compra
# ═══════════════════════════════════════════════════════════════════════════

@pytest.fixture
def seed_oc(engine_origen, seed_maestros):
    insert_orden_compra(engine_origen, orden_id=9001)
    yield
    delete_ordenes_compra(engine_origen, [9001])


def test_ordenes_columnas_correctas(engine_origen, seed_oc):
    chunk = _primer_chunk(ordenes_compra.extract, engine_origen)
    assert chunk is not None
    assert set(chunk.columns) == _COLS_ORDENES


def test_ordenes_razon_social_como_proveedor(engine_origen, seed_oc):
    df = _todos_chunks(ordenes_compra.extract, engine_origen)
    fila = df[df["id_orden_orig"] == 9001]
    assert len(fila) == 1
    assert fila["proveedor"].iloc[0] == "Proveedor ETL SA"


def test_ordenes_watermark_filtra(engine_origen, seed_oc):
    chunk = _primer_chunk(ordenes_compra.extract, engine_origen, watermark=_WM_FUTURO)
    assert chunk is None or len(chunk[chunk["id_orden_orig"] == 9001]) == 0
