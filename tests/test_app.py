from pathlib import Path

from fastapi.testclient import TestClient

from app.config import get_settings
from app.main import app
from app.services.jobs import job_store


def test_health_check() -> None:
    client = TestClient(app)

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_page() -> None:
    client = TestClient(app)

    response = client.get("/")

    assert response.status_code == 200
    assert "Toonify Lab" in response.text


def test_prompt_defaults() -> None:
    client = TestClient(app)

    response = client.get("/api/jobs/prompt-defaults")

    assert response.status_code == 200
    assert response.json()["prompt"]


def test_upload_image(tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    settings.upload_dir = tmp_path

    try:
        client = TestClient(app)
        response = client.post(
            "/api/images/upload",
            files={"file": ("sample.png", b"fake image bytes", "image/png")},
        )
    finally:
        settings.upload_dir = original_upload_dir

    body = response.json()

    assert response.status_code == 201
    assert body["content_type"] == "image/png"
    assert body["size_bytes"] == len(b"fake image bytes")
    assert (tmp_path / body["filename"]).exists()


def test_create_and_get_job(tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    original_result_dir = settings.result_dir
    original_image_provider = settings.image_provider
    settings.upload_dir = tmp_path
    settings.result_dir = tmp_path / "generated"
    settings.image_provider = "mock"
    job_store.clear()

    try:
        client = TestClient(app)
        upload_response = client.post(
            "/api/images/upload",
            files={"file": ("sample.png", b"fake image bytes", "image/png")},
        )
        image_id = upload_response.json()["id"]

        create_response = client.post(
            "/api/jobs",
            json={
                "image_id": image_id,
                "style": "cartoon",
                "prompt": "preserve the person, clean cartoon portrait",
            },
        )
        created_job = create_response.json()

        get_response = client.get(f"/api/jobs/{created_job['id']}")
    finally:
        settings.upload_dir = original_upload_dir
        settings.result_dir = original_result_dir
        settings.image_provider = original_image_provider
        job_store.clear()

    assert create_response.status_code == 201
    assert created_job["image_id"] == image_id
    assert created_job["style"] == "cartoon"
    assert created_job["prompt"] == "preserve the person, clean cartoon portrait"
    assert created_job["status"] == "pending"
    assert get_response.status_code == 200
    fetched_job = get_response.json()
    assert fetched_job["id"] == created_job["id"]
    assert fetched_job["status"] == "completed"
    assert fetched_job["result_path"] is not None
    assert Path(fetched_job["result_path"]).exists()


def test_get_job_result(tmp_path: Path) -> None:
    settings = get_settings()
    original_upload_dir = settings.upload_dir
    original_result_dir = settings.result_dir
    original_image_provider = settings.image_provider
    settings.upload_dir = tmp_path
    settings.result_dir = tmp_path / "generated"
    settings.image_provider = "mock"
    job_store.clear()

    try:
        client = TestClient(app)
        upload_response = client.post(
            "/api/images/upload",
            files={"file": ("sample.png", b"fake image bytes", "image/png")},
        )
        image_id = upload_response.json()["id"]
        create_response = client.post(
            "/api/jobs",
            json={"image_id": image_id, "style": "cartoon"},
        )

        result_response = client.get(f"/api/jobs/{create_response.json()['id']}/result")
    finally:
        settings.upload_dir = original_upload_dir
        settings.result_dir = original_result_dir
        settings.image_provider = original_image_provider
        job_store.clear()

    assert result_response.status_code == 200
    assert result_response.headers["content-type"] == "image/png"
    assert result_response.content == b"fake image bytes"


def test_get_job_result_requires_completed_job() -> None:
    job_store.clear()
    job = job_store.create(image_id="image-id", style="cartoon")
    client = TestClient(app)

    try:
        response = client.get(f"/api/jobs/{job.id}/result")
    finally:
        job_store.clear()

    assert response.status_code == 409


def test_create_job_requires_existing_image() -> None:
    job_store.clear()
    client = TestClient(app)

    response = client.post(
        "/api/jobs",
        json={"image_id": "missing-image", "style": "cartoon"},
    )

    assert response.status_code == 404
