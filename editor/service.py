"""
editor 파이프라인 서비스.

흐름:
  DB에서 Job 조회
  → Gemini 2.5 Pro TTS 음성 생성 (hook/body/cta 파트별 톤 적용)
  → MoviePy 영상 편집 (음성 교체 + 커버 오버레이 + 자막)
  → 최종 MP4 경로를 DB에 저장
"""
import logging
import uuid
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from dashboard.models.job import Job, JobStatus
from editor.tts_gemini import generate_tts
from editor.video_editor import edit_video
from editor.schemas import EditConfig

logger = logging.getLogger(__name__)


class EditorService:
    """
    editor 모듈의 진입점.

    사용 예:
        async with AsyncSessionLocal() as db:
            svc = EditorService(db)
            job = await svc.run(job_id=some_uuid)
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def run(self, job_id: uuid.UUID) -> Job:
        """
        job_id에 해당하는 Job을 편집 파이프라인으로 처리한다.

        전제 조건:
          - job.downloaded_video_path 존재
          - job.script (Script5Parts JSON) 존재

        Args:
            job_id: 편집할 Job의 UUID

        Returns:
            tts_audio_path, final_video_path가 저장된 Job

        Raises:
            ValueError: Job이 없거나 필수 필드가 비어있을 때
        """
        # ── Job 조회 ──────────────────────────────────────────
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()

        if job is None:
            raise ValueError(f"Job을 찾을 수 없습니다: {job_id}")
        if not job.downloaded_video_path:
            raise ValueError(f"downloaded_video_path가 없습니다: {job_id}")
        if not job.script:
            raise ValueError(f"script가 없습니다 (processor를 먼저 실행하세요): {job_id}")

        # ── 상태 → PROCESSING ─────────────────────────────────
        job.status = JobStatus.PROCESSING
        await self.db.commit()

        logger.info("=== EditorService.run 시작 | job_id=%s ===", job_id)

        # 출력 디렉터리: media/{shortcode}/
        job_dir = Path(job.downloaded_video_path).parent
        output_dir = str(job_dir)

        try:
            # ── Step 1: TTS 음성 생성 ─────────────────────────
            logger.info("[1/2] Gemini TTS 음성 생성 중...")
            tts_result = generate_tts(
                script=job.script,
                output_dir=output_dir,
            )
            job.tts_audio_path = tts_result.mp3_path
            job.tts_voice = "Kore"
            await self.db.commit()
            logger.info("TTS 완료: %s (%.1fs)", tts_result.mp3_path, tts_result.duration_sec)

            # ── Step 2: 영상 편집 ─────────────────────────────
            logger.info("[2/2] MoviePy 영상 편집 중...")
            output_path = str(job_dir / "final_output.mp4")

            config = EditConfig(
                source_video_path=job.downloaded_video_path,
                tts_audio_path=tts_result.mp3_path,
                cover_text=job.script.get("cover_text", ""),
                subtitle_timeline=job.script.get("subtitle_timeline", []),
                output_path=output_path,
            )
            final_path = edit_video(config)

            # ── DB 업데이트 ───────────────────────────────────
            job.final_video_path = final_path
            job.status = JobStatus.PENDING   # 업로드 대기
            await self.db.commit()
            await self.db.refresh(job)

            logger.info("=== 편집 완료 | final=%s ===", final_path)
            return job

        except Exception as e:
            job.status = JobStatus.FAILED
            job.error_message = str(e)
            await self.db.commit()
            logger.error("편집 실패 | job_id=%s | error=%s", job_id, e)
            raise
