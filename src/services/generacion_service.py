"""
Servicio de generacion automatica de lecturas y boletas
"""
import time
from datetime import date
from typing import Dict, List, Optional, Tuple
from src.database import get_connection
from src.models_configuracion import (
    obtener_configuracion,
    obtener_periodo_objetivo_generacion,
    obtener_fecha_lectura_por_defecto
)
from src.models_scheduler import (
    crear_log_generacion,
    actualizar_log_generacion,
    actualizar_ultima_ejecucion
)
from src.models_boletas import (
    obtener_configuracion as obtener_config_boletas,
    obtener_lectura_anterior,
    calcular_consumo,
    crear_boleta
)


def obtener_medidores_sin_lectura(año: int, mes: int) -> List[Dict]:
    """
    Obtiene medidores activos que no tienen lectura para el periodo especificado.

    Args:
        año: Año del periodo
        mes: Mes del periodo

    Returns:
        Lista de medidores sin lectura
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT m.id, m.numero_medidor, m.direccion, m.cliente_id,
               c.nombre as cliente_nombre
        FROM medidores m
        JOIN clientes c ON m.cliente_id = c.id
        WHERE m.activo = 1
          AND c.activo = 1
          AND NOT EXISTS (
              SELECT 1 FROM lecturas l
              WHERE l.medidor_id = m.id
                AND l.año = %s
                AND l.mes = %s
          )
        ORDER BY c.nombre, m.numero_medidor
    ''', (año, mes))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_ultima_lectura_medidor(medidor_id: int) -> Optional[Dict]:
    """
    Obtiene la ultima lectura de un medidor.

    Args:
        medidor_id: ID del medidor

    Returns:
        Diccionario con la ultima lectura o None
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, lectura_m3, fecha_lectura, año, mes
        FROM lecturas
        WHERE medidor_id = %s
        ORDER BY año DESC, mes DESC, id DESC
        LIMIT 1
    ''', (medidor_id,))

    row = cursor.fetchone()
    conn.close()

    return dict(row) if row else None


def obtener_ultimas_dos_lecturas_medidor(medidor_id: int) -> List[Dict]:
    """
    Obtiene las ultimas 2 lecturas de un medidor para calcular consumo.

    Args:
        medidor_id: ID del medidor

    Returns:
        Lista con las ultimas 2 lecturas (puede tener 0, 1 o 2 elementos)
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, lectura_m3, fecha_lectura, año, mes
        FROM lecturas
        WHERE medidor_id = %s
        ORDER BY año DESC, mes DESC, id DESC
        LIMIT 2
    ''', (medidor_id,))

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def obtener_ultimo_consumo_boleta(medidor_id: int) -> Optional[int]:
    """
    Obtiene el consumo de la ultima boleta de un medidor.

    Args:
        medidor_id: ID del medidor

    Returns:
        Consumo en m3 de la ultima boleta o None si no hay boletas
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT consumo_m3
        FROM boletas
        WHERE medidor_id = %s
        ORDER BY periodo_anio DESC, periodo_mes DESC, id DESC
        LIMIT 1
    ''', (medidor_id,))

    row = cursor.fetchone()
    conn.close()

    return row['consumo_m3'] if row else None


def calcular_consumo_estimado(medidor_id: int) -> int:
    """
    Calcula el consumo estimado para un medidor.

    Prioridad:
    1. Consumo de la ultima boleta
    2. Diferencia entre las ultimas 2 lecturas
    3. Valor de la unica lectura (medidor nuevo)

    Args:
        medidor_id: ID del medidor

    Returns:
        Consumo estimado en m3
    """
    # Prioridad 1: Buscar consumo de la ultima boleta
    consumo_ultima_boleta = obtener_ultimo_consumo_boleta(medidor_id)

    if consumo_ultima_boleta is not None:
        consumo = consumo_ultima_boleta
    else:
        # Prioridad 2 y 3: Calcular desde lecturas
        lecturas = obtener_ultimas_dos_lecturas_medidor(medidor_id)

        if len(lecturas) >= 2:
            # Diferencia entre las ultimas 2 lecturas
            consumo = lecturas[0]['lectura_m3'] - lecturas[1]['lectura_m3']
        elif len(lecturas) == 1:
            # Medidor nuevo: consumo = lectura - 0
            consumo = lecturas[0]['lectura_m3']
        else:
            # Sin lecturas
            consumo = 0

    # Si el consumo es negativo, usamos 0
    return max(consumo, 0)


def calcular_lectura_estimada(medidor_id: int) -> int:
    """
    Calcula el valor estimado para una lectura faltante.

    Formula: ultima_lectura + consumo_estimado

    Ejemplo:
    - Enero: lectura 50 m3, consumo 50 m3
    - Febrero: sin lectura
    - Lectura estimada = 50 + 50 = 100 m3

    Args:
        medidor_id: ID del medidor

    Returns:
        Valor estimado de la lectura en m3
    """
    ultima_lectura = obtener_ultima_lectura_medidor(medidor_id)

    if not ultima_lectura:
        return 0

    valor_ultima_lectura = ultima_lectura['lectura_m3']
    consumo_estimado = calcular_consumo_estimado(medidor_id)

    return valor_ultima_lectura + consumo_estimado


def crear_lectura_automatica(
    medidor_id: int,
    lectura_m3: int,
    fecha_lectura: date,
    año: int,
    mes: int
) -> int:
    """
    Crea una lectura automatica para un medidor.

    Args:
        medidor_id: ID del medidor
        lectura_m3: Valor de la lectura en m3
        fecha_lectura: Fecha de la lectura
        año: Año del periodo
        mes: Mes del periodo

    Returns:
        ID de la lectura creada
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO lecturas (medidor_id, lectura_m3, fecha_lectura, foto_path, foto_nombre, año, mes)
        VALUES (%s, %s, %s, '', 'generacion_automatica', %s, %s)
        RETURNING id
    ''', (medidor_id, lectura_m3, fecha_lectura, año, mes))

    lectura_id = cursor.fetchone()[0]
    conn.commit()
    conn.close()

    return lectura_id


def obtener_lecturas_sin_boleta_todas() -> List[Dict]:
    """
    Obtiene todas las lecturas que no tienen boleta asociada.

    Returns:
        Lista de lecturas sin boleta
    """
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT l.id, l.medidor_id, l.lectura_m3, l.fecha_lectura, l.año, l.mes,
               m.numero_medidor, m.direccion, c.id as cliente_id, c.nombre as cliente_nombre
        FROM lecturas l
        JOIN medidores m ON l.medidor_id = m.id
        JOIN clientes c ON m.cliente_id = c.id
        LEFT JOIN boletas b ON l.id = b.lectura_id
        WHERE b.id IS NULL AND m.activo = 1
        ORDER BY l.año DESC, l.mes DESC, c.nombre
    ''')

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]


def generar_boleta_desde_lectura(lectura: Dict, config_boletas: Dict) -> Optional[int]:
    """
    Genera una boleta a partir de una lectura.

    Args:
        lectura: Diccionario con datos de la lectura
        config_boletas: Configuracion de tarifas

    Returns:
        ID de la boleta creada o None si fallo
    """
    try:
        medidor_id = lectura['medidor_id']
        año = lectura['año']
        mes = lectura['mes']
        lectura_actual = lectura['lectura_m3']
        cliente_nombre = lectura['cliente_nombre']

        # Obtener lectura anterior
        lectura_anterior = obtener_lectura_anterior(medidor_id, año, mes)
        if lectura_anterior is None:
            lectura_anterior = 0

        # Calcular consumo
        consumo = calcular_consumo(lectura_actual, lectura_anterior)

        # Crear boleta
        boleta_id = crear_boleta(
            lectura_id=lectura['id'],
            cliente_nombre=cliente_nombre,
            medidor_id=medidor_id,
            periodo_anio=año,
            periodo_mes=mes,
            lectura_actual=lectura_actual,
            lectura_anterior=lectura_anterior,
            consumo_m3=consumo,
            cargo_fijo=float(config_boletas['cargo_fijo']),
            precio_m3=float(config_boletas['precio_m3'])
        )

        return boleta_id

    except Exception as e:
        print(f"Error generando boleta para lectura {lectura.get('id')}: {e}")
        return None


def obtener_preview_generacion() -> Dict:
    """
    Obtiene un preview de lo que se generaria sin ejecutar realmente.

    Returns:
        Diccionario con estadisticas del preview
    """
    año, mes = obtener_periodo_objetivo_generacion()
    crear_lecturas = obtener_configuracion('crear_lecturas_faltantes', True)

    # Medidores sin lectura
    medidores_sin_lectura = []
    if crear_lecturas:
        medidores_sin_lectura = obtener_medidores_sin_lectura(año, mes)

    # Lecturas sin boleta
    lecturas_sin_boleta = obtener_lecturas_sin_boleta_todas()

    return {
        'periodo_anio': año,
        'periodo_mes': mes,
        'crear_lecturas_habilitado': crear_lecturas,
        'medidores_sin_lectura': medidores_sin_lectura,
        'total_medidores_sin_lectura': len(medidores_sin_lectura),
        'lecturas_sin_boleta': lecturas_sin_boleta,
        'total_lecturas_sin_boleta': len(lecturas_sin_boleta)
    }


def ejecutar_generacion(
    usuario_id: Optional[int] = None,
    es_automatico: bool = True,
    solo_boletas: bool = False
) -> Dict:
    """
    Ejecuta el proceso de generacion automatica de lecturas y boletas.

    Args:
        usuario_id: ID del usuario que inicia el proceso (None si es automatico)
        es_automatico: True si es ejecucion automatica por cron
        solo_boletas: True para solo generar boletas (no crear lecturas)

    Returns:
        Diccionario con resultados de la ejecucion
    """
    inicio = time.time()
    año, mes = obtener_periodo_objetivo_generacion()

    # Crear log de ejecucion
    log_id = crear_log_generacion(
        usuario_id=usuario_id,
        es_automatico=es_automatico,
        periodo_anio=año,
        periodo_mes=mes
    )

    resultado = {
        'log_id': log_id,
        'periodo_anio': año,
        'periodo_mes': mes,
        'lecturas_creadas': 0,
        'boletas_generadas': 0,
        'errores': 0,
        'detalles': {
            'lecturas': [],
            'boletas': [],
            'errores': []
        }
    }

    try:
        # PASO 1: Crear lecturas faltantes
        crear_lecturas = obtener_configuracion('crear_lecturas_faltantes', True)
        valor_lectura = obtener_configuracion('valor_lectura_faltante', 'ultima')

        if crear_lecturas and not solo_boletas:
            medidores = obtener_medidores_sin_lectura(año, mes)
            fecha_lectura = obtener_fecha_lectura_por_defecto(año, mes)

            for medidor in medidores:
                try:
                    # Determinar valor de la lectura
                    if valor_lectura == 'ultima':
                        # Calcular lectura estimada = ultima lectura + consumo anterior
                        lectura_m3 = calcular_lectura_estimada(medidor['id'])
                    else:
                        # Consumo cero: copiar la ultima lectura (consumo = 0)
                        ultima = obtener_ultima_lectura_medidor(medidor['id'])
                        lectura_m3 = ultima['lectura_m3'] if ultima else 0

                    # Crear lectura
                    lectura_id = crear_lectura_automatica(
                        medidor_id=medidor['id'],
                        lectura_m3=lectura_m3,
                        fecha_lectura=fecha_lectura,
                        año=año,
                        mes=mes
                    )

                    resultado['lecturas_creadas'] += 1
                    resultado['detalles']['lecturas'].append({
                        'medidor_id': medidor['id'],
                        'medidor': medidor['numero_medidor'] or 'Sin número',
                        'cliente': medidor['cliente_nombre'],
                        'lectura_id': lectura_id,
                        'lectura_m3': lectura_m3
                    })

                except Exception as e:
                    resultado['errores'] += 1
                    resultado['detalles']['errores'].append({
                        'tipo': 'lectura',
                        'medidor_id': medidor['id'],
                        'error': str(e)
                    })

        # PASO 2: Generar boletas
        config_boletas = obtener_config_boletas()
        if not config_boletas:
            raise ValueError("No hay configuracion de tarifas activa")

        lecturas = obtener_lecturas_sin_boleta_todas()

        for lectura in lecturas:
            try:
                boleta_id = generar_boleta_desde_lectura(lectura, config_boletas)

                if boleta_id:
                    resultado['boletas_generadas'] += 1
                    resultado['detalles']['boletas'].append({
                        'boleta_id': boleta_id,
                        'lectura_id': lectura['id'],
                        'cliente': lectura['cliente_nombre'],
                        'medidor': lectura['numero_medidor'] or 'Sin número',
                        'periodo': f"{lectura['mes']}/{lectura['año']}"
                    })
                else:
                    resultado['errores'] += 1
                    resultado['detalles']['errores'].append({
                        'tipo': 'boleta',
                        'lectura_id': lectura['id'],
                        'error': 'No se pudo crear la boleta'
                    })

            except Exception as e:
                resultado['errores'] += 1
                resultado['detalles']['errores'].append({
                    'tipo': 'boleta',
                    'lectura_id': lectura['id'],
                    'error': str(e)
                })

        # Actualizar log con resultados
        duracion = time.time() - inicio
        estado = 'completado' if resultado['errores'] == 0 else 'completado'
        mensaje = f"Generacion completada: {resultado['lecturas_creadas']} lecturas, {resultado['boletas_generadas']} boletas"

        if resultado['errores'] > 0:
            mensaje += f", {resultado['errores']} errores"

        actualizar_log_generacion(
            log_id=log_id,
            estado=estado,
            lecturas_creadas=resultado['lecturas_creadas'],
            boletas_generadas=resultado['boletas_generadas'],
            errores=resultado['errores'],
            mensaje=mensaje,
            detalles=resultado['detalles'],
            duracion_segundos=duracion
        )

        # Actualizar ultima ejecucion del cron
        if es_automatico:
            actualizar_ultima_ejecucion('generacion_boletas')

        resultado['estado'] = estado
        resultado['mensaje'] = mensaje
        resultado['duracion_segundos'] = duracion

    except Exception as e:
        duracion = time.time() - inicio
        actualizar_log_generacion(
            log_id=log_id,
            estado='error',
            lecturas_creadas=resultado['lecturas_creadas'],
            boletas_generadas=resultado['boletas_generadas'],
            errores=resultado['errores'] + 1,
            mensaje=f"Error en generacion: {str(e)}",
            detalles=resultado['detalles'],
            duracion_segundos=duracion
        )
        resultado['estado'] = 'error'
        resultado['mensaje'] = str(e)
        resultado['duracion_segundos'] = duracion

    return resultado
