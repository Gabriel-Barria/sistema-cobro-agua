#!/bin/sh
# Script de inicio para producción con Gunicorn

echo "=== Iniciando aplicación con Gunicorn ==="
echo "DATABASE_URL: $DATABASE_URL"
echo "FLASK_ENV: $FLASK_ENV"
echo "FLASK_APP: $FLASK_APP"

# Verificar que la app se puede importar
echo "=== Verificando importación de la aplicación ==="
python -c "from web.app import app; print('✓ Aplicación importada correctamente')" 2>&1

if [ $? -ne 0 ]; then
    echo "ERROR: No se pudo importar la aplicación Flask"
    exit 1
fi

echo "=== Iniciando Gunicorn ==="
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 120 \
    --log-level debug \
    --access-logfile - \
    --error-logfile - \
    --capture-output \
    web.app:app
