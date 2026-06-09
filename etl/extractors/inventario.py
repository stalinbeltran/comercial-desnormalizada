import pandas as pd
from sqlalchemy import text

# Fuentes: inventario + productos + productos_presentaciones + bodegas
# Destino: d_inventario
# Clave upsert: (id_producto, id_presentacion, id_bodega)

QUERY = """
SELECT
    i.id_producto,
    p.codigo                AS codigo_producto,
    p.nombre                AS nombre_producto,
    i.id_presentacion,
    pp.nombre               AS presentacion,
    i.id_bodega,
    b.nombre                AS bodega,
    i.stock_actual,
    i.stock_minimo,
    i.stock_maximo,
    i.created_at,
    i.updated_at,
    i.deleted_at
FROM inventario i
JOIN productos p
    ON p.id = i.id_producto
    AND p.deleted_at IS NULL
JOIN productos_presentaciones pp
    ON pp.id = i.id_presentacion
    AND pp.deleted_at IS NULL
JOIN bodegas b
    ON b.id = i.id_bodega
    AND b.deleted_at IS NULL
WHERE i.updated_at > :watermark
ORDER BY i.id
"""


def extract(engine, watermark, chunksize: int):
    params = {"watermark": watermark or "1970-01-01 00:00:00"}
    conn   = engine.connect()
    return pd.read_sql(text(QUERY), con=conn, params=params, chunksize=chunksize)
