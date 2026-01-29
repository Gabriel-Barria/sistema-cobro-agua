"""
Modelos para configuracion global del sistema
"""
from datetime import date, datetime
from typing import Any, Dict, Optional, Tuple
from src.database import get_connection


def obtener_configuracion(clave: str, default: Any = None) -> Any:
    """Obtiene un valor de configuracion por su clave."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT valor, tipo FROM configuracion_sistema WHERE clave = %s
    ''', (clave,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return default

    return _convertir_valor(row['valor'], row['tipo'])


def _convertir_valor(valor: str, tipo: str) -> Any:
    """Convierte el valor string al tipo correspondiente."""
    if tipo == 'int':
        return int(valor)
    elif tipo == 'float':
        return float(valor)
    elif tipo == 'boolean':
        return valor.lower() in ('true', '1', 'yes', 'si')
    elif tipo == 'json':
        import json
        return json.loads(valor)
    return valor


def obtener_todas_configuraciones() -> Dict[str, Any]:
    """Obtiene todas las configuraciones como diccionario."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT clave, valor, tipo, descripcion FROM configuracion_sistema
        ORDER BY clave
    ''')

    rows = cursor.fetchall()
    conn.close()

    result = {}
    for row in rows:
        result[row['clave']] = {
            'valor': _convertir_valor(row['valor'], row['tipo']),
            'valor_raw': row['valor'],
            'tipo': row['tipo'],
            'descripcion': row['descripcion']
        }

    return result


def guardar_configuracion(clave: str, valor: Any, tipo: str = None) -> None:
    """Guarda o actualiza un valor de configuracion."""
    conn = get_connection()
    cursor = conn.cursor()

    # Si no se especifica tipo, detectarlo
    if tipo is None:
        if isinstance(valor, bool):
            tipo = 'boolean'
            valor = 'true' if valor else 'false'
        elif isinstance(valor, int):
            tipo = 'int'
            valor = str(valor)
        elif isinstance(valor, float):
            tipo = 'float'
            valor = str(valor)
        else:
            tipo = 'string'
            valor = str(valor)
    else:
        valor = str(valor)

    cursor.execute('''
        INSERT INTO configuracion_sistema (clave, valor, tipo, updated_at)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (clave) DO UPDATE SET
            valor = EXCLUDED.valor,
            tipo = EXCLUDED.tipo,
            updated_at = CURRENT_TIMESTAMP
    ''', (clave, valor, tipo))

    conn.commit()
    conn.close()


def guardar_configuraciones_multiple(configuraciones: Dict[str, Any]) -> None:
    """Guarda multiples configuraciones a la vez."""
    for clave, valor in configuraciones.items():
        guardar_configuracion(clave, valor)


def calcular_periodo_para_fecha(fecha: date) -> Tuple[int, int]:
    """
    Calcula el periodo (anio, mes) para una fecha de lectura segun la configuracion.

    Retorna: (anio, mes) del periodo correspondiente
    """
    dia_corte = obtener_configuracion('dia_corte_periodo', 1)
    regla = obtener_configuracion('regla_periodo', 'mes_anterior')

    if regla == 'mes_lectura':
        # El periodo es el mismo mes de la lectura
        return (fecha.year, fecha.month)

    elif regla == 'mes_anterior':
        # El periodo es el mes anterior a la lectura
        if fecha.day < dia_corte:
            # Si es antes del dia de corte, corresponde a 2 meses atras
            if fecha.month == 1:
                return (fecha.year - 1, 12)
            elif fecha.month == 2:
                return (fecha.year - 1, 12)
            else:
                return (fecha.year, fecha.month - 2)
        else:
            # Si es despues del dia de corte, corresponde al mes anterior
            if fecha.month == 1:
                return (fecha.year - 1, 12)
            else:
                return (fecha.year, fecha.month - 1)

    # Default: mes de la lectura
    return (fecha.year, fecha.month)


def obtener_periodo_actual() -> Tuple[int, int]:
    """
    Obtiene el periodo actual basado en la fecha de hoy y la configuracion.

    Retorna: (anio, mes) del periodo actual
    """
    return calcular_periodo_para_fecha(date.today())


def obtener_periodo_objetivo_generacion() -> Tuple[int, int]:
    """
    Obtiene el periodo objetivo para generar boletas.
    Generalmente es el mes anterior al actual.

    Retorna: (anio, mes) del periodo objetivo
    """
    hoy = date.today()

    # El periodo objetivo es el mes anterior
    if hoy.month == 1:
        return (hoy.year - 1, 12)
    else:
        return (hoy.year, hoy.month - 1)


def obtener_fecha_lectura_por_defecto(anio: int, mes: int) -> date:
    """
    Obtiene la fecha de lectura por defecto para un periodo.
    Usa el dia_toma_lectura configurado.

    Args:
        anio: Año del periodo
        mes: Mes del periodo

    Retorna: Fecha de lectura por defecto (mes siguiente al periodo)
    """
    dia_toma = obtener_configuracion('dia_toma_lectura', 5)

    # La lectura se toma el mes siguiente al periodo
    if mes == 12:
        mes_lectura = 1
        anio_lectura = anio + 1
    else:
        mes_lectura = mes + 1
        anio_lectura = anio

    # Validar que el dia sea valido para el mes
    import calendar
    dias_en_mes = calendar.monthrange(anio_lectura, mes_lectura)[1]
    dia_toma = min(dia_toma, dias_en_mes)

    return date(anio_lectura, mes_lectura, dia_toma)


def obtener_datos_bancarios() -> Dict[str, str]:
    """
    Obtiene todos los datos bancarios como diccionario.

    Retorna dict con claves: nombre, cuenta, rut, tipo_cuenta, titular, email
    """
    claves = ['banco_nombre', 'banco_cuenta', 'banco_rut',
              'banco_tipo_cuenta', 'banco_titular', 'banco_email']
    datos = {}
    for clave in claves:
        # Quitar prefijo 'banco_' para las claves del resultado
        clave_corta = clave.replace('banco_', '')
        datos[clave_corta] = obtener_configuracion(clave, '')
    return datos


def guardar_datos_bancarios(datos: Dict[str, str]) -> None:
    """
    Guarda los datos bancarios.

    Args:
        datos: Dict con claves nombre, cuenta, rut, tipo_cuenta, titular, email
    """
    for campo, valor in datos.items():
        guardar_configuracion(f'banco_{campo}', valor, 'string')
