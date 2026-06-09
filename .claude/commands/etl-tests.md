---
name: etl-tests
description: >
  Skill para crear, extender y mantener el test suite profesional del ETL
  comercial_db → comercial_desn_db. Activar cuando el usuario pida escribir
  tests, fixtures, conftest o casos de prueba para cualquier módulo de
  etl/ (watermark, transformer, upsert, extractors, pipeline, run_etl).
  También activar ante: "testear el ETL", "pruebas del pipeline",
  "test de integración ETL", "casos borde del ETL".
---

# ETL Tests — Skill de Referencia

Suite de tests profesional para el ETL que sincroniza `comercial_db` →
`comercial_desn_db`. Cubre unitarios (sin BD), integración por capa y
end-to-end con datos reales en ambas bases de datos.

---

## Stack

| Componente | Librería |
|---|---|
| Framework | pytest |
| Datos ficticios | faker |
| Tabular | pandas |
| BD origen | `comercial_db` (variables `DB_*` en `.env`) |
| BD destino | `comercial_desn_db` (variables `DB_DESN_*` en `.env`) |
| Conexión | SQLAlchemy (engines de `etl/config.py`) |

---

## Estructura de carpetas

```
tests/etl/
├── conftest.py                  # engines, fixtures de seed/teardown
├── helpers/
│   └── db_etl_helpers.py        # insertar y limpiar datos en ambas BDs
├── test_watermark.py            # etl/watermark.py — sin datos de negocio
├── test_transformer.py          # etl/transformers/common.py — puro pandas
├── test_upsert.py               # etl/loaders/upsert.py — solo BD destino
├── test_extractors.py           # etl/extractors/*.py — queries contra origen
├── test_pipeline.py             # etl/pipeline.py — integración por tabla
└── test_integration.py          # end-to-end con ambas BDs y datos reales
```

---

## Reglas generales

1. Usar una BD de test independiente, **nunca** la productiva.
   Configurar en `.env.test` o mediante variables de entorno prefijadas con `TEST_`.
2. Cada test es **independiente**: no depende del estado que dejó otro.
3. Usar **transacciones con rollback** para tests unitarios/capa (no acumulan basura).
4. Los tests de integración E2E usan **TRUNCATE + seed** en setUp y teardown.
5. IDs de seed **fijos y conocidos** para poder hacer assertions exactos.
6. Nunca embeber SQL largo en Python: usar constantes de módulo o archivos `.sql`.
7. Loggear con `caplog` de pytest en tests que verifican comportamiento de logging.

---

## conftest.py — estructura base

```python
import pytest
from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

@pytest.fixture(scope="session")
def engine_origen():
    url = (
        f"mysql+mysqlconnector://{os.environ['DB_USER']}:{os.environ['DB_PASSWORD']}"
        f"@{os.environ['DB_HOST']}:{os.environ['DB_PORT']}/{os.environ['DB_NAME']}"
        "?charset=utf8mb4"
    )
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture(scope="session")
def engine_destino():
    url = (
        f"mysql+mysqlconnector://{os.environ['DB_DESN_USER']}:{os.environ['DB_DESN_PASSWORD']}"
        f"@{os.environ['DB_DESN_HOST']}:{os.environ['DB_DESN_PORT']}/{os.environ['DB_DESN_NAME']}"
        "?charset=utf8mb4"
    )
    engine = create_engine(url, pool_pre_ping=True)
    yield engine
    engine.dispose()

@pytest.fixture(autouse=True)
def limpiar_watermarks(engine_destino):
    """Borra watermarks antes de cada test para evitar contaminación."""
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))
    yield
    with engine_destino.begin() as conn:
        conn.execute(text("DELETE FROM etl_watermarks"))
```

---

## Módulo 1: test_watermark.py

### Casos a cubrir

| # | Escenario | Assertion |
|---|---|---|
| 1 | `get_watermark` sin registro previo | Retorna `None` |
| 2 | `get_watermark` con registro existente | Retorna el `datetime` guardado |
| 3 | `set_watermark` primera vez | Crea fila; `get_watermark` devuelve el mismo `ts` |
| 4 | `set_watermark` segunda vez (upsert) | No duplica; valor actualizado |
| 5 | `clear_watermark` con registro existente | `get_watermark` vuelve a `None` |
| 6 | `clear_watermark` sin registro | No lanza excepción |
| 7 | `_ensure_table` en BD sin la tabla | La crea sin error |

### Patrón

```python
from datetime import datetime
from etl.watermark import clear_watermark, get_watermark, set_watermark

def test_get_watermark_sin_registro(engine_destino):
    assert get_watermark(engine_destino, "d_facturas") is None

def test_set_y_get_watermark(engine_destino):
    ts = datetime(2025, 1, 15, 10, 30, 0)
    set_watermark(engine_destino, "d_facturas", ts)
    assert get_watermark(engine_destino, "d_facturas") == ts

def test_set_watermark_upsert(engine_destino):
    ts1 = datetime(2025, 1, 1)
    ts2 = datetime(2025, 6, 1)
    set_watermark(engine_destino, "d_facturas", ts1)
    set_watermark(engine_destino, "d_facturas", ts2)
    assert get_watermark(engine_destino, "d_facturas") == ts2
```

---

## Módulo 2: test_transformer.py

**Sin BD** — solo pandas. Usar `pd.DataFrame(...)` directo.

### Casos a cubrir

| # | Escenario | Assertion |
|---|---|---|
| 1 | DECIMAL string `"1.5"` | `float` correcto |
| 2 | DECIMAL `None`/NaN | `0.0` (fillna) |
| 3 | DECIMAL no parseable `"abc"` | `0.0` (errors='coerce') |
| 4 | DATETIME string ISO | `datetime64` |
| 5 | DATE → `date` (no `datetime`) | `.dt.date` aplicado |
| 6 | NaN → `None` (MySQL compat) | `None` en lugar de `float('nan')` |
| 7 | Fila con nulo en `required` | Fila descartada |
| 8 | Fila con nulo en col opcional | Fila conservada |
| 9 | DataFrame de entrada no mutado | El original no cambia |
| 10 | `caplog` warning cuando se descartan filas | Log nivel WARNING con conteo |

### Patrón

```python
import pandas as pd
import numpy as np
from etl.transformers.common import clean

def test_decimal_string_convertido():
    df = pd.DataFrame({"stock_actual": ["1.5"], "id_producto": [1],
                       "id_presentacion": [1], "id_bodega": [1]})
    result = clean(df, required=["id_producto"])
    assert result["stock_actual"].iloc[0] == 1.5

def test_fila_con_required_nulo_descartada():
    df = pd.DataFrame({"id_producto": [1, None], "id_bodega": [1, 1],
                       "id_presentacion": [1, 1]})
    result = clean(df, required=["id_producto"])
    assert len(result) == 1

def test_input_no_mutado():
    df = pd.DataFrame({"stock_actual": ["abc"], "id_producto": [1],
                       "id_presentacion": [1], "id_bodega": [1]})
    original = df.copy()
    clean(df, required=["id_producto"])
    pd.testing.assert_frame_equal(df, original)
```

---

## Módulo 3: test_upsert.py

Requiere **solo BD destino** (`engine_destino`). Usar tabla auxiliar de test
`_test_upsert_tmp` o las tablas `d_*` reales con TRUNCATE en fixture.

### Casos a cubrir

| # | Escenario | Assertion |
|---|---|---|
| 1 | DataFrame vacío | Retorna `0`, no toca BD |
| 2 | INSERT de filas nuevas | Filas aparecen en BD |
| 3 | UPDATE de fila existente | Valor actualizado, no duplicado |
| 4 | Segunda ejecución idéntica | `rowcount` refleja no-cambio |
| 5 | `None` en col nullable | Se inserta como NULL (no `"None"`) |
| 6 | `upsert_chunk_safe` ante excepción | No relanza; crea CSV en `dead_letters/` |
| 7 | Nombre archivo dead letter | Contiene `tabla` y `chunk_index` |

### Patrón

```python
import pandas as pd
from sqlalchemy import text
from etl.loaders.upsert import upsert, upsert_chunk_safe

@pytest.fixture(autouse=True)
def truncar_d_ordenes(engine_destino):
    with engine_destino.begin() as conn:
        conn.execute(text("TRUNCATE TABLE d_ordenes_compra"))
    yield
    with engine_destino.begin() as conn:
        conn.execute(text("TRUNCATE TABLE d_ordenes_compra"))

def test_upsert_inserta_filas(engine_destino):
    df = pd.DataFrame([{
        "id_orden_orig": 1, "id_proveedor": 10, "proveedor": "Acme",
        "fecha_emision": "2025-01-01", "estado": "pendiente", "total": 100.00,
        "created_at": "2025-01-01 00:00:00", "updated_at": "2025-01-01 00:00:00",
        "deleted_at": None,
    }])
    rc = upsert(df, "d_ordenes_compra", engine_destino, unique_cols=["id_orden_orig"])
    assert rc >= 1

def test_upsert_actualiza_sin_duplicar(engine_destino):
    fila = {"id_orden_orig": 1, "id_proveedor": 10, "proveedor": "Acme",
            "fecha_emision": "2025-01-01", "estado": "pendiente", "total": 100.00,
            "created_at": "2025-01-01", "updated_at": "2025-01-01", "deleted_at": None}
    df1 = pd.DataFrame([fila])
    df2 = pd.DataFrame([{**fila, "total": 200.00}])
    upsert(df1, "d_ordenes_compra", engine_destino, unique_cols=["id_orden_orig"])
    upsert(df2, "d_ordenes_compra", engine_destino, unique_cols=["id_orden_orig"])
    with engine_destino.connect() as conn:
        rows = conn.execute(text("SELECT COUNT(*), SUM(total) FROM d_ordenes_compra")).fetchone()
    assert rows[0] == 1       # no duplicó
    assert float(rows[1]) == 200.00  # valor actualizado
```

---

## Módulo 4: test_extractors.py

Requiere **BD origen** con datos de seed. Usar fixtures que insertan y
limpian via rollback o TRUNCATE.

### Casos a cubrir por extractor

#### inventario
| # | Escenario | Assertion |
|---|---|---|
| 1 | Columnas retornadas | Exactamente las de `d_inventario` (sin `id`) |
| 2 | Watermark filtra correctamente | Solo filas con `updated_at > watermark` |
| 3 | JOIN no duplica | 1 registro en inventario → 1 fila en resultado |
| 4 | `cantidad/cantidad_minima/cantidad_maxima` se mapean a `stock_*` | Alias correctos |

#### movimientos_inventario
| # | Escenario | Assertion |
|---|---|---|
| 5 | `created_at` del movimiento llega como `fecha` | Alias correcto |
| 6 | Watermark filtra por `mi.updated_at` | Funciona igual |

#### facturas
| # | Escenario | Assertion |
|---|---|---|
| 7 | `numero` llega como `numero_factura` | Alias correcto |
| 8 | `razon_social` de tercero llega como `cliente` | Alias correcto |

#### facturas_detalle
| # | Escenario | Assertion |
|---|---|---|
| 9 | Producto sin categoría → fila presente con `categoria = NULL` | LEFT JOIN no descarta |
| 10 | `numero` de factura llega como `numero_factura` | Alias correcto |

#### ordenes_compra
| # | Escenario | Assertion |
|---|---|---|
| 11 | `razon_social` llega como `proveedor` | Alias correcto |

### Patrón de seed para extractors

```python
@pytest.fixture
def seed_factura(engine_origen):
    """Inserta una factura mínima con sucursal, cliente y vendedor conocidos."""
    with engine_origen.begin() as conn:
        # insertar sucursal, empresa, tercero, factura con IDs fijos
        conn.execute(text("INSERT INTO sucursales (id, id_empresa, nombre, codigo, estado) VALUES (901, 1, 'Test', 'T01', 'activo')"))
        conn.execute(text("INSERT INTO terceros (id, id_tipo_identificacion, numero_identificacion, razon_social, estado) VALUES (901, 1, '9999', 'Cliente Test SA', 'activo')"))
        conn.execute(text("""
            INSERT INTO facturas (id, id_sucursal, id_cliente, numero, fecha_emision,
                estado, subtotal, descuento, impuesto, total, saldo, created_at, updated_at)
            VALUES (901, 901, 901, 'F-0001', '2025-01-15',
                'pendiente', 100, 0, 12, 112, 112, NOW(), NOW())
        """))
    yield
    with engine_origen.begin() as conn:
        conn.execute(text("DELETE FROM facturas WHERE id = 901"))
        conn.execute(text("DELETE FROM terceros WHERE id = 901"))
        conn.execute(text("DELETE FROM sucursales WHERE id = 901"))
```

---

## Módulo 5: test_pipeline.py

Testea la **orquestación** mockeando extractors/loaders o usando BD real.

### Casos a cubrir

| # | Escenario | Assertion |
|---|---|---|
| 1 | `run()` sin args ejecuta 5 tablas | `len(results) == 5` |
| 2 | `run(tables=["d_facturas"])` | Solo 1 resultado |
| 3 | `run(tables=["inexistente"])` | Lista vacía, WARNING loggeado |
| 4 | `full_refresh=True` trunca destino | Tabla vacía antes de cargar |
| 5 | `full_refresh=True` borra watermark | `get_watermark` retorna `None` al inicio |
| 6 | Watermark se guarda con timestamp previo a la extracción | `ts_watermark <= ts_inicio_run` |
| 7 | Extractor con error → pipeline continúa con siguientes tablas | Otros resultados en la lista |
| 8 | Resultado con error tiene `error != None` | Campo de error poblado |
| 9 | Stats `leidas`, `rowcount`, `chunks` son correctos | Valores numéricos ≥ 0 |

### Patrón con mock del extractor

```python
from unittest.mock import patch
import pandas as pd
from etl import pipeline

def test_run_tabla_unica(engine_destino):
    results = pipeline.run(tables=["d_facturas"], full_refresh=False)
    assert len(results) == 1
    assert results[0]["tabla"] == "d_facturas"

def test_extractor_con_error_no_aborta(engine_destino):
    def extractor_roto(engine, watermark, chunksize):
        raise RuntimeError("fallo simulado")
        yield  # hace del función un generator

    tabla_cfg = pipeline.TABLES[0]
    with patch.object(tabla_cfg, "extractor", extractor_roto):
        results = pipeline.run(tables=[tabla_cfg.dest_table])
    assert results[0]["error"] is not None
```

---

## Módulo 6: test_integration.py

**End-to-end** con datos reales en ambas BDs. Usa TRUNCATE en ambos sentidos.

### Casos a cubrir

| # | Escenario | Assertion |
|---|---|---|
| 1 | Bootstrap (sin watermark): filas fuente = filas destino | `COUNT(*)` iguales |
| 2 | Segunda ejecución sin cambios: `rowcount = 0` | No re-inserta |
| 3 | Modificar registro en fuente → re-run: destino actualizado | Valor nuevo en destino |
| 4 | Agregar registro en fuente → re-run: aparece en destino | `COUNT` aumenta en 1 |
| 5 | Soft-delete en maestro (ej: `bodegas.deleted_at`): fila excluida | No aparece en destino |
| 6 | `--full-refresh`: destino queda igual que bootstrap | Mismo `COUNT` |
| 7 | Fuente vacía: sin error, `leidas=0` | `results[0]["error"] is None` |
| 8 | Exactamente `CHUNK_SIZE` filas | `chunks == 1`, todas las filas cargadas |
| 9 | `CHUNK_SIZE + 1` filas | `chunks == 2`, todas las filas cargadas |
| 10 | `razon_social` con caracteres especiales (`ñ`, `&`) | Se guarda y recupera igual |
| 11 | Montos con máxima precisión `DECIMAL(15,4)` | Sin pérdida al pasar por pandas |

---

## Helpers recomendados (`helpers/db_etl_helpers.py`)

```python
from sqlalchemy import text

def truncar_tablas_destino(engine_destino, tablas: list[str]):
    with engine_destino.begin() as conn:
        for t in tablas:
            conn.execute(text(f"TRUNCATE TABLE {t}"))

def contar_filas(engine, tabla: str) -> int:
    with engine.connect() as conn:
        return conn.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()

def leer_campo(engine, tabla: str, where_col: str, where_val, campo: str):
    sql = f"SELECT {campo} FROM {tabla} WHERE {where_col} = :v LIMIT 1"
    with engine.connect() as conn:
        return conn.execute(text(sql), {"v": where_val}).scalar()
```

---

## Convenciones de generación de tests ETL

- Nombre de test: `test_<qué>_<cuándo>_<resultado>` (ej: `test_upsert_fila_duplicada_no_duplica`)
- IDs de seed: usar valores ≥ 900 para no colisionar con datos reales
- Fixtures de scope `"function"` por defecto (aislamiento total)
- Fixtures de scope `"session"` solo para engines (costosos de crear)
- Nunca usar `time.sleep()` en tests; si se necesita orden temporal, insertar con `updated_at` explícito
- El `caplog` de pytest para verificar logs: `with caplog.at_level(logging.WARNING): ...`
- Los tests de extractor que necesitan datos mínimos en maestros (sucursales, terceros, productos)
  deben insertar esos maestros en el mismo fixture, no asumir que ya existen
