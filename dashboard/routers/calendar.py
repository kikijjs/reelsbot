"""
캘린더 라우터.

GET /calendar/monthly?year=2026&month=4
  → 해당 월의 날짜별 예약 건수 + 상태별 색상 반환

GET /calendar/day?date=2026-04-15
  → 특정 날짜의 Job 목록 (상세 카드용)
"""
from datetime import date, datetime, timezone
from calendar import monthrange

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, and_, extract
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.db import get_db
from dashboard.models.job import Job, JobStatus

router = APIRouter(prefix="/calendar", tags=["calendar"])

# 상태 → 색상 매핑
STATUS_COLORS: dict[str, str] = {
    JobStatus.PENDING: "#3B82F6",      # 파랑
    JobStatus.PROCESSING: "#F59E0B",   # 노랑
    JobStatus.COMPLETED: "#10B981",    # 초록
    JobStatus.FAILED: "#EF4444",       # 빨강
}


class DayEntry(BaseModel):
    date: str              # "2026-04-15"
    count: int
    status_counts: dict    # {"PENDING": 2, "COMPLETED": 1, ...}
    dominant_color: str    # 가장 많은 상태의 색상


class MonthlyCalendarResponse(BaseModel):
    year: int
    month: int
    days: list[DayEntry]


class JobSummary(BaseModel):
    id: str
    platform: str
    status: str
    scheduled_at: datetime | None
    cover_text: str | None
    final_video_path: str | None
    color: str


class DayDetailResponse(BaseModel):
    date: str
    jobs: list[JobSummary]


@router.get("/monthly", response_model=MonthlyCalendarResponse)
async def monthly_calendar(
    year: int = Query(..., ge=2024, le=2030),
    month: int = Query(..., ge=1, le=12),
    db: AsyncSession = Depends(get_db),
):
    """월별 캘린더: 날짜별 예약 건수와 상태 분포를 반환한다."""
    _, last_day = monthrange(year, month)
    start = datetime(year, month, 1, tzinfo=timezone.utc)
    end = datetime(year, month, last_day, 23, 59, 59, tzinfo=timezone.utc)

    result = await db.execute(
        select(Job).where(
            and_(Job.scheduled_at >= start, Job.scheduled_at <= end)
        )
    )
    jobs = result.scalars().all()

    # 날짜별 집계
    day_map: dict[str, dict] = {}
    for job in jobs:
        if not job.scheduled_at:
            continue
        day_str = job.scheduled_at.strftime("%Y-%m-%d")
        if day_str not in day_map:
            day_map[day_str] = {s: 0 for s in JobStatus}
        day_map[day_str][job.status] += 1

    days: list[DayEntry] = []
    for day_str, counts in sorted(day_map.items()):
        total = sum(counts.values())
        dominant = max(counts, key=counts.get)
        days.append(DayEntry(
            date=day_str,
            count=total,
            status_counts={k: v for k, v in counts.items() if v > 0},
            dominant_color=STATUS_COLORS[dominant],
        ))

    return MonthlyCalendarResponse(year=year, month=month, days=days)


@router.get("/day", response_model=DayDetailResponse)
async def day_detail(
    date_str: str = Query(..., alias="date", description="YYYY-MM-DD"),
    db: AsyncSession = Depends(get_db),
):
    """특정 날짜의 Job 목록을 반환한다 (캘린더 클릭 시 상세 카드)."""
    try:
        d = date.fromisoformat(date_str)
    except ValueError:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="날짜 형식은 YYYY-MM-DD여야 합니다.")

    start = datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc)
    end = datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=timezone.utc)

    result = await db.execute(
        select(Job).where(
            and_(Job.scheduled_at >= start, Job.scheduled_at <= end)
        ).order_by(Job.scheduled_at)
    )
    jobs = result.scalars().all()

    return DayDetailResponse(
        date=date_str,
        jobs=[
            JobSummary(
                id=str(job.id),
                platform=job.platform,
                status=job.status,
                scheduled_at=job.scheduled_at,
                cover_text=(job.script or {}).get("cover_text"),
                final_video_path=job.final_video_path,
                color=STATUS_COLORS.get(job.status, "#6B7280"),
            )
            for job in jobs
        ],
    )
