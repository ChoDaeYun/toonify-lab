# Toonify Lab

Toonify Lab은 사용자가 업로드한 이미지를 로컬 ComfyUI, OpenAI Image API, 또는 mock provider로 변환해보는 FastAPI 기반 이미지 변환 실험 프로젝트입니다.

현재는 이미지 업로드, 변환 작업 생성, 상태 조회, 결과 이미지 조회, 간단한 Web UI까지 포함합니다.

## 주요 기능

- 이미지 업로드: JPEG, PNG, WebP
- 변환 작업 생성 및 상태 관리
- 변환 결과 이미지 조회/다운로드
- Web UI에서 업로드, 프롬프트 입력, 스타일 선택, 결과 미리보기
- provider 선택
  - `mock`: 개발용 원본 복사
  - `comfyui`: Mac 로컬 ComfyUI 서버 연동
  - `openai`: OpenAI Image API 연동

## 실행

로컬 Python 실행:

```bash
./scripts/dev.sh
```

Docker 실행:

```bash
./scripts/docker-dev.sh
```

테스트와 린트:

```bash
./scripts/test.sh
```

서버 실행 후 접속:

- Web UI: `http://127.0.0.1:8000`
- Swagger UI: `http://127.0.0.1:8000/docs`
- Health check: `http://127.0.0.1:8000/health`

## 환경 설정

기본 설정 파일은 `.env.example`을 참고합니다. 실제 로컬 실행에는 `.env`를 사용합니다.

로컬 ComfyUI를 사용할 때:

```env
IMAGE_PROVIDER=comfyui
COMFYUI_BASE_URL=http://127.0.0.1:8188
COMFYUI_WORKFLOW_PATH=workflows/toonify_img2img.json
COMFYUI_TIMEOUT_SECONDS=300
```

Docker 컨테이너에서 Mac의 ComfyUI를 호출할 때:

```env
IMAGE_PROVIDER=comfyui
COMFYUI_BASE_URL=http://host.docker.internal:8188
```

OpenAI Image API를 사용할 때:

```env
IMAGE_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_IMAGE_MODEL=gpt-image-1.5
OPENAI_IMAGE_SIZE=1024x1024
```

로컬 흐름만 확인할 때:

```env
IMAGE_PROVIDER=mock
```

## API

```text
GET  /health
GET  /api/jobs/prompt-defaults
POST /api/images/upload
POST /api/jobs
GET  /api/jobs/{job_id}
GET  /api/jobs/{job_id}/result
```

`POST /api/jobs` 요청 예시:

```json
{
  "image_id": "uploaded_image_id",
  "style": "cartoon",
  "prompt": "preserve the person, clean cartoon portrait, soft shading"
}
```

지원 스타일:

- `cartoon`
- `character`
- `illustration`

## 디렉터리

```text
app/                         FastAPI 애플리케이션
app/static/                  Web UI
docs/                        프로젝트 문서
scripts/                     실행/테스트 스크립트
tests/                       테스트
workflows/toonify_img2img.json ComfyUI API workflow
uploads/                     업로드 이미지, Git 제외
generated/                   변환 결과, Git 제외
```

## ComfyUI 문서

ComfyUI 설치, workflow, prompt/negative prompt, denoise 튜닝은 [docs/comfyui-local-plan.md](docs/comfyui-local-plan.md)를 확인합니다.
