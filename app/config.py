from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Toonify Lab"
    app_env: str = "local"
    upload_dir: Path = Path("uploads")
    result_dir: Path = Path("generated")
    max_upload_size_mb: int = Field(default=10, ge=1, le=100)
    image_provider: str = "mock"
    openai_api_key: str | None = None
    openai_image_model: str = "gpt-image-1.5"
    openai_image_size: str = "1024x1024"
    comfyui_base_url: str = "http://127.0.0.1:8188"
    comfyui_workflow_path: Path = Path("workflows/toonify_img2img.json")
    comfyui_timeout_seconds: int = Field(default=300, ge=1, le=3600)

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()
