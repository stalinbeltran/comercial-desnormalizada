# Comandos del Proyecto — Comercial Desnormalizada

Referencia de todos los comandos ejecutables del proyecto, organizados por categoría.

---

## 1. Instalación de dependencias

```bash
pip install -r requirements.txt
```

---

## 2. Base de datos — Creación

Crea `comercial_desn_db` con las tablas desnormalizadas y la tabla de control `etl_watermarks`:

```bash
mysql -h localhost -u root -p < db/create/create_desnormalizada.sql
```

Aplica constraints UNIQUE KEY necesarias para el upsert del ETL:

```bash
mysql -h localhost -u root -p comercial_desn_db < db/migrations/001_add_unique_keys.sql
```

---

## 3. Carga masiva inicial (full-load)

Trunca todas las tablas destino y recarga desde `comercial_db`. Idempotente.

```bash
# Todas las tablas
python db/importar_desnormalizada.py

# Solo una tabla
python db/importar_desnormalizada.py --tabla d_inventario
python db/importar_desnormalizada.py --tabla d_movimientos_inventario
python db/importar_desnormalizada.py --tabla d_facturas
python db/importar_desnormalizada.py --tabla d_facturas_detalle
python db/importar_desnormalizada.py --tabla d_ordenes_compra

# Ajustar tamaño de lote (default 500)
python db/importar_desnormalizada.py --batch-size 1000
python db/importar_desnormalizada.py --tabla d_facturas --batch-size 2000
```

---

## 4. ETL incremental

Sincroniza solo registros modificados desde el último watermark.

```bash
# Todas las tablas
py etl/run_etl.py

# Una tabla específica
py etl/run_etl.py --table d_inventario
py etl/run_etl.py --table d_movimientos_inventario
py etl/run_etl.py --table d_facturas
py etl/run_etl.py --table d_facturas_detalle
py etl/run_etl.py --table d_ordenes_compra

# Múltiples tablas
py etl/run_etl.py -t d_facturas -t d_ordenes_compra
```

### Full-refresh (truncar + recargar desde cero)

Borra el watermark, trunca la tabla destino y recarga todo:

```bash
# Una tabla
py etl/run_etl.py --full-refresh --table d_facturas

# Todas las tablas
py etl/run_etl.py --full-refresh
```

---

## 5. Tests

```bash
# Suite completa
pytest

# Por directorio
pytest tests/etl/
pytest tests/reportes/
pytest tests/reportes_desn/
pytest tests/integracion/

# Archivos individuales
pytest tests/etl/test_watermark.py
pytest tests/etl/test_pipeline.py
pytest tests/etl/test_extractors.py
pytest tests/etl/test_transformer.py
pytest tests/etl/test_upsert.py
pytest tests/etl/test_integration.py

# Test específico
pytest tests/etl/test_watermark.py::test_get_watermark_sin_registro

# Con cobertura
pytest --cov=etl --cov=db --cov-report=html

# Verbose / salida corta
pytest -v
pytest --tb=short
```

---

## 6. Variables de entorno (.env)

```env
# BD origen (normalizada)
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=<password>
DB_NAME=comercial_db

# BD destino (desnormalizada)
DB_DESN_HOST=localhost
DB_DESN_PORT=3306
DB_DESN_USER=root
DB_DESN_PASSWORD=<password>
DB_DESN_NAME=comercial_desn_db

# ETL (opcional)
ETL_CHUNK_SIZE=5000
```

---

## 7. Flujo completo — Setup inicial

```bash
pip install -r requirements.txt
mysql -h localhost -u root -p < db/create/create_desnormalizada.sql
mysql -h localhost -u root -p comercial_desn_db < db/migrations/001_add_unique_keys.sql
python db/importar_desnormalizada.py
pytest tests/etl/test_integration.py -v
```

## 8. Flujo operativo — Sincronización incremental diaria

```bash
py etl/run_etl.py
pytest tests/etl/test_integration.py
```

---

## Referencia rápida — Tablas ETL

| Tabla destino               | Tablas origen (JOIN)                                              |
|-----------------------------|-------------------------------------------------------------------|
| `d_inventario`              | inventario + productos + productos_presentaciones + bodegas       |
| `d_movimientos_inventario`  | movimientos_inventario + productos + bodegas                      |
| `d_facturas`                | facturas + sucursales + terceros                                  |
| `d_facturas_detalle`        | facturas_detalle + facturas + productos + categorias              |
| `d_ordenes_compra`          | ordenes_compra + terceros                                         |
