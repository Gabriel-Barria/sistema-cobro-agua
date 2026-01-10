-- Crear tablas en PostgreSQL
-- Adaptado de database.py con sintaxis PostgreSQL

CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    nombre_completo TEXT,
    rut TEXT,
    activo SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS medidores (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    numero_medidor TEXT,
    direccion TEXT,
    activo SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_inicio DATE DEFAULT NULL,
    fecha_baja DATE DEFAULT NULL,
    motivo_baja TEXT DEFAULT NULL,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

CREATE TABLE IF NOT EXISTS lecturas (
    id SERIAL PRIMARY KEY,
    medidor_id INTEGER NOT NULL,
    lectura_m3 INTEGER NOT NULL,
    fecha_lectura DATE NOT NULL,
    foto_path TEXT NOT NULL,
    foto_nombre TEXT NOT NULL,
    año INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (medidor_id) REFERENCES medidores(id)
);

CREATE TABLE IF NOT EXISTS configuracion_boletas (
    id SERIAL PRIMARY KEY,
    cargo_fijo NUMERIC(10,2) NOT NULL DEFAULT 0,
    precio_m3 NUMERIC(10,2) NOT NULL DEFAULT 0,
    activo SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS boletas (
    id SERIAL PRIMARY KEY,
    numero_boleta TEXT UNIQUE NOT NULL,
    lectura_id INTEGER NOT NULL,
    cliente_nombre TEXT NOT NULL,
    medidor_id INTEGER NOT NULL,
    periodo_año INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    lectura_actual INTEGER NOT NULL,
    lectura_anterior INTEGER,
    consumo_m3 INTEGER NOT NULL,
    cargo_fijo NUMERIC(10,2) NOT NULL,
    precio_m3 NUMERIC(10,2) NOT NULL,
    subtotal_consumo NUMERIC(10,2) NOT NULL,
    total NUMERIC(10,2) NOT NULL,
    fecha_emision DATE NOT NULL,
    pagada SMALLINT DEFAULT 0,
    fecha_pago DATE,
    metodo_pago TEXT,
    comprobante_path TEXT,
    estado_anterior INTEGER DEFAULT NULL,
    fecha_envio_revision DATE DEFAULT NULL,
    fecha_aprobacion DATE DEFAULT NULL,
    fecha_rechazo DATE DEFAULT NULL,
    motivo_rechazo TEXT DEFAULT NULL,
    comprobante_anterior TEXT DEFAULT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lectura_id) REFERENCES lecturas(id)
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre);
CREATE INDEX IF NOT EXISTS idx_medidores_cliente ON medidores(cliente_id);
CREATE INDEX IF NOT EXISTS idx_lecturas_medidor ON lecturas(medidor_id);
CREATE INDEX IF NOT EXISTS idx_lecturas_fecha ON lecturas(fecha_lectura);
CREATE INDEX IF NOT EXISTS idx_lecturas_año_mes ON lecturas(año, mes);
CREATE INDEX IF NOT EXISTS idx_boletas_lectura ON boletas(lectura_id);
CREATE INDEX IF NOT EXISTS idx_boletas_medidor ON boletas(medidor_id);
CREATE INDEX IF NOT EXISTS idx_boletas_pagada ON boletas(pagada);
CREATE INDEX IF NOT EXISTS idx_boletas_periodo ON boletas(periodo_año, periodo_mes);
