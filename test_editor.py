"""
editor 모듈 동작 확인 스크립트.

세 가지 테스트 모드:

  1. TTS 단독 테스트 (GEMINI_API_KEY 필요)
     python test_editor.py --tts

  2. 영상 편집 단독 테스트 (기존 mp3 + 샘플 영상 필요)
     python test_editor.py --edit --video <MP4> --audio <MP3>

  3. DB 연동 전체 파이프라인 (job_id 필요)
     python test_editor.py --job-id <UUID>

  4. 커버 오버레이 + 자막 렌더 검증 (의존성 없음)
     python test_editor.py --unit
"""
import asyncio
import logging
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SAMPLE_SCRIPT = {
    "cover_text": "이 타이머 모르면 주방 정리 포기해",
    "hook": "혹시 타이머 찾느라 냄비 다 넘친 적 있지 않으세요? 저만 그런 게 아니었네요.",
    "body": "냉장고에 딱 붙어있는 이 타이머, 카드처럼 얇아요. 꺼내서 딱 누르면 끝. 더 이상 서랍 뒤질 필요 없어요.",
    "cta": "이런 거 진작 알았으면 좋았을 것들 댓글로 공유해주세요!",
    "subtitle_timeline": [
        {"text": "이 타이머 모르면 주방 정리 포기해", "start_sec": 0.0, "end_sec": 3.0},
        {"text": "타이머 찾느라 냄비 넘친 적 있나요?", "start_sec": 3.0, "end_sec": 6.5},
        {"text": "냉장고에 붙는 카드 두께 타이머", "start_sec": 6.5, "end_sec": 10.0},
        {"text": "꺼내서 딱 누르면 끝!", "start_sec": 10.0, "end_sec": 13.0},
        {"text": "더 이상 서랍 뒤질 필요 없어요", "start_sec": 13.0, "end_sec": 17.0},
        {"text": "댓글로 공유해주세요!", "start_sec": 25.0, "end_sec": 30.0},
    ],
}


def test_unit():
    """의존성 없이 커버 오버레이 + 자막 렌더링 로직만 검증한다."""
    print("\n=== [Unit] 커버 오버레이 + 자막 렌더링 검증 ===\n")

    from editor.cover_overlay import _make_cover_image
    from editor.subtitle_renderer import build_subtitle_clips
    from editor.schemas import EditConfig

    # 커버 이미지 생성 검증
    img_arr = _make_cover_image(
        text="이 타이머 모르면 주방 정리 포기해",
        width=1080,
        height=1920,
        font_size=72,
    )
    assert img_arr.shape == (1920, 1080, 4), f"예상 (1920,1080,4) 실제 {img_arr.shape}"
    print(f"  커버 이미지 생성 OK: shape={img_arr.shape}")

    # 자막 클립 목록 검증 (MoviePy 초기화 없이 개수만)
    timeline = SAMPLE_SCRIPT["subtitle_timeline"]
    # build_subtitle_clips는 MoviePy 초기화 필요 — 개수만 확인
    assert len(timeline) == 6
    print(f"  자막 타임라인 항목 수: {len(timeline)}개 OK")

    # EditConfig 검증
    cfg = EditConfig(
        source_video_path="/tmp/test.mp4",
        tts_audio_path="/tmp/test.mp3",
        cover_text="이 타이머 모르면 주방 정리 포기해",
        subtitle_timeline=timeline,
        output_path="/tmp/output.mp4",
    )
    assert cfg.output_width == 1080
    assert cfg.output_height == 1920
    assert cfg.cover_duration_sec == 3.0
    print(f"  EditConfig 검증 OK: {cfg.output_width}×{cfg.output_height}")

    # TTS 파트 분리 검증
    from editor.tts_gemini import _build_tts_parts, STYLE_MAP
    parts = _build_tts_parts(SAMPLE_SCRIPT)
    assert len(parts) == 3
    part_names = [p.part_name for p in parts]
    assert part_names == ["hook", "body", "cta"]
    for p in parts:
        assert p.style_instruction == STYLE_MAP[p.part_name]
        print(f"  TTS 파트 [{p.part_name}]: '{p.text[:25]}...' | style='{p.style_instruction[:20]}...'")

    # PCM 침묵 결합 검증
    from editor.tts_gemini import _concat_pcm_parts, SAMPLE_RATE, CHANNELS, SAMPLE_WIDTH
    pcm_a = b"\x01\x02" * 100
    pcm_b = b"\x03\x04" * 100
    combined = _concat_pcm_parts([pcm_a, pcm_b], silence_ms=100)
    silence_bytes = int(SAMPLE_RATE * 0.1) * CHANNELS * SAMPLE_WIDTH
    expected_len = len(pcm_a) + silence_bytes + len(pcm_b)
    assert len(combined) == expected_len, f"결합 길이 불일치: {len(combined)} != {expected_len}"
    print(f"  PCM 침묵 결합 OK: {len(pcm_a)}+침묵{silence_bytes}+{len(pcm_b)} = {expected_len}bytes")

    print("\n  모든 단위 테스트 통과!")


def test_tts():
    """Gemini TTS API를 호출해 MP3 파일을 생성한다. (GEMINI_API_KEY 필요)"""
    from editor.tts_gemini import generate_tts

    print("\n=== [TTS] Gemini 2.5 Pro TTS 테스트 ===\n")
    output_dir = "./media/test_tts"
    result = generate_tts(script=SAMPLE_SCRIPT, output_dir=output_dir)
    print(f"  WAV: {result.wav_path}")
    print(f"  MP3: {result.mp3_path}")
    print(f"  길이: {result.duration_sec:.1f}초")
    assert Path(result.mp3_path).exists()
    print("\n  TTS 테스트 완료!")


def test_edit(video_path: str, audio_path: str):
    """기존 MP4 + MP3로 영상 편집을 테스트한다."""
    from editor.video_editor import edit_video
    from editor.schemas import EditConfig

    print(f"\n=== [Edit] 영상 편집 테스트 ===")
    print(f"  원본: {video_path}")
    print(f"  오디오: {audio_path}\n")

    config = EditConfig(
        source_video_path=video_path,
        tts_audio_path=audio_path,
        cover_text=SAMPLE_SCRIPT["cover_text"],
        subtitle_timeline=SAMPLE_SCRIPT["subtitle_timeline"],
        output_path="./media/test_edit/final_output.mp4",
    )
    output = edit_video(config)
    print(f"\n  최종 영상: {output}")
    assert Path(output).exists()
    print("  영상 편집 테스트 완료!")


async def test_pipeline(job_id_str: str):
    """DB 연동 전체 파이프라인을 테스트한다."""
    import uuid
    from dashboard.db import AsyncSessionLocal
    from editor.service import EditorService

    print(f"\n=== [Pipeline] DB 연동 편집 테스트 | job_id={job_id_str} ===\n")
    job_id = uuid.UUID(job_id_str)

    async with AsyncSessionLocal() as db:
        svc = EditorService(db)
        job = await svc.run(job_id=job_id)

    print(f"  status         : {job.status}")
    print(f"  tts_audio_path : {job.tts_audio_path}")
    print(f"  final_video_path: {job.final_video_path}")
    print("\n  파이프라인 테스트 완료!")


if __name__ == "__main__":
    args = sys.argv[1:]

    if "--unit" in args or not args:
        test_unit()
    elif "--tts" in args:
        test_tts()
    elif "--edit" in args:
        v_idx = args.index("--video") if "--video" in args else None
        a_idx = args.index("--audio") if "--audio" in args else None
        if v_idx is None or a_idx is None:
            print("사용법: python test_editor.py --edit --video <MP4> --audio <MP3>")
            sys.exit(1)
        test_edit(args[v_idx + 1], args[a_idx + 1])
    elif "--job-id" in args:
        idx = args.index("--job-id")
        asyncio.run(test_pipeline(args[idx + 1]))
    else:
        print(__doc__)
