import pandas as pd
from sqlalchemy import text

# Fuentes: facturas + sucursales + terceros (clientes)
# Destino: d_facturas
# Clave upsert: id_factura_orig

QUERY = """
SELECT
    f.id                AS id_factura_orig,
    f.numero_factura,
    f.fecha_emision,
    f.fecha_vencimiento,
    f.id_sucursal,
    s.nombre            AS sucursal,
    f.id_cliente,
    t.nombre            AS cliente,
    f.subtotal,
    f.descuento,
    f.impuesto,
    f.total,
    f.saldo,
    f.estado,
    f.created_at,
    f.updated_at,
    f.deleted_at
FROM facturas f
JOIN sucursales s
    ON s.id = f.id_sucursal
    AND s.deleted_at IS NULL
JOIN terceros t
    ON t.id = f.id_cliente
    AND t.deleted_at IS NULL
WHERE f.updated_at > :watermark
ORDER BY f.id
"""


def extract(engine, watermark, chunksize: int):
    params = {"watermark": watermark or "1970-01-01 00:00:00"}
    conn   = engine.connect()
    return pd.read_sql(text(QUERY), con=conn, params=params, chunksize=chunksize)
