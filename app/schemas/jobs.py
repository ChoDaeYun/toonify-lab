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


class JobCreateRequest(BaseModel):
    image_id: str = Field(min_length=1)
    style: ToonifyStyle = ToonifyStyle.cartoon
    prompt: str | None = Field(default=None, max_length=2000)


class JobResponse(BaseModel):
    id: str
    image_id: str
    style: ToonifyStyle
    prompt: str | None = None
    status: JobStatus
    result_path: str | None = None
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime


class PromptDefaultsResponse(BaseModel):
    prompt: str
