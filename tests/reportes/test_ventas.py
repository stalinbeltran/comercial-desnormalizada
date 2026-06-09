"""
Tests del módulo de Ventas sobre la BD desnormalizada.

Siembra directamente en d_facturas / d_facturas_detalle.
"""
import pytest
from decimal import Decimal
from tests.helpers.db_helpers import ejecutar_reporte, ejecutar_query


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def seed_facturas(db_connection):
    """
    3 facturas en enero 2025, 1 en febrero, 1 anulada en enero.
    """
    cur = db_connection.cursor()
    cur.executemany("""
        INSERT INTO d_facturas
            (id, id_factura_orig, numero_factura, fecha_emision, fecha_vencimiento,
             id_sucursal, sucursal, id_cliente, cliente,
             subtotal, descuento, impuesto, total, saldo, estado)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        (901, 901, 'F-001', '2025-01-10', '2025-02-10', 901, 'Sucursal Test', 901, 'Cliente Test SA',  89.29, 0, 10.71, 100.00, 100.00, 'activa'),
        (902, 902, 'F-002', '2025-01-15', '2025-02-15', 901, 'Sucursal Test', 901, 'Cliente Test SA', 178.57, 0, 21.43, 200.00, 200.00, 'activa'),
        (903, 903, 'F-003', '2025-01-20', '2025-02-20', 901, 'Sucursal Test', 901, 'Cliente Test SA', 267.86, 0, 32.14, 300.00, 300.00, 'activa'),
        (904, 904, 'F-004', '2025-02-05', '2025-03-05', 901, 'Sucursal Test', 901, 'Cliente Test SA', 891.96, 0, 107.04, 999.00, 999.00, 'activa'),
        (905, 905, 'F-ANU', '2025-01-25', '2025-02-25', 901, 'Sucursal Test', 901, 'Cliente Test SA', 446.43, 0, 53.57, 500.00, 500.00, 'anulada'),
    ])
    cur.close()


@pytest.fixture
def seed_facturas_con_detalle(db_connection, seed_facturas):
    """Agrega detalle a F-001, F-002 (prod 901) y F-003 (prod 902)."""
    cur = db_connection.cursor()
    cur.executemany("""
        INSERT INTO d_facturas_detalle
            (id, id_detalle_orig, id_factura, numero_factura, fecha_emision,
             id_sucursal, estado_factura,
             id_producto, codigo_producto, nombre_producto, id_categoria, categoria,
             cantidad, subtotal, costo_unitario)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """, [
        (901, 901, 901, 'F-001', '2025-01-10', 901, 'activa', 901, 'PROD-T01', 'Producto Test Uno', None, None,  5.0000, 100.00, 10.00),
        (902, 902, 902, 'F-002', '2025-01-15', 901, 'activa', 901, 'PROD-T01', 'Producto Test Uno', None, None, 10.0000, 200.00, 10.00),
        (903, 903, 903, 'F-003', '2025-01-20', 901, 'activa', 902, 'PROD-T02', 'Producto Test Dos', None, None, 15.0000, 300.00, 10.00),
    ])
    cur.close()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestVentasPorPeriodo:

    def test_total_enero_tres_facturas(self, db_connection, seed_facturas):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_periodo.sql",
            ("2025-01-01", "2025-01-31", None, None)
        )
        assert len(resultado) == 3
        total = sum(r["total"] for r in resultado)
        assert total == Decimal("600.00")

    def test_facturas_anuladas_excluidas(self, db_connection, seed_facturas):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_periodo.sql",
            ("2025-01-01", "2025-01-31", None, None)
        )
        numeros = [r["numero_factura"] for r in resultado]
        assert "F-ANU" not in numeros

    def test_filtro_sucursal_solo_devuelve_esa_sucursal(self, db_connection, seed_facturas):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_periodo.sql",
            ("2025-01-01", "2025-01-31", 901, 901)
        )
        assert len(resultado) == 3

    def test_filtro_fecha_excluye_febrero(self, db_connection, seed_facturas):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_periodo.sql",
            ("2025-01-01", "2025-01-31", None, None)
        )
        numeros = [r["numero_factura"] for r in resultado]
        assert "F-004" not in numeros

    def test_periodo_sin_facturas_retorna_vacio(self, db_connection, seed_facturas):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_periodo.sql",
            ("2024-01-01", "2024-01-31", None, None)
        )
        assert resultado == []

    def test_totales_individuales_correctos(self, db_connection, seed_facturas):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_periodo.sql",
            ("2025-01-01", "2025-01-31", None, None)
        )
        totales = {r["numero_factura"]: r["total"] for r in resultado}
        assert totales["F-001"] == Decimal("100.00")
        assert totales["F-002"] == Decimal("200.00")
        assert totales["F-003"] == Decimal("300.00")


class TestVentasPorProducto:

    def test_ranking_correcto(self, db_connection, seed_facturas_con_detalle):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_producto.sql",
            ("2025-01-01", "2025-01-31")
        )
        assert len(resultado) == 2
        por_codigo = {r["codigo_producto"]: r for r in resultado}
        assert por_codigo["PROD-T01"]["total_venta"] == Decimal("300.00")
        assert por_codigo["PROD-T02"]["total_venta"] == Decimal("300.00")

    def test_margen_bruto_calculado(self, db_connection, seed_facturas_con_detalle):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_producto.sql",
            ("2025-01-01", "2025-01-31")
        )
        for r in resultado:
            assert r["margen_bruto"] == Decimal("150.00")

    def test_periodo_sin_ventas_retorna_vacio(self, db_connection, seed_facturas_con_detalle):
        resultado = ejecutar_reporte(
            db_connection, "ventas_por_producto.sql",
            ("2024-01-01", "2024-01-31")
        )
        assert resultado == []
