"""
Script de migración - Procesa las fotos existentes y las migra al nuevo sistema
"""
import os
import shutil
from datetime import date
from typing import List, Dict
from .database import inicializar_db, BASE_DIR
from .parser import parsear_nombre_archivo, extraer_periodo_de_ruta, normalizar_nombre
from .validador_fechas import validar_fechas_carpeta
from .models import (
    obtener_o_crear_cliente,
    obtener_o_crear_medidor,
    crear_lectura,
    lectura_existe
)

# Rutas
FOTOS_DIR = os.path.join(BASE_DIR, 'fotos')
LECTURAS_ORIGEN = os.path.join(os.path.dirname(BASE_DIR), 'lecturas')


def obtener_carpetas_mensuales(ruta_base: str) -> List[str]:
    """
    Obtiene todas las carpetas mensuales de lecturas.

    Args:
        ruta_base: Ruta base de lecturas (ej: comprobantes/lecturas)

    Returns:
        Lista de rutas a carpetas mensuales
    """
    carpetas = []

    for año in os.listdir(ruta_base):
        ruta_año = os.path.join(ruta_base, año)
        if not os.path.isdir(ruta_año):
            continue

        for mes in os.listdir(ruta_año):
            ruta_mes = os.path.join(ruta_año, mes)
            if os.path.isdir(ruta_mes):
                carpetas.append(ruta_mes)

    return carpetas


def copiar_foto(origen: str, medidor_id: int, año: int, mes: int, nombre_archivo: str) -> str:
    """
    Copia una foto al directorio organizado por medidor.

    Args:
        origen: Ruta original de la foto
        medidor_id: ID del medidor
        año: Año del periodo
        mes: Mes del periodo
        nombre_archivo: Nombre original del archivo

    Returns:
        Ruta relativa donde se copió la foto
    """
    # Crear estructura de directorios
    destino_dir = os.path.join(FOTOS_DIR, f'medidor_{medidor_id}', str(año), f'{mes:02d}')
    os.makedirs(destino_dir, exist_ok=True)

    # Copiar archivo
    destino = os.path.join(destino_dir, nombre_archivo)
    shutil.copy2(origen, destino)

    # Retornar ruta relativa desde app/
    ruta_relativa = os.path.relpath(destino, BASE_DIR)
    return ruta_relativa.replace('\\', '/')


def obtener_carpeta_fotos(carpeta: str) -> str:
    """
    Obtiene la carpeta real donde están las fotos.
    Algunas carpetas tienen las fotos directamente, otras en una subcarpeta 'lecturas/'.

    Args:
        carpeta: Ruta a la carpeta mensual

    Returns:
        Ruta a la carpeta con las fotos
    """
    # Verificar si existe subcarpeta 'lecturas'
    subcarpeta = os.path.join(carpeta, 'lecturas')
    if os.path.isdir(subcarpeta):
        return subcarpeta
    return carpeta


def procesar_carpeta(carpeta: str, correcciones_fechas: Dict = None) -> Dict:
    """
    Procesa una carpeta mensual de fotos.

    Args:
        carpeta: Ruta a la carpeta
        correcciones_fechas: Dict con correcciones de fecha por archivo (opcional)

    Returns:
        Dict con estadísticas del proceso
    """
    stats = {
        'procesadas': 0,
        'duplicadas': 0,
        'errores': [],
        'corregidas': 0
    }

    # Extraer periodo de la ruta
    periodo = extraer_periodo_de_ruta(carpeta)
    if not periodo:
        stats['errores'].append(f"No se pudo extraer periodo de: {carpeta}")
        return stats

    año_periodo, mes_periodo = periodo

    # Obtener carpeta real con fotos (puede ser subcarpeta 'lecturas')
    carpeta_fotos = obtener_carpeta_fotos(carpeta)

    # Procesar cada foto
    for archivo in os.listdir(carpeta_fotos):
        if not archivo.lower().endswith(('.jpg', '.jpeg', '.png')):
            continue

        ruta_origen = os.path.join(carpeta_fotos, archivo)

        # Parsear nombre del archivo
        datos = parsear_nombre_archivo(archivo)
        if not datos:
            stats['errores'].append(f"No se pudo parsear: {archivo}")
            continue

        nombre_cliente = normalizar_nombre(datos['nombre'])
        lectura_valor = datos['lectura']
        fecha_lectura = datos['fecha']

        # Aplicar corrección de fecha si existe
        if correcciones_fechas and archivo in correcciones_fechas:
            fecha_lectura = correcciones_fechas[archivo]
            stats['corregidas'] += 1

        # Obtener o crear cliente
        cliente_id = obtener_o_crear_cliente(nombre_cliente)

        # Obtener o crear medidor
        medidor_id = obtener_o_crear_medidor(cliente_id)

        # Verificar si ya existe lectura para este periodo
        if lectura_existe(medidor_id, año_periodo, mes_periodo):
            stats['duplicadas'] += 1
            continue

        # Copiar foto al nuevo sistema
        try:
            foto_path = copiar_foto(ruta_origen, medidor_id, año_periodo, mes_periodo, archivo)
        except Exception as e:
            stats['errores'].append(f"Error copiando {archivo}: {str(e)}")
            continue

        # Crear registro de lectura
        crear_lectura(
            medidor_id=medidor_id,
            lectura_m3=lectura_valor,
            fecha_lectura=fecha_lectura,
            foto_path=foto_path,
            foto_nombre=archivo,
            año=año_periodo,
            mes=mes_periodo
        )

        stats['procesadas'] += 1

    return stats


def migrar_todo(ruta_origen: str = None, generar_log: bool = True) -> Dict:
    """
    Ejecuta la migración completa de todas las fotos.

    Args:
        ruta_origen: Ruta base de lecturas (por defecto: lecturas/)
        generar_log: Si generar archivo de log

    Returns:
        Dict con estadísticas totales
    """
    if ruta_origen is None:
        ruta_origen = LECTURAS_ORIGEN

    print(f"Iniciando migración desde: {ruta_origen}")
    print(f"Destino fotos: {FOTOS_DIR}")
    print("-" * 50)

    # Inicializar base de datos
    inicializar_db()

    # Obtener todas las carpetas mensuales
    carpetas = obtener_carpetas_mensuales(ruta_origen)
    print(f"Carpetas encontradas: {len(carpetas)}")

    stats_total = {
        'carpetas': len(carpetas),
        'procesadas': 0,
        'duplicadas': 0,
        'errores': [],
        'corregidas': 0
    }

    log_lines = ["# Log de Migración", ""]

    for i, carpeta in enumerate(carpetas, 1):
        print(f"\n[{i}/{len(carpetas)}] Procesando: {carpeta}")

        # Validar fechas de la carpeta
        validacion = validar_fechas_carpeta(carpeta)

        # Crear diccionario de correcciones
        correcciones = {}
        if validacion['corregidas']:
            for corr in validacion['corregidas']:
                correcciones[corr['archivo']] = corr['fecha_corregida']
            print(f"  - Correcciones de fecha: {len(correcciones)}")

        # Procesar carpeta
        stats = procesar_carpeta(carpeta, correcciones)

        # Acumular estadísticas
        stats_total['procesadas'] += stats['procesadas']
        stats_total['duplicadas'] += stats['duplicadas']
        stats_total['corregidas'] += stats['corregidas']
        stats_total['errores'].extend(stats['errores'])

        print(f"  - Procesadas: {stats['procesadas']}")
        print(f"  - Duplicadas: {stats['duplicadas']}")
        if stats['errores']:
            print(f"  - Errores: {len(stats['errores'])}")

        # Log
        log_lines.append(f"## {carpeta}")
        log_lines.append(f"- Procesadas: {stats['procesadas']}")
        log_lines.append(f"- Duplicadas: {stats['duplicadas']}")
        log_lines.append(f"- Corregidas: {stats['corregidas']}")
        if stats['errores']:
            log_lines.append("- Errores:")
            for err in stats['errores']:
                log_lines.append(f"  - {err}")
        log_lines.append("")

    # Resumen final
    print("\n" + "=" * 50)
    print("MIGRACIÓN COMPLETADA")
    print("=" * 50)
    print(f"Carpetas procesadas: {stats_total['carpetas']}")
    print(f"Fotos migradas: {stats_total['procesadas']}")
    print(f"Duplicadas omitidas: {stats_total['duplicadas']}")
    print(f"Fechas corregidas: {stats_total['corregidas']}")
    print(f"Errores: {len(stats_total['errores'])}")

    # Guardar log
    if generar_log:
        log_lines.append("# Resumen")
        log_lines.append(f"- Total carpetas: {stats_total['carpetas']}")
        log_lines.append(f"- Total procesadas: {stats_total['procesadas']}")
        log_lines.append(f"- Total duplicadas: {stats_total['duplicadas']}")
        log_lines.append(f"- Total corregidas: {stats_total['corregidas']}")
        log_lines.append(f"- Total errores: {len(stats_total['errores'])}")

        log_path = os.path.join(BASE_DIR, 'migracion_log.md')
        with open(log_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(log_lines))
        print(f"\nLog guardado en: {log_path}")

    return stats_total


if __name__ == '__main__':
    migrar_todo()
