from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class JobStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class ToonifyStyle(StrEnum):
    cartoon = "cartoon"
    character = "character"
    illustration = "illustration"


class ToonifyModel(StrEnum):
    nova_anime_xl = "novaAnimeXL_ilV190.safetensors"
    cat_tower_noobai_xl = "catTowerNoobaiXL_chenkinnoobV12.safetensors"


class JobCreateRequest(BaseModel):
    image_id: str = Field(min_length=1)
    style: ToonifyStyle = ToonifyStyle.cartoon
    model: ToonifyModel = ToonifyModel.nova_anime_xl
    prompt: str | None = Field(default=None, max_length=2000)
    width: int | None = Field(default=None, ge=256, le=1536)
    height: int | None = Field(default=None, ge=256, le=1536)
    crop_x: int | None = Field(default=None, ge=0)
    crop_y: int | None = Field(default=None, ge=0)
    crop_width: int | None = Field(default=None, ge=1)
    crop_height: int | None = Field(default=None, ge=1)


class JobResponse(BaseModel):
    id: str
    image_id: str
    style: ToonifyStyle
    model: ToonifyModel = ToonifyModel.nova_anime_xl
    prompt: str | None = None
    width: int | None = None
    height: int | None = None
    crop_x: int | None = None
    crop_y: int | None = None
    crop_width: int | None = None
    crop_height: int | None = None
    status: JobStatus
    result_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PromptDefaultsResponse(BaseModel):
    prompt: str
    width: int
    height: int
    style: ToonifyStyle
    model: ToonifyModel
