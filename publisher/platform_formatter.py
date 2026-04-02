"""
플랫폼별 메타데이터 자동 생성 모듈.

Claude API를 사용해 각 플랫폼에 최적화된 제목/설명/해시태그를 생성한다.

- Instagram : 해시태그 30개 자동 생성
- YouTube   : SEO 최적화 제목 + 설명 자동 생성
- TikTok    : 캡션 + 트렌딩 해시태그 추천
"""
import json
import logging

import anthropic

from config import settings
from publisher.schemas import PlatformMeta

logger = logging.getLogger(__name__)

MODEL = "claude-sonnet-4-20250514"

# ── 플랫폼별 프롬프트 ─────────────────────────────────────────────

_INSTAGRAM_PROMPT = """
아래 제품 정보와 스크립트를 바탕으로 인스타그램 릴스에 최적화된
캡션과 해시태그 30개를 생성해줘.

[제품 정보]
{analysis}

[스크립트 커버 문구]
{cover_text}

아래 JSON 형식으로만 답해줘 (다른 텍스트 없이):
{{
  "title": "릴스 커버 문구 (30자 이내)",
  "description": "인스타그램 캡션 (훅+본문+CTA, 150자 이내, 이모지 활용)",
  "hashtags": ["#해시태그1", "#해시태그2", ... (정확히 30개)]
}}

해시태그 규칙:
- 한국어 해시태그 20개 + 영어 해시태그 10개
- 제품 관련, 생활꿀팁, 구매욕구 자극 태그 혼합
- 인기 태그와 틈새 태그 균형있게
"""

_YOUTUBE_PROMPT = """
아래 제품 정보와 스크립트를 바탕으로 유튜브 쇼츠에 최적화된
제목, 설명, 태그를 생성해줘.

[제품 정보]
{analysis}

[스크립트 커버 문구]
{cover_text}

아래 JSON 형식으로만 답해줘 (다른 텍스트 없이):
{{
  "title": "SEO 최적화 제목 (60자 이내, 핵심 키워드 포함, 클릭 유도)",
  "description": "유튜브 설명 (200자 이내, 키워드 풍부하게, #Shorts 태그 포함)",
  "hashtags": ["#Shorts", "#쇼츠", "#제품관련태그", ... (10개)],
  "tags": ["키워드1", "키워드2", ... (15개, # 없는 순수 태그)]
}}
"""

_TIKTOK_PROMPT = """
아래 제품 정보와 스크립트를 바탕으로 틱톡에 최적화된
캡션과 해시태그를 생성해줘.

[제품 정보]
{analysis}

[스크립트 커버 문구]
{cover_text}

아래 JSON 형식으로만 답해줘 (다른 텍스트 없이):
{{
  "title": "틱톡 커버 문구 (20자 이내, 임팩트 있게)",
  "description": "틱톡 캡션 (100자 이내, 훅으로 시작, 이모지 적극 활용)",
  "hashtags": ["#fyp", "#foryou", "#한국틱톡", "#제품태그", ... (15개)]
}}
"""


def _call_claude(prompt: str) -> dict:
    """Claude API를 호출해 JSON 응답을 파싱한다."""
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    message = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = message.content[0].text.strip()
    if raw.startswith("```"):
        lines = raw.split("\n")
        raw = "\n".join(lines[1:-1])
    return json.loads(raw)


def _format_analysis(analysis: dict) -> str:
    return (
        f"제품명: {analysis.get('product_name', '')}\n"
        f"감정 전략: {analysis.get('target_emotion', '')}\n"
        f"정서적 혜택: {analysis.get('emotional_benefit', '')}\n"
        f"고통 포인트: {', '.join(analysis.get('user_pain_points', []))}\n"
        f"차별점: {', '.join(analysis.get('product_differentiators', []))}"
    )


def generate_instagram_meta(analysis: dict, script: dict) -> PlatformMeta:
    """인스타그램 릴스용 캡션 + 해시태그 30개를 생성한다."""
    logger.info("Instagram 메타데이터 생성 중...")
    prompt = _INSTAGRAM_PROMPT.format(
        analysis=_format_analysis(analysis),
        cover_text=script.get("cover_text", ""),
    )
    data = _call_claude(prompt)
    # 해시태그가 30개 미만이면 패딩
    hashtags = data.get("hashtags", [])[:30]
    return PlatformMeta(
        title=data.get("title", ""),
        description=data.get("description", ""),
        hashtags=hashtags,
    )


def generate_youtube_meta(analysis: dict, script: dict) -> PlatformMeta:
    """YouTube 쇼츠용 SEO 제목 + 설명 + 태그를 생성한다."""
    logger.info("YouTube 메타데이터 생성 중...")
    prompt = _YOUTUBE_PROMPT.format(
        analysis=_format_analysis(analysis),
        cover_text=script.get("cover_text", ""),
    )
    data = _call_claude(prompt)
    return PlatformMeta(
        title=data.get("title", ""),
        description=data.get("description", ""),
        hashtags=data.get("hashtags", []),
        tags=data.get("tags", []),
    )


def generate_tiktok_meta(analysis: dict, script: dict) -> PlatformMeta:
    """TikTok용 캡션 + 해시태그 + 트렌딩 사운드를 생성한다."""
    logger.info("TikTok 메타데이터 생성 중...")
    prompt = _TIKTOK_PROMPT.format(
        analysis=_format_analysis(analysis),
        cover_text=script.get("cover_text", ""),
    )
    data = _call_claude(prompt)

    # 트렌딩 사운드 추천 (제품명 키워드로 검색)
    from publisher.tiktok import get_trending_sounds
    product_name = analysis.get("product_name", "")
    sounds = get_trending_sounds(keyword=product_name, limit=3)
    trending_sound_id = sounds[0]["sound_id"] if sounds else None
    if trending_sound_id:
        logger.info("트렌딩 사운드 선택: %s (%s)", sounds[0]["title"], trending_sound_id)

    return PlatformMeta(
        title=data.get("title", ""),
        description=data.get("description", ""),
        hashtags=data.get("hashtags", []),
        trending_sound_id=trending_sound_id,
    )


def generate_meta(platform: str, analysis: dict, script: dict) -> PlatformMeta:
    """플랫폼 이름에 따라 적절한 메타데이터 생성 함수를 호출한다."""
    generators = {
        "instagram": generate_instagram_meta,
        "youtube": generate_youtube_meta,
        "tiktok": generate_tiktok_meta,
    }
    fn = generators.get(platform)
    if fn is None:
        raise ValueError(f"지원하지 않는 플랫폼: {platform}")
    return fn(analysis, script)
