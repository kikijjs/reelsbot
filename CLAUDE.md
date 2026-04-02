# reelsbot — 프로젝트 설계 문서

인스타그램 영상 URL을 입력받아 AI로 재편집한 뒤
인스타그램 / 유튜브 쇼츠 / 틱톡에 예약 업로드하는 풀스택 앱.

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 언어 | Python 3.11+ |
| 백엔드 | FastAPI |
| DB | PostgreSQL |
| 태스크 큐 | Celery + Redis |
| 웹 프론트엔드 | React (웹앱) |
| 모바일 | React Native (Expo) |
| AI — 영상 분석 | Gemini 1.5 Pro |
| AI — 스크립트 | Claude claude-sonnet-4-20250514 |
| TTS | Gemini 2.5 Pro TTS (`gemini-2.5-pro-preview-tts`) |
| 영상 편집 | MoviePy + ffmpeg |
| 알림 | Telegram Bot API |

---

## 전체 디렉터리 구조

```
reelsbot/
│
├── CLAUDE.md                          # 이 파일
├── .env.example                       # 환경변수 템플릿
├── docker-compose.yml                 # PostgreSQL + Redis + 앱 컨테이너
├── pyproject.toml                     # Python 의존성 (Poetry)
├── requirements.txt                   # pip 호환용
│
├── alembic/                           # DB 마이그레이션
│   ├── env.py
│   ├── script.py.mako
│   └── versions/
│
├── collector/                         # ① URL 입력 → 영상 다운로드 → Gemini 분석
│   ├── __init__.py
│   ├── downloader.py                  # instaloader로 Instagram 영상 다운로드
│   ├── gemini_analyzer.py             # Gemini 1.5 Pro로 영상 분석 → JSON 반환
│   └── schemas.py                     # GeminiAnalysis Pydantic 모델
│
├── processor/                         # ② Gemini JSON → Claude 한국어 스크립트 생성
│   ├── __init__.py
│   ├── claude_writer.py               # Claude claude-sonnet-4-20250514 API 호출
│   ├── prompt_templates.py            # 페르소나 + 5파트 스크립트 프롬프트
│   ├── ab_test.py                     # A/B 테스트: 스크립트 2버전 생성
│   └── schemas.py                     # Script5Parts, ABTestScript Pydantic 모델
│
├── editor/                            # ③ TTS 음성 생성 + MoviePy 영상 재편집
│   ├── __init__.py
│   ├── tts_gemini.py                  # Gemini 2.5 Pro TTS → WAV → MP3 변환
│   ├── video_editor.py                # MoviePy: 음성 교체 + 자막 + 커버 오버레이
│   ├── subtitle_renderer.py           # 타임라인 기반 자막 합성
│   ├── cover_overlay.py               # 첫 3초 커버 문구 렌더링
│   └── schemas.py                     # EditConfig, SubtitleTimeline Pydantic 모델
│
├── publisher/                         # ④ SNS 예약 업로드 (Celery 큐)
│   ├── __init__.py
│   ├── celery_app.py                  # Celery 앱 설정 + Beat 스케줄러
│   ├── tasks.py                       # upload_job 태스크 (Celery)
│   ├── instagram.py                   # Meta Graph API — Reels 업로드
│   ├── youtube.py                     # YouTube Data API v3 — Shorts 업로드
│   ├── tiktok.py                      # TikTok Content Posting API — 업로드
│   ├── platform_formatter.py          # 플랫폼별 메타데이터 자동 생성
│   │   # - Instagram: 해시태그 30개 자동 생성
│   │   # - YouTube: SEO 최적화 제목 + 설명 자동 생성
│   │   # - TikTok: 트렌딩 사운드 추천
│   ├── notifier.py                    # Telegram 봇 알림 (FAILED 시)
│   └── schemas.py                     # UploadResult Pydantic 모델
│
├── analytics/                         # ⑤ 성과 추적 (업로드 후 24h/72h 수집)
│   ├── __init__.py
│   ├── collector.py                   # 각 플랫폼 API에서 조회수·좋아요·댓글 수집
│   ├── tasks.py                       # Celery 태스크: 24h/72h 후 자동 수집
│   └── schemas.py                     # PerformanceMetrics Pydantic 모델
│
├── templates_store/                   # ⑥ 성공 스크립트 템플릿 저장소
│   ├── __init__.py
│   ├── manager.py                     # 템플릿 저장 / 조회 / 추천 로직
│   └── schemas.py                     # ScriptTemplate Pydantic 모델
│
├── dashboard/                         # ⑦ FastAPI 백엔드 + 웹 대시보드
│   ├── __init__.py
│   ├── main.py                        # FastAPI 앱 엔트리포인트
│   ├── routers/
│   │   ├── jobs.py                    # CRUD: 작업 생성 / 조회 / 수정 / 삭제
│   │   ├── calendar.py                # 월별 캘린더 데이터 API
│   │   ├── analytics.py              # 퍼포먼스 카드 API
│   │   └── templates.py              # 스크립트 템플릿 API
│   ├── models/
│   │   ├── job.py                     # SQLAlchemy Job 모델
│   │   ├── performance.py             # SQLAlchemy Performance 모델
│   │   └── template.py                # SQLAlchemy Template 모델
│   ├── db.py                          # DB 세션 / 연결 설정
│   └── web/                           # React 웹앱 (빌드 산출물 서빙)
│       ├── public/
│       └── src/
│           ├── App.tsx
│           ├── components/
│           │   ├── CalendarView.tsx   # 월별 캘린더 (상태별 색상 구분)
│           │   ├── JobCard.tsx        # 상세 카드 (미리보기 + 스크립트 + 상태)
│           │   ├── PerformanceCard.tsx # 조회수·좋아요·댓글 퍼포먼스 카드
│           │   └── TemplateSelector.tsx # 템플릿 참고 선택 UI
│           ├── pages/
│           │   ├── Dashboard.tsx
│           │   ├── NewJob.tsx         # URL 입력 + 플랫폼 + 예약 시간 설정
│           │   └── JobDetail.tsx
│           └── api/
│               └── client.ts          # Axios API 클라이언트
│
└── mobile/                            # ⑧ React Native (Expo) 앱
    ├── app.json
    ├── package.json
    ├── App.tsx
    └── src/
        ├── screens/
        │   ├── HomeScreen.tsx         # URL 입력 화면
        │   ├── CalendarScreen.tsx     # 캘린더 조회 + 상태 확인
        │   ├── JobDetailScreen.tsx    # 상세 카드 (미리보기 + 스크립트)
        │   └── AnalyticsScreen.tsx    # 퍼포먼스 요약
        ├── components/
        │   ├── CalendarView.tsx       # 월별 캘린더 (react-native-calendars)
        │   ├── StatusBadge.tsx        # 상태 배지 (색상 구분)
        │   └── JobCard.tsx
        ├── notifications/
        │   └── push.ts                # Expo Push Notifications 설정
        └── api/
            └── client.ts              # Axios API 클라이언트
```

---

## 데이터 흐름 (파이프라인)

```
사용자 URL 입력
      │
      ▼
[collector/downloader.py]
  instaloader로 MP4 다운로드
      │
      ▼
[collector/gemini_analyzer.py]
  Gemini 1.5 Pro → 영상 직접 분석
  → GeminiAnalysis JSON 반환
      │
      ▼
[processor/claude_writer.py]
  Claude claude-sonnet-4-20250514 → 5파트 한국어 스크립트 생성
  (A/B 테스트: ab_test.py로 2버전 동시 생성)
      │
      ▼
[editor/tts_gemini.py]
  Gemini 2.5 Pro TTS → 파트별 Style instruction 적용
  WAV 생성 → ffmpeg으로 MP3 변환
      │
      ▼
[editor/video_editor.py]
  원본 음성 제거 → TTS 교체
  커버 문구 오버레이 (첫 3초)
  자막 합성 (타임라인 기반)
  → 최종 MP4 (9:16, 1080×1920)
      │
      ▼
[publisher/tasks.py] (Celery Beat)
  예약 시간 도달 시 자동 실행
  플랫폼별 포맷 최적화 적용
  → Instagram / YouTube Shorts / TikTok 업로드
      │
      ├─ 성공 → DB: COMPLETED
      └─ 실패 → DB: FAILED + Telegram 알림
           │
           ▼
[analytics/tasks.py] (Celery Beat)
  24h / 72h 후 조회수·좋아요·댓글 자동 수집
  → 대시보드 퍼포먼스 카드 업데이트
```

---

## DB 스키마

### jobs 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID (PK) | 작업 고유 ID |
| `instagram_url` | TEXT | 입력 Instagram 영상 URL |
| `platform` | ENUM | `instagram` / `youtube` / `tiktok` |
| `gemini_analysis` | JSONB | Gemini 분석 결과 (아래 구조 참고) |
| `script` | JSONB | Claude 생성 5파트 스크립트 |
| `script_variant_b` | JSONB | A/B 테스트용 B버전 스크립트 (nullable) |
| `tts_audio_path` | TEXT | TTS 생성 MP3 파일 경로 |
| `final_video_path` | TEXT | 최종 편집 MP4 파일 경로 |
| `tts_voice` | TEXT | 사용한 TTS 음성 ID |
| `scheduled_at` | TIMESTAMPTZ | 예약 업로드 시간 |
| `uploaded_at` | TIMESTAMPTZ | 실제 업로드 완료 시간 |
| `status` | ENUM | `PENDING` / `PROCESSING` / `COMPLETED` / `FAILED` |
| `error_message` | TEXT | 실패 시 오류 메시지 (nullable) |
| `created_at` | TIMESTAMPTZ | 생성 시각 |
| `updated_at` | TIMESTAMPTZ | 마지막 수정 시각 |

**상태 전이:** `PENDING → PROCESSING → COMPLETED / FAILED`

### performance_metrics 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID (PK) | |
| `job_id` | UUID (FK → jobs.id) | |
| `collected_at` | TIMESTAMPTZ | 수집 시각 |
| `interval_hours` | INTEGER | 24 또는 72 |
| `views` | BIGINT | 조회수 |
| `likes` | INTEGER | 좋아요 수 |
| `comments` | INTEGER | 댓글 수 |
| `shares` | INTEGER | 공유 수 (지원 플랫폼만) |

### script_templates 테이블

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `id` | UUID (PK) | |
| `name` | TEXT | 템플릿 이름 |
| `script` | JSONB | 저장된 5파트 스크립트 패턴 |
| `source_job_id` | UUID (FK, nullable) | 원본 작업 |
| `performance_score` | FLOAT | 성과 기반 점수 |
| `created_at` | TIMESTAMPTZ | |

---

## Gemini → Claude 전달 JSON 구조

```json
{
  "product_name": "제품명",
  "visual_features": ["특징1", "특징2"],
  "use_case_scene": "사용 장면 묘사",
  "user_pain_points": ["불편함1", "불편함2"],
  "product_differentiators": ["차별점1", "차별점2"],
  "emotional_benefit": "정서적 혜택 설명",
  "target_emotion": "손실회피 | 이득강조 | 호기심"
}
```

---

## Claude 스크립트 5파트 출력 구조

```json
{
  "cover_text": "커버 문구 (Thumbnail Text)",
  "hook": "후킹 문구 (첫 3초)",
  "body": "공감 및 해결 본문",
  "cta": "Call to Action",
  "subtitle_timeline": [
    { "text": "자막 텍스트", "start_sec": 0, "end_sec": 2 },
    { "text": "자막 텍스트", "start_sec": 2, "end_sec": 5 }
  ]
}
```

---

## Claude 스크립트 생성 페르소나

> 너는 인스타그램 릴스, 틱톡, 유튜브 쇼츠의 조회수를 폭발시키고 소비자 심리학을 꿰뚫고 구매 전환까지 이끌어내는 **'1% 숏폼 전략가'** 야.
> 단순히 제품을 설명하는 게 아니라, 시청자가 이 정보를 모르면 **'손해'** 를 본다고 느끼게 하거나, 이 제품 하나로 **'압도적 이득'** 을 얻을 수 있다는 확신을 주는 스크립트를 써야 해.
> 제품의 **'기능'이 아니라** 그 제품이 가져다주는 **'정서적 해방감'** 과 **'시간/에너지의 보상'** 을 파악하는 카피라이터야.

**작성 전략:**
- 과거의 고통 강조: 제품이 없었을 때의 짜증, 낭비되는 시간을 묘사
- 반전의 쾌감: "이렇게 쉬운 걸 왜 몰랐지?"라는 해방감 표현
- 말투: "~하네요", "~몰라요" 같은 친근한 구어체

---

## Gemini TTS 설정

- **모델:** `gemini-2.5-pro-preview-tts`
- **API 키:** `GEMINI_API_KEY` (Google AI Studio)
- **출력:** WAV → ffmpeg으로 MP3 변환
- **모드:** Single-speaker audio

### 파트별 Style Instruction

| 파트 | Style Instruction |
|------|-------------------|
| 후킹(Hook) | 긴박하고 에너지 넘치는 톤, 빠른 템포로 |
| 공감/해결(Body) | 친근하고 공감하는 따뜻한 톤으로 |
| CTA | 확신에 차고 강렬하게, 행동을 촉구하는 톤으로 |

---

## 영상 편집 사양

- **출력 포맷:** MP4
- **해상도:** 1080×1920 (9:16 세로형)
- **처리 내용:**
  - 원본 인스타그램 영상의 기존 음성 제거
  - Gemini TTS 음성 교체
  - 커버 문구 오버레이 (첫 3초)
  - 타임라인 기반 자막 합성

---

## 플랫폼별 자동 포맷 최적화

| 플랫폼 | 자동 생성 항목 |
|--------|---------------|
| Instagram Reels | 해시태그 30개 자동 생성 |
| YouTube Shorts | SEO 최적화 제목 + 설명 자동 생성 |
| TikTok | 트렌딩 사운드 추천 (TikTok API 연동) |

---

## 업로드 예약 시스템

- 사용자가 날짜/시간 선택 → DB에 `PENDING` 상태로 저장
- **Celery Beat**로 예약 시간에 자동 업로드 실행
- 업로드 후:
  - 성공 → `COMPLETED`
  - 실패 → `FAILED` + **Telegram 봇 알림** 발송

---

## 캘린더 UI 사양

웹(`dashboard/web`) 및 모바일(`mobile`) 모두 동일 기준 적용.

| 항목 | 내용 |
|------|------|
| 기본 뷰 | 월별 캘린더, 날짜별 예약 업로드 건수 표시 |
| 클릭 시 | 상세 카드 (영상 미리보기 + 스크립트 + 플랫폼 + 상태) |
| PENDING | 파랑 |
| PROCESSING | 노랑 |
| COMPLETED | 초록 |
| FAILED | 빨강 |
| 기능 | 예약 시간 수정 / 삭제 가능 |

---

## A/B 테스트 모드

- 동일 영상에 대해 스크립트 **2가지 버전** 생성 (`processor/ab_test.py`)
- 각각 다른 시간대에 업로드
- 업로드 후 조회수 / 참여율 비교 → 대시보드에서 확인
- DB: `script` (A버전) + `script_variant_b` (B버전) 별도 저장

---

## 성과 추적

- 업로드 후 **24h / 72h** 조회수·좋아요·댓글 수 자동 수집 (`analytics/`)
- Celery Beat 태스크로 자동 실행
- 대시보드에 **퍼포먼스 카드**로 표시

---

## 템플릿 저장

- 성과가 좋은 스크립트 패턴을 템플릿으로 저장 (`templates_store/`)
- 다음 영상 생성 시 참고 옵션으로 제공
- `performance_score` 기반 정렬

---

## 환경변수 목록 (.env)

```
# AI
GEMINI_API_KEY=                    # Google AI Studio API 키
ANTHROPIC_API_KEY=                 # Anthropic API 키

# DB
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/reelsbot

# Redis / Celery
REDIS_URL=redis://localhost:6379/0

# SNS — Instagram (Meta Graph API)
META_APP_ID=
META_APP_SECRET=
META_ACCESS_TOKEN=
META_INSTAGRAM_USER_ID=

# SNS — YouTube (Data API v3)
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
YOUTUBE_REFRESH_TOKEN=

# SNS — TikTok (Content Posting API)
TIKTOK_CLIENT_KEY=
TIKTOK_CLIENT_SECRET=
TIKTOK_ACCESS_TOKEN=

# 알림
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# 파일 저장
MEDIA_STORAGE_PATH=./media
```

---

## 개발 우선순위 (구현 순서)

1. **DB 모델 + Alembic 마이그레이션** (`dashboard/models/`, `alembic/`)
2. **collector** — 영상 다운로드 + Gemini 분석
3. **processor** — Claude 스크립트 생성 (단일 버전 먼저)
4. **editor** — TTS + MoviePy 영상 편집
5. **publisher** — Celery 태스크 + 플랫폼 업로드
6. **dashboard** — FastAPI 라우터 + React 웹앱
7. **mobile** — Expo React Native 앱
8. **analytics** + **A/B 테스트** + **templates_store** (부가 기능)
