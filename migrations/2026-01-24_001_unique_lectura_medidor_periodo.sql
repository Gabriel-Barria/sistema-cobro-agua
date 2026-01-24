-- Migración: Prevenir lecturas duplicadas por medidor/periodo
-- Fecha: 2026-01-24
-- Descripción: Agrega constraint UNIQUE en (medidor_id, año, mes) para evitar
-- que se registren dos lecturas para el mismo medidor en el mismo periodo.

ALTER TABLE lecturas
ADD CONSTRAINT uq_lectura_medidor_periodo UNIQUE (medidor_id, año, mes);
