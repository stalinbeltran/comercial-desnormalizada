import pandas as pd
from sqlalchemy import text

# Fuentes: movimientos_inventario + productos + bodegas
# Destino: d_movimientos_inventario
# Clave upsert: id_movimiento_orig

QUERY = """
SELECT
    mi.id               AS id_movimiento_orig,
    mi.id_producto,
    p.codigo            AS codigo_producto,
    p.nombre            AS nombre_producto,
    mi.id_bodega,
    b.nombre            AS bodega,
    mi.fecha,
    mi.tipo_movimiento,
    mi.cantidad,
    mi.cantidad_anterior,
    mi.cantidad_posterior,
    mi.costo_unitario,
    mi.tipo_referencia,
    mi.id_referencia,
    mi.observacion,
    mi.created_at,
    mi.updated_at,
    mi.deleted_at
FROM movimientos_inventario mi
JOIN productos p
    ON p.id = mi.id_producto
    AND p.deleted_at IS NULL
JOIN bodegas b
    ON b.id = mi.id_bodega
    AND b.deleted_at IS NULL
WHERE mi.updated_at > :watermark
ORDER BY mi.id
"""


def extract(engine, watermark, chunksize: int):
    params = {"watermark": watermark or "1970-01-01 00:00:00"}
    conn   = engine.connect()
    return pd.read_sql(text(QUERY), con=conn, params=params, chunksize=chunksize)
