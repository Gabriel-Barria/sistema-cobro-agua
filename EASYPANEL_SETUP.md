# Configuración EasyPanel - Sistema de Cobro de Agua

## Repositorio GitHub
- **URL**: https://github.com/Gabriel-Barria/migracion-data-lecturas.git
- **Branch**: main
- **Commit**: 546fd98 (feat: migración completa a PostgreSQL)

---

## 1. Variables de Entorno

Copiar estas variables en EasyPanel > Environment Variables:

```env
POSTGRES_PASSWORD=8a33hmkR6-LZYrlsbSzn085A81IHLaOK
DATABASE_URL=postgresql://lecturas_user:8a33hmkR6-LZYrlsbSzn085A81IHLaOK@postgres:5432/lecturas
SECRET_KEY=ea2f27f6116abf4bc5e196191e55a1157f66cacc58f4bd475e13fd8e86e92514
FLASK_ENV=production
FLASK_APP=web/app.py
```

**IMPORTANTE**: Estas credenciales son únicas para este despliegue. Puedes generar nuevas con:
```bash
# SECRET_KEY
python -c "import secrets; print(secrets.token_hex(32))"

# POSTGRES_PASSWORD
python -c "import secrets; print(secrets.token_urlsafe(24))"
```

---

## 2. Configuración Paso a Paso en EasyPanel

### PASO 1: Crear Nuevo Proyecto
1. Acceder a EasyPanel
2. Click en "New Project"
3. Nombre: `sistema-cobro-agua`
4. Tipo: **Docker Compose**

### PASO 2: Conectar Repositorio GitHub
- Repository URL: `https://github.com/Gabriel-Barria/migracion-data-lecturas.git`
- Branch: `main`
- Build context: `/` (raíz)
- Docker Compose file: `docker-compose.prod.yml`

### PASO 3: Variables de Entorno
Agregar en "Environment Variables":
```
POSTGRES_PASSWORD=8a33hmkR6-LZYrlsbSzn085A81IHLaOK
DATABASE_URL=postgresql://lecturas_user:8a33hmkR6-LZYrlsbSzn085A81IHLaOK@postgres:5432/lecturas
SECRET_KEY=ea2f27f6116abf4bc5e196191e55a1157f66cacc58f4bd475e13fd8e86e92514
FLASK_ENV=production
FLASK_APP=web/app.py
```

### PASO 4: Volúmenes Persistentes
**CRÍTICO**: Crear estos Named Volumes:

| Nombre | Path en contenedor | Descripción |
|--------|-------------------|-------------|
| `postgres_data` | `/var/lib/postgresql/data` | Datos PostgreSQL |
| `fotos_data` | `/app/fotos` | Fotos de lecturas |
| `comprobantes_data` | `/app/comprobantes` | Comprobantes de pago |

### PASO 5: Puerto
- Container port: `5000`
- External port: (asignado por EasyPanel)

### PASO 6: Health Check (opcional)
```
Command: curl -f http://localhost:5000/ || exit 1
Interval: 30s
Timeout: 10s
Retries: 3
```

### PASO 7: Deploy
1. Click en "Deploy"
2. Esperar build (~5-10 min primera vez)
3. Verificar logs
4. Acceder a URL de EasyPanel

---

## 3. Migración de Datos (DESPUÉS del deploy)

### PASO 1: Backup Local
```bash
# En tu máquina local
cp app/db/lecturas.db app/db/lecturas_backup_$(date +%Y%m%d).db
tar czf fotos_backup.tar.gz app/fotos/
tar czf comprobantes_backup.tar.gz app/comprobantes/
```

### PASO 2: Subir al Servidor
```bash
# Reemplazar usuario@servidor con tus datos
scp app/db/lecturas.db usuario@servidor:/tmp/
rsync -avz --progress app/fotos/ usuario@servidor:/tmp/fotos/
rsync -avz --progress app/comprobantes/ usuario@servidor:/tmp/comprobantes/
```

### PASO 3: Copiar a Volúmenes Docker
```bash
# SSH al servidor, luego:

# Fotos
docker run --rm \
  -v sistema-cobro-agua_fotos_data:/data \
  -v /tmp/fotos:/source \
  alpine cp -r /source/. /data/

# Comprobantes
docker run --rm \
  -v sistema-cobro-agua_comprobantes_data:/data \
  -v /tmp/comprobantes:/source \
  alpine cp -r /source/. /data/

# Verificar
docker run --rm -v sistema-cobro-agua_fotos_data:/data alpine ls /data/
```

### PASO 4: Migrar Datos
```bash
# Encontrar nombre del contenedor
docker ps | grep sistema-cobro-agua

# Copiar base de datos SQLite
docker cp /tmp/lecturas.db <nombre-contenedor>:/app/db/

# Ejecutar migración
docker exec -e DATABASE_URL="postgresql://lecturas_user:8a33hmkR6-LZYrlsbSzn085A81IHLaOK@postgres:5432/lecturas" \
  <nombre-contenedor> python migrate_simple.py
```

**Salida esperada**:
```
=== Iniciando migracion SQLite a PostgreSQL ===
[clientes] 53 filas migradas
[medidores] 58 filas migradas
[lecturas] 1235 filas migradas
[boletas] 1219 filas migradas
=== Migracion completada: 2566 filas totales ===
Todos los datos migrados correctamente
```

---

## 4. Verificación

### Servicios
```bash
docker ps | grep sistema-cobro-agua
docker logs <nombre-contenedor-web> --tail 50
```

### Base de Datos
```bash
docker exec <nombre-contenedor-postgres> psql -U lecturas_user -d lecturas -c "SELECT COUNT(*) FROM clientes;"
```

### Aplicación Web
Acceder a URL de EasyPanel y verificar:
- ✅ Login funciona
- ✅ Clientes, medidores, lecturas se muestran
- ✅ Fotos se visualizan
- ✅ Generar boleta funciona
- ✅ Portal de pagos funciona
- ✅ Descargar PDF funciona

---

## 5. Actualizaciones Futuras

```bash
# 1. Hacer cambios localmente
# 2. Commit y push
git add .
git commit -m "descripción"
git push origin main

# 3. EasyPanel redesplegar automáticamente
# 4. Volúmenes persisten (fotos, comprobantes, BD)
```

---

## 6. Backup Automático

Crear script `/root/backup_lecturas.sh`:
```bash
#!/bin/bash
BACKUP_DIR="/backups/lecturas"
DATE=$(date +%Y%m%d_%H%M%S)
mkdir -p $BACKUP_DIR

# PostgreSQL
docker exec <contenedor-postgres> pg_dump -U lecturas_user lecturas > \
  $BACKUP_DIR/lecturas_$DATE.sql

# Fotos
docker run --rm \
  -v sistema-cobro-agua_fotos_data:/data \
  -v $BACKUP_DIR:/backup \
  alpine tar czf /backup/fotos_$DATE.tar.gz -C /data .

# Limpiar antiguos (7 días)
find $BACKUP_DIR -mtime +7 -delete
```

Crontab (2 AM diario):
```bash
0 2 * * * /root/backup_lecturas.sh >> /var/log/backup.log 2>&1
```

---

## 7. Troubleshooting

### Fotos no se muestran
```bash
docker exec <contenedor-web> ls -la /app/fotos/
docker inspect <contenedor-web> | grep -A 10 Mounts
```

### Error conexión PostgreSQL
```bash
docker logs <contenedor-postgres>
docker exec <contenedor-web> env | grep DATABASE_URL
docker exec <contenedor-postgres> pg_isready -U lecturas_user
```

### App crashes
```bash
docker logs <contenedor-web>
docker exec <contenedor-web> env | grep -E "DATABASE_URL|FLASK_ENV|SECRET_KEY"
docker restart <contenedor-web>
```

---

## Checklist

**ANTES**:
- [ ] Backup de datos actuales
- [ ] Repositorio actualizado

**EN EASYPANEL**:
- [ ] Proyecto creado
- [ ] Repositorio conectado
- [ ] Variables de entorno configuradas
- [ ] Volúmenes creados
- [ ] Deploy inicial exitoso

**DESPUÉS**:
- [ ] Archivos subidos al servidor
- [ ] Archivos copiados a volúmenes
- [ ] Migración de datos ejecutada
- [ ] Aplicación verificada
- [ ] Backup automático configurado

---

**¡Sistema listo para producción!**
