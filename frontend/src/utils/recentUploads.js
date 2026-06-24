/**
 * localStorage-backed recent-uploads list (max 5 entries).
 *
 * Each entry is a self-contained snapshot of a completed run:
 *   {
 *     jobId, filename, originalLength, coverFilename, uploadedAt, result,
 *   }
 *
 * `result` mirrors the backend response body from /api/status when status is
 * "completed", so the UI can jump straight back into the results screen
 * without re-running the pipeline.
 */

const STORAGE_KEY = "mst.recentUploads.v1";
export const MAX_RECENT = 5;

function safeParse(raw) {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export function loadRecents() {
  if (typeof window === "undefined") return [];
  return safeParse(window.localStorage.getItem(STORAGE_KEY));
}

export function saveRecents(list) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
}

/**
 * Upsert a recent. If `jobId` already exists, replace it (and bump to the top
 * of the list). Otherwise prepend.
 *
 * Returns { recents, evicted } — evicted is the array of entries that fell off
 * the end of the list and now need their backend job folders deleted.
 */
export function upsertRecent(entry) {
  if (!entry || !entry.jobId) {
    return { recents: loadRecents(), evicted: [] };
  }
  const current = loadRecents();
  const without = current.filter((r) => r.jobId !== entry.jobId);
  const next = [entry, ...without];
  const kept = next.slice(0, MAX_RECENT);
  const evicted = next.slice(MAX_RECENT);
  saveRecents(kept);
  return { recents: kept, evicted };
}

/**
 * Remove a single recent by jobId. Returns the new list.
 */
export function removeRecent(jobId) {
  const current = loadRecents();
  const next = current.filter((r) => r.jobId !== jobId);
  saveRecents(next);
  return next;
}
