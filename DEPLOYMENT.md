# Guía de Despliegue a Producción

Instrucciones para desplegar el Sistema de Cobro de Agua a producción usando EasyPanel con PostgreSQL.

## Pre-requisitos

- ✅ Servidor VPS con Docker y Docker Compose instalados
- ✅ EasyPanel instalado y configurado
- ✅ Acceso SSH al servidor
- ✅ Repositorio GitHub: https://github.com/Gabriel-Barria/sistema-cobro-agua.git
- ✅ Backup de datos actuales (SQLite, fotos, comprobantes)

---

## Paso 1: Configurar EasyPanel

### 1.1. Crear nuevo proyecto

1. Acceder a EasyPanel
2. Crear nuevo proyecto:
   - **Nombre**: `sistema-cobro-agua`
   - **Tipo**: Docker Compose
   - **Repositorio**: `https://github.com/Gabriel-Barria/sistema-cobro-agua.git`
   - **Branch**: `main`
   - **Dockerfile path**: `app/docker-compose.prod.yml`

### 1.2. Configurar variables de entorno

Agregar en la sección **Environment Variables** de EasyPanel:

```env
POSTGRES_PASSWORD=<generar-password-seguro>
DATABASE_URL=postgresql://lecturas_user:<password>@postgres:5432/lecturas
SECRET_KEY=<generar-secret-key>
FLASK_ENV=production
FLASK_APP=web/app.py
```

**Generar secrets seguros:**

```bash
# Secret key (64 caracteres hex)
python -c "import secrets; print(secrets.token_hex(32))"

# Password PostgreSQL (32 caracteres URL-safe)
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

**Ejemplo:**
```env
POSTGRES_PASSWORD=xK9mP2vL5nQ8wR3tY6zB1cF4hJ7sA0dG
DATABASE_URL=postgresql://lecturas_user:xK9mP2vL5nQ8wR3tY6zB1cF4hJ7sA0dG@postgres:5432/lecturas
SECRET_KEY=a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6
FLASK_ENV=production
FLASK_APP=web/app.py
```

### 1.3. Crear volúmenes persistentes

**CRÍTICO**: Los volúmenes deben persistir entre redespliegues

En EasyPanel, crear los siguientes **Named Volumes**:

| Nombre              | Path en contenedor           | Descripción           |
|---------------------|------------------------------|-----------------------|
| `postgres_data`     | `/var/lib/postgresql/data`   | Datos de PostgreSQL   |
| `fotos_data`        | `/app/fotos`                 | Fotos de lecturas     |
| `comprobantes_data` | `/app/comprobantes`          | Comprobantes de pago  |

### 1.4. Configurar puerto y health check

**Puerto expuesto:**
- Container port: `5000`
- External port: (asignado por EasyPanel)

**Health check:**
```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:5000/"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

### 1.5. Deploy inicial

1. Click en **Deploy**
2. Esperar a que el build termine (~5-10 minutos)
3. Verificar logs: `docker logs lecturas-app -f`
4. Acceder a la URL de EasyPanel

---

## Paso 2: Migrar Datos de Producción Actual

### 2.1. Backup de datos actuales (SQLite)

En tu máquina local (donde está corriendo actualmente):

```bash
# Navegar al proyecto
cd /path/to/proyecto

# Backup de base de datos SQLite
cp app/db/lecturas.db app/db/lecturas_backup_$(date +%Y%m%d).db

# Backup de fotos y comprobantes
tar czf fotos_backup_$(date +%Y%m%d).tar.gz app/fotos/
tar czf comprobantes_backup_$(date +%Y%m%d).tar.gz app/comprobantes/
```

### 2.2. Subir archivos al servidor VPS

```bash
# Subir base de datos SQLite
scp app/db/lecturas.db user@your-vps:/tmp/lecturas.db

# Subir fotos (puede tardar dependiendo del tamaño)
rsync -avz --progress app/fotos/ user@your-vps:/tmp/fotos/

# Subir comprobantes
rsync -avz --progress app/comprobantes/ user@your-vps:/tmp/comprobantes/
```

### 2.3. Copiar archivos a volúmenes de Docker

Conectar por SSH al VPS:

```bash
ssh user@your-vps

# Copiar fotos al volumen
docker run --rm \
  -v sistema-cobro-agua_fotos_data:/data \
  -v /tmp/fotos:/source \
  alpine cp -r /source/. /data/

# Copiar comprobantes al volumen
docker run --rm \
  -v sistema-cobro-agua_comprobantes_data:/data \
  -v /tmp/comprobantes:/source \
  alpine cp -r /source/. /data/

# Verificar
docker run --rm -v sistema-cobro-agua_fotos_data:/data alpine ls -la /data/
```

### 2.4. Ejecutar migración de datos

```bash
# Copiar script de migración y base de datos al contenedor
docker cp /tmp/lecturas.db lecturas-app:/app/db/

# Ejecutar migración
docker exec -e DATABASE_URL="postgresql://lecturas_user:<password>@postgres:5432/lecturas" \
  lecturas-app python migrate_sqlite_to_postgres.py
```

**Salida esperada:**
```
🚀 Iniciando migración de SQLite a PostgreSQL
📁 SQLite: db/lecturas.db
🐘 PostgreSQL: postgres:5432/lecturas

📡 Conectando a bases de datos...
⚙️  Deshabilitando constraints...

📦 Migrando tabla: clientes
  ✅ 45 filas migradas
  🔢 Secuencia actualizada

📦 Migrando tabla: medidores
  ✅ 45 filas migradas
  🔢 Secuencia actualizada

📦 Migrando tabla: lecturas
  ✅ 1080 filas migradas
  🔢 Secuencia actualizada

📦 Migrando tabla: boletas
  ✅ 540 filas migradas
  🔢 Secuencia actualizada

⚙️  Rehabilitando constraints...
✅ Migración completada: 1710 filas totales migradas

🔍 Verificando integridad...
  ✅ clientes                 SQLite:    45 | PostgreSQL:    45
  ✅ medidores                SQLite:    45 | PostgreSQL:    45
  ✅ lecturas                 SQLite:  1080 | PostgreSQL:  1080
  ✅ boletas                  SQLite:   540 | PostgreSQL:   540

✅ Verificación exitosa: Todos los datos migrados correctamente
🎉 ¡Migración finalizada exitosamente!
```

---

## Paso 3: Verificación Post-Despliegue

### 3.1. Verificar servicios

```bash
# Verificar contenedores corriendo
docker ps | grep lecturas

# Verificar logs
docker logs lecturas-app --tail 50
docker logs lecturas-db --tail 50

# Verificar PostgreSQL
docker exec lecturas-db psql -U lecturas_user -d lecturas -c "SELECT COUNT(*) FROM clientes;"
```

### 3.2. Verificar aplicación web

Acceder a la URL de EasyPanel y probar:

1. ✅ Login funciona
2. ✅ Listar clientes muestra datos migrados
3. ✅ Listar medidores muestra datos migrados
4. ✅ Ver lecturas muestra datos correctos
5. ✅ Fotos de lecturas se visualizan correctamente
6. ✅ Generar boleta funciona
7. ✅ Portal de pagos (búsqueda por RUT) funciona
8. ✅ Subir comprobante de pago funciona
9. ✅ Ver comprobantes funciona
10. ✅ Estadísticas se calculan correctamente
11. ✅ Exportar a Excel funciona
12. ✅ Generar PDF de boleta funciona

### 3.3. Verificar volúmenes persistentes

```bash
# Verificar fotos
docker exec lecturas-app ls -lh /app/fotos/ | head -10

# Verificar comprobantes
docker exec lecturas-app ls -lh /app/comprobantes/ | head -10

# Verificar datos PostgreSQL
docker volume inspect sistema-cobro-agua_postgres_data
```

---

## Paso 4: Actualizaciones Futuras

### 4.1. Workflow de actualización

```bash
# 1. Hacer cambios en desarrollo local
# 2. Probar localmente con SQLite
cd app
python web/app.py

# 3. Probar con PostgreSQL local (opcional pero recomendado)
docker-compose -f docker-compose.prod.yml up

# 4. Commit y push a GitHub
git add .
git commit -m "feat: nueva funcionalidad"
git push origin main

# 5. EasyPanel detectará cambios y redesplegar automáticamente
# 6. Los volúmenes persisten (fotos, comprobantes, BD)
```

### 4.2. Actualización manual en EasyPanel

Si el auto-deploy está deshabilitado:

1. Acceder a EasyPanel
2. Ir al proyecto `sistema-cobro-agua`
3. Click en **Rebuild & Deploy**
4. Esperar a que termine (~3-5 minutos)
5. Los datos persisten automáticamente

### 4.3. Rollback a versión anterior

Si una actualización falla:

```bash
# En EasyPanel, ir a Deployments
# Seleccionar deployment anterior exitoso
# Click en "Rollback to this version"
```

O manualmente:

```bash
# SSH al servidor
ssh user@your-vps

# Detener servicios
docker-compose -f docker-compose.prod.yml down

# Checkout a commit anterior
cd /path/to/project
git log --oneline  # Ver commits
git checkout <commit-hash>

# Reiniciar servicios
docker-compose -f docker-compose.prod.yml up -d
```

---

## Paso 5: Backup Periódico

### 5.1. Backup automático diario de PostgreSQL

Crear script `/root/backup_lecturas.sh`:

```bash
#!/bin/bash
BACKUP_DIR="/backups/lecturas"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup PostgreSQL
docker exec lecturas-db pg_dump -U lecturas_user lecturas > \
  $BACKUP_DIR/lecturas_$DATE.sql

# Backup volúmenes (fotos y comprobantes)
docker run --rm \
  -v sistema-cobro-agua_fotos_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/fotos_$DATE.tar.gz -C /data .

docker run --rm \
  -v sistema-cobro-agua_comprobantes_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/comprobantes_$DATE.tar.gz -C /data .

# Limpiar backups antiguos (mantener últimos 7 días)
find $BACKUP_DIR -name "*.sql" -mtime +7 -delete
find $BACKUP_DIR -name "*.tar.gz" -mtime +7 -delete

echo "Backup completado: $DATE"
```

Programar en crontab:

```bash
# Editar crontab
crontab -e

# Agregar línea (backup diario a las 2 AM)
0 2 * * * /root/backup_lecturas.sh >> /var/log/backup_lecturas.log 2>&1
```

### 5.2. Restauración desde backup

```bash
# Restaurar PostgreSQL
cat /backups/lecturas/lecturas_20260110_020000.sql | \
  docker exec -i lecturas-db psql -U lecturas_user lecturas

# Restaurar fotos
docker run --rm \
  -v sistema-cobro-agua_fotos_data:/data \
  -v /backups/lecturas:/backup \
  alpine tar xzf /backup/fotos_20260110_020000.tar.gz -C /data

# Restaurar comprobantes
docker run --rm \
  -v sistema-cobro-agua_comprobantes_data:/data \
  -v /backups/lecturas:/backup \
  alpine tar xzf /backup/comprobantes_20260110_020000.tar.gz -C /data
```

---

## Troubleshooting

### Error: "Can't connect to PostgreSQL"

```bash
# Verificar que postgres esté corriendo
docker ps | grep postgres

# Verificar logs de postgres
docker logs lecturas-db

# Verificar DATABASE_URL
docker exec lecturas-app env | grep DATABASE_URL

# Probar conexión manualmente
docker exec lecturas-db psql -U lecturas_user -d lecturas -c "SELECT 1;"
```

### Error: "Fotos no se muestran"

```bash
# Verificar volumen montado
docker inspect lecturas-app | grep -A 10 Mounts

# Verificar permisos
docker exec lecturas-app ls -la /app/fotos/

# Verificar ruta en BD
docker exec lecturas-db psql -U lecturas_user -d lecturas -c \
  "SELECT foto_path FROM lecturas LIMIT 5;"
```

### Error: "Migration failed"

```bash
# Verificar que SQLite esté en el contenedor
docker exec lecturas-app ls -la /app/db/

# Verificar PostgreSQL está listo
docker exec lecturas-db pg_isready -U lecturas_user

# Ejecutar migración con más detalle
docker exec -it lecturas-app python migrate_sqlite_to_postgres.py
```

### Error: "Portal de pagos no funciona"

```bash
# Verificar que los clientes tengan RUT
docker exec lecturas-db psql -U lecturas_user -d lecturas -c \
  "SELECT COUNT(*) FROM clientes WHERE rut IS NULL;"

# Si hay clientes sin RUT, asignarlos manualmente
# o usar el script normalizar_ruts.py
```

### Error: "App crashes al iniciar"

```bash
# Ver logs completos
docker logs lecturas-app

# Verificar variables de entorno
docker exec lecturas-app env | grep -E "DATABASE_URL|FLASK_ENV|SECRET_KEY"

# Reiniciar contenedor
docker restart lecturas-app
```

---

## Monitoreo

### Logs en tiempo real

```bash
# Logs de la aplicación
docker logs -f lecturas-app

# Logs de PostgreSQL
docker logs -f lecturas-db

# Logs de ambos
docker-compose -f docker-compose.prod.yml logs -f
```

### Uso de recursos

```bash
# CPU y memoria
docker stats lecturas-app lecturas-db

# Espacio en disco de volúmenes
docker system df -v
```

### Health check

```bash
# Verificar health status
docker inspect lecturas-app | grep -A 10 Health

# Probar endpoint manualmente
curl http://localhost:5000/
```

---

## Seguridad

### Recomendaciones

1. ✅ Cambiar secrets por defecto (`SECRET_KEY`, `POSTGRES_PASSWORD`)
2. ✅ Usar HTTPS (configurar certificado SSL en EasyPanel)
3. ✅ Habilitar firewall (solo puertos 80, 443, 22)
4. ✅ Actualizar sistema operativo regularmente
5. ✅ Monitorear logs de acceso
6. ✅ Backup periódico automático
7. ✅ Limitar acceso SSH (solo con clave pública)

### Actualizar secrets

```bash
# Generar nuevos secrets
NEW_SECRET=$(python -c "import secrets; print(secrets.token_hex(32))")

# Actualizar en EasyPanel
# Environment Variables > SECRET_KEY > Update

# Reiniciar app
docker restart lecturas-app
```

---

## Contacto y Soporte

- **GitHub**: https://github.com/Gabriel-Barria/sistema-cobro-agua
- **Issues**: https://github.com/Gabriel-Barria/sistema-cobro-agua/issues
- **Email**: (agregar email de contacto)

---

## Checklist de Despliegue

- [ ] Backup de datos actuales (SQLite, fotos, comprobantes)
- [ ] Crear proyecto en EasyPanel
- [ ] Configurar variables de entorno (secrets seguros)
- [ ] Crear volúmenes persistentes
- [ ] Deploy inicial
- [ ] Subir archivos al servidor
- [ ] Copiar archivos a volúmenes Docker
- [ ] Ejecutar migración de datos
- [ ] Verificar servicios corriendo
- [ ] Verificar aplicación web funciona
- [ ] Verificar fotos y comprobantes se muestran
- [ ] Probar portal de pagos
- [ ] Configurar backup automático
- [ ] Configurar HTTPS/SSL
- [ ] Documentar URLs y credenciales

---

**¡Listo! Tu sistema de cobro de agua está en producción con PostgreSQL.**
