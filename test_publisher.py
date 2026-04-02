"""
publisher 모듈 동작 확인 스크립트.

테스트 모드:

  1. 단위 테스트 (의존성 없음) — 기본 실행
     python test_publisher.py
     python test_publisher.py --unit

  2. 메타데이터 생성 테스트 (ANTHROPIC_API_KEY 필요)
     python test_publisher.py --meta instagram
     python test_publisher.py --meta youtube
     python test_publisher.py --meta tiktok

  3. Telegram 알림 테스트 (TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID 필요)
     python test_publisher.py --notify

  4. 전체 업로드 플로우 모킹 테스트 (API 키 불필요)
     python test_publisher.py --mock-upload [instagram|youtube|tiktok]

  5. Celery 태스크 수동 디스패치 (Redis + .env 필요)
     python test_publisher.py --dispatch <JOB_ID>
"""
import json
import logging
import sys
from unittest.mock import patch, MagicMock

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

SAMPLE_ANALYSIS = {
    "product_name": "접이식 주방 타이머",
    "visual_features": ["카드 두께로 접힘", "자석 부착"],
    "use_case_scene": "주방에서 요리 중 타이머 사용",
    "user_pain_points": ["서랍 공간 차지", "분실"],
    "product_differentiators": ["카드 두께", "냉장고 자석"],
    "emotional_benefit": "주방 정리 해방감",
    "target_emotion": "손실회피",
}

SAMPLE_SCRIPT = {
    "cover_text": "이 타이머 모르면 주방 정리 포기해",
    "hook": "혹시 타이머 찾느라 냄비 다 넘친 적 있지 않으세요?",
    "body": "냉장고에 딱 붙어있는 이 타이머, 카드처럼 얇아요.",
    "cta": "댓글로 공유해주세요!",
    "subtitle_timeline": [],
}


# ─────────────────────────────────────────────────────────────────────

def test_unit():
    """의존성 없이 스키마·알림·프롬프트·미디어 URL 로직을 검증한다."""
    print("\n" + "=" * 60)
    print("  [Unit] publisher 모듈 단위 테스트")
    print("=" * 60 + "\n")

    # ── 1. 스키마 검증 ─────────────────────────────────────────
    from publisher.schemas import UploadResult, PlatformMeta

    ok = UploadResult(platform="instagram", success=True, post_id="123", post_url="https://ig.com/p/123/")
    fail = UploadResult(platform="youtube", success=False, error_message="quota exceeded")
    assert ok.success and ok.post_id == "123"
    assert not fail.success and "quota" in fail.error_message
    print(f"  ✓ UploadResult 성공: post_id={ok.post_id}")
    print(f"  ✓ UploadResult 실패: error={fail.error_message}")

    meta = PlatformMeta(
        title="접이식 타이머의 비밀",
        description="주방 서랍 정리 끝! #주방꿀팁",
        hashtags=["#주방꿀팁", "#생활꿀팁", "#타이머"],
        tags=["kitchen timer", "foldable"],
        trending_sound_id="sound_123",
    )
    assert meta.trending_sound_id == "sound_123"
    print(f"  ✓ PlatformMeta: title='{meta.title}' | sound={meta.trending_sound_id}")

    # ── 2. Telegram 메시지 포맷 ────────────────────────────────
    from publisher import notifier
    with patch("publisher.notifier._send") as mock_send:
        notifier.notify_success("job-001", "instagram", "https://ig.com/p/abc/")
        notifier.notify_failure("job-002", "youtube", "quota exceeded")
        calls = mock_send.call_args_list
        assert "✅" in calls[0][0][0] and "INSTAGRAM" in calls[0][0][0]
        assert "❌" in calls[1][0][0] and "YOUTUBE" in calls[1][0][0]
        print(f"  ✓ Telegram 성공 알림: {calls[0][0][0][:55].strip()}...")
        print(f"  ✓ Telegram 실패 알림: {calls[1][0][0][:55].strip()}...")

    # ── 3. 플랫폼 프롬프트 조립 ───────────────────────────────
    from publisher.platform_formatter import (
        _format_analysis, _INSTAGRAM_PROMPT, _YOUTUBE_PROMPT, _TIKTOK_PROMPT
    )
    formatted = _format_analysis(SAMPLE_ANALYSIS)
    for platform, tpl in [
        ("instagram", _INSTAGRAM_PROMPT),
        ("youtube", _YOUTUBE_PROMPT),
        ("tiktok", _TIKTOK_PROMPT),
    ]:
        prompt = tpl.format(analysis=formatted, cover_text=SAMPLE_SCRIPT["cover_text"])
        assert "접이식 주방 타이머" in prompt
        print(f"  ✓ {platform} 프롬프트 조립: {len(prompt)}자")

    # ── 4. 미디어 공개 URL 변환 ────────────────────────────────
    from publisher.media_host import get_public_url
    with patch.dict("os.environ", {"MEDIA_PUBLIC_BASE_URL": "http://localhost:8000"}):
        url = get_public_url("./media/ABC123/final_output.mp4")
        assert "ABC123" in url and url.startswith("http://localhost:8000")
        print(f"  ✓ 미디어 URL 변환: ./media/ABC123/... → {url}")

    # ── 5. Celery Beat 스케줄 설정 ────────────────────────────
    from publisher.celery_app import celery_app
    schedule = celery_app.conf.beat_schedule
    assert "check-pending-jobs" in schedule
    assert schedule["check-pending-jobs"]["schedule"] == 60.0
    print(f"  ✓ Celery Beat 스케줄: {list(schedule.keys())} (60초 간격)")

    # ── 6. TikTok 트렌딩 사운드 조회 (토큰 없을 때 빈 리스트) ──
    from publisher.tiktok import get_trending_sounds
    from config import settings
    original_token = settings.tiktok_access_token
    settings.tiktok_access_token = ""
    sounds = get_trending_sounds(keyword="타이머")
    assert sounds == []
    settings.tiktok_access_token = original_token
    print(f"  ✓ TikTok 트렌딩 사운드 (토큰 없음): 빈 리스트 반환")

    print("\n  모든 단위 테스트 통과!\n")


# ─────────────────────────────────────────────────────────────────────

def test_mock_upload(platform: str = "instagram"):
    """각 플랫폼 업로더를 모킹해서 전체 흐름을 검증한다."""
    print(f"\n{'=' * 60}")
    print(f"  [Mock Upload] {platform.upper()} 업로드 플로우 테스트")
    print(f"{'=' * 60}\n")

    from publisher.schemas import PlatformMeta, UploadResult

    meta = PlatformMeta(
        title="접이식 타이머의 비밀",
        description="주방 정리 끝! 이 타이머 하나로",
        hashtags=["#주방꿀팁"] * (30 if platform == "instagram" else 10),
        tags=["timer", "kitchen"] if platform == "youtube" else [],
        trending_sound_id="sound_789" if platform == "tiktok" else None,
    )

    if platform == "instagram":
        with patch("publisher.instagram.httpx.post") as mock_post, \
             patch("publisher.instagram.httpx.get") as mock_get:

            # 1. 컨테이너 생성
            mock_post.side_effect = [
                MagicMock(status_code=200, json=lambda: {"id": "container_456"}),
                MagicMock(status_code=200, json=lambda: {"id": "media_789"}),
            ]
            mock_post.return_value.raise_for_status = lambda: None

            # 2. 상태 폴링 → FINISHED
            mock_get.return_value = MagicMock(
                status_code=200,
                json=lambda: {"status_code": "FINISHED"},
            )
            mock_get.return_value.raise_for_status = lambda: None

            from publisher.instagram import upload_reel
            result = upload_reel("https://example.com/video.mp4", meta)

    elif platform == "youtube":
        import io
        from unittest.mock import mock_open

        # access_token 갱신 응답
        mock_token_resp = MagicMock()
        mock_token_resp.raise_for_status = MagicMock()
        mock_token_resp.json.return_value = {"access_token": "ya29.test"}

        # resumable 세션 시작 응답 (Location 헤더 포함)
        mock_init_resp = MagicMock()
        mock_init_resp.raise_for_status = MagicMock()
        mock_init_resp.headers = {"Location": "https://upload.googleapis.com/resumable/abc"}
        mock_init_resp.json.return_value = {}

        # 파일 업로드 완료 응답
        mock_put_resp = MagicMock()
        mock_put_resp.status_code = 200
        mock_put_resp.raise_for_status = MagicMock()
        mock_put_resp.json.return_value = {"id": "dQw4w9WgXcQ", "kind": "youtube#video"}

        fake_data = b"\x00" * 1024
        with patch("publisher.youtube.httpx.post", side_effect=[mock_token_resp, mock_init_resp]), \
             patch("publisher.youtube.httpx.put", return_value=mock_put_resp), \
             patch("publisher.youtube.Path") as mock_path, \
             patch("builtins.open", mock_open(read_data=fake_data)):
            mock_path.return_value.stat.return_value.st_size = 1024
            from publisher.youtube import upload_short
            result = upload_short("/fake/video.mp4", meta)

    elif platform == "tiktok":
        from unittest.mock import mock_open

        mock_init_resp = MagicMock()
        mock_init_resp.raise_for_status = MagicMock()
        mock_init_resp.json.return_value = {"data": {
            "publish_id": "pub_123",
            "upload_url": "https://upload.tiktok.com/abc",
        }}

        mock_poll_resp = MagicMock()
        mock_poll_resp.raise_for_status = MagicMock()
        mock_poll_resp.json.return_value = {"data": {
            "status": "PUBLISH_COMPLETE",
            "publicaly_available_post_id": ["7001234567890"],
        }}

        mock_put_resp = MagicMock()
        mock_put_resp.status_code = 200
        mock_put_resp.raise_for_status = MagicMock()

        fake_data = b"\x00" * 1024
        with patch("publisher.tiktok.httpx.post", side_effect=[mock_init_resp, mock_poll_resp]), \
             patch("publisher.tiktok.httpx.put", return_value=mock_put_resp), \
             patch("publisher.tiktok.Path") as mock_path, \
             patch("builtins.open", mock_open(read_data=fake_data)):
            mock_path.return_value.stat.return_value.st_size = 1024
            from publisher.tiktok import upload_video
            result = upload_video("/fake/video.mp4", meta)

    print(f"  platform    : {result.platform}")
    print(f"  success     : {result.success}")
    print(f"  post_id     : {result.post_id}")
    print(f"  post_url    : {result.post_url}")
    if result.error_message:
        print(f"  error       : {result.error_message}")
    assert result.success, f"업로드 실패: {result.error_message}"
    print(f"\n  {platform} 모킹 업로드 테스트 통과!")


# ─────────────────────────────────────────────────────────────────────

def test_meta(platform: str = "instagram"):
    """Claude API로 실제 메타데이터를 생성한다 (ANTHROPIC_API_KEY 필요)."""
    from publisher.platform_formatter import generate_meta

    print(f"\n{'=' * 60}")
    print(f"  [Meta] {platform.upper()} 메타데이터 생성 테스트")
    print(f"{'=' * 60}\n")

    meta = generate_meta(platform, SAMPLE_ANALYSIS, SAMPLE_SCRIPT)

    print(f"  제목     : {meta.title}")
    print(f"  설명     : {meta.description[:60]}...")
    print(f"  해시태그 : {len(meta.hashtags)}개")
    for h in meta.hashtags[:5]:
        print(f"    {h}")
    if platform == "youtube" and meta.tags:
        print(f"  태그 : {meta.tags[:5]}")
    if platform == "tiktok" and meta.trending_sound_id:
        print(f"  트렌딩 사운드 ID: {meta.trending_sound_id}")

    if platform == "instagram":
        assert len(meta.hashtags) <= 30, f"해시태그 {len(meta.hashtags)}개 > 30개"
    print(f"\n  {platform} 메타데이터 생성 완료!")


def test_notify():
    """Telegram 봇 알림을 실제로 전송한다 (토큰 필요)."""
    from publisher.notifier import notify_success, notify_failure
    print("\n=== [Notify] Telegram 알림 전송 테스트 ===\n")
    notify_success("test-job-001", "instagram", "https://www.instagram.com/p/test/")
    print("  성공 알림 전송 완료")
    notify_failure("test-job-002", "youtube", "API quota exceeded: 403 Forbidden")
    print("  실패 알림 전송 완료")


def test_dispatch(job_id: str):
    """Celery로 업로드 태스크를 수동 디스패치한다 (Redis 필요)."""
    from publisher.tasks import upload_job
    print(f"\n=== [Dispatch] 업로드 태스크 디스패치 | job_id={job_id} ===\n")
    async_result = upload_job.delay(job_id)
    print(f"  task_id : {async_result.id}")
    print(f"  상태    : {async_result.status}")
    print("\n  Celery 워커가 실행 중이면 자동 처리됩니다.")
    print("  워커 실행: ./start_worker.sh")


# ─────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or "--unit" in args:
        test_unit()

    elif "--mock-upload" in args:
        idx = args.index("--mock-upload")
        platform = args[idx + 1] if len(args) > idx + 1 and not args[idx + 1].startswith("--") else "instagram"
        test_mock_upload(platform)

    elif "--meta" in args:
        idx = args.index("--meta")
        platform = args[idx + 1] if len(args) > idx + 1 else "instagram"
        test_meta(platform)

    elif "--notify" in args:
        test_notify()

    elif "--dispatch" in args:
        idx = args.index("--dispatch")
        test_dispatch(args[idx + 1])

    else:
        print(__doc__)
