# Registro de Errores del Proyecto — comercial-desnormalizada

Fecha de detección: 2026-06-09
Comando ejecutado: `py -m pytest --tb=short`
Resultado: **19 failed, 77 passed, 86 errors**

---

## Resumen

| Categoría | Cantidad | Estado |
|-----------|----------|--------|
| ERRORS (setup failures) | 86 | Parcialmente corregido |
| FAILED | 19 | Parcialmente corregido |
| PASSED | 77 | OK |

---

## ERROR GROUP 1 — `IntegrityError: 1062 Duplicate entry '901' for key 'PRIMARY'`

**Afecta:** todos los tests en `tests/reportes/`
**Cantidad:** ~50 errors de setup

### Síntoma
```
ERROR at setup of TestComprasPorProveedor::test_total_enero_tres_ordenes
tests\conftest.py:51: in seed_base
    cur.execute("INSERT INTO empresas ... VALUES (901, ...)")
E   mysql.connector.errors.IntegrityError: 1062 Duplicate entry '901' for key 'PRIMARY'
```

### Causa raíz
Cadena de fallos:
1. Las queries en `tests/queries/*.sql` referencian tablas `d_*` (`d_inventario`, `d_facturas`, etc.) que **no existen en `comercial_db`** (solo existen en `comercial_desn_db`).
2. Cuando un test llama a `ejecutar_reporte()`, se lanza `ProgrammingError: Table doesn't exist`.
3. En `tests/helpers/db_helpers.py`, `ejecutar_query()` no cerraba el cursor en caso de excepción:
   ```python
   cur = conn.cursor(dictionary=True)
   cur.execute(sql, params)   # lanza ProgrammingError
   rows = cur.fetchall()      # nunca se ejecuta
   cur.close()                # nunca se ejecuta  ← BUG
   ```
4. El cursor sin cerrar dejaba la conexión en estado inconsistente.
5. El fixture `rollback` de `tests/conftest.py` NO usaba `try/finally`:
   ```python
   def rollback(db_connection):
       db_connection.start_transaction()
       yield
       db_connection.rollback()   # podía no ejecutarse si yield lanzaba excepción
   ```
6. Sin rollback, los datos quedaban sin confirmar. Al llamar `start_transaction()` en el siguiente test, MySQL hacía un **commit implícito** de la transacción pendiente (comportamiento estándar de MySQL con `START TRANSACTION`).
7. Los datos con id=901 quedaban **committed** en `comercial_db`.
8. En la siguiente ejecución de pytest, `seed_base` intentaba insertar id=901 → `Duplicate entry`.

### Archivos involucrados
- `tests/helpers/db_helpers.py` — cursor sin cerrar
- `tests/conftest.py` — rollback sin try/finally
- `tests/reportes/test_*.py` — fixtures usan `comercial_db` pero queries usan `d_*`
- `tests/queries/*.sql` — todas las queries referencian tablas `d_*`

### Corrección aplicada
- **`tests/helpers/db_helpers.py`**: cursor cerrado en `finally`
- **`tests/conftest.py`**: `rollback` usa `try/finally`; fixture de sesión `_cleanup_orphaned_data` limpia ids=901 al iniciar
- **`tests/reportes/conftest.py`** (nuevo): sobrescribe `db_connection` → `comercial_desn_db` y `rollback` con `try/finally`
- **`tests/reportes/test_inventario.py`**: reescrito para sembrar directamente en `d_inventario` y `d_movimientos_inventario`
- **`tests/reportes/test_ventas.py`**: reescrito para sembrar en `d_facturas` y `d_facturas_detalle` (EN PROGRESO al interrumpir)
- **`tests/reportes/test_compras.py`**: PENDIENTE
- **`tests/reportes/test_gerenciales.py`**: PENDIENTE
- **`tests/reportes/test_tesoreria.py`**: PENDIENTE

### Patrón de corrección para `tests/reportes/test_*.py`
Cada archivo debe reemplazar fixtures que insertan en tablas normalizadas por fixtures que insertan directamente en la tabla `d_*` correspondiente. Ejemplo:

**ANTES** (incorrecto — usa `comercial_db`):
```python
@pytest.fixture
def seed_facturas(db_connection, seed_base, seed_terceros):
    cur.executemany("INSERT INTO facturas (...) VALUES ...", [...])
```

**DESPUÉS** (correcto — usa `comercial_desn_db` vía conftest local):
```python
@pytest.fixture
def seed_facturas(db_connection):
    cur.executemany("INSERT INTO d_facturas (...) VALUES ...", [...])
```

### Mapeo de tablas por archivo

| Archivo | Tabla normalizada (antes) | Tabla desnormalizada (después) |
|---------|--------------------------|-------------------------------|
| `test_inventario.py` | `inventario`, `productos`, `bodegas` | `d_inventario` |
| `test_inventario.py` | `movimientos_inventario` | `d_movimientos_inventario` |
| `test_ventas.py` | `facturas`, `sucursales`, `terceros` | `d_facturas` |
| `test_ventas.py` | `facturas_detalle`, `facturas`, `productos` | `d_facturas_detalle` |
| `test_compras.py` | `ordenes_compra`, `terceros`, `bodegas` | `d_ordenes_compra` |
| `test_gerenciales.py` | `facturas`, `facturas_detalle` | `d_facturas`, `d_facturas_detalle` |
| `test_tesoreria.py` | `facturas` | `d_facturas` |

### Caso especial: `TestCobrosDelPeriodo` en `test_tesoreria.py`
Este test consulta `pagos_clientes` directamente (tabla normalizada). No existe tabla `d_pagos_clientes` en `comercial_desn_db`. **Debe marcarse con `@pytest.mark.skip`** con mensaje explicativo.

### Columnas relevantes de tablas `d_*`

**`d_inventario`**
```
id, id_producto, codigo_producto, nombre_producto,
id_presentacion, presentacion, id_bodega, bodega,
stock_actual, stock_minimo, stock_maximo, deleted_at
```

**`d_movimientos_inventario`**
```
id, id_movimiento_orig, id_producto, codigo_producto, nombre_producto,
id_bodega, bodega, fecha (DATETIME), tipo_movimiento,
cantidad, cantidad_anterior, cantidad_posterior, costo_unitario,
tipo_referencia, id_referencia, observacion, deleted_at
```

**`d_facturas`**
```
id, id_factura_orig, numero_factura, fecha_emision (DATE),
fecha_vencimiento (DATE), id_sucursal, sucursal, id_cliente, cliente,
subtotal, descuento, impuesto, total, saldo, estado, deleted_at
```

**`d_facturas_detalle`**
```
id, id_detalle_orig, id_factura, numero_factura, fecha_emision (DATE),
id_sucursal, estado_factura, id_producto, codigo_producto, nombre_producto,
id_categoria (NULL), categoria (NULL), cantidad, subtotal, costo_unitario, deleted_at
```

**`d_ordenes_compra`**
```
id, id_orden_orig, id_proveedor, proveedor, fecha_emision (DATE),
estado, total, deleted_at
```

### SQL inline que debe actualizarse

En `test_compras.py::TestOrdenesCompraEstado.test_conteo_por_estado`:
```python
# ANTES — tabla normalizada
sql = "SELECT estado, COUNT(*) AS total FROM ordenes_compra WHERE ..."

# DESPUÉS — tabla desnormalizada
sql = "SELECT estado, COUNT(*) AS total FROM d_ordenes_compra WHERE ..."
```

En `test_gerenciales.py::TestComparativoPeriodos`:
```python
# ANTES — tabla normalizada
sql = "SELECT SUM(f.total) AS total FROM facturas f WHERE ..."

# DESPUÉS — tabla desnormalizada
sql = "SELECT SUM(total) AS total FROM d_facturas WHERE ..."
```

---

## ERROR GROUP 2 — `IntegrityError: 1062 Duplicate entry '801' for key 'PRIMARY'`

**Afecta:** todos los tests en `tests/integracion/`
**Cantidad:** ~36 errors de setup

### Síntoma
```
ERROR at setup of TestOrdenesCompraEstadoIntegracion.test_etl_importa_canceladas
tests\integracion\conftest.py:65: in seed_ordenes_compra
    cur.execute("INSERT INTO empresas ... VALUES (801, ...)")
E   mysql.connector.errors.IntegrityError: 1062 Duplicate entry '801' for key 'PRIMARY'
```

### Causa raíz
Los fixtures en `tests/integracion/conftest.py` hacen **COMMIT explícito** de los datos seed (necesario para que el ETL los vea). El teardown hace DELETE + COMMIT para limpiar. Si pytest es interrumpido (Ctrl+C) o hay un crash **entre el setup COMMIT y el teardown DELETE**, los datos con id=801 quedan permanentemente en `comercial_db`. La siguiente ejecución falla al intentar insertar los mismos ids.

### Archivos involucrados
- `tests/integracion/conftest.py` — todos los fixtures `seed_*`

### Corrección pendiente
Agregar limpieza previa al inicio de los fixtures **antes de INSERT**, junto con un fixture de sesión que limpie datos huérfanos al inicio:

```python
@pytest.fixture(scope="session", autouse=True)
def _cleanup_integ_orphaned(src_conn, dst_conn):
    """Limpia datos con id=801-809 que puedan haber quedado de sesiones abortadas."""
    cur = src_conn.cursor()
    try:
        # Orden inverso de FK
        cur.execute("DELETE FROM facturas_detalle WHERE id_factura IN (801,802,803,804,805,806)")
        cur.execute("DELETE FROM facturas WHERE id IN (801,802,803,804,805,806)")
        cur.execute("DELETE FROM movimientos_inventario WHERE id IN (801,802,803)")
        cur.execute("DELETE FROM inventario WHERE id IN (801,802)")
        cur.execute("DELETE FROM ordenes_compra WHERE id IN (801,802,803,804,805)")
        cur.execute("DELETE FROM terceros_tipos WHERE id IN (801,802)")
        cur.execute("DELETE FROM terceros WHERE id IN (801,802)")
        cur.execute("DELETE FROM tipos_identificacion WHERE id = 801")
        cur.execute("DELETE FROM productos_presentaciones WHERE id IN (801,802)")
        cur.execute("DELETE FROM productos WHERE id IN (801,802)")
        cur.execute("DELETE FROM bodegas WHERE id = 801")
        cur.execute("DELETE FROM sucursales WHERE id = 801")
        cur.execute("DELETE FROM categorias WHERE id = 801")
        cur.execute("DELETE FROM marcas WHERE id = 801")
        cur.execute("DELETE FROM unidades_medida WHERE id = 801")
        cur.execute("DELETE FROM empresas WHERE id = 801")
        src_conn.commit()
    except Exception:
        src_conn.rollback()
    finally:
        cur.close()

    dst_cur = dst_conn.cursor()
    try:
        dst_cur.execute("DELETE FROM d_facturas_detalle WHERE id IN (801,802,803,804,805,806)")
        dst_cur.execute("DELETE FROM d_facturas WHERE id IN (801,802,803,804,805,806)")
        dst_cur.execute("DELETE FROM d_movimientos_inventario WHERE id IN (801,802,803)")
        dst_cur.execute("DELETE FROM d_inventario WHERE id IN (801,802)")
        dst_cur.execute("DELETE FROM d_ordenes_compra WHERE id IN (801,802,803,804,805)")
        dst_conn.commit()
    except Exception:
        dst_conn.rollback()
    finally:
        dst_cur.close()

    yield
```

---

## FAILED GROUP 1 — `ProgrammingError: Table 'comercial_db.d_inventario' doesn't exist`

**Afecta:** `tests/reportes/test_inventario.py::TestStockPorBodega` y `TestProductosBajoMinimo`
**Cantidad:** 8 tests

### Síntoma
```
E   mysql.connector.errors.ProgrammingError: 1146 (42S02): Table 'comercial_db.d_inventario' doesn't exist
```

### Causa raíz
Los tests usan `db_connection` → `comercial_db` (BD normalizada), pero las queries SQL (`inventario.sql`, `productos_bajo_minimo.sql`) hacen SELECT sobre `d_inventario` que **solo existe en `comercial_desn_db`**. La conexión apuntaba a la BD incorrecta.

### Corrección
Cubierta por la corrección del ERROR GROUP 1: el nuevo `tests/reportes/conftest.py` redirige `db_connection` a `comercial_desn_db`.

---

## FAILED GROUP 2 — `AssertionError: d_* tiene 0 filas pero origen tiene N`

**Afecta:** `tests/test_importacion_desnormalizada.py`
**Cantidad:** 11 tests

### Síntoma
```
E   AssertionError: d_inventario tiene 0 filas pero inventario origen tiene 600
E   assert 0 == 600
```

### Causa raíz
Los tests en `tests/integracion/conftest.py` ejecutan `importar_tabla()` en su setup, que hace `TRUNCATE TABLE d_*` antes de importar. El teardown también hace `TRUNCATE TABLE d_*`. Como resultado, **todas las tablas `d_*` quedan vacías** después de que corren los tests de integración. 

`tests/test_importacion_desnormalizada.py` se ejecuta **después** (orden alfabético en pytest) y encuentra las tablas vacías.

El docstring del archivo ya indicaba que estos tests deben ejecutarse tras `py db/importar_desnormalizada.py`, pero no estaban aislados del ciclo normal de pytest.

### Corrección pendiente
Agregar fixture `autouse` de módulo que ejecute el full-load antes de los tests:

```python
@pytest.fixture(scope="module", autouse=True)
def _full_load(src, dst):
    """Re-ejecuta la importación completa antes de verificar conteos."""
    from db.importar_desnormalizada import importar_tabla, TABLAS_ORDEN
    for tabla in TABLAS_ORDEN:
        importar_tabla(src, dst, tabla, batch_size=500)
    yield
```

Agregar al inicio de `tests/test_importacion_desnormalizada.py`, antes de los fixtures de conexión.

---

## Estado de correcciones

| Corrección | Archivo | Estado |
|------------|---------|--------|
| Cursor cerrado en `finally` | `tests/helpers/db_helpers.py` | ✅ Aplicada |
| `rollback` con `try/finally` | `tests/conftest.py` | ✅ Aplicada |
| Fixture sesión limpia id=901 huérfanos | `tests/conftest.py` | ✅ Aplicada |
| Nuevo conftest redirige a `comercial_desn_db` | `tests/reportes/conftest.py` | ✅ Aplicada |
| Seeds reescritos en `d_inventario`, `d_movimientos_inventario` | `tests/reportes/test_inventario.py` | ✅ Aplicada |
| Seeds reescritos en `d_facturas`, `d_facturas_detalle` | `tests/reportes/test_ventas.py` | ⚠️ Parcial (interrumpido) |
| Seeds reescritos en `d_ordenes_compra`, SQL inline | `tests/reportes/test_compras.py` | ❌ Pendiente |
| Seeds reescritos en `d_facturas`/`d_facturas_detalle`, SQL inline | `tests/reportes/test_gerenciales.py` | ❌ Pendiente |
| Seeds reescritos en `d_facturas`, skip `TestCobrosDelPeriodo` | `tests/reportes/test_tesoreria.py` | ❌ Pendiente |
| Fixture sesión limpia id=801 huérfanos | `tests/integracion/conftest.py` | ❌ Pendiente |
| Fixture `_full_load` autouse | `tests/test_importacion_desnormalizada.py` | ❌ Pendiente |

---

## Comandos de verificación

```bash
# Verificar solo errores corregidos hasta ahora
py -m pytest tests/etl/ tests/reportes/test_inventario.py --tb=short -q

# Suite completa
py -m pytest --tb=short -q

# Test de importación (requiere full-load o fixture autouse)
py -m pytest tests/test_importacion_desnormalizada.py -v

# Tests de integración
py -m pytest tests/integracion/ --tb=short -q
```

---

## Notas adicionales

- Los IDs de seed en `tests/reportes/` usan rango **901+**
- Los IDs de seed en `tests/integracion/` usan rango **801–809**
- Los IDs de seed en `tests/etl/` usan rango **9001+**
- Esta separación de rangos es intencional para evitar colisiones entre suites
- El fixture `rollback` en `tests/conftest.py` es `autouse=True` → aplica a todos los tests bajo `tests/` salvo que sea sobreescrito localmente (como hace `tests/reportes/conftest.py` y `tests/reportes_desn/conftest.py`)
