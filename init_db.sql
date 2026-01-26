-- Crear tablas en PostgreSQL
-- Adaptado de database.py con sintaxis PostgreSQL

CREATE TABLE IF NOT EXISTS clientes (
    id SERIAL PRIMARY KEY,
    nombre TEXT NOT NULL UNIQUE,
    nombre_completo TEXT,
    rut TEXT,
    telefono VARCHAR(20),
    email VARCHAR(100),
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
    FOREIGN KEY (medidor_id) REFERENCES medidores(id),
    CONSTRAINT uq_lectura_medidor_periodo UNIQUE (medidor_id, año, mes)
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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (lectura_id) REFERENCES lecturas(id)
);

-- Tabla de usuarios del sistema (staff)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrador', 'registrador')),
    activo SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de pagos
CREATE TABLE IF NOT EXISTS pagos (
    id SERIAL PRIMARY KEY,
    numero_pago VARCHAR(20) UNIQUE NOT NULL,
    cliente_id INTEGER NOT NULL,
    monto_total NUMERIC(10,2) NOT NULL,
    monto_aplicado NUMERIC(10,2) DEFAULT 0,
    monto_a_favor NUMERIC(10,2) DEFAULT 0,
    estado VARCHAR(20) NOT NULL DEFAULT 'pendiente',
    comprobante_path TEXT,
    metodo_pago VARCHAR(50),
    fecha_pago DATE,
    fecha_envio DATE NOT NULL,
    fecha_procesamiento DATE,
    procesado_por INTEGER,
    motivo_rechazo TEXT,
    notas TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (procesado_por) REFERENCES usuarios(id)
);

-- Relacion pagos-boletas (muchos a muchos)
CREATE TABLE IF NOT EXISTS pago_boletas (
    id SERIAL PRIMARY KEY,
    pago_id INTEGER NOT NULL,
    boleta_id INTEGER NOT NULL,
    monto_aplicado NUMERIC(10,2) NOT NULL,
    es_pago_completo BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (pago_id) REFERENCES pagos(id) ON DELETE CASCADE,
    FOREIGN KEY (boleta_id) REFERENCES boletas(id),
    UNIQUE(pago_id, boleta_id)
);

-- Saldos a favor de clientes
CREATE TABLE IF NOT EXISTS saldos_cliente (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER UNIQUE NOT NULL,
    saldo_disponible NUMERIC(10,2) NOT NULL DEFAULT 0,
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Historial de movimientos de saldo
CREATE TABLE IF NOT EXISTS movimientos_saldo (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER NOT NULL,
    tipo VARCHAR(20) NOT NULL,
    origen VARCHAR(50) NOT NULL,
    pago_id INTEGER,
    boleta_id INTEGER,
    monto NUMERIC(10,2) NOT NULL,
    saldo_anterior NUMERIC(10,2) NOT NULL,
    saldo_nuevo NUMERIC(10,2) NOT NULL,
    descripcion TEXT,
    usuario_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id),
    FOREIGN KEY (pago_id) REFERENCES pagos(id) ON DELETE SET NULL,
    FOREIGN KEY (boleta_id) REFERENCES boletas(id) ON DELETE SET NULL,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id)
);

-- Historial de envios de boletas
CREATE TABLE IF NOT EXISTS envios_boletas (
    id SERIAL PRIMARY KEY,
    boleta_id INTEGER NOT NULL,
    usuario_id INTEGER,
    canal VARCHAR(20) NOT NULL,
    destinatario VARCHAR(100) NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'enviado',
    mensaje_error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boleta_id) REFERENCES boletas(id) ON DELETE CASCADE,
    FOREIGN KEY (usuario_id) REFERENCES usuarios(id) ON DELETE SET NULL
);

-- Índices
CREATE INDEX IF NOT EXISTS idx_envios_boleta ON envios_boletas(boleta_id);
CREATE INDEX IF NOT EXISTS idx_envios_usuario ON envios_boletas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_envios_fecha ON envios_boletas(created_at);
CREATE INDEX IF NOT EXISTS idx_clientes_nombre ON clientes(nombre);
CREATE INDEX IF NOT EXISTS idx_medidores_cliente ON medidores(cliente_id);
CREATE INDEX IF NOT EXISTS idx_lecturas_medidor ON lecturas(medidor_id);
CREATE INDEX IF NOT EXISTS idx_lecturas_fecha ON lecturas(fecha_lectura);
CREATE INDEX IF NOT EXISTS idx_lecturas_año_mes ON lecturas(año, mes);
CREATE INDEX IF NOT EXISTS idx_boletas_lectura ON boletas(lectura_id);
CREATE INDEX IF NOT EXISTS idx_boletas_medidor ON boletas(medidor_id);
CREATE INDEX IF NOT EXISTS idx_boletas_pagada ON boletas(pagada);
CREATE INDEX IF NOT EXISTS idx_boletas_periodo ON boletas(periodo_año, periodo_mes);
CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);
CREATE INDEX IF NOT EXISTS idx_pagos_cliente ON pagos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_envio ON pagos(fecha_envio);
CREATE INDEX IF NOT EXISTS idx_pago_boletas_pago ON pago_boletas(pago_id);
CREATE INDEX IF NOT EXISTS idx_pago_boletas_boleta ON pago_boletas(boleta_id);
CREATE INDEX IF NOT EXISTS idx_saldos_cliente ON saldos_cliente(cliente_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_cliente ON movimientos_saldo(cliente_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos_saldo(tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos_saldo(created_at);
