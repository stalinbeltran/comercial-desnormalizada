---
name: etl-desnormalizacion
description: >
  Skill para implementar, extender y mantener el proceso ETL que sincroniza datos desde
  la base de datos normalizada (comercial_db) hacia la desnormalizada (comercial_desn_db)
  usando pandas y SQLAlchemy. Activar ante cualquier mención de: ETL, extracción, carga,
  sincronización, watermark, incremental, pipeline, d_inventario, d_facturas,
  d_movimientos_inventario, d_facturas_detalle, d_ordenes_compra, etl/config, etl/pipeline,
  o cuando se pida agregar una nueva tabla desnormalizada al proceso.
---

# ETL Desnormalización — Skill de Referencia

Proceso ETL que extrae datos de `comercial_db` (normalizada) y los carga en
`comercial_desn_db` (desnormalizada) usando pandas + SQLAlchemy con soporte para
grandes volúmenes de datos mediante extracción incremental y procesamiento por chunks.

---

## Ubicación del código

```
etl/
├── config.py                  # Engines SQLAlchemy, variables de entorno
├── watermark.py               # Control de marca de tiempo por tabla
├── pipeline.py                # Orquestador: extrae → transforma → carga
├── run_etl.py                 # Punto de entrada CLI
├── extractors/
│   ├── __init__.py
│   ├── inventario.py          # Extrae inventario + productos + presentaciones + bodegas
│   ├── movimientos.py         # Extrae movimientos_inventario + productos + bodegas
│   ├── facturas.py            # Extrae facturas + sucursales + terceros
│   ├── facturas_detalle.py    # Extrae facturas_detalle + facturas + productos + categorias
│   └── ordenes_compra.py      # Extrae ordenes_compra + terceros
├── transformers/
│   ├── __init__.py
│   └── common.py              # Limpieza de tipos, decimales, fechas
└── loaders/
    ├── __init__.py
    └── upsert.py              # INSERT … ON DUPLICATE KEY UPDATE por chunks
```

---

## Variables de entorno (.env)

```
# Fuente (normalizada)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=...
DB_NAME=comercial_db

# Destino (desnormalizada)
DB_DESN_HOST=localhost
DB_DESN_PORT=3306
DB_DESN_USER=root
DB_DESN_PASSWORD=...
DB_DESN_NAME=comercial_desn_db
```

---

## Stack tecnológico

| Componente | Librería |
|---|---|
| Conexión y pooling | SQLAlchemy 2.x |
| Procesamiento tabular | pandas |
| Variables de entorno | python-dotenv |
| Logging | logging (stdlib) |

---

## Mapeo de tablas: fuente → destino

| Tabla destino | Tablas fuente (JOIN en SQL) | Columna de trazabilidad |
|---|---|---|
| `d_inventario` | `inventario` + `productos` + `productos_presentaciones` + `bodegas` | `id_producto`, `id_presentacion`, `id_bodega` (claves compuestas) |
| `d_movimientos_inventario` | `movimientos_inventario` + `productos` + `bodegas` | `id_movimiento_orig` |
| `d_facturas` | `facturas` + `sucursales` + `terceros` | `id_factura_orig` |
| `d_facturas_detalle` | `facturas_detalle` + `facturas` + `productos` + `categorias` | `id_detalle_orig` |
| `d_ordenes_compra` | `ordenes_compra` + `terceros` | `id_orden_orig` |

Cada tabla destino tiene columnas `*_orig` para mantener trazabilidad al registro fuente.

---

## Requerimientos de diseño

### Extracción incremental
- Usar `updated_at` de la tabla principal fuente como cursor.
- La tabla `etl_watermarks` (en `comercial_desn_db`) guarda la última marca procesada:
  ```sql
  CREATE TABLE IF NOT EXISTS etl_watermarks (
      tabla       VARCHAR(100) PRIMARY KEY,
      last_run    DATETIME     NOT NULL,
      updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
  );
  ```
- En la primera ejecución (sin watermark) se carga todo (bootstrap).
- Soportar flag `--full-refresh` para truncar y recargar desde cero.

### Procesamiento por chunks
```python
CHUNK_SIZE = 5_000  # filas por iteración

for chunk in pd.read_sql(query, con=engine_origen, params=params, chunksize=CHUNK_SIZE):
    df = transform(chunk)
    upsert(df, tabla_destino, engine_destino)
```
- Nunca llamar `pd.read_sql()` sin `chunksize` sobre tablas grandes.
- `chunksize` configurable via variable de entorno `ETL_CHUNK_SIZE` (default 5000).

### JOINs siempre en SQL, nunca en pandas
- Las queries de extracción entregan el resultado ya consolidado (con todos los campos necesarios).
- pandas no hace `merge()` entre DataFrames; solo limpia tipos y renombra columnas si hace falta.

### Upsert en el destino
- Usar `INSERT ... ON DUPLICATE KEY UPDATE` para manejar registros nuevos y modificados.
- Las tablas destino deben tener `UNIQUE KEY` sobre la(s) columna(s) `*_orig`.
- Implementar con `method` personalizado en `to_sql` o con `INSERT` directo via SQLAlchemy Core.

### Gestión de conexiones
```python
engine = create_engine(
    url,
    pool_recycle=3600,
    pool_pre_ping=True,
    pool_size=5,
    max_overflow=10,
)
```
- Un engine para origen, uno para destino.
- Usar `with engine.connect() as conn:` para liberar conexiones después de cada chunk.

### Tipos de datos críticos
- `DECIMAL(15,2)` y `DECIMAL(15,4)` → convertir con `pd.to_numeric(df[col], errors='coerce')`.
- `DATETIME` / `DATE` → convertir con `pd.to_datetime(df[col], errors='coerce')`.
- Nulos inesperados en columnas NOT NULL → loggear y descartar la fila (no abortar el chunk).

### Logging y observabilidad
- Loggear por cada tabla: filas_leidas, filas_insertadas, filas_actualizadas, tiempo_seg, errores.
- Si un chunk falla: loggear el error, guardar las filas en `etl/dead_letters/<tabla>_<timestamp>.csv`, continuar con el siguiente chunk.
- Formato de log: `%(asctime)s [%(levelname)s] %(name)s — %(message)s`.

### Idempotencia
- Re-ejecutable sin duplicar datos (upsert + watermark).
- `--full-refresh`: trunca tabla destino y borra watermark antes de cargar.

---

## Patrones de código de referencia

### config.py
```python
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os

load_dotenv()

def make_engine(prefix: str):
    host     = os.environ[f"{prefix}HOST"]
    port     = os.environ[f"{prefix}PORT"]
    user     = os.environ[f"{prefix}USER"]
    password = os.environ[f"{prefix}PASSWORD"]
    db       = os.environ[f"{prefix}NAME"]
    url = f"mysql+mysqlconnector://{user}:{password}@{host}:{port}/{db}?charset=utf8mb4"
    return create_engine(url, pool_recycle=3600, pool_pre_ping=True)

engine_origen  = make_engine("DB_")
engine_destino = make_engine("DB_DESN_")
CHUNK_SIZE     = int(os.getenv("ETL_CHUNK_SIZE", 5000))
```

### watermark.py
```python
from datetime import datetime
from sqlalchemy import text

CREATE_SQL = """
CREATE TABLE IF NOT EXISTS etl_watermarks (
    tabla      VARCHAR(100) PRIMARY KEY,
    last_run   DATETIME     NOT NULL,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
)
"""

def get_watermark(engine, tabla: str):
    with engine.connect() as conn:
        conn.execute(text(CREATE_SQL))
        row = conn.execute(text("SELECT last_run FROM etl_watermarks WHERE tabla=:t"), {"t": tabla}).fetchone()
    return row[0] if row else None

def set_watermark(engine, tabla: str, ts: datetime):
    sql = """
        INSERT INTO etl_watermarks (tabla, last_run) VALUES (:t, :ts)
        ON DUPLICATE KEY UPDATE last_run=:ts
    """
    with engine.begin() as conn:
        conn.execute(text(sql), {"t": tabla, "ts": ts})
```

### Extractor (patrón base)
```python
import pandas as pd
from sqlalchemy import text

QUERY = """
    SELECT
        i.id           AS id_producto,
        p.codigo       AS codigo_producto,
        ...
    FROM inventario i
    JOIN productos p ON p.id = i.id_producto AND p.deleted_at IS NULL
    ...
    WHERE i.deleted_at IS NULL
      AND i.updated_at > :watermark
    ORDER BY i.id
"""

def extract(engine, watermark, chunksize: int):
    params = {"watermark": watermark or "1970-01-01"}
    return pd.read_sql(text(QUERY), con=engine.connect(), params=params, chunksize=chunksize)
```

### Transformer (patrón base)
```python
import pandas as pd

DECIMAL_COLS = ["stock_actual", "stock_minimo", "stock_maximo", "costo_unitario"]
DATE_COLS    = ["created_at", "updated_at"]

def transform(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in DECIMAL_COLS:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    for col in DATE_COLS:
        if col in df.columns:
            df[col] = pd.to_datetime(df[col], errors="coerce")
    return df.dropna(subset=["id_producto"])  # columna NOT NULL de ejemplo
```

### Loader upsert (patrón base)
```python
from sqlalchemy import text

def upsert(df, tabla: str, engine, unique_cols: list[str]):
    if df.empty:
        return 0
    cols        = list(df.columns)
    placeholders = ", ".join([f":{c}" for c in cols])
    updates      = ", ".join([f"{c}=VALUES({c})" for c in cols if c not in unique_cols])
    sql = f"""
        INSERT INTO {tabla} ({', '.join(cols)})
        VALUES ({placeholders})
        ON DUPLICATE KEY UPDATE {updates}
    """
    rows = df.to_dict(orient="records")
    with engine.begin() as conn:
        result = conn.execute(text(sql), rows)
    return result.rowcount
```

---

## Convenciones de generación de código ETL

- Los extractors **solo** retornan un generador de chunks (no cargan ni transforman).
- Los transformers **no** acceden a BD; reciben un DataFrame y devuelven uno.
- Los loaders **no** conocen la lógica de negocio; solo insertan/actualizan filas.
- El pipeline en `pipeline.py` orquesta los tres pasos y gestiona el watermark.
- Loggear con `logging.getLogger(__name__)` en cada módulo; no usar `print()`.
- Capturar excepciones por chunk, nunca dejar que un chunk roto aborte el pipeline completo.
- Las queries SQL van en constantes de módulo o archivos `.sql`, nunca inline dentro de funciones largas.

---

## Ejecución CLI

```bash
# Carga incremental (todas las tablas)
python etl/run_etl.py

# Recarga completa de una tabla
python etl/run_etl.py --full-refresh --table d_facturas

# Recarga completa de todo
python etl/run_etl.py --full-refresh
```

---

## Checklist al agregar una nueva tabla desnormalizada

1. Agregar la query JOIN en `etl/extractors/<nombre>.py`
2. Agregar columnas de limpieza en `etl/transformers/common.py` (o crear transformer propio)
3. Registrar la tabla en `pipeline.py` (lista `TABLES`)
4. Asegurar que la tabla destino tenga `UNIQUE KEY` sobre la columna `*_orig`
5. Verificar que `etl_watermarks` tendrá entrada para la nueva tabla
