"""
Blueprint Mobile - Interfaz mobile-first para registro de lecturas
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from datetime import datetime
import os
from werkzeug.utils import secure_filename

from web.auth import registrador_required
from src.models import (
    listar_clientes, listar_medidores, crear_lectura,
    obtener_lectura, actualizar_lectura, listar_lecturas,
    lectura_existe, obtener_años_disponibles
)
from src.models_boletas import obtener_boleta_por_lectura
from src.database import BASE_DIR

mobile_bp = Blueprint('mobile', __name__)

# Configuración de fotos
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    """Verifica si la extensión del archivo es permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@mobile_bp.route('/lecturas')
@registrador_required
def registro_lecturas():
    """
    Vista de registro de lecturas mobile.
    Muestra lista de clientes SIN lectura en el período seleccionado.
    """
    from src.models import obtener_clientes_sin_lectura

    # Obtener parámetros de período (año, mes)
    año = request.args.get('año', datetime.now().year, type=int)
    mes = request.args.get('mes', datetime.now().month, type=int)

    # Filtrado AUTOMÁTICO: solo clientes sin lectura en período
    clientes_pendientes = obtener_clientes_sin_lectura(año, mes)

    # Obtener años disponibles para el dropdown
    años = obtener_años_disponibles()
    if not años:
        años = [datetime.now().year]

    return render_template('mobile/registro_lecturas.html',
                          clientes=clientes_pendientes,
                          año=año,
                          mes=mes,
                          años=años)


@mobile_bp.route('/api/medidores/<int:cliente_id>')
@registrador_required
def api_medidores_cliente(cliente_id):
    """
    API JSON: Retorna medidores activos de un cliente.
    Usado cuando se hace clic en tarjeta de cliente.
    """
    medidores = listar_medidores(cliente_id=cliente_id)
    # Filtrar solo activos
    medidores_activos = [m for m in medidores if m.get('activo', 1) == 1]

    return jsonify({
        'count': len(medidores_activos),
        'medidores': medidores_activos
    })


@mobile_bp.route('/lecturas/crear', methods=['POST'])
@registrador_required
def crear_lectura_mobile():
    """
    Crea lectura desde interfaz móvil.
    IMPORTANTE: La fecha se captura automáticamente (no viene del formulario).
    """
    try:
        medidor_id = request.form.get('medidor_id', type=int)
        lectura_m3 = request.form.get('lectura_m3', type=int)
        año = request.form.get('año', type=int)
        mes = request.form.get('mes', type=int)
        foto = request.files.get('foto')

        # Validar campos requeridos
        if not medidor_id or not lectura_m3 or not año or not mes:
            return jsonify({'error': 'Campos requeridos faltantes'}), 400

        # Validar foto requerida
        if not foto or foto.filename == '':
            return jsonify({'error': 'La foto es requerida'}), 400

        if not allowed_file(foto.filename):
            return jsonify({'error': 'Formato de foto inválido. Use PNG, JPG o JPEG'}), 400

        # CAPTURA AUTOMÁTICA DE FECHA (diferencia con interfaz actual)
        fecha_lectura = datetime.now().date()

        # Validar duplicado
        if lectura_existe(medidor_id, año, mes):
            return jsonify({'error': 'Ya existe lectura para este período'}), 400

        # Guardar foto
        filename = secure_filename(foto.filename)
        # Estructura: fotos/medidor_{id}/{año}/{mes:02d}/
        foto_dir = os.path.join(BASE_DIR, 'fotos', f'medidor_{medidor_id}', str(año), f'{mes:02d}')
        os.makedirs(foto_dir, exist_ok=True)

        # Nombre único con timestamp
        timestamp = datetime.now().strftime('%H-%M-%S')
        foto_nombre = f'{filename.rsplit(".", 1)[0]}_{timestamp}.{filename.rsplit(".", 1)[1]}'
        foto_path_completa = os.path.join(foto_dir, foto_nombre)
        foto.save(foto_path_completa)

        # Ruta relativa para BD
        foto_path = f'fotos/medidor_{medidor_id}/{año}/{mes:02d}/{foto_nombre}'

        # Crear lectura
        lectura_id = crear_lectura(
            medidor_id=medidor_id,
            lectura_m3=lectura_m3,
            fecha_lectura=fecha_lectura,
            foto_path=foto_path,
            foto_nombre=foto_nombre,
            año=año,
            mes=mes
        )

        return jsonify({
            'success': True,
            'lectura_id': lectura_id,
            'message': 'Lectura registrada exitosamente'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@mobile_bp.route('/ver-lecturas')
@registrador_required
def ver_lecturas():
    """
    Vista de listado de lecturas existentes con opción de editar.
    Filtrado opcional por año/mes.
    """
    año = request.args.get('año', type=int)  # Opcional
    mes = request.args.get('mes', type=int)  # Opcional

    # Usar función existente con filtros opcionales
    lecturas = listar_lecturas(año=año, mes=mes, limit=200, offset=0)

    # Obtener años disponibles para filtros
    años = obtener_años_disponibles()
    if not años:
        años = [datetime.now().year]

    return render_template('mobile/ver_lecturas.html',
                          lecturas=lecturas,
                          año_sel=año,
                          mes_sel=mes,
                          años=años)


@mobile_bp.route('/api/validar-edicion/<int:lectura_id>')
@registrador_required
def validar_edicion_lectura(lectura_id):
    """
    Valida si una lectura puede ser editada.
    Retorna error si existe boleta asociada.
    """
    # VALIDACIÓN CRÍTICA
    boleta = obtener_boleta_por_lectura(lectura_id)

    if boleta:
        return jsonify({
            'puede_editar': False,
            'motivo': 'No se puede editar: existe boleta generada para esta lectura',
            'boleta_id': boleta.get('id')
        })

    return jsonify({'puede_editar': True})


@mobile_bp.route('/api/lectura/<int:lectura_id>')
@registrador_required
def api_obtener_lectura(lectura_id):
    """
    API JSON: Retorna datos de una lectura para edición.
    """
    lectura = obtener_lectura(lectura_id)
    if not lectura:
        return jsonify({'error': 'Lectura no encontrada'}), 404

    return jsonify(lectura)


@mobile_bp.route('/lecturas/<int:lectura_id>/editar', methods=['POST'])
@registrador_required
def editar_lectura_mobile(lectura_id):
    """
    Actualiza una lectura existente.
    Valida que no exista boleta antes de permitir edición.
    """
    try:
        # VALIDACIÓN CRÍTICA
        boleta = obtener_boleta_por_lectura(lectura_id)
        if boleta:
            return jsonify({
                'error': 'No se puede editar: existe boleta generada para esta lectura'
            }), 403

        lectura_m3 = request.form.get('lectura_m3', type=int)
        fecha_str = request.form.get('fecha_lectura')

        fecha_lectura = None
        if fecha_str:
            try:
                fecha_lectura = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                return jsonify({'error': 'Formato de fecha inválido'}), 400

        # Actualizar usando función existente
        actualizar_lectura(lectura_id, lectura_m3=lectura_m3, fecha_lectura=fecha_lectura)

        return jsonify({
            'success': True,
            'message': 'Lectura actualizada exitosamente'
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
