"""
dashboard / analytics / templates_store 모듈 단위 테스트.

실행:
  python test_dashboard.py
"""
import asyncio
import logging
import uuid
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s — %(message)s")
logger = logging.getLogger(__name__)


async def test_all():
    print("\n" + "=" * 60)
    print("  dashboard / analytics / templates_store 단위 테스트")
    print("=" * 60 + "\n")

    # ── 1. 모델 임포트 검증 ───────────────────────────────────────
    from dashboard.models.job import Job, JobStatus, Platform
    from dashboard.models.performance import PerformanceMetric
    from dashboard.models.template import ScriptTemplate
    print("  ✓ DB 모델 임포트")

    # ── 2. FastAPI 앱 + 라우터 임포트 ────────────────────────────
    from dashboard.main import app
    from dashboard.routers.jobs import JobCreate, JobPatch, JobResponse
    from dashboard.routers.calendar import STATUS_COLORS, DayEntry
    from dashboard.routers.analytics import MetricPoint
    from dashboard.routers.templates import TemplateCreate, TemplateResponse
    print("  ✓ FastAPI 앱 + 4개 라우터 임포트")

    # ── 3. 라우터 경로 확인 ──────────────────────────────────────
    routes = {r.path for r in app.routes}
    expected_paths = ["/jobs/", "/calendar/monthly", "/calendar/day",
                      "/analytics/leaderboard", "/templates/", "/health"]
    for path in expected_paths:
        assert path in routes, f"경로 없음: {path}"
    print(f"  ✓ API 경로 {len(routes)}개 등록 확인")

    # ── 4. 캘린더 상태 색상 검증 ─────────────────────────────────
    assert STATUS_COLORS["PENDING"] == "#3B82F6"
    assert STATUS_COLORS["PROCESSING"] == "#F59E0B"
    assert STATUS_COLORS["COMPLETED"] == "#10B981"
    assert STATUS_COLORS["FAILED"] == "#EF4444"
    print("  ✓ 캘린더 상태 색상 (파랑/노랑/초록/빨강)")

    # ── 5. Pydantic 스키마 검증 ───────────────────────────────────
    jc = JobCreate(instagram_url="https://instagram.com/reel/test/", platform="youtube", ab_test=True)
    assert jc.platform == "youtube" and jc.ab_test
    print(f"  ✓ JobCreate: platform={jc.platform}, ab_test={jc.ab_test}")

    tc = TemplateCreate(name="손실회피 패턴", script={"cover_text": "test"})
    assert tc.name == "손실회피 패턴"
    print(f"  ✓ TemplateCreate: name={tc.name}")

    # ── 6. analytics collector 함수 시그니처 ─────────────────────
    from analytics.collector import fetch_metrics
    from unittest.mock import patch
    with patch("analytics.collector._fetch_instagram_metrics", return_value={"views": 1000, "likes": 50, "comments": 10, "shares": 5}):
        result = fetch_metrics("instagram", "media_123")
        assert result["views"] == 1000
    print(f"  ✓ fetch_metrics 모킹: views={result['views']}")

    # ── 7. templates_store 점수 계산 ─────────────────────────────
    from templates_store.manager import _calc_score
    metrics = {"views": 10000, "likes": 500, "comments": 200, "shares": 100}
    score = _calc_score(metrics)
    expected = 10000 * 0.4 + 500 * 1.0 + 200 * 2.0 + 100 * 3.0
    assert abs(score - expected) < 0.001
    print(f"  ✓ 성과 점수 계산: {metrics} → {score:.1f}점")

    # ── 8. analytics schedule 함수 임포트 ────────────────────────
    from analytics.tasks import schedule_analytics_for_job, collect_metrics
    from analytics import schedule_analytics_for_job as exported_fn
    assert schedule_analytics_for_job is exported_fn
    print("  ✓ analytics 모듈 export 확인")

    # ── 9. media_host URL 변환 ────────────────────────────────────
    from publisher.media_host import get_public_url
    import os
    with patch.dict(os.environ, {"MEDIA_PUBLIC_BASE_URL": "https://cdn.example.com"}):
        url = get_public_url("./media/ABC123/final_output.mp4")
        assert url == "https://cdn.example.com/media/ABC123/final_output.mp4"
    print(f"  ✓ media_host CDN URL: {url}")

    print("\n" + "=" * 60)
    print("  모든 단위 테스트 통과!")
    print("=" * 60 + "\n")

    print("  [FastAPI 서버 실행 방법]")
    print("  uvicorn dashboard.main:app --reload --port 8000")
    print()
    print("  [React 웹앱 실행 방법]")
    print("  cd dashboard/web && npm install && npm run dev")
    print()
    print("  [Celery 워커 실행 방법]")
    print("  ./start_worker.sh all")


if __name__ == "__main__":
    asyncio.run(test_all())
