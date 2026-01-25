FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias del sistema para WeasyPrint y curl para downloads
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libgdk-pixbuf-2.0-0 \
    libffi-dev \
    shared-mime-info \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar requirements e instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el codigo de la aplicacion
COPY . .

# Descargar y compilar CSS (Tailwind + DaisyUI)
RUN mkdir -p /app/web/static/css/build && \
    curl -sLo /app/web/static/css/build/tailwindcss https://github.com/tailwindlabs/tailwindcss/releases/latest/download/tailwindcss-linux-x64 && \
    chmod +x /app/web/static/css/build/tailwindcss && \
    curl -sLo /app/web/static/css/build/daisyui.mjs https://github.com/saadeghi/daisyui/releases/latest/download/daisyui.mjs && \
    curl -sLo /app/web/static/css/build/daisyui-theme.mjs https://github.com/saadeghi/daisyui/releases/latest/download/daisyui-theme.mjs

# Compilar CSS
RUN cd /app/web/static/css && ./build/tailwindcss -i src/input.css -o dist/styles.css --minify

# Hacer el script de inicio ejecutable
RUN chmod +x /app/start.sh

# Crear directorio para la base de datos (fotos y comprobantes ya vienen con COPY)
RUN mkdir -p /app/data

# Variables de entorno
ENV FLASK_APP=web/app.py
ENV FLASK_ENV=production
ENV PYTHONUNBUFFERED=1

# Exponer puerto
EXPOSE 5000

# ENTRYPOINT no puede ser sobrescrito facilmente (a diferencia de CMD)
ENTRYPOINT ["/app/start.sh"]
