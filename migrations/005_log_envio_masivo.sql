-- Migracion: Tabla para logs de envio masivo de boletas por WhatsApp
-- Fecha: 2026-01-28

CREATE TABLE IF NOT EXISTS log_envio_masivo (
    id SERIAL PRIMARY KEY,
    fecha_ejecucion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    periodo_año INTEGER NOT NULL,
    periodo_mes INTEGER NOT NULL,
    total_boletas INTEGER DEFAULT 0,
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
CREATE INDEX IF NOT EXISTS idx_log_envio_masivo_periodo ON log_envio_masivo(periodo_año, periodo_mes);
