"""
Celery 태스크 정의.

태스크 목록:
  - dispatch_pending_jobs : Beat가 1분마다 실행 → 예약 시간 된 Job을 upload_job으로 디스패치
  - upload_job            : 단일 Job 업로드 파이프라인 실행
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

from celery import shared_task
from sqlalchemy import select, and_

from publisher.celery_app import celery_app
from config import settings

logger = logging.getLogger(__name__)


# ── 헬퍼: 동기 Celery 태스크에서 async DB 세션을 사용하기 위한 래퍼 ──

def _run_async(coro):
    """동기 컨텍스트에서 코루틴을 실행한다."""
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


# ── Beat 디스패처 ────────────────────────────────────────────────

@celery_app.task(name="publisher.tasks.dispatch_pending_jobs")
def dispatch_pending_jobs():
    """
    1분마다 실행되는 Beat 태스크.
    scheduled_at이 현재 시각 이전인 PENDING Job을 찾아 upload_job을 디스패치한다.
    """
    async def _dispatch():
        from dashboard.db import AsyncSessionLocal
        from dashboard.models.job import Job, JobStatus

        now = datetime.now(timezone.utc)
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Job).where(
                    and_(
                        Job.status == JobStatus.PENDING,
                        Job.final_video_path.is_not(None),
                        Job.scheduled_at <= now,
                    )
                )
            )
            jobs = result.scalars().all()

        dispatched = 0
        for job in jobs:
            upload_job.delay(str(job.id))
            dispatched += 1
            logger.info("업로드 디스패치: job_id=%s platform=%s", job.id, job.platform)

        if dispatched:
            logger.info("총 %d개 업로드 태스크 디스패치 완료", dispatched)

    _run_async(_dispatch())


# ── 업로드 태스크 ────────────────────────────────────────────────

@celery_app.task(
    name="publisher.tasks.upload_job",
    bind=True,
    max_retries=3,
    default_retry_delay=60,   # 실패 시 60초 후 재시도
)
def upload_job(self, job_id_str: str):
    """
    단일 Job의 업로드 파이프라인을 실행한다.

    흐름:
      1. DB에서 Job 조회
      2. 플랫폼별 메타데이터 생성 (Claude)
      3. 플랫폼 업로더 호출
      4. DB 상태 업데이트 (COMPLETED / FAILED)
      5. Telegram 알림
    """
    async def _upload():
        from dashboard.db import AsyncSessionLocal
        from dashboard.models.job import Job, JobStatus
        from publisher.platform_formatter import generate_meta
        from publisher.notifier import notify_success, notify_failure
        from publisher import instagram, youtube, tiktok
        from datetime import datetime, timezone

        job_id = uuid.UUID(job_id_str)

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Job).where(Job.id == job_id))
            job = result.scalar_one_or_none()

            if job is None:
                logger.error("Job을 찾을 수 없음: %s", job_id)
                return

            if job.status != JobStatus.PENDING:
                logger.warning("이미 처리된 Job: %s (status=%s)", job_id, job.status)
                return

            # ── PROCESSING으로 전환 ───────────────────────────
            job.status = JobStatus.PROCESSING
            await db.commit()

            try:
                analysis = job.gemini_analysis or {}
                script = job.script or {}
                platform = job.platform
                video_path = job.final_video_path

                # ── 메타데이터 생성 ───────────────────────────
                logger.info("[1/2] 플랫폼 메타데이터 생성: %s", platform)
                meta = generate_meta(platform, analysis, script)

                # ── 플랫폼별 업로드 ───────────────────────────
                logger.info("[2/2] 업로드 실행: %s", platform)
                if platform == "instagram":
                    from publisher.media_host import get_public_url
                    result_obj = instagram.upload_reel(
                        video_url=get_public_url(video_path),
                        meta=meta,
                    )
                elif platform == "youtube":
                    result_obj = youtube.upload_short(video_path=video_path, meta=meta)
                elif platform == "tiktok":
                    result_obj = tiktok.upload_video(video_path=video_path, meta=meta)
                else:
                    raise ValueError(f"알 수 없는 플랫폼: {platform}")

                # ── DB 업데이트 ───────────────────────────────
                if result_obj.success:
                    job.status = JobStatus.COMPLETED
                    job.uploaded_at = datetime.now(timezone.utc)
                    await db.commit()
                    logger.info("업로드 완료: job_id=%s post_url=%s", job_id, result_obj.post_url)
                    notify_success(job_id_str, platform, result_obj.post_url)
                else:
                    raise RuntimeError(result_obj.error_message or "업로드 실패")

            except Exception as e:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                await db.commit()
                logger.error("업로드 실패: job_id=%s error=%s", job_id, e)
                notify_failure(job_id_str, job.platform, str(e))
                raise self.retry(exc=e)

    _run_async(_upload())
