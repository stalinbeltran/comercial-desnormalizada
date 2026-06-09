"""
Punto de entrada CLI del ETL.

Uso:
    py etl/run_etl.py                                  # incremental, todas las tablas
    py etl/run_etl.py --table d_facturas               # incremental, una tabla
    py etl/run_etl.py --full-refresh                   # recarga total, todas
    py etl/run_etl.py --full-refresh --table d_facturas
"""

import argparse
import logging
import sys
from pathlib import Path

# Garantiza que la raíz del proyecto esté en sys.path al ejecutar como script
sys.path.insert(0, str(Path(__file__).parent.parent))

from etl import pipeline


def _setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="ETL comercial_db → comercial_desn_db")
    parser.add_argument(
        "--table", "-t",
        action="append",
        dest="tables",
        metavar="TABLA",
        help="Tabla destino a procesar (repetible). Omitir = todas.",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Truncar tabla destino y recargar desde cero.",
    )
    return parser.parse_args()


def main() -> int:
    _setup_logging()
    args    = _parse_args()
    results = pipeline.run(tables=args.tables, full_refresh=args.full_refresh)

    errores = [r for r in results if r["error"]]
    if errores:
        logging.getLogger(__name__).error(
            "%d tabla(s) finalizaron con errores.", len(errores)
        )
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
