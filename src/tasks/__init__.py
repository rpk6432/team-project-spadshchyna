from celery import Celery
from celery.schedules import crontab

from config import settings

app = Celery("spadshchyna")
app.config_from_object(
    {
        "broker_url": settings.redis_url,
        "result_backend": None,
        "task_serializer": "json",
        "accept_content": ["json"],
        "timezone": "UTC",
        "enable_utc": True,
        "task_soft_time_limit": 120,
        "task_time_limit": 180,
        "worker_prefetch_multiplier": 1,
        "imports": ["tasks.email", "tasks.bookings"],
        "beat_schedule": {
            "expire-pending-bookings": {
                "task": "tasks.bookings.expire_pending_bookings",
                "schedule": crontab(minute="*/10"),
            },
            "complete-confirmed-bookings": {
                "task": "tasks.bookings.complete_confirmed_bookings",
                "schedule": crontab(minute=5, hour=0),
            },
        },
    }
)
