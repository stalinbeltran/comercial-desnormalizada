import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Callable

from etl.config import CHUNK_SIZE, engine_destino, engine_origen
from etl.extractors import (facturas, facturas_detalle, inventario, movimientos,
                             ordenes_compra)
from etl.loaders.upsert import upsert_chunk_safe
from etl.transformers.common import clean
from etl.watermark import clear_watermark, get_watermark, set_watermark

logger = logging.getLogger(__name__)


@dataclass
class TableConfig:
    name: str                      # nombre en etl_watermarks
    dest_table: str                # tabla destino en comercial_desn_db
    extractor: Callable            # función extract(engine, watermark, chunksize)
    required_cols: list[str]       # columnas NOT NULL para dropna
    unique_cols: list[str]         # columnas del UNIQUE KEY destino


TABLES: list[TableConfig] = [
    TableConfig(
        name="d_inventario",
        dest_table="d_inventario",
        extractor=inventario.extract,
        required_cols=["id_producto", "id_presentacion", "id_bodega"],
        unique_cols=["id_producto", "id_presentacion", "id_bodega"],
    ),
    TableConfig(
        name="d_movimientos_inventario",
        dest_table="d_movimientos_inventario",
        extractor=movimientos.extract,
        required_cols=["id_movimiento_orig", "id_producto", "id_bodega"],
        unique_cols=["id_movimiento_orig"],
    ),
    TableConfig(
        name="d_facturas",
        dest_table="d_facturas",
        extractor=facturas.extract,
        required_cols=["id_factura_orig", "id_sucursal", "id_cliente"],
        unique_cols=["id_factura_orig"],
    ),
    TableConfig(
        name="d_facturas_detalle",
        dest_table="d_facturas_detalle",
        extractor=facturas_detalle.extract,
        required_cols=["id_detalle_orig", "id_factura", "id_producto"],
        unique_cols=["id_detalle_orig"],
    ),
    TableConfig(
        name="d_ordenes_compra",
        dest_table="d_ordenes_compra",
        extractor=ordenes_compra.extract,
        required_cols=["id_orden_orig", "id_proveedor"],
        unique_cols=["id_orden_orig"],
    ),
]


def _run_table(cfg: TableConfig, full_refresh: bool) -> dict:
    log = logger.getChild(cfg.name)
    t0  = time.monotonic()

    if full_refresh:
        log.info("Full-refresh: truncando %s y borrando watermark", cfg.dest_table)
        from sqlalchemy import text
        with engine_destino.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {cfg.dest_table}"))
        clear_watermark(engine_destino, cfg.name)

    extraction_start = datetime.now()
    watermark        = get_watermark(engine_destino, cfg.name)
    log.info("Extrayendo desde watermark: %s", watermark or "inicio")

    total_leidas = total_rowcount = chunk_num = 0

    try:
        for chunk in cfg.extractor(engine_origen, watermark, CHUNK_SIZE):
            chunk_num += 1
            leidas = len(chunk)
            total_leidas += leidas

            df = clean(chunk, cfg.required_cols)
            rc = upsert_chunk_safe(df, cfg.dest_table, engine_destino,
                                   cfg.unique_cols, chunk_num)
            total_rowcount += rc
            log.debug("Chunk %d: %d leídas → rowcount %d", chunk_num, leidas, rc)

    except Exception as exc:
        log.error("Error fatal en extracción de %s: %s", cfg.name, exc)
        return {
            "tabla": cfg.name, "leidas": total_leidas,
            "rowcount": total_rowcount, "chunks": chunk_num,
            "segundos": round(time.monotonic() - t0, 2), "error": str(exc),
        }

    set_watermark(engine_destino, cfg.name, extraction_start)

    stats = {
        "tabla": cfg.name,
        "leidas": total_leidas,
        "rowcount": total_rowcount,
        "chunks": chunk_num,
        "segundos": round(time.monotonic() - t0, 2),
        "error": None,
    }
    log.info(
        "OK — leídas=%d rowcount=%d chunks=%d tiempo=%.2fs",
        stats["leidas"], stats["rowcount"], stats["chunks"], stats["segundos"],
    )
    return stats


def run(tables: list[str] | None = None, full_refresh: bool = False) -> list[dict]:
    """
    Ejecuta el pipeline ETL.

    Args:
        tables: lista de nombres de tabla destino a procesar;
                None = todas.
        full_refresh: trunca y recarga desde cero cada tabla seleccionada.
    """
    selected = (
        [t for t in TABLES if t.dest_table in tables]
        if tables
        else TABLES
    )

    if not selected:
        logger.warning("Ninguna tabla coincide con %s", tables)
        return []

    results = []
    for cfg in selected:
        results.append(_run_table(cfg, full_refresh))

    _log_summary(results)
    return results


def _log_summary(results: list[dict]) -> None:
    logger.info("=" * 60)
    logger.info("RESUMEN ETL")
    for r in results:
        status = "ERROR" if r["error"] else "OK"
        logger.info(
            "  [%s] %-35s leídas=%-8d rowcount=%-8d %.2fs",
            status, r["tabla"], r["leidas"], r["rowcount"], r["segundos"],
        )
    logger.info("=" * 60)
