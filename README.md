# Sistema de Cobro de Agua

Sistema web de gestión de lecturas y facturación de agua con portal de pagos para clientes.

## Características

- 📊 Gestión de clientes y medidores
- 📸 Registro de lecturas con fotos
- 💰 Generación automática de boletas
- 💳 Portal de pagos para clientes (búsqueda por RUT)
- 📱 Interfaz mobile-first para registro de lecturas
- 📄 Exportación de boletas a PDF
- ✅ Validación de comprobantes de pago
- 📈 Estadísticas y reportes

## Stack Tecnológico

- **Backend**: Flask (Python 3.11)
- **Base de datos**: PostgreSQL 15 (producción) / SQLite (desarrollo)
- **Frontend**: Jinja2 templates + CSS
- **PDF**: WeasyPrint
- **Excel**: openpyxl
- **Deploy**: Docker + Docker Compose

## Instalación Local

### Desarrollo (SQLite)

```bash
# Clonar repositorio
git clone https://github.com/Gabriel-Barria/sistema-cobro-agua.git
cd sistema-cobro-agua/app

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Inicializar base de datos
python src/database.py

# Crear datos de prueba (opcional)
python crear_datos_prueba.py

# Ejecutar aplicación
python web/app.py

# Acceder a http://localhost:5000
```

### Producción Local con Docker (PostgreSQL)

```bash
# Configurar variables de entorno
cp .env.example .env
# Editar .env con tus credenciales

# Iniciar servicios
docker-compose -f docker-compose.prod.yml up -d

# Ver logs
docker-compose -f docker-compose.prod.yml logs -f

# Acceder a http://localhost:5000
```

### Migrar datos de SQLite a PostgreSQL

```bash
# Configurar DATABASE_URL
export DATABASE_URL='postgresql://lecturas_user:password@localhost:5432/lecturas'

# Ejecutar migración
python migrate_sqlite_to_postgres.py
```

## Despliegue a Producción

Ver [DEPLOYMENT.md](DEPLOYMENT.md) para instrucciones detalladas de despliegue a EasyPanel o VPS.

## Estructura del Proyecto

```
app/
├── src/
│   ├── database.py          # Conexión y esquema (dual mode: SQLite/PostgreSQL)
│   ├── models.py            # CRUD principal (clientes, medidores, lecturas)
│   └── models_boletas.py    # CRUD de boletas y pagos
├── web/
│   ├── app.py               # Aplicación Flask
│   ├── routes/              # Blueprints
│   │   ├── clientes.py
│   │   ├── medidores.py
│   │   ├── lecturas.py
│   │   ├── boletas.py
│   │   └── pagos_portal.py  # Portal público de pagos
│   └── templates/           # Plantillas HTML
│       ├── base.html
│       ├── clientes/
│       ├── medidores/
│       ├── lecturas/
│       ├── boletas/
│       └── portal/          # Portal de pagos para clientes
├── fotos/                   # Fotos de lecturas (persistente)
├── comprobantes/            # Comprobantes de pago (persistente)
├── init_db.sql              # Esquema PostgreSQL
├── migrate_sqlite_to_postgres.py  # Script de migración
├── docker-compose.prod.yml  # Configuración producción
├── .env.example             # Template de variables de entorno
└── requirements.txt         # Dependencias Python
```

## Flujo de Trabajo

### 1. Registro de Lecturas

1. Acceder a **Lecturas** → **Registrar nueva lectura**
2. Seleccionar periodo (mes/anio)
3. Registrar lecturas con foto del medidor
4. Sistema valida duplicados automáticamente

### 2. Generación de Boletas

1. Acceder a **Boletas** → **Generar boletas**
2. Seleccionar periodo
3. Sistema calcula consumo automáticamente
4. Generar boletas en lote para todos los clientes

### 3. Portal de Pagos (Clientes)

1. Cliente accede a `/portal-pagos`
2. Ingresa RUT
3. Ve sus boletas pendientes
4. Sube comprobante de pago
5. Estado cambia a "En Revisión"

### 4. Validación de Pagos (Admin)

1. Acceder a **Boletas** → **Validar pagos**
2. Revisar comprobantes en revisión
3. Aprobar o rechazar con motivo
4. Cliente puede ver estado actualizado

## Variables de Entorno

Ver `.env.example` para el listado completo.

Variables principales:

```env
# PostgreSQL (producción)
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# Flask
SECRET_KEY=tu-secret-key-seguro
FLASK_ENV=production
```

## Desarrollo

### Activar modo dual (SQLite + PostgreSQL)

El sistema detecta automáticamente qué base de datos usar:

- **SQLite**: Si `DATABASE_URL` no está configurado
- **PostgreSQL**: Si `DATABASE_URL` está presente

### Agregar nuevas funciones

1. Añadir función CRUD en `src/models.py` o `src/models_boletas.py`
2. Usar `get_connection()` que retorna la conexión apropiada
3. Usar placeholders `%s` (compatible con ambos)
4. PostgreSQL usa `RETURNING id` en lugar de `lastrowid`

## Backup y Restauración

### Backup PostgreSQL

```bash
# Backup completo
docker exec lecturas-db pg_dump -U lecturas_user lecturas > backup.sql

# Backup de volúmenes
docker run --rm -v sistema-cobro-agua_fotos_data:/data \
  -v $(pwd):/backup alpine tar czf /backup/fotos_backup.tar.gz -C /data .
```

### Restauración

```bash
# Restaurar base de datos
cat backup.sql | docker exec -i lecturas-db psql -U lecturas_user lecturas

# Restaurar volúmenes
docker run --rm -v sistema-cobro-agua_fotos_data:/data \
  -v $(pwd):/backup alpine tar xzf /backup/fotos_backup.tar.gz -C /data
```

## Troubleshooting

### Error: "Can't connect to PostgreSQL"

```bash
# Verificar que postgres esté corriendo
docker ps | grep postgres

# Verificar logs
docker logs lecturas-db

# Verificar DATABASE_URL
echo $DATABASE_URL
```

### Error: "Fotos no se muestran"

```bash
# Verificar volumen montado
docker inspect lecturas-app | grep -A 10 Mounts

# Verificar permisos
docker exec lecturas-app ls -la /app/fotos/
```

### Error de migración

```bash
# Verificar que SQLite exista
ls -la db/lecturas.db

# Ejecutar migración con verbose
python migrate_sqlite_to_postgres.py
```

## Licencia

MIT

## Autor

Gabriel Barría

## Soporte

Para reportar bugs o solicitar funcionalidades, crear un issue en:
https://github.com/Gabriel-Barria/sistema-cobro-agua/issues
