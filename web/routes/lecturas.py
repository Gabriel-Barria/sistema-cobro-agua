"""
Rutas para gestión de lecturas
"""
import os
import json
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from web.auth import admin_required
from src.models_boletas import obtener_boleta_por_lectura
from src.models import (
    listar_lecturas, obtener_lectura, crear_lectura, actualizar_lectura,
    eliminar_lectura, contar_lecturas, obtener_años_disponibles,
    listar_clientes, listar_medidores, obtener_o_crear_medidor,
    obtener_clientes_incompletos, obtener_fechas_comunes_por_periodo,
    crear_lecturas_multiple
)
from src.database import BASE_DIR

lecturas_bp = Blueprint('lecturas', __name__)

FOTOS_DIR = os.path.join(BASE_DIR, 'fotos')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@lecturas_bp.route('/')
@admin_required
def listar():
    """Lista todas las lecturas con filtros."""
    # Parámetros de filtro
    año = request.args.get('año', type=int)
    mes = request.args.get('mes', type=int)
    cliente_id = request.args.get('cliente_id', type=int)
    medidor_id = request.args.get('medidor_id', type=int)
    page = request.args.get('page', 1, type=int)
    per_page = 20

    # Parámetros de ordenamiento
    orden_col = request.args.get('orden', default=None)
    orden_dir = request.args.get('dir', default='asc')

    # Filtro de incompletos
    incompletos = request.args.get('incompletos', type=int, default=0) == 1

    # Obtener lecturas
    offset = (page - 1) * per_page
    lecturas = listar_lecturas(
        año=año, mes=mes, cliente_id=cliente_id, medidor_id=medidor_id,
        limit=per_page, offset=offset,
        orden_col=orden_col, orden_dir=orden_dir,
        solo_incompletos=incompletos
    )
    total = contar_lecturas(año=año, mes=mes, cliente_id=cliente_id, medidor_id=medidor_id, solo_incompletos=incompletos)

    # Datos para filtros
    años = obtener_años_disponibles()
    clientes = listar_clientes()
    medidores = listar_medidores(cliente_id) if cliente_id else listar_medidores()
    clientes_incompletos = obtener_clientes_incompletos() if incompletos else []

    return render_template('lecturas/lista.html',
                           lecturas=lecturas,
                           años=años,
                           clientes=clientes,
                           medidores=medidores,
                           clientes_incompletos=clientes_incompletos,
                           año_sel=año,
                           mes_sel=mes,
                           cliente_sel=cliente_id,
                           medidor_sel=medidor_id,
                           page=page,
                           total=total,
                           per_page=per_page,
                           orden_col=orden_col,
                           orden_dir=orden_dir,
                           incompletos=incompletos)


@lecturas_bp.route('/<int:lectura_id>')
@admin_required
def detalle(lectura_id):
    """Muestra detalle de una lectura con su foto."""
    lectura = obtener_lectura(lectura_id)
    if not lectura:
        flash('Lectura no encontrada', 'error')
        return redirect(url_for('lecturas.listar'))

    return render_template('lecturas/detalle.html', lectura=lectura)


@lecturas_bp.route('/nueva', methods=['GET', 'POST'])
@admin_required
def crear():
    """Formulario para crear nueva lectura."""
    if request.method == 'POST':
        medidor_id = request.form.get('medidor_id', type=int)
        lectura_m3 = request.form.get('lectura_m3', type=int)
        fecha_str = request.form.get('fecha_lectura')
        año = request.form.get('año', type=int)
        mes = request.form.get('mes', type=int)

        # Validar
        if not all([medidor_id, lectura_m3, fecha_str, año, mes]):
            flash('Todos los campos son requeridos', 'error')
            return redirect(url_for('lecturas.crear'))

        try:
            fecha_lectura = datetime.strptime(fecha_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Fecha inválida', 'error')
            return redirect(url_for('lecturas.crear'))

        # Procesar foto
        foto_path = ''
        foto_nombre = ''

        if 'foto' in request.files:
            file = request.files['foto']
            if file and file.filename and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Crear directorio
                destino_dir = os.path.join(FOTOS_DIR, f'medidor_{medidor_id}', str(año), f'{mes:02d}')
                os.makedirs(destino_dir, exist_ok=True)

                # Guardar archivo
                destino = os.path.join(destino_dir, filename)
                file.save(destino)

                foto_path = f'medidor_{medidor_id}/{año}/{mes:02d}/{filename}'
                foto_nombre = filename

        # Ajustar foto_path para lecturas sin foto
        if not foto_path:
            foto_path = ''
            foto_nombre = 'sin_foto'

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

        flash('Lectura creada exitosamente', 'success')
        return redirect(url_for('lecturas.detalle', lectura_id=lectura_id))

    # GET: mostrar formulario
    medidores = listar_medidores()
    años = list(range(2023, datetime.now().year + 1))

    return render_template('lecturas/crear.html', medidores=medidores, años=años)


@lecturas_bp.route('/<int:lectura_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar(lectura_id):
    """Formulario para editar una lectura."""
    lectura = obtener_lectura(lectura_id)
    if not lectura:
        flash('Lectura no encontrada', 'error')
        return redirect(url_for('lecturas.listar'))

    if request.method == 'POST':
        lectura_m3 = request.form.get('lectura_m3', type=int)
        fecha_str = request.form.get('fecha_lectura')

        fecha_lectura = None
        if fecha_str:
            try:
                fecha_lectura = datetime.strptime(fecha_str, '%Y-%m-%d').date()
            except ValueError:
                flash('Fecha inválida', 'error')
                return redirect(url_for('lecturas.editar', lectura_id=lectura_id))

        actualizar_lectura(lectura_id, lectura_m3=lectura_m3, fecha_lectura=fecha_lectura)
        flash('Lectura actualizada', 'success')
        return redirect(url_for('lecturas.detalle', lectura_id=lectura_id))

    return render_template('lecturas/editar.html', lectura=lectura)


@lecturas_bp.route('/<int:lectura_id>/eliminar', methods=['POST'])
@admin_required
def eliminar(lectura_id):
    """Elimina una lectura."""
    lectura = obtener_lectura(lectura_id)
    if not lectura:
        flash('Lectura no encontrada', 'error')
        return redirect(url_for('lecturas.listar'))

    # Verificar si tiene boleta asociada
    boleta = obtener_boleta_por_lectura(lectura_id)
    if boleta:
        flash('No se puede eliminar: esta lectura tiene una boleta asociada', 'error')
        return redirect(url_for('lecturas.detalle', lectura_id=lectura_id))

    # Eliminar foto si existe
    if lectura['foto_path']:
        # foto_path ya incluye 'fotos/', usar BASE_DIR directamente
        foto_completa = os.path.join(BASE_DIR, lectura['foto_path'])
        if os.path.exists(foto_completa):
            os.remove(foto_completa)

    eliminar_lectura(lectura_id)
    flash('Lectura eliminada', 'success')
    return redirect(url_for('lecturas.listar'))


@lecturas_bp.route('/multiple', methods=['GET', 'POST'])
@admin_required
def crear_multiple():
    """Formulario para crear múltiples lecturas a la vez."""
    if request.method == 'POST':
        medidor_id = request.form.get('medidor_id', type=int)
        lectura_m3 = request.form.get('lectura_m3', type=int)
        periodos_json = request.form.get('periodos_data')

        # Validar campos básicos
        if not medidor_id or lectura_m3 is None:
            flash('Medidor y lectura son requeridos', 'error')
            return redirect(url_for('lecturas.crear_multiple'))

        if not periodos_json:
            flash('Debe seleccionar al menos un periodo', 'error')
            return redirect(url_for('lecturas.crear_multiple'))

        try:
            periodos_data = json.loads(periodos_json)
        except json.JSONDecodeError:
            flash('Error en los datos de periodos', 'error')
            return redirect(url_for('lecturas.crear_multiple'))

        if not periodos_data:
            flash('Debe seleccionar al menos un periodo', 'error')
            return redirect(url_for('lecturas.crear_multiple'))

        # Convertir 'anio' a 'año' para compatibilidad con el modelo
        for p in periodos_data:
            if 'anio' in p and 'año' not in p:
                p['año'] = p['anio']

        # Crear las lecturas
        resultado = crear_lecturas_multiple(medidor_id, lectura_m3, periodos_data)

        creados = len(resultado['creados'])
        omitidos = resultado['omitidos']

        if creados > 0 and omitidos > 0:
            flash(f'Se crearon {creados} lecturas. Se omitieron {omitidos} porque ya existian.', 'success')
        elif creados > 0:
            flash(f'Se crearon {creados} lecturas exitosamente', 'success')
        else:
            flash(f'No se crearon lecturas. {omitidos} periodos ya tenian lecturas registradas.', 'warning')

        return redirect(url_for('lecturas.listar'))

    # GET: mostrar formulario
    medidores = listar_medidores()
    años = list(range(2020, datetime.now().year + 2))

    return render_template('lecturas/crear_multiple.html', medidores=medidores, años=años)


@lecturas_bp.route('/api/medidores')
@admin_required
def api_medidores():
    """API para obtener medidores, opcionalmente filtrado por cliente."""
    cliente_id = request.args.get('cliente_id', type=int)
    medidores = listar_medidores(cliente_id) if cliente_id else listar_medidores()

    return jsonify([{
        'id': m['id'],
        'cliente_id': m['cliente_id'],
        'cliente_nombre': m['cliente_nombre'],
        'numero_medidor': m['numero_medidor'],
        'direccion': m['direccion']
    } for m in medidores])


@lecturas_bp.route('/api/fechas-comunes', methods=['POST'])
@admin_required
def api_fechas_comunes():
    """API para obtener las fechas más comunes por periodo."""
    data = request.get_json(force=True)

    if not data or 'periodos' not in data:
        return jsonify({'error': 'Periodos requeridos'}), 400

    # Aceptar tanto 'año' como 'anio' para compatibilidad
    periodos = [(p.get('año') or p.get('anio'), p['mes']) for p in data['periodos']]
    fechas = obtener_fechas_comunes_por_periodo(periodos)

    # Convertir keys de tuplas a strings para JSON
    resultado = []
    todas_encontradas = True

    for (anio, mes), dia in fechas.items():
        if dia is None:
            todas_encontradas = False

        # Calcular mes/año de lectura (mes siguiente)
        if mes == 12:
            mes_lectura = 1
            anio_lectura = anio + 1
        else:
            mes_lectura = mes + 1
            anio_lectura = anio

        resultado.append({
            'anio': anio,
            'mes': mes,
            'dia': dia,
            'mes_lectura': mes_lectura,
            'anio_lectura': anio_lectura
        })

    return jsonify({
        'fechas': resultado,
        'todas_encontradas': todas_encontradas
    })
