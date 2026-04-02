"""
Gemini 2.5 Pro TTS로 한국어 음성을 생성하는 모듈.

스크립트 5파트 중 hook / body / cta 세 파트를 각각 다른 톤으로 합성한 뒤
하나의 MP3 파일로 결합한다.

파트별 Style Instruction:
  - hook : 긴박하고 에너지 넘치는 톤, 빠른 템포로
  - body : 친근하고 공감하는 따뜻한 톤으로
  - cta  : 확신에 차고 강렬하게, 행동을 촉구하는 톤으로
"""
import io
import logging
import struct
import subprocess
import wave
from pathlib import Path

from google import genai
from google.genai import types as genai_types

from config import settings
from editor.schemas import TTSPartConfig, TTSResult

logger = logging.getLogger(__name__)

# 파트별 Style Instruction
STYLE_MAP: dict[str, str] = {
    "hook": "긴박하고 에너지 넘치는 톤으로, 빠른 템포로 읽어줘.",
    "body": "친근하고 공감하는 따뜻한 톤으로, 자연스럽게 대화하듯 읽어줘.",
    "cta": "확신에 차고 강렬하게, 행동을 촉구하는 톤으로 읽어줘.",
}

TTS_MODEL = "gemini-2.5-pro-preview-tts"
TTS_VOICE = "Kore"          # 한국어 지원 Single-speaker 음성
SAMPLE_RATE = 24000          # Gemini TTS 기본 출력 샘플레이트
CHANNELS = 1
SAMPLE_WIDTH = 2             # 16-bit PCM


def _build_tts_parts(script: dict) -> list[TTSPartConfig]:
    """
    Script5Parts dict에서 TTS 합성할 파트 목록을 만든다.
    cover_text는 영상 오버레이로 처리하므로 제외한다.
    """
    parts = []
    for part_name in ("hook", "body", "cta"):
        text = script.get(part_name, "").strip()
        if text:
            parts.append(
                TTSPartConfig(
                    text=text,
                    style_instruction=STYLE_MAP[part_name],
                    part_name=part_name,
                )
            )
    return parts


def _synthesize_part(client: genai.Client, part: TTSPartConfig) -> bytes:
    """
    단일 파트의 텍스트를 Gemini TTS로 합성하고 raw PCM bytes를 반환한다.
    """
    prompt = f"{part.style_instruction}\n\n{part.text}"
    logger.info("TTS 합성 중 [%s]: %s...", part.part_name, part.text[:30])

    response = client.models.generate_content(
        model=TTS_MODEL,
        contents=prompt,
        config=genai_types.GenerateContentConfig(
            response_modalities=["AUDIO"],
            speech_config=genai_types.SpeechConfig(
                voice_config=genai_types.VoiceConfig(
                    prebuilt_voice_config=genai_types.PrebuiltVoiceConfig(
                        voice_name=TTS_VOICE,
                    )
                )
            ),
        ),
    )

    # 오디오 데이터 추출
    audio_data = response.candidates[0].content.parts[0].inline_data.data
    return audio_data  # raw PCM bytes


def _pcm_to_wav(pcm_data: bytes, wav_path: str) -> None:
    """raw PCM bytes를 WAV 파일로 저장한다."""
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(SAMPLE_WIDTH)
        wf.setframerate(SAMPLE_RATE)
        wf.writeframes(pcm_data)


def _wav_to_mp3(wav_path: str, mp3_path: str) -> None:
    """ffmpeg으로 WAV → MP3 변환한다."""
    cmd = [
        "ffmpeg", "-y",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-qscale:a", "2",   # VBR 고품질
        mp3_path,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg WAV→MP3 변환 실패:\n{result.stderr}")


def _get_wav_duration(wav_path: str) -> float:
    """WAV 파일의 재생 시간(초)을 반환한다."""
    with wave.open(wav_path, "rb") as wf:
        frames = wf.getnframes()
        rate = wf.getframerate()
        return frames / float(rate)


def _concat_pcm_parts(parts_pcm: list[bytes], silence_ms: int = 300) -> bytes:
    """
    여러 PCM 조각을 침묵(silence) 간격을 두고 하나로 이어붙인다.

    Args:
        parts_pcm: 각 파트의 raw PCM bytes 리스트
        silence_ms: 파트 사이 침묵 시간 (밀리초)
    """
    silence_frames = int(SAMPLE_RATE * silence_ms / 1000)
    silence_bytes = b"\x00" * (silence_frames * CHANNELS * SAMPLE_WIDTH)

    result = b""
    for i, pcm in enumerate(parts_pcm):
        result += pcm
        if i < len(parts_pcm) - 1:
            result += silence_bytes
    return result


def generate_tts(script: dict, output_dir: str) -> TTSResult:
    """
    Script5Parts dict에서 hook/body/cta를 TTS로 합성하고
    하나의 MP3 파일로 결합한다.

    Args:
        script: Script5Parts.model_dump() 딕셔너리
        output_dir: 출력 파일을 저장할 디렉터리

    Returns:
        TTSResult — WAV 경로, MP3 경로, 재생 시간(초)
    """
    if not settings.gemini_api_key:
        raise ValueError("GEMINI_API_KEY가 설정되지 않았습니다.")

    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    client = genai.Client(api_key=settings.gemini_api_key)
    parts = _build_tts_parts(script)

    if not parts:
        raise ValueError("TTS로 합성할 텍스트 파트가 없습니다.")

    # 파트별 PCM 합성
    parts_pcm: list[bytes] = []
    for part in parts:
        pcm = _synthesize_part(client, part)
        parts_pcm.append(pcm)
        logger.info("  [%s] PCM %d bytes 합성 완료", part.part_name, len(pcm))

    # PCM 결합 (파트 사이 300ms 침묵)
    combined_pcm = _concat_pcm_parts(parts_pcm, silence_ms=300)

    # WAV 저장
    wav_path = str(out / "tts_output.wav")
    _pcm_to_wav(combined_pcm, wav_path)
    duration = _get_wav_duration(wav_path)
    logger.info("WAV 저장 완료: %s (%.1fs)", wav_path, duration)

    # MP3 변환
    mp3_path = str(out / "tts_output.mp3")
    _wav_to_mp3(wav_path, mp3_path)
    logger.info("MP3 변환 완료: %s", mp3_path)

    return TTSResult(
        wav_path=wav_path,
        mp3_path=mp3_path,
        duration_sec=duration,
    )
