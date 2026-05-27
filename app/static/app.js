const form = document.querySelector("#toonify-form");
const fileInput = document.querySelector("#image-input");
const fileName = document.querySelector("#file-name");
const styleSelect = document.querySelector("#style-select");
const promptInput = document.querySelector("#prompt-input");
const resetPromptButton = document.querySelector("#reset-prompt-button");
const submitButton = document.querySelector("#submit-button");
const statusText = document.querySelector("#status-text");
const jobIdText = document.querySelector("#job-id");
const sourcePreview = document.querySelector("#source-preview");
const resultPreview = document.querySelector("#result-preview");
const downloadLink = document.querySelector("#download-link");

let sourcePreviewUrl = null;
let resultPreviewUrl = null;
let defaultPrompt = "";

loadPromptDefaults();

resetPromptButton.addEventListener("click", () => {
  promptInput.value = defaultPrompt;
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
  } else {
    sourcePreview.removeAttribute("src");
  }
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

    const job = await createJob(upload.id, styleSelect.value, promptInput.value);
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

async function createJob(imageId, style, prompt) {
  const response = await fetch("/api/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ image_id: imageId, style, prompt }),
  });

  return parseJsonResponse(response);
}

async function loadPromptDefaults() {
  try {
    const response = await fetch("/api/jobs/prompt-defaults");
    const defaults = await parseJsonResponse(response);
    defaultPrompt = defaults.prompt;
    promptInput.value = defaultPrompt;
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

    await sleep(1500);
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

function sleep(milliseconds) {
  return new Promise((resolve) => {
    window.setTimeout(resolve, milliseconds);
  });
}
