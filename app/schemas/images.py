from pydantic import BaseModel


class ImageUploadResponse(BaseModel):
    id: str
    filename: str
    content_type: str
    size_bytes: int
    path: str
