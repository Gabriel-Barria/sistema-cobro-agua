-- Migración: Prevenir lecturas duplicadas por medidor/periodo
-- Fecha: 2026-01-24
-- Descripción: Elimina lecturas duplicadas (mismo medidor/periodo) y agrega
-- constraint UNIQUE para prevenir futuros duplicados.
-- Criterio de conservación: prioriza la lectura que tenga boleta asociada,
-- luego la que tenga foto, luego la más reciente (mayor ID).

-- Paso 1: Eliminar duplicados conservando la mejor lectura por grupo
DELETE FROM lecturas
WHERE id NOT IN (
    SELECT DISTINCT ON (medidor_id, anio, mes) l.id
    FROM lecturas l
    LEFT JOIN boletas b ON b.lectura_id = l.id
    ORDER BY medidor_id, anio, mes,
        -- Prioridad 1: tiene boleta asociada
        CASE WHEN b.id IS NOT NULL THEN 0 ELSE 1 END,
        -- Prioridad 2: tiene foto
        CASE WHEN l.foto_path != '' AND l.foto_nombre != 'sin_foto' THEN 0 ELSE 1 END,
        -- Prioridad 3: más reciente
        l.id DESC
);

-- Paso 2: Agregar constraint UNIQUE
ALTER TABLE lecturas
ADD CONSTRAINT uq_lectura_medidor_periodo UNIQUE (medidor_id, anio, mes);
