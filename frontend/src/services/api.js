import axios from "axios";

const API_BASE_URL =
  process.env.REACT_APP_API_URL || "http://localhost:5002/api";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 300000, // 5 minutes for long processing
  headers: {
    "Content-Type": "application/json",
  },
});

/**
 * Upload audio file.
 */
export async function uploadFile(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await api.post("/upload", formData, {
    headers: {
      "Content-Type": "multipart/form-data",
    },
  });

  return response.data;
}

/**
 * Start audio processing.
 */
export async function processAudio(params) {
  const {
    jobId,
    targetLength,
    protectedRegions = [],
    autoProtect = false,
    regenerateSeed = null,
    strictLength = false,
  } = params;

  const response = await api.post("/process", {
    job_id: jobId,
    target_length: targetLength,
    protected_regions: protectedRegions,
    auto_protect: autoProtect,
    regenerate_seed: regenerateSeed,
    strict_length: strictLength,
  });

  return response.data;
}

/**
 * Get processing status.
 */
export async function getStatus(jobId) {
  const response = await api.get(`/status/${jobId}`);
  return response.data;
}

/**
 * Load the demo sample into a fresh job. Returns the same shape as upload,
 * plus `is_sample` and `suggested_target_length` (a 70% trim).
 */
export async function loadSample() {
  const response = await api.post("/sample");
  return response.data;
}

/**
 * Get download URL for processed file.
 */
export function getDownloadUrl(jobId, filename) {
  // Encode each path segment so output names containing spaces, unicode, or
  // other special characters (e.g. "ヨルシカ - option 1 - 5.0 stars.wav")
  // produce a valid URL. Flask decodes the segment back before lookup.
  return `${API_BASE_URL}/download/${encodeURIComponent(jobId)}/${encodeURIComponent(filename)}`;
}

/**
 * Delete a job and all its files on the backend. Used by the recent-uploads
 * eviction path; the backend treats this as idempotent.
 */
export async function deleteJob(jobId) {
  try {
    await api.delete(`/job/${jobId}`);
    return true;
  } catch (err) {
    console.warn("Failed to delete job", jobId, err);
    return false;
  }
}

/**
 * Download file directly.
 */
export async function downloadFile(jobId, filename) {
  // ?download=1 makes the backend set Content-Disposition: attachment so the
  // browser saves the file instead of opening it inline. The plain
  // getDownloadUrl() is reserved for <audio> playback.
  const url = `${getDownloadUrl(jobId, filename)}?download=1`;
  window.open(url, "_blank");
}

const apiService = {
  uploadFile,
  processAudio,
  getStatus,
  getDownloadUrl,
  downloadFile,
};

export default apiService;
