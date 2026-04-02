"""
스크립트 템플릿 저장/조회/성과 기반 점수 갱신 모듈.

성과 점수 공식:
  score = views * 0.4 + likes * 1.0 + comments * 2.0 + shares * 3.0
  (공유 > 댓글 > 좋아요 > 조회 순으로 가중치 부여)
"""
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from dashboard.models.template import ScriptTemplate

logger = logging.getLogger(__name__)

_SCORE_WEIGHTS = {"views": 0.4, "likes": 1.0, "comments": 2.0, "shares": 3.0}


def _calc_score(metrics: dict) -> float:
    return sum(metrics.get(k, 0) * w for k, w in _SCORE_WEIGHTS.items())


async def save_template(
    db: AsyncSession,
    name: str,
    script: dict,
    source_job_id: uuid.UUID | None = None,
    performance_score: float = 0.0,
) -> ScriptTemplate:
    """스크립트를 템플릿으로 저장한다."""
    tmpl = ScriptTemplate(
        id=uuid.uuid4(),
        name=name,
        script=script,
        source_job_id=source_job_id,
        performance_score=performance_score,
    )
    db.add(tmpl)
    await db.commit()
    await db.refresh(tmpl)
    logger.info("템플릿 저장: name=%s score=%.1f", name, performance_score)
    return tmpl


async def get_top_templates(db: AsyncSession, limit: int = 5) -> list[ScriptTemplate]:
    """성과 점수 상위 템플릿을 반환한다."""
    result = await db.execute(
        select(ScriptTemplate)
        .order_by(ScriptTemplate.performance_score.desc())
        .limit(limit)
    )
    return result.scalars().all()


async def update_template_scores(
    db: AsyncSession,
    job_id: uuid.UUID,
    metrics: dict,
) -> None:
    """
    해당 job_id로 만들어진 템플릿의 성과 점수를 갱신한다.
    72h 성과 수집 완료 시 자동 호출된다.
    """
    score = _calc_score(metrics)
    result = await db.execute(
        select(ScriptTemplate).where(ScriptTemplate.source_job_id == job_id)
    )
    templates = result.scalars().all()
    for tmpl in templates:
        tmpl.performance_score = score
    await db.commit()
    if templates:
        logger.info("템플릿 점수 갱신: job_id=%s score=%.1f (%d개)", job_id, score, len(templates))
