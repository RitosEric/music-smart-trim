import React from "react";
import { formatStarRating, formatTime } from "../utils/formatters";
import { getDownloadUrl } from "../services/api";
import WaveformDisplay from "./WaveformDisplay";

function ResultCard({ result, jobId, rank, isPrimary = false, onDownload }) {
  const audioUrl = getDownloadUrl(jobId, result.filename);

  return (
    <div
      className={
        "rounded-lg border-2 p-6 transition-all duration-200 " +
        (isPrimary
          ? "border-primary bg-blue-50 shadow-lg"
          : "border-gray-300 bg-gray-100 opacity-75")
      }
    >
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center gap-3">
            <span
              className={
                "text-2xl font-bold " +
                (isPrimary ? "text-primary" : "text-gray-500")
              }
            >
              #{rank}
            </span>
            {isPrimary && (
              <span className="px-3 py-1 bg-primary text-white text-xs font-semibold rounded-full">
                BEST
              </span>
            )}
          </div>
          <p
            className={
              "text-3xl mt-2 " + (isPrimary ? "" : "text-gray-500")
            }
          >
            {formatStarRating(result.rating)}
          </p>
          <p
            className={
              "text-sm mt-1 " +
              (isPrimary ? "text-gray-600" : "text-gray-500")
            }
          >
            {result.rating.toFixed(1)} / 5.0 stars
          </p>
        </div>

        <div className="text-right">
          <p
            className={
              "text-sm " + (isPrimary ? "text-gray-600" : "text-gray-500")
            }
          >
            Duration
          </p>
          <p
            className={
              "text-lg font-semibold " +
              (isPrimary ? "text-gray-800" : "text-gray-600")
            }
          >
            {formatTime(result.length)}
          </p>
          <p className="text-xs text-gray-500">({result.length.toFixed(1)}s)</p>
        </div>
      </div>

      {/* Waveform + playback handled by WaveSurfer */}
      <div className="mb-4">
        <WaveformDisplay
          audioUrl={audioUrl}
          height={80}
          readOnly
          waveColor={isPrimary ? "#9ca3af" : "#d1d5db"}
          progressColor={isPrimary ? "#3b82f6" : "#9ca3af"}
        />
      </div>

      <div className="flex items-center justify-between">
        <p className="text-xs text-gray-500">{result.filename}</p>
        <button
          onClick={() => onDownload(result.filename)}
          className={
            "px-3 py-1.5 text-sm border rounded transition-colors flex items-center gap-1 " +
            (isPrimary
              ? "text-gray-600 hover:text-primary border-gray-300 hover:border-primary"
              : "text-gray-500 hover:text-gray-700 border-gray-400 hover:border-gray-600")
          }
          title="Download"
        >
          <svg
            className="w-4 h-4"
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
}) {
  if (!results || results.length === 0) {
    return null;
  }

  const [primary, ...alternates] = results;

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center justify-between mb-6 flex-wrap gap-3">
        <h2 className="text-2xl font-bold text-gray-800">Results</h2>
        <div className="flex items-center gap-2">
          {onBackToConfigure && (
            <button
              onClick={onBackToConfigure}
              className="px-4 py-2 bg-white text-gray-700 border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors flex items-center gap-2"
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
                  d="M10 19l-7-7m0 0l7-7m-7 7h18"
                />
              </svg>
              Back to Configure
            </button>
          )}
          <button
            onClick={onRegenerate}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors flex items-center gap-2"
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
                d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
              />
            </svg>
            Regenerate
          </button>
        </div>
      </div>

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
          <h3 className="text-lg font-semibold text-gray-700 mb-3">
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

      <div className="mt-6 p-4 bg-gray-50 border border-gray-200 rounded-lg space-y-2">
        <p className="text-sm text-gray-600">
          Showing top 3 results out of 5 strategies, ranked by quality score.
          The best result is highlighted. Play each option, then download
          the version you like — or click Regenerate for 3 different variations.
        </p>
        <p className="text-sm text-gray-500">
          <span className="font-medium text-gray-700">Heads up:</span> some
          options may sound similar to each other. Songs with a tight section
          structure (few clear chorus/verse boundaries) can leave the engine
          with limited cut choices, so several strategies end up landing on the
          same cuts. Regenerate can also return overlapping results for the
          same reason — try adjusting the target length or protected regions
          if you want more variety.
        </p>
      </div>
    </div>
  );
}

export default ResultsDisplay;
