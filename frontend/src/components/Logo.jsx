import React from "react";

/**
 * Music Smart Trim brand mark — a symmetric audio waveform with two trim
 * markers converging on a center bar. Inline SVG so it stays crisp at any
 * size and the violet→blue brand gradient reads on both light and dark.
 */
function Logo({ size = 40, className = "" }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 56 56"
      className={className}
      role="img"
      aria-label="Music Smart Trim logo"
    >
      <defs>
        <linearGradient id="mstLogoGrad" x1="0" y1="0" x2="1" y2="1">
          <stop offset="0" stopColor="#7c3aed" />
          <stop offset="0.5" stopColor="#6366f1" />
          <stop offset="1" stopColor="#2563eb" />
        </linearGradient>
      </defs>
      <g fill="url(#mstLogoGrad)">
        <rect x="2.5" y="21" width="3" height="14" rx="1.5" />
        <rect x="7.5" y="15" width="3" height="26" rx="1.5" />
        <rect x="12.5" y="19" width="3" height="18" rx="1.5" />
        <path d="M19 22 L24.5 28 L19 34 Z" />
        <rect x="26.5" y="9" width="3" height="38" rx="1.5" />
        <path d="M37 22 L31.5 28 L37 34 Z" />
        <rect x="40.5" y="19" width="3" height="18" rx="1.5" />
        <rect x="45.5" y="15" width="3" height="26" rx="1.5" />
        <rect x="50.5" y="21" width="3" height="14" rx="1.5" />
      </g>
    </svg>
  );
}

export default Logo;
