# Gestión de Ambientes - Sistema de Cobro de Agua

## Estructura de Ambientes

Este proyecto usa **dos ambientes separados** en EasyPanel:

### 🔧 DEV (Desarrollo)
- **Rama Git**: `dev`
- **Base de datos**: `comite_sistema-cobro-agua_bd_dev`
- **Propósito**: Desarrollo, pruebas, validación de cambios
- **Variables de entorno**: Ver `.env.dev`
- **FLASK_ENV**: `development`

### 🚀 PROD (Producción)
- **Rama Git**: `main`
- **Base de datos**: `comite_sistema-cobro-agua_bd_prod` (crear cuando pases a prod)
- **Propósito**: Datos reales de usuarios finales
- **Variables de entorno**: Ver `.env.production`
- **FLASK_ENV**: `production`

---

## 📋 Configuración en EasyPanel

### Ambiente DEV:
```
Repository: https://github.com/Gabriel-Barria/sistema-cobro-agua.git
Branch: dev
Port: 5000

Variables de entorno:
POSTGRES_PASSWORD=3ded1e5249552fcf2931
DATABASE_URL=postgresql://postgres:3ded1e5249552fcf2931@comite_sistema-cobro-agua_bd_dev:5432/sistema-cobro-agua
SECRET_KEY=0681029d46d4ae20e34274a1417dca51107680cedc0e8c5de556506b4123e6d8
FLASK_ENV=development
FLASK_APP=web/app.py
```

### Ambiente PROD:
```
Repository: https://github.com/Gabriel-Barria/sistema-cobro-agua.git
Branch: main
Port: 5000

Variables de entorno:
(Configurar cuando crees el servicio de BD de producción)
Ver .env.production para template
```

---

## 🔄 Flujo de Trabajo

### 1. Desarrollo diario (rama dev)

```bash
# Asegurarte de estar en dev
git checkout dev

# Hacer cambios en el código
# ...

# Commit y push
git add .
git commit -m "feat: descripción del cambio

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
git push origin dev
```

→ EasyPanel DEV se redespliegue automáticamente
→ Probar en ambiente DEV

### 2. Validación

- Acceder al ambiente DEV
- Probar todas las funcionalidades modificadas
- Verificar que no haya errores
- Verificar que los datos se muestran correctamente

### 3. Pasar a Producción (cuando todo está validado)

```bash
# Cambiar a main
git checkout main

# Traer cambios de dev
git merge dev

# Subir a producción
git push origin main
```

→ EasyPanel PROD se redespliegue automáticamente
→ Cambios en producción

---

## ⚠️ Reglas Importantes

1. **NUNCA hacer cambios directamente en rama `main`**
   - Siempre trabajar en rama `dev`
   - Solo hacer merge a `main` cuando todo esté validado

2. **Bases de datos separadas**
   - DEV y PROD tienen bases de datos diferentes
   - Los cambios en DEV NO afectan datos de producción

3. **Credenciales diferentes**
   - Cada ambiente tiene sus propias credenciales
   - NUNCA usar credenciales de producción en desarrollo

4. **Archivos .env**
   - NUNCA subir archivos .env a GitHub
   - Ya están en .gitignore
   - Configurar directamente en EasyPanel

---

## 🔍 Verificar ambiente actual

```bash
# Ver en qué rama estás
git branch

# Ver estado actual
git status

# Ver últimos commits
git log --oneline -5
```

---

## 🆘 Troubleshooting

### ¿Cómo sé en qué ambiente estoy?
- Mira el título del navegador o la URL
- DEV tendrá una URL diferente a PROD en EasyPanel

### ¿Hice cambios en main por error?
```bash
# Revertir último commit (sin borrar cambios)
git reset --soft HEAD~1

# Cambiar a dev
git checkout dev

# Volver a hacer commit
git add .
git commit -m "..."
git push origin dev
```

### ¿Cómo volver a una versión anterior?
```bash
# Ver historial
git log --oneline

# Volver a un commit específico
git checkout <commit-hash>
```

---

## 📊 Estado Actual

**Rama activa**: `dev` ✅
**Ambiente DEV**: Configurado ✅
**Ambiente PROD**: Pendiente de configurar
**Datos migrados en DEV**: 2566 registros ✅

---

**Próximos pasos:**
1. Corregir errores en ambiente DEV
2. Validar que todo funciona correctamente
3. Configurar ambiente PROD
4. Migrar datos a PROD
5. Pasar código validado a rama `main`
