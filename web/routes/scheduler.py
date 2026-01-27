"""
Rutas para el scheduler de generacion automatica
"""
from datetime import time
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from web.auth import admin_required
from src.models_scheduler import (
    obtener_cron_config,
    guardar_cron_config,
    listar_logs_generacion,
    obtener_log_generacion,
    contar_logs_generacion
)
from src.services.generacion_service import obtener_preview_generacion, ejecutar_generacion
from src.services.scheduler_service import (
    recargar_configuracion_cron,
    obtener_estado_scheduler,
    ejecutar_generacion_manual
)

scheduler_bp = Blueprint('scheduler', __name__)


@scheduler_bp.route('/')
@admin_required
def index():
    """Dashboard del scheduler."""
    cron_config = obtener_cron_config('generacion_boletas')
    estado = obtener_estado_scheduler()
    logs = listar_logs_generacion(limit=5)

    return render_template('scheduler/index.html',
                           cron_config=cron_config,
                           estado=estado,
                           logs_recientes=logs)


@scheduler_bp.route('/configuracion', methods=['GET', 'POST'])
@admin_required
def configuracion():
    """Configuracion del cron de generacion."""
    if request.method == 'POST':
        tipo = request.form.get('tipo_programacion', 'dia_mes')
        dia_mes = request.form.get('dia_mes', type=int)
        intervalo_dias = request.form.get('intervalo_dias', type=int)
        hora_str = request.form.get('hora_ejecucion', '08:00')
        activo = request.form.get('activo') == 'on'

        # Parsear hora
        try:
            hora_parts = hora_str.split(':')
            hora = time(int(hora_parts[0]), int(hora_parts[1]))
        except:
            hora = time(8, 0)

        # Guardar configuracion
        guardar_cron_config(
            nombre='generacion_boletas',
            tipo_programacion=tipo,
            dia_mes=dia_mes if tipo == 'dia_mes' else None,
            intervalo_dias=intervalo_dias if tipo == 'intervalo_dias' else None,
            hora_ejecucion=hora,
            activo=activo
        )

        # Recargar configuracion del scheduler
        try:
            recargar_configuracion_cron()
        except Exception as e:
            flash(f'Configuracion guardada pero error al recargar scheduler: {str(e)}', 'warning')
            return redirect(url_for('scheduler.configuracion'))

        flash('Configuracion de cron guardada exitosamente', 'success')
        return redirect(url_for('scheduler.configuracion'))

    cron_config = obtener_cron_config('generacion_boletas')
    estado = obtener_estado_scheduler()

    return render_template('scheduler/configuracion.html',
                           cron_config=cron_config,
                           estado=estado)


@scheduler_bp.route('/ejecutar', methods=['GET', 'POST'])
@admin_required
def ejecutar():
    """Ejecutar generacion manualmente."""
    if request.method == 'POST':
        usuario_id = session.get('user_id')
        solo_boletas = request.form.get('solo_boletas') == 'on'

        resultado = ejecutar_generacion(
            usuario_id=usuario_id,
            es_automatico=False,
            solo_boletas=solo_boletas
        )

        if resultado['estado'] == 'error':
            flash(f'Error en generacion: {resultado["mensaje"]}', 'error')
        else:
            flash(resultado['mensaje'], 'success')

        return redirect(url_for('scheduler.log_detalle', log_id=resultado['log_id']))

    # GET: mostrar preview
    preview = obtener_preview_generacion()

    return render_template('scheduler/ejecutar.html', preview=preview)


@scheduler_bp.route('/logs')
@admin_required
def logs():
    """Lista de logs de generacion."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    offset = (page - 1) * per_page

    logs_list = listar_logs_generacion(limit=per_page, offset=offset)
    total = contar_logs_generacion()

    # Paginacion
    total_pages = max(1, (total + per_page - 1) // per_page)
    pagination = {
        'page': page,
        'per_page': per_page,
        'total': total,
        'total_pages': total_pages,
        'start': offset + 1 if total > 0 else 0,
        'end': min(offset + per_page, total)
    }

    return render_template('scheduler/logs.html',
                           logs=logs_list,
                           pagination=pagination)


@scheduler_bp.route('/logs/<int:log_id>')
@admin_required
def log_detalle(log_id):
    """Detalle de un log de generacion."""
    log = obtener_log_generacion(log_id)
    if not log:
        flash('Log no encontrado', 'error')
        return redirect(url_for('scheduler.logs'))

    return render_template('scheduler/log_detalle.html', log=log)


@scheduler_bp.route('/api/preview')
@admin_required
def api_preview():
    """API para obtener preview de generacion."""
    preview = obtener_preview_generacion()

    return jsonify({
        'periodo': f"{preview['periodo_mes']}/{preview['periodo_año']}",
        'crear_lecturas_habilitado': preview['crear_lecturas_habilitado'],
        'total_medidores_sin_lectura': preview['total_medidores_sin_lectura'],
        'total_lecturas_sin_boleta': preview['total_lecturas_sin_boleta'],
        'medidores': [{
            'id': m['id'],
            'numero': m['numero_medidor'],
            'cliente': m['cliente_nombre']
        } for m in preview['medidores_sin_lectura'][:10]],
        'lecturas': [{
            'id': l['id'],
            'medidor': l['numero_medidor'],
            'cliente': l['cliente_nombre'],
            'periodo': f"{l['mes']}/{l['año']}"
        } for l in preview['lecturas_sin_boleta'][:10]]
    })


@scheduler_bp.route('/api/estado')
@admin_required
def api_estado():
    """API para obtener estado del scheduler."""
    estado = obtener_estado_scheduler()
    return jsonify(estado)
