"""
Blueprint del Portal de Clientes
Permite a los clientes buscar por RUT, ver boletas pendientes y pagar
"""
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response
from werkzeug.utils import secure_filename
import os
from datetime import date, datetime
from src.database import get_connection, BASE_DIR
from src.models import buscar_cliente_por_rut, listar_medidores, obtener_cliente, obtener_medidor
from src.models_boletas import (
    obtener_boletas_pendientes_por_cliente,
    marcar_boletas_en_revision,
    obtener_boleta,
    obtener_ultimo_rechazo,
    obtener_intento_en_revision
)

portal_bp = Blueprint('portal', __name__)

COMPROBANTES_DIR = os.path.join(BASE_DIR, 'comprobantes')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def allowed_file(filename):
    """Verifica si el archivo tiene una extensión permitida."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def normalizar_rut(rut):
    """Normaliza RUT removiendo puntos y guiones."""
    return rut.replace('.', '').replace('-', '').strip().upper()


def validar_formato_rut(rut):
    """Valida formato básico de RUT chileno (sin verificar dígito)."""
    rut_limpio = normalizar_rut(rut)
    if len(rut_limpio) < 8 or len(rut_limpio) > 9:
        return False
    if not rut_limpio[:-1].isdigit():
        return False
    if not (rut_limpio[-1].isdigit() or rut_limpio[-1] == 'K'):
        return False
    return True


@portal_bp.route('/')
def buscar():
    """Página de búsqueda por RUT."""
    return render_template('portal/buscar_rut.html')


@portal_bp.route('/buscar', methods=['POST'])
def buscar_rut():
    """Busca cliente por RUT y redirige a sus boletas."""
    rut = request.form.get('rut', '').strip()
    numero_medidor = request.form.get('numero_medidor', '').strip()

    if not rut:
        flash('Debe ingresar un RUT', 'error')
        return redirect(url_for('portal.buscar'))

    # Validar formato
    if not validar_formato_rut(rut):
        flash('Formato de RUT inválido', 'error')
        return redirect(url_for('portal.buscar'))

    # Normalizar RUT
    rut_normalizado = normalizar_rut(rut)

    # Buscar cliente
    cliente = buscar_cliente_por_rut(rut_normalizado)

    if not cliente:
        flash('No se encontró cliente con ese RUT', 'error')
        return redirect(url_for('portal.buscar'))

    # Opcional: Validar número de medidor si se proporcionó
    if numero_medidor:
        medidores = listar_medidores(cliente_id=cliente['id'])
        medidor_valido = any(
            m.get('numero_medidor', '').lower() == numero_medidor.lower()
            for m in medidores
        )
        if not medidor_valido:
            flash('Número de medidor no coincide con el RUT', 'error')
            return redirect(url_for('portal.buscar'))

    # Guardar en sesión (simple session-based auth)
    session['cliente_id'] = cliente['id']
    session['cliente_rut'] = rut_normalizado

    return redirect(url_for('portal.mis_boletas'))


@portal_bp.route('/mis-boletas')
def mis_boletas():
    """Lista boletas pendientes del cliente autenticado."""
    cliente_id = session.get('cliente_id')

    if not cliente_id:
        flash('Debe ingresar su RUT primero', 'error')
        return redirect(url_for('portal.buscar'))

    # Obtener cliente
    cliente = obtener_cliente(cliente_id)

    if not cliente:
        session.clear()
        flash('Sesión inválida', 'error')
        return redirect(url_for('portal.buscar'))

    # Obtener boletas (pendientes + en revisión)
    boletas_pendientes = obtener_boletas_pendientes_por_cliente(cliente_id, estado=0)
    boletas_en_revision = obtener_boletas_pendientes_por_cliente(cliente_id, estado=1)

    # Agregar info de último rechazo a cada boleta pendiente
    for boleta in boletas_pendientes:
        ultimo_rechazo = obtener_ultimo_rechazo(boleta['id'])
        boleta['ultimo_rechazo'] = ultimo_rechazo

    # Agregar info del intento actual a cada boleta en revisión
    for boleta in boletas_en_revision:
        intento_actual = obtener_intento_en_revision(boleta['id'])
        boleta['intento_actual'] = intento_actual

    return render_template('portal/mis_boletas.html',
                          cliente=cliente,
                          boletas_pendientes=boletas_pendientes,
                          boletas_en_revision=boletas_en_revision)


@portal_bp.route('/pagar', methods=['POST'])
def pagar():
    """Procesa el pago de boletas seleccionadas con comprobante único."""
    cliente_id = session.get('cliente_id')

    if not cliente_id:
        flash('Debe ingresar su RUT primero', 'error')
        return redirect(url_for('portal.buscar'))

    # Obtener boletas seleccionadas
    boletas_ids = request.form.getlist('boletas')

    if not boletas_ids:
        flash('Debe seleccionar al menos una boleta', 'error')
        return redirect(url_for('portal.mis_boletas'))

    # Validar comprobante
    if 'comprobante' not in request.files:
        flash('Debe adjuntar un comprobante de pago', 'error')
        return redirect(url_for('portal.mis_boletas'))

    file = request.files['comprobante']

    if file.filename == '':
        flash('Debe seleccionar un archivo', 'error')
        return redirect(url_for('portal.mis_boletas'))

    if not allowed_file(file.filename):
        flash('Formato de archivo no permitido. Use PNG, JPG, JPEG, GIF o PDF', 'error')
        return redirect(url_for('portal.mis_boletas'))

    # Validar que todas las boletas pertenecen al cliente
    boletas_validas = []
    for boleta_id in boletas_ids:
        boleta = obtener_boleta(int(boleta_id))
        if not boleta:
            flash(f'Boleta {boleta_id} no encontrada', 'error')
            return redirect(url_for('portal.mis_boletas'))

        # Verificar ownership
        medidor = obtener_medidor(boleta['medidor_id'])
        if medidor['cliente_id'] != cliente_id:
            flash('Error de validación: boleta no pertenece al cliente', 'error')
            return redirect(url_for('portal.mis_boletas'))

        # Verificar que está pendiente (no en revisión ni pagada)
        if boleta['pagada'] != 0:
            flash(f'Boleta {boleta["numero_boleta"]} ya no está pendiente', 'error')
            return redirect(url_for('portal.mis_boletas'))

        boletas_validas.append(boleta)

    # Guardar comprobante ÚNICO (una sola vez para todas las boletas)
    filename = secure_filename(file.filename)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')

    # Directorio: comprobantes/pago_{timestamp}_cliente_{id}/
    pago_dir = os.path.join(COMPROBANTES_DIR, f'pago_{timestamp}_cliente_{cliente_id}')
    os.makedirs(pago_dir, exist_ok=True)

    filepath = os.path.join(pago_dir, filename)

    try:
        file.save(filepath)
    except Exception as e:
        flash('Error al subir archivo. Intente nuevamente.', 'error')
        print(f"Error guardando archivo: {e}")
        return redirect(url_for('portal.mis_boletas'))

    # Ruta relativa (compartida por todas las boletas)
    comprobante_path = f'comprobantes/pago_{timestamp}_cliente_{cliente_id}/{filename}'

    # Marcar boletas como "En Revisión"
    exito = marcar_boletas_en_revision([int(bid) for bid in boletas_ids], comprobante_path)

    if exito:
        flash(f'Pago enviado exitosamente. {len(boletas_ids)} boletas en revisión.', 'success')
        return redirect(url_for('portal.confirmacion'))
    else:
        flash('Error al procesar el pago', 'error')
        return redirect(url_for('portal.mis_boletas'))


@portal_bp.route('/confirmacion')
def confirmacion():
    """Página de confirmación de envío."""
    cliente_id = session.get('cliente_id')
    if not cliente_id:
        return redirect(url_for('portal.buscar'))

    return render_template('portal/confirmacion.html')


@portal_bp.route('/salir')
def salir():
    """Cierra la sesión del cliente."""
    session.clear()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('portal.buscar'))
