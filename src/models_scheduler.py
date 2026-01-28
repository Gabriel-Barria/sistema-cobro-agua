"""
Modelos para configuracion de scheduler y logs de generacion
"""
import json
from datetime import datetime, time
from typing import Any, Dict, List, Optional
from src.database import get_connection


# ============================================================
# CONFIGURACION CRON
# ============================================================

def obtener_cron_config(nombre: str = 'generacion_boletas') -> Optional[Dict]:
    """Obtiene la configuracion de un cron por nombre."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, nombre, tipo_programacion, dia_mes, intervalo_dias,
               hora_ejecucion, activo, ultima_ejecucion, created_at, updated_at
        FROM configuracion_cron
        WHERE nombre = %s
    ''', (nombre,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    return {
        'id': row['id'],
        'nombre': row['nombre'],
        'tipo_programacion': row['tipo_programacion'],
        'dia_mes': row['dia_mes'],
        'intervalo_dias': row['intervalo_dias'],
        'hora_ejecucion': row['hora_ejecucion'],
        'activo': row['activo'],
        'ultima_ejecucion': row['ultima_ejecucion'],
        'created_at': row['created_at'],
        'updated_at': row['updated_at']
    }


def guardar_cron_config(
    nombre: str,
    tipo_programacion: str,
    dia_mes: Optional[int] = None,
    intervalo_dias: Optional[int] = None,
    hora_ejecucion: time = time(8, 0),
    activo: bool = True
) -> int:
    """Guarda o actualiza la configuracion de un cron."""
    conn = get_connection()
    cursor = conn.cursor()

    # Convertir hora a string si es necesario
    if isinstance(hora_ejecucion, time):
        hora_str = hora_ejecucion.strftime('%H:%M:%S')
    else:
        hora_str = str(hora_ejecucion)

    cursor.execute('''
        INSERT INTO configuracion_cron (
            nombre, tipo_programacion, dia_mes, intervalo_dias,
            hora_ejecucion, activo, updated_at
        ) VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
        ON CONFLICT (nombre) DO UPDATE SET
            tipo_programacion = EXCLUDED.tipo_programacion,
            dia_mes = EXCLUDED.dia_mes,
            intervalo_dias = EXCLUDED.intervalo_dias,
            hora_ejecucion = EXCLUDED.hora_ejecucion,
            activo = EXCLUDED.activo,
            updated_at = CURRENT_TIMESTAMP
        RETURNING id
    ''', (nombre, tipo_programacion, dia_mes, intervalo_dias, hora_str, activo))

    result = cursor.fetchone()
    cron_id = result[0] if result else None

    conn.commit()
    conn.close()

    return cron_id


def actualizar_ultima_ejecucion(nombre: str = 'generacion_boletas') -> None:
    """Actualiza la fecha de ultima ejecucion del cron."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE configuracion_cron
        SET ultima_ejecucion = CURRENT_TIMESTAMP, updated_at = CURRENT_TIMESTAMP
        WHERE nombre = %s
    ''', (nombre,))

    conn.commit()
    conn.close()


def activar_cron(nombre: str, activo: bool = True) -> None:
    """Activa o desactiva un cron."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        UPDATE configuracion_cron
        SET activo = %s, updated_at = CURRENT_TIMESTAMP
        WHERE nombre = %s
    ''', (activo, nombre))

    conn.commit()
    conn.close()


# ============================================================
# LOGS DE GENERACION
# ============================================================

def crear_log_generacion(
    usuario_id: Optional[int] = None,
    es_automatico: bool = True,
    periodo_anio: Optional[int] = None,
    periodo_mes: Optional[int] = None
) -> int:
    """Crea un nuevo registro de log de generacion."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        INSERT INTO log_generacion_boletas (
            fecha_ejecucion, periodo_anio, periodo_mes, estado,
            iniciado_por, es_automatico
        ) VALUES (CURRENT_TIMESTAMP, %s, %s, 'iniciado', %s, %s)
        RETURNING id
    ''', (periodo_anio, periodo_mes, usuario_id, es_automatico))

    result = cursor.fetchone()
    log_id = result[0]

    conn.commit()
    conn.close()

    return log_id


def actualizar_log_generacion(
    log_id: int,
    estado: str,
    lecturas_creadas: int = 0,
    boletas_generadas: int = 0,
    errores: int = 0,
    mensaje: Optional[str] = None,
    detalles: Optional[Dict] = None,
    duracion_segundos: Optional[float] = None
) -> None:
    """Actualiza un registro de log de generacion."""
    conn = get_connection()
    cursor = conn.cursor()

    detalles_json = json.dumps(detalles) if detalles else None

    cursor.execute('''
        UPDATE log_generacion_boletas
        SET estado = %s,
            lecturas_creadas = %s,
            boletas_generadas = %s,
            errores = %s,
            mensaje = %s,
            detalles = %s,
            duracion_segundos = %s
        WHERE id = %s
    ''', (estado, lecturas_creadas, boletas_generadas, errores,
          mensaje, detalles_json, duracion_segundos, log_id))

    conn.commit()
    conn.close()


def listar_logs_generacion(limit: int = 50, offset: int = 0) -> List[Dict]:
    """Lista los logs de generacion ordenados por fecha."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT l.id, l.fecha_ejecucion, l.periodo_anio, l.periodo_mes,
               l.lecturas_creadas, l.boletas_generadas, l.errores,
               l.estado, l.mensaje, l.detalles, l.duracion_segundos,
               l.iniciado_por, l.es_automatico, u.nombre_completo as usuario_nombre
        FROM log_generacion_boletas l
        LEFT JOIN usuarios u ON l.iniciado_por = u.id
        ORDER BY l.fecha_ejecucion DESC
        LIMIT %s OFFSET %s
    ''', (limit, offset))

    rows = cursor.fetchall()
    conn.close()

    logs = []
    for row in rows:
        detalles = row['detalles']
        if isinstance(detalles, str):
            try:
                detalles = json.loads(detalles)
            except:
                pass

        logs.append({
            'id': row['id'],
            'fecha_ejecucion': row['fecha_ejecucion'],
            'periodo_anio': row['periodo_anio'],
            'periodo_mes': row['periodo_mes'],
            'lecturas_creadas': row['lecturas_creadas'],
            'boletas_generadas': row['boletas_generadas'],
            'errores': row['errores'],
            'estado': row['estado'],
            'mensaje': row['mensaje'],
            'detalles': detalles,
            'duracion_segundos': float(row['duracion_segundos']) if row['duracion_segundos'] else None,
            'iniciado_por': row['iniciado_por'],
            'es_automatico': row['es_automatico'],
            'usuario_nombre': row['usuario_nombre']
        })

    return logs


def obtener_log_generacion(log_id: int) -> Optional[Dict]:
    """Obtiene un log de generacion por ID."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('''
        SELECT l.id, l.fecha_ejecucion, l.periodo_anio, l.periodo_mes,
               l.lecturas_creadas, l.boletas_generadas, l.errores,
               l.estado, l.mensaje, l.detalles, l.duracion_segundos,
               l.iniciado_por, l.es_automatico, u.nombre_completo as usuario_nombre
        FROM log_generacion_boletas l
        LEFT JOIN usuarios u ON l.iniciado_por = u.id
        WHERE l.id = %s
    ''', (log_id,))

    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    detalles = row['detalles']
    if isinstance(detalles, str):
        try:
            detalles = json.loads(detalles)
        except:
            pass

    return {
        'id': row['id'],
        'fecha_ejecucion': row['fecha_ejecucion'],
        'periodo_anio': row['periodo_anio'],
        'periodo_mes': row['periodo_mes'],
        'lecturas_creadas': row['lecturas_creadas'],
        'boletas_generadas': row['boletas_generadas'],
        'errores': row['errores'],
        'estado': row['estado'],
        'mensaje': row['mensaje'],
        'detalles': detalles,
        'duracion_segundos': float(row['duracion_segundos']) if row['duracion_segundos'] else None,
        'iniciado_por': row['iniciado_por'],
        'es_automatico': row['es_automatico'],
        'usuario_nombre': row['usuario_nombre']
    }


def contar_logs_generacion() -> int:
    """Cuenta el total de logs de generacion."""
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute('SELECT COUNT(*) FROM log_generacion_boletas')
    count = cursor.fetchone()[0]

    conn.close()

    return count
