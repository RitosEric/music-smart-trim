import React, { useState, useEffect } from "react";
import { formatTime } from "../utils/formatters";

function ControlPanel({
  originalLength,
  onProcess,
  protectedRegions = [],
  disabled = false,
}) {
  const [targetLength, setTargetLength] = useState("");
  const [autoProtect, setAutoProtect] = useState(false);
  const [useMert, setUseMert] = useState(false);
  const [strictLength, setStrictLength] = useState(false);
  const [minSegmentDuration, setMinSegmentDuration] = useState(10.0);
  const [mode, setMode] = useState(null);
  const [error, setError] = useState(null);

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
      useMert,
      strictLength,
      minSegmentDuration,
      protectedRegions: formattedRegions,
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <h2 className="text-xl font-semibold mb-6">Processing Settings</h2>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Target Length Input */}
        <div>
          <label
            htmlFor="targetLength"
            className="block text-sm font-medium text-gray-700 mb-2"
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
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100 disabled:cursor-not-allowed"
            />
            {mode && (
              <div
                className={`absolute right-3 top-2.5 px-3 py-1 rounded-full text-xs font-semibold ${
                  mode === "trim"
                    ? "bg-orange-100 text-orange-800"
                    : "bg-green-100 text-green-800"
                }`}
              >
                {mode === "trim" ? "✂️ TRIM" : "➕ EXTEND"}
              </div>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-500">
            Original length: {formatTime(originalLength)} (
            {originalLength.toFixed(1)}s)
          </p>
        </div>

        {/* Auto Protect Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex-1">
            <label
              htmlFor="autoProtect"
              className="font-medium text-gray-700 cursor-pointer"
            >
              Auto-Protect Intro/Outro
            </label>
            <p className="text-xs text-gray-500 mt-1">
              Automatically protect the first and last 10-15 seconds
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              id="autoProtect"
              type="checkbox"
              checked={autoProtect}
              onChange={(e) => setAutoProtect(e.target.checked)}
              disabled={disabled}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        {/* MERT Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex-1">
            <label
              htmlFor="useMert"
              className="font-medium text-gray-700 cursor-pointer"
            >
              Use MERT Quality Scoring
            </label>
            <p className="text-xs text-gray-500 mt-1">
              Enhanced quality assessment (slower but more accurate)
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              id="useMert"
              type="checkbox"
              checked={useMert}
              onChange={(e) => setUseMert(e.target.checked)}
              disabled={disabled}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        {/* Strict Length Toggle */}
        <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
          <div className="flex-1">
            <label
              htmlFor="strictLength"
              className="font-medium text-gray-700 cursor-pointer"
            >
              Strict Length (±15s)
            </label>
            <p className="text-xs text-gray-500 mt-1">
              Force the output to stay within 15 seconds of your target. Cuts
              may sound rougher because length is prioritized over musical
              quality. If no compliant option can be found after 5 retries, the
              closest options will be shown with a warning.
            </p>
          </div>
          <label className="relative inline-flex items-center cursor-pointer">
            <input
              id="strictLength"
              type="checkbox"
              checked={strictLength}
              onChange={(e) => setStrictLength(e.target.checked)}
              disabled={disabled}
              className="sr-only peer"
            />
            <div className="w-11 h-6 bg-gray-200 peer-focus:outline-none peer-focus:ring-4 peer-focus:ring-blue-300 rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:border-gray-300 after:border after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-primary"></div>
          </label>
        </div>

        {/* Min Segment Duration (for extend mode) */}
        {mode === "extend" && (
          <div>
            <label
              htmlFor="minSegment"
              className="block text-sm font-medium text-gray-700 mb-2"
            >
              Minimum Segment Duration (seconds)
            </label>
            <input
              id="minSegment"
              type="number"
              min="5"
              max="60"
              step="1"
              value={minSegmentDuration}
              onChange={(e) =>
                setMinSegmentDuration(parseFloat(e.target.value))
              }
              disabled={disabled}
              className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary focus:border-transparent disabled:bg-gray-100"
            />
            <p className="mt-1 text-xs text-gray-500">
              Minimum length for segments to repeat during extension
            </p>
          </div>
        )}

        {/* Protected Regions Info */}
        {protectedRegions.length > 0 && (
          <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg">
            <p className="text-sm font-medium text-blue-800 mb-2">
              Protected Regions: {protectedRegions.length}{" "}
              <span className="font-normal text-blue-700">
                — total {protectedTotal.toFixed(1)}s
              </span>
            </p>
            <div className="space-y-1">
              {protectedRegions.map((region, idx) => (
                <p key={idx} className="text-xs text-blue-700">
                  Region {idx + 1}: {formatTime(region.start)} -{" "}
                  {formatTime(region.end)}
                </p>
              ))}
            </div>
          </div>
        )}

        {/* Error Message */}
        {error && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-sm text-red-600">{error}</p>
          </div>
        )}

        {/* Submit Button */}
        {(() => {
          const target = parseFloat(targetLength);
          const overProtected =
            mode === "trim" &&
            !isNaN(target) &&
            protectedTotal > target;
          return (
            <button
              type="submit"
              disabled={disabled || !targetLength || !mode || overProtected}
              className="w-full px-6 py-3 bg-primary text-white font-semibold rounded-lg hover:bg-blue-600 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors shadow-md hover:shadow-lg"
            >
              {disabled
                ? "Processing..."
                : overProtected
                  ? "Protected regions exceed target"
                  : `Start Processing (${mode || "Enter target length"})`}
            </button>
          );
        })()}
      </form>
    </div>
  );
}

export default ControlPanel;
