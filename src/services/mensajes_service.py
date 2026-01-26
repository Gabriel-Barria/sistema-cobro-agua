"""
Servicio de mensajeria para envio via Sistema Mensajes API.
Soporta WhatsApp y Gmail.
"""
import os
import base64
import requests
from typing import Optional, Dict, Any, Union


MENSAJES_API_URL = os.getenv('MENSAJES_API_URL', 'https://comite-mensajes-api-dev.vk98yo.easypanel.host/api')
MENSAJES_API_KEY = os.getenv('MENSAJES_API_KEY', '')


class MensajesError(Exception):
    """Error al enviar mensaje."""
    pass


def normalizar_telefono(telefono: str) -> str:
    """
    Normaliza numero de telefono al formato internacional.
    Asume numeros chilenos si no tienen codigo de pais.

    Ejemplos:
        912345678 -> +56912345678
        +56912345678 -> +56912345678
        56912345678 -> +56912345678
    """
    if not telefono:
        return ''

    # Limpiar caracteres no numericos excepto +
    limpio = ''.join(c for c in telefono if c.isdigit() or c == '+')

    # Si ya tiene +, retornar tal cual
    if limpio.startswith('+'):
        return limpio

    # Si empieza con 56 (Chile), agregar +
    if limpio.startswith('56') and len(limpio) >= 11:
        return f'+{limpio}'

    # Si es numero de 9 digitos (Chile movil), agregar +56
    if len(limpio) == 9 and limpio[0] == '9':
        return f'+56{limpio}'

    # Por defecto, agregar + si parece internacional
    if len(limpio) >= 10:
        return f'+{limpio}'

    return limpio


def enviar_whatsapp(telefono: str, mensaje: str) -> Dict[str, Any]:
    """
    Envia un mensaje de WhatsApp.

    Args:
        telefono: Numero de telefono del destinatario
        mensaje: Contenido del mensaje

    Returns:
        Dict con resultado del envio (success, messageId, etc.)

    Raises:
        MensajesError: Si hay error en el envio
    """
    if not MENSAJES_API_KEY:
        raise MensajesError('API Key no configurada. Configure MENSAJES_API_KEY en las variables de entorno.')

    telefono_normalizado = normalizar_telefono(telefono)
    if not telefono_normalizado:
        raise MensajesError('Numero de telefono invalido')

    try:
        response = requests.post(
            f'{MENSAJES_API_URL}/send',
            json={
                'channel': 'whatsapp',
                'to': telefono_normalizado,
                'body': mensaje
            },
            headers={
                'X-API-Key': MENSAJES_API_KEY,
                'Content-Type': 'application/json'
            },
            timeout=30
        )

        data = response.json() if response.text else {}

        if response.status_code in (200, 201) and data.get('success'):
            return data
        elif response.status_code == 401:
            raise MensajesError('API Key invalida o expirada')
        elif response.status_code == 403:
            raise MensajesError('No hay conexion de WhatsApp activa en el proyecto')
        elif response.status_code == 429:
            raise MensajesError('Limite de mensajes excedido, intente mas tarde')
        else:
            error_msg = data.get('error', f'Error HTTP {response.status_code}')
            raise MensajesError(error_msg)

    except requests.exceptions.Timeout:
        raise MensajesError('Timeout al conectar con servicio de mensajes')
    except requests.exceptions.ConnectionError:
        raise MensajesError('No se pudo conectar con servicio de mensajes')
    except requests.exceptions.RequestException as e:
        raise MensajesError(f'Error de conexion: {str(e)}')


def enviar_documento_whatsapp(
    telefono: str,
    documento: Union[bytes, str],
    nombre_archivo: str,
    caption: Optional[str] = None
) -> Dict[str, Any]:
    """
    Envia un documento por WhatsApp.

    Args:
        telefono: Numero de telefono del destinatario
        documento: Contenido del documento (bytes) o URL del documento
        nombre_archivo: Nombre del archivo con extension (ej: "boleta.pdf")
        caption: Texto opcional que acompaña al documento

    Returns:
        Dict con resultado del envio

    Raises:
        MensajesError: Si hay error en el envio
    """
    if not MENSAJES_API_KEY:
        raise MensajesError('API Key no configurada. Configure MENSAJES_API_KEY en las variables de entorno.')

    telefono_normalizado = normalizar_telefono(telefono)
    if not telefono_normalizado:
        raise MensajesError('Numero de telefono invalido')

    # Si es bytes, convertir a base64
    if isinstance(documento, bytes):
        media = f"data:application/pdf;base64,{base64.b64encode(documento).decode('utf-8')}"
    else:
        media = documento  # Asumir que es URL

    payload = {
        'channel': 'whatsapp',
        'to': telefono_normalizado,
        'media': media,
        'mediaType': 'document',
        'fileName': nombre_archivo
    }

    if caption:
        payload['caption'] = caption

    try:
        response = requests.post(
            f'{MENSAJES_API_URL}/send',
            json=payload,
            headers={
                'X-API-Key': MENSAJES_API_KEY,
                'Content-Type': 'application/json'
            },
            timeout=60  # Mas tiempo para documentos
        )

        data = response.json() if response.text else {}

        if response.status_code in (200, 201) and data.get('success'):
            return data
        elif response.status_code == 401:
            raise MensajesError('API Key invalida o expirada')
        elif response.status_code == 403:
            raise MensajesError('No hay conexion de WhatsApp activa en el proyecto')
        elif response.status_code == 429:
            raise MensajesError('Limite de mensajes excedido, intente mas tarde')
        else:
            error_msg = data.get('error', f'Error HTTP {response.status_code}')
            raise MensajesError(error_msg)

    except requests.exceptions.Timeout:
        raise MensajesError('Timeout al enviar documento')
    except requests.exceptions.ConnectionError:
        raise MensajesError('No se pudo conectar con servicio de mensajes')
    except requests.exceptions.RequestException as e:
        raise MensajesError(f'Error de conexion: {str(e)}')


def enviar_boleta_whatsapp(
    telefono: str,
    boleta: Dict[str, Any],
    pdf_bytes: Optional[bytes] = None,
    url_portal: Optional[str] = None
) -> Dict[str, Any]:
    """
    Envia notificacion de boleta por WhatsApp, opcionalmente con PDF adjunto.

    Args:
        telefono: Numero de telefono del cliente
        boleta: Diccionario con datos de la boleta
        pdf_bytes: Contenido del PDF en bytes (opcional)
        url_portal: URL opcional del portal de pagos

    Returns:
        Dict con resultado del envio
    """
    # Formatear periodo
    meses = ['', 'Enero', 'Febrero', 'Marzo', 'Abril', 'Mayo', 'Junio',
             'Julio', 'Agosto', 'Septiembre', 'Octubre', 'Noviembre', 'Diciembre']
    periodo = f"{meses[boleta.get('periodo_mes', 1)]} {boleta.get('periodo_año', '')}"

    # Formatear monto
    total = boleta.get('total', 0) or 0
    total_fmt = f"${total:,.0f}".replace(',', '.')

    # Construir mensaje/caption
    mensaje = f"""*Sistema de Agua - Boleta {boleta.get('numero_boleta', '')}*

Periodo: {periodo}
Consumo: {boleta.get('consumo_m3', 0)} m3
*Total a pagar: {total_fmt}*"""

    if url_portal:
        mensaje += f"\n\nPortal de pagos: {url_portal}"

    # Si hay PDF, enviar como documento
    if pdf_bytes:
        nombre_archivo = f"Boleta_{boleta.get('numero_boleta', 'SN')}.pdf"
        return enviar_documento_whatsapp(telefono, pdf_bytes, nombre_archivo, mensaje)

    # Si no hay PDF, enviar solo texto
    return enviar_whatsapp(telefono, mensaje)


def verificar_conexion() -> Dict[str, Any]:
    """
    Verifica el estado de la conexion con el servicio de mensajes.

    Returns:
        Dict con estado de la conexion
    """
    try:
        response = requests.get(
            f'{MENSAJES_API_URL}/health',
            timeout=10
        )
        return {
            'conectado': response.status_code == 200,
            'status': response.status_code,
            'data': response.json() if response.text else {}
        }
    except Exception as e:
        return {
            'conectado': False,
            'error': str(e)
        }
