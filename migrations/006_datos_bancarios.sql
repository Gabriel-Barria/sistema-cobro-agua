-- Migracion: Agregar datos bancarios a configuracion_sistema
-- Fecha: 2026-01-29
-- Descripcion: Inserta los datos bancarios iniciales para transferencias

-- Insertar datos bancarios (si no existen)
INSERT INTO configuracion_sistema (clave, valor, descripcion, tipo) VALUES
('banco_nombre', 'Banco Estado', 'Nombre del banco', 'string'),
('banco_cuenta', '82970400962', 'Numero de cuenta', 'string'),
('banco_rut', '65096733-k', 'RUT del titular', 'string'),
('banco_tipo_cuenta', 'Cuenta Vista o Chequera electronica', 'Tipo de cuenta', 'string'),
('banco_titular', 'Comite de Trabajo Pasaje Bauche', 'Nombre del titular', 'string'),
('banco_email', 'comite.bauche@gmail.com', 'Email de contacto', 'string')
ON CONFLICT (clave) DO NOTHING;
