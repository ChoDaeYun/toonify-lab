from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, HTTPException, status
from fastapi.responses import FileResponse

from app.config import get_settings
from app.schemas.jobs import HandQuality, JobCreateRequest, JobResponse, JobStatus, PromptDefaultsResponse, STYLE_LABELS, StyleOption, ToonifyModel, ToonifyStyle
from app.services.comfyui import get_default_image_size, get_default_workflow_prompt
from app.services.jobs import ToonifyJob, job_store
from app.services.processor import process_toonify_job


router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("/styles", response_model=list[StyleOption])
def get_styles() -> list[StyleOption]:
    return [StyleOption(value=s, label=STYLE_LABELS[s]) for s in ToonifyStyle]


@router.get("/prompt-defaults", response_model=PromptDefaultsResponse)
def get_prompt_defaults(
    style: ToonifyStyle = ToonifyStyle.cartoon,
    model: ToonifyModel = ToonifyModel.nova_anime_xl,
) -> PromptDefaultsResponse:
    settings = get_settings()
    width, height = get_default_image_size(settings.comfyui_workflow_path, style)
    return PromptDefaultsResponse(
        prompt=get_default_workflow_prompt(settings.comfyui_workflow_path, style),
        width=width,
        height=height,
        style=style,
        model=model,
    )


@router.post("", response_model=JobResponse, status_code=status.HTTP_201_CREATED)
def create_job(request: JobCreateRequest, background_tasks: BackgroundTasks) -> JobResponse:
    settings = get_settings()
    image_path = _find_uploaded_image(settings.upload_dir, request.image_id)

    if image_path is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Uploaded image was not found.",
        )

    prompt = request.prompt.strip() if request.prompt and request.prompt.strip() else None
    job = job_store.create(
        image_id=request.image_id,
        style=request.style,
        model=request.model,
        prompt=prompt,
        width=request.width,
        height=request.height,
        crop_x=request.crop_x,
        crop_y=request.crop_y,
        crop_width=request.crop_width,
        crop_height=request.crop_height,
        hand_quality=request.hand_quality,
        denoise=request.denoise,
    )
    background_tasks.add_task(
        process_toonify_job,
        job.id,
        image_path,
        request.style,
        request.model,
        prompt,
        request.width,
        request.height,
        request.crop_x,
        request.crop_y,
        request.crop_width,
        request.crop_height,
        settings.result_dir,
        request.hand_quality,
        request.denoise,
        settings.image_provider,
        settings.openai_api_key,
        settings.openai_image_model,
        settings.openai_image_size,
        settings.comfyui_base_url,
        settings.comfyui_workflow_path,
        settings.comfyui_timeout_seconds,
    )
    return _to_response(job)


@router.get("/{job_id}", response_model=JobResponse)
def get_job(job_id: str) -> JobResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job was not found.",
        )

    return _to_response(job)


@router.get("/{job_id}/result")
def get_job_result(job_id: str) -> FileResponse:
    job = job_store.get(job_id)
    if job is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job was not found.",
        )

    if job.status != JobStatus.completed:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Job result is not ready. Current status: {job.status}",
        )

    if job.result_path is None or not job.result_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job result file was not found.",
        )

    return FileResponse(
        path=job.result_path,
        filename=job.result_path.name,
        media_type=_guess_image_media_type(job.result_path),
    )


def _find_uploaded_image(upload_dir: Path, image_id: str) -> Path | None:
    return next(upload_dir.glob(f"{image_id}.*"), None)


def _guess_image_media_type(path: Path) -> str:
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return media_types.get(path.suffix.lower(), "application/octet-stream")


def _to_response(job: ToonifyJob) -> JobResponse:
    return JobResponse(
        id=job.id,
        image_id=job.image_id,
        style=job.style,
        model=job.model,
        prompt=job.prompt,
        width=job.width,
        height=job.height,
        crop_x=job.crop_x,
        crop_y=job.crop_y,
        crop_width=job.crop_width,
        crop_height=job.crop_height,
        hand_quality=job.hand_quality,
        denoise=job.denoise,
        status=job.status,
        result_path=str(job.result_path) if job.result_path else None,
        error_message=job.error_message,
        created_at=job.created_at,
        updated_at=job.updated_at,
    )
