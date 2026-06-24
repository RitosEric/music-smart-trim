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
        console.log("Upload successful:", result);
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
        className={`
          relative border-2 border-dashed rounded-lg p-12 text-center
          transition-all duration-200 ease-in-out
          ${isDragging ? "border-primary bg-blue-50" : "border-gray-300"}
          ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:border-primary hover:bg-gray-50"}
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
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-primary mb-4"></div>
            <p className="text-gray-600">Uploading...</p>
          </div>
        ) : (
          <>
            <svg
              className="mx-auto h-12 w-12 text-gray-400 mb-4"
              stroke="currentColor"
              fill="none"
              viewBox="0 0 48 48"
              aria-hidden="true"
            >
              <path
                d="M28 8H12a4 4 0 00-4 4v20m32-12v8m0 0v8a4 4 0 01-4 4H12a4 4 0 01-4-4v-4m32-4l-3.172-3.172a4 4 0 00-5.656 0L28 28M8 32l9.172-9.172a4 4 0 015.656 0L28 28m0 0l4 4m4-24h8m-4-4v8m-12 4h.02"
                strokeWidth={2}
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
            <p className="text-lg text-gray-700 mb-2">
              <span className="font-semibold text-primary">
                Click to upload
              </span>{" "}
              or drag and drop
            </p>
            <p className="text-sm text-gray-500">
              MP3, WAV, FLAC, or M4A (max 50MB)
            </p>
          </>
        )}
      </div>

      {error && (
        <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">{error}</p>
        </div>
      )}
    </div>
  );
}

export default AudioUploader;
