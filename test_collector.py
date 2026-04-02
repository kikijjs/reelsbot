"""
collector 모듈 동작 확인 스크립트.

실행 방법:
    # 1. .env 파일 준비 (.env.example 복사)
    cp .env.example .env
    # GEMINI_API_KEY, DATABASE_URL 입력

    # 2. DB 기동 (docker-compose)
    docker-compose up -d db

    # 3. Alembic 마이그레이션
    alembic upgrade head

    # 4. 패키지 설치
    pip install -r requirements.txt

    # 5. 테스트 실행
    python test_collector.py [INSTAGRAM_URL]

    # URL 없이 실행하면 기본 테스트 URL 사용
"""
import asyncio
import json
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


async def main(instagram_url: str) -> None:
    from dashboard.db import AsyncSessionLocal
    from collector.service import CollectorService

    print("\n" + "=" * 60)
    print("  reelsbot — collector 모듈 테스트")
    print("=" * 60)
    print(f"  URL: {instagram_url}")
    print("=" * 60 + "\n")

    async with AsyncSessionLocal() as db:
        svc = CollectorService(db)
        job = await svc.run(
            instagram_url=instagram_url,
            platform="instagram",
        )

    print("\n" + "=" * 60)
    print("  테스트 결과")
    print("=" * 60)
    print(f"  job_id  : {job.id}")
    print(f"  status  : {job.status}")
    print(f"  platform: {job.platform}")
    print(f"  video   : {job.downloaded_video_path}")
    print()
    print("  [Gemini 분석 결과]")
    analysis = job.gemini_analysis or {}
    print(f"  product_name        : {analysis.get('product_name')}")
    print(f"  target_emotion      : {analysis.get('target_emotion')}")
    print(f"  emotional_benefit   : {analysis.get('emotional_benefit')}")
    print(f"  use_case_scene      : {analysis.get('use_case_scene')}")
    print()
    print("  visual_features:")
    for f in analysis.get("visual_features", []):
        print(f"    - {f}")
    print()
    print("  user_pain_points:")
    for p in analysis.get("user_pain_points", []):
        print(f"    - {p}")
    print()
    print("  product_differentiators:")
    for d in analysis.get("product_differentiators", []):
        print(f"    - {d}")
    print()
    print("  [전체 JSON]")
    print(json.dumps(analysis, ensure_ascii=False, indent=2))
    print("=" * 60)
    print("  collector 파이프라인 완료!")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    # CLI 인수로 URL을 받거나 기본 예시 URL 사용
    # 실제 공개 릴스 URL로 교체하세요
    default_url = "https://www.instagram.com/reel/C_example12345/"
    url = sys.argv[1] if len(sys.argv) > 1 else default_url

    if url == default_url:
        print(
            "\n[경고] 기본 테스트 URL이 설정되어 있습니다.\n"
            "실제 공개 Instagram Reel URL을 인수로 전달해주세요:\n"
            "  python test_collector.py https://www.instagram.com/reel/XXXXXXX/\n"
        )
        sys.exit(1)

    asyncio.run(main(url))
