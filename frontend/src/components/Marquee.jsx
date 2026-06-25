import React from "react";

const PHRASES = [
  "Created for video editors",
  "Perfect for YouTube",
  "Fit your song to any video length",
  "Trim without losing the vibe",
  "Made for Reels & Shorts",
  "Keep the hook, drop the filler",
  "Built for storytellers",
];

/**
 * Seamless scrolling marquee of audience taglines. The track is duplicated
 * once and shifted -50%, so the loop is gapless. Pauses on hover; reduced-motion
 * users see it parked (the global reduced-motion rule disables the animation).
 */
function Marquee() {
  const items = [...PHRASES, ...PHRASES];
  return (
    <div className="glass-soft group relative overflow-hidden py-3">
      <div className="flex w-max animate-marquee items-center gap-10 [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)] group-hover:[animation-play-state:paused]">
        {items.map((phrase, i) => (
          <span
            key={i}
            className="flex items-center gap-3 whitespace-nowrap text-sm font-medium text-slate-500 dark:text-slate-400"
            aria-hidden={i >= PHRASES.length ? "true" : undefined}
          >
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-brand-gradient" />
            {phrase}
          </span>
        ))}
      </div>
    </div>
  );
}

export default Marquee;
