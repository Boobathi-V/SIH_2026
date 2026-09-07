/**
 * Centralized API service connecting the React Frontend to the FastAPI DR Model Backend.
 */

export const API_BASE_URL = "http://127.0.0.1:8000";

/**
 * Check whether the AI Model backend service is reachable.
 */
export async function checkBackendHealth() {
  try {
    const response = await fetch(`${API_BASE_URL}/health`, {
      method: "GET",
      signal: AbortSignal.timeout(3000),
    });
    if (!response.ok) return { online: false, error: "Status code error" };
    const data = await response.json();
    return { online: true, data };
  } catch (err) {
    return { online: false, error: err.message };
  }
}

/**
 * Validate retinal image gradeability against the clinical Quality Gate before running full inference.
 * @param {Blob|File} imageFile - The fundus image file.
 * @returns {Promise<Object>} Quality score and gradeability result.
 */
export async function validateImageQuality(imageFile) {
  const formData = new FormData();
  formData.append("file", imageFile, imageFile.name || "retina.png");

  const response = await fetch(`${API_BASE_URL}/validate-quality`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errorDetail = "Quality validation failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.detail || errorDetail;
    } catch {
      // fallback
    }
    throw new Error(errorDetail);
  }

  return await response.json();
}

/**
 * Upload retinal fundus image and receive 5-class DR prediction and Grad-CAM heatmap.
 * @param {Blob|File} imageFile - The fundus image file.
 * @returns {Promise<Object>} The structured clinical prediction JSON.
 */
export async function predictFundusImage(imageFile) {
  const formData = new FormData();
  formData.append("file", imageFile, imageFile.name || "retina.png");
  formData.append("include_base64", "true");

  const response = await fetch(`${API_BASE_URL}/predict`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    let errData = {};
    try {
      errData = await response.json();
    } catch {
      // fallback
    }

    if (response.status === 422 && errData.error === "ImageQualityRejection") {
      const error = new Error(errData.detail || "Image rejected by Retinal Quality Gate.");
      error.isQualityRejection = true;
      error.qualityGate = errData.quality_gate || {};
      error.failureCategory = errData.failure_category || errData.quality_gate?.failure_category;
      error.detailedExplanation = errData.detailed_explanation || errData.quality_gate?.detailed_explanation;
      error.checks = errData.checks || errData.quality_gate?.checks || [];
      error.recaptureGuidance = errData.recapture_guidance || errData.quality_gate?.recapture_guidance;
      throw error;
    }

    const errorDetail = errData.detail || "Inference failed";
    throw new Error(`Model Inference Error (${response.status}): ${errorDetail}`);
  }

  const data = await response.json();
  return data;
}

/**
 * Resolve full URL for Grad-CAM heatmap overlay.
 * @param {string} heatmapUrl - Relative URL from prediction response.
 * @returns {string} Full URL to fetch image.
 */
export function resolveHeatmapUrl(heatmapUrl) {
  if (!heatmapUrl) return "";
  if (heatmapUrl.startsWith("http://") || heatmapUrl.startsWith("https://")) {
    return heatmapUrl;
  }
  return `${API_BASE_URL}${heatmapUrl.startsWith("/") ? "" : "/"}${heatmapUrl}`;
}

/**
 * Resolve full URL for clinical lesion annotated image.
 * @param {string} annotatedUrl - Relative URL from prediction response.
 * @returns {string} Full URL to fetch image.
 */
export function resolveAnnotatedUrl(annotatedUrl) {
  if (!annotatedUrl) return "";
  if (annotatedUrl.startsWith("http://") || annotatedUrl.startsWith("https://")) {
    return annotatedUrl;
  }
  return `${API_BASE_URL}${annotatedUrl.startsWith("/") ? "" : "/"}${annotatedUrl}`;
}

