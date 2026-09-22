"""Configuración central. Lee variables desde .env (nunca desde el código)."""
import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    api_key: str
    base_url: str
    model: str
    site_url: str
    whisper_size: str


def get_settings() -> Settings:
    return Settings(
        api_key=os.getenv("OPENROUTER_API_KEY", "").strip(),
        base_url=os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1").strip(),
        model=os.getenv("OPENROUTER_MODEL", "openai/gpt-4o-mini").strip(),
        site_url=os.getenv("APP_SITE_URL", "http://localhost:8501").strip(),
        whisper_size=os.getenv("WHISPER_MODEL_SIZE", "small").strip(),
    )
