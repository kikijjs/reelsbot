"""
Analytics 라우터.

GET /analytics/{job_id}        — Job의 24h/72h 성과 지표
GET /analytics/leaderboard     — 조회수 상위 Job 목록
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.db import get_db
from dashboard.models.job import Job
from dashboard.models.performance import PerformanceMetric

router = APIRouter(prefix="/analytics", tags=["analytics"])


class MetricPoint(BaseModel):
    interval_hours: int
    collected_at: str
    views: int
    likes: int
    comments: int
    shares: int


class JobAnalyticsResponse(BaseModel):
    job_id: str
    platform: str
    metrics: list[MetricPoint]


class LeaderboardItem(BaseModel):
    job_id: str
    platform: str
    cover_text: str | None
    views_72h: int
    likes_72h: int


@router.get("/{job_id}", response_model=JobAnalyticsResponse)
async def get_job_analytics(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """특정 Job의 수집된 성과 지표를 반환한다."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")

    metrics_result = await db.execute(
        select(PerformanceMetric)
        .where(PerformanceMetric.job_id == job_id)
        .order_by(PerformanceMetric.interval_hours)
    )
    metrics = metrics_result.scalars().all()

    return JobAnalyticsResponse(
        job_id=str(job_id),
        platform=job.platform,
        metrics=[
            MetricPoint(
                interval_hours=m.interval_hours,
                collected_at=m.collected_at.isoformat(),
                views=m.views,
                likes=m.likes,
                comments=m.comments,
                shares=m.shares,
            )
            for m in metrics
        ],
    )


@router.get("/leaderboard", response_model=list[LeaderboardItem])
async def get_leaderboard(
    limit: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
):
    """72h 조회수 기준 상위 Job 목록을 반환한다."""
    result = await db.execute(
        select(PerformanceMetric, Job)
        .join(Job, Job.id == PerformanceMetric.job_id)
        .where(PerformanceMetric.interval_hours == 72)
        .order_by(desc(PerformanceMetric.views))
        .limit(limit)
    )
    rows = result.all()

    return [
        LeaderboardItem(
            job_id=str(job.id),
            platform=job.platform,
            cover_text=(job.script or {}).get("cover_text"),
            views_72h=metric.views,
            likes_72h=metric.likes,
        )
        for metric, job in rows
    ]
