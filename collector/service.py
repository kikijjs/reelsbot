"""
collector 파이프라인 서비스.

흐름: URL 입력 → 영상 다운로드 → Gemini 분석 → DB에 PENDING 상태로 저장
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.models.job import Job, JobStatus, Platform
from collector.downloader import download_video
from collector.gemini_analyzer import analyze_video
from collector.schemas import DownloadResult, GeminiAnalysis

logger = logging.getLogger(__name__)


class CollectorService:
    """
    collector 모듈의 진입점.

    사용 예:
        async with AsyncSessionLocal() as db:
            svc = CollectorService(db)
            job = await svc.run(
                instagram_url="https://www.instagram.com/reel/ABC123/",
                platform="instagram",
            )
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(
        self,
        instagram_url: str,
        platform: str = "instagram",
        scheduled_at: datetime | None = None,
    ) -> Job:
        """
        전체 collector 파이프라인을 실행한다.

        1. Instagram 영상 다운로드
        2. Gemini 1.5 Pro로 영상 분석
        3. jobs 테이블에 PENDING 상태로 저장

        Args:
            instagram_url: 분석할 Instagram Reel/Post URL
            platform: 업로드 대상 플랫폼 (instagram / youtube / tiktok)
            scheduled_at: 예약 업로드 시간 (None이면 미설정)

        Returns:
            생성된 Job 인스턴스
        """
        logger.info("=== CollectorService.run 시작 ===")
        logger.info("URL: %s | 플랫폼: %s", instagram_url, platform)

        # ── Step 1: 영상 다운로드 ──────────────────────────────────
        logger.info("[1/3] 영상 다운로드 중...")
        download_result: DownloadResult = download_video(instagram_url)
        logger.info("다운로드 완료: %s", download_result.video_path)

        # ── Step 2: Gemini 영상 분석 ───────────────────────────────
        logger.info("[2/3] Gemini 1.5 Pro 영상 분석 중...")
        analysis: GeminiAnalysis = analyze_video(download_result.video_path)
        logger.info(
            "분석 완료: product=%s | emotion=%s",
            analysis.product_name,
            analysis.target_emotion,
        )

        # ── Step 3: DB 저장 (PENDING) ──────────────────────────────
        logger.info("[3/3] DB에 작업 저장 중 (PENDING)...")
        job = Job(
            id=uuid.uuid4(),
            instagram_url=instagram_url,
            platform=Platform(platform),
            gemini_analysis=analysis.model_dump(),
            downloaded_video_path=download_result.video_path,
            status=JobStatus.PENDING,
            scheduled_at=scheduled_at,
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        logger.info("=== 저장 완료 | job_id=%s | status=%s ===", job.id, job.status)
        return job
