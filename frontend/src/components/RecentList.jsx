import React, { useState } from "react";
import { getDownloadUrl } from "../services/api";
import { formatTime } from "../utils/formatters";
import { MAX_RECENT } from "../utils/recentUploads";

function CoverThumb({ jobId, coverFilename, filename }) {
  const [errored, setErrored] = useState(false);
  if (!coverFilename || errored) {
    return (
      <div className="w-16 h-16 rounded bg-gray-200 flex items-center justify-center text-gray-400 shrink-0">
        <svg
          className="w-7 h-7"
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth={1.6}
            d="M9 19V6l12-3v13M9 19a3 3 0 11-6 0 3 3 0 016 0zm12-3a3 3 0 11-6 0 3 3 0 016 0z"
          />
        </svg>
      </div>
    );
  }
  return (
    <img
      src={getDownloadUrl(jobId, coverFilename)}
      alt={`Cover for ${filename}`}
      onError={() => setErrored(true)}
      className="w-16 h-16 rounded object-cover shrink-0 bg-gray-200"
    />
  );
}

function RecentList({ recents, onSelect, onRemove }) {
  if (!recents || recents.length === 0) return null;

  return (
    <div className="bg-white rounded-lg shadow-md p-6 mt-6">
      <h2 className="text-lg font-semibold mb-1 text-gray-800">
        Recent uploads
      </h2>
      <p className="text-xs text-gray-400 mb-4">
        Only your {MAX_RECENT} most recent uploads are kept — older ones are
        removed automatically to save storage.
      </p>
      <ul className="space-y-2">
        {recents.map((r) => (
          <li
            key={r.jobId}
            className="flex items-center gap-4 p-3 rounded-lg border border-gray-200 hover:border-primary hover:bg-blue-50 transition-colors"
          >
            <button
              onClick={() => onSelect(r)}
              className="flex items-center gap-4 flex-1 text-left"
            >
              <CoverThumb
                jobId={r.jobId}
                coverFilename={r.coverFilename}
                filename={r.displayName || r.filename}
              />
              <div className="flex-1 min-w-0">
                <p className="font-medium text-gray-900 truncate">
                  {r.displayName || r.filename || "Untitled"}
                </p>
                <p className="text-xs text-gray-500 mt-0.5">
                  Original {formatTime(r.originalLength)}
                  {r.result?.target_length ? (
                    <>
                      {" "}
                      &middot; trimmed to {formatTime(r.result.target_length)}
                    </>
                  ) : null}
                </p>
              </div>
            </button>
            <button
              onClick={() => onRemove(r.jobId)}
              title="Remove from Recent"
              className="text-gray-400 hover:text-red-500 p-1 transition-colors"
            >
              <svg
                className="w-5 h-5"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M6 18L18 6M6 6l12 12"
                />
              </svg>
            </button>
          </li>
        ))}
      </ul>
    </div>
  );
}

export default RecentList;
