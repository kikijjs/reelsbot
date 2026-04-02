# reelsbot

Instagram 영상 URL을 입력받아 AI로 재편집한 뒤 Instagram Reels / YouTube Shorts / TikTok에 예약 업로드하는 풀스택 앱.

---

## 주요 기능

- **자동 영상 분석**: Gemini 1.5 Pro가 Instagram 영상을 직접 분석해 제품 특징, 페인 포인트, 감성 혜택 추출
- **AI 스크립트 생성**: Claude claude-sonnet-4-20250514가 5파트 한국어 숏폼 스크립트 생성 (후킹 → 공감 → 해결 → CTA)
- **A/B 테스트**: 동일 영상에 스크립트 2버전 생성 → 성과 비교
- **AI TTS**: Gemini 2.5 Pro TTS가 파트별 톤으로 음성 합성
- **자동 영상 편집**: 원본 음성 교체 + 커버 문구 + 타임라인 자막 합성 (1080×1920 9:16)
- **3개 플랫폼 예약 업로드**: Instagram Reels / YouTube Shorts / TikTok (Celery Beat 자동 실행)
- **성과 추적**: 업로드 후 24h/72h 조회수·좋아요·댓글 자동 수집
- **템플릿 저장**: 성과 좋은 스크립트 패턴을 저장해 재활용
- **Telegram 알림**: 업로드 실패 시 즉시 알림
- **웹 + 모바일 대시보드**: React 웹앱 + React Native (Expo) 앱

---

## 기술 스택

| 레이어 | 기술 |
|--------|------|
| 언어 | Python 3.11+ |
| 백엔드 | FastAPI |
| DB | PostgreSQL 16 |
| 태스크 큐 | Celery + Redis |
| 웹 프론트엔드 | React + Vite + TypeScript + Tailwind |
| 모바일 | React Native (Expo 51) |
| AI — 영상 분석 | Gemini 1.5 Pro |
| AI — 스크립트 | Claude claude-sonnet-4-20250514 |
| TTS | Gemini 2.5 Pro TTS |
| 영상 편집 | MoviePy 2.x + ffmpeg |
| 알림 | Telegram Bot API |

---

## 빠른 시작 (Docker Compose)

### 1. 저장소 클론

```bash
git clone https://github.com/kikijjs/reelsbot.git
cd reelsbot
```

### 2. 환경변수 설정

```bash
cp .env.example .env
# .env 파일을 열어 GEMINI_API_KEY, ANTHROPIC_API_KEY 등을 입력
```

최소 필수 키 (SNS 업로드 없이 편집까지만 테스트):

```env
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
```

### 3. 실행

```bash
docker compose up --build
```

서비스 목록:

| 서비스 | URL |
|--------|-----|
| FastAPI 백엔드 | http://localhost:8000 |
| API 문서 (Swagger) | http://localhost:8000/docs |
| React 웹 대시보드 | http://localhost:3000 |
| PostgreSQL | localhost:5432 |
| Redis | localhost:6379 |

### 4. 중지

```bash
docker compose down          # 컨테이너 중지
docker compose down -v       # 컨테이너 + 볼륨(DB) 모두 삭제
```

---

## 로컬 개발 환경 (Docker 없이)

### 사전 요구사항

- Python 3.11+
- ffmpeg (`brew install ffmpeg` / `apt install ffmpeg`)
- PostgreSQL 16
- Redis 7

### 설치

```bash
pip install -r requirements.txt
```

### DB 마이그레이션

```bash
alembic upgrade head
```

### 백엔드 실행

```bash
uvicorn dashboard.main:app --reload --port 8000
```

### Celery 워커 + Beat 실행

```bash
./start_worker.sh all     # 워커 + Beat 동시 실행 (개발용)
./start_worker.sh worker  # 워커만
./start_worker.sh beat    # Beat만
```

### 웹 프론트엔드 실행

```bash
cd dashboard/web
npm install
npm run dev   # http://localhost:5173
```

### 모바일 앱 실행

```bash
cd mobile
npm install
npx expo start
```

---

## 디렉터리 구조

```
reelsbot/
├── collector/          # ① Instagram 영상 다운로드 + Gemini 영상 분석
├── processor/          # ② Claude 한국어 스크립트 생성 + A/B 테스트
├── editor/             # ③ Gemini TTS + MoviePy 영상 편집
├── publisher/          # ④ Celery 예약 업로드 (Instagram / YouTube / TikTok)
├── analytics/          # ⑤ 24h/72h 성과 지표 수집
├── templates_store/    # ⑥ 성공 스크립트 템플릿 저장소
├── dashboard/
│   ├── routers/        # FastAPI 라우터
│   ├── models/         # SQLAlchemy 모델
│   └── web/            # React 웹 대시보드 (Vite)
├── mobile/             # React Native Expo 앱
├── alembic/            # DB 마이그레이션
├── config.py           # 환경변수 설정 (pydantic-settings)
├── docker-compose.yml
├── Dockerfile.backend
└── .env.example
```

---

## API 엔드포인트

### 작업 (Jobs)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `POST` | `/jobs/` | 새 작업 생성 (URL 입력 → 파이프라인 시작) |
| `GET` | `/jobs/` | 작업 목록 조회 (status/platform 필터, 페이지네이션) |
| `GET` | `/jobs/{id}` | 작업 상세 조회 (스크립트 포함) |
| `PATCH` | `/jobs/{id}` | 예약 시간 수정 |
| `DELETE` | `/jobs/{id}` | 작업 삭제 |

**작업 생성 예시:**

```bash
curl -X POST http://localhost:8000/jobs/ \
  -H "Content-Type: application/json" \
  -d '{
    "instagram_url": "https://www.instagram.com/reel/ABC123/",
    "platform": "instagram",
    "scheduled_at": "2025-06-01T14:00:00+09:00",
    "ab_test": false
  }'
```

### 캘린더

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/calendar/monthly` | 월별 캘린더 데이터 (`?year=2025&month=6`) |
| `GET` | `/calendar/day` | 특정 날짜 작업 목록 (`?date=2025-06-01`) |

### 분석 (Analytics)

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/analytics/{job_id}` | 작업별 24h/72h 지표 |
| `GET` | `/analytics/leaderboard` | 72h 조회수 상위 목록 |

### 템플릿

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/templates/` | 템플릿 목록 (성과 점수 순) |
| `POST` | `/templates/` | 템플릿 직접 저장 |
| `POST` | `/templates/from-job/{job_id}` | 완료된 작업에서 템플릿 생성 |
| `DELETE` | `/templates/{id}` | 템플릿 삭제 |

### 기타

| 메서드 | 경로 | 설명 |
|--------|------|------|
| `GET` | `/health` | 헬스체크 |
| `GET` | `/docs` | Swagger UI |
| `GET` | `/redoc` | ReDoc |

---

## 데이터 파이프라인

```
사용자 URL 입력 (POST /jobs/)
    │
    ▼
[collector] instaloader → MP4 다운로드
    │
    ▼
[collector] Gemini 1.5 Pro → 영상 분석 JSON
    │
    ▼
[processor] Claude claude-sonnet-4-20250514 → 5파트 스크립트
            (A/B 테스트: 2버전 병렬 생성)
    │
    ▼
[editor] Gemini 2.5 Pro TTS → 파트별 음성 합성 → MP3
    │
    ▼
[editor] MoviePy: 원본 음성 제거 → TTS 교체 → 커버 + 자막
         → 최종 MP4 (1080×1920 9:16)
    │
    ▼
[publisher] Celery Beat: 예약 시간 도달 시 자동 실행
    │
    ├── Instagram Reels (Meta Graph API)
    ├── YouTube Shorts (Data API v3)
    └── TikTok (Content Posting API v2)
         │
         ├── 성공 → COMPLETED
         └── 실패 → FAILED + Telegram 알림
              │
              ▼
         [analytics] 24h/72h 성과 수집 (Celery Beat)
```

---

## 환경변수 전체 목록

`.env.example` 참조.

---

## 테스트

```bash
# 단위 테스트 전체 실행
python test_collector.py
python test_processor.py
python test_editor.py
python test_publisher.py
python test_dashboard.py

# E2E 통합 테스트 (실제 API 키 필요)
python test_e2e_pipeline.py
```

---

## 모바일 앱 (Expo)

```bash
cd mobile
npm install
npx expo start
```

- iOS: Expo Go 앱으로 QR 코드 스캔
- Android: Expo Go 앱으로 QR 코드 스캔
- 실제 기기 푸시 알림: EAS Build 필요 (`npx eas build`)

API 서버 주소 변경:
```
mobile/src/api/client.ts → BASE_URL 또는 EXPO_PUBLIC_API_URL 환경변수
```

---

## 라이선스

MIT
