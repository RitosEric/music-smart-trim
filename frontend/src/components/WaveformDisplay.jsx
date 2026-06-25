import React, { useEffect, useRef, useState } from "react";
import WaveSurfer from "wavesurfer.js";
import RegionsPlugin from "wavesurfer.js/dist/plugins/regions.js";
import useTheme from "../hooks/useTheme";

const COMMITTED_COLOR = "rgba(239, 68, 68, 0.3)"; // red — committed protected region
const PENDING_COLOR = "rgba(234, 179, 8, 0.35)"; // amber — awaiting confirmation

/** Album-art thumbnail with a brand-gradient music-note fallback. */
function PlayerCover({ coverUrl, title }) {
  const [errored, setErrored] = useState(false);
  if (!coverUrl || errored) {
    return (
      <div className="grid h-16 w-16 shrink-0 place-items-center rounded-xl bg-brand-gradient text-white/90 shadow-sm">
        <svg className="h-7 w-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
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
      src={coverUrl}
      alt={title ? `Cover for ${title}` : "Album cover"}
      onError={() => setErrored(true)}
      className="h-16 w-16 shrink-0 rounded-xl bg-slate-200 object-cover shadow-sm dark:bg-white/10"
    />
  );
}

function WaveformDisplay({
  audioUrl,
  onRegionSelect,
  protectedRegions = [],
  height = 128,
  readOnly = false,
  waveColor = null,
  progressColor = null,
  coverUrl = null,
  title = null,
  playerHeader = false,
}) {
  const { isDark } = useTheme();
  // Theme-aware defaults; explicit props (e.g. result cards) still win.
  const effWave = waveColor ?? (isDark ? "#475569" : "#cbd5e1");
  const effProgress = progressColor ?? (isDark ? "#818cf8" : "#6366f1");
  const effCursor = isDark ? "#a5b4fc" : "#4f46e5";
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

  // Hold the current colours in a ref so the WaveSurfer-creation effect can read
  // them at mount without listing them as deps (which would tear down and reload
  // the whole waveform on every theme toggle).
  const colorsRef = useRef({ effWave, effProgress, effCursor });
  useEffect(() => {
    colorsRef.current = { effWave, effProgress, effCursor };
    const ws = wavesurferRef.current;
    if (ws) {
      try {
        ws.setOptions({
          waveColor: effWave,
          progressColor: effProgress,
          cursorColor: effCursor,
        });
      } catch (e) {
        /* instance may be mid-teardown */
      }
    }
  }, [effWave, effProgress, effCursor]);

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
      waveColor: colorsRef.current.effWave,
      progressColor: colorsRef.current.effProgress,
      cursorColor: colorsRef.current.effCursor,
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
    // Colours are applied imperatively via setOptions (see colorsRef effect),
    // so they're intentionally excluded here to avoid reloading on theme change.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [audioUrl, height, readOnly]);

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
      {/* Mini player — cover, title, big play button (configure view) */}
      {playerHeader && (
        <div className="mb-4 flex items-center gap-4">
          <PlayerCover coverUrl={coverUrl} title={title} />
          <div className="min-w-0 flex-1">
            <p className="truncate font-display font-semibold text-slate-900 dark:text-white">
              {title || "Your track"}
            </p>
            <p className="mt-0.5 text-sm tabular-nums text-slate-500 dark:text-slate-400">
              {formatTime(currentTime)} / {formatTime(duration)}
            </p>
          </div>
          <button
            onClick={togglePlayPause}
            disabled={loading}
            aria-label={isPlaying ? "Pause" : "Play"}
            className="grid h-14 w-14 shrink-0 place-items-center rounded-full bg-brand-gradient text-white shadow-lg transition-all duration-200 hover:shadow-glow hover:brightness-105 active:scale-95 disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400 focus-visible:ring-offset-2 focus-visible:ring-offset-transparent"
          >
            {isPlaying ? (
              <svg className="h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M6 5h4v14H6zM14 5h4v14h-4z" />
              </svg>
            ) : (
              <svg className="ml-0.5 h-6 w-6" fill="currentColor" viewBox="0 0 24 24">
                <path d="M8 5v14l11-7z" />
              </svg>
            )}
          </button>
        </div>
      )}

      {loading && (
        <div className="flex h-32 items-center justify-center rounded-2xl bg-slate-100/60 dark:bg-white/[0.04]">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-indigo-200 border-t-indigo-500 dark:border-white/10 dark:border-t-indigo-400"></div>
        </div>
      )}

      <div ref={containerRef} className={loading ? "hidden" : ""} />

      {!loading && (
        <div className="mt-4 space-y-3">
          {/* Playback controls — hidden when the mini player owns play/time */}
          {!playerHeader && (
          <div className="flex items-center justify-between">
            <button
              onClick={togglePlayPause}
              aria-label={isPlaying ? "Pause" : "Play"}
              className="btn-primary px-4 py-2 text-sm"
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

            <div className="text-sm tabular-nums text-slate-500 dark:text-slate-400">
              {formatTime(currentTime)} / {formatTime(duration)}
            </div>
          </div>
          )}

          {/* Region controls — hidden for read-only (result-card) waveforms */}
          {!readOnly && (
            <div className="space-y-3">
              <div className="flex flex-wrap items-center gap-3">
                <button
                  onClick={startNewRegion}
                  disabled={Boolean(pendingRange)}
                  className="btn-ghost px-3 py-1.5 text-sm disabled:cursor-not-allowed disabled:opacity-40"
                >
                  Add Protected Region
                </button>
                <button
                  onClick={clearAll}
                  className="btn-ghost px-3 py-1.5 text-sm"
                >
                  Clear All
                </button>
                <span className="text-xs text-slate-500 dark:text-slate-400">
                  Drag on the waveform to draw a region. Resize it, then press
                  Confirm.
                </span>
              </div>

              {pendingRange && (
                <div className="flex flex-wrap items-center gap-3 rounded-2xl border border-amber-300/60 bg-amber-50/80 p-3 backdrop-blur-md dark:border-amber-400/30 dark:bg-amber-500/10">
                  <div className="flex-1 text-sm text-amber-900 dark:text-amber-200">
                    <span className="font-semibold">Pending region:</span>{" "}
                    {formatTime(pendingRange.start)} –{" "}
                    {formatTime(pendingRange.end)}{" "}
                    <span className="tabular-nums text-amber-700 dark:text-amber-300/80">
                      ({(pendingRange.end - pendingRange.start).toFixed(1)}s)
                    </span>
                  </div>
                  <button
                    onClick={confirmPending}
                    className="btn-primary px-3 py-1.5 text-sm"
                  >
                    Confirm Region
                  </button>
                  <button
                    onClick={cancelPending}
                    className="btn-ghost px-3 py-1.5 text-sm"
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
