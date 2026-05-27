import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

from app.schemas.jobs import ToonifyStyle


def transform_with_comfyui(
    source_path: Path,
    style: ToonifyStyle,
    prompt: str | None,
    result_dir: Path,
    job_id: str,
    base_url: str,
    workflow_path: Path,
    timeout_seconds: int,
) -> Path:
    workflow = _load_workflow(workflow_path)

    with httpx.Client(base_url=base_url, timeout=30) as client:
        uploaded_name = _upload_image(client, source_path)
        _patch_workflow(workflow, uploaded_name, style, prompt, job_id)
        prompt_id = _queue_prompt(client, workflow)
        image_info = _wait_for_result(client, prompt_id, timeout_seconds)
        image_bytes = _download_image(client, image_info)

    result_dir.mkdir(parents=True, exist_ok=True)
    result_path = result_dir / f"{job_id}-{style.value}.png"
    result_path.write_bytes(image_bytes)
    return result_path


def _load_workflow(workflow_path: Path) -> dict:
    if not workflow_path.exists():
        raise FileNotFoundError(f"ComfyUI workflow was not found: {workflow_path}")

    return json.loads(workflow_path.read_text(encoding="utf-8"))


def _upload_image(client: httpx.Client, source_path: Path) -> str:
    with source_path.open("rb") as image_file:
        response = client.post(
            "/upload/image",
            files={"image": (source_path.name, image_file, _guess_media_type(source_path))},
            data={"overwrite": "true"},
        )

    response.raise_for_status()
    return response.json()["name"]


def get_default_workflow_prompt(workflow_path: Path) -> str:
    workflow = _load_workflow(workflow_path)
    return _find_positive_prompt_node(workflow)["inputs"]["text"]


def _patch_workflow(
    workflow: dict,
    image_name: str,
    style: ToonifyStyle,
    prompt: str | None,
    job_id: str,
) -> None:
    load_image_node = _find_node(workflow, "LoadImage")
    positive_node = _find_positive_prompt_node(workflow)
    save_image_node = _find_node(workflow, "SaveImage")

    load_image_node["inputs"]["image"] = image_name
    positive_node["inputs"]["text"] = (
        prompt.strip() if prompt and prompt.strip() else _build_toonify_prompt(style)
    )
    save_image_node["inputs"]["filename_prefix"] = f"toonify_lab/{job_id}-{style.value}"


def _queue_prompt(client: httpx.Client, workflow: dict) -> str:
    response = client.post(
        "/prompt",
        json={"prompt": workflow, "client_id": uuid4().hex},
    )
    response.raise_for_status()
    return response.json()["prompt_id"]


def _wait_for_result(
    client: httpx.Client,
    prompt_id: str,
    timeout_seconds: int,
) -> dict[str, str]:
    deadline = time.monotonic() + timeout_seconds

    while time.monotonic() < deadline:
        response = client.get(f"/history/{prompt_id}")
        response.raise_for_status()
        history = response.json().get(prompt_id)

        if history:
            image_info = _extract_output_image(history)
            if image_info is not None:
                return image_info

        time.sleep(1)

    raise TimeoutError(f"ComfyUI job did not finish within {timeout_seconds} seconds.")


def _extract_output_image(history: dict) -> dict[str, str] | None:
    for output in history.get("outputs", {}).values():
        images = output.get("images", [])
        if images:
            return images[0]
    return None


def _download_image(client: httpx.Client, image_info: dict[str, str]) -> bytes:
    response = client.get(
        "/view",
        params={
            "filename": image_info["filename"],
            "subfolder": image_info.get("subfolder", ""),
            "type": image_info.get("type", "output"),
        },
    )
    response.raise_for_status()
    return response.content


def _find_node(workflow: dict, class_type: str) -> dict:
    for node in workflow.values():
        if node.get("class_type") == class_type:
            return node
    raise ValueError(f"Workflow does not include a {class_type} node.")


def _find_positive_prompt_node(workflow: dict) -> dict:
    for node in workflow.values():
        if node.get("class_type") != "CLIPTextEncode":
            continue

        text = node.get("inputs", {}).get("text", "").lower()
        if "watermark" not in text and "low quality" not in text:
            return node

    raise ValueError("Workflow does not include a positive prompt node.")


def _build_toonify_prompt(style: ToonifyStyle) -> str:
    prompts = {
        ToonifyStyle.cartoon: (
            "cartoon portrait, clean line art, smooth shading, expressive face, bright colors, "
            "polished animated character style, preserve the input photo composition and identity"
        ),
        ToonifyStyle.character: (
            "animated character design, clean silhouette, expressive features, polished concept art, "
            "preserve the input photo composition and recognizable details"
        ),
        ToonifyStyle.illustration: (
            "refined fantasy illustration, painterly texture, soft cinematic lighting, elegant "
            "composition, preserve the input photo structure and main subject"
        ),
    }
    return prompts[style]


def _guess_media_type(path: Path) -> str:
    media_types = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
        ".webp": "image/webp",
    }
    return media_types.get(path.suffix.lower(), "application/octet-stream")
