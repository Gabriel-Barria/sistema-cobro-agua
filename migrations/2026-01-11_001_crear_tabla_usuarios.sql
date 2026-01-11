-- ============================================================
-- Migracion: Crear tabla usuarios para sistema de autenticacion
-- Fecha: 2026-01-11
-- Commit: feat: Implementar sistema de autenticacion con roles
-- Autor: Claude Code
-- ============================================================
--
-- DESCRIPCION:
-- Crea la tabla de usuarios del sistema (staff) para manejar
-- autenticacion y autorizacion basada en roles.
--
-- ROLES DISPONIBLES:
--   - administrador: Acceso completo a todas las rutas
--   - registrador: Solo acceso a /mobile para registro de lecturas
--
-- NOTAS:
--   - El portal publico (/portal) NO requiere autenticacion
--   - Los passwords se almacenan hasheados con werkzeug.security
-- ============================================================

-- Crear tabla de usuarios del sistema (staff)
CREATE TABLE IF NOT EXISTS usuarios (
    id SERIAL PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    nombre_completo VARCHAR(100) NOT NULL,
    rol VARCHAR(20) NOT NULL CHECK (rol IN ('administrador', 'registrador')),
    activo SMALLINT DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indice para busqueda rapida por username
CREATE INDEX IF NOT EXISTS idx_usuarios_username ON usuarios(username);

-- ============================================================
-- POST-MIGRACION:
-- Ejecutar el siguiente script Python para crear el usuario admin:
--
--   python crear_admin_inicial.py
--
-- Credenciales iniciales:
--   Usuario: admin
--   Password: admin123
--
-- IMPORTANTE: Cambiar la contrasena despues del primer login
-- ============================================================
