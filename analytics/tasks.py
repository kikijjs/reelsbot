"""
성과 수집 Celery 태스크.

업로드 완료 후:
  - 24시간 후 → collect_metrics(job_id, interval_hours=24)
  - 72시간 후 → collect_metrics(job_id, interval_hours=72)

collect_metrics 완료 후 templates_store의 점수를 자동 갱신한다.
"""
import asyncio
import logging
import uuid

from publisher.celery_app import celery_app

logger = logging.getLogger(__name__)


def _run_async(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="analytics.tasks.collect_metrics")
def collect_metrics(job_id_str: str, interval_hours: int):
    """
    단일 Job의 성과 지표를 수집해 performance_metrics 테이블에 저장한다.
    """
    async def _collect():
        from dashboard.db import AsyncSessionLocal
        from dashboard.models.job import Job, JobStatus
        from dashboard.models.performance import PerformanceMetric
        from analytics.collector import fetch_metrics
        from sqlalchemy import select
        from datetime import datetime, timezone

        job_id = uuid.UUID(job_id_str)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()

            if job is None or job.status != JobStatus.COMPLETED:
                logger.warning("성과 수집 건너뜀 (Job 없음 또는 미완료): %s", job_id)
                return

            # post_id는 error_message 대신 별도 컬럼이 없으므로
            # final_video_path에서 shortcode를 post_id 대체로 사용
            # 실제 운영 시 Job 모델에 post_id 컬럼 추가 권장
            post_id = str(job_id)   # placeholder; 실제는 업로드 결과의 post_id

            logger.info("성과 수집 시작: job_id=%s platform=%s interval=%dh",
                        job_id, job.platform, interval_hours)

            metrics_data = fetch_metrics(job.platform, post_id)

            metric = PerformanceMetric(
                job_id=job_id,
                interval_hours=interval_hours,
                collected_at=datetime.now(timezone.utc),
                **metrics_data,
            )
            db.add(metric)
            await db.commit()
            logger.info("성과 저장 완료: views=%d likes=%d",
                        metrics_data["views"], metrics_data["likes"])

            # 72h 수집 완료 시 templates_store 점수 갱신
            if interval_hours == 72:
                from templates_store.manager import update_template_scores
                await update_template_scores(db, job_id, metrics_data)

    _run_async(_collect())


def schedule_analytics_for_job(job_id: str):
    """
    업로드 완료 직후 호출. 24h/72h 후에 collect_metrics를 예약한다.
    publisher/tasks.py의 upload_job 성공 시 호출한다.
    """
    collect_metrics.apply_async(
        args=[job_id, 24],
        countdown=24 * 3600,   # 24시간 후
    )
    collect_metrics.apply_async(
        args=[job_id, 72],
        countdown=72 * 3600,   # 72시간 후
    )
    logger.info("성과 수집 예약 완료: job_id=%s (24h, 72h 후)", job_id)
