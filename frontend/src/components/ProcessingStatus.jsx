import React from "react";

function ProcessingStatus({
  progress = 0,
  message = "Processing...",
  visible = true,
}) {
  if (!visible) return null;

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex items-center gap-4">
        <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary flex-shrink-0"></div>

        <div className="flex-1">
          <p className="text-lg font-semibold text-gray-800 mb-2">{message}</p>

          <div className="w-full bg-gray-200 rounded-full h-3 overflow-hidden">
            <div
              className="bg-primary h-3 rounded-full transition-all duration-300 ease-out"
              style={{ width: `${Math.min(100, Math.max(0, progress))}%` }}
            ></div>
          </div>

          <p className="text-sm text-gray-600 mt-2">{progress}%</p>
        </div>
      </div>

      <div className="mt-4 p-3 bg-blue-50 border border-blue-200 rounded-lg">
        <p className="text-sm text-blue-700">
          💡 This may take 1-3 minutes depending on file length and settings
        </p>
      </div>

      <p className="mt-2 text-xs text-gray-400">
        The final length may not exactly match your target — edits are made at
        whole-section boundaries. For a length within ±15s, enable the Strict
        Length toggle.
      </p>
    </div>
  );
}

export default ProcessingStatus;
