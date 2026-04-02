"""
A/B 테스트 스크립트 생성 모듈.

동일한 Gemini 분석 결과에 대해 서로 다른 감정 전략으로
스크립트 2버전을 동시에 생성한다.
"""
import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

from processor.claude_writer import generate_script
from processor.prompt_templates import build_ab_prompt_pair
from processor.schemas import ABTestScript, Script5Parts

logger = logging.getLogger(__name__)


def generate_ab_scripts(analysis: dict) -> ABTestScript:
    """
    A/B 테스트용 스크립트 2버전을 동시에 생성한다.

    ThreadPoolExecutor로 두 Claude API 호출을 병렬 실행하여 대기 시간을 줄인다.

    Args:
        analysis: GeminiAnalysis.model_dump() 딕셔너리

    Returns:
        ABTestScript — variant_a (primary 전략) + variant_b (대안 전략)
    """
    primary_emotion = analysis.get("target_emotion", "이득강조")
    all_emotions = ["손실회피", "이득강조", "호기심"]
    secondary_emotion = next(e for e in all_emotions if e != primary_emotion)

    logger.info(
        "A/B 스크립트 병렬 생성 | A: %s | B: %s",
        primary_emotion,
        secondary_emotion,
    )

    def _gen_a() -> Script5Parts:
        return generate_script(analysis, emotion_strategy=primary_emotion)

    def _gen_b() -> Script5Parts:
        return generate_script(analysis, emotion_strategy=secondary_emotion)

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(_gen_a)
        future_b = executor.submit(_gen_b)
        variant_a = future_a.result()
        variant_b = future_b.result()

    logger.info("A/B 스크립트 생성 완료")
    return ABTestScript(variant_a=variant_a, variant_b=variant_b)
