# Migraciones de Base de Datos

Scripts SQL para mantener la base de datos sincronizada con el codigo.

## Uso

1. Revisar que migraciones faltan ejecutar en produccion
2. Ejecutar los scripts SQL en orden cronologico
3. Verificar que se aplicaron correctamente

## Convencion de Nombres

```
YYYY-MM-DD_NNN_descripcion.sql
```

- `YYYY-MM-DD`: Fecha del commit
- `NNN`: Numero secuencial del dia (001, 002, etc.)
- `descripcion`: Que hace la migracion

## Reglas

- Cada script debe ser **idempotente** (usar `IF NOT EXISTS`, `ON CONFLICT DO NOTHING`, etc.)
- Documentar el commit relacionado en el header del script
- No incluir datos sensibles (passwords en texto plano)

## Historial de Migraciones

| Fecha | Script | Descripcion | Commit |
|-------|--------|-------------|--------|
| 2026-01-11 | 001_crear_tabla_usuarios.sql | Tabla para autenticacion con roles | feat: Implementar sistema de autenticacion con roles |
| 2026-01-11 | 002_historial_pagos.sql | Historial de intentos de pago + eliminar campos obsoletos | feat: Agregar historial de intentos de pago |

## Ejecucion en Produccion

### Opcion 1: Desde EasyPanel (Terminal del contenedor PostgreSQL)
```bash
psql -U lecturas_user -d lecturas -f /path/to/migration.sql
```

### Opcion 2: Copiar y ejecutar manualmente
1. Abrir terminal del contenedor PostgreSQL en EasyPanel
2. Conectar: `psql -U lecturas_user -d lecturas`
3. Pegar el contenido del script SQL
4. Verificar con `\dt` (listar tablas)

### Scripts Python asociados
Algunas migraciones requieren ejecutar scripts Python adicionales:
- `crear_admin_inicial.py` - Crea usuario admin con password hasheado
