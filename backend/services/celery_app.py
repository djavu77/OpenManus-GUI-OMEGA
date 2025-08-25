"""
Configuração do Celery para Tarefas Assíncronas
Sistema de IA Conversacional Avançada
"""

import os
import asyncio
from celery import Celery
from celery.schedules import crontab

from app.logger import logger

# Configuração do Celery
CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/1")
CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/2")

# Criar aplicação Celery
celery_app = Celery(
    "sistema_ia_conversacional",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "backend.services.celery_tasks"
    ]
)

# Configuração do Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="America/Sao_Paulo",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutos
    task_soft_time_limit=25 * 60,  # 25 minutos
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Configurar tarefas periódicas
celery_app.conf.beat_schedule = {
    # Análise de feedback a cada hora
    'analyze-feedback': {
        'task': 'backend.services.celery_tasks.analyze_feedback_batch',
        'schedule': crontab(minute=0),  # A cada hora
    },
    
    # Otimização do modelo a cada 6 horas
    'optimize-model': {
        'task': 'backend.services.celery_tasks.optimize_model_parameters',
        'schedule': crontab(minute=0, hour='*/6'),  # A cada 6 horas
    },
    
    # Limpeza de dados antigos diariamente
    'cleanup-old-data': {
        'task': 'backend.services.celery_tasks.cleanup_old_data',
        'schedule': crontab(minute=0, hour=2),  # 2:00 AM todos os dias
    },
    
    # Backup da base de conhecimento diariamente
    'backup-knowledge-base': {
        'task': 'backend.services.celery_tasks.backup_knowledge_base',
        'schedule': crontab(minute=30, hour=3),  # 3:30 AM todos os dias
    },
    
    # Análise de tendências semanalmente
    'analyze-trends': {
        'task': 'backend.services.celery_tasks.analyze_performance_trends',
        'schedule': crontab(minute=0, hour=4, day_of_week=1),  # Segunda-feira 4:00 AM
    },
}

# Configurações de roteamento de tarefas
celery_app.conf.task_routes = {
    'backend.services.celery_tasks.analyze_feedback_batch': {'queue': 'learning'},
    'backend.services.celery_tasks.optimize_model_parameters': {'queue': 'optimization'},
    'backend.services.celery_tasks.generate_embeddings': {'queue': 'embeddings'},
    'backend.services.celery_tasks.cleanup_old_data': {'queue': 'maintenance'},
}

# Configurações de retry
celery_app.conf.task_default_retry_delay = 60  # 1 minuto
celery_app.conf.task_max_retries = 3

if __name__ == "__main__":
    # Iniciar worker Celery
    logger.info("🚀 Iniciando Celery Worker...")
    celery_app.start()