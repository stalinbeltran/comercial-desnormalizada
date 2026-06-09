"""
Sobrescribe db_connection y rollback para tests/reportes/.
Conecta a comercial_desn_db para poder ejecutar los SQL que consultan
las tablas d_* (d_inventario, d_facturas, d_ordenes_compra, etc.).
"""
import os
import pytest
import mysql.connector
from dotenv import load_dotenv

load_dotenv()

_DESN_CONFIG = {
    "host":     os.getenv("DB_DESN_HOST", "localhost"),
    "port":     int(os.getenv("DB_DESN_PORT", 3306)),
    "user":     os.getenv("DB_DESN_USER", "root"),
    "password": os.getenv("DB_DESN_PASSWORD", ""),
    "database": os.getenv("DB_DESN_NAME", "comercial_desn_db"),
}


@pytest.fixture(scope="session")
def db_connection():
    conn = mysql.connector.connect(**_DESN_CONFIG)
    conn.autocommit = False
    yield conn
    conn.close()


@pytest.fixture(autouse=True)
def rollback(db_connection):
    db_connection.start_transaction()
    try:
        yield
    finally:
        db_connection.rollback()
