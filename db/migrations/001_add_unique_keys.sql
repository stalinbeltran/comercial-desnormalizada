-- =============================================================================
-- Migración 001: UNIQUE KEYs en tablas desnormalizadas
-- Requeridos para que el ETL pueda ejecutar INSERT … ON DUPLICATE KEY UPDATE.
-- Ejecutar una sola vez sobre comercial_desn_db.
-- =============================================================================

USE comercial_desn_db;

-- d_inventario: clave natural compuesta (no hay id_orig)
ALTER TABLE d_inventario
    ADD CONSTRAINT uk_inv_prod_pres_bod
        UNIQUE KEY (id_producto, id_presentacion, id_bodega);

-- d_movimientos_inventario
ALTER TABLE d_movimientos_inventario
    ADD CONSTRAINT uk_mov_orig
        UNIQUE KEY (id_movimiento_orig);

-- d_facturas
ALTER TABLE d_facturas
    ADD CONSTRAINT uk_fac_orig
        UNIQUE KEY (id_factura_orig);

-- d_facturas_detalle
ALTER TABLE d_facturas_detalle
    ADD CONSTRAINT uk_det_orig
        UNIQUE KEY (id_detalle_orig);

-- d_ordenes_compra
ALTER TABLE d_ordenes_compra
    ADD CONSTRAINT uk_oc_orig
        UNIQUE KEY (id_orden_orig);

-- Tabla de control del ETL
CREATE TABLE IF NOT EXISTS etl_watermarks (
    tabla      VARCHAR(100) PRIMARY KEY,
    last_run   DATETIME     NOT NULL,
    updated_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
