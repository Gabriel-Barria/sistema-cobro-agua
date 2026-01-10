#!/bin/bash
# Script de inicio para producción con Gunicorn

echo "Iniciando aplicación con Gunicorn..."
exec gunicorn --bind 0.0.0.0:5000 \
    --workers 4 \
    --timeout 120 \
    --access-logfile - \
    --error-logfile - \
    web.app:app
