"""Приложение Celery для обработки фоновых задач."""

from celery import Celery

from app.core.config import settings


celery_app = Celery(
    "app.celery.celery_app",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.celery.tasks.llm_tasks"],
)
