"""
reelsbot FastAPI 앱 엔트리포인트.

실행:
  uvicorn dashboard.main:app --reload --port 8000
"""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import settings
from dashboard.routers import jobs, calendar, analytics, templates


@asynccontextmanager
async def lifespan(app: FastAPI):
    # media/ 디렉터리가 없으면 생성
    Path(settings.media_storage_path).mkdir(parents=True, exist_ok=True)
    yield


app = FastAPI(
    title="reelsbot API",
    description="Instagram 영상을 AI로 재편집해 SNS에 예약 업로드하는 서비스",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS — React 개발 서버 허용
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(jobs.router)
app.include_router(calendar.router)
app.include_router(analytics.router)
app.include_router(templates.router)

# media/ 정적 파일 서빙 (Instagram 업로드용 공개 URL)
_media_path = Path(settings.media_storage_path)
_media_path.mkdir(parents=True, exist_ok=True)
app.mount("/media", StaticFiles(directory=str(_media_path)), name="media")


@app.get("/health")
async def health():
    return {"status": "ok", "version": "1.0.0"}
