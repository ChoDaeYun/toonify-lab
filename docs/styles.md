# 스타일 가이드

현재 지원하는 스타일 목록과 각 스타일의 동작 방식을 정리합니다.

## 스타일 목록

| 값 | 표시명 | 워크플로우 | 방식 |
|---|---|---|---|
| `cartoon` | Cartoon | `toonify_cartoon.json` | img2img |
| `character` | Character | `toonify_character.json` | img2img |
| `illustration` | Illustration | `toonify_illustration.json` | img2img |
| `background_change` | Background Change | `toonify_background_change.json` | Inpainting + IP-Adapter |
| `full_anime` | Full Anime | `toonify_full_anime.json` | img2img + IP-Adapter |
| `sketch` | Sketch | `toonify_sketch.json` | img2img |

스타일 목록은 `GET /api/jobs/styles` API로 동적으로 제공됩니다. 프론트엔드 셀렉트박스는 이 API를 사용하므로 코드 추가만 하면 자동으로 반영됩니다.

---

## 스타일별 상세

### sketch

연필 스케치 스타일입니다. 사진을 손으로 그린 연필화처럼 변환합니다.

- `denoise`: 0.35 — 구도/인물 유지하면서 스타일만 변환
- 흑백(grayscale) 강제, 크로스해칭/연필 질감 프롬프트 적용
- 사람 수, 포즈, 배치 보존 가중치 포함

### cartoon / character / illustration

기본 img2img 방식입니다. 원본 이미지를 그대로 스타일만 바꿉니다.

- `denoise`: 0.28 — 원본 구도/인물을 최대한 유지
- 인물 얼굴 보존 가중치 적용

### background_change

인물은 원본 픽셀 그대로 유지하고 배경만 애니 스타일로 재생성합니다.

처리 흐름:

```text
LoadImage → ImageScale
    ↓
GroundingDINO + SAM → 인물 마스크 자동 생성
    ↓
GrowMask (8px 확장) → InvertMask (배경 영역 선택)
    ↓
IP-Adapter (원본 이미지 분위기 참조, weight=0.4)
    ↓
VAEEncodeForInpaint → KSampler denoise=1.0 (배경 완전 재생성)
    ↓
VAEDecode → ImageCompositeMasked (원본 인물 합성)
    ↓
SaveImage
```

인물 마스킹 프롬프트:

```text
person . people . human . figure  (threshold: 0.35)
```

인물이 감지되지 않으면 배경 전체가 재생성됩니다.

IP-Adapter 설정:

```json
"weight": 0.4,
"start_at": 0.0,
"end_at": 0.6,
"weight_type": "style transfer"
```

### full_anime

인물과 배경 모두 애니 스타일로 변환합니다.

처리 흐름:

```text
LoadImage → ImageScale
    ↓
IP-Adapter (원본 이미지 분위기 참조, weight=0.4)
    ↓
VAEEncode → KSampler denoise=0.65
    ↓
VAEDecode → SaveImage
```

`denoise=0.65`로 원본 구도를 유지하면서 인물과 배경을 함께 변환합니다.

IP-Adapter 설정은 `background_change`와 동일합니다.

---

## 스타일 추가 방법

스타일을 새로 추가할 때 수정할 파일 목록입니다.

**1. `app/schemas/jobs.py`**

`ToonifyStyle` enum에 값 추가:

```python
new_style = "new_style"
```

`STYLE_LABELS`에 표시명 추가:

```python
ToonifyStyle.new_style: "New Style",
```

**2. `app/services/comfyui.py`**

`_build_toonify_prompt()`에 ComfyUI용 기본 프롬프트 추가:

```python
ToonifyStyle.new_style: "...",
```

**3. `app/services/processor.py`**

`_build_toonify_prompt()`에 OpenAI용 기본 프롬프트 추가:

```python
ToonifyStyle.new_style: "...",
```

**4. `workflows/toonify_new_style.json`**

스타일 전용 워크플로우 파일 추가. 파일이 없으면 `toonify_img2img.json`을 fallback으로 사용합니다.

`index.html`은 수정하지 않아도 됩니다. `/api/jobs/styles`에서 자동으로 반영됩니다.

---

## EXIF 회전 보정

업로드 시 JPEG EXIF orientation을 자동으로 보정합니다. 스마트폰으로 촬영한 세로 사진이 가로로 나오는 문제를 방지합니다.

처리 위치: `app/services/image_editing.py` — `fix_orientation()`

보정 대상 orientation 값:

| EXIF 값 | 회전 |
|---|---|
| 3 | 180도 |
| 6 | 270도 (시계 반대방향 90도) |
| 8 | 90도 (시계 방향) |
