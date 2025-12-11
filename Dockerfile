FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y --no-install-recommends \
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
CMD ["python", "-m", "flask", "run", "--host=0.0.0.0", "--port=5000"]
