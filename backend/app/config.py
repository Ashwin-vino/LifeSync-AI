import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

# Locate root .env
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = ROOT_DIR / ".env"

class Settings(BaseSettings):
    # App
    PROJECT_NAME: str = "LifeSync AI"
    ENVIRONMENT: str = "development"
    PORT: int = 8000
    FRONTEND_URL: str = "http://localhost:5173"

    # Gemini
    GEMINI_API_KEY: str

    # FalkorDB
    FALKORDB_HOST: str
    FALKORDB_PORT: int = 61973
    FALKORDB_USERNAME: str = "default"
    FALKORDB_PASSWORD: str
    FALKORDB_TLS: bool = False
    FALKORDB_GRAPH_NAME: str = "lifesync_memory"

    # Supabase
    SUPABASE_URL: str
    SUPABASE_ANON_KEY: str
    SUPABASE_SERVICE_ROLE_KEY: Optional[str] = None

    # External APIs
    WGER_API_KEY: Optional[str] = None
    USDA_API_KEY: Optional[str] = None

    model_config = SettingsConfigDict(
        env_file=ENV_FILE if ENV_FILE.exists() else None,
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
