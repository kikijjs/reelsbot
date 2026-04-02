"""
Celery 앱 설정.

- Broker/Backend: Redis
- Beat 스케줄러: 1분마다 예약된 PENDING Job을 확인해 업로드 태스크 실행
"""
from celery import Celery
from celery.schedules import crontab

from config import settings

celery_app = Celery(
    "reelsbot",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["publisher.tasks"],
)

celery_app.conf.update(
    # 직렬화
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # 타임존
    timezone="Asia/Seoul",
    enable_utc=True,
    # 태스크 ACK 정책 — 실행 시작 전 ACK (재시도 방지)
    task_acks_late=False,
    # 워커 동시성 (I/O 바운드이므로 스레드 풀 사용)
    worker_concurrency=4,
    worker_prefetch_multiplier=1,
    # Beat 스케줄: 1분마다 예약된 작업 체크
    beat_schedule={
        "check-pending-jobs": {
            "task": "publisher.tasks.dispatch_pending_jobs",
            "schedule": 60.0,   # 60초마다 실행
        },
    },
)
