-- ============================================================
-- Migración: Sistema de Pagos Mejorado
-- Fecha: 2026-01-22
-- Descripción: Crear tablas para nuevo sistema de pagos con
--              soporte para pagos parciales y saldos a favor
-- ============================================================

-- 1. Crear tabla de pagos (reemplaza historial_pagos)
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

-- Índices para pagos
CREATE INDEX IF NOT EXISTS idx_pagos_cliente ON pagos(cliente_id);
CREATE INDEX IF NOT EXISTS idx_pagos_estado ON pagos(estado);
CREATE INDEX IF NOT EXISTS idx_pagos_fecha_envio ON pagos(fecha_envio);

-- 2. Crear tabla de relación pago-boletas
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

-- Índices para pago_boletas
CREATE INDEX IF NOT EXISTS idx_pago_boletas_pago ON pago_boletas(pago_id);
CREATE INDEX IF NOT EXISTS idx_pago_boletas_boleta ON pago_boletas(boleta_id);

-- 3. Crear tabla de saldos de cliente
CREATE TABLE IF NOT EXISTS saldos_cliente (
    id SERIAL PRIMARY KEY,
    cliente_id INTEGER UNIQUE NOT NULL,
    saldo_disponible NUMERIC(10,2) NOT NULL DEFAULT 0,
    ultima_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (cliente_id) REFERENCES clientes(id)
);

-- Índice para saldos
CREATE INDEX IF NOT EXISTS idx_saldos_cliente ON saldos_cliente(cliente_id);

-- 4. Crear tabla de movimientos de saldo (auditoría)
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

-- Índices para movimientos
CREATE INDEX IF NOT EXISTS idx_movimientos_cliente ON movimientos_saldo(cliente_id);
CREATE INDEX IF NOT EXISTS idx_movimientos_tipo ON movimientos_saldo(tipo);
CREATE INDEX IF NOT EXISTS idx_movimientos_fecha ON movimientos_saldo(created_at);

-- 5. Agregar campos a tabla boletas
ALTER TABLE boletas ADD COLUMN IF NOT EXISTS monto_pagado NUMERIC(10,2) DEFAULT 0;
ALTER TABLE boletas ADD COLUMN IF NOT EXISTS saldo_pendiente NUMERIC(10,2);

-- 6. Inicializar campos en boletas existentes
UPDATE boletas SET
    saldo_pendiente = CASE WHEN pagada = 2 THEN 0 ELSE total END,
    monto_pagado = CASE WHEN pagada = 2 THEN total ELSE 0 END
WHERE saldo_pendiente IS NULL;

-- 7. Migrar boletas ya pagadas a tabla pagos
INSERT INTO pagos (numero_pago, cliente_id, monto_total, monto_aplicado,
                   estado, metodo_pago, fecha_pago, fecha_envio,
                   comprobante_path, notas)
SELECT
    'MIG-' || b.id,
    m.cliente_id,
    b.total,
    b.total,
    'aprobado',
    COALESCE(b.metodo_pago, 'migrado'),
    COALESCE(b.fecha_pago, b.fecha_emision),
    COALESCE(b.fecha_pago, b.fecha_emision),
    b.comprobante_path,
    'Migrado del sistema anterior'
FROM boletas b
JOIN medidores m ON b.medidor_id = m.id
WHERE b.pagada = 2
AND NOT EXISTS (
    SELECT 1 FROM pagos p WHERE p.numero_pago = 'MIG-' || b.id
);

-- 8. Crear relaciones pago_boletas para boletas migradas
INSERT INTO pago_boletas (pago_id, boleta_id, monto_aplicado, es_pago_completo)
SELECT p.id, b.id, b.total, TRUE
FROM pagos p
JOIN boletas b ON p.numero_pago = 'MIG-' || b.id
WHERE p.numero_pago LIKE 'MIG-%'
AND NOT EXISTS (
    SELECT 1 FROM pago_boletas pb WHERE pb.pago_id = p.id AND pb.boleta_id = b.id
);

-- 9. Migrar historial_pagos existente (si existe la tabla)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'historial_pagos') THEN
        INSERT INTO pagos (numero_pago, cliente_id, monto_total, estado,
                           comprobante_path, metodo_pago, fecha_envio,
                           fecha_procesamiento, motivo_rechazo, notas)
        SELECT
            'HPG-' || h.id,
            m.cliente_id,
            b.total,
            h.estado,
            h.comprobante_path,
            h.metodo_pago,
            h.fecha_envio,
            h.fecha_procesamiento,
            h.motivo_rechazo,
            'Migrado desde historial_pagos'
        FROM historial_pagos h
        JOIN boletas b ON h.boleta_id = b.id
        JOIN medidores m ON b.medidor_id = m.id
        WHERE NOT EXISTS (
            SELECT 1 FROM pagos p WHERE p.numero_pago = 'HPG-' || h.id
        );

        -- Crear relaciones para historial migrado
        INSERT INTO pago_boletas (pago_id, boleta_id, monto_aplicado, es_pago_completo)
        SELECT p.id, h.boleta_id, b.total, (h.estado = 'aprobado')
        FROM pagos p
        JOIN (SELECT * FROM historial_pagos) h ON p.numero_pago = 'HPG-' || h.id
        JOIN boletas b ON h.boleta_id = b.id
        WHERE p.numero_pago LIKE 'HPG-%'
        AND NOT EXISTS (
            SELECT 1 FROM pago_boletas pb WHERE pb.pago_id = p.id AND pb.boleta_id = h.boleta_id
        );
    END IF;
END $$;

-- 10. Inicializar saldos de clientes
INSERT INTO saldos_cliente (cliente_id, saldo_disponible)
SELECT id, 0 FROM clientes
ON CONFLICT (cliente_id) DO NOTHING;

-- 11. Renombrar tabla historial_pagos a legacy (si existe)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'historial_pagos') THEN
        ALTER TABLE historial_pagos RENAME TO historial_pagos_legacy;
    END IF;
END $$;
