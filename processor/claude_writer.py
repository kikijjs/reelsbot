"""
Claude claude-sonnet-4-20250514으로 한국어 숏폼 스크립트를 생성하는 모듈.

Gemini가 추출한 GeminiAnalysis JSON을 입력받아 5파트 스크립트를 반환한다.
"""
import json
import logging

import anthropic

from config import settings
from processor.schemas import Script5Parts
from processor.prompt_templates import build_script_prompt

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"
MAX_TOKENS = 2048


def _parse_claude_response(raw: str) -> Script5Parts:
    """Claude 응답에서 JSON을 추출하고 Script5Parts로 파싱한다."""
    text = raw.strip()

    # 마크다운 코드블록 제거
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])

    data = json.loads(text)
    return Script5Parts(**data)


def generate_script(analysis: dict, emotion_strategy: str = "") -> Script5Parts:
    """
    Gemini 분석 결과를 바탕으로 Claude로 5파트 스크립트를 생성한다.

    Args:
        analysis: GeminiAnalysis.model_dump() 딕셔너리
        emotion_strategy: 감정 전략 힌트 ("손실회피" / "이득강조" / "호기심")
                          비어있으면 analysis의 target_emotion 사용

    Returns:
        Script5Parts — cover_text, hook, body, cta, subtitle_timeline

    Raises:
        ValueError: Claude 응답 파싱 실패 시
        anthropic.APIError: API 호출 오류 시
    """
    if not settings.anthropic_api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요."
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    prompt = build_script_prompt(analysis, emotion_strategy=emotion_strategy)
    logger.info(
        "Claude 스크립트 생성 요청 | 제품: %s | 전략: %s",
        analysis.get("product_name"),
        emotion_strategy or analysis.get("target_emotion"),
    )

    raw_text = ""
    try:
        message = client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        raw_text = message.content[0].text
        logger.debug("Claude 원본 응답:\n%s", raw_text)

        script = _parse_claude_response(raw_text)
        logger.info(
            "스크립트 생성 완료 | cover_text: %s", script.cover_text[:30]
        )
        return script

    except json.JSONDecodeError as e:
        raise ValueError(
            f"Claude 응답 JSON 파싱 실패: {e}\n응답: {raw_text}"
        ) from e
