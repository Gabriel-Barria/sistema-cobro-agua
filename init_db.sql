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
    recibe_boleta_whatsapp BOOLEAN DEFAULT FALSE,
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
    anio INTEGER NOT NULL,
    mes INTEGER NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (medidor_id) REFERENCES medidores(id),
    CONSTRAINT uq_lectura_medidor_periodo UNIQUE (medidor_id, anio, mes)
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
    periodo_anio INTEGER NOT NULL,
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
    saldo_pendiente NUMERIC(10,2),
    monto_pagado NUMERIC(10,2) DEFAULT 0,
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
CREATE INDEX IF NOT EXISTS idx_lecturas_anio_mes ON lecturas(anio, mes);
CREATE INDEX IF NOT EXISTS idx_boletas_lectura ON boletas(lectura_id);
CREATE INDEX IF NOT EXISTS idx_boletas_medidor ON boletas(medidor_id);
CREATE INDEX IF NOT EXISTS idx_boletas_pagada ON boletas(pagada);
CREATE INDEX IF NOT EXISTS idx_boletas_periodo ON boletas(periodo_anio, periodo_mes);
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

-- Configuracion global del sistema
CREATE TABLE IF NOT EXISTS configuracion_sistema (
    id SERIAL PRIMARY KEY,
    clave VARCHAR(100) UNIQUE NOT NULL,
    valor TEXT NOT NULL,
    descripcion TEXT,
    tipo VARCHAR(20) DEFAULT 'string',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Configuracion cron para generacion automatica
CREATE TABLE IF NOT EXISTS configuracion_cron (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) UNIQUE NOT NULL,
    tipo_programacion VARCHAR(20) NOT NULL CHECK (tipo_programacion IN ('dia_mes', 'intervalo_dias', 'manual')),
    dia_mes INTEGER CHECK (dia_mes >= 1 AND dia_mes <= 28),
    intervalo_dias INTEGER CHECK (intervalo_dias >= 1),
    hora_ejecucion TIME NOT NULL DEFAULT '08:00:00',
    activo BOOLEAN DEFAULT TRUE,
    ultima_ejecucion TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Logs de generacion de boletas
CREATE TABLE IF NOT EXISTS log_generacion_boletas (
    id SERIAL PRIMARY KEY,
    fecha_ejecucion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    periodo_anio INTEGER,
    periodo_mes INTEGER,
    lecturas_creadas INTEGER DEFAULT 0,
    boletas_generadas INTEGER DEFAULT 0,
    errores INTEGER DEFAULT 0,
    estado VARCHAR(20) CHECK (estado IN ('iniciado', 'completado', 'error')),
    mensaje TEXT,
    detalles JSONB,
    duracion_segundos NUMERIC(10,2),
    iniciado_por INTEGER REFERENCES usuarios(id),
    es_automatico BOOLEAN DEFAULT TRUE
);

-- Indices para nuevas tablas
CREATE INDEX IF NOT EXISTS idx_config_sistema_clave ON configuracion_sistema(clave);
CREATE INDEX IF NOT EXISTS idx_config_cron_nombre ON configuracion_cron(nombre);
CREATE INDEX IF NOT EXISTS idx_log_generacion_fecha ON log_generacion_boletas(fecha_ejecucion);
CREATE INDEX IF NOT EXISTS idx_log_generacion_estado ON log_generacion_boletas(estado);

-- Insertar configuracion inicial del sistema
INSERT INTO configuracion_sistema (clave, valor, descripcion, tipo) VALUES
('frecuencia_facturacion', 'mensual', 'Frecuencia de facturacion: mensual, bimestral, trimestral', 'string'),
('dia_corte_periodo', '1', 'Dia del mes que define cambio de periodo (1-28)', 'int'),
('regla_periodo', 'mes_anterior', 'Regla: mes_lectura (periodo=mes de lectura), mes_anterior (periodo=mes anterior a lectura)', 'string'),
('dia_toma_lectura', '5', 'Dia habitual de toma de lecturas (1-28)', 'int'),
('crear_lecturas_faltantes', 'true', 'Crear lecturas automaticas para medidores sin lectura', 'boolean'),
('valor_lectura_faltante', 'ultima', 'Valor para lecturas faltantes: ultima (copia ultima lectura), cero (valor 0)', 'string')
ON CONFLICT (clave) DO NOTHING;

-- Insertar datos bancarios iniciales
INSERT INTO configuracion_sistema (clave, valor, descripcion, tipo) VALUES
('banco_nombre', 'Banco Estado', 'Nombre del banco', 'string'),
('banco_cuenta', '82970400962', 'Numero de cuenta', 'string'),
('banco_rut', '65096733-k', 'RUT del titular', 'string'),
('banco_tipo_cuenta', 'Cuenta Vista o Chequera electronica', 'Tipo de cuenta', 'string'),
('banco_titular', 'Comite de Trabajo Pasaje Bauche', 'Nombre del titular', 'string'),
('banco_email', 'comite.bauche@gmail.com', 'Email de contacto', 'string')
ON CONFLICT (clave) DO NOTHING;

-- Insertar configuracion cron por defecto
INSERT INTO configuracion_cron (nombre, tipo_programacion, dia_mes, hora_ejecucion, activo) VALUES
('generacion_boletas', 'dia_mes', 5, '08:00:00', false)
ON CONFLICT (nombre) DO NOTHING;

-- Logs de envio masivo de boletas por WhatsApp
CREATE TABLE IF NOT EXISTS log_envio_masivo (
    id SERIAL PRIMARY KEY,
    fecha_ejecucion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    periodo_anio INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    total_boletas INTEGER DEFAULT 0,
    total_enviables INTEGER DEFAULT 0,
    enviadas_exitosas INTEGER DEFAULT 0,
    enviadas_fallidas INTEGER DEFAULT 0,
    omitidas_sin_telefono INTEGER DEFAULT 0,
    omitidas_no_recibe_wa INTEGER DEFAULT 0,
    omitidas_ya_enviadas INTEGER DEFAULT 0,
    estado VARCHAR(20) CHECK (estado IN ('iniciado', 'completado', 'error', 'interrumpido')),
    mensaje TEXT,
    detalles JSONB,
    duracion_segundos NUMERIC(10,2),
    iniciado_por INTEGER REFERENCES usuarios(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_log_envio_masivo_fecha ON log_envio_masivo(fecha_ejecucion);
CREATE INDEX IF NOT EXISTS idx_log_envio_masivo_periodo ON log_envio_masivo(periodo_anio, periodo_mes);
