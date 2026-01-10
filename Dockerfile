FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para WeasyPrint
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo de la aplicacion
COPY . .

# Crear directorio para la base de datos y fotos
RUN mkdir -p /app/data /app/fotos

# Variables de entorno
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Exponer puerto
EXPOSE 5000

# Comando para ejecutar la aplicacion
# Comando para ejecutar la aplicacion con Gunicorn (servidor WSGI de producción)
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "--access-logfile", "-", "--error-logfile", "-", "web.app:app"]
