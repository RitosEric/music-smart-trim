import React from "react";

/**
 * Glass pill that toggles light/dark. The sun and moon are stacked and
 * cross-faded/rotated so the swap animates rather than snapping.
 */
function ThemeToggle({ isDark, onToggle }) {
  return (
    <button
      type="button"
      onClick={onToggle}
      role="switch"
      aria-checked={isDark}
      aria-label={isDark ? "Switch to light mode" : "Switch to dark mode"}
      title={isDark ? "Switch to light mode" : "Switch to dark mode"}
      className="group relative grid h-11 w-11 place-items-center rounded-2xl border border-white/60 bg-white/60 text-slate-700 shadow-sm backdrop-blur-md transition-all duration-200 hover:bg-white/90 active:scale-95 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-400/70 dark:border-white/10 dark:bg-white/[0.07] dark:text-amber-300 dark:hover:bg-white/[0.14]"
    >
      {/* Sun — visible in dark mode */}
      <svg
        className="absolute h-5 w-5 transition-all duration-300 ease-out dark:rotate-0 dark:scale-100 dark:opacity-100 rotate-90 scale-0 opacity-0"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="4" />
        <path
          strokeLinecap="round"
          d="M12 2v2m0 16v2M4.93 4.93l1.41 1.41m11.32 11.32l1.41 1.41M2 12h2m16 0h2M4.93 19.07l1.41-1.41m11.32-11.32l1.41-1.41"
        />
      </svg>
      {/* Moon — visible in light mode */}
      <svg
        className="absolute h-5 w-5 transition-all duration-300 ease-out rotate-0 scale-100 opacity-100 dark:-rotate-90 dark:scale-0 dark:opacity-0"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path
          strokeLinecap="round"
          strokeLinejoin="round"
          d="M21 12.79A9 9 0 1111.21 3 7 7 0 0021 12.79z"
        />
      </svg>
    </button>
  );
}

export default ThemeToggle;
