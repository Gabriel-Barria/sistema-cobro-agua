"""
Modelos para el sistema de boletas - CRUD desacoplado
"""
from datetime import date
from typing import List, Dict, Optional
from .database import get_connection


# =============================================================================
# CONFIGURACION DE BOLETAS
# =============================================================================

def obtener_configuracion():
    """Obtiene la configuracion activa de boletas."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT id, cargo_fijo, precio_m3, activo, created_at, updated_at
        FROM configuracion_boletas
        WHERE activo = 1
        ORDER BY id DESC
        LIMIT 1
    ''')
    config = cursor.fetchone()
    conn.close()
    return dict(config) if config else None


def guardar_configuracion(cargo_fijo: float, precio_m3: float):
    """Guarda o actualiza la configuracion de boletas."""
    conn = get_connection()
    cursor = conn.cursor()

    # Desactivar configuraciones anteriores
    cursor.execute('UPDATE configuracion_boletas SET activo = 0')

    # Crear nueva configuracion
    cursor.execute('''
        INSERT INTO configuracion_boletas (cargo_fijo, precio_m3, activo)
        VALUES (%s, %s, 1)
        RETURNING id
    ''', (cargo_fijo, precio_m3))

    config_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return config_id


# =============================================================================
# BOLETAS - CRUD
# =============================================================================

def generar_numero_boleta(año: int, mes: int) -> str:
    """Genera un numero de boleta unico formato BOL-YYYYMM-XXXX."""
    conn = get_connection()
    cursor = conn.cursor()

    # Buscar el número máximo existente para ese periodo
    cursor.execute('''
        SELECT numero_boleta FROM boletas
        WHERE periodo_año = %s AND periodo_mes = %s
        ORDER BY numero_boleta DESC
        LIMIT 1
    ''', (año, mes))

    resultado = cursor.fetchone()
    conn.close()

    if resultado:
        # Extraer el número secuencial del formato BOL-YYYYMM-XXXX
        ultimo_numero = resultado['numero_boleta']
        numero_secuencial = int(ultimo_numero.split('-')[-1])
        numero = numero_secuencial + 1
    else:
        # Primera boleta del periodo
        numero = 1

    return f"BOL-{año}{mes:02d}-{numero:04d}"


def crear_boleta(lectura_id: int, cliente_nombre: str, medidor_id: int,
                 periodo_año: int, periodo_mes: int, lectura_actual: int,
                 lectura_anterior: int, consumo_m3: int, cargo_fijo: float,
                 precio_m3: float) -> int:
    """Crea una nueva boleta."""
    conn = get_connection()
    cursor = conn.cursor()

    numero_boleta = generar_numero_boleta(periodo_año, periodo_mes)
    subtotal_consumo = consumo_m3 * precio_m3
    total = cargo_fijo + subtotal_consumo
    fecha_emision = date.today().isoformat()

    cursor.execute('''
        INSERT INTO boletas (
            numero_boleta, lectura_id, cliente_nombre, medidor_id,
            periodo_año, periodo_mes, lectura_actual, lectura_anterior,
            consumo_m3, cargo_fijo, precio_m3, subtotal_consumo, total,
            fecha_emision, pagada
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 0)
        RETURNING id
    ''', (numero_boleta, lectura_id, cliente_nombre, medidor_id,
          periodo_año, periodo_mes, lectura_actual, lectura_anterior,
          consumo_m3, cargo_fijo, precio_m3, subtotal_consumo, total,
          fecha_emision))

    boleta_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()
    return boleta_id


def obtener_boleta(boleta_id: int):
    """Obtiene una boleta por su ID."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT b.*, l.foto_path
        FROM boletas b
        LEFT JOIN lecturas l ON b.lectura_id = l.id
        WHERE b.id = %s
    ''', (boleta_id,))
    boleta = cursor.fetchone()
    conn.close()
    return dict(boleta) if boleta else None


def obtener_boleta_por_lectura(lectura_id: int):
    """Verifica si ya existe una boleta para una lectura."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT id FROM boletas WHERE lectura_id = %s', (lectura_id,))
    boleta = cursor.fetchone()
    conn.close()
    return dict(boleta) if boleta else None


def listar_boletas(cliente_id: int = None, medidor_id: int = None,
                   pagada: int = None, sin_comprobante: bool = False,
                   año: int = None, mes: int = None):
    """Lista boletas con filtros opcionales."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT b.*, m.numero_medidor, c.nombre as cliente_nombre_actual, c.id as cliente_id
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE 1=1
    '''
    params = []

    if cliente_id is not None:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    if medidor_id is not None:
        query += ' AND b.medidor_id = %s'
        params.append(medidor_id)

    if pagada is not None:
        query += ' AND b.pagada = %s'
        params.append(pagada)

    if sin_comprobante:
        query += ' AND b.pagada = 2 AND (b.comprobante_path IS NULL OR b.comprobante_path = \'\')'

    if año is not None:
        query += ' AND b.periodo_año = %s'
        params.append(año)

    if mes is not None:
        query += ' AND b.periodo_mes = %s'
        params.append(mes)

    query += ' ORDER BY b.periodo_año DESC, b.periodo_mes DESC, b.id DESC'

    cursor.execute(query, params)
    boletas = cursor.fetchall()
    conn.close()
    return [dict(b) for b in boletas]


def marcar_boleta_pagada(boleta_id: int, metodo_pago: str) -> bool:
    """Marca una boleta como pagada."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE boletas
        SET pagada = 1, fecha_pago = %s, metodo_pago = %s
        WHERE id = %s
    ''', (date.today().isoformat(), metodo_pago, boleta_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def desmarcar_boleta_pagada(boleta_id: int) -> bool:
    """Desmarca una boleta como pagada, restaurando saldo pendiente."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE boletas
        SET pagada = 0, fecha_pago = NULL, metodo_pago = NULL,
            monto_pagado = 0, saldo_pendiente = total,
            comprobante_path = NULL
        WHERE id = %s
    ''', (boleta_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def guardar_comprobante(boleta_id: int, comprobante_path: str) -> bool:
    """Guarda la ruta del comprobante de pago."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE boletas
        SET comprobante_path = %s
        WHERE id = %s
    ''', (comprobante_path, boleta_id))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


def eliminar_boleta(boleta_id: int) -> bool:
    """Elimina una boleta."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('DELETE FROM boletas WHERE id = %s', (boleta_id,))

    conn.commit()
    affected = cursor.rowcount
    conn.close()
    return affected > 0


# =============================================================================
# FUNCIONES AUXILIARES PARA CALCULO
# =============================================================================

def obtener_lectura_anterior(medidor_id: int, año: int, mes: int):
    """Obtiene la lectura del periodo anterior."""
    conn = get_connection()
    cursor = conn.cursor()

    # Calcular periodo anterior
    if mes == 1:
        mes_anterior = 12
        año_anterior = año - 1
    else:
        mes_anterior = mes - 1
        año_anterior = año

    cursor.execute('''
        SELECT lectura_m3 FROM lecturas
        WHERE medidor_id = %s AND año = %s AND mes = %s
    ''', (medidor_id, año_anterior, mes_anterior))

    lectura = cursor.fetchone()
    conn.close()
    return lectura['lectura_m3'] if lectura else None


def calcular_consumo(lectura_actual: int, lectura_anterior: int) -> int:
    """Calcula el consumo como diferencia entre lecturas."""
    if lectura_anterior is None:
        return lectura_actual
    consumo = lectura_actual - lectura_anterior
    return max(0, consumo)  # No permitir consumo negativo


def obtener_lecturas_sin_boleta(año: int = None, mes: int = None,
                                 cliente_id: int = None):
    """Obtiene lecturas que aun no tienen boleta asociada."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT l.*, m.numero_medidor, c.nombre as cliente_nombre, c.id as cliente_id
        FROM lecturas l
        JOIN medidores m ON l.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        LEFT JOIN boletas b ON l.id = b.lectura_id
        WHERE b.id IS NULL AND m.activo = 1
    '''
    params = []

    if año is not None:
        query += ' AND l.año = %s'
        params.append(año)

    if mes is not None:
        query += ' AND l.mes = %s'
        params.append(mes)

    if cliente_id is not None:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    query += ' ORDER BY l.año DESC, l.mes DESC, c.nombre'

    cursor.execute(query, params)
    lecturas = cursor.fetchall()
    conn.close()
    return [dict(l) for l in lecturas]


def obtener_años_disponibles():
    """Obtiene los años con lecturas disponibles."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT año FROM lecturas ORDER BY año DESC')
    años = [row['año'] for row in cursor.fetchall()]
    conn.close()
    return años


def obtener_estadisticas_boletas(cliente_id: int = None, medidor_id: int = None,
                                  pagada: int = None, sin_comprobante: bool = False,
                                  año: int = None, mes: int = None):
    """Obtiene estadisticas de boletas con filtros opcionales."""
    conn = get_connection()
    cursor = conn.cursor()

    query = '''
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN b.pagada = 2 THEN 1 ELSE 0 END) as pagadas,
            SUM(CASE WHEN b.pagada = 1 THEN 1 ELSE 0 END) as en_revision,
            SUM(CASE WHEN b.pagada = 0 THEN 1 ELSE 0 END) as pendientes,
            SUM(CASE WHEN b.pagada = 2 AND (b.comprobante_path IS NULL OR b.comprobante_path = '') THEN 1 ELSE 0 END) as sin_comprobante,
            SUM(b.total) as monto_total,
            SUM(CASE WHEN b.pagada = 2 THEN b.total ELSE 0 END) as monto_pagado,
            SUM(CASE WHEN b.pagada = 1 THEN b.total ELSE 0 END) as monto_en_revision,
            SUM(CASE WHEN b.pagada = 0 THEN b.total ELSE 0 END) as monto_pendiente
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        WHERE 1=1
    '''
    params = []

    if cliente_id is not None:
        query += ' AND c.id = %s'
        params.append(cliente_id)

    if medidor_id is not None:
        query += ' AND b.medidor_id = %s'
        params.append(medidor_id)

    if pagada is not None:
        query += ' AND b.pagada = %s'
        params.append(pagada)

    if sin_comprobante:
        query += ' AND b.pagada = 2 AND (b.comprobante_path IS NULL OR b.comprobante_path = \'\')'

    if año is not None:
        query += ' AND b.periodo_año = %s'
        params.append(año)

    if mes is not None:
        query += ' AND b.periodo_mes = %s'
        params.append(mes)

    cursor.execute(query, params)
    stats = cursor.fetchone()
    conn.close()
    return dict(stats) if stats else None


def obtener_boletas_pendientes_por_cliente(cliente_id: int, estado: int = 0) -> List[Dict]:
    """
    Obtiene boletas de un cliente por estado.

    Args:
        cliente_id: ID del cliente
        estado: 0 = Pendiente, 1 = En Revisión, 2 = Pagada

    Returns:
        Lista de boletas con info del medidor
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT b.*, m.numero_medidor, m.direccion
        FROM boletas b
        JOIN medidores m ON b.medidor_id = m.id
        WHERE m.cliente_id = %s AND b.pagada = %s
        ORDER BY b.periodo_año DESC, b.periodo_mes DESC
    ''', (cliente_id, estado))

    boletas = cursor.fetchall()
    conn.close()
    return [dict(b) for b in boletas]


def marcar_boletas_en_revision(boleta_ids: List[int], comprobante_path: str) -> bool:
    """
    Marca múltiples boletas como "En Revisión" y crea un pago en el nuevo sistema.

    Transición: Pendiente (0) → En Revisión (1)

    Args:
        boleta_ids: Lista de IDs de boletas
        comprobante_path: Ruta relativa del comprobante compartido

    Returns:
        True si el pago se registró exitosamente
    """
    if not boleta_ids:
        return False

    from decimal import Decimal
    from src.models_pagos import registrar_pago

    conn = get_connection()
    cursor = conn.cursor()

    try:
        # Obtener el cliente_id y calcular el monto total de las boletas
        cursor.execute('''
            SELECT DISTINCT m.cliente_id
            FROM boletas b
            JOIN medidores m ON b.medidor_id = m.id
            WHERE b.id = ANY(%s)
        ''', (boleta_ids,))
        cliente_result = cursor.fetchone()

        if not cliente_result:
            conn.close()
            return False

        cliente_id = cliente_result['cliente_id']

        # Calcular monto total de las boletas seleccionadas
        cursor.execute('''
            SELECT COALESCE(SUM(saldo_pendiente), SUM(total)) as monto_total
            FROM boletas
            WHERE id = ANY(%s) AND pagada = 0
        ''', (boleta_ids,))
        monto_result = cursor.fetchone()
        monto_total = Decimal(str(monto_result['monto_total'])) if monto_result and monto_result['monto_total'] else Decimal('0')

        conn.close()

        if monto_total <= 0:
            return False

        # Usar el nuevo sistema de pagos
        resultado = registrar_pago(
            cliente_id=cliente_id,
            monto_total=monto_total,
            boletas_ids=boleta_ids,
            comprobante_path=comprobante_path,
            metodo_pago='transferencia'
        )

        return resultado.get('pago_id') is not None

    except Exception as e:
        conn.close()
        print(f"Error en marcar_boletas_en_revision: {e}")
        return False


# =============================================================================
# CONSULTAS DE PAGOS (usa tabla pagos)
# =============================================================================

def obtener_ultimo_rechazo(boleta_id: int) -> Optional[Dict]:
    """
    Obtiene el último rechazo de una boleta.

    Args:
        boleta_id: ID de la boleta

    Returns:
        Diccionario con info del rechazo o None si no hay rechazos
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, pb.boleta_id, p.comprobante_path, p.fecha_envio, p.estado,
               p.fecha_procesamiento, p.motivo_rechazo, p.created_at, p.numero_pago
        FROM pagos p
        JOIN pago_boletas pb ON p.id = pb.pago_id
        WHERE pb.boleta_id = %s AND p.estado = 'rechazado'
        ORDER BY p.created_at DESC
        LIMIT 1
    ''', (boleta_id,))
    rechazo = cursor.fetchone()
    conn.close()

    return dict(rechazo) if rechazo else None


def obtener_intento_en_revision(boleta_id: int) -> Optional[Dict]:
    """
    Obtiene el intento actualmente en revisión de una boleta.

    Args:
        boleta_id: ID de la boleta

    Returns:
        Diccionario con info del intento o None si no hay ninguno en revisión
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT p.id, pb.boleta_id, p.comprobante_path, p.fecha_envio, p.estado,
               p.created_at, p.numero_pago
        FROM pagos p
        JOIN pago_boletas pb ON p.id = pb.pago_id
        WHERE pb.boleta_id = %s AND p.estado = 'en_revision'
        ORDER BY p.created_at DESC
        LIMIT 1
    ''', (boleta_id,))
    intento = cursor.fetchone()
    conn.close()

    return dict(intento) if intento else None
