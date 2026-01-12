"""
Blueprint del Portal de Clientes
Permite a los clientes buscar por RUT, ver boletas pendientes y pagar
"""
from io import BytesIO
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, make_response, send_file
from werkzeug.utils import secure_filename
from weasyprint import HTML
import os
from datetime import date, datetime
from src.database import get_connection, BASE_DIR
from src.models import buscar_cliente_por_rut, listar_medidores, obtener_cliente, obtener_medidor, obtener_lectura
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


@portal_bp.route('/descargar/<int:boleta_id>')
def descargar_boleta(boleta_id):
    """Descarga PDF de boleta verificando ownership."""
    cliente_id = session.get('cliente_id')
    if not cliente_id:
        flash('Debe ingresar su RUT primero', 'error')
        return redirect(url_for('portal.buscar'))

    # Obtener boleta
    boleta = obtener_boleta(boleta_id)
    if not boleta:
        flash('Boleta no encontrada', 'error')
        return redirect(url_for('portal.mis_boletas'))

    # Verificar ownership
    medidor = obtener_medidor(boleta['medidor_id'])
    if medidor['cliente_id'] != cliente_id:
        flash('Acceso denegado', 'error')
        return redirect(url_for('portal.mis_boletas'))

    # Nombres de meses en espanol
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    # Obtener la lectura actual asociada para la foto del medidor y fecha
    lectura_actual = None
    foto_lectura = None
    fecha_lectura_actual = None
    if boleta['lectura_id']:
        lectura_actual = obtener_lectura(boleta['lectura_id'])
        if lectura_actual:
            if lectura_actual.get('foto_path') and lectura_actual.get('foto_path') != '':
                foto_lectura = os.path.join(BASE_DIR, lectura_actual['foto_path'])
            fecha_lectura_actual = lectura_actual.get('fecha_lectura')

    # Obtener la lectura anterior y su fecha
    fecha_lectura_anterior = None
    if boleta['lectura_anterior'] is not None:
        medidor_id = boleta['medidor_id']
        año = boleta['periodo_año']
        mes = boleta['periodo_mes']

        # Calcular periodo anterior
        if mes == 1:
            mes_anterior = 12
            año_anterior = año - 1
        else:
            mes_anterior = mes - 1
            año_anterior = año

        # Buscar lectura anterior
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT fecha_lectura FROM lecturas
            WHERE medidor_id = %s AND año = %s AND mes = %s
        ''', (medidor_id, año_anterior, mes_anterior))
        lectura_ant = cursor.fetchone()
        conn.close()

        if lectura_ant:
            fecha_lectura_anterior = lectura_ant['fecha_lectura']

    # Renderizar template HTML
    html_string = render_template('boletas/boleta_pdf.html',
                                   boleta=boleta,
                                   meses=meses,
                                   foto_lectura=foto_lectura,
                                   fecha_lectura_actual=fecha_lectura_actual,
                                   fecha_lectura_anterior=fecha_lectura_anterior)

    # Generar PDF usando WeasyPrint
    pdf_file = BytesIO()
    HTML(string=html_string, base_url=BASE_DIR).write_pdf(pdf_file)
    pdf_file.seek(0)

    # Devolver PDF como descarga
    return send_file(
        pdf_file,
        mimetype='application/pdf',
        as_attachment=True,
        download_name=f'boleta_{boleta["numero_boleta"]}.pdf'
    )


@portal_bp.route('/salir')
def salir():
    """Cierra la sesión del cliente."""
    session.clear()
    flash('Sesión cerrada', 'success')
    return redirect(url_for('portal.buscar'))
