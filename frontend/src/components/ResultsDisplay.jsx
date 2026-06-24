import React from "react";
import { formatStarRating, formatTime } from "../utils/formatters";
import { getDownloadUrl } from "../services/api";
import WaveformDisplay from "./WaveformDisplay";
import useTheme from "../hooks/useTheme";

function ResultCard({ result, jobId, rank, isPrimary = false, onDownload }) {
  const { isDark } = useTheme();
  const audioUrl = getDownloadUrl(jobId, result.filename);

  // Brand indigo progress for the best take; muted slate for alternates.
  const waveColor = isPrimary
    ? isDark
      ? "#64748b"
      : "#94a3b8"
    : isDark
      ? "#3f445c"
      : "#cbd5e1";
  const progressColor = isPrimary
    ? isDark
      ? "#818cf8"
      : "#6366f1"
    : isDark
      ? "#64748b"
      : "#94a3b8";

  return (
    <div
      className={
        "p-6 " +
        (isPrimary
          ? "glass-panel ring-1 ring-indigo-400/40 dark:ring-indigo-400/30"
          : "glass-soft opacity-95")
      }
    >
      <div className="mb-4 flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-3">
            <span
              className={
                "font-display text-2xl font-bold " +
                (isPrimary
                  ? "text-indigo-600 dark:text-indigo-400"
                  : "text-slate-400 dark:text-slate-500")
              }
            >
              #{rank}
            </span>
            {isPrimary && (
              <span className="rounded-full bg-brand-gradient px-3 py-1 text-xs font-semibold text-white shadow-sm">
                BEST
              </span>
            )}
          </div>
          <p
            className={
              "mt-2 text-3xl " +
              (isPrimary
                ? "text-amber-400"
                : "text-slate-400 dark:text-slate-500")
            }
            aria-label={`${result.rating.toFixed(1)} out of 5 stars`}
          >
            {formatStarRating(result.rating)}
          </p>
          <p
            className={
              "mt-1 text-sm tabular-nums " +
              (isPrimary
                ? "text-slate-600 dark:text-slate-300"
                : "text-slate-500 dark:text-slate-400")
            }
          >
            {result.rating.toFixed(1)} / 5.0 stars
          </p>
        </div>

        <div className="text-right">
          <p className="text-sm text-slate-500 dark:text-slate-400">Duration</p>
          <p
            className={
              "text-lg font-semibold tabular-nums " +
              (isPrimary
                ? "text-slate-900 dark:text-white"
                : "text-slate-600 dark:text-slate-300")
            }
          >
            {formatTime(result.length)}
          </p>
          <p className="text-xs tabular-nums text-slate-400 dark:text-slate-500">
            ({result.length.toFixed(1)}s)
          </p>
        </div>
      </div>

      {/* Waveform + playback handled by WaveSurfer */}
      <div className="mb-4">
        <WaveformDisplay
          audioUrl={audioUrl}
          height={80}
          readOnly
          waveColor={waveColor}
          progressColor={progressColor}
        />
      </div>

      <div className="flex items-center justify-between gap-3">
        <p className="truncate text-xs text-slate-400 dark:text-slate-500">
          {result.filename}
        </p>
        <button
          onClick={() => onDownload(result.filename)}
          className="btn-ghost px-3 py-1.5 text-sm"
          title="Download"
        >
          <svg
            className="h-4 w-4"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"
            />
          </svg>
          Download
        </button>
      </div>
    </div>
  );
}

function ResultsDisplay({
  results,
  jobId,
  onRegenerate,
  onDownload,
  onBackToConfigure,
  strictLengthRequested = false,
  strictLengthMet = false,
}) {
  if (!results || results.length === 0) {
    return null;
  }

  const [primary, ...alternates] = results;
  const showStrictFallback = strictLengthRequested && !strictLengthMet;

  return (
    <div className="glass-panel p-6">
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <h2 className="font-display text-2xl font-bold text-slate-900 dark:text-white">
          Results
        </h2>
        <div className="flex items-center gap-2">
          {onBackToConfigure && (
            <button onClick={onBackToConfigure} className="btn-ghost text-sm">
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
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
              Back to Configure
            </button>
          )}
          <button onClick={onRegenerate} className="btn-primary text-sm">
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Regenerate
          </button>
        </div>
      </div>

      {showStrictFallback && (
        <div className="mb-6 rounded-2xl border border-amber-300/60 bg-amber-50/80 p-4 backdrop-blur-md dark:border-amber-400/30 dark:bg-amber-500/10">
          <p className="text-sm font-semibold text-amber-900 dark:text-amber-200">
            Strict length couldn't be met
          </p>
          <p className="mt-1 text-sm text-amber-800 dark:text-amber-300/90">
            We tried progressively more aggressive edits but none landed within
            15 seconds of your target. Showing the closest options we found
            instead — their durations may be more than 15s off target.
          </p>
        </div>
      )}

      {/* Primary Result */}
      <div className="mb-6">
        <ResultCard
          result={primary}
          jobId={jobId}
          rank={1}
          isPrimary={true}
          onDownload={onDownload}
        />
      </div>

      {/* Alternates */}
      {alternates.length > 0 && (
        <div>
          <h3 className="mb-3 font-display text-lg font-semibold text-slate-700 dark:text-slate-200">
            Alternative Options
          </h3>
          <div className="space-y-4">
            {alternates.map((result, idx) => (
              <ResultCard
                key={result.filename}
                result={result}
                jobId={jobId}
                rank={idx + 2}
                isPrimary={false}
                onDownload={onDownload}
              />
            ))}
          </div>
        </div>
      )}

      <div className="glass-soft mt-6 space-y-2 p-4">
        <p className="text-sm text-slate-600 dark:text-slate-300">
          Showing top 3 results out of 5 strategies, ranked by quality score.
          The best result is highlighted. Play each option, then download the
          version you like — or click Regenerate for 3 different variations.
        </p>
        <p className="text-sm text-slate-500 dark:text-slate-400">
          <span className="font-medium text-slate-700 dark:text-slate-200">
            Heads up:
          </span>{" "}
          some options may sound similar to each other. Songs with a tight
          section structure (few clear chorus/verse boundaries) can leave the
          engine with limited cut choices, so several strategies end up landing
          on the same cuts. Regenerate can also return overlapping results for
          the same reason — try adjusting the target length or protected regions
          if you want more variety.
        </p>
      </div>
    </div>
  );
}

export default ResultsDisplay;
