import React, { useState, useEffect, useCallback } from "react";
import AudioUploader from "./components/AudioUploader";
import WaveformDisplay from "./components/WaveformDisplay";
import ControlPanel from "./components/ControlPanel";
import ProcessingStatus from "./components/ProcessingStatus";
import ResultsDisplay from "./components/ResultsDisplay";
import RecentList from "./components/RecentList";
import {
  processAudio,
  getStatus,
  downloadFile,
  getDownloadUrl,
  deleteJob,
} from "./services/api";
import useWebSocket from "./hooks/useWebSocket";
import {
  loadRecents,
  upsertRecent,
  removeRecent,
} from "./utils/recentUploads";

function App() {
  // State management
  const [stage, setStage] = useState("upload"); // upload, configure, processing, results
  const [uploadData, setUploadData] = useState(null);
  const [protectedRegions, setProtectedRegions] = useState([]);
  const [processing, setProcessing] = useState(false);
  const [processingProgress, setProcessingProgress] = useState(0);
  const [processingMessage, setProcessingMessage] = useState("");
  const [results, setResults] = useState(null);
  const [error, setError] = useState(null);
  const [recents, setRecents] = useState(() => loadRecents());

  // WebSocket connection
  const { connected, lastMessage, joinJob, leaveJob } = useWebSocket();

  const persistRecent = useCallback((entry) => {
    const { recents: kept, evicted } = upsertRecent(entry);
    setRecents(kept);
    // Fire-and-forget cleanup of the evicted jobs on the backend.
    evicted.forEach((r) => {
      if (r.jobId && r.jobId !== entry.jobId) {
        deleteJob(r.jobId);
      }
    });
  }, []);

  // Handle upload complete
  const handleUploadComplete = (data) => {
    console.log("Upload complete:", data);
    setUploadData(data);
    setStage("configure");
    setError(null);
  };

  // Handle region selection
  const handleRegionSelect = (regions) => {
    console.log("Selected regions:", regions);
    setProtectedRegions(regions);
  };

  // Handle process start
  const handleProcess = async (params) => {
    if (!uploadData) return;

    setError(null);
    setProcessing(true);
    setStage("processing");
    setProcessingProgress(0);
    setProcessingMessage("Starting processing...");

    if (connected) {
      joinJob(uploadData.job_id);
    }

    try {
      await processAudio({
        jobId: uploadData.job_id,
        targetLength: params.targetLength,
        protectedRegions: params.protectedRegions,
        autoProtect: params.autoProtect,
        useMert: params.useMert,
        strictLength: params.strictLength,
        minSegmentDuration: params.minSegmentDuration,
      });

      pollStatus(uploadData.job_id);
    } catch (err) {
      console.error("Processing error:", err);
      setError(
        err.response?.data?.error || "Processing failed. Please try again.",
      );
      setProcessing(false);
      setStage("configure");
    }
  };

  const pollStatus = useCallback(
    (jobId) => {
      const interval = setInterval(async () => {
        try {
          const status = await getStatus(jobId);
          console.log("Status poll:", status);

          if (status.status === "completed") {
            clearInterval(interval);
            setProcessing(false);
            setResults(status.result);
            // Snapshot this run into the recent list so it can be jumped back to.
            if (uploadData) {
              persistRecent({
                jobId: uploadData.job_id,
                filename: uploadData.filename,
                displayName:
                  uploadData.display_name || uploadData.filename || "Untitled",
                originalLength: uploadData.original_length,
                coverFilename: uploadData.cover_filename || null,
                uploadedAt: new Date().toISOString(),
                result: status.result,
              });
            }
            setStage("results");
            if (connected) {
              leaveJob(jobId);
            }
          } else if (status.status === "failed") {
            clearInterval(interval);
            setProcessing(false);
            setError(status.error || "Processing failed");
            setStage("configure");
            if (connected) {
              leaveJob(jobId);
            }
          }
        } catch (err) {
          console.error("Status poll error:", err);
        }
      }, 2000);

      setTimeout(() => clearInterval(interval), 600000);
    },
    [connected, leaveJob, uploadData, persistRecent],
  );

  // Handle WebSocket progress updates
  useEffect(() => {
    if (lastMessage && lastMessage.job_id === uploadData?.job_id) {
      console.log("WebSocket update:", lastMessage);
      setProcessingProgress(lastMessage.progress);
      setProcessingMessage(lastMessage.message);
    }
  }, [lastMessage, uploadData]);

  // Handle regenerate
  const handleRegenerate = async () => {
    if (!uploadData) return;

    setResults(null);
    setStage("processing");
    setProcessing(true);
    setProcessingProgress(0);
    setProcessingMessage("Regenerating with different parameters...");

    if (connected) {
      joinJob(uploadData.job_id);
    }

    try {
      await processAudio({
        jobId: uploadData.job_id,
        targetLength: results.target_length,
        protectedRegions: protectedRegions.map(
          (r) => `${formatTime(r.start)}-${formatTime(r.end)}`,
        ),
        autoProtect: false,
        useMert: false,
        strictLength: results.strict_length_requested === true,
        regenerateSeed: Date.now() % 1000,
      });

      pollStatus(uploadData.job_id);
    } catch (err) {
      console.error("Regeneration error:", err);
      setError(err.response?.data?.error || "Regeneration failed");
      setProcessing(false);
      setStage("results");
    }
  };

  // Handle download
  const handleDownload = (filename) => {
    if (uploadData) {
      downloadFile(uploadData.job_id, filename);
    }
  };

  // Handle start over
  const handleStartOver = () => {
    setStage("upload");
    setUploadData(null);
    setProtectedRegions([]);
    setProcessing(false);
    setResults(null);
    setError(null);
  };

  // Jump back to configure from results (e.g. to reconfigure protected regions
  // or target length) without losing the audio that's already uploaded.
  const handleBackToConfigure = () => {
    setStage("configure");
    setResults(null);
    setError(null);
  };

  // Restore a recent upload — land directly on results. The audio file and
  // output WAVs are still on the backend as long as the job hasn't been
  // evicted (cache holds top 5).
  const handleSelectRecent = (entry) => {
    if (!entry || !entry.result) return;
    setUploadData({
      job_id: entry.jobId,
      filename: entry.filename,
      display_name: entry.displayName || entry.filename,
      original_length: entry.originalLength,
      cover_filename: entry.coverFilename,
    });
    setProtectedRegions([]);
    setResults(entry.result);
    setError(null);
    setStage("results");
  };

  const handleRemoveRecent = (jobId) => {
    setRecents(removeRecent(jobId));
    deleteJob(jobId);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-900">
                Music Smart Trim
              </h1>
              <p className="text-gray-600 mt-1">
                Smart audio editing that preserves musical structure
              </p>
            </div>
            {stage !== "upload" && (
              <button
                onClick={handleStartOver}
                className="px-4 py-2 text-gray-600 hover:text-gray-900 transition-colors"
              >
                ← Start Over
              </button>
            )}
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 py-8">
        {error && (
          <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-lg">
            <p className="text-red-800 font-semibold">Error</p>
            <p className="text-red-600 text-sm mt-1">{error}</p>
          </div>
        )}

        {/* Stage 1: Upload */}
        {stage === "upload" && (
          <>
            <div className="bg-white rounded-lg shadow-md p-8">
              <h2 className="text-2xl font-semibold mb-6">Upload Audio File</h2>
              <AudioUploader onUploadComplete={handleUploadComplete} />
            </div>
            <RecentList
              recents={recents}
              onSelect={handleSelectRecent}
              onRemove={handleRemoveRecent}
            />
          </>
        )}

        {/* Stage 2: Configure */}
        {stage === "configure" && uploadData && (
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-xl font-semibold mb-4">Audio Waveform</h2>
              <WaveformDisplay
                audioUrl={getDownloadUrl(
                  uploadData.job_id,
                  uploadData.filename,
                )}
                onRegionSelect={handleRegionSelect}
                protectedRegions={protectedRegions}
              />
            </div>
            <ControlPanel
              originalLength={uploadData.original_length}
              protectedRegions={protectedRegions}
              onProcess={handleProcess}
            />
          </div>
        )}

        {/* Stage 3: Processing */}
        {stage === "processing" && (
          <ProcessingStatus
            progress={processingProgress}
            message={processingMessage}
            visible={processing}
          />
        )}

        {/* Stage 4: Results */}
        {stage === "results" && results && (
          <ResultsDisplay
            results={results.outputs}
            jobId={uploadData?.job_id}
            onRegenerate={handleRegenerate}
            onDownload={handleDownload}
            onBackToConfigure={handleBackToConfigure}
            strictLengthRequested={results.strict_length_requested === true}
            strictLengthMet={results.strict_length_met === true}
          />
        )}

        {/* WebSocket Status Indicator */}
        <div className="fixed bottom-4 right-4 px-3 py-2 bg-white rounded-full shadow-lg text-xs">
          <span
            className={`inline-block w-2 h-2 rounded-full mr-2 ${
              connected ? "bg-green-500" : "bg-red-500"
            }`}
          ></span>
          {connected ? "Connected" : "Disconnected"}
        </div>
      </main>

      {/* Footer */}
      <footer className="mt-16 bg-white border-t border-gray-200">
        <div className="max-w-7xl mx-auto px-4 py-6 text-center text-gray-500 text-sm">
          Music Smart Trim © 2026
        </div>
      </footer>
    </div>
  );
}

export default App;
