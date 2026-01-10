"""
Aplicación Flask principal - Sistema de Lecturas de Medidores
"""
import os
import sys

# Agregar src al path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from flask import Flask, render_template, send_from_directory

from src.database import inicializar_db, BASE_DIR
from src.models import obtener_estadisticas

app = Flask(__name__)
app.config['SECRET_KEY'] = 'lecturas-medidores-secret-key'

# Directorio base de la app
APP_DIR = BASE_DIR


@app.route('/')
def index():
    """Página principal con estadísticas."""
    stats = obtener_estadisticas()
    return render_template('index.html', stats=stats)


@app.route('/foto/<path:filename>')
def servir_foto(filename):
    """Sirve las fotos desde el directorio de la app."""
    return send_from_directory(APP_DIR, filename)


@app.route('/comprobantes/<path:filename>')
def servir_comprobante(filename):
    """Sirve los comprobantes de pago desde el directorio de la app."""
    comprobantes_dir = os.path.join(APP_DIR, 'comprobantes')
    return send_from_directory(comprobantes_dir, filename)


# Registrar blueprints
from web.routes.lecturas import lecturas_bp
from web.routes.clientes import clientes_bp
from web.routes.medidores import medidores_bp
from web.routes.boletas import boletas_bp
from web.routes.mobile import mobile_bp
from web.routes.portal import portal_bp

app.register_blueprint(lecturas_bp, url_prefix='/lecturas')
app.register_blueprint(clientes_bp, url_prefix='/clientes')
app.register_blueprint(medidores_bp, url_prefix='/medidores')
app.register_blueprint(boletas_bp, url_prefix='/boletas')
app.register_blueprint(mobile_bp, url_prefix='/mobile')
app.register_blueprint(portal_bp, url_prefix='/portal')


# Filtros de plantilla
@app.template_filter('mes_nombre')
def mes_nombre(mes):
    """Convierte número de mes a nombre."""
    meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    return meses[mes] if 1 <= mes <= 12 else str(mes)


@app.template_filter('fecha_formato')
def fecha_formato(fecha):
    """Convierte fecha a formato dd/mm/yyyy."""
    if not fecha:
        return '-'
    if isinstance(fecha, str):
        # Si viene como yyyy-mm-dd
        if '-' in fecha and len(fecha) == 10:
            partes = fecha.split('-')
            if len(partes) == 3:
                return f"{partes[2]}/{partes[1]}/{partes[0]}"
    return str(fecha)


@app.template_filter('formato_pesos')
def formato_pesos(monto):
    """Formatea un monto en pesos con separador de miles (punto)."""
    try:
        # Convertir a float y formatear sin decimales
        valor = float(monto)
        # Formatear con separador de miles usando coma
        formateado = "{:,.0f}".format(valor)
        # Reemplazar coma por punto (formato chileno)
        return formateado.replace(',', '.')
    except (ValueError, TypeError):
        return str(monto)


def crear_app():
    """Factory para crear la aplicación."""
    inicializar_db()
    return app


if __name__ == '__main__':
    inicializar_db()
    app.run(debug=True, port=5000)
