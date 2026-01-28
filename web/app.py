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
from web.auth import admin_required

app = Flask(__name__)

# Configuración de sesiones seguras
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'lecturas-medidores-secret-key-dev')
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # 1 hora

# Directorio base de la app
APP_DIR = BASE_DIR


@app.route('/')
@admin_required
def index():
    """Página principal con estadísticas."""
    stats = obtener_estadisticas()
    return render_template('index.html', stats=stats)

@app.route('/health')
def health():
    """Health check endpoint para EasyPanel/Docker."""
    return {'status': 'ok', 'service': 'sistema-cobro-agua'}, 200


@app.route('/foto/<path:filename>')
def servir_foto(filename):
    """Sirve las fotos desde el directorio de fotos de la app."""
    # Si filename empieza con 'fotos/', quitarlo para evitar duplicacion
    if filename.startswith('fotos/'):
        filename = filename[6:]
    fotos_dir = os.path.join(APP_DIR, 'fotos')
    return send_from_directory(fotos_dir, filename)


@app.route('/comprobantes/<path:filename>')
def servir_comprobante(filename):
    """Sirve los comprobantes de pago desde el directorio de la app."""
    comprobantes_dir = os.path.join(APP_DIR, 'comprobantes')
    return send_from_directory(comprobantes_dir, filename)


# Registrar blueprints
from web.routes.auth import auth_bp
from web.routes.usuarios import usuarios_bp
from web.routes.lecturas import lecturas_bp
from web.routes.clientes import clientes_bp
from web.routes.medidores import medidores_bp
from web.routes.boletas import boletas_bp
from web.routes.mobile import mobile_bp
from web.routes.portal import portal_bp
from web.routes.configuracion import configuracion_bp
from web.routes.scheduler import scheduler_bp
from web.routes.envio_masivo import envio_masivo_bp

app.register_blueprint(auth_bp)
app.register_blueprint(usuarios_bp)
app.register_blueprint(lecturas_bp, url_prefix='/lecturas')
app.register_blueprint(clientes_bp, url_prefix='/clientes')
app.register_blueprint(medidores_bp, url_prefix='/medidores')
app.register_blueprint(boletas_bp, url_prefix='/boletas')
app.register_blueprint(mobile_bp, url_prefix='/mobile')
app.register_blueprint(portal_bp, url_prefix='/portal')
app.register_blueprint(configuracion_bp, url_prefix='/configuracion')
app.register_blueprint(scheduler_bp, url_prefix='/scheduler')
app.register_blueprint(envio_masivo_bp)


# Filtros de plantilla
@app.template_filter('mes_nombre')
def mes_nombre(mes):
    """Convierte número de mes a nombre."""
    meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    return meses[mes] if 1 <= mes <= 12 else str(mes)


@app.template_filter('nombre_mes')
def nombre_mes(mes):
    """Convierte número de mes a nombre corto (Ene, Feb, etc.)."""
    meses = ['', 'Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun',
             'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']
    try:
        idx = int(mes)
        return meses[idx] if 1 <= idx <= 12 else str(mes)
    except (ValueError, TypeError):
        return str(mes)


@app.template_filter('fecha_formato')
def fecha_formato(fecha):
    """Convierte fecha a formato dd/mm/yyyy."""
    if not fecha:
        return '-'
    # Si es objeto date o datetime
    if hasattr(fecha, 'strftime'):
        return fecha.strftime('%d/%m/%Y')
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


@app.template_filter('formato_fecha_hora')
def formato_fecha_hora(fecha):
    """Convierte datetime a formato dd/mm/yyyy HH:MM."""
    if not fecha:
        return '-'
    # Si es objeto datetime
    if hasattr(fecha, 'strftime'):
        return fecha.strftime('%d/%m/%Y %H:%M')
    if isinstance(fecha, str):
        # Si viene como yyyy-mm-dd HH:MM:SS
        if 'T' in fecha or ' ' in fecha:
            try:
                from datetime import datetime
                if 'T' in fecha:
                    dt = datetime.fromisoformat(fecha.replace('Z', '+00:00'))
                else:
                    dt = datetime.strptime(fecha[:19], '%Y-%m-%d %H:%M:%S')
                return dt.strftime('%d/%m/%Y %H:%M')
            except:
                pass
    return str(fecha)


@app.context_processor
def utility_processor():
    """Inyecta utilidades al contexto de templates."""
    def url_for_page(page):
        """Genera URL preservando query params actuales, cambiando solo page."""
        from flask import request
        args = request.args.copy()
        args['page'] = page
        return request.path + '?' + '&'.join(
            f'{k}={v}' for k, v in args.items() if v != ''
        )
    return {'url_for_page': url_for_page}


def _iniciar_scheduler():
    """Inicializa el scheduler de tareas programadas."""
    try:
        from src.services.scheduler_service import init_scheduler, start_scheduler
        init_scheduler(app)
        start_scheduler()
        print("Scheduler iniciado correctamente")
    except Exception as e:
        print(f"Error inicializando scheduler: {e}")


# Inicializar base de datos al importar el modulo
inicializar_db()

# Inicializar scheduler (con 1 worker no hay riesgo de duplicados)
_iniciar_scheduler()


if __name__ == '__main__':
    app.run(debug=True, port=5000)
