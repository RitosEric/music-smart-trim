/**
 * Format seconds to MM:SS string.
 */
export function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return "0:00";
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${mins}:${secs.toString().padStart(2, "0")}`;
}

/**
 * Format file size to human readable string.
 */
export function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return "0 B";
  const k = 1024;
  const sizes = ["B", "KB", "MB", "GB"];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  return `${(bytes / Math.pow(k, i)).toFixed(2)} ${sizes[i]}`;
}

/**
 * Render star rating as whole-star symbols (rounds to nearest integer).
 * The exact decimal value is shown separately as "X.X / 5.0" by the caller.
 */
export function formatStarRating(rating) {
  const fullStars = Math.max(0, Math.min(5, Math.round(rating || 0)));
  const emptyStars = 5 - fullStars;
  return "★".repeat(fullStars) + "☆".repeat(emptyStars);
}
