"""
Gemini 1.5 Pro를 사용해 Instagram 영상을 분석하는 모듈.

영상 파일을 File API로 업로드한 뒤,
제품 특징 / 사용 장면 / 고통 포인트 / 차별점 / 정서적 혜택을 JSON으로 추출한다.
"""
import json
import logging
import time
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from config import settings
from collector.schemas import GeminiAnalysis

logger = logging.getLogger(__name__)

_ANALYSIS_PROMPT = """
아래 인스타그램 영상을 분석해줘.

다음 항목을 한국어로 정확하게 추출해서 JSON만 반환해줘 (다른 텍스트 없이):

{
  "product_name": "제품명 또는 주요 주제 (예: 접이식 주방 타이머)",
  "visual_features": ["시각적으로 보이는 특징1", "특징2", ...],
  "use_case_scene": "영상에서 실제로 어떤 상황/장면이 보이는지 구체적으로 묘사",
  "user_pain_points": ["이 제품이 해결하는 불편함1", "불편함2", ...],
  "product_differentiators": ["기존 제품 대비 차별점1", "차별점2", ...],
  "emotional_benefit": "이 제품이 시청자에게 주는 핵심 정서적 혜택 (예: 요리 시간 단축으로 인한 해방감)",
  "target_emotion": "손실회피 또는 이득강조 또는 호기심 중 하나만"
}

규칙:
- JSON 외에 다른 텍스트를 절대 포함하지 마
- target_emotion은 반드시 "손실회피", "이득강조", "호기심" 셋 중 하나여야 해
- 모든 값은 한국어로 작성해
"""


def _upload_video(client: genai.Client, video_path: str):
    """영상을 Gemini File API에 업로드하고 처리 완료까지 대기한다."""
    logger.info("Gemini File API에 영상 업로드 중: %s", video_path)

    with open(video_path, "rb") as f:
        video_file = client.files.upload(
            file=f,
            config=genai_types.UploadFileConfig(mime_type="video/mp4"),
        )

    # 파일 처리 완료 대기 (PROCESSING → ACTIVE)
    max_wait = 120  # 최대 2분
    waited = 0
    poll_interval = 5

    while video_file.state.name == "PROCESSING":
        if waited >= max_wait:
            raise TimeoutError(
                f"Gemini 파일 처리 타임아웃 ({max_wait}초 초과): {video_file.name}"
            )
        logger.info("파일 처리 중... (%ds 경과)", waited)
        time.sleep(poll_interval)
        waited += poll_interval
        video_file = client.files.get(name=video_file.name)

    if video_file.state.name != "ACTIVE":
        raise RuntimeError(
            f"Gemini 파일 처리 실패. 상태: {video_file.state.name}"
        )

    logger.info("파일 업로드 완료: %s", video_file.name)
    return video_file


def _parse_gemini_response(raw: str) -> GeminiAnalysis:
    """Gemini 응답에서 JSON을 추출하고 GeminiAnalysis로 파싱한다."""
    # 마크다운 코드블록 제거
    text = raw.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        # 첫 줄(```json 또는 ```) 과 마지막 줄(```) 제거
        text = "\n".join(lines[1:-1])

    data = json.loads(text)
    return GeminiAnalysis(**data)


def analyze_video(video_path: str) -> GeminiAnalysis:
    """
    MP4 파일을 Gemini 1.5 Pro로 분석해 GeminiAnalysis를 반환한다.

    Args:
        video_path: 로컬 MP4 파일 경로

    Returns:
        GeminiAnalysis — 제품 분석 결과

    Raises:
        FileNotFoundError: 영상 파일이 없을 때
        ValueError: Gemini 응답 파싱 실패 시
        RuntimeError: Gemini API 오류 시
    """
    if not Path(video_path).exists():
        raise FileNotFoundError(f"영상 파일을 찾을 수 없습니다: {video_path}")

    client = genai.Client(api_key=settings.gemini_api_key)

    # 1. 영상 업로드
    video_file = _upload_video(client, video_path)

    raw_text = ""
    try:
        # 2. Gemini 1.5 Pro로 분석 요청
        logger.info("Gemini 1.5 Pro 영상 분석 요청 중...")

        response = client.models.generate_content(
            model="gemini-1.5-pro",
            contents=[
                genai_types.Part.from_uri(
                    file_uri=video_file.uri,
                    mime_type="video/mp4",
                ),
                _ANALYSIS_PROMPT,
            ],
            config=genai_types.GenerateContentConfig(
                temperature=0.2,
                max_output_tokens=1024,
            ),
        )

        raw_text = response.text
        logger.debug("Gemini 원본 응답:\n%s", raw_text)

        # 3. JSON 파싱
        analysis = _parse_gemini_response(raw_text)
        logger.info("영상 분석 완료: product_name=%s", analysis.product_name)
        return analysis

    except json.JSONDecodeError as e:
        raise ValueError(f"Gemini 응답 JSON 파싱 실패: {e}\n응답: {raw_text}") from e

    finally:
        # 4. 업로드된 파일 정리 (비용/보안)
        try:
            client.files.delete(name=video_file.name)
            logger.info("Gemini 임시 파일 삭제: %s", video_file.name)
        except Exception as cleanup_err:
            logger.warning("Gemini 파일 삭제 실패 (무시): %s", cleanup_err)
