"""
Tests del módulo de Inventario sobre la BD desnormalizada.

Siembra directamente en d_inventario / d_movimientos_inventario
(sin cadena FK de la BD normalizada).
"""
import pytest
from decimal import Decimal
from tests.helpers.db_helpers import ejecutar_reporte, ejecutar_query


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_inventario(db_connection):
    """Stock inicial: Producto 1 = 50 und, Producto 2 = 3 und (bajo mínimo de 10)."""
    cur = db_connection.cursor()
    cur.executemany("""
        INSERT INTO d_inventario
            (id, id_producto, codigo_producto, nombre_producto,
             id_presentacion, presentacion,
             id_bodega, bodega,
             stock_actual, stock_minimo, stock_maximo)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        (901, 901, 'PROD-T01', 'Producto Test Uno', 901, 'Unidad', 901, 'Bodega Test',  50.0000, 10.0000, 200.0000),
        (902, 902, 'PROD-T02', 'Producto Test Dos', 902, 'Unidad', 901, 'Bodega Test',   3.0000, 10.0000, 100.0000),
    ])
    cur.close()


@pytest.fixture
def seed_kardex(db_connection, seed_inventario):
    """
    Kardex del Producto 1 en Bodega 901:
      entrada  +30  → saldo 30
      entrada  +20  → saldo 50
      salida   -15  → saldo 35
    Saldo esperado final: 35
    """
    cur = db_connection.cursor()
    cur.executemany("""
        INSERT INTO d_movimientos_inventario
            (id, id_movimiento_orig,
             id_producto, codigo_producto, nombre_producto,
             id_bodega, bodega,
             fecha, tipo_movimiento,
             cantidad, cantidad_anterior, cantidad_posterior,
             costo_unitario, tipo_referencia, id_referencia, observacion)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        (901, 901, 901, 'PROD-T01', 'Producto Test Uno', 901, 'Bodega Test',
         '2025-01-10 08:00:00', 'entrada', 30, 0,  30, 5.00, None, None, None),
        (902, 902, 901, 'PROD-T01', 'Producto Test Uno', 901, 'Bodega Test',
         '2025-01-11 08:00:00', 'entrada', 20, 30, 50, 5.00, None, None, None),
        (903, 903, 901, 'PROD-T01', 'Producto Test Uno', 901, 'Bodega Test',
         '2025-01-12 08:00:00', 'salida',  15, 50, 35, 5.00, None, None, None),
    ])
    cur.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestStockPorBodega:

    def test_retorna_filas_para_bodega_con_stock(self, db_connection, seed_inventario):
        resultado = ejecutar_reporte(db_connection, "inventario.sql", (901,))
        assert len(resultado) == 2

    def test_cantidades_exactas(self, db_connection, seed_inventario):
        resultado = ejecutar_reporte(db_connection, "inventario.sql", (901,))
        stocks = {r["codigo_producto"]: r["stock_actual"] for r in resultado}
        assert stocks["PROD-T01"] == Decimal("50.0000")
        assert stocks["PROD-T02"] == Decimal("3.0000")

    def test_bodega_sin_stock_retorna_lista_vacia(self, db_connection):
        resultado = ejecutar_reporte(db_connection, "inventario.sql", (901,))
        assert resultado == []

    def test_no_incluye_productos_eliminados(self, db_connection, seed_inventario):
        cur = db_connection.cursor()
        cur.execute("UPDATE d_inventario SET deleted_at = NOW() WHERE id = 901")
        cur.close()
        resultado = ejecutar_reporte(db_connection, "inventario.sql", (901,))
        codigos = [r["codigo_producto"] for r in resultado]
        assert "PROD-T01" not in codigos


class TestProductosBajoMinimo:

    def test_detecta_producto_bajo_minimo(self, db_connection, seed_inventario):
        resultado = ejecutar_reporte(db_connection, "productos_bajo_minimo.sql", (901,))
        assert len(resultado) == 1
        assert resultado[0]["codigo_producto"] == "PROD-T02"

    def test_no_incluye_productos_con_stock_suficiente(self, db_connection, seed_inventario):
        resultado = ejecutar_reporte(db_connection, "productos_bajo_minimo.sql", (901,))
        codigos = [r["codigo_producto"] for r in resultado]
        assert "PROD-T01" not in codigos

    def test_sin_productos_bajo_minimo_retorna_vacio(self, db_connection):
        resultado = ejecutar_reporte(db_connection, "productos_bajo_minimo.sql", (901,))
        assert resultado == []

    def test_stock_igual_a_minimo_no_aparece(self, db_connection, seed_inventario):
        cur = db_connection.cursor()
        cur.execute("UPDATE d_inventario SET stock_actual = 10.0000 WHERE id = 902")
        cur.close()
        resultado = ejecutar_reporte(db_connection, "productos_bajo_minimo.sql", (901,))
        assert resultado == []


class TestKardex:

    def test_numero_de_movimientos(self, db_connection, seed_kardex):
        resultado = ejecutar_reporte(
            db_connection, "kardex.sql",
            (901, 901, "2020-01-01", "2099-12-31")
        )
        assert len(resultado) == 3

    def test_saldo_final_cuadra(self, db_connection, seed_kardex):
        resultado = ejecutar_reporte(
            db_connection, "kardex.sql",
            (901, 901, "2020-01-01", "2099-12-31")
        )
        assert resultado[-1]["cantidad_posterior"] == Decimal("35.0000")

    def test_filtro_de_fecha_excluye_movimientos_fuera_de_rango(self, db_connection, seed_kardex):
        resultado = ejecutar_reporte(
            db_connection, "kardex.sql",
            (901, 901, "2000-01-01", "2000-01-31")
        )
        assert resultado == []

    def test_secuencia_de_saldos_es_coherente(self, db_connection, seed_kardex):
        resultado = ejecutar_reporte(
            db_connection, "kardex.sql",
            (901, 901, "2020-01-01", "2099-12-31")
        )
        for r in resultado:
            if r["tipo_movimiento"] == "entrada":
                esperado = r["cantidad_anterior"] + r["cantidad"]
            else:
                esperado = r["cantidad_anterior"] - r["cantidad"]
            assert r["cantidad_posterior"] == pytest.approx(float(esperado), abs=0.0001)
