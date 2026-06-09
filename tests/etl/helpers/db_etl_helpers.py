"""Helpers de BD para el test suite del ETL."""
from sqlalchemy import text

# IDs reservados para seed de tests ETL (no colisionan con los 901 del conftest principal)
SEED_ID = 9000


# ---------------------------------------------------------------------------
# Maestros — árbol completo de dependencias FK
# ---------------------------------------------------------------------------

_INSERT_MAESTROS = [
    ("empresas",
     "INSERT IGNORE INTO empresas (id, razon_social, ruc_rif, moneda) "
     "VALUES (9000, 'Test ETL SA', '9999999999001', 'USD')"),
    ("tipos_identificacion",
     "INSERT IGNORE INTO tipos_identificacion (id, nombre, codigo) "
     "VALUES (9000, 'Tipo ETL Test', 'ETL-TEST-9000')"),
    ("unidades_medida",
     "INSERT IGNORE INTO unidades_medida (id, nombre, abreviatura) "
     "VALUES (9000, 'Unidad ETL', 'ETL')"),
    ("marcas",
     "INSERT IGNORE INTO marcas (id, nombre) VALUES (9000, 'Marca ETL')"),
    ("categorias",
     "INSERT IGNORE INTO categorias (id, nombre) VALUES (9000, 'Cat ETL')"),
    ("sucursales",
     "INSERT IGNORE INTO sucursales (id, id_empresa, nombre, codigo, estado) "
     "VALUES (9000, 9000, 'Sucursal ETL', 'SETL', 1)"),
    ("bodegas",
     "INSERT IGNORE INTO bodegas (id, id_sucursal, nombre, codigo, estado) "
     "VALUES (9000, 9000, 'Bodega ETL', 'BETL', 1)"),
    ("terceros",
     "INSERT IGNORE INTO terceros (id, id_tipo_identificacion, numero_identificacion, "
     "razon_social, estado) VALUES (9000, 9000, '9999999999', 'Proveedor ETL SA', 1)"),
    ("productos",
     "INSERT IGNORE INTO productos (id, id_categoria, id_marca, id_unidad_medida, "
     "codigo, nombre, aplica_impuesto, porcentaje_impuesto, estado) "
     "VALUES (9000, 9000, 9000, 9000, 'ETL-TEST', 'Producto ETL', 1, 12.00, 1)"),
    ("productos_presentaciones",
     "INSERT IGNORE INTO productos_presentaciones (id, id_producto, nombre, "
     "factor_conversion, estado) VALUES (9000, 9000, 'Unidad', 1.0000, 1)"),
]

_DELETE_MAESTROS = [
    "DELETE FROM productos_presentaciones WHERE id = 9000",
    "DELETE FROM productos WHERE id = 9000",
    "DELETE FROM terceros WHERE id = 9000",
    "DELETE FROM bodegas WHERE id = 9000",
    "DELETE FROM sucursales WHERE id = 9000",
    "DELETE FROM categorias WHERE id = 9000",
    "DELETE FROM marcas WHERE id = 9000",
    "DELETE FROM unidades_medida WHERE id = 9000",
    "DELETE FROM tipos_identificacion WHERE id = 9000",
    "DELETE FROM empresas WHERE id = 9000",
]


def insert_maestros(engine_origen) -> None:
    with engine_origen.begin() as conn:
        for _, sql in _INSERT_MAESTROS:
            conn.execute(text(sql))


def delete_maestros(engine_origen) -> None:
    with engine_origen.begin() as conn:
        for sql in _DELETE_MAESTROS:
            conn.execute(text(sql))


# ---------------------------------------------------------------------------
# Utilidades de consulta
# ---------------------------------------------------------------------------

def contar_filas(engine, tabla: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()


def leer_campo(engine, tabla: str, where_col: str, where_val, campo: str):
    sql = f"SELECT {campo} FROM {tabla} WHERE {where_col} = :v LIMIT 1"
    with engine.connect() as conn:
        return conn.execute(text(sql), {"v": where_val}).scalar()


def truncar_tablas_destino(engine_destino, tablas: list) -> None:
    with engine_destino.begin() as conn:
        for t in tablas:
            conn.execute(text(f"TRUNCATE TABLE {t}"))


# ---------------------------------------------------------------------------
# Builders de registros transaccionales para seed
# ---------------------------------------------------------------------------

def insert_inventario(engine_origen, id_producto=9000, id_presentacion=9000,
                      id_bodega=9000, cantidad=10, updated_at="NOW()") -> None:
    sql = text(f"""
        INSERT IGNORE INTO inventario
            (id_producto, id_presentacion, id_bodega, cantidad,
             cantidad_minima, cantidad_maxima, updated_at)
        VALUES (:prod, :pres, :bod, :cant, 2, 50, {updated_at})
    """)
    with engine_origen.begin() as conn:
        conn.execute(sql, {"prod": id_producto, "pres": id_presentacion,
                           "bod": id_bodega, "cant": cantidad})


def delete_inventario(engine_origen, id_producto=9000) -> None:
    with engine_origen.begin() as conn:
        conn.execute(text("DELETE FROM inventario WHERE id_producto = :p"),
                     {"p": id_producto})


def insert_factura(engine_origen, factura_id: int, numero: str = None,
                   updated_at: str = "NOW()") -> None:
    if numero is None:
        numero = f"F-ETL-{factura_id}"
    sql = text(f"""
        INSERT IGNORE INTO facturas
            (id, id_sucursal, id_cliente, numero, fecha_emision,
             estado, subtotal, descuento, impuesto, total, saldo, updated_at)
        VALUES (:id, 9000, 9000, :num, '2025-01-15',
                'pendiente', 100, 0, 12, 112, 112, {updated_at})
    """)
    with engine_origen.begin() as conn:
        conn.execute(sql, {"id": factura_id, "num": numero})


def delete_facturas(engine_origen, ids: list) -> None:
    if not ids:
        return
    placeholders = ", ".join(str(i) for i in ids)
    with engine_origen.begin() as conn:
        conn.execute(text(f"DELETE FROM facturas WHERE id IN ({placeholders})"))
        conn.execute(text(f"DELETE FROM facturas_detalle WHERE id_factura IN ({placeholders})"))


def insert_orden_compra(engine_origen, orden_id: int, numero: str = None,
                        total: float = 500.0, updated_at: str = "NOW()") -> None:
    if numero is None:
        numero = f"OC-ETL-{orden_id}"
    sql = text(f"""
        INSERT IGNORE INTO ordenes_compra
            (id, id_sucursal, id_proveedor, id_bodega_destino, numero,
             fecha_emision, estado, subtotal, descuento, impuesto, total, updated_at)
        VALUES (:id, 9000, 9000, 9000, :num,
                '2025-01-10', 'pendiente', :total, 0, 0, :total, {updated_at})
    """)
    with engine_origen.begin() as conn:
        conn.execute(sql, {"id": orden_id, "num": numero, "total": total})


def delete_ordenes_compra(engine_origen, ids: list) -> None:
    if not ids:
        return
    placeholders = ", ".join(str(i) for i in ids)
    with engine_origen.begin() as conn:
        conn.execute(text(f"DELETE FROM ordenes_compra WHERE id IN ({placeholders})"))
