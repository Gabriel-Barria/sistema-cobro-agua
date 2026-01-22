-- Migración: Agregar campos telefono y email a clientes
-- Fecha: 2026-01-22

ALTER TABLE clientes ADD COLUMN IF NOT EXISTS telefono VARCHAR(20);
ALTER TABLE clientes ADD COLUMN IF NOT EXISTS email VARCHAR(100);
