from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import get_settings
from app.routers.images import router as images_router
from app.routers.jobs import router as jobs_router


settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Upload images and prepare toonify transformation jobs.",
)

app.include_router(images_router)
app.include_router(jobs_router)

static_dir = Path(__file__).parent / "static"
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(static_dir / "index.html")


@app.get("/health", tags=["system"])
def health_check() -> dict[str, str]:
    return {"status": "ok", "app": settings.app_name, "environment": settings.app_env}
