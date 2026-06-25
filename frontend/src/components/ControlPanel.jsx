import React, { useState, useEffect } from "react";
import { formatTime } from "../utils/formatters";

function ControlPanel({
  originalLength,
  onProcess,
  protectedRegions = [],
  disabled = false,
  initialTargetLength = null,
  initialStrictLength = false,
  showGeneratePrompt = false,
  onDismissPrompt,
}) {
  const [targetLength, setTargetLength] = useState(
    initialTargetLength != null ? String(initialTargetLength) : "",
  );
  const [autoProtect, setAutoProtect] = useState(false);
  const [strictLength, setStrictLength] = useState(initialStrictLength);
  const [mode, setMode] = useState(null);
  const [error, setError] = useState(null);

  // Prefill the target when provided (e.g. the demo's 60s trim).
  useEffect(() => {
    if (initialTargetLength != null) {
      setTargetLength(String(initialTargetLength));
    }
  }, [initialTargetLength]);

  // Pre-enable strict length when requested (the demo turns it on).
  useEffect(() => {
    if (initialStrictLength) {
      setStrictLength(true);
    }
  }, [initialStrictLength]);

  // Determine mode based on target length
  useEffect(() => {
    const target = parseFloat(targetLength);
    if (!isNaN(target) && target > 0) {
      if (target < originalLength) {
        setMode("trim");
      } else if (target > originalLength) {
        setMode("extend");
      } else {
        setMode(null);
      }
    } else {
      setMode(null);
    }
  }, [targetLength, originalLength]);

  // For trim mode, every protected second must still fit inside the output.
  // Cap the sum at the original length so wildly overlapping regions can't
  // produce a misleading "180s protected of a 120s clip" total.
  const protectedTotal = Math.min(
    protectedRegions.reduce((sum, r) => sum + Math.max(0, r.end - r.start), 0),
    originalLength,
  );

  const handleSubmit = (e) => {
    e.preventDefault();
    setError(null);

    const target = parseFloat(targetLength);

    // Validation
    if (isNaN(target) || target <= 0) {
      setError("Please enter a valid target length");
      return;
    }

    if (target === originalLength) {
      setError("Target length must be different from original length");
      return;
    }

    if (target < originalLength && protectedTotal > target) {
      setError(
        `Protected regions total ${protectedTotal.toFixed(1)}s, which is more ` +
          `than the target length of ${target.toFixed(1)}s. ` +
          `Shrink the protected regions or raise the target length.`,
      );
      return;
    }

    // Convert protected regions to MM:SS-MM:SS format
    const formattedRegions = protectedRegions.map((region) => {
      const startStr = formatTime(region.start);
      const endStr = formatTime(region.end);
      return `${startStr}-${endStr}`;
    });

    onProcess({
      targetLength: target,
      autoProtect,
      strictLength,
      protectedRegions: formattedRegions,
    });
  };

  return (
    <div className="glass-panel p-6">
      <h2 className="mb-6 font-display text-xl font-semibold text-slate-900 dark:text-white">
        Processing Settings
      </h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Length Input */}
        <div>
          <label
            htmlFor="targetLength"
            className="mb-2 block text-sm font-medium text-slate-700 dark:text-slate-300"
          >
            Target Length (seconds)
          </label>
          <div className="relative">
            <input
              id="targetLength"
              type="number"
              min="1"
              step="1"
              value={targetLength}
              onChange={(e) => setTargetLength(e.target.value)}
              placeholder={`Original: ${originalLength.toFixed(0)}s`}
              disabled={disabled}
              className="glass-input pr-28 tabular-nums"
            />
            {mode && (
              <div
                className={`absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full px-3 py-1 text-xs font-semibold ${
                  mode === "trim"
                    ? "bg-orange-500/15 text-orange-700 dark:bg-orange-400/15 dark:text-orange-300"
                    : "bg-emerald-500/15 text-emerald-700 dark:bg-emerald-400/15 dark:text-emerald-300"
                }`}
              >
                {mode === "trim" ? "TRIM" : "EXTEND"}
              </div>
            )}
          </div>
          <p className="mt-1.5 text-xs text-slate-500 dark:text-slate-400">
            Original length: {formatTime(originalLength)} (
            {originalLength.toFixed(1)}s)
          </p>
        </div>

        {/* Auto Protect Toggle */}
        <div className="glass-soft flex items-center justify-between gap-4 p-4">
          <div className="flex-1">
            <label
              htmlFor="autoProtect"
              className="cursor-pointer font-medium text-slate-800 dark:text-slate-100"
            >
              Auto-Protect Intro/Outro
            </label>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Automatically protect the first and last 10–15 seconds.
            </p>
          </div>
          <label className="relative inline-flex shrink-0 cursor-pointer items-center">
            <input
              id="autoProtect"
              type="checkbox"
              checked={autoProtect}
              onChange={(e) => setAutoProtect(e.target.checked)}
              disabled={disabled}
              className="peer sr-only"
            />
            <div className="peer h-6 w-11 rounded-full bg-slate-300 transition-colors after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-all after:content-[''] peer-checked:bg-indigo-500 peer-checked:after:translate-x-full peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-400/70 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-transparent dark:bg-white/15 dark:peer-checked:bg-indigo-500"></div>
          </label>
        </div>

        {/* Strict Length Toggle */}
        <div className="glass-soft flex items-center justify-between gap-4 p-4">
          <div className="flex-1">
            <label
              htmlFor="strictLength"
              className="cursor-pointer font-medium text-slate-800 dark:text-slate-100"
            >
              Strict Length (±15s)
            </label>
            <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
              Force the output to stay within 15 seconds of your target. Cuts
              may sound rougher because length is prioritized over musical
              quality. If no option fits after several refinement passes, the
              closest results are shown with a warning.
            </p>
          </div>
          <label className="relative inline-flex shrink-0 cursor-pointer items-center">
            <input
              id="strictLength"
              type="checkbox"
              checked={strictLength}
              onChange={(e) => setStrictLength(e.target.checked)}
              disabled={disabled}
              className="peer sr-only"
            />
            <div className="peer h-6 w-11 rounded-full bg-slate-300 transition-colors after:absolute after:left-[2px] after:top-[2px] after:h-5 after:w-5 after:rounded-full after:bg-white after:shadow-sm after:transition-all after:content-[''] peer-checked:bg-indigo-500 peer-checked:after:translate-x-full peer-focus-visible:ring-2 peer-focus-visible:ring-indigo-400/70 peer-focus-visible:ring-offset-2 peer-focus-visible:ring-offset-transparent dark:bg-white/15 dark:peer-checked:bg-indigo-500"></div>
          </label>
        </div>

        {/* Protected Regions Info */}
        {protectedRegions.length > 0 && (
          <div className="rounded-2xl border border-indigo-300/50 bg-indigo-50/70 p-4 backdrop-blur-md dark:border-indigo-400/20 dark:bg-indigo-500/10">
            <p className="mb-2 text-sm font-medium text-indigo-800 dark:text-indigo-200">
              Protected Regions: {protectedRegions.length}{" "}
              <span className="font-normal text-indigo-600 dark:text-indigo-300">
                — total {protectedTotal.toFixed(1)}s
              </span>
            </p>
            <div className="space-y-1">
              {protectedRegions.map((region, idx) => (
                <p
                  key={idx}
                  className="text-xs tabular-nums text-indigo-600 dark:text-indigo-300"
                >
                  Region {idx + 1}: {formatTime(region.start)} –{" "}
                  {formatTime(region.end)}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="rounded-2xl border border-red-300/60 bg-red-50/80 p-3 backdrop-blur-md dark:border-red-500/30 dark:bg-red-950/40">
            <p className="text-sm text-red-600 dark:text-red-400">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        {(() => {
          const target = parseFloat(targetLength);
          const overProtected =
            mode === "trim" && !isNaN(target) && protectedTotal > target;
          return (
            <div className="relative">
              {/* Demo coach-mark pointing at Generate (dismissable). The
                  positioning transform (outer) is kept separate from the
                  entrance animation (inner) so they don't clobber each other. */}
              {showGeneratePrompt && (
                <div className="absolute -top-3 left-1/2 z-20 w-72 max-w-[88vw] -translate-x-1/2 -translate-y-full">
                  <div className="animate-fade-up">
                    <div className="relative rounded-2xl border border-white/60 bg-white/95 p-4 pr-9 text-left shadow-xl backdrop-blur-xl dark:border-white/10 dark:bg-[#10101e]/95">
                      <button
                        type="button"
                        onClick={onDismissPrompt}
                        aria-label="Dismiss tip"
                        className="absolute right-2 top-2 rounded-lg p-1 text-slate-400 transition-colors hover:bg-slate-500/10 hover:text-slate-700 dark:hover:text-slate-200"
                      >
                        <svg
                          className="h-4 w-4"
                          fill="none"
                          stroke="currentColor"
                          strokeWidth="2"
                          viewBox="0 0 24 24"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M6 18L18 6M6 6l12 12"
                          />
                        </svg>
                      </button>
                      <p className="text-sm font-semibold text-slate-900 dark:text-white">
                        Your sample is ready
                      </p>
                      <p className="mt-1 text-xs text-slate-500 dark:text-slate-400">
                        We set a target length and switched on strict length so
                        the result lands close to it. Click Generate to hear it.
                      </p>
                    </div>
                    <div className="mx-auto -mt-1.5 h-3 w-3 rotate-45 border-b border-r border-white/60 bg-white/95 dark:border-white/10 dark:bg-[#10101e]" />
                  </div>
                </div>
              )}
              <button
                type="submit"
                disabled={disabled || !targetLength || !mode || overProtected}
                className="btn-primary w-full"
              >
                {disabled
                  ? "Processing…"
                  : overProtected
                    ? "Protected regions exceed target"
                    : `Generate${mode ? ` · ${mode === "trim" ? "Trim" : "Extend"}` : ""}`}
              </button>
            </div>
          );
        })()}
      </form>
    </div>
  );
}

export default ControlPanel;
