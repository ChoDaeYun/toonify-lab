import base64
from pathlib import Path
from shutil import copyfile

from app.schemas.jobs import ToonifyModel, ToonifyStyle
from app.services.comfyui import transform_with_comfyui
from app.services.image_editing import CropBox, crop_image
from app.services.jobs import job_store


def process_toonify_job(
    job_id: str,
    source_path: Path,
    style: ToonifyStyle,
    model: ToonifyModel,
    prompt: str | None,
    width: int | None,
    height: int | None,
    crop_x: int | None,
    crop_y: int | None,
    crop_width: int | None,
    crop_height: int | None,
    result_dir: Path,
    image_provider: str = "mock",
    openai_api_key: str | None = None,
    openai_image_model: str = "gpt-image-1.5",
    openai_image_size: str = "1024x1024",
    comfyui_base_url: str = "http://127.0.0.1:8188",
    comfyui_workflow_path: Path = Path("workflows/toonify_img2img.json"),
    comfyui_timeout_seconds: int = 300,
) -> None:
    job_store.mark_processing(job_id)

    try:
        result_dir.mkdir(parents=True, exist_ok=True)
        crop_box = _build_crop_box(crop_x, crop_y, crop_width, crop_height)
        transform_source_path = crop_image(source_path, result_dir, job_id, crop_box)
        if image_provider == "openai":
            result_path = _transform_with_openai(
                source_path=transform_source_path,
                style=style,
                result_dir=result_dir,
                job_id=job_id,
                api_key=openai_api_key,
                model=openai_image_model,
                size=openai_image_size,
                prompt=prompt,
            )
        elif image_provider == "comfyui":
            result_path = transform_with_comfyui(
                source_path=transform_source_path,
                style=style,
                model=model,
                prompt=prompt,
                width=width,
                height=height,
                result_dir=result_dir,
                job_id=job_id,
                base_url=comfyui_base_url,
                workflow_path=comfyui_workflow_path,
                timeout_seconds=comfyui_timeout_seconds,
            )
        else:
            result_path = _transform_with_mock(
                source_path=transform_source_path,
                style=style,
                result_dir=result_dir,
                job_id=job_id,
            )
    except Exception as exc:
        job_store.mark_failed(job_id, str(exc))
        return

    job_store.mark_completed(job_id, result_path)


def _build_crop_box(
    crop_x: int | None,
    crop_y: int | None,
    crop_width: int | None,
    crop_height: int | None,
) -> CropBox | None:
    values = (crop_x, crop_y, crop_width, crop_height)
    if all(value is None for value in values):
        return None

    if any(value is None for value in values):
        raise ValueError("Crop area requires crop_x, crop_y, crop_width, and crop_height.")

    return CropBox(
        x=crop_x,
        y=crop_y,
        width=crop_width,
        height=crop_height,
    )


def _transform_with_mock(
    source_path: Path,
    style: ToonifyStyle,
    result_dir: Path,
    job_id: str,
) -> Path:
    result_path = result_dir / f"{job_id}-{style.value}{source_path.suffix}"
    copyfile(source_path, result_path)
    return result_path


def _transform_with_openai(
    source_path: Path,
    style: ToonifyStyle,
    result_dir: Path,
    job_id: str,
    api_key: str | None,
    model: str,
    size: str,
    prompt: str | None,
) -> Path:
    if not api_key:
        raise ValueError("OPENAI_API_KEY is required when IMAGE_PROVIDER=openai.")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    image_prompt = prompt.strip() if prompt and prompt.strip() else _build_toonify_prompt(style)

    with source_path.open("rb") as image_file:
        response = client.images.edit(
            model=model,
            image=image_file,
            prompt=image_prompt,
            size=size,
        )

    image_base64 = response.data[0].b64_json
    if not image_base64:
        raise ValueError("OpenAI image response did not include image data.")

    result_path = result_dir / f"{job_id}-{style.value}.png"
    result_path.write_bytes(base64.b64decode(image_base64))
    return result_path


def _build_toonify_prompt(style: ToonifyStyle) -> str:
    prompts = {
        ToonifyStyle.cartoon: (
            "Transform the input photo into a clean, polished cartoon portrait. "
            "Preserve the person's identity, pose, clothing, and main composition. "
            "Use smooth outlines, expressive but natural features, and bright balanced colors."
        ),
        ToonifyStyle.character: (
            "Transform the input photo into a charming character design. "
            "Preserve the subject's identity and recognizable details while making it feel like "
            "a production-ready animated character."
        ),
        ToonifyStyle.illustration: (
            "Transform the input photo into a refined editorial illustration. "
            "Preserve the original composition and key details while using painterly texture, "
            "soft lighting, and tasteful stylization."
        ),
    }
    return prompts[style]
