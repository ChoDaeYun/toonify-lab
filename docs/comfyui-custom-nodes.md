# ComfyUI 커스텀 노드 및 모델 설치 기록

Toonify Lab에서 사용하는 커스텀 노드와 추가 모델 설치 내용을 기록합니다.

## 설치 위치

ComfyUI 데이터 디렉토리:

```text
/Users/Documents/ComfyUI/
```

ComfyUI 실행 파일:

```text
/Applications/ComfyUI.app
```

ComfyUI venv:

```text
/Users/Documents/ComfyUI/.venv/  (Python 3.12)
```

---

## 커스텀 노드

### comfyui_segment_anything

인물 자동 마스킹에 사용합니다. `background_change` 스타일의 inpainting 워크플로우에서 필요합니다.

```text
/Users/Documents/ComfyUI/custom_nodes/comfyui_segment_anything/
```

설치 명령:

```bash
cd /Users/Documents/ComfyUI/custom_nodes
git clone https://github.com/storyicon/comfyui_segment_anything.git
/Users/Documents/ComfyUI/.venv/bin/pip3 install segment_anything timm addict yapf
```

제공 노드:

- `SAMModelLoader (segment anything)` — SAM 모델 로드
- `GroundingDinoModelLoader (segment anything)` — GroundingDINO 모델 로드
- `GroundingDinoSAMSegment (segment anything)` — 텍스트 프롬프트로 인물 마스크 자동 생성

#### transformers 버전 호환성 패치

이 노드는 `transformers 5.x`와 호환되지 않습니다. 설치 시 4.x로 다운그레이드가 필요합니다.

```bash
/Users/Documents/ComfyUI/.venv/bin/pip3 install "transformers==4.49.0"
```

추가로 `local_groundingdino`의 `BertModelWarper`가 `transformers 4.49`에서 제거된 메서드를 직접 참조하는 문제가 있어 아래 파일을 직접 패치했습니다.

패치 파일:

```text
custom_nodes/comfyui_segment_anything/local_groundingdino/models/GroundingDINO/bertwarper.py
```

패치 내용:

- `get_head_mask`: transformers에서 제거됨 → `BertModelWarper`에 직접 구현
- `get_extended_attention_mask`: bool 텐서 처리 문제 → `BertModelWarper`에 직접 구현 (float32 변환 후 마스킹)

---

### ComfyUI_IPAdapter_plus

원본 이미지의 색감/분위기를 참조해 배경 생성에 반영합니다. `background_change`, `full_anime` 스타일에서 사용합니다.

```text
/Users/Documents/ComfyUI/custom_nodes/ComfyUI_IPAdapter_plus/
```

설치 명령:

```bash
cd /Users/Documents/ComfyUI/custom_nodes
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
```

별도 pip 패키지 설치 불필요합니다.

제공 노드:

- `IPAdapterModelLoader` — IP-Adapter 모델 로드
- `IPAdapterAdvanced` — 이미지를 레퍼런스로 모델에 주입

---

## 추가 모델

### SAM (Segment Anything Model)

인물 마스크 생성에 사용합니다.

```text
/Users/Documents/ComfyUI/models/sams/sam_vit_h_4b8939.pth
```

크기: 338MB

워크플로우에서 참조하는 이름:

```text
sam_vit_h (2.56GB)
```

다운로드:

```bash
curl -L -o /Users/Documents/ComfyUI/models/sams/sam_vit_h_4b8939.pth \
  "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth"
```

---

### GroundingDINO

텍스트로 인물 영역을 탐지합니다. SAM과 함께 사용합니다.

```text
/Users/Documents/ComfyUI/models/grounding-dino/groundingdino_swint_ogc.pth
```

크기: 60MB

워크플로우에서 참조하는 이름:

```text
GroundingDINO_SwinT_OGC (694MB)
```

다운로드:

```bash
curl -L -o /Users/Documents/ComfyUI/models/grounding-dino/groundingdino_swint_ogc.pth \
  "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth"
```

---

### IP-Adapter SDXL (ViT-H)

원본 이미지의 색감과 분위기를 배경 생성에 반영하는 데 사용합니다.

```text
/Users/Documents/ComfyUI/models/ipadapter/ip-adapter_sdxl_vit-h.safetensors
```

크기: 437MB

다운로드:

```bash
curl -L -o /Users/Documents/ComfyUI/models/ipadapter/ip-adapter_sdxl_vit-h.safetensors \
  "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl_vit-h.safetensors"
```

---

### CLIP ViT-H Vision Encoder

IP-Adapter가 이미지를 인코딩하는 데 필요한 vision encoder입니다.

```text
/Users/Documents/ComfyUI/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors
```

크기: 134MB

다운로드:

```bash
curl -L -o /Users/Documents/ComfyUI/models/clip_vision/CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors \
  "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors"
```

---

## 새 환경 세팅 순서 (Mac)

ComfyUI를 새로 설치하거나 환경을 다시 구성할 때 순서입니다.

```text
1. ComfyUI 앱 설치 및 실행 (포트 8188 확인)
2. custom_nodes/comfyui_segment_anything 클론
3. transformers==4.49.0 으로 다운그레이드
4. bertwarper.py 패치 적용 (위 패치 내용 참고)
5. custom_nodes/ComfyUI_IPAdapter_plus 클론
6. models/sams/ — sam_vit_h_4b8939.pth 다운로드
7. models/grounding-dino/ — groundingdino_swint_ogc.pth 다운로드
8. models/ipadapter/ — ip-adapter_sdxl_vit-h.safetensors 다운로드
9. models/clip_vision/ — CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors 다운로드
10. ComfyUI 재시작
```

---

## Windows 세팅

### 사전 준비

- **GPU**: NVIDIA GPU 권장 (CUDA 지원). AMD GPU는 ComfyUI에서 제한적으로 지원
- **필수 소프트웨어**: Git, Docker Desktop, Python (ComfyUI 설치 시 포함됨)

### ComfyUI 설치

아래 링크에서 윈도우용 설치 파일 다운로드:

```text
https://github.com/comfyanonymous/ComfyUI/releases
```

`ComfyUI_windows_portable` 압축 파일을 받아서 원하는 위치에 압축 해제합니다. 이후 문서에서는 아래 경로를 기준으로 설명합니다.

```text
C:\ComfyUI\
```

실제 설치 위치에 맞게 경로를 바꿔서 적용합니다.

### 디렉토리 구조

```text
C:\ComfyUI\
├── custom_nodes\
├── models\
│   ├── checkpoints\
│   ├── clip_vision\
│   ├── grounding-dino\
│   ├── ipadapter\
│   └── sams\
├── python_embeded\       ← ComfyUI 내장 Python
└── ComfyUI\
    └── custom_nodes\     ← 여기에 커스텀 노드 설치
```

### 커스텀 노드 설치

PowerShell 또는 명령 프롬프트에서 실행합니다.

```powershell
cd C:\ComfyUI\ComfyUI\custom_nodes

git clone https://github.com/storyicon/comfyui_segment_anything.git
git clone https://github.com/cubiq/ComfyUI_IPAdapter_plus.git
```

### Python 패키지 설치

ComfyUI 내장 Python을 사용합니다.

```powershell
C:\ComfyUI\python_embeded\python.exe -m pip install segment_anything timm addict yapf
C:\ComfyUI\python_embeded\python.exe -m pip install "transformers==4.49.0"
```

### bertwarper.py 패치

Mac과 동일하게 패치합니다. 파일 위치만 다릅니다.

```text
C:\ComfyUI\ComfyUI\custom_nodes\comfyui_segment_anything\local_groundingdino\models\GroundingDINO\bertwarper.py
```

패치 내용은 Mac과 동일합니다 (위 패치 내용 참고).

### 모델 다운로드

PowerShell에서 실행합니다. `curl` 대신 `Invoke-WebRequest`를 사용합니다.

```powershell
# SAM
Invoke-WebRequest -Uri "https://dl.fbaipublicfiles.com/segment_anything/sam_vit_h_4b8939.pth" `
  -OutFile "C:\ComfyUI\models\sams\sam_vit_h_4b8939.pth"

# GroundingDINO
Invoke-WebRequest -Uri "https://github.com/IDEA-Research/GroundingDINO/releases/download/v0.1.0-alpha/groundingdino_swint_ogc.pth" `
  -OutFile "C:\ComfyUI\models\grounding-dino\groundingdino_swint_ogc.pth"

# IP-Adapter SDXL
Invoke-WebRequest -Uri "https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter_sdxl_vit-h.safetensors" `
  -OutFile "C:\ComfyUI\models\ipadapter\ip-adapter_sdxl_vit-h.safetensors"

# CLIP ViT-H
Invoke-WebRequest -Uri "https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors" `
  -OutFile "C:\ComfyUI\models\clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors"
```

파일이 크므로 브라우저로 직접 다운로드해서 해당 폴더에 넣어도 됩니다.

### Toonify Lab API 서버 실행

`.env` 설정은 Mac과 동일합니다. Docker Desktop이 실행 중인 상태에서:

```powershell
docker compose up
```

ComfyUI URL은 Docker 내부에서 호스트를 가리켜야 하므로 아래로 설정합니다.

```env
IMAGE_PROVIDER=comfyui
COMFYUI_BASE_URL=http://host.docker.internal:8188
```

### 노드 로드 확인

ComfyUI 실행 후 브라우저에서 확인하거나 PowerShell에서 실행합니다.

```powershell
curl http://localhost:8188/object_info | python -c "
import sys, json
nodes = json.load(sys.stdin)
for name in ['IPAdapterAdvanced', 'IPAdapterModelLoader', 'SAMModelLoader (segment anything)', 'GroundingDinoSAMSegment (segment anything)']:
    print('OK' if name in nodes else 'MISSING', name)
"
```

### Windows 전용 주의사항

**경로 구분자**: 워크플로우 JSON이나 설정 파일에 경로를 직접 쓸 일은 없으므로 별도 처리 불필요합니다.

**CUDA 버전**: ComfyUI 설치 파일에 CUDA 버전이 포함되어 있습니다. GPU 드라이버가 최신인지 확인합니다.

**AMD GPU**: ROCm 기반으로 동작할 수 있지만 segment anything, IP-Adapter 호환성이 불안정할 수 있습니다. NVIDIA GPU 사용을 권장합니다.

**CPU 전용**: GPU가 없으면 ComfyUI가 CPU로 동작하지만 처리 시간이 수십 배 느립니다.

---

## 자주 보는 문제

### `BertModel object has no attribute get_head_mask`

transformers 버전이 5.x입니다. 4.49로 다운그레이드하고 bertwarper.py 패치를 확인합니다.

### `to() received an invalid combination of arguments - got (dtype=torch.device)`

bertwarper.py의 `get_extended_attention_mask`가 패치되지 않은 상태입니다. 위 패치 내용을 적용합니다.

### `Subtraction with a bool tensor is not supported`

`get_extended_attention_mask` 패치에서 `float32` 변환 누락입니다. 패치 코드에 `extended_attention_mask.to(dtype=torch.float32)` 변환이 있는지 확인합니다.

### IP-Adapter 노드가 없다고 나올 때

ComfyUI를 재시작하지 않았거나 `ComfyUI_IPAdapter_plus` 클론이 안 된 상태입니다. 재시작 후 `/object_info` API로 노드 로드 여부를 확인합니다.

```bash
curl -s http://localhost:8188/object_info | python3 -c "
import sys, json
nodes = json.load(sys.stdin)
for name in ['IPAdapterAdvanced', 'IPAdapterModelLoader', 'SAMModelLoader (segment anything)', 'GroundingDinoSAMSegment (segment anything)']:
    print('OK' if name in nodes else 'MISSING', name)
"
```
