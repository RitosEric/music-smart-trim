import React, { useState, useCallback } from "react";
import { uploadFile } from "../services/api";
import { formatFileSize } from "../utils/formatters";

function AudioUploader({ onUploadComplete, disabled = false }) {
  const [isDragging, setIsDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);

  const handleUpload = useCallback(
    async (file) => {
      if (!file) return;

      // Validate file type
      const validTypes = [
        "audio/mpeg",
        "audio/wav",
        "audio/flac",
        "audio/x-m4a",
      ];
      if (
        !validTypes.includes(file.type) &&
        !file.name.match(/\.(mp3|wav|flac|m4a)$/i)
      ) {
        setError("Please upload an audio file (MP3, WAV, FLAC, or M4A)");
        return;
      }

      // Validate file size (50MB max)
      const maxSize = 50 * 1024 * 1024;
      if (file.size > maxSize) {
        setError(`File too large. Maximum size: ${formatFileSize(maxSize)}`);
        return;
      }

      setError(null);
      setUploading(true);

      try {
        const result = await uploadFile(file);
        onUploadComplete(result);
      } catch (err) {
        console.error("Upload error:", err);
        setError(
          err.response?.data?.error || "Upload failed. Please try again.",
        );
      } finally {
        setUploading(false);
      }
    },
    [onUploadComplete],
  );

  const handleDragOver = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragging(true);
    },
    [disabled],
  );

  const handleDragLeave = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragging(false);

      if (disabled || uploading) return;

      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleUpload(files[0]);
      }
    },
    [disabled, uploading, handleUpload],
  );

  const handleFileInput = useCallback(
    (e) => {
      const files = e.target.files;
      if (files && files.length > 0) {
        handleUpload(files[0]);
      }
    },
    [handleUpload],
  );

  return (
    <div className="w-full">
      <div
        role="button"
        tabIndex={disabled || uploading ? -1 : 0}
        aria-label="Upload an audio file — click or drag and drop"
        className={`
          group relative overflow-hidden rounded-3xl border-2 border-dashed p-12 text-center
          transition-all duration-200 ease-out
          ${
            isDragging
              ? "scale-[1.01] border-indigo-400 bg-indigo-50/70 dark:border-indigo-400 dark:bg-indigo-500/10"
              : "border-slate-300/80 bg-white/30 dark:border-white/15 dark:bg-white/[0.03]"
          }
          ${
            disabled
              ? "cursor-not-allowed opacity-50"
              : "cursor-pointer hover:border-indigo-400/80 hover:bg-white/50 focus-visible:border-indigo-400 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/60 dark:hover:bg-white/[0.06]"
          }
          ${uploading ? "pointer-events-none" : ""}
        `}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() =>
          !disabled &&
          !uploading &&
          document.getElementById("file-input").click()
        }
        onKeyDown={(e) => {
          if ((e.key === "Enter" || e.key === " ") && !disabled && !uploading) {
            e.preventDefault();
            document.getElementById("file-input").click();
          }
        }}
      >
        <input
          id="file-input"
          type="file"
          accept=".mp3,.wav,.flac,.m4a,audio/*"
          onChange={handleFileInput}
          className="hidden"
          disabled={disabled || uploading}
        />

        {uploading ? (
          <div className="flex flex-col items-center">
            <div className="mb-4 h-12 w-12 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-500 dark:border-white/10 dark:border-t-indigo-400"></div>
            <p className="text-slate-600 dark:text-slate-300">Uploading…</p>
          </div>
        ) : (
          <>
            <span className="mx-auto mb-5 grid h-16 w-16 place-items-center rounded-2xl bg-brand-gradient text-white shadow-lg transition-transform duration-200 group-hover:scale-105">
              <svg
                className="h-8 w-8"
                stroke="currentColor"
                fill="none"
                strokeWidth="2"
                viewBox="0 0 24 24"
                aria-hidden="true"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M12 16V4m0 0L8 8m4-4l4 4M4 16v2a2 2 0 002 2h12a2 2 0 002-2v-2"
                />
              </svg>
            </span>
            <p className="mb-1 text-lg text-slate-700 dark:text-slate-200">
              <span className="font-semibold text-indigo-600 dark:text-indigo-400">
                Click to upload
              </span>{" "}
              or drag and drop
            </p>
            <p className="text-sm text-slate-500 dark:text-slate-400">
              MP3, WAV, FLAC, or M4A · up to 50MB
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-4 rounded-2xl border border-red-300/60 bg-red-50/80 p-3 backdrop-blur-md dark:border-red-500/30 dark:bg-red-950/40">
          <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
        </div>
      )}
    </div>
  );
}

export default AudioUploader;
