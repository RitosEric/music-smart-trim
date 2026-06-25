import React from "react";

// Fixed silhouette so the "equalizer" reads as a deliberate shape, not noise.
const HEIGHTS = [
  0.35, 0.55, 0.7, 0.5, 0.85, 0.6, 1, 0.72, 0.5, 0.8, 0.6, 0.95, 0.68, 0.5,
  0.78, 0.55, 0.9, 0.62, 0.48, 0.7, 0.42, 0.6, 0.4, 0.3,
];

/**
 * Decorative animated waveform (brand gradient bars). Purely visual — used in
 * the upload dropzone. `active` brightens it and adds a glow, e.g. while a file
 * is being dragged over.
 */
function FakeWaveform({ active = false }) {
  return (
    <div
      aria-hidden="true"
      className={`flex h-14 items-center justify-center gap-1 transition-all duration-300 ${
        active ? "drop-shadow-[0_0_16px_rgba(99,102,241,0.75)]" : ""
      }`}
    >
      {HEIGHTS.map((h, i) => (
        <span
          key={i}
          className="w-1.5 origin-center rounded-full bg-brand-gradient animate-bar-pulse"
          style={{
            height: `${h * 100}%`,
            animationDelay: `${i * 0.06}s`,
            animationDuration: active ? "0.9s" : undefined,
            opacity: active ? 1 : 0.85,
          }}
        />
      ))}
    </div>
  );
}

export default FakeWaveform;
