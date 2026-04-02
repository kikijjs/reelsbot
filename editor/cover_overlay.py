"""
커버 문구 오버레이 모듈.

첫 3초 동안 영상 중앙에 반투명 배경과 함께 커버 텍스트를 렌더링한다.
Pillow로 RGBA 이미지를 직접 그린 뒤 MoviePy ImageClip으로 합성한다.
"""
import logging
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy import ImageClip

logger = logging.getLogger(__name__)

_FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf",
    "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
]


def _find_font(size: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in _FONT_CANDIDATES:
        if Path(path).exists():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _make_cover_image(
    text: str,
    width: int,
    height: int,
    font_size: int = 72,
    text_color: tuple = (255, 255, 255),
    bg_color: tuple = (0, 0, 0, 160),
    padding: int = 40,
) -> np.ndarray:
    """
    커버 문구를 담은 RGBA 이미지 배열을 생성한다.
    화면 중앙 40% 위치에 반투명 박스와 텍스트를 렌더링한다.
    """
    font = _find_font(font_size)

    dummy = Image.new("RGBA", (1, 1))
    draw = ImageDraw.Draw(dummy)
    bbox = draw.textbbox((0, 0), text, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]

    box_w = min(text_w + padding * 2, int(width * 0.90))
    box_h = text_h + padding * 2

    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    box_x = (width - box_w) // 2
    box_y = int(height * 0.40) - box_h // 2

    draw.rounded_rectangle(
        [box_x, box_y, box_x + box_w, box_y + box_h],
        radius=20,
        fill=bg_color,
    )

    text_x = box_x + (box_w - text_w) // 2
    text_y = box_y + padding
    draw.text((text_x, text_y), text, font=font, fill=text_color)

    return np.array(img)


def build_cover_clip(
    cover_text: str,
    video_width: int,
    video_height: int,
    duration_sec: float = 3.0,
    font_size: int = 72,
) -> ImageClip:
    """
    커버 문구 오버레이 클립을 생성한다 (MoviePy 2.x).

    Args:
        cover_text: 표시할 커버 텍스트
        video_width / video_height: 영상 해상도 (px)
        duration_sec: 오버레이 표시 시간 (초)

    Returns:
        ImageClip — 0초~duration_sec 동안 표시
    """
    logger.info("커버 오버레이 생성: '%s' (%.1fs)", cover_text, duration_sec)

    img_array = _make_cover_image(
        text=cover_text,
        width=video_width,
        height=video_height,
        font_size=font_size,
    )

    clip = ImageClip(img_array, transparent=True, duration=duration_sec)
    return clip
