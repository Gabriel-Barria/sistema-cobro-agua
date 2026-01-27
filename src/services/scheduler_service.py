"""
Servicio de APScheduler para tareas programadas
"""
import os
import logging
from datetime import datetime
from typing import Optional
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.executors.pool import ThreadPoolExecutor

logger = logging.getLogger(__name__)

# Scheduler global
_scheduler: Optional[BackgroundScheduler] = None


def get_scheduler() -> BackgroundScheduler:
    """Obtiene la instancia global del scheduler."""
    global _scheduler
    if _scheduler is None:
        raise RuntimeError("Scheduler no inicializado. Llama a init_scheduler primero.")
    return _scheduler


def init_scheduler(app=None) -> BackgroundScheduler:
    """
    Inicializa el scheduler con configuracion de PostgreSQL.

    Args:
        app: Instancia de Flask app (opcional, para obtener config de DB)

    Returns:
        Instancia del BackgroundScheduler
    """
    global _scheduler

    if _scheduler is not None:
        logger.info("Scheduler ya inicializado")
        return _scheduler

    # Obtener URL de la base de datos
    database_url = os.environ.get('DATABASE_URL', 'postgresql://postgres:postgres@localhost:5432/agua_db')

    # SQLAlchemy requiere 'postgresql://' no 'postgres://'
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)

    # Configurar jobstore con PostgreSQL
    jobstores = {
        'default': SQLAlchemyJobStore(url=database_url)
    }

    executors = {
        'default': ThreadPoolExecutor(2)
    }

    job_defaults = {
        'coalesce': True,  # Combinar ejecuciones perdidas en una sola
        'max_instances': 1,  # Solo una instancia del job a la vez
        'misfire_grace_time': 3600  # 1 hora de gracia para jobs perdidos
    }

    _scheduler = BackgroundScheduler(
        jobstores=jobstores,
        executors=executors,
        job_defaults=job_defaults,
        timezone='America/Santiago'
    )

    logger.info("Scheduler inicializado correctamente")
    return _scheduler


def start_scheduler():
    """Inicia el scheduler si no esta corriendo."""
    global _scheduler

    if _scheduler is None:
        init_scheduler()

    if not _scheduler.running:
        _scheduler.start()
        logger.info("Scheduler iniciado")

        # Programar job de generacion si esta activo
        _setup_generacion_job()


def shutdown_scheduler():
    """Detiene el scheduler."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Scheduler detenido")


def _setup_generacion_job():
    """Configura el job de generacion de boletas segun la configuracion."""
    from src.models_scheduler import obtener_cron_config

    try:
        config = obtener_cron_config('generacion_boletas')
        if not config:
            logger.info("No hay configuracion de cron para generacion_boletas")
            return

        if not config['activo']:
            logger.info("Cron de generacion_boletas esta desactivado")
            # Remover job si existe
            remove_generacion_job()
            return

        # Obtener parametros del cron
        tipo = config['tipo_programacion']
        hora = config['hora_ejecucion']

        if isinstance(hora, str):
            hora_parts = hora.split(':')
            hour = int(hora_parts[0])
            minute = int(hora_parts[1]) if len(hora_parts) > 1 else 0
        else:
            hour = hora.hour
            minute = hora.minute

        # Remover job anterior si existe
        remove_generacion_job()

        if tipo == 'dia_mes':
            # Ejecutar un dia especifico del mes
            dia = config['dia_mes'] or 5
            _scheduler.add_job(
                _ejecutar_generacion_job,
                'cron',
                id='generacion_boletas',
                day=dia,
                hour=hour,
                minute=minute,
                replace_existing=True
            )
            logger.info(f"Job generacion_boletas programado: dia {dia} a las {hour}:{minute:02d}")

        elif tipo == 'intervalo_dias':
            # Ejecutar cada X dias
            intervalo = config['intervalo_dias'] or 30
            _scheduler.add_job(
                _ejecutar_generacion_job,
                'interval',
                id='generacion_boletas',
                days=intervalo,
                start_date=datetime.now().replace(hour=hour, minute=minute, second=0),
                replace_existing=True
            )
            logger.info(f"Job generacion_boletas programado: cada {intervalo} dias a las {hour}:{minute:02d}")

        elif tipo == 'manual':
            # No programar automaticamente
            logger.info("Cron de generacion_boletas en modo manual")

    except Exception as e:
        logger.error(f"Error configurando job de generacion: {e}")


def remove_generacion_job():
    """Remueve el job de generacion si existe."""
    global _scheduler

    if _scheduler:
        try:
            _scheduler.remove_job('generacion_boletas')
            logger.info("Job generacion_boletas removido")
        except Exception:
            pass  # Job no existe


def _ejecutar_generacion_job():
    """Funcion que ejecuta la generacion automatica."""
    from src.services.generacion_service import ejecutar_generacion

    logger.info("Iniciando generacion automatica de boletas...")

    try:
        resultado = ejecutar_generacion(usuario_id=None, es_automatico=True)
        logger.info(f"Generacion completada: {resultado['mensaje']}")
    except Exception as e:
        logger.error(f"Error en generacion automatica: {e}")


def recargar_configuracion_cron():
    """Recarga la configuracion del cron desde la base de datos."""
    global _scheduler

    if _scheduler and _scheduler.running:
        _setup_generacion_job()
        logger.info("Configuracion de cron recargada")


def obtener_estado_scheduler() -> dict:
    """Obtiene el estado actual del scheduler."""
    global _scheduler

    if _scheduler is None:
        return {
            'inicializado': False,
            'corriendo': False,
            'jobs': [],
            'proxima_ejecucion': None
        }

    jobs = []
    proxima_ejecucion = None

    if _scheduler.running:
        for job in _scheduler.get_jobs():
            next_run = job.next_run_time
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': next_run.isoformat() if next_run else None,
                'next_run_time_formatted': next_run.strftime('%d/%m/%Y %H:%M') if next_run else None,
                'trigger': str(job.trigger)
            })
            # Guardar la proxima ejecucion mas cercana
            if next_run and (proxima_ejecucion is None or next_run < proxima_ejecucion):
                proxima_ejecucion = next_run

    return {
        'inicializado': True,
        'corriendo': _scheduler.running,
        'jobs': jobs,
        'proxima_ejecucion': proxima_ejecucion.strftime('%d/%m/%Y %H:%M') if proxima_ejecucion else None
    }


def ejecutar_generacion_manual(usuario_id: int) -> dict:
    """
    Ejecuta la generacion de forma manual.

    Args:
        usuario_id: ID del usuario que ejecuta

    Returns:
        Resultado de la ejecucion
    """
    from src.services.generacion_service import ejecutar_generacion

    logger.info(f"Generacion manual iniciada por usuario {usuario_id}")
    resultado = ejecutar_generacion(usuario_id=usuario_id, es_automatico=False)
    logger.info(f"Generacion manual completada: {resultado['mensaje']}")

    return resultado
