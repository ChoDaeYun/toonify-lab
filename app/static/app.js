const form = document.querySelector("#toonify-form");
const fileInput = document.querySelector("#image-input");
const fileName = document.querySelector("#file-name");
const styleSelect = document.querySelector("#style-select");
const modelSelect = document.querySelector("#model-select");
const promptInput = document.querySelector("#prompt-input");
const resetPromptButton = document.querySelector("#reset-prompt-button");
const widthInput = document.querySelector("#width-input");
const heightInput = document.querySelector("#height-input");
const resetSizeButton = document.querySelector("#reset-size-button");
const submitButton = document.querySelector("#submit-button");
const statusText = document.querySelector("#status-text");
const jobIdText = document.querySelector("#job-id");
const sourcePreview = document.querySelector("#source-preview");
const resultPreview = document.querySelector("#result-preview");
const downloadLink = document.querySelector("#download-link");
const cropBox = document.querySelector("#crop-box");
const resetCropButton = document.querySelector("#reset-crop-button");
const cropMeta = document.querySelector("#crop-meta");
const cropWidthInput = document.querySelector("#crop-width-input");
const cropHeightInput = document.querySelector("#crop-height-input");

let sourcePreviewUrl = null;
let resultPreviewUrl = null;
let defaultPrompt = "";
let defaultWidth = 512;
let defaultHeight = 768;
let naturalImageSize = null;
let cropPercent = null;
let cropInteractionMode = null;
let dragStart = null;

loadStyles().then(() => loadPromptDefaults());

resetPromptButton.addEventListener("click", () => {
  promptInput.value = defaultPrompt;
});

styleSelect.addEventListener("change", () => {
  loadPromptDefaults();
});

modelSelect.addEventListener("change", () => {
  loadPromptDefaults();
});

resetSizeButton.addEventListener("click", () => {
  widthInput.value = defaultWidth;
  heightInput.value = defaultHeight;
  syncCropToTargetAspect();
});

resetCropButton.addEventListener("click", () => {
  resetCrop();
});

cropWidthInput.addEventListener("input", () => {
  updateCropSize("width");
});

cropHeightInput.addEventListener("input", () => {
  updateCropSize("height");
});

widthInput.addEventListener("input", () => {
  syncCropToTargetAspect();
});

heightInput.addEventListener("input", () => {
  syncCropToTargetAspect();
});

window.addEventListener("resize", () => {
  renderCrop();
});

fileInput.addEventListener("change", () => {
  const file = fileInput.files[0];
  fileName.textContent = file ? file.name : "JPEG, PNG, WebP";
  clearResult();

  if (sourcePreviewUrl) {
    URL.revokeObjectURL(sourcePreviewUrl);
  }

  if (file) {
    sourcePreviewUrl = URL.createObjectURL(file);
    sourcePreview.src = sourcePreviewUrl;
    naturalImageSize = null;
    cropPercent = null;
    cropBox.hidden = true;
  } else {
    sourcePreview.removeAttribute("src");
    resetCrop();
  }
});

sourcePreview.addEventListener("load", () => {
  naturalImageSize = {
    width: sourcePreview.naturalWidth,
    height: sourcePreview.naturalHeight,
  };
  resetCrop();
});

cropBox.addEventListener("pointerdown", (event) => {
  if (!cropPercent) {
    return;
  }

  cropInteractionMode = event.target.dataset.handle === "resize" ? "resize" : "move";
  cropBox.setPointerCapture(event.pointerId);
  dragStart = {
    pointerX: event.clientX,
    pointerY: event.clientY,
    cropX: cropPercent.x,
    cropY: cropPercent.y,
    cropWidth: cropPercent.width,
    cropHeight: cropPercent.height,
    aspectRatio: cropPercent.width / cropPercent.height,
  };
});

cropBox.addEventListener("pointermove", (event) => {
  if (!cropInteractionMode || !dragStart || !cropPercent) {
    return;
  }

  const imageRect = getDisplayedImageRect();
  if (!imageRect) {
    return;
  }

  const dx = ((event.clientX - dragStart.pointerX) / imageRect.width) * 100;
  const dy = ((event.clientY - dragStart.pointerY) / imageRect.height) * 100;

  if (cropInteractionMode === "resize") {
    resizeCrop(dx, dy);
  } else {
    cropPercent.x = clamp(dragStart.cropX + dx, 0, 100 - cropPercent.width);
    cropPercent.y = clamp(dragStart.cropY + dy, 0, 100 - cropPercent.height);
  }

  renderCrop();
});

cropBox.addEventListener("pointerup", () => {
  cropInteractionMode = null;
  dragStart = null;
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();

  const file = fileInput.files[0];
  if (!file) {
    setStatus("이미지를 먼저 선택해주세요.", "error");
    return;
  }

  try {
    setBusy(true);
    clearResult();
    setStatus("이미지 업로드 중", "processing");

    const upload = await uploadImage(file);
    setStatus("변환 작업 생성 중", "processing");

    const job = await createJob(
      upload.id,
      styleSelect.value,
      modelSelect.value,
      promptInput.value,
      Number(widthInput.value),
      Number(heightInput.value),
      getCropPayload(),
    );
    jobIdText.textContent = `job: ${job.id}`;

    await waitForJob(job.id);
  } catch (error) {
    setStatus(error.message || "처리 중 오류가 발생했습니다.", "error");
  } finally {
    setBusy(false);
  }
});

async function uploadImage(file) {
  const body = new FormData();
  body.append("file", file);

  const response = await fetch("/api/images/upload", {
    method: "POST",
    body,
  });

  return parseJsonResponse(response);
}

async function createJob(imageId, style, model, prompt, width, height, crop) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId, style, model, prompt, width, height, ...crop }),
  });

  return parseJsonResponse(response);
}

async function loadStyles() {
  const response = await fetch("/api/jobs/styles");
  if (!response.ok) return;
  const styles = await response.json();
  styleSelect.innerHTML = styles
    .map((s) => `<option value="${s.value}">${s.label}</option>`)
    .join("");
}

async function loadPromptDefaults() {
  try {
    const style = styleSelect.value;
    const model = modelSelect.value;
    const response = await fetch(`/api/jobs/prompt-defaults?style=${style}&model=${encodeURIComponent(model)}`);
    const defaults = await parseJsonResponse(response);
    defaultPrompt = defaults.prompt;
    defaultWidth = defaults.width;
    defaultHeight = defaults.height;
    promptInput.value = defaultPrompt;
    widthInput.value = defaultWidth;
    heightInput.value = defaultHeight;
  } catch {
    defaultPrompt = "";
    promptInput.placeholder = "기본 프롬프트를 불러오지 못했습니다. 직접 입력할 수 있습니다.";
  }
}

async function waitForJob(jobId) {
  for (;;) {
    const response = await fetch(`/api/jobs/${jobId}`);
    const job = await parseJsonResponse(response);

    setStatus(`작업 상태: ${job.status}`, job.status);

    if (job.status === "completed") {
      await showResult(jobId);
      return;
    }

    if (job.status === "failed") {
      throw new Error(job.error_message || "변환 작업이 실패했습니다.");
    }

    await sleep(5000);
  }
}

async function showResult(jobId) {
  const response = await fetch(`/api/jobs/${jobId}/result`);
  if (!response.ok) {
    throw new Error("결과 이미지를 불러오지 못했습니다.");
  }

  const blob = await response.blob();
  if (resultPreviewUrl) {
    URL.revokeObjectURL(resultPreviewUrl);
  }

  resultPreviewUrl = URL.createObjectURL(blob);
  resultPreview.src = resultPreviewUrl;
  downloadLink.href = resultPreviewUrl;
  downloadLink.hidden = false;
  setStatus("변환 완료", "completed");
}

async function parseJsonResponse(response) {
  const body = await response.json().catch(() => ({}));

  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "요청이 실패했습니다.";
    throw new Error(detail);
  }

  return body;
}

function setStatus(message, state) {
  statusText.textContent = message;
  statusText.dataset.state = state;
}

function setBusy(isBusy) {
  submitButton.disabled = isBusy;
  submitButton.textContent = isBusy ? "처리 중" : "변환 시작";
}

function clearResult() {
  if (resultPreviewUrl) {
    URL.revokeObjectURL(resultPreviewUrl);
    resultPreviewUrl = null;
  }

  resultPreview.removeAttribute("src");
  downloadLink.hidden = true;
  downloadLink.removeAttribute("href");
  jobIdText.textContent = "";
}

function resetCrop() {
  if (!naturalImageSize) {
    cropPercent = null;
    cropBox.hidden = true;
    cropMeta.textContent = "전체 이미지 사용";
    return;
  }

  cropPercent = {
    x: 0,
    y: 0,
    ...getInitialCropSize(),
  };
  cropPercent.x = (100 - cropPercent.width) / 2;
  cropPercent.y = (100 - cropPercent.height) / 2;
  cropWidthInput.value = cropPercent.width;
  cropHeightInput.value = cropPercent.height;
  cropBox.hidden = false;
  renderCrop();
}

function updateCropSize(changedAxis) {
  if (!cropPercent) {
    return;
  }

  const aspectRatio = getTargetCropPercentAspectRatio();

  if (changedAxis === "height") {
    cropPercent.height = Number(cropHeightInput.value);
    cropPercent.width = cropPercent.height * aspectRatio;
  } else {
    cropPercent.width = Number(cropWidthInput.value);
    cropPercent.height = cropPercent.width / aspectRatio;
  }

  fitCropSize();
  cropPercent.x = clamp(cropPercent.x, 0, 100 - cropPercent.width);
  cropPercent.y = clamp(cropPercent.y, 0, 100 - cropPercent.height);
  cropWidthInput.value = Math.round(cropPercent.width);
  cropHeightInput.value = Math.round(cropPercent.height);
  renderCrop();
}

function resizeCrop(dx, dy) {
  const widthFromPointer = dragStart.cropWidth + dx;
  const heightFromPointer = dragStart.cropHeight + dy;
  const widthFromHeight = heightFromPointer * dragStart.aspectRatio;

  let nextWidth =
    Math.abs(dx) >= Math.abs(dy) ? widthFromPointer : Math.max(widthFromPointer, widthFromHeight);
  let nextHeight = nextWidth / dragStart.aspectRatio;
  const maxWidth = 100 - dragStart.cropX;
  const maxHeight = 100 - dragStart.cropY;

  if (nextWidth > maxWidth) {
    nextWidth = maxWidth;
    nextHeight = nextWidth / dragStart.aspectRatio;
  }

  if (nextHeight > maxHeight) {
    nextHeight = maxHeight;
    nextWidth = nextHeight * dragStart.aspectRatio;
  }

  cropPercent.width = clamp(nextWidth, 20, maxWidth);
  cropPercent.height = clamp(nextHeight, 20, maxHeight);
  cropWidthInput.value = Math.round(cropPercent.width);
  cropHeightInput.value = Math.round(cropPercent.height);
}

function syncCropToTargetAspect() {
  if (!cropPercent || !naturalImageSize) {
    return;
  }

  const centerX = cropPercent.x + cropPercent.width / 2;
  const centerY = cropPercent.y + cropPercent.height / 2;
  const areaScale = Math.max(cropPercent.width, cropPercent.height);
  const nextSize = getInitialCropSize(areaScale);

  cropPercent.width = nextSize.width;
  cropPercent.height = nextSize.height;
  cropPercent.x = clamp(centerX - cropPercent.width / 2, 0, 100 - cropPercent.width);
  cropPercent.y = clamp(centerY - cropPercent.height / 2, 0, 100 - cropPercent.height);
  cropWidthInput.value = Math.round(cropPercent.width);
  cropHeightInput.value = Math.round(cropPercent.height);
  renderCrop();
}

function fitCropSize() {
  const aspectRatio = getTargetCropPercentAspectRatio();

  if (cropPercent.width > 100) {
    cropPercent.width = 100;
    cropPercent.height = cropPercent.width / aspectRatio;
  }

  if (cropPercent.height > 100) {
    cropPercent.height = 100;
    cropPercent.width = cropPercent.height * aspectRatio;
  }

  cropPercent.width = clamp(cropPercent.width, 20, 100);
  cropPercent.height = clamp(cropPercent.height, 20, 100);
}

function getInitialCropSize(scale = 80) {
  const aspectRatio = getTargetCropPercentAspectRatio();

  if (aspectRatio >= 1) {
    return {
      width: scale,
      height: scale / aspectRatio,
    };
  }

  return {
    width: scale * aspectRatio,
    height: scale,
  };
}

function getTargetCropPercentAspectRatio() {
  if (!naturalImageSize) {
    return 1;
  }

  const targetWidth = Number(widthInput.value) || defaultWidth;
  const targetHeight = Number(heightInput.value) || defaultHeight;
  const targetRatio = targetWidth / targetHeight;
  const imageRatio = naturalImageSize.width / naturalImageSize.height;

  return targetRatio / imageRatio;
}

function renderCrop() {
  const imageRect = getDisplayedImageRect();
  if (!cropPercent || !imageRect) {
    return;
  }

  cropBox.style.left = `${imageRect.left + (imageRect.width * cropPercent.x) / 100}px`;
  cropBox.style.top = `${imageRect.top + (imageRect.height * cropPercent.y) / 100}px`;
  cropBox.style.width = `${(imageRect.width * cropPercent.width) / 100}px`;
  cropBox.style.height = `${(imageRect.height * cropPercent.height) / 100}px`;

  const crop = getCropPayload();
  cropMeta.textContent = `${crop.crop_width} x ${crop.crop_height} @ ${crop.crop_x}, ${crop.crop_y}`;
}

function getCropPayload() {
  if (!cropPercent || !naturalImageSize) {
    return {};
  }

  return {
    crop_x: Math.round((naturalImageSize.width * cropPercent.x) / 100),
    crop_y: Math.round((naturalImageSize.height * cropPercent.y) / 100),
    crop_width: Math.round((naturalImageSize.width * cropPercent.width) / 100),
    crop_height: Math.round((naturalImageSize.height * cropPercent.height) / 100),
  };
}

function getDisplayedImageRect() {
  if (!sourcePreview.src || !naturalImageSize) {
    return null;
  }

  const frameRect = sourcePreview.parentElement.getBoundingClientRect();
  const imageElementRect = sourcePreview.getBoundingClientRect();
  const imageRatio = naturalImageSize.width / naturalImageSize.height;
  const frameRatio = frameRect.width / frameRect.height;

  if (imageRatio > frameRatio) {
    const width = imageElementRect.width;
    const height = width / imageRatio;
    return {
      left: imageElementRect.left - frameRect.left,
      top: imageElementRect.top - frameRect.top + (imageElementRect.height - height) / 2,
      width,
      height,
    };
  }

  const height = imageElementRect.height;
  const width = height * imageRatio;
  return {
    left: imageElementRect.left - frameRect.left + (imageElementRect.width - width) / 2,
    top: imageElementRect.top - frameRect.top,
    width,
    height,
  };
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function sleep(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}
