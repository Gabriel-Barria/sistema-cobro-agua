"""
Servicio de envio masivo de boletas por WhatsApp
"""
import os
import time
import json
import threading
from io import BytesIO
from datetime import datetime
from typing import Dict, List, Optional
from flask import render_template, current_app
from weasyprint import HTML

from src.database import get_connection
from src.models_configuracion import obtener_periodo_objetivo_generacion
from src.models_boletas import registrar_envio_boleta
from src.services.mensajes_service import enviar_boleta_whatsapp, MensajesError


# Directorio base del proyecto
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Pausa entre envios (segundos) para evitar rate limiting
PAUSA_ENTRE_ENVIOS = 2


def obtener_boletas_periodo_envio(anio: int, mes: int) -> List[Dict]:
    """
    Obtiene boletas del periodo especificado con datos del cliente.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT
            b.id, b.numero_boleta, b.cliente_nombre, b.medidor_id,
            b.periodo_anio, b.periodo_mes, b.lectura_actual, b.lectura_anterior,
            b.consumo_m3, b.cargo_fijo, b.precio_m3, b.subtotal_consumo,
            b.total, b.fecha_emision, b.pagada, b.lectura_id,
            c.id as cliente_id, c.telefono, c.recibe_boleta_whatsapp,
            m.numero_medidor, m.direccion
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE b.periodo_anio = %s
          AND b.periodo_mes = %s
          AND b.pagada = 0
        ORDER BY c.nombre, b.numero_boleta
    ''', (anio, mes))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def verificar_ya_enviada_whatsapp(boleta_id: int, anio: int, mes: int) -> bool:
    """
    Verifica si una boleta ya fue enviada por WhatsApp en el periodo actual.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT COUNT(*) as total
        FROM envios_boletas
        WHERE boleta_id = %s
          AND canal = 'whatsapp'
          AND estado = 'enviado'
    ''', (boleta_id,))

    row = cursor.fetchone()
    conn.close()

    return row['total'] > 0


def obtener_preview_envio() -> Dict:
    """
    Obtiene un preview del envio masivo sin ejecutar.
    """
    anio, mes = obtener_periodo_objetivo_generacion()

    boletas = obtener_boletas_periodo_envio(anio, mes)

    enviables = []
    sin_telefono = []
    no_recibe_wa = []
    ya_enviadas = []

    for boleta in boletas:
        telefono = boleta.get('telefono')
        recibe_wa = boleta.get('recibe_boleta_whatsapp', False)

        if verificar_ya_enviada_whatsapp(boleta['id'], anio, mes):
            ya_enviadas.append(boleta)
        elif not telefono:
            sin_telefono.append(boleta)
        elif not recibe_wa:
            no_recibe_wa.append(boleta)
        else:
            enviables.append(boleta)

    return {
        'periodo_anio': anio,
        'periodo_mes': mes,
        'total_boletas': len(boletas),
        'enviables': enviables,
        'total_enviables': len(enviables),
        'sin_telefono': sin_telefono,
        'total_sin_telefono': len(sin_telefono),
        'no_recibe_wa': no_recibe_wa,
        'total_no_recibe_wa': len(no_recibe_wa),
        'ya_enviadas': ya_enviadas,
        'total_ya_enviadas': len(ya_enviadas)
    }


def hay_proceso_en_curso() -> Optional[Dict]:
    """
    Verifica si hay un proceso de envio masivo en curso.

    Returns:
        Diccionario con datos del proceso en curso o None
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, fecha_ejecucion, periodo_anio, periodo_mes,
               total_boletas, enviadas_exitosas, enviadas_fallidas
        FROM log_envio_masivo
        WHERE estado = 'iniciado'
        ORDER BY fecha_ejecucion DESC
        LIMIT 1
    ''')

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def crear_log_envio_masivo(usuario_id: int, anio: int, mes: int, total_boletas: int = 0, total_enviables: int = 0) -> int:
    """
    Crea un registro de log para el envio masivo.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO log_envio_masivo
        (periodo_anio, periodo_mes, estado, iniciado_por, total_boletas, total_enviables)
        VALUES (%s, %s, 'iniciado', %s, %s, %s)
        RETURNING id
    ''', (anio, mes, usuario_id, total_boletas, total_enviables))

    log_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return log_id


def actualizar_log_envio_masivo(
    log_id: int,
    estado: str = None,
    total_boletas: int = None,
    enviadas_exitosas: int = None,
    enviadas_fallidas: int = None,
    omitidas_sin_telefono: int = None,
    omitidas_no_recibe_wa: int = None,
    omitidas_ya_enviadas: int = None,
    mensaje: str = None,
    detalles: Dict = None,
    duracion_segundos: float = None
):
    """
    Actualiza un registro de log de envio masivo.
    """
    conn = get_connection()
    cursor = conn.cursor()

    # Construir query dinamico solo con campos no nulos
    updates = []
    params = []

    if estado is not None:
        updates.append("estado = %s")
        params.append(estado)
    if total_boletas is not None:
        updates.append("total_boletas = %s")
        params.append(total_boletas)
    if enviadas_exitosas is not None:
        updates.append("enviadas_exitosas = %s")
        params.append(enviadas_exitosas)
    if enviadas_fallidas is not None:
        updates.append("enviadas_fallidas = %s")
        params.append(enviadas_fallidas)
    if omitidas_sin_telefono is not None:
        updates.append("omitidas_sin_telefono = %s")
        params.append(omitidas_sin_telefono)
    if omitidas_no_recibe_wa is not None:
        updates.append("omitidas_no_recibe_wa = %s")
        params.append(omitidas_no_recibe_wa)
    if omitidas_ya_enviadas is not None:
        updates.append("omitidas_ya_enviadas = %s")
        params.append(omitidas_ya_enviadas)
    if mensaje is not None:
        updates.append("mensaje = %s")
        params.append(mensaje)
    if detalles is not None:
        updates.append("detalles = %s")
        params.append(json.dumps(detalles))
    if duracion_segundos is not None:
        updates.append("duracion_segundos = %s")
        params.append(duracion_segundos)

    if updates:
        params.append(log_id)
        cursor.execute(f'''
            UPDATE log_envio_masivo
            SET {', '.join(updates)}
            WHERE id = %s
        ''', params)
        conn.commit()

    conn.close()


def obtener_log_envio(log_id: int) -> Optional[Dict]:
    """
    Obtiene un registro de log de envio masivo.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT l.*, u.nombre_completo as usuario_nombre
        FROM log_envio_masivo l
        LEFT JOIN usuarios u ON l.iniciado_por = u.id
        WHERE l.id = %s
    ''', (log_id,))

    row = cursor.fetchone()
    conn.close()

    if row:
        log = dict(row)
        if log.get('detalles') and isinstance(log['detalles'], str):
            log['detalles'] = json.loads(log['detalles'])
        return log
    return None


def listar_logs_envio(limite: int = 50) -> List[Dict]:
    """
    Lista los ultimos logs de envio masivo.
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT l.id, l.fecha_ejecucion, l.periodo_anio, l.periodo_mes,
               l.total_boletas, l.enviadas_exitosas, l.enviadas_fallidas,
               l.estado, l.duracion_segundos, l.mensaje,
               u.nombre_completo as usuario_nombre
        FROM log_envio_masivo l
        LEFT JOIN usuarios u ON l.iniciado_por = u.id
        ORDER BY l.fecha_ejecucion DESC
        LIMIT %s
    ''', (limite,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def generar_pdf_boleta_standalone(boleta: Dict, app) -> bytes:
    """
    Genera el PDF de una boleta sin contexto de request.
    Se usa dentro del thread de background.
    """
    meses = {
        1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
        5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
        9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }

    # Obtener datos de la lectura actual para la foto y fecha
    foto_lectura = None
    fecha_lectura_actual = None

    if boleta.get('lectura_id'):
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT foto_path, fecha_lectura FROM lecturas WHERE id = %s
        ''', (boleta['lectura_id'],))
        lectura = cursor.fetchone()
        conn.close()

        if lectura:
            if lectura.get('foto_path') and lectura['foto_path'] != '':
                foto_lectura = os.path.join(BASE_DIR, 'web', 'fotos', lectura['foto_path'])
            fecha_lectura_actual = lectura.get('fecha_lectura')

    # Obtener fecha de lectura anterior
    fecha_lectura_anterior = None
    if boleta.get('lectura_anterior') is not None:
        medidor_id = boleta['medidor_id']
        año = boleta['periodo_anio']
        mes = boleta['periodo_mes']

        if mes == 1:
            mes_anterior = 12
            año_anterior = año - 1
        else:
            mes_anterior = mes - 1
            año_anterior = año

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

    # Renderizar template HTML dentro del contexto de la app
    with app.app_context():
        html_string = render_template('boletas/boleta_pdf.html',
                                       boleta=boleta,
                                       meses=meses,
                                       foto_lectura=foto_lectura,
                                       fecha_lectura_actual=fecha_lectura_actual,
                                       fecha_lectura_anterior=fecha_lectura_anterior)

    # Generar PDF usando WeasyPrint
    web_dir = os.path.join(BASE_DIR, 'web')
    pdf_file = BytesIO()
    HTML(string=html_string, base_url=web_dir).write_pdf(pdf_file)
    pdf_file.seek(0)

    return pdf_file.getvalue()


def _ejecutar_envio_en_background(log_id: int, usuario_id: int, app):
    """
    Funcion interna que ejecuta el envio masivo en un thread separado.
    """
    inicio = time.time()

    try:
        anio, mes = obtener_periodo_objetivo_generacion()

        # Obtener preview para clasificar boletas
        preview = obtener_preview_envio()

        detalles = {
            'enviadas': [],
            'fallidas': [],
            'omitidas': []
        }

        # Actualizar log con totales iniciales
        actualizar_log_envio_masivo(
            log_id=log_id,
            total_boletas=preview['total_boletas'],
            omitidas_sin_telefono=preview['total_sin_telefono'],
            omitidas_no_recibe_wa=preview['total_no_recibe_wa'],
            omitidas_ya_enviadas=preview['total_ya_enviadas']
        )

        enviadas_exitosas = 0
        enviadas_fallidas = 0

        # Agregar omitidas a detalles
        for boleta in preview['sin_telefono']:
            detalles['omitidas'].append({
                'boleta_id': boleta['id'],
                'numero_boleta': boleta['numero_boleta'],
                'cliente': boleta['cliente_nombre'],
                'motivo': 'sin_telefono'
            })

        for boleta in preview['no_recibe_wa']:
            detalles['omitidas'].append({
                'boleta_id': boleta['id'],
                'numero_boleta': boleta['numero_boleta'],
                'cliente': boleta['cliente_nombre'],
                'motivo': 'no_recibe_whatsapp'
            })

        for boleta in preview['ya_enviadas']:
            detalles['omitidas'].append({
                'boleta_id': boleta['id'],
                'numero_boleta': boleta['numero_boleta'],
                'cliente': boleta['cliente_nombre'],
                'motivo': 'ya_enviada'
            })

        boletas_enviables = preview['enviables']
        total_enviables = len(boletas_enviables)

        for i, boleta in enumerate(boletas_enviables):
            telefono = boleta['telefono']

            try:
                # Generar PDF
                pdf_bytes = generar_pdf_boleta_standalone(boleta, app)

                # Enviar por WhatsApp
                enviar_boleta_whatsapp(telefono, boleta, pdf_bytes=pdf_bytes)

                # Registrar envio exitoso
                registrar_envio_boleta(
                    boleta_id=boleta['id'],
                    usuario_id=usuario_id,
                    canal='whatsapp',
                    destinatario=telefono,
                    estado='enviado'
                )

                enviadas_exitosas += 1
                detalles['enviadas'].append({
                    'boleta_id': boleta['id'],
                    'numero_boleta': boleta['numero_boleta'],
                    'cliente': boleta['cliente_nombre'],
                    'telefono': telefono
                })

                # Actualizar progreso cada envio
                actualizar_log_envio_masivo(
                    log_id=log_id,
                    enviadas_exitosas=enviadas_exitosas,
                    enviadas_fallidas=enviadas_fallidas,
                    mensaje=f"Enviando... {enviadas_exitosas}/{total_enviables}"
                )

            except MensajesError as e:
                error_msg = str(e)

                # Si es error 429 (rate limit), interrumpir el proceso
                if 'Limite de mensajes excedido' in error_msg:
                    detalles['fallidas'].append({
                        'boleta_id': boleta['id'],
                        'numero_boleta': boleta['numero_boleta'],
                        'cliente': boleta['cliente_nombre'],
                        'error': error_msg
                    })
                    enviadas_fallidas += 1

                    duracion = time.time() - inicio
                    mensaje = f"Interrumpido por limite. Enviadas: {enviadas_exitosas}, Pendientes: {total_enviables - i - 1}"

                    actualizar_log_envio_masivo(
                        log_id=log_id,
                        estado='interrumpido',
                        enviadas_exitosas=enviadas_exitosas,
                        enviadas_fallidas=enviadas_fallidas,
                        mensaje=mensaje,
                        detalles=detalles,
                        duracion_segundos=duracion
                    )
                    return

                # Otro error: registrar y continuar
                registrar_envio_boleta(
                    boleta_id=boleta['id'],
                    usuario_id=usuario_id,
                    canal='whatsapp',
                    destinatario=telefono,
                    estado='fallido',
                    mensaje_error=error_msg
                )

                enviadas_fallidas += 1
                detalles['fallidas'].append({
                    'boleta_id': boleta['id'],
                    'numero_boleta': boleta['numero_boleta'],
                    'cliente': boleta['cliente_nombre'],
                    'error': error_msg
                })

            except Exception as e:
                enviadas_fallidas += 1
                detalles['fallidas'].append({
                    'boleta_id': boleta['id'],
                    'numero_boleta': boleta['numero_boleta'],
                    'cliente': boleta['cliente_nombre'],
                    'error': str(e)
                })

            # Pausa entre envios
            if i < total_enviables - 1:
                time.sleep(PAUSA_ENTRE_ENVIOS)

        # Proceso completado
        duracion = time.time() - inicio
        mensaje = f"Completado: {enviadas_exitosas} exitosas, {enviadas_fallidas} fallidas"

        actualizar_log_envio_masivo(
            log_id=log_id,
            estado='completado',
            enviadas_exitosas=enviadas_exitosas,
            enviadas_fallidas=enviadas_fallidas,
            mensaje=mensaje,
            detalles=detalles,
            duracion_segundos=duracion
        )

    except Exception as e:
        duracion = time.time() - inicio
        actualizar_log_envio_masivo(
            log_id=log_id,
            estado='error',
            mensaje=f"Error: {str(e)}",
            duracion_segundos=duracion
        )


def iniciar_envio_masivo_async(usuario_id: int, app) -> int:
    """
    Inicia el proceso de envio masivo en background.

    Args:
        usuario_id: ID del usuario que ejecuta el proceso
        app: Instancia de la aplicacion Flask

    Returns:
        ID del log creado
    """
    # Verificar si hay proceso en curso
    proceso = hay_proceso_en_curso()
    if proceso:
        raise ValueError(f"Ya hay un proceso en curso (ID: {proceso['id']})")

    anio, mes = obtener_periodo_objetivo_generacion()

    # Obtener preview para saber totales
    preview = obtener_preview_envio()

    # Crear log inicial con total de enviables
    log_id = crear_log_envio_masivo(
        usuario_id, anio, mes,
        total_boletas=preview['total_boletas'],
        total_enviables=preview['total_enviables']
    )

    # Iniciar thread de background
    thread = threading.Thread(
        target=_ejecutar_envio_en_background,
        args=(log_id, usuario_id, app),
        daemon=True
    )
    thread.start()

    return log_id
