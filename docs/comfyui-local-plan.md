# ComfyUI Local Guide

이 문서는 Toonify Lab에서 Mac 로컬 ComfyUI를 변환 엔진으로 사용하는 방법을 정리합니다.

## 현재 구현 상태

ComfyUI provider는 이미 구현되어 있습니다.

```text
이미지 업로드
-> POST /api/jobs
-> workflow JSON 로드
-> ComfyUI에 이미지 업로드
-> /prompt 실행
-> /history polling
-> /view로 결과 다운로드
-> generated/에 저장
```

사용하는 workflow:

```text
workflows/toonify_img2img.json
```

현재 workflow는 img2img 구조입니다.

```text
LoadImage
-> VAEEncode
-> KSampler
-> VAEDecode
-> SaveImage
```

## 실행 전 준비

ComfyUI가 먼저 실행되어 있어야 합니다.

```text
http://127.0.0.1:8188
```

checkpoint 모델은 ComfyUI 설치 폴더의 아래 위치에 있어야 합니다.

```text
ComfyUI/models/checkpoints/
```

모델 설치 참고:

```text
https://comfyui-wiki.com/ko/install/install-models
```

## 환경 설정

로컬 Python 실행 시:

```env
IMAGE_PROVIDER=comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
COMFYUI_WORKFLOW_PATH=workflows/toonify_img2img.json
COMFYUI_TIMEOUT_SECONDS=300
```

Docker 실행 시:

```env
IMAGE_PROVIDER=comfyui
COMFYUI_BASE_URL=http://host.docker.internal:8188
```

## Positive Prompt

Web UI의 프롬프트 입력란은 ComfyUI positive prompt로 전달됩니다.

페이지가 열릴 때 기본값은 workflow JSON의 positive prompt에서 불러옵니다.

관련 API:

```text
GET /api/jobs/prompt-defaults
```

요청별로 직접 입력한 prompt는 `POST /api/jobs`에 포함됩니다.

```json
{
  "image_id": "uploaded_image_id",
  "style": "cartoon",
  "prompt": "preserve the person, keep the same face, clean cartoon style"
}
```

사람을 유지하고 싶을 때 권장 positive prompt:

```text
preserve the person, keep the same human subject, same pose, same face, same body, same clothing, portrait of a person, clean cartoon style, soft shading
```

## Negative Prompt

negative prompt는 현재 UI에서 직접 수정하지 않습니다. workflow JSON의 `CLIPTextEncode` negative 노드 값이 그대로 사용됩니다.

예시:

```text
text, watermark, logo, signature, blurry, low quality, low resolution, distorted, deformed, bad anatomy, extra objects, messy composition, oversaturated, noisy, artifacts, jpeg artifacts, no person, missing person, empty scene, landscape only, object only
```

사람이 사라지는 결과를 줄이려면 negative prompt에 다음 표현을 유지하는 것이 좋습니다.

```text
no person, missing person, empty scene, landscape only, object only
```

## Denoise 튜닝

`workflows/toonify_img2img.json`의 `KSampler` 노드에서 `denoise` 값을 조정할 수 있습니다.

```json
"denoise": 0.4
```

권장 기준:

- `0.30`: 원본 인물/구도 보존 강함
- `0.40`: 보존과 스타일 변환의 균형
- `0.55`: 스타일 강함, 인물이나 구도가 변할 수 있음
- `0.70+`: 원본 훼손 가능성 큼

사람이 사라지거나 배경/물체로 바뀌면 먼저 `0.35 ~ 0.45` 범위로 낮춥니다.

## Steps / CFG

`KSampler` 노드에서 조정합니다.

```json
"steps": 20,
"cfg": 8
```

기준:

- `steps 15~20`: 빠름
- `steps 25~35`: 더 안정적이지만 느림
- `cfg 5~7`: 원본 반영이 부드러움
- `cfg 8~10`: 프롬프트 반영이 강함

## Checkpoint 변경

workflow JSON에서 다음 값을 바꿀 수 있습니다.

```json
"ckpt_name": "novaAnimeXL_ilV190.safetensors"
```

이 값은 `ComfyUI/models/checkpoints/` 안의 실제 파일명과 정확히 같아야 합니다.

## 자주 보는 문제

### 사진이 그대로 나온다

`IMAGE_PROVIDER=mock`이면 변환하지 않고 원본을 복사합니다. ComfyUI를 쓰려면 `IMAGE_PROVIDER=comfyui`로 설정합니다.

### `[Errno 8] nodename nor servname provided, or not known`

ComfyUI 주소가 현재 실행 방식과 맞지 않을 때 발생합니다.

```text
./scripts/dev.sh        -> http://127.0.0.1:8188
./scripts/docker-dev.sh -> http://host.docker.internal:8188
```

### 사람이 사라진다

- positive prompt에 `preserve the person`, `same face`, `same pose`를 넣습니다.
- negative prompt에 `no person`, `missing person`, `empty scene`을 유지합니다.
- `denoise`를 `0.35 ~ 0.45`로 낮춥니다.

### checkpoint 누락

workflow가 참조하는 모델 파일이 ComfyUI에 없습니다.

```text
ComfyUI/models/checkpoints/
```

여기에 `.safetensors` 또는 `.ckpt` 파일을 넣고 ComfyUI에서 refresh 또는 재시작합니다.
