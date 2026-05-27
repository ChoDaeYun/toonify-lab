from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status


@dataclass(frozen=True)
class SavedUploadFile:
    id: str
    filename: str
    path: Path
    size_bytes: int


async def save_upload_file(
    file: UploadFile,
    upload_dir: Path,
    max_size_bytes: int,
    extension: str,
) -> SavedUploadFile:
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_id = uuid4().hex
    filename = f"{file_id}{extension}"
    destination = upload_dir / filename
    size_bytes = 0

    with destination.open("wb") as output:
        while chunk := await file.read(1024 * 1024):
            size_bytes += len(chunk)
            if size_bytes > max_size_bytes:
                output.close()
                destination.unlink(missing_ok=True)
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Uploaded image is too large.",
                )

            output.write(chunk)

    if size_bytes == 0:
        destination.unlink(missing_ok=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded image is empty.",
        )

    return SavedUploadFile(
        id=file_id,
        filename=filename,
        path=destination,
        size_bytes=size_bytes,
    )
