import React, { useState } from "react";
import { getDownloadUrl } from "../services/api";
import { formatTime } from "../utils/formatters";
import { MAX_RECENT } from "../utils/recentUploads";

function CoverThumb({ jobId, coverFilename, filename }) {
  const [errored, setErrored] = useState(false);
  if (!coverFilename || errored) {
    return (
      <div className="grid h-16 w-16 shrink-0 place-items-center rounded-xl bg-brand-gradient text-white/90 shadow-sm">
        <svg
          className="h-7 w-7"
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
      className="h-16 w-16 shrink-0 rounded-xl bg-slate-200 object-cover dark:bg-white/10"
    />
  );
}

function RecentList({ recents, onSelect, onRemove }) {
  if (!recents || recents.length === 0) return null;

  return (
    <div className="glass-panel p-6">
      <h2 className="mb-1 font-display text-lg font-semibold text-slate-900 dark:text-white">
        Recent uploads
      </h2>
      <p className="mb-4 text-xs text-slate-400 dark:text-slate-500">
        Only your {MAX_RECENT} most recent uploads are kept — older ones are
        removed automatically to save storage.
      </p>
      <ul className="space-y-2">
        {recents.map((r) => (
          <li
            key={r.jobId}
            className="glass-soft flex items-center gap-4 p-3 transition-all duration-200 hover:border-indigo-400/60 hover:bg-white/70 dark:hover:bg-white/[0.07]"
          >
            <button
              onClick={() => onSelect(r)}
              className="flex flex-1 items-center gap-4 rounded-xl text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/60"
            >
              <CoverThumb
                jobId={r.jobId}
                coverFilename={r.coverFilename}
                filename={r.displayName || r.filename}
              />
              <div className="min-w-0 flex-1">
                <p className="truncate font-medium text-slate-900 dark:text-white">
                  {r.displayName || r.filename || "Untitled"}
                </p>
                <p className="mt-0.5 text-xs text-slate-500 dark:text-slate-400">
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
              aria-label={`Remove ${r.displayName || r.filename || "upload"} from recent`}
              className="rounded-lg p-1.5 text-slate-400 transition-colors hover:bg-red-500/10 hover:text-red-500 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-red-400/50"
            >
              <svg
                className="h-5 w-5"
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
