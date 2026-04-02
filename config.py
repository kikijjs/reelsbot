from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # AI
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # DB
    database_url: str = "postgresql+asyncpg://reelsbot:reelsbot@localhost:5432/reelsbot"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # 파일 저장
    media_storage_path: str = "./media"

    # 텔레그램
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""


settings = Settings()
