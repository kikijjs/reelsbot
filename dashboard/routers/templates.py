"""
스크립트 템플릿 라우터.

GET    /templates/          — 템플릿 목록 (성과 점수 순)
POST   /templates/          — 템플릿 저장
GET    /templates/{id}      — 단일 템플릿 조회
DELETE /templates/{id}      — 삭제
POST   /templates/from-job/{job_id} — Job의 스크립트를 템플릿으로 저장
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.db import get_db
from dashboard.models.job import Job
from dashboard.models.template import ScriptTemplate

router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateCreate(BaseModel):
    name: str
    script: dict
    source_job_id: uuid.UUID | None = None
    performance_score: float = 0.0


class TemplateResponse(BaseModel):
    id: uuid.UUID
    name: str
    script: dict
    source_job_id: uuid.UUID | None
    performance_score: float
    created_at: str

    model_config = {"from_attributes": True}


@router.get("/", response_model=list[TemplateResponse])
async def list_templates(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(ScriptTemplate).order_by(ScriptTemplate.performance_score.desc())
    )
    return result.scalars().all()


@router.post("/", response_model=TemplateResponse, status_code=201)
async def create_template(body: TemplateCreate, db: AsyncSession = Depends(get_db)):
    tmpl = ScriptTemplate(
        id=uuid.uuid4(),
        name=body.name,
        script=body.script,
        source_job_id=body.source_job_id,
        performance_score=body.performance_score,
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl


@router.get("/{template_id}", response_model=TemplateResponse)
async def get_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == template_id))
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return tmpl


@router.delete("/{template_id}", status_code=204)
async def delete_template(template_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(ScriptTemplate).where(ScriptTemplate.id == template_id))
    tmpl = result.scalar_one_or_none()
    if tmpl is None:
        raise HTTPException(status_code=404, detail="Template not found")
    await db.delete(tmpl)
    await db.commit()


@router.post("/from-job/{job_id}", response_model=TemplateResponse, status_code=201)
async def save_from_job(
    job_id: uuid.UUID,
    name: str,
    db: AsyncSession = Depends(get_db),
):
    """Job의 script를 템플릿으로 저장한다."""
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    if not job.script:
        raise HTTPException(status_code=400, detail="스크립트가 없습니다.")

    tmpl = ScriptTemplate(
        id=uuid.uuid4(),
        name=name,
        script=job.script,
        source_job_id=job_id,
        performance_score=0.0,
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    return tmpl
