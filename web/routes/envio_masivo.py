"""
Rutas para envio masivo de boletas por WhatsApp
"""
from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app, jsonify
from web.auth import admin_required, get_current_user
from src.services.envio_masivo_service import (
    obtener_preview_envio,
    iniciar_envio_masivo_async,
    obtener_log_envio,
    listar_logs_envio,
    hay_proceso_en_curso
)


envio_masivo_bp = Blueprint('envio_masivo', __name__, url_prefix='/envio-masivo')


@envio_masivo_bp.route('/')
@admin_required
def index():
    """Muestra el dashboard de envio masivo con preview."""
    preview = obtener_preview_envio()
    proceso_en_curso = hay_proceso_en_curso()

    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    return render_template('envio_masivo/index.html',
                           preview=preview,
                           meses=meses,
                           proceso_en_curso=proceso_en_curso)


@envio_masivo_bp.route('/ejecutar', methods=['POST'])
@admin_required
def ejecutar():
    """Inicia el envio masivo de boletas en background."""
    usuario = get_current_user()
    usuario_id = usuario['id'] if usuario else None

    if not usuario_id:
        flash('Debe iniciar sesion para ejecutar el envio masivo', 'error')
        return redirect(url_for('envio_masivo.index'))

    try:
        log_id = iniciar_envio_masivo_async(usuario_id, current_app._get_current_object())
        flash('Proceso de envio masivo iniciado. La pagina se actualizara automaticamente.', 'success')
        return redirect(url_for('envio_masivo.log_detalle', log_id=log_id))
    except ValueError as e:
        flash(str(e), 'warning')
        return redirect(url_for('envio_masivo.index'))
    except Exception as e:
        flash(f'Error al iniciar envio: {str(e)}', 'error')
        return redirect(url_for('envio_masivo.index'))


@envio_masivo_bp.route('/estado/<int:log_id>')
@admin_required
def estado(log_id):
    """API endpoint para obtener estado del proceso (polling)."""
    log = obtener_log_envio(log_id)

    if not log:
        return jsonify({'error': 'Log no encontrado'}), 404

    return jsonify({
        'id': log['id'],
        'estado': log['estado'],
        'total_boletas': log['total_boletas'],
        'total_enviables': log.get('total_enviables', 0),
        'enviadas_exitosas': log['enviadas_exitosas'],
        'enviadas_fallidas': log['enviadas_fallidas'],
        'mensaje': log.get('mensaje', ''),
        'duracion_segundos': float(log['duracion_segundos']) if log.get('duracion_segundos') else None,
        'en_curso': log['estado'] == 'iniciado'
    })


@envio_masivo_bp.route('/logs')
@admin_required
def logs():
    """Lista los logs de envio masivo."""
    logs_list = listar_logs_envio(limite=50)

    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    return render_template('envio_masivo/logs.html',
                           logs=logs_list,
                           meses=meses)


@envio_masivo_bp.route('/logs/<int:log_id>')
@admin_required
def log_detalle(log_id):
    """Muestra el detalle de un log de envio."""
    log = obtener_log_envio(log_id)

    if not log:
        flash('Log no encontrado', 'error')
        return redirect(url_for('envio_masivo.logs'))

    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    return render_template('envio_masivo/log_detalle.html',
                           log=log,
                           meses=meses)
