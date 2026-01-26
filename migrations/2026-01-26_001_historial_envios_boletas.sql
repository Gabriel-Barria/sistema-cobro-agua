-- Migracion: Crear tabla historial de envios de boletas
-- Fecha: 2026-01-26
-- Descripcion: Registra el historial de envios de boletas por WhatsApp, email, etc.

-- Crear tabla de envios
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

-- Indices para consultas eficientes
CREATE INDEX IF NOT EXISTS idx_envios_boleta ON envios_boletas(boleta_id);
CREATE INDEX IF NOT EXISTS idx_envios_usuario ON envios_boletas(usuario_id);
CREATE INDEX IF NOT EXISTS idx_envios_fecha ON envios_boletas(created_at);
CREATE INDEX IF NOT EXISTS idx_envios_canal ON envios_boletas(canal);

-- Comentarios
COMMENT ON TABLE envios_boletas IS 'Historial de envios de boletas por diferentes canales';
COMMENT ON COLUMN envios_boletas.canal IS 'Canal de envio: whatsapp, email, etc.';
COMMENT ON COLUMN envios_boletas.estado IS 'Estado del envio: enviado, fallido';
COMMENT ON COLUMN envios_boletas.destinatario IS 'Telefono o email del destinatario';
