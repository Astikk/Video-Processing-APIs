from celery import Celery

celery = Celery(
    "video_tasks",
    broker="redis://localhost:6379/0",   # Redis for queue
    backend="redis://localhost:6379/1"   # Redis for results
)
