"""
Jobs CRUD 라우터.

POST   /jobs/              — 새 작업 생성 (URL 입력 → collector 파이프라인 실행)
GET    /jobs/              — 작업 목록 조회 (페이지네이션)
GET    /jobs/{job_id}      — 작업 상세 조회
PATCH  /jobs/{job_id}      — 예약 시간 수정
DELETE /jobs/{job_id}      — 작업 삭제
POST   /jobs/{job_id}/run  — 수동으로 processor → editor 파이프라인 실행
"""
import uuid
from datetime import datetime
from typing import Literal

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.db import get_db
from dashboard.models.job import Job, JobStatus, Platform

router = APIRouter(prefix="/jobs", tags=["jobs"])


# ── Pydantic 스키마 ───────────────────────────────────────────────

class JobCreate(BaseModel):
    instagram_url: str
    platform: Literal["instagram", "youtube", "tiktok"] = "instagram"
    scheduled_at: datetime | None = None
    ab_test: bool = False


class JobPatch(BaseModel):
    scheduled_at: datetime | None = None
    platform: Literal["instagram", "youtube", "tiktok"] | None = None


class JobResponse(BaseModel):
    id: uuid.UUID
    instagram_url: str
    platform: str
    status: str
    gemini_analysis: dict | None
    script: dict | None
    script_variant_b: dict | None
    downloaded_video_path: str | None
    tts_audio_path: str | None
    final_video_path: str | None
    scheduled_at: datetime | None
    uploaded_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class JobListResponse(BaseModel):
    items: list[JobResponse]
    total: int
    page: int
    size: int


# ── 헬퍼 ─────────────────────────────────────────────────────────

async def _get_job_or_404(job_id: uuid.UUID, db: AsyncSession) -> Job:
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail=f"Job {job_id} not found")
    return job


async def _run_full_pipeline(job_id: uuid.UUID, ab_test: bool) -> None:
    """collector → processor → editor 파이프라인을 백그라운드에서 실행한다."""
    from dashboard.db import AsyncSessionLocal
    from collector.service import CollectorService
    from processor.service import ProcessorService
    from editor.service import EditorService

    async with AsyncSessionLocal() as db:
        # collector는 이미 실행되어 job이 생성됐으므로 processor부터
        proc = ProcessorService(db)
        await proc.run(job_id=job_id, ab_test=ab_test)

    async with AsyncSessionLocal() as db:
        editor = EditorService(db)
        await editor.run(job_id=job_id)


# ── 엔드포인트 ────────────────────────────────────────────────────

@router.post("/", response_model=JobResponse, status_code=201)
async def create_job(
    body: JobCreate,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """
    Instagram URL을 받아 collector 파이프라인(다운로드 + Gemini 분석)을 실행하고
    PENDING 상태의 Job을 생성한다. 이후 processor → editor는 백그라운드에서 실행.
    """
    from collector.service import CollectorService

    svc = CollectorService(db)
    job = await svc.run(
        instagram_url=body.instagram_url,
        platform=body.platform,
        scheduled_at=body.scheduled_at,
    )
    # processor + editor는 백그라운드 태스크로
    background_tasks.add_task(_run_full_pipeline, job.id, body.ab_test)
    return job


@router.get("/", response_model=JobListResponse)
async def list_jobs(
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    status: str | None = Query(None),
    platform: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    """작업 목록을 페이지네이션으로 반환한다."""
    query = select(Job)
    if status:
        query = query.where(Job.status == status)
    if platform:
        query = query.where(Job.platform == platform)

    total_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = total_result.scalar_one()

    query = query.order_by(Job.created_at.desc()).offset((page - 1) * size).limit(size)
    result = await db.execute(query)
    jobs = result.scalars().all()

    return JobListResponse(items=jobs, total=total, page=page, size=size)


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await _get_job_or_404(job_id, db)


@router.patch("/{job_id}", response_model=JobResponse)
async def patch_job(job_id: uuid.UUID, body: JobPatch, db: AsyncSession = Depends(get_db)):
    """예약 시간 또는 플랫폼을 수정한다."""
    job = await _get_job_or_404(job_id, db)
    if body.scheduled_at is not None:
        job.scheduled_at = body.scheduled_at
    if body.platform is not None:
        job.platform = Platform(body.platform)
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}", status_code=204)
async def delete_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await _get_job_or_404(job_id, db)
    await db.delete(job)
    await db.commit()


@router.post("/{job_id}/run", response_model=JobResponse)
async def run_pipeline(
    job_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    ab_test: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    """분석 완료된 Job에 대해 processor → editor 파이프라인을 수동 실행한다."""
    job = await _get_job_or_404(job_id, db)
    if not job.gemini_analysis:
        raise HTTPException(status_code=400, detail="gemini_analysis가 없습니다. collector를 먼저 실행하세요.")
    background_tasks.add_task(_run_full_pipeline, job.id, ab_test)
    return job
