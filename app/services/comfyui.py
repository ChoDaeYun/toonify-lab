import json
import time
from pathlib import Path
from uuid import uuid4

import httpx

from app.schemas.jobs import HandQuality, ToonifyModel, ToonifyStyle


def resolve_workflow_path(base_workflow_path: Path, style: ToonifyStyle) -> Path:
    style_file = base_workflow_path.parent / f"toonify_{style.value}.json"
    if style_file.exists():
        return style_file
    return base_workflow_path


def transform_with_comfyui(
    source_path: Path,
    style: ToonifyStyle,
    model: ToonifyModel,
    prompt: str | None,
    width: int | None,
    height: int | None,
    result_dir: Path,
    job_id: str,
    base_url: str,
    workflow_path: Path,
    timeout_seconds: int,
    hand_quality: HandQuality = HandQuality.normal,
    denoise: float | None = None,
) -> Path:
    workflow = _load_workflow(resolve_workflow_path(workflow_path, style))

    with httpx.Client(base_url=base_url, timeout=30) as client:
        uploaded_name = _upload_image(client, source_path)
        _patch_workflow(workflow, uploaded_name, style, model, prompt, width, height, job_id, hand_quality, denoise)
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


def get_default_workflow_prompt(workflow_path: Path, style: ToonifyStyle | None = None) -> str:
    path = resolve_workflow_path(workflow_path, style) if style else workflow_path
    workflow = _load_workflow(path)
    return _find_positive_prompt_node(workflow)["inputs"]["text"]


def get_default_image_size(workflow_path: Path, style: ToonifyStyle | None = None) -> tuple[int, int]:
    path = resolve_workflow_path(workflow_path, style) if style else workflow_path
    workflow = _load_workflow(path)
    scale_node = _find_optional_node(workflow, "ImageScale")
    if scale_node is None:
        return 512, 768

    inputs = scale_node.get("inputs", {})
    return int(inputs.get("width", 512)), int(inputs.get("height", 768))


def _patch_workflow(
    workflow: dict,
    image_name: str,
    style: ToonifyStyle,
    model: ToonifyModel,
    prompt: str | None,
    width: int | None,
    height: int | None,
    job_id: str,
    hand_quality: HandQuality = HandQuality.normal,
    denoise: float | None = None,
) -> None:
    load_image_node = _find_node(workflow, "LoadImage")
    positive_node = _find_positive_prompt_node(workflow)
    save_image_node = _find_node(workflow, "SaveImage")
    scale_node = _find_optional_node(workflow, "ImageScale")
    checkpoint_node = _find_optional_node(workflow, "CheckpointLoaderSimple")
    ksampler_node = _find_optional_node(workflow, "KSampler")

    load_image_node["inputs"]["image"] = image_name

    base_prompt = prompt.strip() if prompt and prompt.strip() else _build_toonify_prompt(style)
    positive_node["inputs"]["text"] = _apply_hand_quality(base_prompt, hand_quality)

    if checkpoint_node is not None:
        checkpoint_node["inputs"]["ckpt_name"] = model.value
    if scale_node is not None:
        if width is not None:
            scale_node["inputs"]["width"] = width
        if height is not None:
            scale_node["inputs"]["height"] = height
    if ksampler_node is not None and denoise is not None:
        ksampler_node["inputs"]["denoise"] = denoise
    save_image_node["inputs"]["filename_prefix"] = f"toonify_lab/{job_id}-{style.value}"


_HAND_TOKENS_NORMAL = ", (detailed hands:1.3), (correct fingers:1.3), (natural hand pose:1.2), (five fingers:1.2)"
_HAND_TOKENS_STRONG = ", (detailed hands:1.5), (correct fingers:1.5), (natural hand pose:1.4), (five fingers:1.4), (perfect anatomy:1.3)"


def _apply_hand_quality(prompt: str, hand_quality: HandQuality) -> str:
    if hand_quality == HandQuality.off:
        return prompt
    tokens = _HAND_TOKENS_NORMAL if hand_quality == HandQuality.normal else _HAND_TOKENS_STRONG
    # 이미 손 토큰이 포함된 경우(예: 워크플로우 기본 프롬프트) 중복 삽입 방지
    if "detailed hands" in prompt:
        return prompt
    return prompt + tokens


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


def _find_optional_node(workflow: dict, class_type: str) -> dict | None:
    for node in workflow.values():
        if node.get("class_type") == class_type:
            return node
    return None


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
        ToonifyStyle.anime_line: (
            "anime line art, clean black outlines, flat cel shading, vibrant colors, "
            "(anime illustration:1.3), (hand-drawn line art:1.2), smooth color fills, "
            "(detailed face:1.3), (detailed eyes:1.4), (clear nose:1.2), (defined lips:1.2), "
            "(iris detail:1.3), expressive anime face, "
            "(preserve original composition:1.5), (same pose:1.5), (same number of people:1.5), "
            "(same gender:1.5), (same direction:1.4), "
            "same clothing, same arrangement, high quality anime art, masterpiece, best quality"
        ),
        ToonifyStyle.sketch: (
            "pencil sketch, hand-drawn pencil drawing, fine line art, detailed cross-hatching, "
            "graphite shading, (monochrome:1.3), (grayscale:1.3), expressive pencil strokes, "
            "textured paper background, artist sketch style, loose gestural lines, "
            "(preserve original composition:1.4), (same pose:1.3), (same number of people:1.4), "
            "same clothing, same arrangement, high quality sketch, masterpiece"
        ),
        ToonifyStyle.full_anime: (
            "full anime style illustration, anime character design, expressive anime face, "
            "detailed anime eyes, clean cel shading, smooth anime coloring, vivid anime background, "
            "(preserve number of people:1.5), (same composition:1.4), (same pose:1.4), "
            "(same arrangement:1.4), (same walking direction:1.4), same clothing, same body position, "
            "high quality anime art, masterpiece, best quality"
        ),
        ToonifyStyle.background_change: (
            "anime style illustration, vivid detailed background, lush environment, "
            "(new illustrated background:1.4), (replace background only:1.5), "
            "(preserve original composition:1.6), (preserve all figures:1.5), "
            "(preserve original pose:1.5), (preserve body silhouette:1.5), "
            "(same number of people:1.4), (same clothing:1.4), (same walking direction:1.4), "
            "same body position, same framing, same camera angle, "
            "best quality, masterpiece"
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
