import React, { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.js";

const COMMITTED_COLOR = "rgba(239, 68, 68, 0.3)"; // red — committed protected region
const PENDING_COLOR = "rgba(234, 179, 8, 0.35)"; // amber — awaiting confirmation

function WaveformDisplay({
  audioUrl,
  onRegionSelect,
  protectedRegions = [],
  height = 128,
  readOnly = false,
  waveColor = "#9ca3af",
  progressColor = "#3b82f6",
}) {
  const containerRef = useRef(null);
  const wavesurferRef = useRef(null);
  const regionsPluginRef = useRef(null);
  // The current draft region (a WaveSurfer Region instance) that has not yet
  // been confirmed. Lives in WaveSurfer only — not yet in the parent's prop.
  const pendingRegionRef = useRef(null);
  const [pendingRange, setPendingRange] = useState(null); // { start, end } or null
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [loading, setLoading] = useState(true);

  // Keep latest onRegionSelect in a ref so the effect below doesn't re-run
  // whenever the parent re-renders (the callback identity changes each render).
  const onRegionSelectRef = useRef(onRegionSelect);
  useEffect(() => {
    onRegionSelectRef.current = onRegionSelect;
  }, [onRegionSelect]);

  // Keep latest protectedRegions in a ref so the once-per-mount event handlers
  // below see the current committed list when they need to call back.
  const protectedRegionsRef = useRef(protectedRegions);
  useEffect(() => {
    protectedRegionsRef.current = protectedRegions;
  }, [protectedRegions]);

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return;

    const wavesurfer = WaveSurfer.create({
      container: containerRef.current,
      waveColor,
      progressColor,
      cursorColor: "#1e40af",
      barWidth: 2,
      barRadius: 3,
      cursorWidth: 2,
      height,
      barGap: 1,
      responsive: true,
      normalize: true,
    });

    wavesurferRef.current = wavesurfer;

    // Result-card waveforms are play-only — skip the regions plugin entirely.
    const regionsPlugin = readOnly
      ? null
      : wavesurfer.registerPlugin(RegionsPlugin.create());
    regionsPluginRef.current = regionsPlugin;

    wavesurfer.load(audioUrl).catch((err) => {
      if (err?.name !== "AbortError") {
        console.error("WaveSurfer load error:", err);
      }
    });

    wavesurfer.on("ready", () => {
      setLoading(false);
      setDuration(wavesurfer.getDuration());
      // Drag-to-create only makes sense once the waveform has rendered.
      if (regionsPlugin) {
        regionsPlugin.enableDragSelection({ color: PENDING_COLOR });
      }
    });

    wavesurfer.on("play", () => setIsPlaying(true));
    wavesurfer.on("pause", () => setIsPlaying(false));
    wavesurfer.on("audioprocess", () => setCurrentTime(wavesurfer.getCurrentTime()));
    wavesurfer.on("seeking", () => setCurrentTime(wavesurfer.getCurrentTime()));

    if (regionsPlugin) {
      // A brand-new region (drag-created or via Add Region) is *pending* —
      // we only have one pending slot, so replace any prior pending region.
      regionsPlugin.on("region-created", (region) => {
        if (region?.data?.kind === "committed") return;
        if (pendingRegionRef.current && pendingRegionRef.current !== region) {
          pendingRegionRef.current.remove();
        }
        region.setOptions({ color: PENDING_COLOR });
        if (region.data) {
          region.data.kind = "pending";
        }
        pendingRegionRef.current = region;
        setPendingRange({ start: region.start, end: region.end });
      });

      regionsPlugin.on("region-updated", (region) => {
        // Pending: just track the new bounds, do NOT notify the parent yet.
        if (region === pendingRegionRef.current) {
          setPendingRange({ start: region.start, end: region.end });
          return;
        }
        // Committed: surface the new bounds for ALL committed regions.
        const committed = regionsPlugin
          .getRegions()
          .filter((r) => r !== pendingRegionRef.current)
          .map((r) => ({ start: r.start, end: r.end }));
        onRegionSelectRef.current?.(committed);
      });
    }

    return () => {
      try {
        wavesurfer.destroy();
      } catch (err) {
        if (err?.name !== "AbortError") {
          console.error("WaveSurfer destroy error:", err);
        }
      }
      pendingRegionRef.current = null;
    };
  }, [audioUrl, height, readOnly, waveColor, progressColor]);

  // Sync committed regions from the parent prop into WaveSurfer. The pending
  // region (if any) is preserved across this sync.
  useEffect(() => {
    const plugin = regionsPluginRef.current;
    if (!plugin) return;

    plugin.getRegions().forEach((r) => {
      if (r !== pendingRegionRef.current) r.remove();
    });

    protectedRegions.forEach((region) => {
      plugin.addRegion({
        start: region.start,
        end: region.end,
        color: COMMITTED_COLOR,
        drag: true,
        resize: true,
        data: { kind: "committed" },
      });
    });
  }, [protectedRegions]);

  const togglePlayPause = () => {
    if (wavesurferRef.current) {
      wavesurferRef.current.playPause();
    }
  };

  const startNewRegion = () => {
    const plugin = regionsPluginRef.current;
    const ws = wavesurferRef.current;
    if (!plugin || !ws) return;
    const dur = ws.getDuration();
    if (!dur) return;
    plugin.addRegion({
      start: dur * 0.3,
      end: dur * 0.5,
      color: PENDING_COLOR,
      drag: true,
      resize: true,
      data: { kind: "pending" },
    });
    // region-created handler will pick this up and set pendingRegionRef.
  };

  const confirmPending = () => {
    if (!pendingRegionRef.current) return;
    const { start, end } = pendingRegionRef.current;
    pendingRegionRef.current.remove();
    pendingRegionRef.current = null;
    setPendingRange(null);
    const next = [...(protectedRegionsRef.current || []), { start, end }];
    onRegionSelectRef.current?.(next);
  };

  const cancelPending = () => {
    if (pendingRegionRef.current) {
      pendingRegionRef.current.remove();
      pendingRegionRef.current = null;
    }
    setPendingRange(null);
  };

  const clearAll = () => {
    if (pendingRegionRef.current) {
      pendingRegionRef.current.remove();
      pendingRegionRef.current = null;
      setPendingRange(null);
    }
    onRegionSelectRef.current?.([]);
  };

  const formatTime = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins}:${secs.toString().padStart(2, "0")}`;
  };

  return (
    <div className="w-full">
      {loading && (
        <div className="flex items-center justify-center h-32 bg-gray-100 rounded-lg">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-primary"></div>
        </div>
      )}

      <div ref={containerRef} className={loading ? "hidden" : ""} />

      {!loading && (
        <div className="mt-4 space-y-3">
          {/* Playback controls */}
          <div className="flex items-center justify-between">
            <button
              onClick={togglePlayPause}
              className="px-4 py-2 bg-primary text-white rounded-lg hover:bg-blue-600 transition-colors flex items-center gap-2"
            >
              {isPlaying ? (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zM7 8a1 1 0 012 0v4a1 1 0 11-2 0V8zm5-1a1 1 0 00-1 1v4a1 1 0 102 0V8a1 1 0 00-1-1z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Pause
                </>
              ) : (
                <>
                  <svg
                    className="w-5 h-5"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z"
                      clipRule="evenodd"
                    />
                  </svg>
                  Play
                </>
              )}
            </button>

            <div className="text-sm text-gray-600">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
          </div>

          {/* Region controls — hidden for read-only (result-card) waveforms */}
          {!readOnly && (
            <div className="space-y-3">
              <div className="flex items-center gap-3 flex-wrap">
                <button
                  onClick={startNewRegion}
                  disabled={Boolean(pendingRange)}
                  className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 disabled:bg-gray-100 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors text-sm"
                >
                  Add Protected Region
                </button>
                <button
                  onClick={clearAll}
                  className="px-3 py-1.5 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition-colors text-sm"
                >
                  Clear All
                </button>
                <span className="text-xs text-gray-500">
                  Drag on the waveform to draw a region. Resize it, then press Confirm.
                </span>
              </div>

              {pendingRange && (
                <div className="flex items-center gap-3 p-3 bg-amber-50 border border-amber-200 rounded">
                  <div className="flex-1 text-sm text-amber-900">
                    <span className="font-semibold">Pending region:</span>{" "}
                    {formatTime(pendingRange.start)} – {formatTime(pendingRange.end)}{" "}
                    <span className="text-amber-700">
                      ({(pendingRange.end - pendingRange.start).toFixed(1)}s)
                    </span>
                  </div>
                  <button
                    onClick={confirmPending}
                    className="px-3 py-1.5 bg-primary text-white rounded hover:bg-blue-600 transition-colors text-sm font-medium"
                  >
                    Confirm Region
                  </button>
                  <button
                    onClick={cancelPending}
                    className="px-3 py-1.5 bg-white text-gray-700 border border-gray-300 rounded hover:bg-gray-50 transition-colors text-sm"
                  >
                    Cancel
                  </button>
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default WaveformDisplay;
