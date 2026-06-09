import pandas as pd
from sqlalchemy import text

# Fuentes: ordenes_compra + terceros (proveedores)
# Destino: d_ordenes_compra
# Clave upsert: id_orden_orig

QUERY = """
SELECT
    oc.id               AS id_orden_orig,
    oc.id_proveedor,
    t.razon_social      AS proveedor,
    oc.fecha_emision,
    oc.estado,
    oc.total,
    oc.created_at,
    oc.updated_at,
    oc.deleted_at
FROM ordenes_compra oc
JOIN terceros t
    ON t.id = oc.id_proveedor
    AND t.deleted_at IS NULL
WHERE oc.updated_at > :watermark
ORDER BY oc.id
"""


def extract(engine, watermark, chunksize: int):
    params = {"watermark": watermark or "1970-01-01 00:00:00"}
    conn   = engine.connect()
    return pd.read_sql(text(QUERY), con=conn, params=params, chunksize=chunksize)
