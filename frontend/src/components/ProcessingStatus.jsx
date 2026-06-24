import React from "react";

function ProcessingStatus({
  progress = 0,
  message = "Processing...",
  visible = true,
}) {
  if (!visible) return null;

  const pct = Math.min(100, Math.max(0, progress));

  return (
    <div className="glass-panel p-6">
      <div className="flex items-center gap-4">
        <div className="relative h-11 w-11 flex-shrink-0">
          <div className="absolute inset-0 animate-spin rounded-full border-2 border-indigo-200/60 border-t-indigo-500 dark:border-white/10 dark:border-t-indigo-400"></div>
          <div className="absolute inset-2 rounded-full bg-brand-gradient opacity-80 blur-[2px]"></div>
        </div>

        <div className="flex-1">
          <p className="mb-2 font-display text-lg font-semibold text-slate-900 dark:text-white">
            {message}
          </p>

          <div className="relative h-3 w-full overflow-hidden rounded-full bg-slate-200/70 dark:bg-white/10">
            <div
              className="h-3 rounded-full bg-brand-gradient transition-all duration-500 ease-out"
              style={{ width: `${pct}%` }}
            >
              {/* moving sheen */}
              <div className="h-full w-full overflow-hidden rounded-full">
                <div className="h-full w-1/3 animate-shimmer bg-gradient-to-r from-transparent via-white/40 to-transparent"></div>
              </div>
            </div>
          </div>

          <p className="mt-2 text-sm tabular-nums text-slate-500 dark:text-slate-400">
            {pct}%
          </p>
        </div>
      </div>

      <div className="mt-4 rounded-2xl border border-indigo-300/40 bg-indigo-50/60 p-3 backdrop-blur-md dark:border-indigo-400/20 dark:bg-indigo-500/10">
        <p className="flex items-start gap-2 text-sm text-indigo-800 dark:text-indigo-200">
          <svg
            className="mt-0.5 h-4 w-4 flex-shrink-0"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
            />
          </svg>
          This may take 1–3 minutes depending on file length and settings.
        </p>
      </div>

      <p className="mt-2 text-xs text-slate-400 dark:text-slate-500">
        The final length may not exactly match your target — edits are made at
        whole-section boundaries. For a length within ±15s, enable the Strict
        Length toggle.
      </p>
    </div>
  );
}

export default ProcessingStatus;
