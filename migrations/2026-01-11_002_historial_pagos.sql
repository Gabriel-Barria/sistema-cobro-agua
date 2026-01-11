-- ============================================================
-- Migracion: Historial de intentos de pago
-- Fecha: 2026-01-11
-- Commit: feat: Agregar historial de intentos de pago
-- Autor: Claude Code
-- ============================================================
--
-- DESCRIPCION:
-- 1. Crea tabla historial_pagos para registrar todos los intentos
-- 2. Elimina campos obsoletos de la tabla boletas
--
-- ESTADOS EN HISTORIAL:
--   - en_revision: Comprobante enviado, pendiente de revision
--   - aprobado: Pago aceptado por el administrador
--   - rechazado: Pago rechazado con motivo
--
-- NOTA: Esta migracion elimina los campos antiguos de historial
-- que solo guardaban el ultimo intento. Ahora todo se guarda
-- en la tabla historial_pagos.
-- ============================================================

-- 1. Crear tabla de historial de intentos de pago
CREATE TABLE IF NOT EXISTS historial_pagos (
    id SERIAL PRIMARY KEY,
    boleta_id INTEGER NOT NULL,
    comprobante_path TEXT NOT NULL,
    fecha_envio DATE NOT NULL,
    estado VARCHAR(20) NOT NULL DEFAULT 'en_revision',
    fecha_procesamiento DATE,
    motivo_rechazo TEXT,
    metodo_pago TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (boleta_id) REFERENCES boletas(id) ON DELETE CASCADE
);

-- Indice para busqueda rapida por boleta
CREATE INDEX IF NOT EXISTS idx_historial_boleta ON historial_pagos(boleta_id);

-- ============================================================
-- 2. Eliminar campos obsoletos de la tabla boletas
-- ============================================================
-- Estos campos ya no se usan porque el historial completo
-- ahora vive en la tabla historial_pagos
-- ============================================================

ALTER TABLE boletas DROP COLUMN IF EXISTS estado_anterior;
ALTER TABLE boletas DROP COLUMN IF EXISTS fecha_envio_revision;
ALTER TABLE boletas DROP COLUMN IF EXISTS fecha_aprobacion;
ALTER TABLE boletas DROP COLUMN IF EXISTS fecha_rechazo;
ALTER TABLE boletas DROP COLUMN IF EXISTS motivo_rechazo;
ALTER TABLE boletas DROP COLUMN IF EXISTS comprobante_anterior;
