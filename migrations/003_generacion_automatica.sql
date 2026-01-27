-- Migracion: Sistema de generacion automatica de boletas
-- Fecha: 2026-01-27

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
    periodo_año INTEGER,
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

-- Insertar configuracion cron por defecto (desactivado)
INSERT INTO configuracion_cron (nombre, tipo_programacion, dia_mes, hora_ejecucion, activo) VALUES
('generacion_boletas', 'dia_mes', 5, '08:00:00', false)
ON CONFLICT (nombre) DO NOTHING;
