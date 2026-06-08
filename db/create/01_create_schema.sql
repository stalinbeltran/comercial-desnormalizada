-- =============================================================================
-- EMPRESA COMERCIAL DB — Esquema completo
-- Motor: MySQL 8.0+
-- Convenciones:
--   · Todas las tablas: id PK, created_at, updated_at, deleted_at (soft delete)
--   · Montos: DECIMAL(15,2)  |  Cantidades: DECIMAL(15,4)
--   · FK nombradas: id_<tabla_referenciada>
--   · snake_case plural en nombres de tabla
-- =============================================================================
  
CREATE DATABASE IF NOT EXISTS comercial_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE comercial_db;

-- =============================================================================
-- MODULO: ORGANIZACION
-- =============================================================================

CREATE TABLE empresas (
    id            INT            NOT NULL AUTO_INCREMENT,
    razon_social  VARCHAR(200)   NOT NULL,
    nombre_comercial VARCHAR(200) NULL,
    ruc_rif       VARCHAR(30)    NOT NULL,
    direccion     VARCHAR(500)   NULL,
    telefono      VARCHAR(30)    NULL,
    email         VARCHAR(100)   NULL,
    sitio_web     VARCHAR(200)   NULL,
    logo_url      VARCHAR(500)   NULL,
    moneda        CHAR(3)        NOT NULL DEFAULT 'USD',
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_empresas_ruc (ruc_rif)
) ENGINE=InnoDB;

CREATE TABLE areas (
    id            INT            NOT NULL AUTO_INCREMENT,
    id_empresa    INT            NOT NULL,
    nombre        VARCHAR(100)   NOT NULL,
    descripcion   VARCHAR(300)   NULL,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_areas_empresa (id_empresa),
    CONSTRAINT fk_areas_empresa FOREIGN KEY (id_empresa) REFERENCES empresas (id)
) ENGINE=InnoDB;

CREATE TABLE cargos (
    id            INT            NOT NULL AUTO_INCREMENT,
    id_empresa    INT            NOT NULL,
    nombre        VARCHAR(100)   NOT NULL,
    descripcion   VARCHAR(300)   NULL,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_cargos_empresa (id_empresa),
    CONSTRAINT fk_cargos_empresa FOREIGN KEY (id_empresa) REFERENCES empresas (id)
) ENGINE=InnoDB;

CREATE TABLE sucursales (
    id            INT            NOT NULL AUTO_INCREMENT,
    id_empresa    INT            NOT NULL,
    nombre        VARCHAR(150)   NOT NULL,
    codigo        VARCHAR(20)    NOT NULL,
    direccion     VARCHAR(500)   NULL,
    telefono      VARCHAR(30)    NULL,
    email         VARCHAR(100)   NULL,
    estado        TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activa, 0=inactiva',
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_sucursales_codigo (codigo, id_empresa),
    KEY ix_sucursales_empresa (id_empresa),
    CONSTRAINT fk_sucursales_empresa FOREIGN KEY (id_empresa) REFERENCES empresas (id)
) ENGINE=InnoDB;

CREATE TABLE bodegas (
    id            INT            NOT NULL AUTO_INCREMENT,
    id_sucursal   INT            NOT NULL,
    nombre        VARCHAR(150)   NOT NULL,
    codigo        VARCHAR(20)    NOT NULL,
    descripcion   VARCHAR(300)   NULL,
    estado        TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activa, 0=inactiva',
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_bodegas_codigo (codigo, id_sucursal),
    KEY ix_bodegas_sucursal (id_sucursal),
    CONSTRAINT fk_bodegas_sucursal FOREIGN KEY (id_sucursal) REFERENCES sucursales (id)
) ENGINE=InnoDB;

CREATE TABLE empleados (
    id                    INT            NOT NULL AUTO_INCREMENT,
    id_sucursal           INT            NOT NULL,
    id_area               INT            NULL,
    id_cargo              INT            NULL,
    nombres               VARCHAR(100)   NOT NULL,
    apellidos             VARCHAR(100)   NOT NULL,
    tipo_identificacion   VARCHAR(20)    NOT NULL COMMENT 'cedula, ruc, pasaporte',
    numero_identificacion VARCHAR(30)    NOT NULL,
    email                 VARCHAR(100)   NULL,
    telefono              VARCHAR(30)    NULL,
    fecha_ingreso         DATE           NOT NULL,
    estado                TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activo, 0=inactivo',
    created_at            DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at            DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_empleados_identificacion (numero_identificacion),
    KEY ix_empleados_sucursal (id_sucursal),
    KEY ix_empleados_area (id_area),
    KEY ix_empleados_cargo (id_cargo),
    CONSTRAINT fk_empleados_sucursal FOREIGN KEY (id_sucursal) REFERENCES sucursales (id),
    CONSTRAINT fk_empleados_area     FOREIGN KEY (id_area)     REFERENCES areas (id),
    CONSTRAINT fk_empleados_cargo    FOREIGN KEY (id_cargo)    REFERENCES cargos (id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULO: PRODUCTOS E INVENTARIO
-- =============================================================================

CREATE TABLE unidades_medida (
    id            INT            NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(60)    NOT NULL,
    abreviatura   VARCHAR(10)    NOT NULL,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_unidades_abreviatura (abreviatura)
) ENGINE=InnoDB;

CREATE TABLE marcas (
    id            INT            NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(100)   NOT NULL,
    descripcion   VARCHAR(300)   NULL,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_marcas_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE categorias (
    id                  INT            NOT NULL AUTO_INCREMENT,
    id_categoria_padre  INT            NULL,
    nombre              VARCHAR(100)   NOT NULL,
    descripcion         VARCHAR(300)   NULL,
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_categorias_padre (id_categoria_padre),
    CONSTRAINT fk_categorias_padre FOREIGN KEY (id_categoria_padre) REFERENCES categorias (id)
) ENGINE=InnoDB;

CREATE TABLE productos (
    id                INT            NOT NULL AUTO_INCREMENT,
    id_categoria      INT            NULL,
    id_marca          INT            NULL,
    id_unidad_medida  INT            NOT NULL,
    codigo            VARCHAR(50)    NOT NULL,
    nombre            VARCHAR(200)   NOT NULL,
    descripcion       TEXT           NULL,
    aplica_impuesto   TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=si, 0=no',
    porcentaje_impuesto DECIMAL(5,2) NOT NULL DEFAULT 0.00,
    estado            TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activo, 0=inactivo',
    created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at        DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_productos_codigo (codigo),
    KEY ix_productos_categoria (id_categoria),
    KEY ix_productos_marca (id_marca),
    KEY ix_productos_unidad (id_unidad_medida),
    CONSTRAINT fk_productos_categoria    FOREIGN KEY (id_categoria)     REFERENCES categorias (id),
    CONSTRAINT fk_productos_marca        FOREIGN KEY (id_marca)          REFERENCES marcas (id),
    CONSTRAINT fk_productos_unidad_medida FOREIGN KEY (id_unidad_medida) REFERENCES unidades_medida (id)
) ENGINE=InnoDB;

CREATE TABLE productos_presentaciones (
    id                  INT            NOT NULL AUTO_INCREMENT,
    id_producto         INT            NOT NULL,
    nombre              VARCHAR(100)   NOT NULL,
    factor_conversion   DECIMAL(15,4)  NOT NULL DEFAULT 1.0000 COMMENT 'unidades base por presentacion',
    codigo_barras       VARCHAR(50)    NULL,
    estado              TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activa, 0=inactiva',
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_presentaciones_barras (codigo_barras),
    KEY ix_presentaciones_producto (id_producto),
    CONSTRAINT fk_presentaciones_producto FOREIGN KEY (id_producto) REFERENCES productos (id)
) ENGINE=InnoDB;

CREATE TABLE inventario (
    id                INT            NOT NULL AUTO_INCREMENT,
    id_producto       INT            NOT NULL,
    id_presentacion   INT            NOT NULL,
    id_bodega         INT            NOT NULL,
    cantidad          DECIMAL(15,4)  NOT NULL DEFAULT 0.0000,
    cantidad_minima   DECIMAL(15,4)  NOT NULL DEFAULT 0.0000,
    cantidad_maxima   DECIMAL(15,4)  NULL,
    created_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at        DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_inventario (id_producto, id_presentacion, id_bodega),
    KEY ix_inventario_bodega (id_bodega),
    CONSTRAINT fk_inventario_producto     FOREIGN KEY (id_producto)     REFERENCES productos (id),
    CONSTRAINT fk_inventario_presentacion FOREIGN KEY (id_presentacion) REFERENCES productos_presentaciones (id),
    CONSTRAINT fk_inventario_bodega       FOREIGN KEY (id_bodega)       REFERENCES bodegas (id)
) ENGINE=InnoDB;

CREATE TABLE movimientos_inventario (
    id                  INT            NOT NULL AUTO_INCREMENT,
    id_producto         INT            NOT NULL,
    id_presentacion     INT            NOT NULL,
    id_bodega           INT            NOT NULL,
    tipo_movimiento     VARCHAR(20)    NOT NULL COMMENT 'entrada, salida, traslado_entrada, traslado_salida, ajuste_positivo, ajuste_negativo',
    cantidad            DECIMAL(15,4)  NOT NULL,
    cantidad_anterior   DECIMAL(15,4)  NOT NULL,
    cantidad_posterior  DECIMAL(15,4)  NOT NULL,
    costo_unitario      DECIMAL(15,2)  NULL,
    id_referencia       INT            NULL COMMENT 'id del documento origen',
    tipo_referencia     VARCHAR(50)    NULL COMMENT 'recepcion, factura, pedido, ajuste',
    observacion         VARCHAR(500)   NULL,
    id_usuario          INT            NULL,
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_movinv_producto (id_producto),
    KEY ix_movinv_bodega (id_bodega),
    KEY ix_movinv_referencia (tipo_referencia, id_referencia),
    KEY ix_movinv_created (created_at),
    CONSTRAINT fk_movinv_producto     FOREIGN KEY (id_producto)     REFERENCES productos (id),
    CONSTRAINT fk_movinv_presentacion FOREIGN KEY (id_presentacion) REFERENCES productos_presentaciones (id),
    CONSTRAINT fk_movinv_bodega       FOREIGN KEY (id_bodega)       REFERENCES bodegas (id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULO: TERCEROS (clientes y proveedores unificados)
-- =============================================================================

CREATE TABLE tipos_identificacion (
    id            INT            NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(60)    NOT NULL,
    codigo        VARCHAR(20)    NOT NULL,
    created_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_tipos_ident_codigo (codigo)
) ENGINE=InnoDB;

CREATE TABLE terceros (
    id                    INT            NOT NULL AUTO_INCREMENT,
    id_tipo_identificacion INT           NOT NULL,
    numero_identificacion VARCHAR(30)    NOT NULL,
    razon_social          VARCHAR(200)   NOT NULL,
    nombre_comercial      VARCHAR(200)   NULL,
    email                 VARCHAR(100)   NULL,
    telefono              VARCHAR(30)    NULL,
    direccion_principal   VARCHAR(500)   NULL,
    estado                TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activo, 0=inactivo',
    created_at            DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at            DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at            DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_terceros_identificacion (numero_identificacion, id_tipo_identificacion),
    KEY ix_terceros_tipo_ident (id_tipo_identificacion),
    CONSTRAINT fk_terceros_tipo_ident FOREIGN KEY (id_tipo_identificacion) REFERENCES tipos_identificacion (id)
) ENGINE=InnoDB;

CREATE TABLE terceros_tipos (
    id          INT          NOT NULL AUTO_INCREMENT,
    id_tercero  INT          NOT NULL,
    tipo        VARCHAR(20)  NOT NULL COMMENT 'cliente, proveedor',
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at  DATETIME     NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_terceros_tipos (id_tercero, tipo),
    KEY ix_terceros_tipos_tercero (id_tercero),
    CONSTRAINT fk_terceros_tipos_tercero FOREIGN KEY (id_tercero) REFERENCES terceros (id)
) ENGINE=InnoDB;

CREATE TABLE contactos (
    id          INT           NOT NULL AUTO_INCREMENT,
    id_tercero  INT           NOT NULL,
    nombres     VARCHAR(100)  NOT NULL,
    apellidos   VARCHAR(100)  NULL,
    cargo       VARCHAR(100)  NULL,
    email       VARCHAR(100)  NULL,
    telefono    VARCHAR(30)   NULL,
    principal   TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1=contacto principal',
    created_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at  DATETIME      NULL,
    PRIMARY KEY (id),
    KEY ix_contactos_tercero (id_tercero),
    CONSTRAINT fk_contactos_tercero FOREIGN KEY (id_tercero) REFERENCES terceros (id)
) ENGINE=InnoDB;

CREATE TABLE direcciones (
    id               INT           NOT NULL AUTO_INCREMENT,
    id_tercero       INT           NOT NULL,
    tipo             VARCHAR(20)   NOT NULL COMMENT 'principal, envio, facturacion',
    direccion        VARCHAR(500)  NOT NULL,
    ciudad           VARCHAR(100)  NULL,
    estado_provincia VARCHAR(100)  NULL,
    pais             VARCHAR(100)  NULL DEFAULT 'Ecuador',
    codigo_postal    VARCHAR(20)   NULL,
    principal        TINYINT(1)    NOT NULL DEFAULT 0 COMMENT '1=direccion principal',
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME      NULL,
    PRIMARY KEY (id),
    KEY ix_direcciones_tercero (id_tercero),
    CONSTRAINT fk_direcciones_tercero FOREIGN KEY (id_tercero) REFERENCES terceros (id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULO: SEGURIDAD
-- =============================================================================

CREATE TABLE usuarios (
    id              INT           NOT NULL AUTO_INCREMENT,
    id_empleado     INT           NULL,
    username        VARCHAR(60)   NOT NULL,
    email           VARCHAR(100)  NOT NULL,
    password_hash   VARCHAR(255)  NOT NULL,
    nombre_completo VARCHAR(200)  NOT NULL,
    estado          VARCHAR(20)   NOT NULL DEFAULT 'activo' COMMENT 'activo, inactivo, bloqueado',
    ultimo_acceso   DATETIME      NULL,
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at      DATETIME      NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_username (username),
    UNIQUE KEY uq_usuarios_email (email),
    KEY ix_usuarios_empleado (id_empleado),
    CONSTRAINT fk_usuarios_empleado FOREIGN KEY (id_empleado) REFERENCES empleados (id)
) ENGINE=InnoDB;

CREATE TABLE roles (
    id            INT           NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(80)   NOT NULL,
    descripcion   VARCHAR(300)  NULL,
    estado        TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1=activo, 0=inactivo',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME      NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_roles_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE permisos (
    id            INT           NOT NULL AUTO_INCREMENT,
    modulo        VARCHAR(60)   NOT NULL,
    accion        VARCHAR(60)   NOT NULL,
    descripcion   VARCHAR(200)  NULL,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME      NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_permisos (modulo, accion)
) ENGINE=InnoDB;

CREATE TABLE roles_permisos (
    id            INT       NOT NULL AUTO_INCREMENT,
    id_rol        INT       NOT NULL,
    id_permiso    INT       NOT NULL,
    created_at    DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME  NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_roles_permisos (id_rol, id_permiso),
    KEY ix_roles_permisos_rol (id_rol),
    KEY ix_roles_permisos_permiso (id_permiso),
    CONSTRAINT fk_roles_permisos_rol     FOREIGN KEY (id_rol)     REFERENCES roles (id),
    CONSTRAINT fk_roles_permisos_permiso FOREIGN KEY (id_permiso) REFERENCES permisos (id)
) ENGINE=InnoDB;

CREATE TABLE usuarios_roles (
    id            INT       NOT NULL AUTO_INCREMENT,
    id_usuario    INT       NOT NULL,
    id_rol        INT       NOT NULL,
    id_sucursal   INT       NULL COMMENT 'NULL = aplica en todas las sucursales',
    created_at    DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME  NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME  NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_usuarios_roles (id_usuario, id_rol, id_sucursal),
    KEY ix_usuarios_roles_usuario (id_usuario),
    KEY ix_usuarios_roles_rol (id_rol),
    CONSTRAINT fk_usuarios_roles_usuario   FOREIGN KEY (id_usuario)  REFERENCES usuarios (id),
    CONSTRAINT fk_usuarios_roles_rol       FOREIGN KEY (id_rol)      REFERENCES roles (id),
    CONSTRAINT fk_usuarios_roles_sucursal  FOREIGN KEY (id_sucursal) REFERENCES sucursales (id)
) ENGINE=InnoDB;

CREATE TABLE parametros (
    id            INT           NOT NULL AUTO_INCREMENT,
    clave         VARCHAR(100)  NOT NULL,
    valor         TEXT          NOT NULL,
    descripcion   VARCHAR(300)  NULL,
    tipo_dato     VARCHAR(20)   NOT NULL DEFAULT 'string' COMMENT 'string, integer, decimal, boolean, json',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME      NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_parametros_clave (clave)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULO: COMPRAS
-- =============================================================================

CREATE TABLE ordenes_compra (
    id                      INT             NOT NULL AUTO_INCREMENT,
    id_sucursal             INT             NOT NULL,
    id_proveedor            INT             NOT NULL,
    id_bodega_destino       INT             NOT NULL,
    numero                  VARCHAR(30)     NOT NULL,
    fecha_emision           DATE            NOT NULL,
    fecha_entrega_esperada  DATE            NULL,
    estado                  VARCHAR(20)     NOT NULL DEFAULT 'borrador' COMMENT 'borrador, aprobada, parcial, completa, cancelada',
    subtotal                DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    descuento               DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    impuesto                DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    total                   DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    observaciones           TEXT            NULL,
    id_usuario_crea         INT             NULL,
    id_usuario_aprueba      INT             NULL,
    fecha_aprobacion        DATETIME        NULL,
    created_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at              DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at              DATETIME        NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ordenes_compra_numero (numero),
    KEY ix_oc_sucursal (id_sucursal),
    KEY ix_oc_proveedor (id_proveedor),
    KEY ix_oc_estado (estado),
    KEY ix_oc_fecha (fecha_emision),
    CONSTRAINT fk_oc_sucursal       FOREIGN KEY (id_sucursal)        REFERENCES sucursales (id),
    CONSTRAINT fk_oc_proveedor      FOREIGN KEY (id_proveedor)       REFERENCES terceros (id),
    CONSTRAINT fk_oc_bodega_destino FOREIGN KEY (id_bodega_destino)  REFERENCES bodegas (id),
    CONSTRAINT fk_oc_usuario_crea   FOREIGN KEY (id_usuario_crea)    REFERENCES usuarios (id),
    CONSTRAINT fk_oc_usuario_aprueba FOREIGN KEY (id_usuario_aprueba) REFERENCES usuarios (id)
) ENGINE=InnoDB;

CREATE TABLE ordenes_compra_detalle (
    id                INT             NOT NULL AUTO_INCREMENT,
    id_orden_compra   INT             NOT NULL,
    id_producto       INT             NOT NULL,
    id_presentacion   INT             NOT NULL,
    cantidad          DECIMAL(15,4)   NOT NULL,
    cantidad_recibida DECIMAL(15,4)   NOT NULL DEFAULT 0.0000,
    precio_unitario   DECIMAL(15,2)   NOT NULL,
    descuento         DECIMAL(15,2)   NOT NULL DEFAULT 0.00,
    subtotal          DECIMAL(15,2)   NOT NULL,
    created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at        DATETIME        NULL,
    PRIMARY KEY (id),
    KEY ix_ocd_orden (id_orden_compra),
    KEY ix_ocd_producto (id_producto),
    CONSTRAINT fk_ocd_orden       FOREIGN KEY (id_orden_compra) REFERENCES ordenes_compra (id),
    CONSTRAINT fk_ocd_producto    FOREIGN KEY (id_producto)     REFERENCES productos (id),
    CONSTRAINT fk_ocd_presentacion FOREIGN KEY (id_presentacion) REFERENCES productos_presentaciones (id)
) ENGINE=InnoDB;

CREATE TABLE recepciones (
    id               INT           NOT NULL AUTO_INCREMENT,
    id_orden_compra  INT           NOT NULL,
    id_bodega        INT           NOT NULL,
    numero           VARCHAR(30)   NOT NULL,
    fecha_recepcion  DATE          NOT NULL,
    estado           VARCHAR(20)   NOT NULL DEFAULT 'completa' COMMENT 'completa, parcial',
    observaciones    TEXT          NULL,
    id_usuario       INT           NULL,
    created_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME      NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_recepciones_numero (numero),
    KEY ix_rec_orden (id_orden_compra),
    KEY ix_rec_bodega (id_bodega),
    CONSTRAINT fk_rec_orden   FOREIGN KEY (id_orden_compra) REFERENCES ordenes_compra (id),
    CONSTRAINT fk_rec_bodega  FOREIGN KEY (id_bodega)       REFERENCES bodegas (id),
    CONSTRAINT fk_rec_usuario FOREIGN KEY (id_usuario)      REFERENCES usuarios (id)
) ENGINE=InnoDB;

CREATE TABLE recepciones_detalle (
    id                       INT            NOT NULL AUTO_INCREMENT,
    id_recepcion             INT            NOT NULL,
    id_orden_compra_detalle  INT            NOT NULL,
    id_producto              INT            NOT NULL,
    id_presentacion          INT            NOT NULL,
    cantidad_esperada        DECIMAL(15,4)  NOT NULL,
    cantidad_recibida        DECIMAL(15,4)  NOT NULL,
    costo_unitario           DECIMAL(15,2)  NULL,
    observaciones            VARCHAR(500)   NULL,
    created_at               DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at               DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at               DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_recd_recepcion (id_recepcion),
    KEY ix_recd_ocd (id_orden_compra_detalle),
    CONSTRAINT fk_recd_recepcion  FOREIGN KEY (id_recepcion)            REFERENCES recepciones (id),
    CONSTRAINT fk_recd_ocd        FOREIGN KEY (id_orden_compra_detalle) REFERENCES ordenes_compra_detalle (id),
    CONSTRAINT fk_recd_producto    FOREIGN KEY (id_producto)             REFERENCES productos (id),
    CONSTRAINT fk_recd_presentacion FOREIGN KEY (id_presentacion)        REFERENCES productos_presentaciones (id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULO: VENTAS
-- =============================================================================

CREATE TABLE listas_precios (
    id            INT           NOT NULL AUTO_INCREMENT,
    nombre        VARCHAR(100)  NOT NULL,
    descripcion   VARCHAR(300)  NULL,
    moneda        CHAR(3)       NOT NULL DEFAULT 'USD',
    fecha_desde   DATE          NULL,
    fecha_hasta   DATE          NULL,
    estado        TINYINT(1)    NOT NULL DEFAULT 1 COMMENT '1=activa, 0=inactiva',
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at    DATETIME      NULL,
    PRIMARY KEY (id)
) ENGINE=InnoDB;

CREATE TABLE listas_precios_detalle (
    id               INT            NOT NULL AUTO_INCREMENT,
    id_lista_precios INT            NOT NULL,
    id_producto      INT            NOT NULL,
    id_presentacion  INT            NOT NULL,
    precio           DECIMAL(15,2)  NOT NULL,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_lpd (id_lista_precios, id_producto, id_presentacion),
    KEY ix_lpd_lista (id_lista_precios),
    KEY ix_lpd_producto (id_producto),
    CONSTRAINT fk_lpd_lista        FOREIGN KEY (id_lista_precios) REFERENCES listas_precios (id),
    CONSTRAINT fk_lpd_producto     FOREIGN KEY (id_producto)      REFERENCES productos (id),
    CONSTRAINT fk_lpd_presentacion FOREIGN KEY (id_presentacion)  REFERENCES productos_presentaciones (id)
) ENGINE=InnoDB;

CREATE TABLE pedidos (
    id                     INT            NOT NULL AUTO_INCREMENT,
    id_sucursal            INT            NOT NULL,
    id_cliente             INT            NOT NULL,
    id_vendedor            INT            NULL,
    id_lista_precios       INT            NULL,
    numero                 VARCHAR(30)    NOT NULL,
    fecha_pedido           DATE           NOT NULL,
    fecha_entrega_esperada DATE           NULL,
    estado                 VARCHAR(20)    NOT NULL DEFAULT 'borrador' COMMENT 'borrador, confirmado, procesando, despachado, entregado, cancelado',
    subtotal               DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    descuento              DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    impuesto               DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    total                  DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    observaciones          TEXT           NULL,
    created_at             DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at             DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at             DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pedidos_numero (numero),
    KEY ix_ped_sucursal (id_sucursal),
    KEY ix_ped_cliente (id_cliente),
    KEY ix_ped_vendedor (id_vendedor),
    KEY ix_ped_estado (estado),
    KEY ix_ped_fecha (fecha_pedido),
    CONSTRAINT fk_ped_sucursal      FOREIGN KEY (id_sucursal)      REFERENCES sucursales (id),
    CONSTRAINT fk_ped_cliente       FOREIGN KEY (id_cliente)       REFERENCES terceros (id),
    CONSTRAINT fk_ped_vendedor      FOREIGN KEY (id_vendedor)      REFERENCES empleados (id),
    CONSTRAINT fk_ped_lista_precios FOREIGN KEY (id_lista_precios) REFERENCES listas_precios (id)
) ENGINE=InnoDB;

CREATE TABLE pedidos_detalle (
    id                 INT            NOT NULL AUTO_INCREMENT,
    id_pedido          INT            NOT NULL,
    id_producto        INT            NOT NULL,
    id_presentacion    INT            NOT NULL,
    cantidad           DECIMAL(15,4)  NOT NULL,
    cantidad_despachada DECIMAL(15,4) NOT NULL DEFAULT 0.0000,
    precio_unitario    DECIMAL(15,2)  NOT NULL,
    descuento          DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    subtotal           DECIMAL(15,2)  NOT NULL,
    created_at         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at         DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at         DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_pedd_pedido (id_pedido),
    KEY ix_pedd_producto (id_producto),
    CONSTRAINT fk_pedd_pedido       FOREIGN KEY (id_pedido)       REFERENCES pedidos (id),
    CONSTRAINT fk_pedd_producto     FOREIGN KEY (id_producto)     REFERENCES productos (id),
    CONSTRAINT fk_pedd_presentacion FOREIGN KEY (id_presentacion) REFERENCES productos_presentaciones (id)
) ENGINE=InnoDB;

CREATE TABLE facturas (
    id               INT            NOT NULL AUTO_INCREMENT,
    id_sucursal      INT            NOT NULL,
    id_cliente       INT            NOT NULL,
    id_pedido        INT            NULL,
    id_vendedor      INT            NULL,
    numero           VARCHAR(30)    NOT NULL,
    fecha_emision    DATE           NOT NULL,
    fecha_vencimiento DATE          NULL,
    estado           VARCHAR(20)    NOT NULL DEFAULT 'activa' COMMENT 'activa, pagada, anulada, vencida',
    subtotal         DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    descuento        DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    impuesto         DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    total            DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    saldo            DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    observaciones    TEXT           NULL,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_facturas_numero (numero),
    KEY ix_fac_sucursal (id_sucursal),
    KEY ix_fac_cliente (id_cliente),
    KEY ix_fac_estado (estado),
    KEY ix_fac_fecha (fecha_emision),
    KEY ix_fac_vencimiento (fecha_vencimiento),
    CONSTRAINT fk_fac_sucursal FOREIGN KEY (id_sucursal) REFERENCES sucursales (id),
    CONSTRAINT fk_fac_cliente  FOREIGN KEY (id_cliente)  REFERENCES terceros (id),
    CONSTRAINT fk_fac_pedido   FOREIGN KEY (id_pedido)   REFERENCES pedidos (id),
    CONSTRAINT fk_fac_vendedor FOREIGN KEY (id_vendedor) REFERENCES empleados (id)
) ENGINE=InnoDB;

CREATE TABLE facturas_detalle (
    id               INT            NOT NULL AUTO_INCREMENT,
    id_factura       INT            NOT NULL,
    id_producto      INT            NOT NULL,
    id_presentacion  INT            NOT NULL,
    id_bodega        INT            NOT NULL,
    cantidad         DECIMAL(15,4)  NOT NULL,
    precio_unitario  DECIMAL(15,2)  NOT NULL,
    descuento        DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    subtotal         DECIMAL(15,2)  NOT NULL,
    costo_unitario   DECIMAL(15,2)  NULL COMMENT 'costo al momento de la venta para margen',
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_facd_factura (id_factura),
    KEY ix_facd_producto (id_producto),
    KEY ix_facd_bodega (id_bodega),
    CONSTRAINT fk_facd_factura      FOREIGN KEY (id_factura)      REFERENCES facturas (id),
    CONSTRAINT fk_facd_producto     FOREIGN KEY (id_producto)     REFERENCES productos (id),
    CONSTRAINT fk_facd_presentacion FOREIGN KEY (id_presentacion) REFERENCES productos_presentaciones (id),
    CONSTRAINT fk_facd_bodega       FOREIGN KEY (id_bodega)       REFERENCES bodegas (id)
) ENGINE=InnoDB;

CREATE TABLE notas_credito (
    id              INT            NOT NULL AUTO_INCREMENT,
    id_factura      INT            NOT NULL,
    id_cliente      INT            NOT NULL,
    numero          VARCHAR(30)    NOT NULL,
    fecha_emision   DATE           NOT NULL,
    motivo          VARCHAR(300)   NOT NULL,
    estado          VARCHAR(20)    NOT NULL DEFAULT 'activa' COMMENT 'activa, aplicada, anulada',
    subtotal        DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    impuesto        DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    total           DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    observaciones   TEXT           NULL,
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at      DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_notas_credito_numero (numero),
    KEY ix_nc_factura (id_factura),
    KEY ix_nc_cliente (id_cliente),
    CONSTRAINT fk_nc_factura FOREIGN KEY (id_factura) REFERENCES facturas (id),
    CONSTRAINT fk_nc_cliente FOREIGN KEY (id_cliente) REFERENCES terceros (id)
) ENGINE=InnoDB;

CREATE TABLE notas_credito_detalle (
    id               INT            NOT NULL AUTO_INCREMENT,
    id_nota_credito  INT            NOT NULL,
    id_producto      INT            NOT NULL,
    id_presentacion  INT            NOT NULL,
    cantidad         DECIMAL(15,4)  NOT NULL,
    precio_unitario  DECIMAL(15,2)  NOT NULL,
    subtotal         DECIMAL(15,2)  NOT NULL,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_ncd_nota (id_nota_credito),
    CONSTRAINT fk_ncd_nota         FOREIGN KEY (id_nota_credito) REFERENCES notas_credito (id),
    CONSTRAINT fk_ncd_producto     FOREIGN KEY (id_producto)     REFERENCES productos (id),
    CONSTRAINT fk_ncd_presentacion FOREIGN KEY (id_presentacion) REFERENCES productos_presentaciones (id)
) ENGINE=InnoDB;

-- =============================================================================
-- MODULO: TESORERIA
-- =============================================================================

CREATE TABLE formas_pago (
    id                   INT          NOT NULL AUTO_INCREMENT,
    nombre               VARCHAR(80)  NOT NULL,
    tipo                 VARCHAR(20)  NOT NULL COMMENT 'efectivo, tarjeta, transferencia, credito, cheque',
    requiere_referencia  TINYINT(1)   NOT NULL DEFAULT 0 COMMENT '1=si, 0=no',
    estado               TINYINT(1)   NOT NULL DEFAULT 1 COMMENT '1=activa, 0=inactiva',
    created_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at           DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at           DATETIME     NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_formas_pago_nombre (nombre)
) ENGINE=InnoDB;

CREATE TABLE cuentas_bancarias (
    id              INT            NOT NULL AUTO_INCREMENT,
    id_empresa      INT            NOT NULL,
    banco           VARCHAR(100)   NOT NULL,
    numero_cuenta   VARCHAR(30)    NOT NULL,
    tipo_cuenta     VARCHAR(20)    NOT NULL COMMENT 'corriente, ahorro',
    moneda          CHAR(3)        NOT NULL DEFAULT 'USD',
    saldo_actual    DECIMAL(15,2)  NOT NULL DEFAULT 0.00,
    estado          TINYINT(1)     NOT NULL DEFAULT 1 COMMENT '1=activa, 0=inactiva',
    created_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at      DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at      DATETIME       NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_cuentas_numero (numero_cuenta),
    KEY ix_cuentas_empresa (id_empresa),
    CONSTRAINT fk_cuentas_empresa FOREIGN KEY (id_empresa) REFERENCES empresas (id)
) ENGINE=InnoDB;

CREATE TABLE pagos_clientes (
    id                  INT            NOT NULL AUTO_INCREMENT,
    id_factura          INT            NOT NULL,
    id_cliente          INT            NOT NULL,
    id_forma_pago       INT            NOT NULL,
    id_cuenta_bancaria  INT            NULL,
    numero_referencia   VARCHAR(80)    NULL,
    fecha_pago          DATE           NOT NULL,
    monto               DECIMAL(15,2)  NOT NULL,
    observaciones       VARCHAR(500)   NULL,
    id_usuario          INT            NULL,
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_pagc_factura (id_factura),
    KEY ix_pagc_cliente (id_cliente),
    KEY ix_pagc_fecha (fecha_pago),
    CONSTRAINT fk_pagc_factura  FOREIGN KEY (id_factura)         REFERENCES facturas (id),
    CONSTRAINT fk_pagc_cliente  FOREIGN KEY (id_cliente)         REFERENCES terceros (id),
    CONSTRAINT fk_pagc_forma    FOREIGN KEY (id_forma_pago)      REFERENCES formas_pago (id),
    CONSTRAINT fk_pagc_cuenta   FOREIGN KEY (id_cuenta_bancaria) REFERENCES cuentas_bancarias (id),
    CONSTRAINT fk_pagc_usuario  FOREIGN KEY (id_usuario)         REFERENCES usuarios (id)
) ENGINE=InnoDB;

CREATE TABLE pagos_proveedores (
    id                  INT            NOT NULL AUTO_INCREMENT,
    id_orden_compra     INT            NOT NULL,
    id_proveedor        INT            NOT NULL,
    id_forma_pago       INT            NOT NULL,
    id_cuenta_bancaria  INT            NULL,
    numero_referencia   VARCHAR(80)    NULL,
    fecha_pago          DATE           NOT NULL,
    monto               DECIMAL(15,2)  NOT NULL,
    observaciones       VARCHAR(500)   NULL,
    id_usuario          INT            NULL,
    created_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at          DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at          DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_pagp_orden (id_orden_compra),
    KEY ix_pagp_proveedor (id_proveedor),
    KEY ix_pagp_fecha (fecha_pago),
    CONSTRAINT fk_pagp_orden     FOREIGN KEY (id_orden_compra)    REFERENCES ordenes_compra (id),
    CONSTRAINT fk_pagp_proveedor FOREIGN KEY (id_proveedor)       REFERENCES terceros (id),
    CONSTRAINT fk_pagp_forma     FOREIGN KEY (id_forma_pago)      REFERENCES formas_pago (id),
    CONSTRAINT fk_pagp_cuenta    FOREIGN KEY (id_cuenta_bancaria) REFERENCES cuentas_bancarias (id),
    CONSTRAINT fk_pagp_usuario   FOREIGN KEY (id_usuario)         REFERENCES usuarios (id)
) ENGINE=InnoDB;

CREATE TABLE caja (
    id               INT            NOT NULL AUTO_INCREMENT,
    id_sucursal      INT            NOT NULL,
    id_usuario       INT            NOT NULL,
    tipo_movimiento  VARCHAR(20)    NOT NULL COMMENT 'apertura, ingreso, egreso, cierre',
    monto            DECIMAL(15,2)  NOT NULL,
    saldo_anterior   DECIMAL(15,2)  NOT NULL,
    saldo_posterior  DECIMAL(15,2)  NOT NULL,
    concepto         VARCHAR(300)   NOT NULL,
    id_referencia    INT            NULL,
    tipo_referencia  VARCHAR(50)    NULL COMMENT 'pago_cliente, pago_proveedor, gasto',
    fecha_movimiento DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at       DATETIME       NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    deleted_at       DATETIME       NULL,
    PRIMARY KEY (id),
    KEY ix_caja_sucursal (id_sucursal),
    KEY ix_caja_usuario (id_usuario),
    KEY ix_caja_fecha (fecha_movimiento),
    CONSTRAINT fk_caja_sucursal FOREIGN KEY (id_sucursal) REFERENCES sucursales (id),
    CONSTRAINT fk_caja_usuario  FOREIGN KEY (id_usuario)  REFERENCES usuarios (id)
) ENGINE=InnoDB;
