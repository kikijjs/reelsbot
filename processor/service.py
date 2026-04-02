"""
processor 파이프라인 서비스.

흐름: DB에서 Job 조회 → Gemini 분석 JSON 읽기 → Claude 스크립트 생성 → DB 업데이트
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.models.job import Job, JobStatus
from processor.claude_writer import generate_script
from processor.ab_test import generate_ab_scripts
from processor.schemas import Script5Parts, ABTestScript

logger = logging.getLogger(__name__)


class ProcessorService:
    """
    processor 모듈의 진입점.

    사용 예:
        async with AsyncSessionLocal() as db:
            svc = ProcessorService(db)

            # 단일 버전
            job = await svc.run(job_id=some_uuid)

            # A/B 테스트 버전
            job = await svc.run(job_id=some_uuid, ab_test=True)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(self, job_id: uuid.UUID, ab_test: bool = False) -> Job:
        """
        job_id에 해당하는 Job의 gemini_analysis를 읽어
        Claude 스크립트를 생성하고 DB에 저장한다.

        Args:
            job_id: 처리할 Job의 UUID
            ab_test: True이면 A/B 2버전 동시 생성

        Returns:
            스크립트가 저장된 Job 인스턴스

        Raises:
            ValueError: job_id가 없거나 gemini_analysis가 비어있을 때
        """
        # ── Job 조회 ──────────────────────────────────────────────
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"Job을 찾을 수 없습니다: {job_id}")
        if not job.gemini_analysis:
            raise ValueError(f"gemini_analysis가 비어있습니다: {job_id}")

        # ── 상태 → PROCESSING ─────────────────────────────────────
        job.status = JobStatus.PROCESSING
        await self.db.commit()

        logger.info(
            "=== ProcessorService.run 시작 | job_id=%s | ab_test=%s ===",
            job_id,
            ab_test,
        )

        analysis = job.gemini_analysis

        try:
            if ab_test:
                # A/B 테스트: 2버전 병렬 생성
                logger.info("[A/B] 스크립트 2버전 생성 중...")
                ab: ABTestScript = generate_ab_scripts(analysis)
                job.script = ab.variant_a.model_dump()
                job.script_variant_b = ab.variant_b.model_dump()
                logger.info("[A/B] 완료 | A_cover: %s", ab.variant_a.cover_text[:20])
            else:
                # 단일 버전
                logger.info("[단일] 스크립트 생성 중...")
                script: Script5Parts = generate_script(analysis)
                job.script = script.model_dump()
                logger.info("[단일] 완료 | cover: %s", script.cover_text[:20])

            # ── 상태 → PENDING (업로드 대기) ─────────────────────
            job.status = JobStatus.PENDING
            await self.db.commit()
            await self.db.refresh(job)

            logger.info("=== 스크립트 저장 완료 | job_id=%s ===", job_id)
            return job

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            await self.db.commit()
            logger.error("스크립트 생성 실패 | job_id=%s | error=%s", job_id, e)
            raise
