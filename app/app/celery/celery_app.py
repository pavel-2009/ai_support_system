"""Приложение Celery для обработки фоновых задач."""

from celery import Celery

from app.core.config import settings
from app.core.logging import configure_logging

configure_logging()

celery_app = Celery(
    "app.celery.celery_app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.celery.tasks.llm_tasks"],
)

# Celery не должен перехватывать root logger и создавать собственный вывод.
# Все сообщения проходят через нашу единую маршрутизацию в console/*.log files.
celery_app.conf.update(
    worker_hijack_root_logger=False,
)
