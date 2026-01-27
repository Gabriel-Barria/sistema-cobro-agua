-- Migracion: Agregar campo recibe_boleta_whatsapp a clientes
-- Fecha: 2026-01-27

-- Agregar campo para indicar si el cliente recibe boleta por WhatsApp
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS recibe_boleta_whatsapp BOOLEAN DEFAULT FALSE;

-- Crear indice para filtrar por este campo
CREATE INDEX IF NOT EXISTS idx_clientes_recibe_whatsapp ON clientes(recibe_boleta_whatsapp);
