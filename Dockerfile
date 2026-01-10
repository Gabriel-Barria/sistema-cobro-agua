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

# Hacer el script de inicio ejecutable
RUN chmod +x /app/start.sh

# Crear directorio para la base de datos y fotos
RUN mkdir -p /app/data /app/fotos

# Variables de entorno
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Exponer puerto
EXPOSE 5000

# ENTRYPOINT no puede ser sobrescrito facilmente (a diferencia de CMD)
ENTRYPOINT ["/app/start.sh"]
