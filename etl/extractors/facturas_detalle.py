import pandas as pd
from sqlalchemy import text

# Fuentes: facturas_detalle + facturas + productos + categorias
# Destino: d_facturas_detalle
# Clave upsert: id_detalle_orig

QUERY = """
SELECT
    fd.id               AS id_detalle_orig,
    fd.id_factura,
    f.numero_factura,
    f.fecha_emision,
    f.id_sucursal,
    f.estado            AS estado_factura,
    fd.id_producto,
    p.codigo            AS codigo_producto,
    p.nombre            AS nombre_producto,
    p.id_categoria,
    c.nombre            AS categoria,
    fd.cantidad,
    fd.subtotal,
    fd.costo_unitario,
    fd.created_at,
    fd.updated_at,
    fd.deleted_at
FROM facturas_detalle fd
JOIN facturas f
    ON f.id = fd.id_factura
    AND f.deleted_at IS NULL
JOIN productos p
    ON p.id = fd.id_producto
    AND p.deleted_at IS NULL
LEFT JOIN categorias c
    ON c.id = p.id_categoria
    AND c.deleted_at IS NULL
WHERE fd.updated_at > :watermark
ORDER BY fd.id
"""


def extract(engine, watermark, chunksize: int):
    params = {"watermark": watermark or "1970-01-01 00:00:00"}
    conn   = engine.connect()
    return pd.read_sql(text(QUERY), con=conn, params=params, chunksize=chunksize)
