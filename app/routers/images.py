from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import get_settings
from app.schemas.images import ImageUploadResponse
from app.services.storage import save_upload_file


router = APIRouter(prefix="/api/images", tags=["images"])

ALLOWED_CONTENT_TYPES = {
    "image/jpeg": ".jpg",
    "image/png": ".png",
    "image/webp": ".webp",
}


@router.post(
    "/upload",
    response_model=ImageUploadResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
    settings = get_settings()

    if file.content_type not in ALLOWED_CONTENT_TYPES:
        allowed = ", ".join(sorted(ALLOWED_CONTENT_TYPES))
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported image type. Allowed types: {allowed}",
        )

    saved_file = await save_upload_file(
        file=file,
        upload_dir=settings.upload_dir,
        max_size_bytes=settings.max_upload_size_bytes,
        extension=ALLOWED_CONTENT_TYPES[file.content_type],
    )

    return ImageUploadResponse(
        id=saved_file.id,
        filename=saved_file.filename,
        content_type=file.content_type,
        size_bytes=saved_file.size_bytes,
        path=str(saved_file.path),
    )
