"""
Rutas para gestión de medidores
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash

from web.auth import admin_required
from src.models import (
    listar_medidores, obtener_medidor, listar_lecturas,
    crear_medidor, actualizar_medidor, eliminar_medidor,
    listar_clientes, desactivar_medidor, reactivar_medidor,
    obtener_estadisticas_medidores
)

medidores_bp = Blueprint('medidores', __name__)


@medidores_bp.route('/')
@admin_required
def listar():
    """Lista todos los medidores con filtros."""
    busqueda = request.args.get('busqueda', '').strip() or None
    estado = request.args.get('estado', '').strip() or None
    cliente_id = request.args.get('cliente_id', type=int) or None

    medidores = listar_medidores(cliente_id=cliente_id, busqueda=busqueda, estado=estado)
    clientes = listar_clientes()
    stats = obtener_estadisticas_medidores(busqueda=busqueda, cliente_id=cliente_id, estado=estado)

    return render_template('medidores/lista.html',
                           medidores=medidores,
                           clientes=clientes,
                           stats=stats,
                           filtros={
                               'busqueda': busqueda or '',
                               'estado': estado or '',
                               'cliente_id': cliente_id or ''
                           })


@medidores_bp.route('/nuevo', methods=['GET', 'POST'])
@admin_required
def crear():
    """Formulario para crear nuevo medidor."""
    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id', type=int)
        numero_medidor = request.form.get('numero_medidor', '').strip() or None
        direccion = request.form.get('direccion', '').strip() or None
        fecha_inicio = request.form.get('fecha_inicio', '').strip() or None

        if not cliente_id:
            flash('Debe seleccionar un cliente', 'error')
            return redirect(url_for('medidores.crear'))

        medidor_id = crear_medidor(cliente_id, numero_medidor, direccion, fecha_inicio)
        flash('Medidor creado exitosamente', 'success')
        return redirect(url_for('medidores.detalle', medidor_id=medidor_id))

    clientes = listar_clientes()
    return render_template('medidores/crear.html', clientes=clientes)


@medidores_bp.route('/<int:medidor_id>')
@admin_required
def detalle(medidor_id):
    """Muestra detalle de un medidor con historial de lecturas."""
    medidor = obtener_medidor(medidor_id)
    if not medidor:
        flash('Medidor no encontrado', 'error')
        return redirect(url_for('medidores.listar'))

    # Obtener historial de lecturas
    lecturas = listar_lecturas(medidor_id=medidor_id, limit=100)

    return render_template('medidores/detalle.html', medidor=medidor, lecturas=lecturas)


@medidores_bp.route('/<int:medidor_id>/editar', methods=['GET', 'POST'])
@admin_required
def editar(medidor_id):
    """Edita datos de un medidor."""
    medidor = obtener_medidor(medidor_id)
    if not medidor:
        flash('Medidor no encontrado', 'error')
        return redirect(url_for('medidores.listar'))

    if request.method == 'POST':
        cliente_id = request.form.get('cliente_id', type=int)
        numero_medidor = request.form.get('numero_medidor', '').strip()
        direccion = request.form.get('direccion', '').strip()

        actualizar_medidor(
            medidor_id,
            numero_medidor=numero_medidor,
            direccion=direccion,
            cliente_id=cliente_id
        )
        flash('Medidor actualizado', 'success')
        return redirect(url_for('medidores.detalle', medidor_id=medidor_id))

    clientes = listar_clientes()
    return render_template('medidores/editar.html', medidor=medidor, clientes=clientes)


@medidores_bp.route('/<int:medidor_id>/eliminar', methods=['POST'])
@admin_required
def eliminar(medidor_id):
    """Elimina un medidor."""
    medidor = obtener_medidor(medidor_id)
    if not medidor:
        flash('Medidor no encontrado', 'error')
        return redirect(url_for('medidores.listar'))

    exito, motivo = eliminar_medidor(medidor_id)

    if exito:
        flash('Medidor eliminado exitosamente', 'success')
    elif motivo == "lecturas":
        flash('No se puede eliminar el medidor porque tiene lecturas asociadas', 'error')
    elif motivo == "boletas":
        flash('No se puede eliminar el medidor porque tiene boletas asociadas', 'error')
    else:
        flash('Error al eliminar el medidor', 'error')

    return redirect(url_for('medidores.listar'))


@medidores_bp.route('/<int:medidor_id>/desactivar', methods=['POST'])
@admin_required
def desactivar(medidor_id):
    """Desactiva un medidor."""
    medidor = obtener_medidor(medidor_id)
    if not medidor:
        flash('Medidor no encontrado', 'error')
        return redirect(url_for('medidores.listar'))

    if medidor.get('activo') == 0:
        flash('El medidor ya esta inactivo', 'warning')
        return redirect(url_for('medidores.detalle', medidor_id=medidor_id))

    fecha_baja = request.form.get('fecha_baja', '').strip()
    motivo_baja = request.form.get('motivo_baja', '').strip() or None

    if not fecha_baja:
        flash('Debe proporcionar una fecha de baja', 'error')
        return redirect(url_for('medidores.detalle', medidor_id=medidor_id))

    if desactivar_medidor(medidor_id, fecha_baja, motivo_baja):
        flash('Medidor desactivado exitosamente', 'success')
    else:
        flash('Error al desactivar el medidor', 'error')

    return redirect(url_for('medidores.detalle', medidor_id=medidor_id))


@medidores_bp.route('/<int:medidor_id>/reactivar', methods=['POST'])
@admin_required
def reactivar(medidor_id):
    """Reactiva un medidor."""
    medidor = obtener_medidor(medidor_id)
    if not medidor:
        flash('Medidor no encontrado', 'error')
        return redirect(url_for('medidores.listar'))

    if medidor.get('activo') == 1:
        flash('El medidor ya esta activo', 'warning')
        return redirect(url_for('medidores.detalle', medidor_id=medidor_id))

    fecha_inicio = request.form.get('fecha_inicio', '').strip() or None

    if reactivar_medidor(medidor_id, fecha_inicio):
        flash('Medidor reactivado exitosamente', 'success')
    else:
        flash('Error al reactivar el medidor', 'error')

    return redirect(url_for('medidores.detalle', medidor_id=medidor_id))
