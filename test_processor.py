"""
processor 모듈 동작 확인 스크립트.

두 가지 모드로 실행 가능:
  1. 단독 모드: ANTHROPIC_API_KEY만 있으면 됨 (DB 불필요)
     python test_processor.py

  2. DB 연동 모드: job_id로 기존 Job의 gemini_analysis를 읽어서 처리
     python test_processor.py --job-id <UUID>
     python test_processor.py --job-id <UUID> --ab-test
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

# 테스트용 고정 Gemini 분석 샘플 (DB 없이 독립 실행 시 사용)
SAMPLE_ANALYSIS = {
    "product_name": "접이식 주방 타이머",
    "visual_features": ["카드 두께로 접히는 디자인", "터치 버튼", "자석 부착 가능"],
    "use_case_scene": "주방 조리대 앞에서 파스타를 삶으며 타이머를 설정하는 장면. 냉장고 옆 자석에 붙여두고 꺼내 쓰는 모습",
    "user_pain_points": [
        "기존 타이머는 서랍 공간을 차지함",
        "둥근 타이머는 굴러다녀서 찾기 어려움",
        "요리 중 손이 젖어 있어도 조작해야 함",
    ],
    "product_differentiators": [
        "접으면 신용카드 두께",
        "냉장고에 자석으로 부착 가능",
        "터치 한 번으로 1분 추가",
    ],
    "emotional_benefit": "주방을 깔끔하게 유지하면서 요리에만 집중할 수 있는 해방감",
    "target_emotion": "손실회피",
}


def _print_script(label: str, script) -> None:
    print(f"\n{'─' * 50}")
    print(f"  {label}")
    print(f"{'─' * 50}")
    print(f"  [커버 문구]   {script.cover_text}")
    print(f"\n  [후킹 Hook]")
    print(f"  {script.hook}")
    print(f"\n  [공감·해결 Body]")
    print(f"  {script.body}")
    print(f"\n  [CTA]")
    print(f"  {script.cta}")
    print(f"\n  [자막 타임라인]")
    for cue in script.subtitle_timeline:
        print(f"    {cue.start_sec:5.1f}s ~ {cue.end_sec:5.1f}s │ {cue.text}")


async def run_standalone(ab_test: bool = False) -> None:
    """DB 없이 SAMPLE_ANALYSIS로 독립 실행."""
    from processor.claude_writer import generate_script
    from processor.ab_test import generate_ab_scripts

    print("\n" + "=" * 60)
    print("  processor 모듈 테스트 (독립 모드)")
    print("=" * 60)
    print(f"  제품: {SAMPLE_ANALYSIS['product_name']}")
    print(f"  전략: {SAMPLE_ANALYSIS['target_emotion']}")
    print(f"  A/B:  {'ON' if ab_test else 'OFF'}")

    if ab_test:
        ab = generate_ab_scripts(SAMPLE_ANALYSIS)
        _print_script("A버전 스크립트", ab.variant_a)
        _print_script("B버전 스크립트", ab.variant_b)
    else:
        script = generate_script(SAMPLE_ANALYSIS)
        _print_script("스크립트", script)

    print("\n" + "=" * 60)
    print("  processor 파이프라인 완료!")
    print("=" * 60)


async def run_with_db(job_id_str: str, ab_test: bool = False) -> None:
    """기존 Job의 gemini_analysis를 읽어 처리."""
    import uuid
    from dashboard.db import AsyncSessionLocal
    from processor.service import ProcessorService

    job_id = uuid.UUID(job_id_str)
    print(f"\n  job_id: {job_id} | ab_test: {ab_test}")

    async with AsyncSessionLocal() as db:
        svc = ProcessorService(db)
        job = await svc.run(job_id=job_id, ab_test=ab_test)

    print(f"\n  status : {job.status}")
    print(f"  script A cover: {(job.script or {}).get('cover_text', 'N/A')}")
    if ab_test and job.script_variant_b:
        print(f"  script B cover: {job.script_variant_b.get('cover_text', 'N/A')}")


if __name__ == "__main__":
    args = sys.argv[1:]
    ab_test = "--ab-test" in args

    if "--job-id" in args:
        idx = args.index("--job-id")
        job_id = args[idx + 1]
        asyncio.run(run_with_db(job_id, ab_test=ab_test))
    else:
        asyncio.run(run_standalone(ab_test=ab_test))
