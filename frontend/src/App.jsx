import React, { useState, useEffect, useCallback } from "react";
import AudioUploader from "./components/AudioUploader";
import WaveformDisplay from "./components/WaveformDisplay";
import ControlPanel from "./components/ControlPanel";
import ProcessingStatus from "./components/ProcessingStatus";
import ResultsDisplay from "./components/ResultsDisplay";
import RecentList from "./components/RecentList";
import Logo from "./components/Logo";
import ThemeToggle from "./components/ThemeToggle";
import Marquee from "./components/Marquee";
import {
  processAudio,
  getStatus,
  downloadFile,
  getDownloadUrl,
  deleteJob,
  loadSample,
} from "./services/api";
import useWebSocket from "./hooks/useWebSocket";
import useTheme from "./hooks/useTheme";
import {
  loadRecents,
  upsertRecent,
  removeRecent,
} from "./utils/recentUploads";

/** Soft, slowly drifting colour fields behind the frosted glass. */
function AmbientBackground() {
  return (
    <div
      aria-hidden="true"
      className="pointer-events-none fixed inset-0 -z-10 overflow-hidden"
    >
      <div className="absolute -left-32 -top-40 h-[42rem] w-[42rem] rounded-full bg-violet-400/30 blur-3xl animate-float dark:bg-violet-700/25" />
      <div className="absolute -right-32 top-1/4 h-[38rem] w-[38rem] rounded-full bg-sky-400/30 blur-3xl animate-float [animation-delay:-5s] dark:bg-sky-700/20" />
      <div className="absolute -bottom-48 left-1/4 h-[40rem] w-[40rem] rounded-full bg-indigo-400/25 blur-3xl animate-float [animation-delay:-10s] dark:bg-indigo-700/25" />
    </div>
  );
}

function App() {
  const { isDark, toggleTheme } = useTheme();

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
  const [loadingSample, setLoadingSample] = useState(false);
  const [demoTarget, setDemoTarget] = useState(null);
  const [demoHint, setDemoHint] = useState(false);

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
    setUploadData(data);
    setDemoTarget(null);
    setDemoHint(false);
    setStage("configure");
    setError(null);
  };

  // Load the demo sample, prefill a 70% trim target, and prompt to Generate.
  const handleTrySample = async () => {
    setError(null);
    setLoadingSample(true);
    try {
      const data = await loadSample();
      setUploadData(data);
      setProtectedRegions([]);
      setDemoTarget(data.suggested_target_length ?? null);
      setDemoHint(true);
      setStage("configure");
    } catch (err) {
      setError(
        err.response?.data?.error ||
          "Couldn't load the sample song. Please try again.",
      );
    } finally {
      setLoadingSample(false);
    }
  };

  // Handle region selection
  const handleRegionSelect = (regions) => {
    setProtectedRegions(regions);
  };

  // Handle process start
  const handleProcess = async (params) => {
    if (!uploadData) return;

    setError(null);
    setDemoHint(false);
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
        strictLength: params.strictLength,
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
        autoProtect: results.auto_protect_requested === true,
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
    setDemoTarget(null);
    setDemoHint(false);
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
    // Clear demo prefill/hint so a sample run can't leak its 70% target into a
    // recent upload reopened via "Back to Configure".
    setDemoTarget(null);
    setDemoHint(false);
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
    <div className="relative flex min-h-dvh flex-col">
      <AmbientBackground />

      {/* Header */}
      <header className="sticky top-0 z-30 border-b border-white/40 bg-white/55 backdrop-blur-xl backdrop-saturate-150 transition-colors duration-300 dark:border-white/[0.06] dark:bg-[#05050c]/60">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="grid h-12 w-12 place-items-center rounded-2xl border border-white/60 bg-white/70 shadow-sm dark:border-white/10 dark:bg-white/[0.06]">
              <Logo size={34} />
            </span>
            <div className="leading-tight">
              <h1 className="bg-brand-gradient bg-clip-text font-display text-xl font-bold tracking-tight text-transparent sm:text-2xl">
                Music Smart Trim
              </h1>
              <p className="hidden text-xs text-slate-500 dark:text-slate-400 sm:block">
                Smart audio editing that preserves musical structure
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            {stage !== "upload" && (
              <button
                onClick={handleStartOver}
                className="btn-ghost text-sm"
                aria-label="Start over with a new file"
              >
                <svg
                  className="h-4 w-4"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  viewBox="0 0 24 24"
                  aria-hidden="true"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    d="M10 19l-7-7m0 0l7-7m-7 7h18"
                  />
                </svg>
                <span className="hidden sm:inline">Start Over</span>
              </button>
            )}
            <ThemeToggle isDark={isDark} onToggle={toggleTheme} />
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto w-full max-w-6xl flex-1 px-4 py-8 sm:px-6">
        {error && (
          <div className="mb-6 animate-fade-up rounded-2xl border border-red-300/60 bg-red-50/80 p-4 backdrop-blur-md dark:border-red-500/30 dark:bg-red-950/40">
            <p className="font-semibold text-red-800 dark:text-red-300">Error</p>
            <p className="mt-1 text-sm text-red-600 dark:text-red-400">
              {error}
            </p>
          </div>
        )}

        {/* Stage 1: Upload */}
        {stage === "upload" && (
          <div className="animate-fade-up space-y-6">
            <div className="glass-panel p-8">
              <h2 className="mb-1 font-display text-2xl font-semibold text-slate-900 dark:text-white">
                Upload your track
              </h2>
              <p className="mb-6 text-sm text-slate-500 dark:text-slate-400">
                Drop in a song and we'll find a musical way to reach your target
                length.
              </p>
              <AudioUploader onUploadComplete={handleUploadComplete} />

              {/* Always-available demo entry point. If the sample file isn't
                  present, handleTrySample surfaces a friendly error. */}
              <div className="mt-6">
                <div className="flex items-center gap-3">
                  <span className="h-px flex-1 bg-slate-300/60 dark:bg-white/10" />
                  <span className="text-xs font-medium uppercase tracking-wide text-slate-400 dark:text-slate-500">
                    or
                  </span>
                  <span className="h-px flex-1 bg-slate-300/60 dark:bg-white/10" />
                </div>
                <button
                  onClick={handleTrySample}
                  disabled={loadingSample}
                  className="btn-ghost mt-4 w-full"
                >
                  {loadingSample ? (
                    <>
                      <span className="h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent" />
                      Loading sample…
                    </>
                  ) : (
                    <>
                      <svg
                        className="h-5 w-5 text-indigo-500 dark:text-indigo-400"
                        fill="currentColor"
                        viewBox="0 0 24 24"
                        aria-hidden="true"
                      >
                        <path d="M8 5v14l11-7z" />
                      </svg>
                      Try our sample song
                    </>
                  )}
                </button>
                <p className="mt-2 text-center text-xs text-slate-400 dark:text-slate-500">
                  No file handy? Preview a finished trim in a few seconds.
                </p>
              </div>
            </div>
            <RecentList
              recents={recents}
              onSelect={handleSelectRecent}
              onRemove={handleRemoveRecent}
            />
          </div>
        )}

        {/* Stage 2: Configure */}
        {stage === "configure" && uploadData && (
          <div className="animate-fade-up space-y-6">
            <div className="glass-panel p-6">
              <WaveformDisplay
                audioUrl={getDownloadUrl(uploadData.job_id, uploadData.filename)}
                onRegionSelect={handleRegionSelect}
                protectedRegions={protectedRegions}
                playerHeader
                title={uploadData.display_name || uploadData.filename}
                coverUrl={
                  uploadData.cover_filename
                    ? getDownloadUrl(uploadData.job_id, uploadData.cover_filename)
                    : null
                }
              />
            </div>
            <ControlPanel
              originalLength={uploadData.original_length}
              protectedRegions={protectedRegions}
              onProcess={handleProcess}
              initialTargetLength={demoTarget}
              showGeneratePrompt={demoHint}
              onDismissPrompt={() => setDemoHint(false)}
            />
          </div>
        )}

        {/* Stage 3: Processing */}
        {stage === "processing" && (
          <div className="animate-fade-up">
            <ProcessingStatus
              progress={processingProgress}
              message={processingMessage}
              visible={processing}
            />
          </div>
        )}

        {/* Stage 4: Results */}
        {stage === "results" && results && (
          <div className="animate-fade-up">
            <ResultsDisplay
              results={results.outputs}
              jobId={uploadData?.job_id}
              onRegenerate={handleRegenerate}
              onDownload={handleDownload}
              onBackToConfigure={handleBackToConfigure}
              strictLengthRequested={results.strict_length_requested === true}
              strictLengthMet={results.strict_length_met === true}
            />
          </div>
        )}

        {/* Brand marquee — shown on every stage except the transient
            processing screen (front page, configure, and results). */}
        {stage !== "processing" && (
          <div className="mt-6 animate-fade-up">
            <Marquee />
          </div>
        )}
      </main>

      {/* WebSocket Status Indicator */}
      <div className="fixed bottom-4 right-4 z-40 flex items-center gap-2 rounded-full border border-white/60 bg-white/70 px-3 py-2 text-xs font-medium text-slate-600 shadow-lg backdrop-blur-md dark:border-white/10 dark:bg-white/[0.08] dark:text-slate-300">
        <span
          className={`inline-block h-2 w-2 rounded-full ${
            connected
              ? "bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.7)]"
              : "bg-red-500"
          }`}
        ></span>
        {connected ? "Connected" : "Disconnected"}
      </div>

      {/* Footer */}
      <footer className="border-t border-white/40 bg-white/40 backdrop-blur-md transition-colors duration-300 dark:border-white/[0.06] dark:bg-white/[0.02]">
        <div className="mx-auto max-w-6xl px-4 py-6 text-center text-sm text-slate-500 dark:text-slate-400 sm:px-6">
          Music Smart Trim © 2026
        </div>
      </footer>
    </div>
  );
}

export default App;
